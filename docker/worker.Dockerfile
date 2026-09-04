FROM python:3.12-slim

WORKDIR /app

# Ensure we don't buffer Python output to view logs immediately
ENV PYTHONUNBUFFERED=1

# Copy backend dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend directory
COPY backend /app

# Point Python to /app so it can resolve `app.` and `worker.` imports
ENV PYTHONPATH=/app

CMD ["python", "-m", "worker.main"]