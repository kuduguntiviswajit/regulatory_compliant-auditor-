import json
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.taxonomy import (
    block_for_article,
    fine_tier_and_points,
    topic_for_article,
    snippet_checkable
)


def assign_risk_type(article_number: str) -> str:
    num = int(article_number)

    if num == 5:
        return "Prohibited"
    elif num == 50:
        return "Transparency"
    elif 6 <= num <= 15:
        return "High"
    else:
        return "General"



def build_vector_store() -> None:
    # Load structured articles JSON
    articles_path = Path("data/eu_ai_act_articles.json")
    if not articles_path.exists():
        raise FileNotFoundError(f"Missing file: {articles_path}")

    with articles_path.open("r", encoding="utf-8") as f:
        articles = json.load(f)

    # Chunking settings (critical for good retrieval)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=150
    )

    documents = []

    for article in articles:
        combined_text = f"{article['title']}\n\n{article['content']}"

        num = int(article["article_number"])
        block = block_for_article(num)
        tier, points = fine_tier_and_points(num)
        topic = topic_for_article(article["article_number"], article["title"], article["content"])
        checkable = snippet_checkable(block)
        risk_type = assign_risk_type(article["article_number"])

        base_metadata = {
            "article_number": article["article_number"],
            "title": article["title"],
            "risk_type": risk_type,
            "block": block,
            "topic": topic,
            "snippet_checkable": checkable,
            "fine_tier": tier,
            "severity_points": points
        }

        chunks = splitter.split_text(combined_text)

        for idx, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={**base_metadata, "chunk_id": idx}
            )
            documents.append(doc)

    print(f"Total chunk-documents to embed: {len(documents)}")

    embedding_model = SentenceTransformerEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

    # Build and persist Chroma
    persist_dir = Path("data/vector_store")
    persist_dir.mkdir(parents=True, exist_ok=True)

    vector_store = Chroma.from_documents(
    documents=documents,
    embedding=embedding_model,
    persist_directory=str(persist_dir)
)

# Newer Chroma versions persist automatically when using persist_directory.
# Close client if available.
try:
    vector_store._client.persist()  # some versions expose persist on client
except Exception:
    pass

try:
    vector_store._client.close()
except Exception:
    pass

print("Vector store successfully built and saved.")


if __name__ == "__main__":
    build_vector_store()
