# Phase 1 — Vector ETL Pipeline

## Goal
Parse and embed 14 real corporate 10-K PDFs (Apple, Tesla, Microsoft 2021–2025) into a Qdrant vector database with structured metadata, using semantic chunking and hybrid dense + sparse vectors.

## Steps

1. Start Qdrant locally (from the project root):
   ```bash
   docker-compose up -d
   ```

2. Run the ingestion pipeline:
   ```bash
   python phase1_etl/ingest.py
   ```
   This loads `extract_pdfs.py`, chunks all PDFs semantically (paragraph + sentence boundaries), embeds them with `all-MiniLM-L6-v2`, and upserts dense + sparse vectors into Qdrant.

3. Validate the pipeline:
   ```bash
   python phase1_etl/phase1_validation.py
   ```

## What to verify
- The Qdrant collection `financial_reports` contains chunks from all PDF reports.
- Returned results match the query text and the metadata filter (`company`, `year`).
- Each chunk retains: `company`, `year`, `source_file`, `source_page`, `chunk_id`.

## Files
| File | Role |
|---|---|
| `extract_pdfs.py` | PDF parsing, text cleaning, semantic chunking |
| `ingest.py` | Qdrant collection creation, embedding, upsert |
| `phase1_validation.py` | End-to-end retrieval smoke test |
