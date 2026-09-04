# docker/sandbox-base.Dockerfile
FROM python:3.11-slim

# Install testing utilities
RUN pip install --no-cache-dir pytest

# Create a non-root user for execution
RUN useradd -m -s /bin/bash sandboxuser
USER sandboxuser

WORKDIR /workspace