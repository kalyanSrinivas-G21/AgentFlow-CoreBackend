# backend/app/tools/document_tools.py
import os
import magic
from typing import Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.tools.base import Tool, register_tool
from app.tools.models import ToolResult
from app.workspace.service import WorkspaceService
from app.workspace.parsers.registry import DocumentParserRegistry
from app.models_ai.ollama_provider import OllamaProvider
from app.models_ai.router import ModelRouter
from app.workspace.embedding_service import EmbeddingService
from app.workspace.models import DocumentChunk
from app.workspace.models import File
from app.workspace.ingestion import process_document, ProcessingStatus

class ExtractInput(BaseModel):
    file_path: str = Field(..., description="Relative path of the document to extract")
    file_id: str = Field(..., description="UUID of the file record")

@register_tool
class DocumentExtractTool(Tool):
    name = "document.extract"
    description = "Extracts text from a document natively or via PaddleOCR."
    input_schema = ExtractInput
    timeout_s = 60.0
    retryable = True

    async def run(self, args: Dict[str, Any], project_id: str, db: AsyncSession = None) -> ToolResult:
        if not db:
            return ToolResult(success=False, error="Database session required")

        target = WorkspaceService.resolve_path(project_id, args["file_path"])
        
        if not target.exists():
            return ToolResult(success=False, error="File not found")

        # Step 8.3: Direct Native Parsing routing (Saves VRAM)
        mime_type = magic.from_file(str(target), mime=True)
        
        file_row = await db.scalar(select(File).where(File.id == args["file_id"], File.project_id == project_id))
        if file_row is None:
            return ToolResult(success=False, error="File does not belong to this project")

        processing = process_document(target, mime_type)
        if processing.status != ProcessingStatus.COMPLETED:
            return ToolResult(success=False, error=f"Document status {processing.status}: {processing.failure_reason}")
        extracted_text = processing.text or ""
        
        embedding_service = EmbeddingService(db)
        await embedding_service.chunk_and_embed(args["file_id"], extracted_text)
        
        return ToolResult(
            success=True, 
            output=f"Extraction Complete. Summary: {extracted_text[:300]}...",
            metadata={"chars": len(extracted_text), "parser": "native_or_paddleocr"}
        )

class QueryInput(BaseModel):
    file_id: str = Field(..., description="UUID of the file to query")
    question: str = Field(..., description="Question to answer based on the document")

@register_tool
class DocumentQueryTool(Tool):
    name = "document.query"
    description = "Queries an indexed document using RAG."
    input_schema = QueryInput
    timeout_s = 45.0
    retryable = True

    async def run(self, args: Dict[str, Any], project_id: str, db: AsyncSession = None) -> ToolResult:
        if not db:
            return ToolResult(success=False, error="Database session required")

        provider = OllamaProvider(base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        question_embedding = await provider.embed("nomic-embed-text", args["question"])

        # Step 8.5: Project Scope Integrity (JOIN on File)
        stmt = (
            select(DocumentChunk)
            .join(File, DocumentChunk.file_id == File.id)
            .where(
                DocumentChunk.file_id == args["file_id"],
                File.project_id == project_id  # SECURITY: Prevent cross-tenant leakage
            )
            .order_by(DocumentChunk.embedding.cosine_distance(question_embedding))
            .limit(3)
        )

        result = await db.execute(stmt)
        top_chunks = result.scalars().all()

        if not top_chunks:
            return ToolResult(success=False, error="No document content found for the given file_id or project.")

        context_text = "\n\n".join([c.text for c in top_chunks])

        router = ModelRouter()
        tier1_model = router.route(required_capabilities=["general"])

        prompt = f"Context:\n{context_text}\n\nQuestion: {args['question']}\nAnswer concisely based only on the context."
        answer = await provider.generate(model=tier1_model, prompt=prompt)

        return ToolResult(success=True, output=answer, metadata={"chunks_retrieved": len(top_chunks), "model_used": tier1_model})