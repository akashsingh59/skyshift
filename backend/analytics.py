import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "skyshift_analytics.db"
DB_PATH = Path(os.getenv("ANALYTICS_DB_PATH", str(DEFAULT_DB_PATH)))


def init_analytics_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS roster_downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                downloaded_at TEXT NOT NULL,
                shift TEXT NOT NULL,
                total_controllers INTEGER NOT NULL,
                requester_ip TEXT,
                user_agent TEXT
            )
            """
        )
        connection.commit()


def analytics_health_status():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.execute("SELECT 1")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("ROLLBACK")

    return {
        "status": "ok",
        "dbPath": str(DB_PATH),
        "writable": True,
    }


def record_roster_download(shift: str, total_controllers: int, requester_ip: str | None, user_agent: str | None):
    downloaded_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.execute(
            """
            INSERT INTO roster_downloads (downloaded_at, shift, total_controllers, requester_ip, user_agent)
            VALUES (?, ?, ?, ?, ?)
            """,
            (downloaded_at, shift, total_controllers, requester_ip, user_agent),
        )
        connection.commit()


def get_last_24h_download_summary():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    since = now - timedelta(hours=24)

    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.row_factory = sqlite3.Row

        total_row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM roster_downloads
            WHERE downloaded_at >= ?
            """,
            (since.isoformat(),),
        ).fetchone()

        hour_rows = connection.execute(
            """
            SELECT
                strftime('%Y-%m-%dT%H:00:00Z', downloaded_at) AS hour_bucket_utc,
                COUNT(*) AS downloads
            FROM roster_downloads
            WHERE downloaded_at >= ?
            GROUP BY hour_bucket_utc
            ORDER BY hour_bucket_utc ASC
            """,
            (since.isoformat(),),
        ).fetchall()

        shift_rows = connection.execute(
            """
            SELECT shift, COUNT(*) AS downloads
            FROM roster_downloads
            WHERE downloaded_at >= ?
            GROUP BY shift
            ORDER BY shift ASC
            """,
            (since.isoformat(),),
        ).fetchall()

    return {
        "windowStartUtc": since.isoformat().replace("+00:00", "Z"),
        "windowEndUtc": now.isoformat().replace("+00:00", "Z"),
        "totalDownloads": int(total_row["total"]) if total_row else 0,
        "downloadsByHour": [
            {
                "hourStartUtc": row["hour_bucket_utc"],
                "downloads": row["downloads"],
            }
            for row in hour_rows
        ],
        "downloadsByShift": [
            {
                "shift": row["shift"],
                "downloads": row["downloads"],
            }
            for row in shift_rows
        ],
    }
