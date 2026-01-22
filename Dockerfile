FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 必要なビルドツールとシステムパッケージをインストール
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirement.txt ./

RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirement.txt

COPY . .

EXPOSE 8000

# 本番用: Gunicorn + Uvicorn workers (2ワーカー)
# t2.microは1 vCPU, 1GB RAMなので2ワーカーが安全
CMD ["gunicorn", "main:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
