# --------------------------------------------
# Kai Omniseal Production Dockerfile - Final
# Maintainer: Akhila & Maya
# Build: docker build -t kai-omniseal .
# Run: docker run -p 8080:8080 kai-omniseal
# Railway: Automatically deployed via git push
# --------------------------------------------

# Multi-stage build for optimized production image
FROM python:3.10-slim as builder

ARG PIP_VERSION="23.3.2"
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

RUN pip install --no-cache-dir --upgrade "pip==${PIP_VERSION}"

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.10-slim as production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* && apt-get clean

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash appuser

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY --chown=appuser:appuser . .

RUN mkdir -p /app/logs /app/tmp && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

USER appuser

EXPOSE 8080

# ✅ PATCHED HERE: HEALTH ENDPOINT THAT MATCHES YOUR MAIN.PY
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# ✅ PATCHED: Correct app entry point
ENTRYPOINT ["python"]
CMD ["main.py"]
