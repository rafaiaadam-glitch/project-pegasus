FROM python:3.11.9-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip "wheel>=0.46.2" \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && pip install --no-cache-dir --force-reinstall "jaraco.context>=6.1.0"

COPY backend /app/backend
COPY pipeline /app/pipeline
COPY schemas /app/schemas

ENV PORT=8080
EXPOSE 8080

# Use shell form to allow environment variable substitution
CMD uvicorn backend.app:app --host 0.0.0.0 --port $PORT
