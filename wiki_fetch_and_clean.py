import re
import os
import requests
from urllib.parse import urlparse, unquote

WIKI_API_URL = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "AIStorytellingSIHProject/1.0 (student project)"}
OUTPUT_DIR = "cleaned_topics"


def extract_page_title_from_url(url: str) -> str:
    """
    Pulls the page title out of a Wikipedia URL.
    e.g. https://en.wikipedia.org/wiki/Mughal_Empire -> "Mughal Empire"
    """
    path = urlparse(url).path          # /wiki/Mughal_Empire
    title = path.split("/wiki/")[-1]   # Mughal_Empire
    title = unquote(title)             # handles %20 etc. if present
    title = title.replace("_", " ")
    return title


def fetch_raw_wikipedia(page_title: str) -> str:
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "explaintext": True,
        "redirects": 1,
        "titles": page_title,
    }
    response = requests.get(WIKI_API_URL, params=params, headers=HEADERS, timeout=10)
    response.raise_for_status()
    data = response.json()
    page = next(iter(data["query"]["pages"].values()))

    if "missing" in page:
        raise ValueError(f"No Wikipedia page found for '{page_title}'. Check the URL/title.")

    return page.get("extract", "")


def clean_wikipedia_text(raw_text: str) -> str:
    stop_sections = ["See also", "References", "External links", "Further reading", "Notes", "Bibliography"]
    for section in stop_sections:
        pattern = rf"\n\s*=*\s*{re.escape(section)}\s*=*\s*\n"
        match = re.search(pattern, raw_text, flags=re.IGNORECASE)
        if match:
            raw_text = raw_text[:match.start()]

    raw_text = re.sub(r"\[\d+\]", "", raw_text)
    raw_text = re.sub(r"\[note \d+\]", "", raw_text, flags=re.IGNORECASE)
    raw_text = re.sub(r"={2,}\s*.*?\s*={2,}", "", raw_text)
    raw_text = re.sub(r"\n{3,}", "\n\n", raw_text)
    raw_text = re.sub(r"[ \t]{2,}", " ", raw_text)

    return raw_text.strip()


def save_cleaned_text(page_title: str, cleaned_text: str, topic_folder: str) -> str:
    folder_path = os.path.join(OUTPUT_DIR, topic_folder)
    os.makedirs(folder_path, exist_ok=True)
    safe_name = page_title.replace(" ", "_").replace("&", "and").replace("/", "-")
    out_path = os.path.join(folder_path, f"{safe_name}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(cleaned_text)
    return out_path


def process_wikipedia_url(url: str, topic_folder: str):
    page_title = extract_page_title_from_url(url)
    print(f"Fetching: {page_title} ...")

    raw = fetch_raw_wikipedia(page_title)
    cleaned = clean_wikipedia_text(raw)
    out_path = save_cleaned_text(page_title, cleaned, topic_folder)

    print(f"Saved -> {out_path}")
    print(f"Raw length: {len(raw)} chars | Cleaned length: {len(cleaned)} chars")


def sanitize_folder_name(name: str) -> str:
    return name.strip().replace(" ", "_").replace("&", "and").replace("/", "-")


if __name__ == "__main__":
    print("=== Wikipedia Topic Fetcher & Cleaner ===\n")

    while True:
        topic_input = input("Main topic name (e.g. Delhi Sultanate): ").strip()
        if topic_input:
            break
        print("Please enter a topic name.")

    topic_folder = sanitize_folder_name(topic_input)
    print(f"\nAll pages you fetch now will be saved under: {OUTPUT_DIR}/{topic_folder}/\n")
    print("Paste Wikipedia URLs for this topic one at a time.")
    print("Type 'done' when finished with this topic (you can restart the script for the next topic).\n")

    while True:
        url = input("URL: ").strip()
        if url.lower() == "done":
            break
        if "wikipedia.org/wiki/" not in url:
            print("That doesn't look like a valid Wikipedia article URL. Try again.\n")
            continue

        try:
            process_wikipedia_url(url, topic_folder)
        except Exception as e:
            print(f"Error: {e}")

        print()  # blank line before next prompt

    print(f"\nAll done for '{topic_input}'. Files saved in {OUTPUT_DIR}/{topic_folder}/")