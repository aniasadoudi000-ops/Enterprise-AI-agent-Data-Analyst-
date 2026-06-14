"""
Streamlit UI for the Enterprise AI Data Analyst.

Two pages:
  1. Project Overview  -- architecture diagram, dataset, tech stack
  2. Chat with Agent   -- ChatGPT-style interface calling the FastAPI endpoint

Usage:
    # Against local API
    streamlit run streamlit_app.py

    # Against Cloud Run
    set API_URL=https://enterprise-ai-analyst-883304283246.europe-west1.run.app
    streamlit run streamlit_app.py
"""

import os
import time

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8080")

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Enterprise AI Data Analyst",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar navigation ─────────────────────────────────────────────────────────

st.sidebar.title("🤖 Enterprise AI\nData Analyst")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigation",
    ["📋 Project Overview", "💬 Chat with the Agent"],
    label_visibility="collapsed",
)
st.sidebar.markdown("---")
st.sidebar.caption(f"API: `{API_URL}`")

# ── Check API connectivity in sidebar ─────────────────────────────────────────
try:
    r = requests.get(f"{API_URL}/health", timeout=5)
    if r.status_code == 200:
        st.sidebar.success("API connected")
    else:
        st.sidebar.warning("API responded with error")
except Exception:
    st.sidebar.error("API unreachable")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 -- PROJECT OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════

MERMAID_DIAGRAM = """
flowchart TD
    User([User Question]) --> API[FastAPI /query]
    API --> Cache{Redis Semantic Cache}
    Cache -- HIT similarity >= 0.75 --> Return1([Cached Answer - cost 0])
    Cache -- MISS --> Agent
    subgraph Agent [LangGraph ReAct Agent]
        direction TB
        LLM[Groq LLM - Llama 3.3 70B] -->|tool_calls| Router{Tool Router}
        Router --> SQL[execute_sql - Tool 1]
        Router --> Vector[search_vector_db - Tool 2]
        SQL --> SQLite[(SQLite DB)]
        Vector --> Qdrant[(Qdrant Vector DB)]
        SQL --> LLM
        Vector --> LLM
        LLM -->|no tool_calls| Answer([Final Answer])
    end
    Agent --> FinOps[FinOps Logger]
    FinOps --> Store[Store in Cache]
    Store --> Return2([API Response JSON])
    subgraph ETL [Phase 1 - Vector ETL Pipeline]
        direction LR
        PDFs[14 x 10-K PDFs] --> Extract[extract_pdfs.py]
        Extract --> Chunk[Semantic Chunking]
        Chunk --> Embed[all-MiniLM-L6-v2]
        Embed --> Upsert[ingest.py]
        Upsert --> Qdrant
    end
"""

if page == "📋 Project Overview":
    st.title("🏢 Enterprise AI Data Analyst")
    st.markdown(
        """
        A production-grade **Multi-Modal Enterprise Agent** that answers complex business questions
        by combining structured SQL queries and semantic vector search over 14 corporate 10-K reports.

        Built with **LangGraph**, **Qdrant**, **FastAPI** and **Groq (Llama 3.3 70B)**.
        Includes a **Redis semantic cache** (Advanced Option 2).
        """
    )

    st.markdown("---")

    # The problem
    st.subheader("The Business Problem")
    st.info(
        "**Example question:**\n\n"
        "> *What was Apple's total revenue in 2023, and what did their annual report say "
        "about supply chain risks?*\n\n"
        "A standard LLM cannot answer this. It requires **querying a database AND reading a "
        "200-page PDF simultaneously**. This agent does both autonomously."
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("PDF Reports", "14", "Apple · Tesla · Microsoft")
    col2.metric("Financial KPIs", "5 metrics", "2021 – 2025")
    col3.metric("LLM", "Llama 3.3 70B", "via Groq API")

    st.markdown("---")

    # Database contant
    
    st.subheader("⚠️ What the Vector DB Actually Contains")
    st.warning(
        "The ingested PDF documents currently contain **only the cover pages** "
        "of the SEC 10-K annual reports. This means vector search is limited to "
        "the following information:"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
    **✅ Available in Vector DB**
    | Info |
    |---|
    | Years ingested |
    | Legal name |
    | IRS number |
    | State of incorporation |
    | HQ address |
    | Phone number |
    | Fiscal year end |
    | Stock ticker |
    """)

    with col2:
        st.markdown("""
    **❌ NOT always available in Vector DB**
    - Gross profit / Revenue figures
    - Supply chain risk discussion
    - Hardware revenue strategy
    - AI investment details
    - R&D expense breakdown
    - Any narrative content from the report body

    > These figures come exclusively from the **SQLite database** (structured data).
    """)

    st.info(
        "💡 **Tip for best results:** Questions about **numbers and financials** "
        "Questions about **cover page details** (HQ address, phone number, stock ticker, fiscal year end) work best. "
        "Questions requiring **narrative content** from the PDF body "
        "will return limited results."
    )
    
    st.markdown("---")

    # Architecture diagram via Mermaid
    st.subheader("System Architecture")
    mermaid_html = f"""
    <html>
    <head>
      <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
      <script>mermaid.initialize({{ startOnLoad: true, theme: 'default' }});</script>
    </head>
    <body style="background:white; padding:10px;">
      <div class="mermaid">
{MERMAID_DIAGRAM}
      </div>
    </body>
    </html>
    """
    st.components.v1.html(mermaid_html, height=900, scrolling=False)

    st.markdown("---")

    # Tech stack
    st.subheader("Technology Stack")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
| Component | Technology |
|---|---|
| Agent Framework | LangGraph (ReAct loop) |
| LLM | Groq / Llama 3.3 70B |
| Vector Database | Qdrant (Docker) |
| Embedding Model | all-MiniLM-L6-v2 |
| SQL Database | SQLite |
""")
    with col2:
        st.markdown("""
| Component | Technology |
|---|---|
| API | FastAPI (REST) |
| Semantic Cache | Redis + cosine similarity |
| Deployment | Google Cloud Run |
| Chunking | Semantic (paragraph + sentence) |
| Vectors | Hybrid dense + sparse (TF-IDF) |
""")

    st.markdown("---")

    # Dataset
    st.subheader("Dataset")
    st.markdown("""
| Company | Years | Reports |
|---|---|---|
| 🍎 Apple | 2021, 2022, 2023, 2024, 2025 | 5 x 10-K |
| ⚡ Tesla | 2022, 2023, 2024, 2025 | 4 x 10-K |
| 🪟 Microsoft | 2021, 2022, 2023, 2024, 2025 | 5 x 10-K |
""")

    st.markdown("---")

    # Advanced option
    st.subheader("Advanced Option 2 — Semantic Cache (Redis)")
    st.markdown("""
If User B asks a question with **≥ 0.75 cosine similarity** to a question User A asked previously,
the agent is bypassed entirely — the cached answer is returned **instantly at $0 cost**.

| Scenario | Latency | Cost |
|---|---|---|
| Cache MISS (first query) | ~1–5 seconds | ~$0.0002 |
| Cache HIT | < 50 ms | $0.0000 |
""")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 -- CHAT WITH THE AGENT
# ══════════════════════════════════════════════════════════════════════════════

elif page == "💬 Chat with the Agent":
    st.title("💬 Chat with the Agent")
    st.caption(
        "Ask any question about Apple, Tesla, or Microsoft financials. "
        "The agent queries the SQL database and/or the PDF vector store automatically."
    )

    # Initialise session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "total_cost" not in st.session_state:
        st.session_state.total_cost = 0.0
    if "prefill" not in st.session_state:
        st.session_state.prefill = ""

    # Example questions
    with st.expander("💡 Example questions — click to use", expanded=True):
        examples = [
            "What was Apple's total revenue in 2023?",
            "Compare Microsoft's net income between 2022 and 2023.",
            "What did Tesla say about supply chain risks in their 2023 report?",
            "Which company had the highest R&D expenses in 2023?",
            "What was Apple's gross profit in 2024?",
        ]
        cols = st.columns(len(examples))
        for col, ex in zip(cols, examples):
            if col.button(ex[:35] + "...", key=f"btn_{ex}", help=ex):
                st.session_state.prefill = ex

    st.markdown("---")

    # Chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("meta"):
                meta = msg["meta"]
                badge = "  ⚡ *Cache HIT*" if meta.get("cache_hit") else ""
                st.caption(f"Cost: `${meta['cost']:.6f}` | Latency: `{meta['latency']}s`{badge}")

    # Input — use prefill if a button was clicked
    user_input = st.chat_input("Ask a question about Apple, Tesla, or Microsoft...")
    if not user_input and st.session_state.prefill:
        user_input = st.session_state.prefill
        st.session_state.prefill = ""

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Agent is thinking..."):
                try:
                    resp = requests.post(
                        f"{API_URL}/query",
                        json={"question": user_input},
                        timeout=120,
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        answer = data["answer"]
                        cost = data.get("token_cost_usd", 0.0)
                        latency = data.get("latency_seconds", 0.0)
                        cache_hit = cost == 0.0 and latency < 0.5
                        st.session_state.total_cost += cost

                        st.markdown(answer)
                        badge = "  ⚡ *Cache HIT*" if cache_hit else ""
                        st.caption(f"Cost: `${cost:.6f}` | Latency: `{latency}s`{badge}")

                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                            "meta": {"cost": cost, "latency": latency, "cache_hit": cache_hit},
                        })
                    else:
                        st.error(f"API error {resp.status_code}: {resp.text[:300]}")

                except requests.exceptions.ConnectionError:
                    st.error(
                        f"Cannot connect to `{API_URL}`.  \n"
                        "Start the API with `uvicorn phase3_deployment.api:app --port 8080`  \n"
                        "or set `API_URL` in your `.env` to your Cloud Run URL."
                    )
                except requests.exceptions.Timeout:
                    st.error("Request timed out after 120 seconds.")
                except Exception as e:
                    st.error(f"Unexpected error: {e}")

        st.rerun()

    # Session stats footer
    if st.session_state.messages:
        st.markdown("---")
        n_queries = len([m for m in st.session_state.messages if m["role"] == "user"])
        col1, col2, col3 = st.columns([1, 1, 2])
        col1.metric("Queries sent", n_queries)
        col2.metric("Session cost", f"${st.session_state.total_cost:.6f}")
        with col3:
            if st.button("🗑️ Clear conversation"):
                st.session_state.messages = []
                st.session_state.total_cost = 0.0
                st.rerun()
