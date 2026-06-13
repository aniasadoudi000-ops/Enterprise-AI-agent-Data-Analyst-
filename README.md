# Enterprise AI Data Analyst

A production-grade **Multi-Modal Enterprise Agent** that answers complex business questions by combining:
- **Structured SQL queries** against a local SQLite financial database
- **Semantic vector search** over 14 real corporate 10-K reports (Apple, Tesla, Microsoft 2021–2025)

Built with LangGraph, Qdrant, FastAPI, and Groq (Llama 3.3 70B). Includes a Redis semantic cache (Advanced Option 2).

---

## Architecture

```
User Question
     │
     ▼
[FastAPI /query]
     │
     ├─ Semantic Cache (Redis) ──► Cache HIT → instant answer
     │
     └─ Cache MISS
          │
          ▼
     [LangGraph ReAct Agent]
          │
          ├─ execute_sql ──────► SQLite financial_data.db
          │
          └─ search_vector_db ─► Qdrant (all-MiniLM-L6-v2 embeddings)
                                      └─ 14 PDF 10-K reports
```

---

## Prerequisites

- Python 3.11+
- Docker Desktop (for Qdrant + Redis)
- A [Groq API key](https://console.groq.com/) (free tier available)

---

## Setup

### 1. Clone and install dependencies

```bash
git clone <your-repo-url>
cd Enterprise-AI-agent-Data-Analyst-
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in your GROQ_API_KEY
```

### 3. Start Docker services (Qdrant + Redis)

```bash
docker-compose up -d
```

Verify: Qdrant dashboard at http://localhost:6333/dashboard

---

## Phase 1 — Vector ETL Pipeline

Ingests 14 corporate 10-K PDFs into Qdrant with semantic chunking and metadata.

```bash
# (Optional) Inspect extraction and chunking on a single file
python phase1_etl/extract_pdfs.py

# Ingest all PDFs into Qdrant
python phase1_etl/ingest.py

# Validate semantic search with metadata filters
python phase1_etl/phase1_validation.py
```

Expected output: `Inserted N PDF chunks into Qdrant.`

---

## Phase 2 — LangGraph Agent

Run the agent interactively from the command line:

```bash
python phase2_agent/agent.py
```

The agent will answer 3 sample queries covering SQL, vector search, and multi-tool synthesis.

---

## Phase 3 — FastAPI Deployment

### Run locally

```bash
# 1. Create the SQLite database first
python database/create_db.py

# 2. Start the API server
uvicorn phase3_deployment.api:app --host 0.0.0.0 --port 8080 --reload
```

API docs available at http://localhost:8080/docs

### Example query

```bash
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What was Apple revenue in 2023 and what did they say about supply chain risks?"}'
```

### Build and run with Docker

```bash
docker build -t enterprise-ai-analyst .
docker run -p 8080:8080 \
  -e GROQ_API_KEY=your_key \
  -e QDRANT_URL=http://host.docker.internal:6333 \
  enterprise-ai-analyst
```

### Deploy to Google Cloud Run

```bash
# Authenticate and set project
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Build and push to Artifact Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/enterprise-ai-analyst

# Deploy to Cloud Run
gcloud run deploy enterprise-ai-analyst \
  --image gcr.io/YOUR_PROJECT_ID/enterprise-ai-analyst \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GROQ_API_KEY=your_key,QDRANT_URL=your_qdrant_url
```

---

## Phase 4 — Evaluation

Run the RAGAS-style evaluation script (5 test queries):

```bash
python phase4_report/evaluate.py
```

See `phase4_report/REPORT.md` for the full architecture report, evaluation results, and cost analysis.

---

## Project Structure

```
├── data/raw/                   # 14 corporate 10-K PDF reports
├── database/
│   └── create_db.py            # Creates SQLite financial database
├── phase1_etl/
│   ├── extract_pdfs.py         # PDF parsing and semantic chunking
│   ├── ingest.py               # Embeds and loads chunks into Qdrant
│   └── phase1_validation.py    # Validates retrieval with metadata filters
├── phase2_agent/
│   ├── agent.py                # LangGraph ReAct agent (SQL + Vector tools)
│   └── semantic_cache.py       # Redis semantic cache (Advanced Option 2)
├── phase3_deployment/
│   ├── api.py                  # FastAPI REST endpoint
│   └── Dockerfile              # Container for Cloud Run
├── phase4_report/
│   ├── evaluate.py             # RAGAS evaluation (5 test queries)
│   └── REPORT.md               # Phase 4 architecture report
├── docker-compose.yml          # Qdrant + Redis services
├── Dockerfile                  # Root container
├── requirements.txt
├── .env.example
└── README.md
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Groq API key for Llama 3.3 70B inference |
| `QDRANT_URL` | Qdrant server URL (default: `http://localhost:6333`) |
| `REDIS_URL` | Redis URL for semantic cache (default: `redis://localhost:6379`) |
