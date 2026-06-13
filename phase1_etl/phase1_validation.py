import os

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer

load_dotenv()

COLLECTION_NAME = "financial_reports"


def main():
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    client = QdrantClient(url=qdrant_url)

    if not client.collection_exists(COLLECTION_NAME):
        raise RuntimeError(
            f"Collection '{COLLECTION_NAME}' does not exist. "
            "Run 'python phase1_etl/01_fake_ingest.py' first."
        )

    collection_info = client.get_collection(COLLECTION_NAME)
    point_count = collection_info.points_count
    print(f"Collection '{COLLECTION_NAME}' contains {point_count} chunks.")

    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    query_text = "What did Apple say about services revenue and growth in 2024?"
    query_vector = embedder.encode(query_text).tolist()

    strict_filter = models.Filter(
        must=[
            models.FieldCondition(key="company", match=models.MatchValue(value="Apple")),
            models.FieldCondition(key="year", match=models.MatchValue(value=2024)),
        ]
    )

    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        using="text_dense",
        query_filter=strict_filter,
        limit=3,
        with_payload=True,
    )

    print("\nTest query:", query_text)
    print("Top results with metadata filter:")
    for i, hit in enumerate(response.points, start=1):
        print(f"\n[{i}] score={hit.score:.4f}")
        print("  company:", hit.payload.get("company"))
        print("  year:", hit.payload.get("year"))
        print("  source_file:", hit.payload.get("source_file"))
        print("  source_page:", hit.payload.get("source_page"))
        print("  chunk_id:", hit.payload.get("chunk_id"))
        print("  text:", hit.payload.get("text"))


if __name__ == "__main__":
    main()
