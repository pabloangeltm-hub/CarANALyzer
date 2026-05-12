"""SQLite backup utility for Agartha production deployments."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from tools.utils import db


DEFAULT_RETENTION_DAYS = 30


@dataclass(frozen=True)
class BackupResult:
    source: str
    backup_path: str
    removed_old_backups: int
    rclone_remote: str | None
    rclone_uploaded: bool
    created_at: str


def create_sqlite_backup(source: Path, backup_dir: Path) -> Path:
    if not source.exists():
        raise FileNotFoundError(f"SQLite DB not found: {source}")
    if source.stat().st_size == 0:
        raise ValueError(f"SQLite DB is empty: {source}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{source.stem}_{timestamp}{source.suffix}"

    with sqlite3.connect(source) as src, sqlite3.connect(backup_path) as dst:
        src.backup(dst)
    return backup_path


def prune_old_backups(backup_dir: Path, *, retention_days: int, now: datetime | None = None) -> int:
    if retention_days < 1:
        raise ValueError("retention_days must be >= 1")
    if not backup_dir.exists():
        return 0

    cutoff = (now or datetime.now()) - timedelta(days=retention_days)
    removed = 0
    for path in backup_dir.glob("*.db"):
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        if modified < cutoff:
            path.unlink()
            removed += 1
    return removed


def upload_with_rclone(backup_path: Path, remote: str) -> None:
    subprocess.run(
        ["rclone", "copy", str(backup_path), remote],
        check=True,
        capture_output=True,
        text=True,
    )


def run_backup(
    *,
    source: Path,
    backup_dir: Path,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    rclone_remote: str | None = None,
) -> BackupResult:
    backup_path = create_sqlite_backup(source, backup_dir)
    removed = prune_old_backups(backup_dir, retention_days=retention_days)
    uploaded = False
    if rclone_remote:
        upload_with_rclone(backup_path, rclone_remote)
        uploaded = True
    return BackupResult(
        source=str(source),
        backup_path=str(backup_path),
        removed_old_backups=removed,
        rclone_remote=rclone_remote,
        rclone_uploaded=uploaded,
        created_at=datetime.now().isoformat(timespec="seconds"),
    )


def _notify_failure(message: str) -> None:
    try:
        from tools.telegram_notifier import TelegramNotifier

        TelegramNotifier().send_text(f"Agartha DB backup failed:\n{message}")
    except Exception:
        return


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backup Agartha SQLite database.")
    parser.add_argument(
        "--db-path",
        default=os.getenv("AGARTHA_DB_PATH", db.DB_PATH),
        help="SQLite database path. Defaults to AGARTHA_DB_PATH or .tmp/agartha.db.",
    )
    parser.add_argument(
        "--backup-dir",
        default=os.getenv("AGARTHA_BACKUP_DIR", ".tmp/backups"),
        help="Local backup directory.",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=int(os.getenv("AGARTHA_BACKUP_RETENTION_DAYS", str(DEFAULT_RETENTION_DAYS))),
        help="Delete local .db backups older than this many days.",
    )
    parser.add_argument(
        "--rclone-remote",
        default=os.getenv("AGARTHA_BACKUP_RCLONE_REMOTE", "").strip() or None,
        help="Optional rclone destination, for example r2:agartha-backups/db.",
    )
    parser.add_argument(
        "--no-alert",
        action="store_true",
        help="Do not send Telegram alert on failure.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = _parser().parse_args(argv)
    try:
        result = run_backup(
            source=Path(args.db_path),
            backup_dir=Path(args.backup_dir),
            retention_days=args.retention_days,
            rclone_remote=args.rclone_remote,
        )
    except Exception as exc:
        if not args.no_alert:
            _notify_failure(str(exc))
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    print(json.dumps({"ok": True, **asdict(result)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
