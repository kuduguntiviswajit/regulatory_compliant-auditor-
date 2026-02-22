import json
from pathlib import Path

import pandas as pd
import streamlit as st

LOG_PATH = Path("data/audit_logs.jsonl")

st.set_page_config(page_title="Audit History", layout="wide")
st.title("Audit History")
st.caption("Past audit runs from data/audit_logs.jsonl (traceability log).")

# ---- Guard: log exists ----
if not LOG_PATH.exists():
    st.warning("No audit log found yet. Run an audit first from the main page.")
    st.stop()

# ---- Download button (jsonl) ----
try:
    st.download_button(
        label="Download audit_logs.jsonl",
        data=LOG_PATH.read_bytes(),
        file_name="audit_logs.jsonl",
        mime="application/jsonl",
    )
except Exception:
    # if file locked/permission issues, don't block UI
    st.info("Download not available right now (file access issue).")

# ---- Load JSONL safely ----
rows = []
with LOG_PATH.open("r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue

if not rows:
    st.info("Audit log is empty. Run an audit first.")
    st.stop()

# ---- Helpers ----
def safe_get(d, key, default=None):
    return d.get(key, default) if isinstance(d, dict) else default

def normalize_request_id(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() == "none":
        return None
    return s

# ---- Normalize for table ----
table_rows = []
for r in rows:
    table_rows.append(
        {
            "timestamp_utc": safe_get(r, "timestamp_utc"),
            "request_id": normalize_request_id(safe_get(r, "request_id")),
            "detected_category": safe_get(r, "detected_category"),
            "status": safe_get(r, "status"),
            "deterministic_status": safe_get(r, "deterministic_status"),
            "risk_score": safe_get(r, "risk_score"),
            "violated_articles": ", ".join(safe_get(r, "violated_articles", []) or []),
            "deterministic_violated_articles": ", ".join(
                safe_get(r, "deterministic_violated_articles", []) or []
            ),
            "policy_text": safe_get(r, "policy_text", ""),
            "confidence_score": safe_get(r, "confidence_score"),
            "citations_count": len(safe_get(r, "citations", []) or []),
        }
    )

df = pd.DataFrame(table_rows)

# ---- Quick stats ----
st.subheader("Quick Stats")
c1, c2, c3, c4 = st.columns(4)

total_runs = len(df)
non_compliant = int((df["status"] == "Non-Compliant").sum()) if "status" in df else 0
avg_risk = (
    round(pd.to_numeric(df["risk_score"], errors="coerce").dropna().mean(), 1)
    if "risk_score" in df
    else 0
)
unique_policies = int(df["policy_text"].nunique()) if "policy_text" in df else 0

c1.metric("Total Runs", total_runs)
c2.metric("Non-Compliant", non_compliant)
c3.metric("Avg Risk Score", avg_risk if pd.notna(avg_risk) else 0)
c4.metric("Unique Policies", unique_policies)

# Category counts chart (optional)
if "detected_category" in df and df["detected_category"].notna().any():
    st.bar_chart(df["detected_category"].value_counts())

st.divider()

# ---- Filters ----
st.subheader("Filters")
col1, col2, col3, col4 = st.columns(4)

with col1:
    status_filter = st.multiselect(
        "LLM Status",
        options=sorted(df["status"].dropna().unique().tolist()),
        default=[],
    )

with col2:
    cat_filter = st.multiselect(
        "Detected Category",
        options=sorted(df["detected_category"].dropna().unique().tolist()),
        default=[],
    )

with col3:
    min_risk = st.slider("Min Risk Score", 0, 100, 0)

with col4:
    policy_search = st.text_input("Search in policy text")

filtered = df.copy()

if status_filter:
    filtered = filtered[filtered["status"].isin(status_filter)]

if cat_filter:
    filtered = filtered[filtered["detected_category"].isin(cat_filter)]

# risk_score may contain None -> filter safely
filtered_risk = pd.to_numeric(filtered["risk_score"], errors="coerce").fillna(-1)
filtered = filtered[filtered_risk >= min_risk]

if policy_search.strip():
    q = policy_search.strip().lower()
    filtered = filtered[filtered["policy_text"].fillna("").str.lower().str.contains(q)]

st.divider()

# ---- Table ----
st.subheader(f"Audit Runs ({len(filtered)} shown / {len(df)} total)")
st.dataframe(
    filtered.sort_values("timestamp_utc", ascending=False),
    use_container_width=True,
)

st.divider()

# ---- Detail viewer ----
st.subheader("View One Run (full record)")

request_ids = (
    filtered.sort_values("timestamp_utc", ascending=False)["request_id"]
    .dropna()
    .astype(str)
    .tolist()
)
request_ids = [rid for rid in request_ids if rid.strip() and rid.lower() != "none"]

if not request_ids:
    st.info("No records match your filters.")
    st.stop()

st.write("Search by request_id (or select from list):")
search_id = st.text_input("Enter request_id", key="request_id_search").strip()

if search_id:
    selected_id = search_id
else:
    selected_id = st.selectbox("Select request_id", options=request_ids)

# Find record by id (normalize both sides)
selected = None
for r in rows:
    if normalize_request_id(r.get("request_id")) == selected_id:
        selected = r
        break

if not selected:
    st.warning("Could not find that request_id in the log.")
    st.stop()

# ---- Render details ----
st.write("**Policy text:**")
st.code(selected.get("policy_text", ""))

st.write("**Citations:**")
cits = selected.get("citations", []) or []
if not cits:
    st.info("No citations recorded.")
else:
    st.dataframe(cits, use_container_width=True)

st.write("**Raw JSON:**")
st.code(json.dumps(selected, indent=2, ensure_ascii=False))
