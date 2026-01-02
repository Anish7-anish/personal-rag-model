import json
from datetime import datetime, timezone
from app.config import LOG_PATH


def log_query_event(payload: dict) -> None:
    payload = dict(payload)
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(payload) + "\n")
