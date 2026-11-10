#!/bin/bash
set -e

# Skip ingestion if indexes are already present (e.g. committed to repo or cached volume).
# This avoids re-embedding on every Render deploy.
if [ -f "data/chunks/metadata.json" ] && [ -f "data/bm25_index.pkl" ]; then
    echo "Indexes already present — skipping ingestion."
    exit 0
fi

echo "Indexes not found — running ingestion..."
python -m src.ingestion
