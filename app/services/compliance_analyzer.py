import json
import os
import re
from functools import lru_cache
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

# -----------------------------
# Config (safe defaults)
# -----------------------------
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
REQUEST_TIMEOUT = float(os.getenv("OPENAI_REQUEST_TIMEOUT", "45"))
MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "2"))

VECTOR_DIR = os.getenv("VECTOR_STORE_DIR", "data/vector_store")
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "all-MiniLM-L6-v2")

MAX_POLICY_CHARS = int(os.getenv("MAX_POLICY_CHARS", "6000"))
MAX_ARTICLE_CHARS = int(os.getenv("MAX_ARTICLE_CHARS", "12000"))  # packed context limit


def _sanitize_policy(policy_text: str) -> str:
    text = (policy_text or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    if len(text) > MAX_POLICY_CHARS:
        text = text[:MAX_POLICY_CHARS] + "..."
    return text


def _safe_json_from_text(text: str) -> dict:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    # Extract first JSON object if the model added extra text
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    return {"error": "Model did not return valid JSON", "raw_output": text}


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=OPENAI_MODEL,
        temperature=0,
        request_timeout=REQUEST_TIMEOUT,
        max_retries=MAX_RETRIES,
    )


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformerEmbeddings:
    return SentenceTransformerEmbeddings(model_name=EMBED_MODEL_NAME)


@lru_cache(maxsize=1)
def get_vector_store() -> Chroma:
    return Chroma(
        persist_directory=VECTOR_DIR,
        embedding_function=get_embedding_model(),
    )


def classify_risk_category(policy_text: str) -> str:
    policy_text = _sanitize_policy(policy_text)
    if not policy_text:
        return "Low / Minimal Risk"

    prompt = ChatPromptTemplate.from_template(
        """
You are an expert in the EU AI Act.

Classify the following policy into exactly ONE category:

- Prohibited AI Practice
- High-Risk AI System
- Transparency Obligation
- Low / Minimal Risk

Return ONLY the category name.

Policy:
{policy}
""".strip()
    )

    chain = prompt | get_llm()
    response = chain.invoke({"policy": policy_text})
    cat = (response.content or "").strip()

    allowed = {
        "Prohibited AI Practice",
        "High-Risk AI System",
        "Transparency Obligation",
        "Low / Minimal Risk",
    }
    return cat if cat in allowed else "Low / Minimal Risk"


def retrieve_relevant_articles(
    policy_text: str,
    category: str,
    k: int = 4,
    topic: Optional[str] = None,
):
    """
    Retrieval with strict-safe filtering for Chroma:
    - top-level must be ONE operator
    - use $and to combine filters
    """
    policy_text = _sanitize_policy(policy_text)
    vector_store = get_vector_store()

    scope_map = {
        "Prohibited AI Practice": {"risk_type": "Prohibited", "block": "RedLine"},
        "High-Risk AI System": {"risk_type": "High", "block": "HighRiskMandatory"},
        "Transparency Obligation": {"risk_type": "Transparency", "block": "Transparency"},
        "Low / Minimal Risk": {"risk_type": "General", "block": "General"},
    }
    scope = scope_map.get(category, {"risk_type": "General", "block": "General"})

    chroma_filter = {"$and": [{"risk_type": scope["risk_type"]}, {"block": scope["block"]}]}
    if topic:
        chroma_filter["$and"].append({"topic": topic})

    results = vector_store.similarity_search(policy_text, k=k, filter=chroma_filter)

    # Fallback 1: remove topic
    if not results and topic:
        chroma_filter = {"$and": [{"risk_type": scope["risk_type"]}, {"block": scope["block"]}]}
        results = vector_store.similarity_search(policy_text, k=k, filter=chroma_filter)

    # Fallback 2: only risk_type
    if not results:
        results = vector_store.similarity_search(policy_text, k=k, filter={"risk_type": scope["risk_type"]})

    # Fallback 3: no filter
    if not results:
        results = vector_store.similarity_search(policy_text, k=k)

    return results


def _pack_articles(retrieved_docs) -> str:
    chunks: List[str] = []
    total = 0
    for doc in retrieved_docs:
        art = f"Article {doc.metadata.get('article_number')} - {doc.metadata.get('title')}\n{doc.page_content}"
        if total + len(art) > MAX_ARTICLE_CHARS:
            break
        chunks.append(art)
        total += len(art)
    return "\n\n".join(chunks)


def llm_assessment(policy_text: str, retrieved_docs):
    policy_text = _sanitize_policy(policy_text)

    # IMPORTANT: double-curly braces so prompt template doesn't treat JSON keys as variables
    prompt = ChatPromptTemplate.from_template(
        """
You are a regulatory compliance auditor specializing in the EU AI Act.

Company Policy:
{policy}

Relevant EU AI Act Articles:
{articles}

Return ONLY valid JSON in this exact schema:

{{
  "status": "Compliant | At Risk | Non-Compliant",
  "violated_articles": ["Article number or empty list"],
  "reasoning": "Clear legal explanation referencing specific clauses",
  "confidence_score": 0-100
}}

Rules:
- Do not include markdown.
- Do not include explanations outside JSON.
""".strip()
    )

    article_text = _pack_articles(retrieved_docs)
    chain = prompt | get_llm()

    response = chain.invoke({"policy": policy_text, "articles": article_text})
    parsed = _safe_json_from_text(response.content)

    # Normalize
    if not isinstance(parsed, dict):
        parsed = {"error": "Invalid model output", "raw_output": str(response.content)}

    parsed.setdefault("status", "At Risk")
    parsed.setdefault("violated_articles", [])
    parsed.setdefault("reasoning", "")
    parsed.setdefault("confidence_score", 50)

    if parsed["violated_articles"] is None:
        parsed["violated_articles"] = []

    return parsed
