# Deployment Guide

Hướng dẫn deploy hệ thống lên production.

---

## Production Checklist

Trước khi deploy, đảm bảo:

- [ ] `DASHBOARD_SECRET` được set thành random string (không dùng default)
- [ ] `APP_ENV=production` trong `.env`
- [ ] `DASHBOARD_PASSWORD` được set
- [ ] `LLM_API_KEY` hợp lệ
- [ ] Frontend đã build: `cd frontend && npm run build`
- [ ] Tests pass: `pytest`

---

## Docker (Khuyến nghị)

### Docker Compose

```yaml
# docker-compose.yml (production)
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=production
      - DASHBOARD_SECRET=${DASHBOARD_SECRET}
      - DASHBOARD_PASSWORD=${DASHBOARD_PASSWORD}
      - LLM_PROVIDER=${LLM_PROVIDER}
      - LLM_API_KEY=${LLM_API_KEY}
      - REDIS_URL=redis://redis:6379/0
      - JOB_QUEUE_BACKEND=rq
    depends_on:
      - redis
    volumes:
      - workspace:/app/workspace

  worker:
    build: .
    command: rq worker flutter_ai_factory
    environment:
      - REDIS_URL=redis://redis:6379/0
      - LLM_PROVIDER=${LLM_PROVIDER}
      - LLM_API_KEY=${LLM_API_KEY}
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: always

volumes:
  workspace:
  redis_data:
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm curl && \
    rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend build
COPY frontend/ frontend/
RUN cd frontend && npm install --no-audit --no-fund && npm run build

# App source
COPY . .

EXPOSE 8000
CMD ["uvicorn", "dashboard.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Chạy

```bash
# Tạo .env.production
cp .env.example .env.production
# Edit .env.production với production values

# Build & run
docker-compose up -d --build

# Xem logs
docker-compose logs -f api
```

---

## VPS + Docker Compose

### Yêu cầu

- Ubuntu 22.04+ / Debian 12+
- 2GB+ RAM
- Docker & Docker Compose installed

### Steps

```bash
# 1. SSH vào server
ssh root@your-server-ip

# 2. Cài Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker && systemctl start docker

# 3. Clone repo
git clone <repo-url> /opt/aisoftwareorg
cd /opt/aisoftwareorg

# 4. Cấu hình
cp .env.example .env.production
nano .env.production  # Điền production values

# 5. Deploy
docker-compose -f docker-compose.yml --env-file .env.production up -d --build

# 6. Verify
curl http://localhost:8000/health
```

### Nginx Reverse Proxy (optional)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Railway

1. Connect GitHub repo
2. Add environment variables từ `.env.example`
3. Set build command: `cd frontend && npm install && npm run build`
4. Set start command: `uvicorn dashboard.app:app --host 0.0.0.0 --port $PORT`
5. Add Redis service từ Railway marketplace

---

## Render

1. Create Web Service từ GitHub repo
2. Build Command: `pip install -r requirements.txt && cd frontend && npm install && npm run build`
3. Start Command: `uvicorn dashboard.app:app --host 0.0.0.0 --port $PORT`
4. Add Redis instance
5. Set environment variables

---

## Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Init & deploy
fly launch
fly secrets set DASHBOARD_SECRET=$(openssl rand -hex 32)
fly secrets set LLM_API_KEY=sk-...
fly deploy
```

---

## Environment Variables (Production)

| Variable | Required | Notes |
|---|---|---|
| `APP_ENV` | ✅ | Set to `production` |
| `DASHBOARD_SECRET` | ✅ | Random string (min 32 chars) |
| `DASHBOARD_PASSWORD` | ✅ | Strong password for auth |
| `LLM_PROVIDER` | ✅ | `openrouter`, `openai`, `gemini` |
| `LLM_API_KEY` | ✅ | Valid API key |
| `JOB_QUEUE_BACKEND` | Recommended | `rq` for production |
| `REDIS_URL` | If using RQ | `redis://...` |
| `DAILY_COST_LIMIT` | Recommended | Max daily spend in USD |

---

## Monitoring

### Health Check

```bash
curl http://your-domain/health
# {"status": "ok", "queue_backend": "rq"}
```

### Logs

```bash
# Docker
docker-compose logs -f api

# Direct
tail -f logs/*.log
```

### Costs

Truy cập Dashboard → Costs tab để theo dõi token usage.
