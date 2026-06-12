"""
Phase 3 - FastAPI REST API
Exposes the LangGraph agent as a REST endpoint for Cloud Run deployment.
"""

import sys
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.append(str(Path(__file__).resolve().parent.parent))

from phase2_agent.agent import build_agent
from langchain_core.messages import HumanMessage

app = FastAPI(
    title="Enterprise AI Data Analyst",
    description="Multi-Modal Agent combining SQL and Vector DB for financial analysis",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    question: str
    answer: str
    token_cost_usd: float
    latency_seconds: float

@app.get("/")
def root():
    return {"status": "ok", "message": "Enterprise AI Data Analyst is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    start_time = time.time()

    try:
        agent = build_agent()
        result = agent.invoke({
            "messages": [HumanMessage(content=request.question)],
            "token_cost": 0.0,
        })

        final_answer = result["messages"][-1].content
        total_cost = result.get("token_cost", 0.0)
        latency = round(time.time() - start_time, 3)

        print(f"[API] question='{request.question[:50]}' | cost=${total_cost:.6f} | latency={latency}s")

        return QueryResponse(
            question=request.question,
            answer=final_answer,
            token_cost_usd=total_cost,
            latency_seconds=latency,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8080, reload=False)