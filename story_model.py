# story_model.py
# Pure logic module: fetches Wikipedia content and generates a narrative
# story via Gemini. No Flask code lives here anymore - app.py imports
# TOPICS and get_story() from this file.

import os
import json
import logging
import re
import time
import requests
from google import genai
from google.genai import errors as genai_errors
from google.genai.types import GenerateContentConfig, ThinkingConfig, ThinkingLevel

logging.getLogger("google_genai.models").setLevel(logging.ERROR)

from dotenv import load_dotenv
load_dotenv()

from templates.fact_check import fact_check_topic

# ---------- CONFIG ----------
# Set this in your terminal before running, instead of hardcoding it:
#   PowerShell:  $env:GEMINI_API_KEY = "your-key-here"
#   Then just:   python app.py
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError(
    )
client = genai.Client(api_key=API_KEY)

MODEL_FALLBACK_CHAIN = ["gemini-3.5-flash-lite"]
MAX_RETRIES_PER_MODEL = 1
RETRY_DELAY_SECONDS = 3

WIKI_API_URL = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "AIStorytellingSIHProject/1.0 (student project)"}
CACHE_FILE = "history_cache.json"  # not wired up yet - see note below

TOPICS = {
    # Medieval India
    "Mughal Empire": "https://en.wikipedia.org/wiki/Mughal_Empire",
    "Delhi Sultanate": "https://en.wikipedia.org/wiki/Delhi_Sultanate",
    "Vijayanagara Empire": "https://en.wikipedia.org/wiki/Vijayanagara_Empire",
    "Chola Empire": "https://en.wikipedia.org/wiki/Chola_dynasty",
    "Maratha Empire": "https://en.wikipedia.org/wiki/Maratha_Empire",
    "Rajput Kingdoms": "https://en.wikipedia.org/wiki/Rajput",
    "Sikh Empire": "https://en.wikipedia.org/wiki/Sikh_Empire",
    # Modern India
    "British East India Company & Expansion": "https://en.wikipedia.org/wiki/Company_rule_in_India",
    "Revolt of 1857": "https://en.wikipedia.org/wiki/Indian_Rebellion_of_1857",
    "Indian National Congress & Early Nationalism": "https://en.wikipedia.org/wiki/Indian_National_Congress",
    "Swadeshi Movement": "https://en.wikipedia.org/wiki/Swadeshi_movement",
    "Gandhian Era & Non-Cooperation Movement": "https://en.wikipedia.org/wiki/Non-cooperation_movement",
    "Civil Disobedience & Quit India Movement": "https://en.wikipedia.org/wiki/Quit_India_Movement",
    "Indian Independence & Partition": "https://en.wikipedia.org/wiki/Partition_of_India",
    # Ancient India
    "Indus Valley Civilization": "https://en.wikipedia.org/wiki/Indus_Valley_Civilization",
    "Vedic Period": "https://en.wikipedia.org/wiki/Vedic_period",
    "Mahajanapadas & Rise of Magadha": "https://en.wikipedia.org/wiki/Magadha",
    "Maurya Empire": "https://en.wikipedia.org/wiki/Maurya_Empire",
    "Gupta Empire": "https://en.wikipedia.org/wiki/Gupta_Empire",
    "Buddhism & Jainism": "https://en.wikipedia.org/wiki/Buddhism_and_Jainism",
    "Sangam Age & Ancient South India": "https://en.wikipedia.org/wiki/Sangam_literature",
}


def fetch_history_content(topic: str) -> str:
    wiki_title = topic
    for display_name, page_title in TOPICS.items():
        if display_name.strip().lower() == topic.strip().lower():
            wiki_title = page_title
            break

    if wiki_title.startswith("http"):
        wiki_title = wiki_title.split("/")[-1]

    print(f"[DEBUG] wiki_title = '{wiki_title}'")

    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "explaintext": True,
        "redirects": 1,
        "titles": wiki_title,
    }

    response = requests.get(WIKI_API_URL, params=params, headers=HEADERS, timeout=10)
    response.raise_for_status()
    data = response.json()

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        raise ValueError(f"No Wikipedia page found for '{topic}'")

    page = next(iter(pages.values()))
    if "-1" in pages or "missing" in page:
        raise ValueError(f"No Wikipedia page found for '{topic}'")
    extract = page.get("extract", "")
    if not extract:
        raise ValueError(f"Wikipedia page for '{topic}' had no readable content")

    return extract[:8000]


def _build_config_for_model(model_name: str) -> GenerateContentConfig:
    if model_name.startswith("gemini-3"):
        return GenerateContentConfig(
            max_output_tokens=3500,
            thinking_config=ThinkingConfig(thinking_level=ThinkingLevel.LOW),
        )
    else:
        return GenerateContentConfig(
            max_output_tokens=3500,
            temperature=0.9,
        )


def _stream_story_from_model(model_name: str, prompt: str) -> str:
    full_story = ""
    last_chunk = None
    stream = client.models.generate_content_stream(
        model=model_name,
        contents=prompt,
        config=_build_config_for_model(model_name),
    )

    for chunk in stream:
        last_chunk = chunk
        if chunk.candidates:
            content = chunk.candidates[0].content
            parts = (content.parts if content else None) or []
            for part in parts:
                if getattr(part, "thought", False):
                    continue
                if part.text:
                    print(part.text, end="", flush=True)
                    full_story += part.text

    if last_chunk and last_chunk.candidates:
        finish_reason = last_chunk.candidates[0].finish_reason
        if finish_reason == "MAX_TOKENS":
            print(f"\n\n[WARNING: story was cut off (hit max_output_tokens) - raise the limit in _build_config_for_model()]\n")

    return full_story


def generate_story(topic: str, history_text: str) -> str:
    prompt = f"""
You are a skilled storyteller who explains Indian history to students
in an engaging, narrative way (like a story, not a textbook).

Topic: {topic}

Here is factual historical content to base the story on:
\"\"\"{history_text}\"\"\"

Instructions:
- Write it as a flowing narrative story, not bullet points.
- Cover the major dynasties/rulers and the overall timeline mentioned
  in the content - do not focus on just one king if the topic spans several.
- Keep historical facts accurate - do not invent events.
- Make it engaging and easy for a student to follow.
- Length: around 700-1000 words, since this topic spans multiple
  rulers and a long timeline.
- Tell the complete story with a proper ending - do not cut it off
  or leave it open-ended. This story is separate from the quiz feature,
  so do not reference any choices or "what would you have done" questions.
- Do NOT start the story with "Imagine..." or any similar phrase
  (e.g. "Picture this", "Close your eyes and imagine", "Envision").
  Open instead with a concrete scene, a date, a fact, or a character's
  action - vary the opening line across different stories.
"""

    last_error = None
    for model_name in MODEL_FALLBACK_CHAIN:
        for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
            try:
                print(f"[Using {model_name}, attempt {attempt}]\n")
                return _stream_story_from_model(model_name, prompt)
            except genai_errors.ServerError as e:
                last_error = e
                print(f"\n[{model_name} unavailable, retrying in {RETRY_DELAY_SECONDS}s...]\n")
                time.sleep(RETRY_DELAY_SECONDS)
            except genai_errors.ClientError as e:
                last_error = e
                print(f"\n[{model_name} rejected the request, trying next model...]\n")
                break

    raise RuntimeError(
        f"All models failed. Last error: {last_error}. "
        f"Check your API key, quota, or internet connection."
    )

def get_story(topic: str, retry_on_fail: bool = True) -> str:
    try:
        history_text = fetch_history_content(topic)
        story = generate_story(topic, history_text)

        result = fact_check_topic(topic, story, history_text)

        if result["verdict"] == "needs_review" and retry_on_fail:
            print(f"\n[FACT-CHECK] {len(result['issues'])} issue(s) found — regenerating once...\n")
            issues_summary = "; ".join(i["claim"] for i in result["issues"])
            stricter_note = (
                f"\n\nIMPORTANT: A previous draft of this story included these "
                f"unsupported or incorrect claims - do NOT repeat them: {issues_summary}"
            )
            story = generate_story(topic, history_text + stricter_note)
            result = fact_check_topic(topic, story, history_text)

            if result["verdict"] == "needs_review":
                print("[FACT-CHECK] Retry still failed - falling back to cached story.")
                story = load_cached_fallback(topic)

        return story

    except (RuntimeError, requests.RequestException) as e:
        print(f"\n[GEMINI/WIKI FAILURE] {e}")
        print("[FALLBACK] Serving cached story instead.\n")
        return load_cached_fallback(topic)

def load_cached_fallback(topic: str) -> str:
    from templates.generate_fallbacks import safe_filename, FALLBACK_DIR
    filepath = os.path.join(FALLBACK_DIR, safe_filename(topic))

    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"No fallback story saved for '{topic}'. "
            f"Run generate_fallbacks.py first."
        )

    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    # Quick manual test: python story_model.py
    try:
        topic = input("\nEnter a historical topic from the list above: ")
        story = get_story(topic)
        print("\n--- Story Generated ---\n")
    except (ValueError, RuntimeError, requests.RequestException) as e:
        print(f"Error: {e}")
