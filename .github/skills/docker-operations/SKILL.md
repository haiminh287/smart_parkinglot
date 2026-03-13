---
name: docker-operations
description: 'Kỹ năng vận hành Docker - Build, optimize images, compose multi-service, troubleshoot containers.'
---

# 🐳 Kỹ năng Vận hành Docker (Docker Operations Skill)

## Mục đích
Skill này cung cấp best practices cho việc xây dựng, tối ưu, và quản lý Docker containers trong môi trường doanh nghiệp.

## Điều kiện Kích hoạt
Sử dụng skill này khi:
- Cần tạo hoặc tối ưu Dockerfile
- Cần setup Docker Compose cho multi-service
- Cần debug container issues
- Cần optimize Docker image size

## Best Practices

### 1. Dockerfile Optimization
```dockerfile
# ✅ ĐÚNG: Multi-stage build, specific versions, non-root user
FROM node:20.11-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20.11-alpine AS runner
RUN addgroup -g 1001 -S app && adduser -S app -u 1001
WORKDIR /app
COPY --from=builder --chown=app:app /app/dist ./dist
COPY --from=builder --chown=app:app /app/node_modules ./node_modules
USER app
EXPOSE 3000
CMD ["node", "dist/app.js"]

# ❌ SAI: Chạy root, không multi-stage, dùng latest tag
# FROM node:latest
# COPY . .
# RUN npm install
# CMD ["node", "src/app.js"]
```

### 2. Layer Caching Strategy
```dockerfile
# Copy package files TRƯỚC source code để tận dụng cache
COPY package.json package-lock.json ./    # Layer 1: Thay đổi ít
RUN npm ci                                 # Layer 2: Cache nếu packages không đổi
COPY . .                                   # Layer 3: Thay đổi thường xuyên
```

### 3. .dockerignore
```
.git
.github
node_modules
coverage
tests
docs
*.md
.env
.env.*
.vscode
.idea
```

### 4. Docker Compose Patterns
```yaml
# docker-compose.yml - Production-ready
version: '3.9'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: runner
    ports:
      - "${PORT:-3000}:3000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:3000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    networks:
      - backend

  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - backend

volumes:
  postgres_data:
  redis_data:

networks:
  backend:
    driver: bridge
```

### 5. Troubleshooting Commands
```bash
# Xem logs
docker compose logs -f app

# Exec vào container
docker compose exec app sh

# Kiểm tra resource usage
docker stats

# Inspect networking
docker network inspect backend

# Clean up
docker system prune -af --volumes
```

### 6. Security Checklist
- [ ] Base image dùng `-alpine` variant (nhỏ gọn, ít CVE)
- [ ] Chạy với non-root user
- [ ] Không copy `.env` vào image
- [ ] Pin version cụ thể (không dùng `:latest`)
- [ ] Scan image: `docker scout cves <image>`
- [ ] Secrets KHÔNG nằm trong build args
