from enum import StrEnum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from app.workspace.parsers.registry import DocumentParserRegistry


class ProcessingStatus(StrEnum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    PARTIALLY_PROCESSED = "Partially Processed"
    FAILED = "Failed"
    UNPROCESSABLE = "Unprocessable"


class DocumentProcessingResult(BaseModel):
    status: ProcessingStatus
    text: Optional[str] = None
    failure_reason: Optional[str] = None
    parser: Optional[str] = None


def process_document(file_path: Path, mime_type: str) -> DocumentProcessingResult:
    try:
        text = DocumentParserRegistry.parse(file_path, mime_type)
        if not text.strip():
            return DocumentProcessingResult(status=ProcessingStatus.UNPROCESSABLE, failure_reason="Parser returned no content")
        return DocumentProcessingResult(status=ProcessingStatus.COMPLETED, text=text, parser="native_or_local_ocr")
    except Exception as exc:
        return DocumentProcessingResult(status=ProcessingStatus.FAILED, failure_reason=str(exc), parser="native_or_local_ocr")
