FROM python:3.12-slim

WORKDIR /app

# Системные зависимости (cryptography требует libssl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY static/ ./static/
COPY appinfo/ ./appinfo/

# Директория для SQLite БД и сертификатов — монтируется как volume
RUN mkdir -p /data/certs

ENV PYTHONUNBUFFERED=1
ENV DB_PATH=/data/ncaclmanager.db

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/heartbeat', timeout=3)" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
