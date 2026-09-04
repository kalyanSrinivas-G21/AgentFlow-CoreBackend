import base64
import io
import os
import pypdfium2 as pdfium
from typing import Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.tools.base import Tool, register_tool
from app.workspace.service import WorkspaceService
from app.models_ai.ollama_provider import OllamaProvider
from app.models_ai.tier_router import TierRouter
from app.workspace.embedding_service import EmbeddingService
from app.workspace.models import DocumentChunk

class ExtractInput(BaseModel):
    file_path: str = Field(..., description="Relative path of the document to extract")
    file_id: str = Field(..., description="UUID of the file record")

@register_tool
class DocumentExtractTool(Tool):
    name = "document.extract"
    input_schema = ExtractInput
    timeout_s = 60.0
    retryable = True

    async def run(self, args: Dict[str, Any], project_id: str, db: AsyncSession = None) -> str:
        if not db:
            raise ValueError("Database session required for document.extract")

        parsed = self.input_schema(**args)
        target = WorkspaceService.resolve_path(project_id, parsed.file_path)
        
        images_b64 = []
        
        if target.suffix.lower() == ".pdf":
            # Rasterize PDF pages to images for the local VLM
            pdf = pdfium.PdfDocument(str(target))
            for i in range(min(len(pdf), 20)):  # Cap at 20 pages for local VRAM limits
                page = pdf[i]
                bitmap = page.render(scale=2)
                pil_image = bitmap.to_pil()
                buffered = io.BytesIO()
                pil_image.save(buffered, format="JPEG")
                images_b64.append(base64.b64encode(buffered.getvalue()).decode("utf-8"))
        else:
            with target.open("rb") as f:
                images_b64.append(base64.b64encode(f.read()).decode("utf-8"))

        # Initialize local VLM (Tier 2)
        router = TierRouter()
        vlm_model = router.get_model_for_tier(2)
        provider = OllamaProvider(base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        
        prompt = "Extract all text and structured data from this document verbatim. Provide a summary at the top."
        extracted_text = await provider.generate(model=vlm_model, prompt=prompt, images=images_b64)
        
        # Save to Local Vector Database
        embedding_service = EmbeddingService(db)
        await embedding_service.chunk_and_embed(parsed.file_id, extracted_text)
        
        return f"Extraction Complete and Indexed. Length: {len(extracted_text)} chars.\n\nSummary:\n{extracted_text[:500]}..."

class QueryInput(BaseModel):
    file_id: str = Field(..., description="UUID of the file to query")
    question: str = Field(..., description="Question to answer based on the document")

@register_tool
class DocumentQueryTool(Tool):
    name = "document.query"
    input_schema = QueryInput
    timeout_s = 45.0
    retryable = True

    async def run(self, args: Dict[str, Any], project_id: str, db: AsyncSession = None) -> str:
        if not db:
            raise ValueError("Database session required for document.query")

        parsed = self.input_schema(**args)
        provider = OllamaProvider(base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

        # 1. Embed the Question
        question_embedding = await provider.embed("nomic-embed-text", parsed.question)

        # 2. Vector Search using pgvector Cosine Distance (<=>)
        stmt = select(DocumentChunk).where(
            DocumentChunk.file_id == parsed.file_id
        ).order_by(
            DocumentChunk.embedding.cosine_distance(question_embedding)
        ).limit(3)

        result = await db.execute(stmt)
        top_chunks = result.scalars().all()

        if not top_chunks:
            return "No document content found for the given file_id."

        context_text = "\n\n".join([c.text for c in top_chunks])

        # 3. Tier-1 RAG Synthesis
        router = TierRouter()
        tier1_model = router.get_model_for_tier(1)

        prompt = f"Context:\n{context_text}\n\nQuestion: {parsed.question}\nAnswer concisely based only on the context."
        answer = await provider.generate(model=tier1_model, prompt=prompt)

        return answer