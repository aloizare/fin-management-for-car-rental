# ---- Builder Stage ----
FROM python:3.12-slim AS builder

WORKDIR /app

# Install dependencies only (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Runtime Stage ----
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY app/ ./app/

# Copy alembic migrations
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini

# HF Spaces runs as user with UID 1000
RUN mkdir -p /app/uploads && chmod 777 /app/uploads

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
