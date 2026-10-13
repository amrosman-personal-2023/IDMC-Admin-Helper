FROM python:3.12-slim

# --- system deps -----------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# --- non-root service account ---------------------------------------------
RUN groupadd -r idmc && useradd -r -g idmc -d /app idmc

WORKDIR /app

# --- Python deps -----------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir anthropic openai google-genai "httpx==0.27.0"

# --- Application source ---------------------------------------------------
COPY . .
RUN rm -rf tests/

# Config files are mounted at runtime; create mount-point dirs
RUN mkdir -p /etc/idmc-portal /opt/idmc/staging /opt/idmc/scripts \
    && chown -R idmc:idmc /app /etc/idmc-portal /opt/idmc

USER idmc

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "2"]
