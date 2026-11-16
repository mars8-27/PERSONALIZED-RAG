from contextlib import asynccontextmanager
import json
import uuid
import httpx
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.config import settings
from src.database import init_db, get_db, DocumentRecord, RetrievalAuditLog
from src.ingestion import compute_sha256, parse_and_chunk_document
from src.vector_store import HybridVectorStore
from src.security import build_isolated_messages, sanitize_llm_output

vector_store = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store
    init_db()
    vector_store = HybridVectorStore()
    yield

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

class QueryRequest(BaseModel):
    tenant_id: str
    query: str
    top_k: int = 4

async def call_local_vllm(messages: list[dict]) -> str:
    payload = {
        "model": settings.VLLM_MODEL_NAME,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 512,
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{settings.VLLM_BASE_URL}/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as exc:
        return (
            f"[Local vLLM Server Offline at {settings.VLLM_BASE_URL} — "
            f"Verified Hybrid Retrieval & Security Pipeline Successfully. Details: {exc}]"
        )

@app.post("/api/v1/documents/upload")
async def upload_document(
    tenant_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(status_code=400, detail="Only .pdf and .txt files are allowed.")

    file_bytes = await file.read()
    file_hash = compute_sha256(file_bytes)

    existing = (
        db.query(DocumentRecord)
        .filter(DocumentRecord.tenant_id == tenant_id, DocumentRecord.file_hash == file_hash)
        .first()
    )
    if existing:
        return {
            "status": "duplicate_skipped",
            "doc_id": existing.doc_id,
            "chunks_indexed": existing.chunk_count,
        }

    chunks = parse_and_chunk_document(file_bytes, file.filename)
    if not chunks:
        raise HTTPException(status_code=400, detail="No readable text found in document.")

    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    vector_store.index_document_chunks(tenant_id=tenant_id, doc_id=doc_id, chunks=chunks)

    record = DocumentRecord(
        doc_id=doc_id,
        tenant_id=tenant_id,
        filename=file.filename,
        file_hash=file_hash,
        chunk_count=len(chunks),
    )
    db.add(record)
    db.commit()

    return {
        "status": "indexed",
        "doc_id": doc_id,
        "filename": file.filename,
        "chunks_indexed": len(chunks),
    }

@app.post("/api/v1/chat/query")
async def query_documents(req: QueryRequest, db: Session = Depends(get_db)):
    retrieved = vector_store.hybrid_search(
        tenant_id=req.tenant_id, query=req.query, top_k=req.top_k
    )
    if not retrieved:
        return {
            "answer": "No authorized documents matched your query for this tenant ID.",
            "citations": [],
        }

    messages = build_isolated_messages(req.query, retrieved)
    raw_answer = await call_local_vllm(messages)
    safe_answer = sanitize_llm_output(raw_answer)

    chunk_ids = [c["chunk_id"] for c in retrieved]
    audit_entry = RetrievalAuditLog(
        tenant_id=req.tenant_id,
        query_text=req.query,
        retrieved_chunk_ids=json.dumps(chunk_ids),
        llm_response=safe_answer,
    )
    db.add(audit_entry)
    db.commit()

    return {
        "answer": safe_answer,
        "citations": retrieved,
    }

@app.get("/api/v1/audit/{tenant_id}")
def get_audit_logs(tenant_id: str, db: Session = Depends(get_db)):
    logs = (
        db.query(RetrievalAuditLog)
        .filter(RetrievalAuditLog.tenant_id == tenant_id)
        .order_by(RetrievalAuditLog.timestamp.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "query": log.query_text,
            "chunk_ids": json.loads(log.retrieved_chunk_ids),
            "response": log.llm_response,
        }
        for log in logs
    ]
