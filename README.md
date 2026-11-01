# Asha: Clinic Voice Receptionist Agent

Asha is a small AI receptionist for a clinic. A caller says what they need, Asha offers real appointment slots from a database, books the one the caller picks, and saves a confirmation message. A second flow reminds patients about upcoming appointments.

This is a learning project built step by step. It is small on purpose, but it is designed the way a real system should be: the language model talks, and plain code enforces the rules.

> **Status:** work in progress. The database, tools, rule engine, LLM wrapper and a first tool-calling loop work today. Voice (speech in and out) and the reminder flow are planned. See the [Roadmap](#roadmap).

---

## What Asha does

**Inbound call (patient calls the clinic)**

1. Asha greets the caller and says she is the clinic's virtual assistant.
2. The caller says what they need, for example "I need to see a skin doctor".
3. Asha offers up to three free slots from the database.
4. The caller picks one, Asha confirms the name, and the booking is saved.
5. A confirmation message is written to an outbox table (a stand-in for a real SMS).

The caller can also cancel or reschedule, and ask simple questions such as the clinic address.

**Outbound reminder call (clinic calls the patient)** *(planned)*

- Asha calls, asks "Am I speaking with Priya?", and only after a yes, reminds the patient of the day, time, doctor and place.
- The call is made only if the booking was made at least about 4 days ahead, and about 1.5 days before the appointment. For last-minute bookings the confirmation message is enough.
- Calls are made only during calling hours (about 8 AM to 6 PM local time), never at night.
- Asha does not ask "does that time still work?". She only reminds. If the patient brings up a problem (can't come, wants another day, asks the address), Asha handles it with the same tools.

---

## Design ideas

| Idea | How it is done |
|---|---|
| **The model proposes, the code decides** | The LLM can only *ask* for a tool. Every request goes through one function (`runner.py`) that checks the rules first. |
| **No invented slots** | Slots come only from the database. A booking is allowed only for a slot that was offered in this call and chosen by the caller. |
| **No double booking** | Booking is one atomic SQL statement: `UPDATE ... WHERE status = 'free'`. If it changes zero rows, someone else got the slot. |
| **All or nothing** | Booking, appointment record and confirmation message are saved in one transaction. |
| **Identity comes from the session, not the model** | The phone number (from caller ID in a real system) and patient name are filled in by code. Extra arguments the model sends are dropped. |
| **State machine for the call** | Each state allows only certain tools. Terminal states (emergency, needs human) end the call. |
| **Provider fallback** | One `chat()` function tries Gemini first, then DeepSeek, so a provider outage does not end the call. |
| **Repeatable tests** | Time is passed in as a parameter, so results do not depend on the real clock. |

### Safety rules

- Asha does **not** diagnose or give medical advice. Symptoms are only used to pick a speciality from a short fixed list.
- Possible emergencies are not handled by Asha. She tells the caller to contact their local emergency number and ends the call.
- If the caller is stuck or angry, the call is logged as needing a human and reception calls back.
- Only fake demo patients are used. Free LLM tiers may use submitted content to improve their products, so never send real patient data.

---

## Architecture

```
caller text
    │
    ▼
 llm.py ───────► Gemini (primary) ──fails──► DeepSeek (backup)
    │
    │  model replies with text, or asks for a tool
    ▼
 runner.py  (the one door between the model and the tools)
    │   1. keep only allowed arguments
    │   2. check the rules      ◄── state_machine.py (call memory + allowed tools)
    │   3. run the real tool    ──► tools.py ──► SQLite (clinic.db)
    │   4. update the call state
    ▼
 result goes back to the model, which turns it into a short spoken sentence
```

Call flow (inbound):

```
GREETING → UNDERSTAND → OFFER_SLOTS → CONFIRM_DETAILS → BOOKING → WRAP_UP
                │
                ├── cancel → SHOW_APPOINTMENTS → CANCELLING → WRAP_UP
                ├── emergency → EMERGENCY_END
                └── stuck → NEEDS_HUMAN
```

---

## Tech stack and why

| Part | Choice | Why |
|---|---|---|
| Language | Python 3.10+ | Best ecosystem for LLM and voice work. |
| Database | SQLite (built-in `sqlite3`) | No setup, real transactions, and atomic booking with one statement. For production I would move to PostgreSQL. |
| LLM (primary) | Gemini Flash-Lite (`gemini-3.5-flash-lite`) | Free tier for development, fast, supports tool calling. |
| LLM (backup) | DeepSeek (`deepseek-flash`) | Very cheap, OpenAI-compatible API, easy to add as a fallback. |
| Framework | None | The flow is small and a state machine fits it. Plain code is faster to debug and easy to explain. |
| Config | `python-dotenv` | Keys stay out of code and out of Git. |
| Time | Built-in `datetime` | Calling hours and reminder times need correct local time. |

Model names change often. Check the provider's current model list if a call returns a "model not found" error.

---

## Project structure

```
.
├── config.py           # clinic details and the clock (NOW / TODAY)
├── db.py               # SQLite connection and table creation
├── seed.py             # fake doctors and slots for testing
├── tools.py            # get_available_slots, book_slot, cancel_appointment, get_my_appointments
├── state_machine.py    # call states, call memory, allowed tools, state changes
├── runner.py           # the single door between the LLM and the tools
├── tool_specs.py       # tool descriptions the model reads
├── llm.py              # chat() with Gemini, DeepSeek fallback
├── try_gemini.py       # scratch test: one Gemini call
├── try_deepseek.py     # scratch test: one DeepSeek call
├── try_tool_call.py    # scratch test: model asks for tools, runner executes them
├── check_setup.py      # checks that the keys are found
├── requirements.txt
└── .env.example
```

### Database tables

- `slots`: doctor, speciality, start time, status (`free` or `booked`)
- `appointments`: patient name, phone, slot, status (`booked` or `cancelled`), when it was created
- `outbox`: fake SMS messages (phone, text, time)

---

## Getting started

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/muralikrishna1729/Asha-Clinic-Voice-Agent.git
cd Asha-Clinic-Voice-Agent
python -m venv .venv

# Mac / Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\activate
```

### 2. Install the packages

```bash
pip install -r requirements.txt
```

### 3. Add your keys

Copy `.env.example` to `.env` and fill it in:

```
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_MODEL=deepseek-flash
```

Never commit `.env`. It is listed in `.gitignore`.

### 4. Check the setup

```bash
python check_setup.py
```

---

## Running the pieces

Each file can be run on its own, so you can see every layer working.

```bash
python db.py              # create the tables
python seed.py            # fill fake slots and print them
python tools.py           # test the four tools without any AI
python state_machine.py   # test the rules and state changes without any AI
python runner.py          # test the runner with two callers, blocked calls and the outbox
python llm.py             # test Gemini, the fallback, and the all-providers-fail case
python try_tool_call.py   # the model asks for tools and the runner executes them
```

The first tests need no API key. Only `llm.py`, `try_gemini.py`, `try_deepseek.py` and `try_tool_call.py` call an LLM.

---

## Roadmap

- [x] Project setup, private repo, keys kept out of Git
- [x] SQLite tables and fake demo data
- [x] Tools: search slots, book, cancel, list appointments
- [x] State machine and tool runner (rules enforced in code, tested without AI)
- [x] LLM wrapper with fallback between providers
- [x] First tool-calling loop with Gemini
- [ ] Full conversation loop with message history and state-based tool lists
- [ ] Extra tools so the model can report "slot chosen", "name given", "details confirmed"
- [ ] Fallback that also works with tool calls
- [ ] Automated tests with fake conversations and a fixed clock
- [ ] Voice: speech-to-text and text-to-speech, then latency work
- [ ] Reminder flow: scheduler script, calling-hours rule, outbound call
- [ ] Do-not-call list and handling for voicemail or wrong person

---

## Known limits

- The "SMS" is a row in a table, and the "call" is a text conversation in the terminal. Real telephony and SMS need a provider, and commercial SMS in India needs sender registration.
- SQLite allows one writer at a time. That is fine for a demo, not for a busy clinic.
- Free LLM tiers have rate limits, and free-tier content may be used by the provider, so only fake data belongs here.
- The model is not perfectly repeatable, so tests of its behavior should be run more than once.

---

## Disclaimer

This is a learning project, not a medical product. It must not be used with real patient data or to give medical advice.