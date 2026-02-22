import json
import requests
import streamlit as st
from datetime import datetime

DEFAULT_API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="EU AI Act Compliance & Risk Auditor", layout="wide")

st.title("EU AI Act Compliance & Risk Auditor")
st.caption("Paste a company policy snippet and run an audit against the EU AI Act (RAG + deterministic risk scoring).")

with st.sidebar:
    st.subheader("API Settings")
    api_base = st.text_input("FastAPI base URL", value=DEFAULT_API_URL)
    st.caption("Make sure FastAPI is running: `uvicorn main:app --reload`")

API_AUDIT = f"{api_base.rstrip('/')}/audit"
API_REPORT_LATEST = f"{api_base.rstrip('/')}/report/latest"

policy_text = st.text_area("Company Policy Text", height=180)

col1, col2 = st.columns([1, 3])
with col1:
    run_btn = st.button("Run Audit", type="primary")
with col2:
    st.info("Tip: Use the Audit History page to view & filter past runs.")

def build_markdown_report(result: dict) -> str:
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    lines = []
    lines.append(f"# EU AI Act Compliance Report")
    lines.append(f"- **Generated (UTC):** {ts}")
    lines.append(f"- **Request ID:** {result.get('request_id', 'N/A')}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- **LLM Status:** {result.get('status', 'N/A')}")
    lines.append(f"- **Deterministic Status:** {result.get('deterministic_status', 'N/A')}")
    lines.append(f"- **Risk Score:** {result.get('risk_score', 'N/A')}")
    lines.append(f"- **Detected Category:** {result.get('detected_category', 'N/A')}")
    lines.append("")
    lines.append("## Violations")
    lines.append(f"- **LLM Violated Articles:** {', '.join(result.get('violated_articles', []) or []) or 'None'}")
    lines.append(
        f"- **Deterministic Violated Articles:** {', '.join(result.get('deterministic_violated_articles', []) or []) or 'None'}"
    )
    lines.append("")
    lines.append("## Reasoning")
    lines.append(result.get("reasoning", "").strip() or "N/A")
    lines.append("")
    lines.append("## Citations")
    cits = result.get("citations", []) or []
    if not cits:
        lines.append("None")
    else:
        for c in cits:
            lines.append(
                f"- Article {c.get('article_number')} — {c.get('title')} "
                f"(risk_type={c.get('risk_type')}, block={c.get('block')}, topic={c.get('topic')})"
            )
    return "\n".join(lines)

if run_btn:
    if not policy_text.strip():
        st.warning("Please paste a policy snippet first.")
        st.stop()

    try:
        resp = requests.post(API_AUDIT, json={"policy_text": policy_text}, timeout=90)
    except requests.RequestException as e:
        st.error(f"Could not reach FastAPI at {API_AUDIT}.")
        st.code(str(e))
        st.stop()

    if resp.status_code != 200:
        st.error(f"API Error ({resp.status_code})")
        st.code(resp.text)
        st.stop()

    result = resp.json()

    # --- Top summary cards ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("LLM Status", result.get("status", "N/A"))
    c2.metric("Deterministic Status", result.get("deterministic_status", "N/A"))
    c3.metric("Risk Score", result.get("risk_score", "N/A"))
    c4.metric("Detected Category", result.get("detected_category", "N/A"))

    st.divider()

    left, right = st.columns(2)
    with left:
        st.subheader("Violated Articles")
        st.write("LLM:")
        st.write(result.get("violated_articles") or "None")
        st.write("Deterministic:")
        st.write(result.get("deterministic_violated_articles") or "None")

    with right:
        st.subheader("Request ID")
        st.code(result.get("request_id", "N/A"))

    st.divider()

    st.subheader("Reasoning")
    st.write(result.get("reasoning", ""))

    st.divider()

    st.subheader("Citations (EU AI Act Articles)")
    citations = result.get("citations", []) or []
    if not citations:
        st.info("No citations returned.")
    else:
        # Dedup display just in case
        seen = set()
        clean = []
        for c in citations:
            key = (c.get("article_number"), c.get("title"))
            if key in seen:
                continue
            seen.add(key)
            clean.append(c)
        st.dataframe(clean, use_container_width=True)

    st.divider()

    # ---- Export (high value) ----
    st.subheader("Export Compliance Report")

    report_md = build_markdown_report(result)
    report_json = json.dumps(result, indent=2)

    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            label="Download JSON Report",
            data=report_json,
            file_name=f"eu_ai_act_report_{result.get('request_id','unknown')}.json",
            mime="application/json",
        )
    with col_b:
        st.download_button(
            label="Download Markdown Report",
            data=report_md,
            file_name=f"eu_ai_act_report_{result.get('request_id','unknown')}.md",
            mime="text/markdown",
        )

    with st.expander("Show raw JSON response"):
        st.code(report_json)
