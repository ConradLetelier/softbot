import json
import os

TRACKER_FILE = "data/processed_news.json"

def is_news_processed(url):
    """Checks if a news URL has already been handled."""
    if not os.path.exists(TRACKER_FILE):
        return False
    try:
        with open(TRACKER_FILE, 'r') as f:
            processed = json.load(f)
            return url in processed
    except Exception:
        return False

def mark_news_as_processed(url):
    """Adds a news URL to the processed list."""
    processed = []
    os.makedirs(os.path.dirname(TRACKER_FILE), exist_ok=True)
    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE, 'r') as f:
                processed = json.load(f)
        except Exception:
            processed = []
    
    if url not in processed:
        processed.append(url)
        # Keep only the last 500 items to prevent the file from growing too large
        processed = processed[-500:]
        with open(TRACKER_FILE, 'w') as f:
            json.dump(processed, f)
