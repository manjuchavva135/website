FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/apps/worker:/app/apps/api:/app/packages/shared-py

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt /app/apps/api/requirements.txt
COPY apps/worker/requirements.txt /app/apps/worker/requirements.txt
COPY packages/shared-py /app/packages/shared-py

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/apps/api/requirements.txt \
    && pip install --no-cache-dir -r /app/apps/worker/requirements.txt \
    && pip install --no-cache-dir -e /app/packages/shared-py

COPY apps/api /app/apps/api
COPY apps/worker /app/apps/worker

HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD python -m worker.health --skip-external

CMD ["celery", "-A", "worker.celery_app:celery_app", "--workdir", "apps/worker", "worker", "--loglevel=info", "--concurrency=1"]
