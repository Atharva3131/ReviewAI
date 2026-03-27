"""Vector embedding model for semantic search and similarity"""

import enum
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import numpy as np
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ContentType(str, enum.Enum):
    """Content type for embeddings"""

    REVIEW = "review"
    SUPPORT_TICKET = "support_ticket"
    CUSTOMER_PROFILE = "customer_profile"
    RECOVERY_ACTION = "recovery_action"
    RESPONSE_TEMPLATE = "response_template"
    KNOWLEDGE_BASE = "knowledge_base"


class EmbeddingModel(str, enum.Enum):
    """Embedding model enumeration"""

    OPENAI_ADA_002 = "text-embedding-ada-002"
    OPENAI_3_SMALL = "text-embedding-3-small"
    OPENAI_3_LARGE = "text-embedding-3-large"
    SENTENCE_TRANSFORMERS = "sentence-transformers"
    CUSTOM = "custom"


class Embedding(Base):
    """Vector embedding model for semantic search and similarity matching"""

    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Content reference
    content_type = Column(Enum(ContentType), nullable=False, index=True)
    content_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Content snapshot (for reference)
    content_text = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash

    # Vector embedding (1536 dimensions for OpenAI ada-002)
    embedding = Column(Vector(1536), nullable=False)

    # Model information
    model_name = Column(Enum(EmbeddingModel), nullable=False, index=True)
    model_version = Column(String(50), nullable=True)
    embedding_dimensions = Column(Integer, default=1536, nullable=False)

    # Processing metadata
    processing_time_ms = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)

    # Usage tracking
    similarity_searches = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    organization = relationship("Organization", back_populates="embeddings")

    def __repr__(self):
        return f"<Embedding(id={self.id}, content_type='{self.content_type}', model='{self.model_name}')>"

    @property
    def embedding_vector(self) -> List[float]:
        """Get embedding as Python list"""
        if isinstance(self.embedding, list):
            return self.embedding
        elif hasattr(self.embedding, "tolist"):
            return self.embedding.tolist()
        else:
            return list(self.embedding)

    @property
    def embedding_array(self) -> np.ndarray:
        """Get embedding as numpy array"""
        return np.array(self.embedding_vector)

    @property
    def is_stale(self) -> bool:
        """Check if embedding might be stale (older than 30 days)"""
        from datetime import timedelta

        threshold = datetime.now(timezone.utc) - timedelta(days=30)
        return self.created_at < threshold

    def update_usage(self):
        """Update usage statistics"""
        self.similarity_searches += 1
        self.last_used_at = datetime.now(timezone.utc)

    def calculate_similarity(self, other_embedding: "Embedding") -> float:
        """Calculate cosine similarity with another embedding"""
        return self.cosine_similarity(
            self.embedding_array, other_embedding.embedding_array
        )

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    @staticmethod
    def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
        """Calculate Euclidean distance between two vectors"""
        return np.linalg.norm(a - b)

    def to_dict(self, include_vector: bool = False):
        """Convert to dictionary"""
        data = {
            "id": str(self.id),
            "organization_id": str(self.organization_id),
            "content_type": self.content_type.value,
            "content_id": str(self.content_id),
            "content_text": (
                self.content_text[:200] + "..."
                if len(self.content_text) > 200
                else self.content_text
            ),
            "content_hash": self.content_hash,
            "model_name": self.model_name.value,
            "model_version": self.model_version,
            "embedding_dimensions": self.embedding_dimensions,
            "processing_time_ms": self.processing_time_ms,
            "token_count": self.token_count,
            "similarity_searches": self.similarity_searches,
            "last_used_at": (
                self.last_used_at.isoformat() if self.last_used_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_stale": self.is_stale,
        }

        if include_vector:
            data["embedding"] = self.embedding_vector

        return data


class EmbeddingService:
    """Service class for embedding operations"""

    @staticmethod
    async def find_similar_embeddings(
        session,
        organization_id: str,
        query_embedding: List[float],
        content_type: ContentType = None,
        limit: int = 10,
        similarity_threshold: float = 0.7,
    ) -> List[Tuple[Embedding, float]]:
        """
        Find similar embeddings using cosine similarity
        Returns list of (embedding, similarity_score) tuples
        """
        from sqlalchemy import text

        # Build query
        query_parts = [
            "SELECT *, (embedding <=> :query_embedding) as distance",
            "FROM embeddings",
            "WHERE organization_id = :org_id",
        ]

        params = {"query_embedding": query_embedding, "org_id": organization_id}

        if content_type:
            query_parts.append("AND content_type = :content_type")
            params["content_type"] = content_type.value

        query_parts.extend(
            ["ORDER BY embedding <=> :query_embedding", f"LIMIT {limit}"]
        )

        query_sql = " ".join(query_parts)

        result = await session.execute(text(query_sql), params)
        rows = result.fetchall()

        # Convert to embeddings with similarity scores
        similar_embeddings = []
        for row in rows:
            # Convert distance to similarity (1 - distance for cosine)
            similarity = 1 - row.distance

            if similarity >= similarity_threshold:
                embedding = session.get(Embedding, row.id)
                if embedding:
                    embedding.update_usage()
                    similar_embeddings.append((embedding, similarity))

        return similar_embeddings

    @staticmethod
    async def find_similar_content(
        session,
        organization_id: str,
        query_text: str,
        content_type: ContentType = None,
        limit: int = 5,
    ) -> List[Tuple[str, str, float]]:
        """
        Find similar content by text query
        Returns list of (content_id, content_text, similarity_score) tuples
        """
        # This would typically involve:
        # 1. Generate embedding for query_text
        # 2. Search for similar embeddings
        # 3. Return content information

        # Placeholder implementation
        # In real implementation, you'd call your embedding service here
        return []

    @staticmethod
    def generate_content_hash(content: str) -> str:
        """Generate SHA-256 hash of content"""
        import hashlib

        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    async def create_embedding(
        session,
        organization_id: str,
        content_type: ContentType,
        content_id: str,
        content_text: str,
        embedding_vector: List[float],
        model_name: EmbeddingModel = EmbeddingModel.OPENAI_ADA_002,
        model_version: str = None,
        processing_time_ms: int = None,
        token_count: int = None,
    ) -> Embedding:
        """Create new embedding record"""

        content_hash = EmbeddingService.generate_content_hash(content_text)

        embedding = Embedding(
            organization_id=organization_id,
            content_type=content_type,
            content_id=content_id,
            content_text=content_text,
            content_hash=content_hash,
            embedding=embedding_vector,
            model_name=model_name,
            model_version=model_version,
            embedding_dimensions=len(embedding_vector),
            processing_time_ms=processing_time_ms,
            token_count=token_count,
        )

        session.add(embedding)
        await session.commit()
        await session.refresh(embedding)

        return embedding

    @staticmethod
    async def update_embedding(
        session,
        embedding: Embedding,
        content_text: str,
        embedding_vector: List[float],
        processing_time_ms: int = None,
        token_count: int = None,
    ) -> Embedding:
        """Update existing embedding"""

        embedding.content_text = content_text
        embedding.content_hash = EmbeddingService.generate_content_hash(content_text)
        embedding.embedding = embedding_vector
        embedding.embedding_dimensions = len(embedding_vector)
        embedding.processing_time_ms = processing_time_ms
        embedding.token_count = token_count
        embedding.updated_at = datetime.now(timezone.utc)

        await session.commit()
        await session.refresh(embedding)

        return embedding
