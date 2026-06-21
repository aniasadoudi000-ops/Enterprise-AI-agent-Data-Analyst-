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
  --region europe-west1 \
  --allow-unauthenticated \
  --min-instances=0 \
  --timeout=300 \
  --cpu=2 \
  --memory=2Gi \
  --set-env-vars GROQ_API_KEY=your_key,QDRANT_URL=your_qdrant_cloud_url,REDIS_URL=your_redis_url
```

---

## Streamlit UI

A two-page interactive UI is included (`streamlit_app.py`): a project overview page and a ChatGPT-style chat page that sends questions to the FastAPI endpoint.

### Run locally

```bash
# Make sure API_URL is set in your .env (local or Cloud Run)
streamlit run streamlit_app.py
```

### Deploy on Streamlit Community Cloud (free, always-on)

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Select your repo, branch `main`, and file `streamlit_app.py`
4. In **Secrets** (TOML format), add:
   ```toml
   API_URL = "Your API_URL"
   ```
5. Click **Deploy** — you get a public URL like `https://your-app.streamlit.app`

The Streamlit app runs on Streamlit's servers 24/7 and calls your Cloud Run API. No need to keep your computer on.

---

### Local evaluation (direct agent call)

Run the RAGAS-style evaluation script (5 test queries, calls the agent directly via LangGraph):

```bash
python phase4_report/evaluate.py
# → generates evaluation_results.json
```

### Cloud evaluation (HTTP against deployed endpoint)

Validates the full production stack end-to-end by sending the same 5 questions to the live Cloud Run URL:

```bash
# Set your deployed API URL
export API_URL=https://enterprise-ai-analyst-883304283246.europe-west1.run.app

python phase4_report/evaluate_cloud.py
# → generates phase4_report/cloud_evaluation_results.json
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
│   ├── evaluate.py             # RAGAS evaluation — local (5 test queries)
│   ├── evaluate_cloud.py       # RAGAS evaluation — HTTP against Cloud Run
│   └── REPORT.md               # Phase 4 architecture report
├── docker-compose.yml          # Qdrant + Redis services
├── Dockerfile                  # Root container
├── streamlit_app.py            # Two-page Streamlit UI
├── requirements.txt
├── .env.example
└── README.md
```

---

## Environment Variables

| Variable | Description |
|---|â€”|
| `GROQ_API_KEY` | Groq API key for Llama 3.3 70B inference |
| `QDRANT_URL` | Qdrant server URL (Qdrant Cloud URL or `http://localhost:6333`) |
| `REDIS_URL` | Redis URL for semantic cache (default: `redis://localhost:6379`) |
| `API_URL` | FastAPI endpoint used by Streamlit and `evaluate_cloud.py` (Cloud Run URL or `http://localhost:8080`) |


## Test the agent diretly hear 

Go to [enterprise-ai-analyst](https://dnkbzi5mm8wwwgbefgrake.streamlit.app)
## Collaboration

Projet réalisé en binôme avec Isaac Schama dans le cadre du cours GenAI. Contributions personnelles : conception de l'agent LangGraph (Phase 2), déploiement Cloud Run (Phase 3), cache sémantique Redis (option bonus), et correction de l'implémentation initiale de la Phase 1.
