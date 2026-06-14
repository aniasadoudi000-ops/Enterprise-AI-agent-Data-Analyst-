import re
from pathlib import Path
from typing import Dict, List

import pdfplumber

DATA_RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
DEFAULT_CHUNK_SIZE = 1500
DEFAULT_CHUNK_OVERLAP = 200


def extract_company_and_year(filename: str) -> tuple[str, int]:
    """Extract company name and year from a filename like apple_10k_2021.pdf."""
    match = re.match(r"(?P<company>[a-zA-Z]+)_10k_(?P<year>\d{4})\.pdf$", filename)
    if not match:
        raise ValueError(f"Unexpected file name format: {filename}")

    company = match.group("company").capitalize()
    year = int(match.group("year"))
    return company, year


def clean_text(text: str) -> str:
    """Normalize whitespace so chunking works on cleaner text."""
    text = text.replace("\x00", " ")
    text = re.sub(r"-\n", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pages_from_pdf(pdf_path: str) -> List[Dict[str, str]]:
    """Extract cleaned text page by page from a PDF."""
    pages: List[Dict[str, str]] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            page_text = clean_text(page_text)
            if page_text:
                pages.append({"page_number": page_number, "text": page_text})

    return pages


def split_paragraphs(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Split text into coarse semantic units using paragraph and sentence boundaries."""
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", text) if paragraph.strip()]
    chunks: List[str] = []
    current_chunk = ""

    def flush_chunk() -> None:
        nonlocal current_chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        current_chunk = ""

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            flush_chunk()
            sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", paragraph) if sentence.strip()]
            sentence_buffer = ""
            for sentence in sentences:
                candidate = f"{sentence_buffer} {sentence}".strip()
                if len(candidate) <= chunk_size:
                    sentence_buffer = candidate
                else:
                    if sentence_buffer:
                        chunks.append(sentence_buffer.strip())
                    sentence_buffer = sentence
            if sentence_buffer:
                chunks.append(sentence_buffer.strip())
            continue

        candidate = f"{current_chunk}\n\n{paragraph}".strip() if current_chunk else paragraph
        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            flush_chunk()
            current_chunk = paragraph

    flush_chunk()

    if chunk_overlap > 0 and len(chunks) > 1:
        overlapped_chunks: List[str] = []
        previous_tail = ""
        for chunk in chunks:
            if previous_tail:
                overlapped_chunks.append(f"{previous_tail}\n\n{chunk}".strip())
            else:
                overlapped_chunks.append(chunk)
            previous_tail = chunk[-chunk_overlap:]
        return overlapped_chunks

    return chunks


def chunk_text_semantically(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
    return split_paragraphs(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def extract_all_documents() -> List[Dict]:
    """Extract PDFs from data/raw and return chunk-level documents with metadata."""
    if not DATA_RAW_DIR.exists():
        raise RuntimeError(f"Directory {DATA_RAW_DIR} does not exist.")

    pdf_files = sorted(DATA_RAW_DIR.glob("*.pdf"))
    if not pdf_files:
        raise RuntimeError(f"No PDF files found in {DATA_RAW_DIR}")

    print(f"Found {len(pdf_files)} PDF files in {DATA_RAW_DIR}")
    print("Starting extraction and semantic chunking...\n")

    all_documents: List[Dict] = []

    for pdf_file in pdf_files:
        company, year = extract_company_and_year(pdf_file.name)
        print(f"Processing: {pdf_file.name}")

        pages = extract_pages_from_pdf(str(pdf_file))
        if not pages:
            print(f"  Skipping {pdf_file.name}: no extractable text found.\n")
            continue

        chunk_counter = 0
        for page in pages:
            chunks = chunk_text_semantically(page["text"])
            for chunk in chunks:
                all_documents.append(
                    {
                        "id": f"{company.lower()}_{year}_p{page['page_number']}_c{chunk_counter}",
                        "company": company,
                        "year": year,
                        "document_type": "10-K",
                        "source_file": pdf_file.name,
                        "source_page": page["page_number"],
                        "chunk_id": chunk_counter,
                        "text": chunk,
                        "char_count": len(chunk),
                    }
                )
                chunk_counter += 1

        print(f"  ✓ Extracted {chunk_counter} chunks from {pdf_file.name}\n")

    print(f"Total chunks extracted: {len(all_documents)}\n")
    return all_documents


if __name__ == "__main__":
    documents = extract_all_documents()

    if documents:
        sample = documents[0]
        print("Sample document:")
        print(f"  ID: {sample['id']}")
        print(f"  Company: {sample['company']}")
        print(f"  Year: {sample['year']}")
        print(f"  Type: {sample['document_type']}")
        print(f"  Source: {sample['source_file']}")
        print(f"  Page: {sample['source_page']}")
        print(f"  Chunk ID: {sample['chunk_id']}")
        print(f"  Text preview: {sample['text'][:200]}...")