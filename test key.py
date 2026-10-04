# test_key.py
from dotenv import load_dotenv
import os
from google import genai

load_dotenv()
key = os.environ.get("GEMINI_API_KEY")  # match whatever name your .env actually uses
print("Key loaded:", repr(key))

client = genai.Client(api_key=key)
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Say hello in one word."
)
print(response.text)