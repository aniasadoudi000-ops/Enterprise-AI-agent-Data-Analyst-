"""
Phase 4 — RAGAS-style Evaluation Script

Runs 5 representative test queries through the LangGraph agent and records
outputs for manual grading on two RAGAS dimensions:
  - Faithfulness  : Does the answer contain only verifiable claims? (1–5)
  - Answer Relevance: Does the answer address what was asked? (1–5)

Usage:
    # Make sure docker-compose services are running and the DB is created
    python phase4_report/evaluate.py

Output:
    Console log + evaluation_results.json
"""

import json
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()

sys.path.append(str(Path(__file__).resolve().parent.parent))
from phase2_agent.agent import build_agent

# ── 5 evaluation queries ───────────────────────────────────────────────────────

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
        "ground_truth": "Tesla's 2023 10-K discusses supply chain disruptions, component shortages, and dependency on single-source suppliers as key operational risks.",
    },
    {
        "id": "Q3",
        "question": "Compare Microsoft's net income between 2022 and 2023. Did it grow?",
        "type": "SQL only",
        "ground_truth": "Microsoft net income was $72,738M in 2022 and $72,361M in 2023 — a slight decrease of ~0.5%.",
    },
    {
        "id": "Q4",
        "question": "What was Apple's hardware revenue strategy in 2024, and how much gross profit did they generate that year?",
        "type": "Multi-modal (SQL + Vector)",
        "ground_truth": "Apple's gross profit in 2024 was $180,683M. Their reports discuss continued investment in custom silicon (M-series chips) and services bundled with hardware.",
    },
    {
        "id": "Q5",
        "question": "Which company had the highest R&D expenses in 2023, and what did their report say about AI investments?",
        "type": "Multi-modal (SQL + Vector)",
        "ground_truth": "Microsoft had the highest R&D expense in 2023 at $29,510M... wait — Microsoft 2023 R&D was $27,195M, Apple was $29,915M. Their reports discuss AI integration across products (Copilot, Azure AI).",
    },
]

# ── Manual scoring rubric ──────────────────────────────────────────────────────
# After running, open evaluation_results.json and fill in the scores manually.
# Faithfulness  (1-5): 5 = every claim is verifiable from sources, 1 = hallucinations
# Answer Relevance (1-5): 5 = directly addresses the question, 1 = off-topic

SCORING_TEMPLATE = {
    "faithfulness": None,        # Fill in manually after review
    "answer_relevance": None,    # Fill in manually after review
    "notes": "",
}


def run_evaluation():
    print("=" * 70)
    print("RAGAS-STYLE EVALUATION — Enterprise AI Data Analyst")
    print("=" * 70)
    print(f"Running {len(TEST_QUERIES)} test queries...\n")

    agent = build_agent()
    results = []

    for query in TEST_QUERIES:
        print(f"\n[{query['id']}] {query['type']}")
        print(f"Question: {query['question']}")
        print("-" * 50)

        start = time.time()
        try:
            state = agent.invoke({
                "messages": [HumanMessage(content=query["question"])],
                "token_cost": 0.0,
            })
            answer = state["messages"][-1].content
            token_cost = state.get("token_cost", 0.0)
            latency = round(time.time() - start, 2)
            status = "ok"
        except Exception as e:
            answer = f"ERROR: {e}"
            token_cost = 0.0
            latency = round(time.time() - start, 2)
            status = "error"

        print(f"Answer: {answer[:300]}{'...' if len(answer) > 300 else ''}")
        print(f"Cost: ${token_cost:.6f} | Latency: {latency}s | Status: {status}")

        results.append({
            "id": query["id"],
            "type": query["type"],
            "question": query["question"],
            "ground_truth": query["ground_truth"],
            "agent_answer": answer,
            "token_cost_usd": round(token_cost, 6),
            "latency_seconds": latency,
            "status": status,
            "scores": SCORING_TEMPLATE.copy(),   # Fill in manually
        })

    # Save results
    output_path = Path("evaluation_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    total_cost = sum(r["token_cost_usd"] for r in results)
    avg_latency = sum(r["latency_seconds"] for r in results) / len(results)
    ok_count = sum(1 for r in results if r["status"] == "ok")

    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    print(f"  Queries run   : {len(results)}")
    print(f"  Successful    : {ok_count}/{len(results)}")
    print(f"  Total cost    : ${total_cost:.6f}")
    print(f"  Avg latency   : {avg_latency:.2f}s")
    print(f"  Cost/100 queries (estimated): ${total_cost / len(results) * 100:.4f}")
    print(f"\n  Results saved to: {output_path.resolve()}")
    print("  Open the JSON file and fill in 'faithfulness' and 'answer_relevance' scores manually.")


if __name__ == "__main__":
    run_evaluation()
