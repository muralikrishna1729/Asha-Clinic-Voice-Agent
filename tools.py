from db import get_connection
from datetime import datetime
from config import CLINIC_NAME, CLINIC_ADDRESS

def get_available_slots(speciality=None, date=None, limit=3, now=None):
    """Return free slots that start after 'now', earliest first..
    speciality: e.g. 'Dermatology' (optional)
    date: 'YYYY-MM-DD' (optional)
    limit: how many to return (a voice agent should not read 30 slots)
    now: the current time (for testing purposes)
    """
    now = now or datetime.now()
    sql = "SELECT id, doctor, speciality, start_time FROM slots WHERE status = 'free' AND start_time > ?"
    params = [now.strftime("%Y-%m-%d %H:%M")]

    if speciality:
        sql += " AND LOWER(speciality) = LOWER(?)"
        params.append(speciality)
    if date:
        sql += " AND date(start_time) = ?"
        params.append(date)

    sql += " ORDER BY start_time LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]

def book_slot(slot_id, patient_name, phone, now = None):
    """Book a slot only if it is still free. Also saves the confirmation message."""
    now = now or datetime.now()
    with get_connection() as conn: # one transaction: all steps succeed, or none do
        # 1. Try to take the slot. This works only if it is still free.
        curr = conn.execute(
            "UPDATE slots SET status = 'booked' WHERE id = ? AND status = 'free'",
            (slot_id,),
        )
        if curr.rowcount == 0:   # nothing changed, so someone else has it (or the id is wrong)
            return {"ok": False, "reason": "slot_not_available"}

        # 2. Save the appointment
        conn.execute(
            "INSERT INTO appointments (patient_name, phone, slot_id, created_at) VALUES (?, ?, ?, ?)",
            (patient_name, phone, slot_id, now.strftime("%Y-%m-%d %H:%M:%S")),
        )
        appointment_id = curr.lastrowid
        # 3. Save the confirmation message (our fake SMS)
        slot = conn.execute(
            "SELECT doctor, start_time FROM slots WHERE id = ?", (slot_id,)
        ).fetchone()
        when = datetime.strptime(slot["start_time"], "%Y-%m-%d %H:%M").strftime("%a %d %b at %H:%M")
        message = (
            f"Hi {patient_name}, your appointment with {slot['doctor']} is confirmed "
            f"for {when}. {CLINIC_NAME}, {CLINIC_ADDRESS}."
        )
        conn.execute(
            "INSERT INTO outbox (phone, message, created_at) VALUES (?, ?, ?)",
            (phone, message, now.strftime("%Y-%m-%d %H:%M")),
        )
    return {
    "ok": True,
    "appointment_id": appointment_id,
    "doctor": slot["doctor"],
    "start_time": slot["start_time"],
}

def cancel_appointment(appointment_id, phone, now = None):
    """Cancel a booked appointment, free its slot, and save a cancellation message.
    The phone number must match the booking, so nobody can cancel someone else's appointment."""
    now = now or datetime.now()

    with get_connection() as conn:
        # 1. Cancel it, but only if it is booked AND belongs to this phone number
        cur = conn.execute(
            "UPDATE appointments SET status = 'cancelled' "
            "WHERE id = ? AND phone = ? AND status = 'booked'",
            (appointment_id, phone),
        )
        if cur.rowcount == 0:
            return {"ok": False, "reason": "appointment_not_found"}

        # 2. Free the slot so someone else can book it
        row = conn.execute(
            "SELECT a.patient_name, s.id AS slot_id, s.doctor, s.start_time "
            "FROM appointments a JOIN slots s ON s.id = a.slot_id WHERE a.id = ?",
            (appointment_id,),
        ).fetchone()
        conn.execute("UPDATE slots SET status = 'free' WHERE id = ?", (row["slot_id"],))

        # 3. Save the cancellation message (our fake SMS)
        when = datetime.strptime(row["start_time"], "%Y-%m-%d %H:%M").strftime("%a %d %b at %H:%M")
        message = (
            f"Hi {row['patient_name']}, your appointment with {row['doctor']} "
            f"on {when} has been cancelled. {CLINIC_NAME}."
        )
        conn.execute(
            "INSERT INTO outbox (phone, message, created_at) VALUES (?, ?, ?)",
            (phone, message, now.strftime("%Y-%m-%d %H:%M")),
        )

    return {"ok": True, "doctor": row["doctor"], "start_time": row["start_time"]}

def get_my_appointments(phone, now=None):
    """Return this phone number's upcoming booked appointments, earliest first."""
    now = now or datetime.now()

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT a.id AS appointment_id, a.patient_name, "
            "       s.doctor, s.speciality, s.start_time "
            "FROM appointments a JOIN slots s ON s.id = a.slot_id "
            "WHERE a.phone = ? AND a.status = 'booked' AND s.start_time >= ? "
            "ORDER BY s.start_time",
            (phone, now.strftime("%Y-%m-%d %H:%M")),
        ).fetchall()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    # print("Any 3 earliest:")
    # for s in get_available_slots():
    #     print(" ", s)

    # print("Dermatology:")
    # for s in get_available_slots(speciality="dermatology"):
    #     print(" ", s)

    # print("On 2026-11-04:")
    # for s in get_available_slots(date="2026-11-04", limit=10):
    #     print(" ", s)

    # print("Unknown speciality:", get_available_slots(speciality="Cardiology"))

    # from seed import seed
    # from config import NOW

    # seed()  # fresh data every run

    # print("1. Priya books slot 1:")
    # print("  ", book_slot(1, "Priya", "9999900001", now=NOW))

    # print("2. Ravi tries the same slot 1:")
    # print("  ", book_slot(1, "Ravi", "9999900002", now=NOW))

    # print("3. Slot 1 should be gone from the free list:")
    # print("  ", [s["id"] for s in get_available_slots(limit=5)])

    # print("4. Outbox and appointments:")
    # with get_connection() as conn:
    #     for r in conn.execute("SELECT phone, message FROM outbox"):
    #         print("  ", dict(r))
    #     print("   appointments:", conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0])
    #     print("   outbox rows :", conn.execute("SELECT COUNT(*) FROM outbox").fetchone()[0])

    from datetime import datetime
    print([s["id"] for s in get_available_slots(limit=3, now=datetime(2026, 11, 2, 9, 0))])
    print([s["id"] for s in get_available_slots(limit=3, now=datetime(2026, 11, 3, 10, 30))])