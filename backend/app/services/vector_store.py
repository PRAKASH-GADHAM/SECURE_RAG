"""Vector store service.

Handles ChromaDB operations for storing and retrieving document embeddings.
Provides user-scoped namespaces for multi-tenant isolation.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import Optional
from dataclasses import dataclass

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class VectorSearchResult:
    """Result from vector similarity search."""

    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict


class VectorStore:
    """Service for ChromaDB vector operations.

    Provides user-scoped collections for multi-tenant document isolation.
    Scores are normalized to [0, 1] where 1 is most similar.
    """

    def __init__(self):
        """Initialize the vector store client."""
        self._client = None
        self._collections: dict[str, chromadb.Collection] = {}

    @property
    def client(self) -> chromadb.ClientAPI:
        """Get or create the ChromaDB client.

        Clears stale collection cache on reconnect.
        """
        if self._client is None:
            logger.info(
                f"Connecting to ChromaDB: {settings.CHROMA_HOST}:{settings.CHROMA_PORT}"
            )
            self._client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
            )
            # Clear stale collections when reconnecting
            self._collections.clear()
            logger.info("ChromaDB client connected")
        return self._client

    def _get_user_collection(self, user_id: str) -> chromadb.Collection:
        """Get or create a collection for a specific user.

        Args:
            user_id: User ID for namespace isolation.

        Returns:
            ChromaDB collection for the user.
        """
        collection_name = f"user_{user_id}_documents"

        if collection_name not in self._collections:
            self._collections[collection_name] = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )

        return self._collections[collection_name]

    @staticmethod
    def _normalize_score(distance: float) -> float:
        """Normalize ChromaDB distance to a similarity score in [0, 1].

        ChromaDB with cosine distance returns values in [0, 2]:
        - 0 = identical vectors
        - 1 = orthogonal vectors
        - 2 = opposite vectors

        Maps to [1, 0] similarity, clamped to [0, 1].

        Args:
            distance: Raw ChromaDB distance value.

        Returns:
            Similarity score in [0, 1], higher = more similar.
        """
        score = 1.0 - (distance / 2.0)
        return max(0.0, min(1.0, score))

    def add_chunks(
        self,
        user_id: str,
        document_id: str,
        chunk_ids: list[str],
        contents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> int:
        """Add document chunks to the vector store.

        Args:
            user_id: User ID for namespace isolation.
            document_id: Document ID.
            chunk_ids: List of chunk IDs.
            contents: List of chunk text contents.
            embeddings: List of embedding vectors.
            metadatas: List of metadata dictionaries.

        Returns:
            Number of chunks added.
        """
        if not chunk_ids:
            return 0

        collection = self._get_user_collection(user_id)

        # Ensure all metadata values are strings (ChromaDB requirement)
        sanitized_metadatas = []
        for meta in metadatas:
            sanitized = {}
            for k, v in meta.items():
                if v is None:
                    sanitized[k] = ""
                elif isinstance(v, (list, dict)):
                    sanitized[k] = str(v)
                else:
                    sanitized[k] = v
            sanitized_metadatas.append(sanitized)

        # Add in batches to handle large documents
        batch_size = 100
        total_added = 0
        for i in range(0, len(chunk_ids), batch_size):
            end_idx = min(i + batch_size, len(chunk_ids))
            collection.add(
                ids=chunk_ids[i:end_idx],
                documents=contents[i:end_idx],
                embeddings=embeddings[i:end_idx],
                metadatas=sanitized_metadatas[i:end_idx],
            )
            total_added += end_idx - i

        logger.info(
            f"Added {total_added} chunks to vector store: "
            f"user={user_id}, doc={document_id}"
        )

        return total_added

    def search(
        self,
        user_id: str,
        query_embedding: list[float],
        top_k: int = 5,
        document_ids: Optional[list[str]] = None,
    ) -> list[VectorSearchResult]:
        """Search for similar chunks in the vector store.

        Args:
            user_id: User ID for namespace isolation.
            query_embedding: Query embedding vector.
            top_k: Number of results to return.
            document_ids: Optional filter by document IDs.

        Returns:
            List of search results sorted by similarity score (descending).
        """
        collection = self._get_user_collection(user_id)

        # Build where filter if document IDs provided
        where = None
        if document_ids:
            if len(document_ids) == 1:
                where = {"document_id": document_ids[0]}
            else:
                where = {"document_id": {"$in": document_ids}}

        try:
            # Request extra results for reranking headroom
            query_k = min(top_k * 2, collection.count()) if collection.count() > 0 else top_k
            query_k = max(query_k, top_k)

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=query_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

        # Parse and normalize results
        search_results = []
        if results and results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                score = self._normalize_score(distance)

                search_results.append(
                    VectorSearchResult(
                        chunk_id=chunk_id,
                        document_id=results["metadatas"][0][i].get("document_id", ""),
                        content=results["documents"][0][i] if results["documents"] else "",
                        score=score,
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    )
                )

        # Sort by score descending and return top_k
        search_results.sort(key=lambda r: r.score, reverse=True)
        search_results = search_results[:top_k]

        logger.info(
            f"Vector search: user={user_id}, results={len(search_results)}, "
            f"top_score={search_results[0].score:.4f}" if search_results else
            f"Vector search: user={user_id}, results=0"
        )

        return search_results

    def delete_document(self, user_id: str, document_id: str) -> int:
        """Delete all chunks for a document from the vector store.

        Args:
            user_id: User ID for namespace isolation.
            document_id: Document ID to delete.

        Returns:
            Number of chunks deleted.
        """
        collection = self._get_user_collection(user_id)

        # Find all chunks for this document
        try:
            results = collection.get(
                where={"document_id": document_id},
                include=["metadatas"],
            )
        except Exception as e:
            logger.warning(f"Failed to query chunks for deletion: {e}")
            return 0

        if results and results["ids"]:
            chunk_ids = results["ids"]
            collection.delete(ids=chunk_ids)
            logger.info(
                f"Deleted {len(chunk_ids)} chunks from vector store: "
                f"user={user_id}, doc={document_id}"
            )
            return len(chunk_ids)

        return 0

    def delete_user_collection(self, user_id: str) -> bool:
        """Delete all data for a user.

        Args:
            user_id: User ID.

        Returns:
            True if deleted.
        """
        collection_name = f"user_{user_id}_documents"
        try:
            self.client.delete_collection(collection_name)
            self._collections.pop(collection_name, None)
            logger.info(f"Deleted user collection: {collection_name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete collection {collection_name}: {e}")
            return False

    def get_collection_stats(self, user_id: str) -> dict:
        """Get statistics for a user's collection.

        Args:
            user_id: User ID.

        Returns:
            Dictionary with collection statistics.
        """
        collection = self._get_user_collection(user_id)
        count = collection.count()

        return {
            "user_id": user_id,
            "total_chunks": count,
            "collection_name": f"user_{user_id}_documents",
        }


# Module-level instance
vector_store = VectorStore()
