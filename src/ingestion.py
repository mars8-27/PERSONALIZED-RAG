import hashlib
import io
from src.security import sanitize_ingested_text

def compute_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()

def parse_and_chunk_document(
    file_bytes: bytes, filename: str, chunk_size: int = 600, overlap: int = 120
) -> list[dict]:
    pages_text = []

    if filename.lower().endswith(".pdf"):
        try:
            import fitz
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                for page_index, page in enumerate(doc):
                    clean_page = sanitize_ingested_text(page.get_text("text"))
                    if clean_page:
                        pages_text.append((page_index + 1, clean_page))
        except ImportError:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            for page_index, page in enumerate(reader.pages):
                clean_page = sanitize_ingested_text(page.extract_text() or "")
                if clean_page:
                    pages_text.append((page_index + 1, clean_page))
    else:
        raw_str = file_bytes.decode("utf-8", errors="ignore")
        clean_text = sanitize_ingested_text(raw_str)
        if clean_text:
            pages_text.append((1, clean_text))

    chunks = []
    chunk_index = 0
    for page_num, text in pages_text:
        start = 0
        text_length = len(text)
        while start < text_length:
            end = min(start + chunk_size, text_length)
            snippet = text[start:end].strip()
            if snippet:
                chunks.append({
                    "chunk_index": chunk_index,
                    "page": page_num,
                    "text": snippet,
                })
                chunk_index += 1
            if end == text_length:
                break
            start += chunk_size - overlap

    return chunks
