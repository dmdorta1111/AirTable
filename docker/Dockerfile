# =============================================================================
# PyBase Dockerfile
# Multi-stage build for optimized production image
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Build stage
# -----------------------------------------------------------------------------
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install dependencies
WORKDIR /app
COPY pyproject.toml .

# Install dependencies
RUN pip install --upgrade pip && \
    pip install -e ".[extraction]"

# -----------------------------------------------------------------------------
# Stage 2: Production stage
# -----------------------------------------------------------------------------
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    # For PDF extraction
    poppler-utils \
    # For OCR
    tesseract-ocr \
    tesseract-ocr-eng \
    # For image processing
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 pybase && \
    useradd --uid 1000 --gid pybase --shell /bin/bash --create-home pybase

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=pybase:pybase src/ ./src/
COPY --chown=pybase:pybase pyproject.toml ./

# Switch to non-root user
USER pybase

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health')"

# Default command
CMD ["uvicorn", "pybase.main:app", "--host", "0.0.0.0", "--port", "8000"]

# -----------------------------------------------------------------------------
# Stage 3: Development stage
# -----------------------------------------------------------------------------
FROM production as development

# Switch to root for installing dev dependencies
USER root

# Install development dependencies
RUN pip install -e ".[dev]"

# Switch back to non-root user
USER pybase

# Development command with auto-reload
CMD ["uvicorn", "pybase.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
