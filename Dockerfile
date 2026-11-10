FROM python:3.13-slim

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Install dependencies first (layer-cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Ensure indexes exist; skip if already present (committed to repo)
RUN bash scripts/ingest.sh

RUN chown -R appuser:appuser /app
USER appuser

# Fly.io sets PORT=8080 by default. We expose 8080 to match.
EXPOSE 8080

# Always use $PORT — Fly injects it at runtime (default 8080 if not set)
CMD ["sh", "-c", "uvicorn src.api:app --host 0.0.0.0 --port ${PORT:-8080}"]
