from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings


def test_retrieval(query: str):
    embedding_model = SentenceTransformerEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

    vector_store = Chroma(
        persist_directory="data/vector_store",
        embedding_function=embedding_model
    )

    results = vector_store.similarity_search(query, k=3)

    for i, doc in enumerate(results):
        print(f"\nResult {i+1}")
        print("Article:", doc.metadata["article_number"])
        print("Title:", doc.metadata["title"])
        print("Preview:", doc.page_content[:500])


if __name__ == "__main__":
    query = "prohibited AI practices"
    test_retrieval(query)
