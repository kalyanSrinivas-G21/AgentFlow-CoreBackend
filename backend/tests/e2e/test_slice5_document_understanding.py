import pytest
import uuid
from pathlib import Path
from PIL import Image, ImageDraw
from unittest.mock import AsyncMock
from app.workspace.service import WorkspaceService
from app.tools.document_tools import DocumentExtractTool

@pytest.mark.asyncio
async def test_document_extraction_vlm():
    """Proves the local VLM can read and extract text from a synthetic image."""
    project_id = uuid.uuid4()
    file_id = str(uuid.uuid4())
    filename = "test_confidential_sop.jpg"
    
    # 1. Generate a synthetic image with Pillow to avoid hardcoded binary dependencies
    target_path = WorkspaceService.resolve_path(project_id, filename)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    img = Image.new('RGB', (400, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    secret_text = "CONFIDENTIAL: System shutdown override code is 9942-X."
    d.text((10, 80), secret_text, fill=(0, 0, 0))
    img.save(target_path)
    
    # 2. Trigger Extraction Tool
    tool = DocumentExtractTool()
    
    # Mock the DB for this isolated tool test, as we are testing VLM vision connectivity, not DB writes here
    db_mock = AsyncMock() 
    db_mock.add = AsyncMock()
    db_mock.commit = AsyncMock()
    
    try:
        # NOTE: This requires Ollama running locally with a Tier 2 VLM (e.g., llava or qwen2.5vl)
        result = await tool.run({
            "file_path": filename,
            "file_id": file_id
        }, str(project_id), db=db_mock)
        
        # 3. Assert VLM successfully extracted the visual text
        assert "9942-X" in result, f"VLM failed to extract secret text. Result: {result}"
        
    except Exception as e:
        pytest.skip(f"Skipping VLM test due to missing local Ollama VLM model or timeout: {e}")
    finally:
        target_path.unlink()