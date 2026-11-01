import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tool_specs import TOOL_SPECS
from config import TODAY, NOW
from state_machine import CallSession, handle_event
from runner import run_tool
from seed import seed

load_dotenv()
seed()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM = (
    "You are Asha, the virtual receptionist of a small clinic, speaking on a phone call. "
    "Keep replies short. "
    f"Today is {TODAY.strftime('%A, %Y-%m-%d')}."
)

config = types.GenerateContentConfig(
    system_instruction=SYSTEM,
    tools=[types.Tool(function_declarations=TOOL_SPECS)],
)

# One session for the whole demo — phone from caller ID, never from the LLM.
session = CallSession(phone="9999900001")

# Each test message and the state-machine event it triggers (if any).
tests = [
    ("Hi, who is this?", "greeted"),
    ("I need to see a skin doctor.", "wants_book"),
    ("Do you have anything on Wednesday for general medicine?", None),
    ("Book slot 5 for me, my name is Ravi.", None),
]

for text, event in tests:
    print(f"\nCaller: {text}")

    # Drive the state machine for events we can map from the user's utterance.
    if event:
        ok, reason = handle_event(session, event)
        print(f"  [state: {event} -> {'ok' if ok else 'rejected: ' + reason}] state={session.state.name}")

    # Special setup for the booking test: choose a slot, give a name, confirm details.
    if text.startswith("Book slot"):
        # Find an offered dermatology slot to choose (from the earlier search).
        offered = sorted(session.offered_slot_ids)
        if offered:
            handle_event(session, "slot_chosen", slot_id=offered[0])
        handle_event(session, "name_given", name="Ravi")
        handle_event(session, "details_confirmed")
        print(f"  [state: slot_chosen/name_given/details_confirmed -> state={session.state.name}]")

    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL"), contents=text, config=config
    )
    parts = response.candidates[0].content.parts or []
    for part in parts:
        if part.function_call:
            fname = part.function_call.name
            fargs = dict(part.function_call.args or {})
            print(f"  TOOL REQUEST: {fname} {fargs}")
            result = run_tool(session, fname, fargs, now=NOW)
            print(f"  TOOL RESULT:  {result}")

            # Feed the tool result back to Gemini for a final text reply.
            follow_up = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL"),
                contents=[
                    types.Content(role="user", parts=[types.Part.from_text(text=text)]),
                    types.Content(
                        role="model",
                        parts=[
                            types.Part(
                                function_call=part.function_call,
                                thought_signature=part.thought_signature,
                            )
                        ],
                    ),
                    types.Content(
                        role="user",
                        parts=[types.Part.from_function_response(name=fname, response=result)],
                    ),
                ],
                config=config,
            )
            for fp in follow_up.candidates[0].content.parts or []:
                if fp.text:
                    print(f"  TEXT: {fp.text.strip()}")
        elif part.text:
            print(f"  TEXT: {part.text.strip()}")