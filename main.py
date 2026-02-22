from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.services.compliance_analyzer import get_llm, get_vector_store, get_embedding_model

app = FastAPI(
    title="EU AI Act Compliance Auditor",
    description="Vector-grounded LLM compliance engine",
    version="1.1.0",
)

# Allow Streamlit (and browser tools) to call FastAPI.
# You can restrict this later to specific origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"message": "Compliance Auditor API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


# Warm up caches once at startup (faster first /audit call)
@app.on_event("startup")
def warmup():
    get_embedding_model()
    get_vector_store()
    get_llm()
