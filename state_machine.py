from dataclasses import dataclass, field
from enum import Enum


class State(Enum):
    GREETING = "greeting"
    UNDERSTAND = "understand"
    OFFER_SLOTS = "offer_slots"
    CONFIRM_DETAILS = "confirm_details"
    BOOKING = "booking"
    SHOW_APPOINTMENTS = "show_appointments"
    CANCELLING = "cancelling"
    WRAP_UP = "wrap_up"
    EMERGENCY_END = "emergency_end"
    NEEDS_HUMAN = "needs_human"


# Which tools may be used in which state. A state not listed here allows no tools.
ALLOWED_TOOLS = {
    State.OFFER_SLOTS: {"get_available_slots"},
    State.BOOKING: {"book_slot"},
    State.SHOW_APPOINTMENTS: {"get_my_appointments"},
    State.CANCELLING: {"cancel_appointment"},
}

TERMINAL = {State.EMERGENCY_END, State.NEEDS_HUMAN}   # the call is over, nothing else is allowed

# Simple moves that need no extra checking: (current state, event) -> next state
SIMPLE_MOVES = {
    (State.GREETING, "greeted"): State.UNDERSTAND,
    (State.UNDERSTAND, "wants_book"): State.OFFER_SLOTS,
    (State.UNDERSTAND, "wants_cancel"): State.SHOW_APPOINTMENTS,
    (State.CONFIRM_DETAILS, "wants_other_slots"): State.OFFER_SLOTS,
    (State.WRAP_UP, "needs_more"): State.UNDERSTAND,
}

@dataclass
class CallSession:
    """Everything we remember during one call."""
    phone: str                                    # from caller ID, never from the LLM
    state: State = State.GREETING
    offered_slot_ids: set = field(default_factory=set)
    chosen_slot_id: int | None = None
    patient_name: str | None = None
    shown_appointment_ids: set = field(default_factory=set)
    chosen_appointment_id: int | None = None


def check_tool_call(session, tool_name, args):
    """Return (True, "") if the tool call is allowed, else (False, reason)."""
    allowed = ALLOWED_TOOLS.get(session.state, set())
    if tool_name not in allowed:
        return False, f"{tool_name} is not allowed in state {session.state.name}"

    if tool_name == "book_slot":
        slot_id = args.get("slot_id")
        if slot_id not in session.offered_slot_ids:
            return False, "that slot was not offered in this call"
        if slot_id != session.chosen_slot_id:
            return False, "the patient did not choose that slot"
        if not session.patient_name:
            return False, "patient name not collected yet"

    if tool_name == "cancel_appointment":
        chosen = session.chosen_appointment_id
        if chosen is None or args.get("appointment_id") != chosen:
            return False, "the caller did not choose that appointment"

    return True, ""


def handle_event(session, event, **data):
    """Something happened in the conversation. Return (True, "") if we moved, else (False, reason)."""
    if session.state in TERMINAL:
        return False, "the call is already over"
    # These two work from any state
    if event == "emergency":
        session.state = State.EMERGENCY_END
        return True, ""
    if event == "stuck":
        session.state = State.NEEDS_HUMAN
        return True, ""

    # Events that need checks
    if event == "slot_chosen":
        if session.state != State.OFFER_SLOTS:
            return False, "no slots are being offered right now"
        if data.get("slot_id") not in session.offered_slot_ids:
            return False, "that slot was not offered in this call"
        session.chosen_slot_id = data["slot_id"]
        session.state = State.CONFIRM_DETAILS
        return True, ""
    
    if event == "name_given":
        if session.state != State.CONFIRM_DETAILS:
            return False, "not collecting details right now"
        name = (data.get("name") or "").strip()
        if len(name) < 2:
            return False, "name is too short"
        session.patient_name = name
        return True, ""

    if event == "details_confirmed":
        if session.state != State.CONFIRM_DETAILS:
            return False, "not collecting details right now"
        if session.chosen_slot_id is None or not session.patient_name:
            return False, "slot or name is missing"
        session.state = State.BOOKING
        return True, ""

    if event == "appointment_chosen":
        if session.state != State.SHOW_APPOINTMENTS:
            return False, "no appointments are being shown right now"
        if data.get("appointment_id") not in session.shown_appointment_ids:
            return False, "that appointment was not shown to the caller"
        session.chosen_appointment_id = data["appointment_id"]
        session.state = State.CANCELLING
        return True, ""

    # Simple moves from the table
    next_state = SIMPLE_MOVES.get((session.state, event))
    if next_state is None:
        return False, f"'{event}' is not valid in state {session.state.name}"
    if event == "wants_other_slots":
        session.chosen_slot_id = None
    session.state = next_state
    return True, ""

def after_tool(session, tool_name, result):
    """A tool has run. Update the call's memory and state from its result."""
    if tool_name == "get_available_slots":
        session.offered_slot_ids |= {s["id"] for s in result}

    elif tool_name == "book_slot":
        if result["ok"]:
            session.state = State.WRAP_UP
        else:                                  # slot was taken: forget old offers, search again
            session.chosen_slot_id = None
            session.offered_slot_ids = set()
            session.state = State.OFFER_SLOTS

    elif tool_name == "get_my_appointments":
        session.shown_appointment_ids |= {a["appointment_id"] for a in result}

    elif tool_name == "cancel_appointment":
        if result["ok"]:
            session.state = State.WRAP_UP
        else:
            session.chosen_appointment_id = None
            session.state = State.SHOW_APPOINTMENTS







    
if __name__ == "__main__":
    # def show(label, session, tool, args):
    #     ok, reason = check_tool_call(session, tool, args)
    #     print(f"{label}: {'ALLOWED' if ok else 'BLOCKED - ' + reason}")

    # s = CallSession(phone="9999900001")

    # show("1. book in GREETING", s, "book_slot", {"slot_id": 1})

    # s.state = State.OFFER_SLOTS
    # show("2. search in OFFER_SLOTS", s, "get_available_slots", {})

    # s.offered_slot_ids = {1, 2, 3}
    # s.state = State.BOOKING
    # show("3. book, nothing chosen yet", s, "book_slot", {"slot_id": 1})

    # s.chosen_slot_id = 1
    # show("4. book, no name yet", s, "book_slot", {"slot_id": 1})

    # s.patient_name = "Priya"
    # show("5. book a slot never offered", s, "book_slot", {"slot_id": 9})
    # show("6. book the chosen slot", s, "book_slot", {"slot_id": 1})

    # s.state = State.CANCELLING
    # show("7. cancel an unseen appointment", s, "cancel_appointment", {"appointment_id": 5})
    # s.shown_appointment_ids = {5}
    # show("8. cancel a shown appointment", s, "cancel_appointment", {"appointment_id": 5})

    def event(session, event_name, **data):
        ok, reason = handle_event(session, event_name, **data)
        note = "" if ok else f"  ({reason})"
        print(f"  {event_name:<18} {'ok      ' if ok else 'REJECTED'} state={session.state.name}{note}")

    def run_tool(session, tool, args, fake_result):
        ok, reason = check_tool_call(session, tool, args)
        if not ok:
            print(f"  {tool:<20} BLOCKED  ({reason})")
            return
        after_tool(session, tool, fake_result)
        print(f"  {tool:<20} allowed  state={session.state.name}")

    print("1. Happy booking")
    s = CallSession(phone="9999900001")
    event(s, "greeted")
    event(s, "wants_book")
    run_tool(s, "get_available_slots", {}, [{"id": 1}, {"id": 2}, {"id": 3}])
    event(s, "slot_chosen", slot_id=2)
    event(s, "name_given", name="Priya")
    event(s, "details_confirmed")
    run_tool(s, "book_slot", {"slot_id": 2}, {"ok": True})

    print("2. Patient picks a slot that was never offered")
    s = CallSession(phone="9999900001")
    event(s, "greeted")
    event(s, "wants_book")
    run_tool(s, "get_available_slots", {}, [{"id": 1}])
    event(s, "slot_chosen", slot_id=9)

    print("3. Slot taken at the last moment")
    s = CallSession(phone="9999900002")
    event(s, "greeted")
    event(s, "wants_book")
    run_tool(s, "get_available_slots", {}, [{"id": 1}])
    event(s, "slot_chosen", slot_id=1)
    event(s, "name_given", name="Ravi")
    event(s, "details_confirmed")
    run_tool(s, "book_slot", {"slot_id": 1}, {"ok": False, "reason": "slot_not_available"})
    event(s, "slot_chosen", slot_id=1)

    print("4. Cancel path")
    s = CallSession(phone="9999900001")
    event(s, "greeted")
    event(s, "wants_cancel")
    run_tool(s, "get_my_appointments", {}, [{"appointment_id": 5}, {"appointment_id": 6}])
    event(s, "appointment_chosen", appointment_id=5)
    run_tool(s, "cancel_appointment", {"appointment_id": 6}, {"ok": True})
    run_tool(s, "cancel_appointment", {"appointment_id": 5}, {"ok": True})
    event(s, "needs_more")

    print("5. Emergency")
    s = CallSession(phone="9999900001")
    event(s, "greeted")
    event(s, "wants_book")
    event(s, "emergency")
    event(s, "wants_book")