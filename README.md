# PERSONALIZED-RAG (VaultRAG): Air-Gapped Hybrid RAG & Compliance Engine

![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)
![Qdrant](https://img.shields.io/badge/Qdrant-Hybrid_Search-dc244c.svg)
![Security](https://img.shields.io/badge/Security-Defense_in_Depth-success.svg)
![Tests](https://img.shields.io/badge/Tests-Pytest_Passing-brightgreen.svg)

**PERSONALIZED-RAG (VaultRAG)** is a 100% local, zero-data-egress Retrieval-Augmented Generation (RAG) platform engineered for strict data privacy, multi-tenant access control, and defense-in-depth LLM security. Built without reliance on external third-party APIs, it combines dense semantic embeddings with deterministic sparse keyword vectors via **Reciprocal Rank Fusion (RRF)** and logs every retrieval event in an immutable **SQLite** audit trail.

---

## System Architecture

~~~text
+-------------------------------------------------------------------------+
|                        GRADIO WEB DASHBOARD (src/ui.py)                 |
|  [Tenant ACL Switcher]   [PDF/TXT Upload]   [Hybrid Chat & Audit View]  |
+------------------------------------+------------------------------------+
                                     | HTTP REST (127.0.0.1:8000)
                                     v
+-------------------------------------------------------------------------+
|                    FASTAPI ORCHESTRATOR (src/main.py)                   |
+-----------------+------------------+------------------+-----------------+
                  |                  |                  |
     1. Ingest    v     2. Retrieve  v     3. Isolate   v    4. Audit
+-----------------+--+ +-------------+----+ +-----------+--+ +------------+
|  src/ingestion.py  | |src/vector_store  | |src/security  | |src/database|
| - SHA-256 Dedupe   | |- BGE Dense Vecs  | |- NFKC Clean  | |- SQLAlchemy|
| - PyMuPDF / pypdf  | |- CRC32 Sparse Vec| |- XML Isolate | |- Document  |
| - Sliding Window   | |- Mandatory Tenant| |- Exfiltration| |  Registry  |
|   Chunker          | |  Pre-Filter ACL  | |  Image Block | |- Compliance|
|                    | |- Qdrant RRF      | |              | |  Audit Log |
+--------------------+ +------------------+ +--------------+ +------------+
~~~

---

## Core Engineering Highlights

1. **Zero-Trust Pre-Retrieval Multi-Tenancy (ACL)**
   Traditional file permissions disappear once documents are chunked into a vector database. This engine attaches `tenant_id` metadata to every vector payload and enforces mandatory pre-retrieval filtering inside Qdrant's `Prefetch` stages—guaranteeing Tenant A can never score or retrieve chunks belonging to Tenant B.
2. **Hybrid Vector Search with Reciprocal Rank Fusion (RRF)**
   Pure dense embeddings (`BAAI/bge-small-en-v1.5`) capture semantic meaning but frequently miss exact alphanumeric identifiers, invoice codes, or legal clause numbers. The retrieval layer computes deterministic CRC32 term-frequency sparse vectors alongside dense embeddings and merges both rankings using Qdrant's native `Fusion.RRF`.
3. **Defense-in-Depth AI Security (`src/security.py`)**
   * **Ingestion Sanitization**: Normalizes Unicode (`NFKC`), strips invisible zero-width control characters (`\u200b`–`\u200f`) used to smuggle hidden prompts, and neutralizes embedded `<script>`/`<iframe>` tags.
   * **Indirect Prompt Injection Isolation**: Wraps untrusted document chunks in explicit `<untrusted_reference>` XML boundaries with system-level non-execution directives.
   * **Markdown Exfiltration Blocking**: Strips remote Markdown image tags (`![alt](http...)`) from LLM responses so poisoned documents cannot trigger browser tracking pixels to leak data.
4. **Transactional Deduplication & Compliance Auditing (`src/database.py`)**
   Uses **SQLAlchemy ORM** and **SQLite** to block duplicate uploads via SHA-256 file hashing and records every user query alongside the exact Qdrant `chunk_id` list injected into the LLM context window.

---

## Tech Stack

| Layer | Technology | Role in Architecture |
| :--- | :--- | :--- |
| **Backend API** | FastAPI, Uvicorn, Pydantic | Asynchronous REST endpoints, request validation, and lifespan orchestration |
| **Vector Engine** | Qdrant (`qdrant-client`) | Hybrid vector storage (Dense Cosine + Sparse Term-Frequency) & RRF fusion |
| **Embeddings** | Sentence-Transformers (`BAAI/bge-small-en-v1.5`) | Local 384-dimensional normalized semantic embeddings |
| **Relational DB** | SQLite, SQLAlchemy 2.0 ORM | SHA-256 document deduplication registry and query-to-chunk compliance audit trail |
| **Document Parsing** | PyMuPDF (`fitz`), `pypdf` | High-speed local PDF text extraction and sliding-window chunking |
| **LLM Inference** | vLLM / Ollama (`httpx` AsyncClient) | Local OpenAI-compatible inference with graceful offline verification fallback |
| **Frontend UI** | Gradio | Interactive multi-tenant testing workspace and live citation inspector |
| **Testing** | Pytest | Automated verification of Unicode sanitization, XML isolation, and exfiltration blocking |

---

## Repository Structure

~~~text
PERSONALIZED-RAG/
├── docker-compose.yml            # Production container orchestration for Qdrant & vLLM
├── requirements.txt              # Python package dependencies
├── README.md                     # Portfolio overview & quickstart
├── PROJECT_HANDBOOK.md           # Deep-dive engineering manual & interview reference
├── sample_enterprise_policy.txt  # Sample document with test prompt injection payload
├── src/
│   ├── __init__.py               # Package initializer
│   ├── config.py                 # Environment-driven configuration & model settings
│   ├── database.py               # SQLAlchemy ORM models (DocumentRecord, RetrievalAuditLog)
│   ├── security.py               # Sanitization, XML prompt isolation & output filtering
│   ├── ingestion.py              # SHA-256 hashing, PDF/TXT parsing & sliding-window chunker
│   ├── vector_store.py           # Qdrant Hybrid Search (Dense + CRC32 Sparse + RRF + ACL)
│   ├── main.py                   # FastAPI endpoints & async local LLM client
│   └── ui.py                     # Gradio web dashboard for live testing & audit inspection
└── tests/
    └── test_security.py          # Pytest suite verifying security boundaries
~~~

---

## Quickstart Guide

### 1. Clone & Set Up Environment
~~~powershell
git clone https://github.com/mars8-27/PERSONALIZED-RAG.git
cd PERSONALIZED-RAG
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --prefer-binary -r requirements.txt
~~~

### 2. Run the Automated Security Test Suite
~~~powershell
python -m pytest tests/test_security.py -v
~~~

### 3. Launch the Platform
Open two terminals in the project root with `.venv` activated:

**Terminal 1 — Start FastAPI Backend:**
~~~powershell
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
~~~

**Terminal 2 — Start Gradio Dashboard:**
~~~powershell
python -m src.ui
~~~

* **Gradio Web UI**: `http://127.0.0.1:7860`
* **Interactive Swagger API Docs**: `http://127.0.0.1:8000/docs`
