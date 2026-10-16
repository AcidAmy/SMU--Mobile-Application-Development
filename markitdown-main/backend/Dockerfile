# ==============================================================================
# MarkItDown Backend Service Dockerfile
# FastAPI + PyTorch Document Classifier + SQLite + MarkItDown Conversion Engine
# ==============================================================================

FROM python:3.12-slim-bookworm

# Metadata
LABEL maintainer="MarkItDown Team"
LABEL description="Full-stack MarkItDown Backend with PyTorch Deep Learning Classifier and REST API"

# Python and environment settings
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    EXIFTOOL_PATH=/usr/bin/exiftool \
    FFMPEG_PATH=/usr/bin/ffmpeg \
    MARKITDOWN_ENABLE_PLUGINS=True \
    ORT_DISABLE_TELEMETRY=1

# Install runtime dependencies for MarkItDown engine (ffmpeg, exiftool) and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libimage-exiftool-perl \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy packages and requirements first for Docker layer caching
COPY packages /app/packages
COPY backend/requirements.txt /app/backend/requirements.txt

# Install PyTorch CPU wheels (keeping image lightweight), numpy<2, backend requirements,
# and core packages (markitdown with all format extras, plus markitdown-ocr plugin)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "numpy<2" && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /app/backend/requirements.txt && \
    pip install --no-cache-dir -e /app/packages/markitdown[all] -e /app/packages/markitdown-ocr

# Copy backend application source code
COPY backend /app/backend

# Create runtime directories for SQLite persistence, uploads, and weights
RUN mkdir -p /app/backend/data /app/backend/classifier/weights

# Expose FastAPI backend port
EXPOSE 8000

# Healthcheck targeting FastAPI /api/health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start Uvicorn ASGI server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
