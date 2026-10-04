# quiz.py

import json
import os

QUIZ_DIR = os.path.join(os.path.dirname(__file__), "quiz_data")

QUIZ_DATA = {}   # topic -> {"round1": {...}, "round2_A": {...}, ...}
ENDINGS = {}     # topic -> {"ending_1": {...}, ...}


def _load_all_topics():
    """Load every *.json file in quiz_data/ into QUIZ_DATA and ENDINGS."""
    if not os.path.isdir(QUIZ_DIR):
        return
    for filename in os.listdir(QUIZ_DIR):
        if not filename.endswith(".json"):
            continue
        topic_slug = filename[:-5]  # strip ".json"
        filepath = os.path.join(QUIZ_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        # each topic file has "rounds" and "endings" top-level keys
        QUIZ_DATA[topic_slug] = data.get("rounds", {})
        ENDINGS[topic_slug] = data.get("endings", {})


_load_all_topics()


def get_quiz_node(topic: str, path: str):
    """
    path examples: 'round1', 'round2_A', 'round4_B4', 'ending_1', etc.
    Returns the question node or ending node for that path, or None if not found.
    """
    if path.startswith("ending_"):
        return ENDINGS.get(topic, {}).get(path)

    topic_data = QUIZ_DATA.get(topic)
    if not topic_data:
        return None

    return topic_data.get(path)
