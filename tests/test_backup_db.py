import json
import os
import sqlite3
from datetime import datetime, timedelta

from tools import backup_db


def _create_db(path):
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO sample (name) VALUES ('agartha')")
        conn.commit()


def test_create_sqlite_backup_copies_database(tmp_path):
    source = tmp_path / "agartha.db"
    backup_dir = tmp_path / "backups"
    _create_db(source)

    backup_path = backup_db.create_sqlite_backup(source, backup_dir)

    assert backup_path.exists()
    assert backup_path.parent == backup_dir
    with sqlite3.connect(backup_path) as conn:
        row = conn.execute("SELECT name FROM sample").fetchone()
    assert row == ("agartha",)


def test_prune_old_backups_removes_only_expired_db_files(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    old_backup = backup_dir / "old.db"
    fresh_backup = backup_dir / "fresh.db"
    ignored = backup_dir / "notes.txt"
    old_backup.write_text("old")
    fresh_backup.write_text("fresh")
    ignored.write_text("ignore")

    now = datetime(2026, 5, 10, 12, 0, 0)
    old_mtime = (now - timedelta(days=31)).timestamp()
    fresh_mtime = (now - timedelta(days=1)).timestamp()
    os.utime(old_backup, (old_mtime, old_mtime))
    os.utime(fresh_backup, (fresh_mtime, fresh_mtime))

    removed = backup_db.prune_old_backups(backup_dir, retention_days=30, now=now)

    assert removed == 1
    assert not old_backup.exists()
    assert fresh_backup.exists()
    assert ignored.exists()


def test_run_backup_uploads_with_rclone_when_remote_is_set(tmp_path, monkeypatch):
    source = tmp_path / "agartha.db"
    backup_dir = tmp_path / "backups"
    _create_db(source)
    calls = []

    def fake_upload(backup_path, remote):
        calls.append((backup_path, remote))

    monkeypatch.setattr(backup_db, "upload_with_rclone", fake_upload)

    result = backup_db.run_backup(
        source=source,
        backup_dir=backup_dir,
        retention_days=30,
        rclone_remote="r2:agartha/db",
    )

    assert result.rclone_uploaded is True
    assert result.rclone_remote == "r2:agartha/db"
    assert len(calls) == 1
    assert calls[0][0].exists()
    assert calls[0][1] == "r2:agartha/db"


def test_main_outputs_json_and_nonzero_on_missing_db(tmp_path, capsys):
    exit_code = backup_db.main(
        [
            "--db-path",
            str(tmp_path / "missing.db"),
            "--backup-dir",
            str(tmp_path / "backups"),
            "--no-alert",
        ]
    )

    captured = capsys.readouterr()
    body = json.loads(captured.err)
    assert exit_code == 1
    assert body["ok"] is False
    assert "SQLite DB not found" in body["error"]
