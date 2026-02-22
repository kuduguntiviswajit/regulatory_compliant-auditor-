from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma

embedding_model = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

db = Chroma(
    persist_directory="data/vector_store",
    embedding_function=embedding_model
)

# Get a few documents without filters
docs = db.similarity_search("prohibited AI practices", k=5)

print("Docs returned:", len(docs))
for i, d in enumerate(docs, start=1):
    print("\n--- Doc", i, "---")
    print("Metadata:", d.metadata)
