# Intent Engine - Production Dockerfile
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV WORKERS=2

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        libpq-dev \
        postgresql-client \
        libevent-2.1-7 \
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libpango-1.0-0 \
        libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install core build dependencies
RUN pip install --upgrade pip

# Install PyTorch CPU version (large download, cache this layer)
# We do this before requirements.txt to ensure we get the CPU-only version
RUN pip install --no-cache-dir torch==2.1.1+cpu -f https://download.pytorch.org/whl/torch_stable.html

# Install Python dependencies (cached unless requirements.txt changes)
COPY requirements.txt .
# Filter out torch from requirements.txt to avoid overwriting the CPU version with the GPU version
RUN grep -v "torch" requirements.txt > requirements-no-torch.txt && \
    pip install --no-cache-dir -r requirements-no-torch.txt && \
    rm requirements-no-torch.txt

# Set Playwright browser path and install Chromium
ENV PLAYWRIGHT_BROWSERS_PATH=/app/pw-browsers
RUN playwright install chromium

# Copy project files (respects .dockerignore)
COPY . .

# Make migration script executable
RUN chmod +x /app/scripts/run_migrations.sh 2>/dev/null || true

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /app/data && chown appuser:appuser /app/data && \
    chown -R appuser:appuser /app/pw-browsers
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Run the application
CMD ["sh", "-c", "uvicorn app.main_api:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-2}"]
