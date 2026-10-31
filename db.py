import sqlite3

DB_PATH = "clinic.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # lets us read columns by name
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite ignores links between tables unless we turn this on
    return conn


def create_tables():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS slots (
            id          INTEGER PRIMARY KEY,
            doctor      TEXT NOT NULL,
            speciality  TEXT NOT NULL,
            start_time  TEXT NOT NULL,      -- like '2026-11-02 10:00'
            status      TEXT NOT NULL DEFAULT 'free'
                        CHECK (status IN ('free', 'booked'))
        );
        CREATE TABLE IF NOT EXISTS appointments (
            id            INTEGER PRIMARY KEY,
            patient_name  TEXT NOT NULL,
            phone         TEXT NOT NULL,
            slot_id       INTEGER NOT NULL REFERENCES slots(id),
            status        TEXT NOT NULL DEFAULT 'booked'
                          CHECK (status IN ('booked', 'cancelled')),
            created_at    TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS outbox (
            id          INTEGER PRIMARY KEY,
            phone       TEXT NOT NULL,
            message     TEXT NOT NULL,
            created_at  TEXT NOT NULL
        );
        """)

if __name__ == "__main__":
    create_tables()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    print("Tables:", [r["name"] for r in rows])
    