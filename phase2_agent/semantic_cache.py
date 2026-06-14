"""
Advanced Option 2: Semantic Cache using Redis

"""

import json
import hashlib
import numpy as np
from sentence_transformers import SentenceTransformer
import redis
import os

#REDIS_URL = "redis://localhost:6379"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SIMILARITY_THRESHOLD = 0.75
CACHE_TTL = 86400  # 24 hours

embedder = SentenceTransformer("all-MiniLM-L6-v2")
redis_client = redis.from_url(REDIS_URL)


def cosine_similarity(a: list, b: list) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def get_cached_answer(question: str) -> dict | None:
    """Check if a semantically similar question exists in cache."""
    query_vector = embedder.encode(question).tolist()
    cached_keys = redis_client.keys("cache:*")

    for key in cached_keys:
        cached = json.loads(redis_client.get(key))
        similarity = cosine_similarity(query_vector, cached["vector"])
        if similarity >= SIMILARITY_THRESHOLD:
            print(f"[Cache HIT] similarity={similarity:.4f} | question='{cached['question']}'")
            return {
                "answer": cached["answer"],
                "token_cost_usd": 0.0,
                "cache_hit": True,
                "similarity": similarity,
            }

    print(f"[Cache MISS] No similar question found for: '{question}'")
    return None


def store_in_cache(question: str, answer: str):
    """Store question + answer + embedding in Redis."""
    vector = embedder.encode(question).tolist()
    key = f"cache:{hashlib.md5(question.encode()).hexdigest()}"
    payload = json.dumps({
        "question": question,
        "answer": answer,
        "vector": vector,
    })
    redis_client.setex(key, CACHE_TTL, payload)
    print(f"[Cache STORE] Stored answer for: '{question}'")


if __name__ == "__main__":
    # Test the cache
    store_in_cache(
        "What was Apple total revenue in 2023?",
        "Apple's total revenue in 2023 was $383,285 million."
    )

    # Exact match
    result = get_cached_answer("What was Apple total revenue in 2023?")
    print("Exact match:", result)

    # Semantic match
    result = get_cached_answer("How much did Apple earn in 2023?")
    print("Semantic match:", result)

    # No match
    result = get_cached_answer("What is Tesla's gigafactory capacity?")
    print("No match:", result)