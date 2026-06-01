FROM python:3.12-slim AS base

# Security: run as non-root
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Install dependencies before copying source to exploit layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Drop privileges
USER appuser

EXPOSE 8000

# Production: gunicorn with uvicorn workers
# 2 workers is a safe default for a CPU-light I/O-bound proxy;
# tune with WEB_CONCURRENCY env var for larger hosts.
CMD ["gunicorn", "main:app", \
  "--worker-class", "uvicorn.workers.UvicornWorker", \
  "--workers", "2", \
  "--bind", "0.0.0.0:8000", \
  "--timeout", "180", \
  "--graceful-timeout", "30", \
  "--access-logfile", "-", \
  "--error-logfile", "-"]
