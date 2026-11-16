import os

class Settings:
    PROJECT_NAME: str = "VaultRAG - Air-Gapped Enterprise RAG"
    SQLITE_URL: str = os.getenv("SQLITE_URL", "sqlite:///./vaultrag_meta.db")
    QDRANT_URL: str = os.getenv("QDRANT_URL", "")
    QDRANT_LOCAL_PATH: str = os.getenv("QDRANT_LOCAL_PATH", "./qdrant_storage")
    COLLECTION_NAME: str = "vaultrag_hybrid_chunks"

    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIM: int = 384

    VLLM_BASE_URL: str = os.getenv("VLLM_BASE_URL", "http://localhost:8001/v1")
    VLLM_MODEL_NAME: str = os.getenv("VLLM_MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct")

settings = Settings()
