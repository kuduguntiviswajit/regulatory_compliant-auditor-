# app/core/taxonomy.py
from typing import Dict, Tuple, List


def block_for_article(num: int) -> str:
    if 1 <= num <= 4:
        return "Foundation"
    if num == 5:
        return "RedLine"
    if 6 <= num <= 15:
        return "HighRiskMandatory"
    if num == 50:
        return "Transparency"
    if 51 <= num <= 55:
        return "GPAI"
    if 99 <= num <= 101:
        return "Enforcement"
    return "General"


def fine_tier_and_points(num: int) -> Tuple[str, int]:
    if num == 5:
        return ("Tier1", 50)            # prohibited
    if num in [9, 10, 13, 14, 15]:
        return ("Tier2", 20)            # key high-risk obligations
    if 99 <= num <= 101:
        return ("Tier3", 10)            # enforcement / authority-related
    return ("None", 0)


# Hard overrides (most reliable)
TOPIC_OVERRIDES: Dict[str, str] = {
    "5": "prohibited",
    "9": "risk_management",
    "10": "data_governance",
    "13": "transparency",
    "14": "human_oversight",
    "15": "accuracy_robustness_security",
    "50": "transparency",
    "51": "gpaI_models",
    "52": "gpaI_models",
    "53": "gpaI_models",
    "54": "gpaI_models",
    "55": "gpaI_models",
}

# Keyword topics (IMPORTANT: no generic "prohibited" keyword topic)
TOPIC_KEYWORDS: List[Tuple[str, List[str]]] = [
    # Useful topic for queries like facial recognition / emotion recognition
    ("biometrics", ["biometric", "facial recognition", "emotion recognition"]),

    ("transparency", ["transparency", "inform", "disclose", "information to natural persons"]),
    ("risk_management", ["risk management", "risk mitigation"]),
    ("data_governance", ["data governance", "data quality", "training data", "datasets"]),
    ("technical_documentation", ["technical documentation", "documentation"]),
    ("logging", ["logging", "logs", "record-keeping", "records"]),
    ("human_oversight", ["human oversight", "oversight", "supervision"]),
    ("accuracy_robustness_security", ["accuracy", "robustness", "security", "cybersecurity"]),
    ("post_market_monitoring", ["post-market monitoring", "monitoring system"]),
    ("incident_reporting", ["incident", "serious incident", "reporting"]),
    ("gpaI_models", ["general-purpose ai", "gpai", "model", "foundation model"]),
]


def topic_for_article(article_number: str, title: str, content: str) -> str:
    # 1) Overrides first (most accurate)
    if article_number in TOPIC_OVERRIDES:
        return TOPIC_OVERRIDES[article_number]

    # 2) Keyword scan (safe topics only)
    text = f"{title}\n{content}".lower()

    for topic, keywords in TOPIC_KEYWORDS:
        if any(k.lower() in text for k in keywords):
            return topic

    return "general"


def snippet_checkable(block: str) -> bool:
    # Articles that can be checked directly against a policy snippet
    return block in {"Foundation", "RedLine", "HighRiskMandatory", "Transparency", "GPAI"}
