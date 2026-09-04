import os
from sqlalchemy.ext.asyncio import AsyncSession
from app.workspace.models import DocumentChunk
from app.models_ai.ollama_provider import OllamaProvider

class EmbeddingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.provider = OllamaProvider(base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        self.embed_model = "nomic-embed-text"

    async def chunk_and_embed(self, file_id: str, text: str, chunk_size: int = 500):
        """Simple fixed-length chunking and embedding generation for local vector RAG."""
        if not text.strip():
            return

        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        for i, chunk_text in enumerate(chunks):
            embedding = await self.provider.embed(self.embed_model, chunk_text)
            
            chunk_record = DocumentChunk(
                file_id=file_id,
                chunk_index=i,
                text=chunk_text,
                embedding=embedding
            )
            self.db.add(chunk_record)
        
        await self.db.commit()