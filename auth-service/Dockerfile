FROM python:3.12-slim

# --- system deps -----------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# --- non-root service account ---------------------------------------------
RUN groupadd -r idmc && useradd -r -g idmc -d /app idmc

WORKDIR /app

# --- Python deps (layer-cached unless requirements change) ----------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir psycopg2-binary

# --- Application source ---------------------------------------------------
COPY . .

# Drop test fixtures from the production image
RUN rm -rf tests/ alembic/versions/__pycache__

RUN chown -R idmc:idmc /app
USER idmc

EXPOSE 8001

# Run Alembic migrations then start the service
CMD ["sh", "-c", \
     "alembic upgrade head && \
      uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 2"]
