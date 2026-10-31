from datetime import datetime
import tools
from state_machine import check_tool_call, after_tool

# The only arguments the LLM may supply for each tool. Anything else is thrown away.
ALLOWED_ARGS = {
    "get_available_slots": {"speciality", "date", "limit"},
    "book_slot": {"slot_id"},
    "get_my_appointments": set(),
    "cancel_appointment": {"appointment_id"},
}


def run_tool(session, tool_name, args, now=None):
    """The one door between the LLM and our tools. Returns a dict for the LLM."""
    now = now or datetime.now()

    if tool_name not in ALLOWED_ARGS:
        return {"ok": False, "reason": f"unknown tool: {tool_name}"}

    # 1. Keep only the arguments this tool allows (phone and name can never come from the LLM)
    args = {k: v for k, v in (args or {}).items() if k in ALLOWED_ARGS[tool_name]}

    # 2. Check the rules
    allowed, reason = check_tool_call(session, tool_name, args)
    if not allowed:
        return {"ok": False, "blocked": True, "reason": reason}

    # 3. Run the real tool. Phone and name come from the session.
    try:
        if tool_name == "get_available_slots":
            raw = tools.get_available_slots(**args)
        elif tool_name == "book_slot":
            raw = tools.book_slot(args["slot_id"], session.patient_name, session.phone, now=now)
        elif tool_name == "get_my_appointments":
            raw = tools.get_my_appointments(session.phone, now=now)
        else:  # cancel_appointment
            raw = tools.cancel_appointment(args["appointment_id"], session.phone, now=now)
    except Exception as e:
        print("TOOL ERROR:", repr(e))        # we want to see real bugs while developing
        return {"ok": False, "reason": "tool_error"}

    # 4. Update the call's memory and state
    after_tool(session, tool_name, raw)

    # 5. Shape the result for the LLM
    if tool_name == "get_available_slots":
        return {"ok": True, "slots": raw}
    if tool_name == "get_my_appointments":
        return {"ok": True, "appointments": raw}
    return raw


if __name__ == "__main__":
    from seed import seed
    from config import NOW
    from state_machine import CallSession, handle_event

    def call(session, tool, args):
        result = run_tool(session, tool, args, now=NOW)
        print(f"  {tool}({args})\n     -> {result}\n     state={session.state.name}")
        return result

    seed()

    print("1. Two callers look at slots at the same time")
    priya = CallSession(phone="9999900001")
    ravi = CallSession(phone="9999900002")
    for s in (priya, ravi):
        handle_event(s, "greeted")
        handle_event(s, "wants_book")
    print(" LLM tries to book before any slots were offered:")
    call(priya, "book_slot", {"slot_id": 1})
    p_slots = call(priya, "get_available_slots", {})["slots"]
    call(ravi, "get_available_slots", {})
    target = p_slots[0]["id"]

    print("2. Priya books (the LLM also sneaks in another phone and name)")
    handle_event(priya, "slot_chosen", slot_id=target)
    handle_event(priya, "name_given", name="Priya")
    handle_event(priya, "details_confirmed")
    call(priya, "book_slot", {"slot_id": target, "phone": "0000000000", "patient_name": "Hacker"})

    print("3. Ravi wants the same slot, but it is gone")
    handle_event(ravi, "slot_chosen", slot_id=target)
    handle_event(ravi, "name_given", name="Ravi")
    handle_event(ravi, "details_confirmed")
    call(ravi, "book_slot", {"slot_id": target})
    print(" Ravi searches again and takes the next free slot")
    new_slots = call(ravi, "get_available_slots", {})["slots"]
    handle_event(ravi, "slot_chosen", slot_id=new_slots[0]["id"])
    handle_event(ravi, "details_confirmed")
    call(ravi, "book_slot", {"slot_id": new_slots[0]["id"]})

    print("4. Priya cancels")
    handle_event(priya, "needs_more")
    handle_event(priya, "wants_cancel")
    appts = call(priya, "get_my_appointments", {})["appointments"]
    my_id = appts[0]["appointment_id"]
    handle_event(priya, "appointment_chosen", appointment_id=my_id)
    print(" LLM tries to cancel Ravi's appointment instead:")
    call(priya, "cancel_appointment", {"appointment_id": my_id + 1})
    print(" Now the right one:")
    call(priya, "cancel_appointment", {"appointment_id": my_id})

    print("5. Outbox")
    from db import get_connection
    with get_connection() as conn:
        for r in conn.execute("SELECT phone, message FROM outbox"):
            print("  ", dict(r))
