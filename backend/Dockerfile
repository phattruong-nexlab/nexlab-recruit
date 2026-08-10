# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# --- Dependencies ---
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# --- Source ---
COPY main.py config.py ./
COPY app ./app

# Cloud Run inject biến PORT; mặc định 8080.
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
