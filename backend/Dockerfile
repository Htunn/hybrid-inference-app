# ---------------------------------------------------------------------------- #
# Stage 1 — build: install Python deps into an isolated prefix               #
# ---------------------------------------------------------------------------- #
FROM python:3.12-slim AS builder

WORKDIR /install

COPY requirements.txt .
# Install into a custom prefix so we can copy only the installed packages
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt

# ---------------------------------------------------------------------------- #
# Stage 2 — runtime: lean image, no pip, no build tools                       #
# ---------------------------------------------------------------------------- #
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="infermesh-backend" \
  org.opencontainers.image.description="FastAPI backend for InferMesh" \
  org.opencontainers.image.base.name="python:3.12-slim"

# Security: non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Pull only the installed packages from the builder stage
COPY --from=builder /install/deps /usr/local

WORKDIR /app
COPY . .

# Set Hugging Face cache directory to a writable location
# sentence-transformers downloads models to HF_HOME on first use
ENV HF_HOME=/tmp/huggingface

# Create cache directory and set ownership before dropping privileges
RUN mkdir -p /tmp/huggingface && chown -R appuser:appgroup /tmp/huggingface

# Drop privileges before the process starts
USER appuser

EXPOSE 8000

# Healthcheck so Docker/Compose knows when the app is ready
HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Production: gunicorn with uvicorn workers
# Tune WEB_CONCURRENCY for the host; default 2 is safe for I/O-bound proxies.
CMD ["gunicorn", "main:app", \
  "--worker-class", "uvicorn.workers.UvicornWorker", \
  "--workers", "2", \
  "--bind", "0.0.0.0:8000", \
  "--timeout", "180", \
  "--graceful-timeout", "30", \
  "--access-logfile", "-", \
  "--error-logfile", "-", \
  "--forwarded-allow-ips", "*"]
