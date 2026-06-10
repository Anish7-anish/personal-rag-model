import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import (
    APP_LOG_PATH,
    LOG_LEVEL,
    LOG_PATH,
    MONGO_COLLECTION,
    MONGO_DB,
    MONGO_URI,
    TRACE_LOG_PATH,
    TRACE_PREVIEW_CHARS,
)


LOGGER_NAME = "personal_rag"


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def preview_text(text: str | None, limit: int | None = None) -> str:
    if not text:
        return ""
    preview_limit = limit or TRACE_PREVIEW_CHARS
    compact = " ".join(text.split())
    if len(compact) <= preview_limit:
        return compact
    return compact[: preview_limit - 3] + "..."


def get_app_logger(name: str = LOGGER_NAME) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(APP_LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def _json_default(value: Any) -> str:
    return str(value)


def _append_jsonl(path: str, payload: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=_json_default) + "\n")


def log_trace_event(event_type: str, payload: dict, trace_id: str | None = None) -> dict:
    event = {
        "timestamp": utcnow_iso(),
        "event_type": event_type,
        "trace_id": trace_id,
        **payload,
    }
    _append_jsonl(TRACE_LOG_PATH, event)
    logger = get_app_logger()
    logger.info(
        "trace event=%s trace_id=%s payload=%s",
        event_type,
        trace_id or "-",
        preview_text(json.dumps(payload, default=_json_default), 400),
    )
    return event


def log_query_event(payload: dict) -> None:
    payload = dict(payload)
    payload["timestamp"] = utcnow_iso()
    if MONGO_URI:
        try:
            from pymongo import MongoClient
        except Exception:
            _append_jsonl(LOG_PATH, payload)
            return

        try:
            client = MongoClient(MONGO_URI)
            db = client[MONGO_DB]
            db[MONGO_COLLECTION].insert_one(payload)
            client.close()
            return
        except Exception:
            _append_jsonl(LOG_PATH, payload)
            return

    _append_jsonl(LOG_PATH, payload)


def read_recent_jsonl(path: str, limit: int = 20) -> list[dict]:
    file_path = Path(path)
    if not file_path.exists():
        return []

    lines = file_path.read_text(encoding="utf-8").splitlines()
    output = []
    for line in lines[-limit:]:
        if not line.strip():
            continue
        try:
            output.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return output
