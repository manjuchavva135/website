FROM python:3.11-slim

WORKDIR /app

COPY packages/shared-py /app/packages/shared-py
COPY apps/api /app/apps/api
COPY apps/worker /app/apps/worker

RUN pip install --no-cache-dir -r /app/apps/worker/requirements.txt && \
    pip install --no-cache-dir -e /app/packages/shared-py

WORKDIR /app/apps/worker
ENV PYTHONPATH=/app/apps/worker:/app/apps/api:/app/packages/shared-py

HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD python -m worker.health --skip-external

CMD ["celery", "-A", "worker.celery_app:celery_app", "worker", "--loglevel=info"]
