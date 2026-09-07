# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install basic system dependencies AND the Docker CLI for sandbox tool capability
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gnupg \
    && curl -fsSL https://get.docker.com -o get-docker.sh \
    && sh get-docker.sh \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -u 1000 workbench

# Add workbench to docker group so it can interact with the socket
RUN usermod -aG docker workbench

COPY requirements.txt .

# Removed --no-cache-dir to allow download resumption and increased timeout for massive ML packages
RUN pip install --default-timeout=1000 -r requirements.txt

# Install OS-level dependencies for python-magic and paddleocr AFTER pip
# This preserves the massive pip cache for paddlepaddle
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Set permissions for the non-root user
RUN chown -R workbench:workbench /app

USER workbench

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]