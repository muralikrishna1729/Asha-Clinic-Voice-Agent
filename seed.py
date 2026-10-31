from datetime import datetime, timedelta
from config import TODAY
from db import get_connection, create_tables

DOCTORS = [
    ("Dr. Rao",   "General Medicine", ["10:00", "11:30"]),
    ("Dr. Meena", "Dermatology",      ["14:00", "16:00"]),
    ("Dr. Khan",  "Orthopedics",      ["09:30", "15:00"]),
]
DAYS_AHEAD = 5  # slots for tomorrow and the next 4 days


def seed():
    create_tables()
    with get_connection() as conn:
        # clear old data, children first because of the foreign keys
        conn.execute("DELETE FROM outbox")
        conn.execute("DELETE FROM appointments")
        conn.execute("DELETE FROM slots")

        for offset in range(1, DAYS_AHEAD + 1):
            day = TODAY + timedelta(days=offset)
            for doctor, speciality, times in DOCTORS:
                for t in times:
                    conn.execute(
                        "INSERT INTO slots (doctor, speciality, start_time) VALUES (?, ?, ?)",
                        (doctor, speciality, f"{day.isoformat()} {t}"),
                    )


def show_slots():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, doctor, speciality, start_time, status FROM slots ORDER BY start_time"
        ).fetchall()
    for r in rows:
        when = datetime.strptime(r["start_time"], "%Y-%m-%d %H:%M").strftime("%a %d %b, %H:%M")
        print(f'{r["id"]:>2}  {when}  {r["doctor"]:<9} {r["speciality"]:<17} {r["status"]}')
    print("Total slots:", len(rows))


if __name__ == "__main__":
    seed()
    show_slots()