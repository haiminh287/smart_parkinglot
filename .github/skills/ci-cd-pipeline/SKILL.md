---
name: ci-cd-pipeline
description: 'Kỹ năng thiết lập CI/CD pipeline chuẩn doanh nghiệp - GitHub Actions, automated testing, Docker build, multi-environment deployment.'
---

# 🔄 Kỹ năng CI/CD Pipeline (Continuous Integration & Deployment Skill)

## Mục đích
Skill này cung cấp template và best practices cho việc thiết lập CI/CD pipeline end-to-end.

## Điều kiện Kích hoạt
Sử dụng skill này khi:
- Cần tạo GitHub Actions workflows mới
- Cần setup automated testing trong CI
- Cần cấu hình multi-environment deployment
- Cần optimize build times

## 1. CI Pipeline Template (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: 🔄 CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

env:
  NODE_VERSION: '20'
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ──────────────────────────────────────
  # Job 1: Lint & Format Check
  # ──────────────────────────────────────
  lint:
    name: 🔍 Lint & Format
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm run format:check

  # ──────────────────────────────────────
  # Job 2: Security Audit
  # ──────────────────────────────────────
  security:
    name: 🛡️ Security Audit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
      - run: npm ci
      - run: npm audit --production --audit-level=high
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'HIGH,CRITICAL'

  # ──────────────────────────────────────
  # Job 3: Unit Tests
  # ──────────────────────────────────────
  unit-tests:
    name: 🧪 Unit Tests
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
      - run: npm ci
      - run: npm run test:unit -- --coverage
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: unit-coverage
          path: coverage/

  # ──────────────────────────────────────
  # Job 4: Integration Tests
  # ──────────────────────────────────────
  integration-tests:
    name: 🔗 Integration Tests
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: postgresql://test_user:test_pass@localhost:5432/test_db
      REDIS_URL: redis://localhost:6379
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
      - run: npm ci
      - run: npm run db:migrate:test
      - run: npm run test:integration -- --coverage

  # ──────────────────────────────────────
  # Job 5: Docker Build
  # ──────────────────────────────────────
  docker-build:
    name: 🐳 Docker Build
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests, security]
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        if: github.event_name != 'pull_request'
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=
            type=ref,event=branch
            type=semver,pattern={{version}}
      - uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

## 2. CD Pipeline Template

```yaml
# .github/workflows/deploy.yml
name: 🚀 Deploy Pipeline

on:
  push:
    branches: [main]
    tags: ['v*.*.*']
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

jobs:
  deploy-staging:
    name: 🟡 Deploy Staging
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.example.com
    if: github.ref == 'refs/heads/main' || github.event.inputs.environment == 'staging'
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Staging
        run: |
          echo "Deploying to staging..."
          # Add deployment commands here

  smoke-tests:
    name: 💨 Smoke Tests
    runs-on: ubuntu-latest
    needs: deploy-staging
    steps:
      - uses: actions/checkout@v4
      - name: Run Smoke Tests
        run: |
          curl -sf https://staging.example.com/health || exit 1
          echo "Smoke tests passed!"

  deploy-production:
    name: 🟢 Deploy Production
    runs-on: ubuntu-latest
    needs: smoke-tests
    environment:
      name: production
      url: https://example.com
    if: startsWith(github.ref, 'refs/tags/v') || github.event.inputs.environment == 'production'
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Production
        run: |
          echo "Deploying to production..."
          # Add production deployment commands here
```

## 3. Environment Variables Strategy

```
┌──────────────────────────────────────────┐
│ GitHub Secrets (encrypted at rest)       │
│ - DATABASE_URL                           │
│ - JWT_SECRET                             │
│ - API_KEYS                               │
│ - DEPLOY_TOKENS                          │
└──────────┬───────────────────────────────┘
           │
     ┌─────▼──────┐  ┌─────────────┐  ┌──────────────┐
     │ Development │  │   Staging    │  │  Production  │
     │ .env.local  │  │ env: staging │  │ env: prod    │
     │ (gitignored)│  │ (GH Secrets) │  │ (GH Secrets) │
     └─────────────┘  └─────────────┘  └──────────────┘
```

## 4. Build Optimization Tips
- ✅ Sử dụng `npm ci` thay vì `npm install` trong CI
- ✅ Cache node_modules qua `actions/setup-node` với `cache: 'npm'`
- ✅ Sử dụng Docker BuildKit cache (`cache-from: type=gha`)
- ✅ Enable `concurrency` để cancel build cũ khi có push mới
- ✅ Chạy lint, unit test, integration test song song (parallel jobs)
- ✅ Pin versions cho tất cả Actions (`@v4` thay vì `@latest`)
