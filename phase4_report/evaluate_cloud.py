"""
Phase 4 -- Cloud Evaluation Script

Tests the DEPLOYED Cloud Run endpoint via HTTP POST.
Uses Python requests -- NO curl, NO shell quoting issues with apostrophes.

Usage:
    # Against Cloud Run (set API_URL in your .env or as env variable)
    python phase4_report/evaluate_cloud.py

    # Against local API (default if API_URL is not set)
    python phase4_report/evaluate_cloud.py

Output:
    Console log + phase4_report/cloud_evaluation_results.json
"""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# Set API_URL in .env to your Cloud Run URL, or leave blank to test locally
API_URL = os.getenv("API_URL", "http://localhost:8080")

# ── 5 evaluation queries ───────────────────────────────────────────────────────
# Python strings handle apostrophes natively -- no shell escaping needed.

TEST_QUERIES = [
    {
        "id": "Q1",
        "question": "What was Apple's total revenue in 2023?",
        "type": "SQL only",
        "ground_truth": "Apple's total revenue in 2023 was $383,285 million.",
    },
    {
        "id": "Q2",
        "question": "What did Tesla say about supply chain risks in their 2023 annual report?",
        "type": "Vector search only",
        "ground_truth": (
            "Tesla's 2023 10-K discusses supply chain disruptions, component shortages, "
            "and dependency on single-source suppliers as key operational risks."
        ),
    },
    {
        "id": "Q3",
        "question": "Compare Microsoft's net income between 2022 and 2023. Did it grow?",
        "type": "SQL only",
        "ground_truth": (
            "Microsoft net income was $72,738M in 2022 and $72,361M in 2023 "
            "-- a slight decrease of ~0.5%."
        ),
    },
    {
        "id": "Q4",
        "question": (
            "What was Apple's hardware revenue strategy in 2024, "
            "and how much gross profit did they generate that year?"
        ),
        "type": "Multi-modal (SQL + Vector)",
        "ground_truth": (
            "Apple's gross profit in 2024 was $180,683M. Their reports discuss continued "
            "investment in custom silicon (M-series chips) and services bundled with hardware."
        ),
    },
    {
        "id": "Q5",
        "question": (
            "Which company had the highest R&D expenses in 2023, "
            "and what did their report say about AI investments?"
        ),
        "type": "Multi-modal (SQL + Vector)",
        "ground_truth": (
            "Apple had the highest R&D expense in 2023 at $29,915M. "
            "Their reports discuss AI integration across products (on-device ML, Apple Intelligence)."
        ),
    },
]


def run_cloud_evaluation():
    print("=" * 70)
    print(f"CLOUD EVALUATION -- Target: {API_URL}")
    print("=" * 70)

    # Health check first
    try:
        health = requests.get(f"{API_URL}/health", timeout=15)
        print(f"[Health] {health.json()}\n")
    except Exception as e:
        print(f"[ERROR] Cannot reach {API_URL}: {e}")
        print("  --> Make sure the API is running (local or Cloud Run).")
        return

    results = []

    for query in TEST_QUERIES:
        print(f"\n[{query['id']}] {query['type']}")
        print(f"Question: {query['question']}")
        print("-" * 50)

        start = time.time()
        try:
            # json= handles apostrophes and all special characters safely
            response = requests.post(
                f"{API_URL}/query",
                json={"question": query["question"]},
                timeout=120,
            )
            elapsed = round(time.time() - start, 2)

            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "")
                cost = data.get("token_cost_usd", 0.0)
                latency = data.get("latency_seconds", elapsed)
                status = "ok"
                cache_hit = cost == 0.0 and latency < 0.5
                cache_note = "[CACHE HIT]" if cache_hit else ""
            else:
                answer = f"HTTP {response.status_code}: {response.text[:200]}"
                cost, latency, status, cache_note = 0.0, elapsed, "http_error", ""

        except requests.exceptions.Timeout:
            answer = "TIMEOUT -- request exceeded 120 seconds"
            cost, latency, status, cache_note = 0.0, 120.0, "timeout", ""
        except Exception as e:
            answer = f"ERROR: {e}"
            cost, latency, status, cache_note = 0.0, 0.0, "error", ""

        print(f"Answer: {answer[:300]}{'...' if len(answer) > 300 else ''}")
        print(f"Cost: ${cost:.6f} | Latency: {latency}s | Status: {status} {cache_note}")

        results.append({
            "id": query["id"],
            "type": query["type"],
            "question": query["question"],
            "ground_truth": query["ground_truth"],
            "agent_answer": answer,
            "token_cost_usd": round(cost, 6),
            "latency_seconds": latency,
            "status": status,
            "target_url": API_URL,
            "scores": {
                "faithfulness": None,
                "answer_relevance": None,
                "notes": "",
            },
        })

    # Save results next to this script
    output_path = Path(__file__).resolve().parent / "cloud_evaluation_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    ok_count = sum(1 for r in results if r["status"] == "ok")
    total_cost = sum(r["token_cost_usd"] for r in results)
    avg_latency = sum(r["latency_seconds"] for r in results) / len(results)

    print("\n" + "=" * 70)
    print("CLOUD EVALUATION SUMMARY")
    print("=" * 70)
    print(f"  Target        : {API_URL}")
    print(f"  Successful    : {ok_count}/{len(results)}")
    print(f"  Total cost    : ${total_cost:.6f}")
    print(f"  Avg latency   : {avg_latency:.2f}s")
    print(f"  Est. cost/100 : ${total_cost / max(ok_count, 1) * 100:.4f}")
    print(f"\n  Results saved : {output_path}")
    print("  --> Open the JSON and fill in faithfulness / answer_relevance scores manually.")


if __name__ == "__main__":
    run_cloud_evaluation()
