import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_FILE = DATA_DIR / "approved_insights.jsonl"


def save_approved_insight(context_key: str, data_summary_str: str, insight: str):
    """
    Appends an approved insight to the local JSONL cache file.
    """
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        record = {
            "context_key": context_key,
            "data_summary_str": data_summary_str,
            "insight": insight.strip(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        with open(CACHE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        import sys

        print(
            f"[insights_logger] Failed to save approved insight: {e}", file=sys.stderr
        )


def get_relevant_insights(context_key: str, limit: int = 2) -> list[dict]:
    """
    Reads the local JSONL cache and returns the most recent approved insights
    matching the given context_key.
    """
    if not CACHE_FILE.exists():
        return []

    results = []
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if record.get("context_key") == context_key:
                        results.append(record)
                except json.JSONDecodeError:
                    continue
        # Sort by timestamp desc and take the latest 'limit' records
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results[:limit]
    except Exception as e:
        import sys

        print(
            f"[insights_logger] Failed to load approved insights: {e}", file=sys.stderr
        )
        return []
