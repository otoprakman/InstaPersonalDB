import chromadb
from chromadb.utils import embedding_functions
import uuid

# Client setup
client = chromadb.PersistentClient(path="data/chroma_db")

# Embedding function
# Use a local model to avoid API costs and keep it consistent with the "CPU/Offline" theme
# sentence-transformers/all-MiniLM-L6-v2 is standard and fast
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2",
    device="cpu"  # Force CPU
)

collection = client.get_or_create_collection(
    name="insta_posts",
    embedding_function=sentence_transformer_ef
)

def ingest_document(shortcode, content, image_path=None):
    """
    Upsert a document into ChromaDB.
    """
    if not content or not content.strip():
        return
        
    collection.upsert(
        documents=[content],
        metadatas=[{"shortcode": shortcode, "image_path": str(image_path) if image_path else ""}],
        ids=[shortcode]
    )
    print(f"Ingested {shortcode} into RAG.")

def document_exists(shortcode):
    """
    Check if a document exists in the collection.
    """
    existing = collection.get(ids=[shortcode])
    return len(existing['ids']) > 0

def query_similar(query_text, n_results=5):
    """
    Query the database.
    """
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )
    return results
