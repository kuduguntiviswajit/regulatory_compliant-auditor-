import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

LOG_PATH = Path("data/audit_logs.jsonl")


def log_audit_event(event: Dict[str, Any]) -> None:
    """
    Appends one JSON record per audit request (JSONL format).
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **event,
    }

    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
