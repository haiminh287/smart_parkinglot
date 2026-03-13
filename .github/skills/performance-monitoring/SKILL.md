---
name: performance-monitoring
description: 'Kỹ năng giám sát hiệu suất ứng dụng - APM, load testing, profiling, và optimization strategies.'
---

# 📊 Kỹ năng Giám sát Hiệu suất (Performance Monitoring Skill)

## Mục đích
Skill này cung cấp công cụ và quy trình giám sát, đo lường, và tối ưu hiệu suất ứng dụng.

## Điều kiện Kích hoạt
Sử dụng skill này khi:
- Cần thiết lập monitoring cho ứng dụng
- Cần chạy load testing
- Cần profile và tìm bottlenecks
- Cần tối ưu performance

## 1. Health Check Endpoint
```javascript
// Endpoint chuẩn cho monitoring systems
app.get('/health', async (req, res) => {
  const healthCheck = {
    status: 'healthy',
    version: process.env.APP_VERSION || '1.0.0',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: {
      used: Math.round(process.memoryUsage().heapUsed / 1024 / 1024) + 'MB',
      total: Math.round(process.memoryUsage().heapTotal / 1024 / 1024) + 'MB',
    },
    checks: {},
  };

  try {
    // Database check
    await db.query('SELECT 1');
    healthCheck.checks.database = 'connected';
  } catch {
    healthCheck.checks.database = 'disconnected';
    healthCheck.status = 'degraded';
  }

  try {
    // Redis check
    await redis.ping();
    healthCheck.checks.redis = 'connected';
  } catch {
    healthCheck.checks.redis = 'disconnected';
    healthCheck.status = 'degraded';
  }

  const statusCode = healthCheck.status === 'healthy' ? 200 : 503;
  res.status(statusCode).json(healthCheck);
});
```

## 2. Request Logging Middleware
```javascript
const requestLogger = (req, res, next) => {
  const start = process.hrtime.bigint();
  
  res.on('finish', () => {
    const duration = Number(process.hrtime.bigint() - start) / 1e6; // ms
    
    logger.info({
      method: req.method,
      url: req.originalUrl,
      statusCode: res.statusCode,
      duration: `${duration.toFixed(2)}ms`,
      contentLength: res.get('content-length'),
      userAgent: req.get('user-agent'),
      ip: req.ip,
      timestamp: new Date().toISOString(),
    });

    // Cảnh báo nếu response quá chậm
    if (duration > 3000) {
      logger.warn({
        message: 'Slow request detected',
        method: req.method,
        url: req.originalUrl,
        duration: `${duration.toFixed(2)}ms`,
      });
    }
  });

  next();
};
```

## 3. Database Query Profiling
```javascript
// Hook vào ORM để log slow queries
const queryProfiler = {
  beforeQuery(options) {
    options._startTime = Date.now();
  },
  afterQuery(options) {
    const duration = Date.now() - options._startTime;
    if (duration > 1000) { // > 1 giây
      logger.warn({
        message: 'Slow query detected',
        query: options.sql,
        duration: `${duration}ms`,
        model: options.model?.name,
      });
    }
  },
};
```

## 4. Load Testing với Artillery/k6
```yaml
# artillery-config.yml
config:
  target: "http://localhost:3000"
  phases:
    - duration: 60      # 1 phút warmup
      arrivalRate: 5
      name: "Warm up"
    - duration: 120     # 2 phút load
      arrivalRate: 20
      name: "Sustained load"
    - duration: 60      # 1 phút stress
      arrivalRate: 50
      name: "Stress test"
  defaults:
    headers:
      Content-Type: "application/json"

scenarios:
  - name: "API Health Check"
    flow:
      - get:
          url: "/health"
  - name: "User CRUD"
    flow:
      - post:
          url: "/api/v1/users"
          json:
            name: "Test User"
            email: "test-{{ $randomNumber() }}@example.com"
      - get:
          url: "/api/v1/users"
```

```bash
# Chạy load test
npx artillery run artillery-config.yml --output reports/load-test.json

# Tạo HTML report
npx artillery report reports/load-test.json
```

## 5. Performance Budgets
| Metric | Target | Critical |
|--------|--------|----------|
| API Response (P95) | < 200ms | > 500ms |
| API Response (P99) | < 500ms | > 1000ms |
| Database Query | < 100ms | > 500ms |
| Memory Usage | < 256MB | > 512MB |
| CPU Usage | < 60% | > 85% |
| Error Rate | < 0.1% | > 1% |
| Throughput | > 100 rps | < 50 rps |

## 6. Optimization Checklist
- [ ] Database indexes cho frequent queries
- [ ] Connection pooling (pool size ≥ 10)
- [ ] Response caching (Redis, in-memory)
- [ ] Pagination cho list endpoints
- [ ] Gzip/Brotli compression
- [ ] Lazy loading cho non-critical modules
- [ ] N+1 query elimination
- [ ] Async/parallel processing khi có thể
- [ ] Static asset CDN
- [ ] Query result denormalization (đọc nhiều)
