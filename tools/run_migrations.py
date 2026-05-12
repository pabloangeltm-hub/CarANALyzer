"""Production-safe SQLite migration runner for Agartha."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from tools.backup_db import create_sqlite_backup


DEFAULT_DB_PATH = ".tmp/agartha.db"
DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parent / "api" / "migrations"
DEFAULT_BUSY_TIMEOUT_MS = 30000


class MigrationError(RuntimeError):
    """Raised when migrations cannot be applied safely."""


@dataclass(frozen=True)
class Migration:
    filename: str
    path: str
    checksum: str
    sql: str


@dataclass(frozen=True)
class MigrationRunResult:
    db_path: str
    migrations_dir: str
    applied: list[str]
    skipped: list[str]
    pending: list[str]
    backup_path: str | None
    dry_run: bool
    created_at: str


def discover_migrations(migrations_dir: Path) -> list[Migration]:
    if not migrations_dir.exists():
        raise FileNotFoundError(f"migrations directory not found: {migrations_dir}")
    if not migrations_dir.is_dir():
        raise NotADirectoryError(f"migrations path is not a directory: {migrations_dir}")

    migrations: list[Migration] = []
    for path in sorted(migrations_dir.glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        migrations.append(
            Migration(
                filename=path.name,
                path=str(path),
                checksum=checksum,
                sql=sql,
            )
        )
    if not migrations:
        raise MigrationError(f"no .sql migrations found in {migrations_dir}")
    return migrations


def _connect(db_path: Path, busy_timeout_ms: int) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=busy_timeout_ms / 1000)
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _read_applied(conn: sqlite3.Connection) -> dict[str, str]:
    table_exists = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = 'schema_migrations'
        """
    ).fetchone()
    if table_exists is None:
        return {}

    rows = conn.execute("SELECT filename, checksum FROM schema_migrations").fetchall()
    return {str(row["filename"]): str(row["checksum"]) for row in rows}


def _ensure_schema_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename   TEXT PRIMARY KEY,
            checksum   TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def _validate_applied(migrations: list[Migration], applied: dict[str, str]) -> None:
    known = {migration.filename: migration for migration in migrations}
    for filename, checksum in applied.items():
        migration = known.get(filename)
        if migration is not None and migration.checksum != checksum:
            raise MigrationError(
                f"applied migration checksum mismatch for {filename}; "
                "refusing to continue"
            )


def _split_sql_statements(sql: str, *, filename: str) -> list[str]:
    statements: list[str] = []
    buffer = ""
    for line in sql.splitlines():
        buffer += line + "\n"
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                statements.append(statement)
            buffer = ""

    if buffer.strip():
        raise MigrationError(f"incomplete SQL statement in {filename}")
    return statements


def _apply_sql(conn: sqlite3.Connection, migration: Migration) -> None:
    for statement in _split_sql_statements(migration.sql, filename=migration.filename):
        conn.execute(statement)


def plan_migrations(
    *,
    db_path: Path,
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
    busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
) -> tuple[list[Migration], list[str], list[str]]:
    migrations = discover_migrations(migrations_dir)
    applied: dict[str, str] = {}
    if db_path.exists():
        with _connect(db_path, busy_timeout_ms) as conn:
            applied = _read_applied(conn)
    _validate_applied(migrations, applied)
    skipped = [migration.filename for migration in migrations if migration.filename in applied]
    pending = [migration.filename for migration in migrations if migration.filename not in applied]
    return migrations, skipped, pending


def run_migrations(
    *,
    db_path: Path,
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
    backup: bool = True,
    backup_dir: Path | None = None,
    dry_run: bool = False,
    busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
) -> MigrationRunResult:
    migrations, skipped, pending = plan_migrations(
        db_path=db_path,
        migrations_dir=migrations_dir,
        busy_timeout_ms=busy_timeout_ms,
    )
    backup_path: Path | None = None

    if dry_run:
        return MigrationRunResult(
            db_path=str(db_path),
            migrations_dir=str(migrations_dir),
            applied=[],
            skipped=skipped,
            pending=pending,
            backup_path=None,
            dry_run=True,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )

    if backup and pending and db_path.exists() and db_path.stat().st_size > 0:
        backup_path = create_sqlite_backup(db_path, backup_dir or (db_path.parent / "backups"))

    applied_now: list[str] = []
    with _connect(db_path, busy_timeout_ms) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            _ensure_schema_migrations(conn)
            current_applied = _read_applied(conn)
            _validate_applied(migrations, current_applied)

            for migration in migrations:
                if migration.filename in current_applied:
                    continue
                _apply_sql(conn, migration)
                conn.execute(
                    """
                    INSERT INTO schema_migrations (filename, checksum, applied_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        migration.filename,
                        migration.checksum,
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                )
                current_applied[migration.filename] = migration.checksum
                applied_now.append(migration.filename)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    final_skipped = [migration.filename for migration in migrations if migration.filename not in applied_now]
    return MigrationRunResult(
        db_path=str(db_path),
        migrations_dir=str(migrations_dir),
        applied=applied_now,
        skipped=final_skipped,
        pending=[],
        backup_path=str(backup_path) if backup_path else None,
        dry_run=False,
        created_at=datetime.now().isoformat(timespec="seconds"),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Agartha SQLite migrations safely.")
    parser.add_argument(
        "--db-path",
        default=os.getenv("AGARTHA_DB_PATH", DEFAULT_DB_PATH),
        help="SQLite database path. Defaults to AGARTHA_DB_PATH or .tmp/agartha.db.",
    )
    parser.add_argument(
        "--migrations-dir",
        default=os.getenv("AGARTHA_MIGRATIONS_DIR", str(DEFAULT_MIGRATIONS_DIR)),
        help="Directory containing ordered .sql migration files.",
    )
    parser.add_argument(
        "--backup-dir",
        default=os.getenv("AGARTHA_MIGRATION_BACKUP_DIR", "").strip() or None,
        help="Optional backup directory. Defaults to <db-dir>/backups.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip the automatic pre-migration backup.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report pending migrations without creating or changing the database.",
    )
    parser.add_argument(
        "--busy-timeout-ms",
        type=int,
        default=int(os.getenv("AGARTHA_DB_BUSY_TIMEOUT_MS", str(DEFAULT_BUSY_TIMEOUT_MS))),
        help="SQLite busy timeout in milliseconds.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = _parser().parse_args(argv)
    try:
        result = run_migrations(
            db_path=Path(args.db_path),
            migrations_dir=Path(args.migrations_dir),
            backup=not args.no_backup,
            backup_dir=Path(args.backup_dir) if args.backup_dir else None,
            dry_run=args.dry_run,
            busy_timeout_ms=args.busy_timeout_ms,
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    print(json.dumps({"ok": True, **asdict(result)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
