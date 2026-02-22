import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.risk_scoring import compute_risk_score
from app.services.compliance_analyzer import (
    retrieve_relevant_articles,
    llm_assessment,
    classify_risk_category,
)
from app.utils.audit_logger import log_audit_event

router = APIRouter()
LOG_PATH = Path("data/audit_logs.jsonl")


class PolicyRequest(BaseModel):
    policy_text: str = Field(..., min_length=3, description="Company policy snippet to audit")


def _dedupe_citations(retrieved_docs):
    citations = []
    seen = set()
    for d in retrieved_docs:
        md = d.metadata or {}
        key = (md.get("article_number"), md.get("title"))
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            {
                "article_number": md.get("article_number"),
                "title": md.get("title"),
                "risk_type": md.get("risk_type"),
                "block": md.get("block"),
                "topic": md.get("topic"),
            }
        )
    return citations


@router.post("/audit")
def audit_policy(request: PolicyRequest):
    request_id = str(uuid4())

    try:
        category = classify_risk_category(request.policy_text)
        retrieved = retrieve_relevant_articles(request.policy_text, category)

        result = llm_assessment(request.policy_text, retrieved)

        # deterministic scoring
        score_pack = compute_risk_score(category, retrieved)
        result["risk_score"] = score_pack.get("risk_score", 0)
        result["deterministic_status"] = score_pack.get("deterministic_status", "At Risk")
        result["deterministic_violated_articles"] = score_pack.get("deterministic_violated_articles", [])

        citations = _dedupe_citations(retrieved)

        # attach response fields
        result["request_id"] = request_id
        result["detected_category"] = category
        result["citations"] = citations

        # log one flat record
        log_audit_event(
            {
                "request_id": request_id,
                "policy_text": request.policy_text,
                "detected_category": category,
                "status": result.get("status"),
                "violated_articles": result.get("violated_articles", []),
                "confidence_score": result.get("confidence_score"),
                "deterministic_status": result.get("deterministic_status"),
                "risk_score": result.get("risk_score"),
                "deterministic_violated_articles": result.get("deterministic_violated_articles", []),
                "citations": citations,
            }
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        # hardening: return clean error, no traceback to client
        raise HTTPException(status_code=500, detail=f"Audit failed: {type(e).__name__}: {e}")


def _read_log_lines():
    if not LOG_PATH.exists():
        return []
    rows = []
    with LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


@router.get("/report/{request_id}")
def get_report(request_id: str):
    rows = _read_log_lines()
    for r in reversed(rows):
        if str(r.get("request_id")) == str(request_id):
            return r
    raise HTTPException(status_code=404, detail="request_id not found in audit logs")


@router.get("/report/latest")
def get_latest_report():
    rows = _read_log_lines()
    if not rows:
        raise HTTPException(status_code=404, detail="No audit logs found yet")
    return rows[-1]