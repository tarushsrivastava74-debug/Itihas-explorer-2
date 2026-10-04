# generate_fallbacks.py
# One-time script: generates and saves a story for every topic in TOPICS,
# so you have a pre-verified fallback ready if Gemini is slow/down during
# the demo, or if a live story keeps failing fact-checks.

import os
import re
import time
from templates.story_model import TOPICS, fetch_history_content, generate_story

FALLBACK_DIR = "fallback_stories"


def safe_filename(topic: str) -> str:
    # turns "Buddhism & Jainism" into "Buddhism_Jainism" etc.
    name = re.sub(r"[^\w\s-]", "", topic)
    name = re.sub(r"\s+", "_", name.strip())
    return name + ".txt"


def generate_all_fallbacks():
    os.makedirs(FALLBACK_DIR, exist_ok=True)

    for topic in TOPICS:
        filepath = os.path.join(FALLBACK_DIR, safe_filename(topic))

        if os.path.exists(filepath):
            print(f"[SKIP] Already have a fallback for '{topic}'")
            continue

        print(f"[GENERATING] {topic} ...")
        try:
            history_text = fetch_history_content(topic)
            story = generate_story(topic, history_text)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(story)

            print(f"[SAVED] {filepath}\n")
            time.sleep(2)  # small pause between calls, be nice to the API

        except Exception as e:
            print(f"[FAILED] {topic}: {e}\n")


if __name__ == "__main__":
    generate_all_fallbacks()