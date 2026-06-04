"""Semantic memory backed by Qdrant + Bedrock Titan embeddings."""

from __future__ import annotations

import json
import uuid
from typing import Any

import boto3
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from .models import MemoryEntry

DEFAULT_EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
DEFAULT_EMBEDDING_DIM = 1024


class Memory:
    """Persistent semantic memory for an agent.

    Stores text entries with embeddings, retrieves them by similarity.
    Backend: Qdrant (in-memory or remote).
    """

    def __init__(
        self,
        collection_name: str,
        *,
        qdrant_url: str | None = None,
        qdrant_path: str | None = None,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        embedding_dim: int = DEFAULT_EMBEDDING_DIM,
        aws_region: str = "us-east-1",
        aws_profile: str | None = None,
    ) -> None:
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim

        # In-memory if neither URL nor path given (good for tests)
        if qdrant_url is None and qdrant_path is None:
            self.qdrant: QdrantClient = QdrantClient(":memory:")
        elif qdrant_path is not None:
            self.qdrant = QdrantClient(path=qdrant_path)
        else:
            self.qdrant = QdrantClient(url=qdrant_url)

        session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
        self._bedrock = session.client("bedrock-runtime")

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        existing = {c.name for c in self.qdrant.get_collections().collections}
        if self.collection_name in existing:
            return
        self.qdrant.create_collection(
            collection_name=self.collection_name,
            vectors_config=qdrant_models.VectorParams(
                size=self.embedding_dim,
                distance=qdrant_models.Distance.COSINE,
            ),
        )

    def _embed(self, text: str) -> list[float]:
        body = json.dumps({"inputText": text, "dimensions": self.embedding_dim})
        response = self._bedrock.invoke_model(
            modelId=self.embedding_model,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        embedding: list[float] = result["embedding"]
        return embedding

    def remember(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a memory entry, return its ID."""
        entry_id = str(uuid.uuid4())
        embedding = self._embed(text)
        payload = {"text": text, **(metadata or {})}
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[
                qdrant_models.PointStruct(
                    id=entry_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )
        return entry_id

    def recall(self, query: str, *, limit: int = 5) -> list[MemoryEntry]:
        """Retrieve top-N most similar memory entries."""
        embedding = self._embed(query)
        # Use query_points (modern API); falls back gracefully on older clients
        if hasattr(self.qdrant, "query_points"):
            response = self.qdrant.query_points(
                collection_name=self.collection_name,
                query=embedding,
                limit=limit,
            )
            hits = response.points
        else:
            hits = self.qdrant.search(  # type: ignore[attr-defined]
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=limit,
            )
        results: list[MemoryEntry] = []
        for hit in hits:
            payload = hit.payload or {}
            text = payload.pop("text", "")
            results.append(MemoryEntry(text=text, metadata=payload))
        return results

    def forget(self, entry_id: str) -> None:
        """Delete a memory entry by ID."""
        self.qdrant.delete(
            collection_name=self.collection_name,
            points_selector=qdrant_models.PointIdsList(points=[entry_id]),
        )
