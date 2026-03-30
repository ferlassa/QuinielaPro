# ── Backend (FastAPI) ──────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# System dependencies for psycopg2 + sklearn
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Run with Uvicorn — shell form for PORT expansion
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
