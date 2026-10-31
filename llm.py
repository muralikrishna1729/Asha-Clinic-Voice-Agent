import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import OpenAI

load_dotenv()


class LLMError(Exception):
    """Raised when every provider has failed."""


def _call_gemini(messages, timeout):
    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY"),
        http_options=types.HttpOptions(timeout=int(timeout * 1000)),  # Gemini wants milliseconds
    )
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    contents = [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part.from_text(text=m["content"])],
        )
        for m in messages
        if m["role"] != "system"
    ]
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL"),
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system or None),
    )
    return response.text


def _call_deepseek(messages, timeout):
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
        timeout=timeout,
        max_retries=0,          # no hidden retries, we want to fall back quickly
    )
    response = client.chat.completions.create(
        model=os.getenv("DEEPSEEK_MODEL"),
        messages=messages,
    )
    return response.choices[0].message.content


PROVIDERS = [("gemini", _call_gemini), ("deepseek", _call_deepseek)]   # order = priority


def chat(messages, timeout=10):
    """messages: [{'role': 'system'|'user'|'assistant', 'content': '...'}, ...]
    Returns {'text', 'provider', 'seconds'}. Raises LLMError if all providers fail."""
    errors = []
    for name, call in PROVIDERS:
        start = time.perf_counter()
        try:
            text = call(messages, timeout)
            if not text or not text.strip():
                raise ValueError("empty reply")
            return {
                "text": text.strip(),
                "provider": name,
                "seconds": round(time.perf_counter() - start, 2),
            }
        except Exception as e:
            print(f"[llm] {name} failed after {time.perf_counter() - start:.2f}s: {e!r}")
            errors.append(f"{name}: {e!r}")
    raise LLMError("all providers failed: " + " | ".join(errors))


if __name__ == "__main__":
    msgs = [
        {"role": "system", "content": "You are Asha, a clinic receptionist. Reply in one short sentence."},
        {"role": "user", "content": "Hi, I need a doctor appointment."},
    ]

    print("1. Normal call")
    print("  ", chat(msgs))

    print("2. Gemini key broken on purpose")
    good_key = os.environ["GEMINI_API_KEY"]
    os.environ["GEMINI_API_KEY"] = "wrong-key"
    try:
        print("  ", chat(msgs))
    except LLMError:
        print("   (expected for now: the backup has no balance either)")
    os.environ["GEMINI_API_KEY"] = good_key

    print("3. Impossible timeout, so both providers fail")
    try:
        chat(msgs, timeout=0.05)
    except LLMError as e:
        print("   LLMError:", e)