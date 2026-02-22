from typing import Dict, Any

BASE_SCORE = {
    "Prohibited AI Practice": 100,
    "High-Risk AI System": 50,
    "Transparency Obligation": 30,
    "Low / Minimal Risk": 0,
}

def compute_risk_score(category: str, retrieved_docs) -> Dict[str, Any]:
    base = BASE_SCORE.get(category, 20)

    seen_articles = set()
    penalty_points = 0
    violated_articles = []

    for d in retrieved_docs:
        md = d.metadata or {}
        art = md.get("article_number")
        if not art or art in seen_articles:
            continue

        seen_articles.add(art)

        points = int(md.get("severity_points", 0))
        if points > 0:
            penalty_points += points
            violated_articles.append(f"Article {art}")

    score = min(100, base + penalty_points)

    if score <= 30:
        status = "Compliant"
    elif score <= 60:
        status = "At Risk"
    else:
        status = "Non-Compliant"

    return {
        "risk_score": score,
        "deterministic_status": status,
        "deterministic_violated_articles": violated_articles
    }
    
    