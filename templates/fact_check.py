# fact_check.py
import os
import json
from google import genai
from google.genai.types import GenerateContentConfig

API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

FACT_CHECK_PROMPT = """You are a strict historical fact-checker.

SOURCE MATERIAL (ground truth, from Wikipedia):
---
{source}
---

GENERATED STORY (to be checked):
---
{story}
---

Compare the story against the source material. List every claim in the story that:
1. Is NOT supported by the source (unverifiable/invented), or
2. CONTRADICTS the source (factually wrong)

Respond ONLY in this JSON format, no markdown fences, no extra text:
{{
  "issues": [
    {{"claim": "the exact sentence/claim from the story", "problem": "unsupported" or "contradiction", "explanation": "short reason"}}
  ],
  "verdict": "pass" or "needs_review"
}}

If there are no issues, return an empty issues list and verdict "pass".
"""


def fact_check_topic(topic: str, story_text: str, source_text: str) -> dict:
    prompt = FACT_CHECK_PROMPT.format(source=source_text, story=story_text)

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=GenerateContentConfig(temperature=0),
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw.split("json", 1)[-1]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"issues": [], "verdict": "error", "raw_response": raw}