import re
import uuid
import zlib
from collections import Counter
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from src.config import settings

class HybridVectorStore:
    def __init__(self):
        if settings.QDRANT_URL:
            self.client = QdrantClient(url=settings.QDRANT_URL)
        else:
            self.client = QdrantClient(path=settings.QDRANT_LOCAL_PATH)
        self.encoder = SentenceTransformer(settings.EMBEDDING_MODEL)
        self._ensure_collection()

    def _ensure_collection(self):
        collections = [c.name for c in self.client.get_collections().collections]
        if settings.COLLECTION_NAME not in collections:
            self.client.create_collection(
                collection_name=settings.COLLECTION_NAME,
                vectors_config={
                    "dense": models.VectorParams(
                        size=settings.EMBEDDING_DIM,
                        distance=models.Distance.COSINE,
                    )
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(
                        index=models.SparseIndexParams(on_disk=False)
                    )
                },
            )

    @staticmethod
    def _compute_sparse_vector(text: str) -> models.SparseVector:
        tokens = re.findall(r"\b\w+\b", text.lower())
        counts = Counter(tokens)
        hash_map = {}
        for token, count in counts.items():
            idx = zlib.crc32(token.encode("utf-8")) & 0x7FFFFFFF
            hash_map[idx] = hash_map.get(idx, 0.0) + float(count)

        indices = sorted(hash_map.keys())
        values = [hash_map[idx] for idx in indices]
        return models.SparseVector(indices=indices, values=values)

    def index_document_chunks(self, tenant_id: str, doc_id: str, chunks: list[dict]):
        points = []
        texts = [c["text"] for c in chunks]
        dense_vectors = self.encoder.encode(texts, normalize_embeddings=True).tolist()

        for chunk, dense_vec in zip(chunks, dense_vectors):
            chunk_uid = f"{doc_id}_c{chunk['chunk_index']}"
            point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_uid))
            sparse_vec = self._compute_sparse_vector(chunk["text"])

            points.append(
                models.PointStruct(
                    id=point_uuid,
                    vector={"dense": dense_vec, "sparse": sparse_vec},
                    payload={
                        "chunk_id": chunk_uid,
                        "tenant_id": tenant_id,
                        "doc_id": doc_id,
                        "page": chunk["page"],
                        "text": chunk["text"],
                    },
                )
            )

        self.client.upsert(collection_name=settings.COLLECTION_NAME, points=points)

    def hybrid_search(self, tenant_id: str, query: str, top_k: int = 4) -> list[dict]:
        dense_query = self.encoder.encode(query, normalize_embeddings=True).tolist()
        sparse_query = self._compute_sparse_vector(query)

        acl_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="tenant_id",
                    match=models.MatchValue(value=tenant_id),
                )
            ]
        )

        response = self.client.query_points(
            collection_name=settings.COLLECTION_NAME,
            prefetch=[
                models.Prefetch(
                    query=dense_query,
                    using="dense",
                    filter=acl_filter,
                    limit=top_k * 3,
                ),
                models.Prefetch(
                    query=sparse_query,
                    using="sparse",
                    filter=acl_filter,
                    limit=top_k * 3,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )

        return [
            {
                "chunk_id": pt.payload["chunk_id"],
                "doc_id": pt.payload["doc_id"],
                "page": pt.payload["page"],
                "text": pt.payload["text"],
                "score": round(pt.score, 4),
            }
            for pt in response.points
        ]
