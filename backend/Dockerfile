FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY pipeline /app/pipeline
COPY schemas /app/schemas

ENV PORT=8080
EXPOSE 8080

# Use shell form to allow environment variable substitution
CMD uvicorn backend.app:app --host 0.0.0.0 --port $PORT
