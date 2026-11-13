FROM python:3.13-slim

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Install dependencies first (layer-cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source (indexes in data/ are committed and copied here)
COPY . .

RUN chown -R appuser:appuser /app
USER appuser

# HuggingFace Spaces uses port 7860; Render uses $PORT
EXPOSE 7860

CMD ["sh", "-c", "uvicorn src.api:app --host 0.0.0.0 --port ${PORT:-7860}"]
