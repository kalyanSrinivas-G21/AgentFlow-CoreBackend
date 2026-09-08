from pathlib import Path

import pytest

from app.workspace.ingestion import ProcessingStatus, process_document


def test_corrupted_document_reports_failed_not_completed(tmp_path: Path):
    document = tmp_path / "broken.pdf"
    document.write_bytes(b"not a pdf")

    result = process_document(document, "application/pdf")

    assert result.status == ProcessingStatus.FAILED
    assert result.text is None
    assert result.failure_reason


def test_unsupported_document_reports_failed_status(tmp_path: Path):
    document = tmp_path / "unknown.bin"
    document.write_bytes(b"data")

    result = process_document(document, "application/octet-stream")

    assert result.status == ProcessingStatus.FAILED
    assert "parser" in (result.failure_reason or "").lower()
