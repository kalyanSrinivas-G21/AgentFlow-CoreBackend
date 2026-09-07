# backend/tests/unit/test_multimodal_pipeline.py
import pytest
from pathlib import Path
from app.workspace.parsers.registry import DocumentParserRegistry

def test_csv_parser(tmp_path):
    """Verifies that native CSV parsing successfully routes and extracts data."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("Name,Role\nAlice,Admin\nBob,User")
    
    extracted = DocumentParserRegistry.parse(csv_file, "text/csv")
    assert "Alice | Admin" in extracted
    assert "Bob | User" in extracted

def test_unsupported_mime_type(tmp_path):
    """Verifies the parser strictly rejects unknown MIME types."""
    bin_file = tmp_path / "test.bin"
    bin_file.write_bytes(b"\x00\x01\x02")
    
    with pytest.raises(ValueError, match="No parser available"):
        DocumentParserRegistry.parse(bin_file, "application/octet-stream")