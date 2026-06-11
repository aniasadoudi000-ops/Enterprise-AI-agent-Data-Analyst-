import os
import importlib.util
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
COLLECTION_NAME = "financial_reports"


def load_extractor_module():
    extractor_path = BASE_DIR / "03_extract_pdfs.py"
    spec = importlib.util.spec_from_file_location("phase1_pdf_extractor", extractor_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load extractor module from {extractor_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def create_collection(client: QdrantClient):
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing collection '{COLLECTION_NAME}'.")

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "text_dense": models.VectorParams(size=384, distance=models.Distance.COSINE)
        },
        sparse_vectors_config={"text_sparse": models.SparseVectorParams()},
    )
    print(f"Created collection '{COLLECTION_NAME}' with dense + sparse vectors.")



def main():
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    client = QdrantClient(url=qdrant_url)

    create_collection(client)

    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    extractor = load_extractor_module()
    documents = extractor.extract_all_documents()

    if not documents:
        raise RuntimeError("No chunks were extracted from the source PDFs.")

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([doc["text"] for doc in documents])

    points = []
    for idx, document in enumerate(documents, start=1):
        dense_vector = embedder.encode(document["text"]).tolist()
        sparse_row = tfidf_matrix[idx - 1]

        points.append(
            models.PointStruct(
                id=idx,
                vector={
                    "text_dense": dense_vector,
                    "text_sparse": models.SparseVector(
                        indices=sparse_row.indices.tolist(),
                        values=sparse_row.data.tolist(),
                    ),
                },
                payload={
                    "id": document["id"],
                    "company": document["company"],
                    "year": document["year"],
                    "document_type": document["document_type"],
                    "source_file": document["source_file"],
                    "source_page": document["source_page"],
                    "chunk_id": document["chunk_id"],
                    "char_count": document["char_count"],
                    "text": document["text"],
                    "source": "raw_pdf_documents",
                },
            )
        )

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"Inserted {len(points)} PDF chunks into Qdrant.")
    print("The phase 1 pipeline is now based on the real PDF corpus in data/raw.")



if __name__ == "__main__":
    main()
