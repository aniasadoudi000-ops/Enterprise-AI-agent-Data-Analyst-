"""
Phase 2 - Agentic State Machine
LangGraph ReAct Agent with two tools:
  - execute_sql: queries SQLite database
  - search_vector_db: searches Qdrant with metadata filters
"""

import os
import sqlite3
import json
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel, Field

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "financial_reports"
DB_PATH = "database/financial_data.db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ── Shared resources (loaded once) ────────────────────────────────────────────

embedder = SentenceTransformer(EMBEDDING_MODEL)
qdrant_client = QdrantClient(url=QDRANT_URL)
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
)

# ── Pydantic schema for vector search filters ─────────────────────────────────

class VectorSearchInput(BaseModel):
    query: str = Field(description="The semantic search query text")
    company: str | None = Field(default=None, description="Filter by company name e.g. Apple, Tesla, Microsoft")
    year: int | None = Field(default=None, description="Filter by document year e.g. 2023")
    top_k: int = Field(default=3, description="Number of results to return")


# ── Tool 1: execute_sql ───────────────────────────────────────────────────────

@tool
def execute_sql(query: str) -> str:
    """
    Execute a SQL query against the local SQLite financial database.
    Use this tool for structured numerical questions like revenue, profit, growth rates.
    The database contains tables: financials (company, year, revenue, net_income, gross_profit, rd_expense, total_assets).
    Always write valid SQLite syntax. If unsure of table structure, run: SELECT name FROM sqlite_master WHERE type='table';
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()

        if not results:
            return "Query executed successfully but returned no results."

        # Format as readable table
        rows = [dict(zip(columns, row)) for row in results]
        return json.dumps(rows, indent=2)

    except sqlite3.OperationalError as e:
        # Error recovery: return the error so the agent can fix its query
        return f"SQL_ERROR: {str(e)}. Please fix your query and try again."
    except Exception as e:
        return f"UNEXPECTED_ERROR: {str(e)}"


# ── Tool 2: search_vector_db ──────────────────────────────────────────────────

@tool
def search_vector_db(query: str, company: str = None, year: int = None, top_k: int = 3) -> str:
    """
    Search the Qdrant vector database containing financial reports (10-K PDFs).
    Use this tool for qualitative questions about strategy, risks, outlook, or any text content.
    Optionally filter by company name (e.g. 'Apple') and/or year (e.g. 2023).
    """
    try:
        # Build metadata filters
        filters = []
        if company:
            filters.append(
                qdrant_models.FieldCondition(
                    key="company",
                    match=qdrant_models.MatchValue(value=company.capitalize())
                )
            )
        if year:
            filters.append(
                qdrant_models.FieldCondition(
                    key="year",
                    match=qdrant_models.MatchValue(value=int(year))
                )
            )

        query_filter = qdrant_models.Filter(must=filters) if filters else None

        # Embed the query
        query_vector = embedder.encode(query).tolist()

        # Search
        response = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            using="text_dense",
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        if not response.points:
            return "No results found in the vector database for this query."

        results = []
        for hit in response.points:
            results.append({
                "score": round(hit.score, 4),
                "company": hit.payload.get("company"),
                "year": hit.payload.get("year"),
                "source_file": hit.payload.get("source_file"),
                "source_page": hit.payload.get("source_page"),
                "text": hit.payload.get("text", "")[:500],  # truncate for context
            })

        return json.dumps(results, indent=2)

    except Exception as e:
        return f"VECTOR_SEARCH_ERROR: {str(e)}"


# ── LangGraph State ───────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    token_cost: float  # FinOps tracking


# ── Agent nodes ───────────────────────────────────────────────────────────────

tools = [execute_sql, search_vector_db]
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = """You are an Enterprise AI Data Analyst with access to two tools:

1. execute_sql: for structured numerical data (revenue, profit, growth rates)
2. search_vector_db: for qualitative text from financial reports (risks, strategy, outlook)

For complex questions, use BOTH tools and synthesize a complete answer.
Always cite your sources (company, year, page when available).
If a SQL query fails, analyze the error and retry with a corrected query.
Be concise but thorough."""


def call_agent(state: AgentState) -> AgentState:
    """Call the LLM with tools."""
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)

    # Rough token cost tracking (Gemini Flash: ~$0.075/1M input, ~$0.30/1M output)
    input_tokens = response.usage_metadata.get("input_tokens", 0) if hasattr(response, "usage_metadata") and response.usage_metadata else 0
    output_tokens = response.usage_metadata.get("output_tokens", 0) if hasattr(response, "usage_metadata") and response.usage_metadata else 0
    cost = (input_tokens * 0.075 + output_tokens * 0.30) / 1_000_000
    total_cost = state.get("token_cost", 0.0) + cost

    print(f"[FinOps] Tokens: {input_tokens} in / {output_tokens} out | Step cost: ${cost:.6f} | Total: ${total_cost:.6f}")

    return {"messages": [response], "token_cost": total_cost}


def call_tools(state: AgentState) -> AgentState:
    """Execute tool calls from the last AI message."""
    last_message = state["messages"][-1]
    tool_map = {t.name: t for t in tools}
    tool_messages = []

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        print(f"[Tool] Calling: {tool_name}({tool_args})")

        if tool_name in tool_map:
            result = tool_map[tool_name].invoke(tool_args)
        else:
            result = f"ERROR: Tool '{tool_name}' not found."

        tool_messages.append(
            ToolMessage(content=str(result), tool_call_id=tool_call["id"])
        )

    return {"messages": tool_messages}


def should_continue(state: AgentState) -> str:
    """Decide whether to call tools or end."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "call_tools"
    return END


# ── Build the graph ───────────────────────────────────────────────────────────

def build_agent():
    graph = StateGraph(AgentState)
    graph.add_node("agent", call_agent)
    graph.add_node("call_tools", call_tools)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("call_tools", "agent")
    return graph.compile()


# ── Run the agent ─────────────────────────────────────────────────────────────

def run_agent(question: str):
    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print('='*60)

    agent = build_agent()
    result = agent.invoke({
        "messages": [HumanMessage(content=question)],
        "token_cost": 0.0,
    })

    final_answer = result["messages"][-1].content
    total_cost = result.get("token_cost", 0.0)

    print(f"\n[Answer]\n{final_answer}")
    print(f"\n[FinOps] Total cost for this query: ${total_cost:.6f}")
    return final_answer


if __name__ == "__main__":
    # Test queries
    questions = [
        "What was Apple's total revenue in 2023?",
        "What did Tesla say about supply chain risks in their 2023 annual report?",
        "Compare Microsoft's net income between 2022 and 2023.",
    ]

    for q in questions:
        run_agent(q)
