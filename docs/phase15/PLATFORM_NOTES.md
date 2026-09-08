# Phase 15 Platform Notes

## PaddleOCR and Windows

`backend/app/workspace/parsers/registry.py` and `backend/app/tools/document_tools.py` contain the PaddleOCR path, which depends on `paddlepaddle`. The declared requirement `paddlepaddle>=2.6.1` did not have a compatible distribution for the Windows development interpreter used on 2026-09-07.

This does not block Stage Four application-level sovereignty telemetry and is not being worked around in the OCR pipeline. Placeholder decision for Stage Seven: run PaddleOCR-dependent OCR demonstrations in the supported Linux/container environment, or replace it with a locally supported OCR backend after comparing accuracy and sovereignty constraints. The decision must be finalized before claiming Windows OCR support.
