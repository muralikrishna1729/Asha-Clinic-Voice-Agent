SPECIALITIES = ["General Medicine", "Dermatology", "Orthopedics"]

TOOL_SPECS = [
    {
        "name": "get_available_slots",
        "description": "Get the earliest free appointment slots. Use it when the caller wants to book. "
                       "Never guess slots, always use this tool.",
        "parameters": {
            "type": "object",
            "properties": {
                "speciality": {
                    "type": "string",
                    "enum": SPECIALITIES,
                    "description": "Type of doctor needed. Leave out if the caller is not sure.",
                },
                "date": {
                    "type": "string",
                    "description": "Only slots on this day, format YYYY-MM-DD. Leave out if not asked.",
                },
            },
        },
    },
    {
        "name": "book_slot",
        "description": "Book one of the slots that was offered to the caller.",
        "parameters": {
            "type": "object",
            "properties": {
                "slot_id": {"type": "integer", "description": "The id of the chosen slot."},
            },
            "required": ["slot_id"],
        },
    },
    {
        "name": "get_my_appointments",
        "description": "List the caller's upcoming appointments.",
    },
    {
        "name": "cancel_appointment",
        "description": "Cancel one of the caller's appointments.",
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {"type": "integer", "description": "The id of the appointment."},
            },
            "required": ["appointment_id"],
        },
    },
]