# app/utils/audit_logger.py
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

LOG_PATH = Path("data/audit_logs.jsonl")


def log_audit_event(event: Dict[str, Any]) -> None:
    """
    Appends one JSON record per audit request (JSONL format).
    If request_id is missing, it generates one.
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    request_id = event.get("request_id") or str(uuid.uuid4())

    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        **{k: v for k, v in event.items() if k != "request_id"},
    }

    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

