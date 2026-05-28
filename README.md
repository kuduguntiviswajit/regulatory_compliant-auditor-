# EU AI Act Compliance Auditor

A vector-grounded LLM compliance engine that audits company policy snippets against the EU AI Act. Combines semantic retrieval (RAG) with deterministic risk scoring to classify policies into EU AI Act risk categories, detect violations, and generate traceable compliance reports — all served through a FastAPI backend and a two-page Streamlit dashboard.

---

## What This Project Does

The EU AI Act (Regulation 2024/1689) introduces a risk-based regulatory framework for AI systems across the European Union. Companies deploying AI need to verify whether their internal policies comply with the Act's requirements — covering prohibited practices, high-risk obligations, transparency rules, and general-purpose AI model governance.

This project automates that compliance check end to end:

1. A company policy snippet is submitted via API or dashboard
2. An LLM classifies the policy into one of four EU AI Act risk categories
3. The vector store retrieves the most relevant EU AI Act articles using semantic search
4. The LLM generates a structured compliance assessment grounded in the retrieved articles
5. A deterministic risk scoring engine independently calculates a risk score based on article severity
6. Both assessments (LLM + deterministic) are returned with full article citations and logged for audit traceability

The dual-scoring approach (LLM reasoning + rule-based scoring) is a deliberate design choice — it provides a cross-check between probabilistic and deterministic outputs, making the system more defensible in a regulatory context.

---

## Tech Stack

| Component               | Technology                                     |
| ------------------------ | ---------------------------------------------- |
| Backend API              | FastAPI, Pydantic V2, Uvicorn                  |
| LLM Integration          | LangChain, OpenAI GPT-4o-mini                  |
| Vector Store             | ChromaDB, Sentence-Transformers (all-MiniLM-L6-v2) |
| Embeddings               | SentenceTransformerEmbeddings                  |
| Text Processing          | LangChain Text Splitters, Regex                |
| Dashboard                | Streamlit                                      |
| Data Format              | JSON (articles), JSONL (audit logs)            |
| Language                 | Python                                         |
| Version Control          | Git                                            |

---

## Project Architecture

```
regulatory_compliant-auditor-/
├── main.py                              # FastAPI app entry point with startup warmup
├── requirements.txt                     # Full dependency list
│
├── app/
│   ├── api/
│   │   └── routes.py                    # /audit, /report/{id}, /report/latest endpoints
│   ├── services/
│   │   ├── compliance_analyzer.py       # LLM risk classification, RAG retrieval, assessment
│   │   ├── risk_scoring.py              # Deterministic risk scoring engine
│   │   ├── vector_store_builder.py      # Embeds EU AI Act articles into ChromaDB
│   │   ├── audit_logger.py              # JSONL audit trail logger
│   │   └── retriever_test.py            # Manual retrieval verification script
│   ├── core/
│   │   └── taxonomy.py                  # Article-to-block mapping, fine tiers, topic classification
│   └── utils/
│       ├── eu_act_parser.py             # PDF-to-JSON extractor for EU AI Act text
│       ├── audit_logger.py              # Shared audit logging utility
│       └── debug_chroma_metadata.py     # Vector store metadata inspector
│
├── streamlit_app/
│   ├── app.py                           # Main audit page with report export
│   └── pages/
│       └── 2_Audit_History.py           # Filterable audit history with detail viewer
│
└── data/
    └── eu_ai_act_articles.json          # Structured EU AI Act articles (parsed from official PDF)
```

---

## How It Works

### Risk Classification

When a policy snippet is submitted, the LLM classifies it into exactly one EU AI Act category:

| Category                  | Description                                                    |
| ------------------------- | -------------------------------------------------------------- |
| Prohibited AI Practice    | Practices explicitly banned (Article 5) — social scoring, real-time biometrics |
| High-Risk AI System       | Systems requiring conformity assessment (Articles 6–15)        |
| Transparency Obligation   | Systems requiring disclosure to users (Article 50)             |
| Low / Minimal Risk        | Systems with no mandatory requirements                         |

### RAG Retrieval

The classified category determines which block of EU AI Act articles the vector store searches. The retrieval uses a multi-fallback strategy:

1. **Primary:** Filter by both `risk_type` and `block` (and optional `topic`)
2. **Fallback 1:** Drop topic filter, keep risk_type + block
3. **Fallback 2:** Filter by `risk_type` only
4. **Fallback 3:** Unfiltered semantic search

This ensures the system always returns relevant articles, even for edge-case policies.

### Deterministic Risk Scoring

Independent of the LLM assessment, a rule-based scoring engine assigns a risk score (0–100):

| Category                  | Base Score | Additional Penalty                          |
| ------------------------- | ---------- | ------------------------------------------- |
| Prohibited AI Practice    | 100        | +50 per Article 5 violation                 |
| High-Risk AI System       | 50         | +20 per key obligation (Articles 9,10,13–15)|
| Transparency Obligation   | 30         | +10 per enforcement article                 |
| Low / Minimal Risk        | 0          | No penalty                                  |

| Score Range | Status         |
| ----------- | -------------- |
| 0–30        | Compliant      |
| 31–60       | At Risk        |
| 61–100      | Non-Compliant  |

### Article Taxonomy

Each EU AI Act article is tagged with structured metadata during vector store ingestion:

- **Block:** Foundation, RedLine, HighRiskMandatory, Transparency, GPAI, Enforcement, General
- **Fine Tier:** Tier1 (prohibited, 50 points), Tier2 (key obligations, 20 points), Tier3 (enforcement, 10 points)
- **Topic:** Automatically classified via hard overrides and keyword scanning (biometrics, data governance, human oversight, etc.)
- **Snippet Checkable:** Whether the article can be directly evaluated against a policy snippet

---

## API Endpoints

### `POST /audit`

Submit a policy snippet for compliance analysis.

**Request:**
```json
{
  "policy_text": "Our system uses real-time facial recognition in public spaces for law enforcement."
}
```

**Response:**
```json
{
  "request_id": "a1b2c3d4-...",
  "status": "Non-Compliant",
  "detected_category": "Prohibited AI Practice",
  "violated_articles": ["Article 5"],
  "reasoning": "Real-time remote biometric identification in publicly accessible spaces for law enforcement is prohibited under Article 5(1)(h)...",
  "confidence_score": 95,
  "risk_score": 100,
  "deterministic_status": "Non-Compliant",
  "deterministic_violated_articles": ["Article 5"],
  "citations": [
    {
      "article_number": "5",
      "title": "Prohibited AI practices",
      "risk_type": "Prohibited",
      "block": "RedLine",
      "topic": "prohibited"
    }
  ]
}
```

### `GET /report/{request_id}`

Retrieve a specific audit report by request ID.

### `GET /report/latest`

Retrieve the most recent audit report.

### `GET /health`

Health check endpoint.

---

## Dashboard Pages

| Page           | Description                                                        |
| -------------- | ------------------------------------------------------------------ |
| Audit          | Submit policies, view LLM + deterministic results, export reports  |
| Audit History  | Filter past runs by status, category, risk score; view full details|

The audit page displays four summary metrics (LLM Status, Deterministic Status, Risk Score, Detected Category), violated articles from both engines, reasoning, and article citations. Reports are exportable as JSON or Markdown.

The history page provides quick stats (total runs, non-compliant count, average risk score, unique policies), a category distribution bar chart, and multi-filter search with full record drill-down.

---

## Data Pipeline

### PDF → Structured JSON

The `eu_act_parser.py` utility extracts articles from the official EU AI Act PDF:

1. Load PDF using LangChain's PyPDFLoader
2. Extract article sections using regex pattern matching
3. Parse article number, title, and content from each section
4. Deduplicate and save as structured JSON

### JSON → Vector Store

The `vector_store_builder.py` ingests the structured articles into ChromaDB:

1. Load articles from `data/eu_ai_act_articles.json`
2. Assign metadata: risk_type, block, topic, fine_tier, severity_points, snippet_checkable
3. Chunk articles using RecursiveCharacterTextSplitter (1200 chars, 150 overlap)
4. Embed using all-MiniLM-L6-v2 via SentenceTransformerEmbeddings
5. Persist to ChromaDB at `data/vector_store/`

---

## Setup

```bash
# Clone the repo
git clone https://github.com/kuduguntiviswajit/regulatory_compliant-auditor-.git
cd regulatory_compliant-auditor-

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set OpenAI API key
export OPENAI_API_KEY="your-key-here"    # Windows: set OPENAI_API_KEY=your-key-here

# Build the vector store (first time only)
python -m app.services.vector_store_builder

# Run the API
uvicorn main:app --reload

# In a separate terminal, launch the dashboard
streamlit run streamlit_app/app.py
```

Open http://127.0.0.1:8000/docs for the interactive API docs.
Open http://localhost:8501 for the Streamlit dashboard.

---

## Design Decisions

**Why RAG + deterministic scoring instead of LLM-only?**
LLMs can hallucinate compliance status. The deterministic scoring engine provides an independent, reproducible cross-check based on article severity metadata. If the two assessments disagree, that's a signal for human review.

**Why ChromaDB with metadata filtering?**
Filtering by risk_type and block before semantic search reduces retrieval noise. A policy about facial recognition shouldn't retrieve articles about GPAI model governance. The multi-fallback retrieval ensures coverage even when strict filters return no results.

**Why GPT-4o-mini instead of a larger model?**
For classification and structured JSON extraction from a focused context window (policy + 4 retrieved articles), GPT-4o-mini provides sufficient accuracy at lower cost and latency. The deterministic scoring layer compensates for cases where the LLM under-performs.

**Why JSONL for audit logs?**
Append-only JSONL is simple, human-readable, and doesn't require a database. Each audit run is a self-contained record with timestamp, request ID, policy text, both assessments, and citations — making it straightforward to replay, filter, or migrate to a database later.

**Why Sentence-Transformers (all-MiniLM-L6-v2)?**
Lightweight, fast, runs on CPU, and performs well for semantic similarity on regulatory text. No GPU or API calls required for embeddings.

---

## Relevance to Compliance & Data Analytics Roles

| Responsibility                        | Project Component                                    |
| ------------------------------------- | ---------------------------------------------------- |
| Regulatory data analysis              | EU AI Act article parsing, classification, scoring   |
| ETL pipeline design                   | PDF → JSON → ChromaDB ingestion pipeline             |
| API development                       | FastAPI REST endpoints with Pydantic validation      |
| Dashboard & reporting                 | Two-page Streamlit app with export functionality     |
| Audit trail & traceability            | JSONL logging with request IDs and timestamps        |
| Risk scoring & classification         | Deterministic risk engine + LLM-based assessment     |
| Vector database & semantic search     | ChromaDB with metadata-filtered RAG retrieval        |
| LLM integration & prompt engineering  | Structured JSON output prompts with safe parsing     |

---

Built by Viswajit Kudugunti — [GitHub](https://github.com/kuduguntiviswajit)
