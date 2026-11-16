@echo off
echo ===================================================
echo VaultRAG / PERSONALIZED-RAG Startup Sequence
echo ===================================================

echo [1/2] Starting FastAPI Backend on Port 8000...
start "VaultRAG Backend (FastAPI)" cmd /c ".\.venv\Scripts\activate & python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 & pause"

echo Waiting 5 seconds for the embedding model to load...
timeout /t 5 /nobreak > NUL

echo [2/2] Starting Gradio UI on Port 7860...
start "VaultRAG UI (Gradio)" cmd /c ".\.venv\Scripts\activate & python -m src.ui & pause"

echo Servers launched in separate windows! You can close this window.
