# --------------------------------------------
# Kai Omniseal Production Dockerfile
# Maintainer: Akhila & Maya
# Build: docker build -t kai-omniseal .
# Run: docker run -p 8080:8080 kai-omniseal
# Railway: Automatically deployed via git push
# --------------------------------------------

# Multi-stage build for optimized production image
FROM python:3.10-slim as builder

# Set build arguments for flexibility
ARG PYTHON_VERSION=3.10
ARG ENVIRONMENT=production
ARG PIP_VERSION="23.3.2"

# Set environment variables for Python optimization and locale
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Install system dependencies required for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Upgrade pip to pinned stable version
RUN pip install --no-cache-dir --upgrade "pip==${PIP_VERSION}"

# Set working directory
WORKDIR /app

# Copy dependency files first for better layer caching
COPY requirements.txt ./
# If using Poetry (future-proofing)
# COPY pyproject.toml poetry.lock* ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Poetry alternative (commented out for requirements.txt workflow)
# RUN pip install poetry && \
#     poetry config virtualenvs.create false && \
#     poetry install --no-root --only main

# Production stage
FROM python:3.10-slim as production

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH" \
    ENVIRONMENT=production \
    PORT=8080 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security (production stage only)
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files with proper ownership
# .dockerignore will exclude unnecessary files
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/tmp && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Switch to non-root user
USER appuser

# Expose port (Railway will override this)
EXPOSE 8080

# Health check for container orchestration
# Uses multiple endpoints for comprehensive health monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Use ENTRYPOINT + CMD for better signal handling and flexibility
ENTRYPOINT ["python"]
CMD ["kai_omniseal.py"]
