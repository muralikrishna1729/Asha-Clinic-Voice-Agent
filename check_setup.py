import os

from dotenv import load_dotenv

load_dotenv()

keys = (os.getenv("GEMINI_API_KEY"), os.getenv("DEEPSEEK_API_KEY"))
placeholders = {"", "paste_your_key_here", "your_key_here"}
print("Keys found:", all(key is not None and key.strip() not in placeholders for key in keys))
