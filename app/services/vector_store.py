import logging
import os
from typing import Any, Dict, List

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Simple ChromaDB wrapper for storing and searching embeddings.
    """

    def __init__(self, persist_directory: str, collection_name: str = "hanbang_qa"):
        os.makedirs(persist_directory, exist_ok=True)
        self.persist_directory = persist_directory

        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"[VectorStore] Initialized at {persist_directory}")

    def add_documents(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        """Bulk insert documents and embeddings."""
        if not ids:
            return
        self.collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas)
        logger.info(f"[VectorStore] Added {len(ids)} documents")

    def search(self, query_embedding: List[float], top_k: int = 3) -> Dict[str, Any]:
        """Query similar documents."""
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

    def clear(self) -> None:
        """Remove all documents and recreate the collection."""
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection.name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("[VectorStore] Collection cleared")
