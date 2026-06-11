# Enterprise-AI-agent-Data-Analyst-
Multi-Modal Enterprise Agent—an autonomous AI analyst capable of answering complex business questions by navigating both unstructured documents (PDFs/Reports) and structured relational databases (SQL).

## Quick start for phase 1
- Put the source PDF reports in `data/raw`.
- Run `python phase1_etl/03_extract_pdfs.py` to inspect extraction and semantic chunking.
- Run `python phase1_etl/01_fake_ingest.py` to ingest the PDF chunks into Qdrant.
- Run `python phase1_etl/02_phase1_validation.py` to confirm retrieval with metadata filters.
