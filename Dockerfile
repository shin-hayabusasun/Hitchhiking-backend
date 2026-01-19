FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 依存インストール
COPY requirement.txt ./
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirement.txt

# アプリをコピー
COPY . .

EXPOSE 8000

# 本番用：reloadなし、複数ワーカー
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
