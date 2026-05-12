import json
import sqlite3

import pytest

from tools import run_migrations


def _table_names(db_path):
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    return {row[0] for row in rows}


def test_run_migrations_applies_sql_files_and_records_ledger(tmp_path):
    db_path = tmp_path / "agartha.db"

    result = run_migrations.run_migrations(db_path=db_path, backup=False)

    assert result.applied == [
        "002_dealers.sql",
        "003_api_usage.sql",
        "004_saved_searches.sql",
    ]
    assert result.skipped == []
    assert result.pending == []
    assert result.backup_path is None
    assert {"dealers", "api_usage", "saved_searches", "schema_migrations"}.issubset(
        _table_names(db_path)
    )

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT filename FROM schema_migrations ORDER BY filename"
        ).fetchall()

    assert [row[0] for row in rows] == result.applied


def test_run_migrations_is_idempotent_after_ledger_exists(tmp_path):
    db_path = tmp_path / "agartha.db"
    run_migrations.run_migrations(db_path=db_path, backup=False)

    result = run_migrations.run_migrations(db_path=db_path, backup=False)

    assert result.applied == []
    assert result.skipped == [
        "002_dealers.sql",
        "003_api_usage.sql",
        "004_saved_searches.sql",
    ]


def test_run_migrations_creates_backup_for_existing_database(tmp_path):
    db_path = tmp_path / "agartha.db"
    backup_dir = tmp_path / "backups"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE legacy (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO legacy DEFAULT VALUES")
        conn.commit()

    result = run_migrations.run_migrations(
        db_path=db_path,
        backup=True,
        backup_dir=backup_dir,
    )

    assert result.backup_path is not None
    backup_path = backup_dir / result.backup_path.split("\\")[-1].split("/")[-1]
    assert backup_path.exists()
    with sqlite3.connect(backup_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM legacy").fetchone()[0]
    assert count == 1


def test_dry_run_reports_pending_without_creating_database(tmp_path):
    db_path = tmp_path / "dry_run.db"

    result = run_migrations.run_migrations(db_path=db_path, dry_run=True)

    assert result.dry_run is True
    assert result.applied == []
    assert result.pending == [
        "002_dealers.sql",
        "003_api_usage.sql",
        "004_saved_searches.sql",
    ]
    assert not db_path.exists()


def test_checksum_mismatch_refuses_to_continue(tmp_path):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    migration = migrations_dir / "001_create_sample.sql"
    migration.write_text("CREATE TABLE sample (id INTEGER PRIMARY KEY);\n", encoding="utf-8")
    db_path = tmp_path / "agartha.db"

    run_migrations.run_migrations(
        db_path=db_path,
        migrations_dir=migrations_dir,
        backup=False,
    )
    migration.write_text(
        "CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT);\n",
        encoding="utf-8",
    )

    with pytest.raises(run_migrations.MigrationError, match="checksum mismatch"):
        run_migrations.run_migrations(
            db_path=db_path,
            migrations_dir=migrations_dir,
            backup=False,
        )


def test_main_outputs_json_for_dry_run(tmp_path, capsys):
    exit_code = run_migrations.main(
        [
            "--db-path",
            str(tmp_path / "dry_run_cli.db"),
            "--dry-run",
        ]
    )

    captured = capsys.readouterr()
    body = json.loads(captured.out)
    assert exit_code == 0
    assert body["ok"] is True
    assert body["dry_run"] is True
    assert body["pending"] == [
        "002_dealers.sql",
        "003_api_usage.sql",
        "004_saved_searches.sql",
    ]
