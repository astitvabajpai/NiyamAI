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

# HuggingFace Spaces requires port 7860
EXPOSE 7860

# PORT env var: HF sets it to 7860, Fly sets it to 8080, fallback to 7860
CMD ["sh", "-c", "uvicorn src.api:app --host 0.0.0.0 --port ${PORT:-7860}"]
