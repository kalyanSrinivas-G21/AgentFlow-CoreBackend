# backend/app/workspace/embedding_service.py
import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.workspace.models import DocumentChunk
from app.models_ai.runtime import OllamaRuntime

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.runtime = OllamaRuntime()
        self.embed_model = "nomic-embed-text"
        self.expected_dim = 768 # nomic-embed-text dimension

    async def chunk_and_embed(self, file_id: str, text: str, chunk_size: int = 500):
        """Simple fixed-length chunking and embedding generation for local vector RAG."""
        if not text.strip():
            return

        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        for i, chunk_text in enumerate(chunks):
            embedding = await self.runtime.embed(self.embed_model, chunk_text)
            
            # Step 8.4: Embedding Dimensionality Integrity
            if len(embedding) != self.expected_dim:
                logger.error(f"Dimension mismatch! Expected {self.expected_dim}, got {len(embedding)}")
                raise ValueError("Embedding dimensionality mismatch prevents pgvector insertion.")
            
            chunk_record = DocumentChunk(
                file_id=file_id,
                chunk_index=i,
                text=chunk_text,
                embedding=embedding
            )
            self.db.add(chunk_record)
        
        await self.db.commit()