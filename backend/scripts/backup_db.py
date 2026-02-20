"""
Database Backup Script
Creates timestamped pg_dump backups and retains the last 7.

Usage:
    python scripts/backup_db.py
"""

import os
import sys
import subprocess
import gzip
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Add parent to path so we can import app config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def get_db_params():
    """Parse DATABASE_URL from .env into pg_dump-compatible params."""
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    db_url = os.getenv("DATABASE_URL", "")
    # Convert asyncpg URL to standard postgres URL for pg_dump
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    parsed = urlparse(db_url)
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "dbname": parsed.path.lstrip("/") or "orbit",
    }


def run_backup():
    params = get_db_params()
    backup_dir = Path(__file__).resolve().parent.parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sql_file = backup_dir / f"orbit_{timestamp}.sql"
    gz_file = backup_dir / f"orbit_{timestamp}.sql.gz"

    env = os.environ.copy()
    env["PGPASSWORD"] = params["password"]

    print(f"📦 Backing up database '{params['dbname']}' ...")

    try:
        result = subprocess.run(
            [
                "pg_dump",
                "-h", params["host"],
                "-p", params["port"],
                "-U", params["user"],
                "-d", params["dbname"],
                "-f", str(sql_file),
                "--no-owner",
                "--no-acl",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            print(f"❌ pg_dump failed: {result.stderr}")
            sys.exit(1)

        # Compress
        with open(sql_file, "rb") as f_in:
            with gzip.open(gz_file, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        sql_file.unlink()  # Remove uncompressed

        size_kb = gz_file.stat().st_size / 1024
        print(f"✅ Backup saved: {gz_file.name} ({size_kb:.1f} KB)")

    except FileNotFoundError:
        print("❌ pg_dump not found. Make sure PostgreSQL client tools are installed.")
        sys.exit(1)

    # Cleanup: keep only the last 7 backups
    backups = sorted(backup_dir.glob("orbit_*.sql.gz"), reverse=True)
    for old in backups[7:]:
        old.unlink()
        print(f"🗑️  Removed old backup: {old.name}")

    print(f"📁 Total backups: {min(len(backups), 7)}")


if __name__ == "__main__":
    run_backup()
