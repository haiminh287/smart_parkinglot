# Runtime Smoke Verification — Chatbot Health + Refresh Contract After Recreate

**Ngày:** 2026-03-16

**Scope:** rebuild/recreate tối thiểu runtime bị ảnh hưởng trực tiếp rồi verify lại full smoke matrix qua `http://localhost:8080`

## Runtime Action

Lệnh đã chạy:

```powershell
docker compose -f backend-microservices/docker-compose.yml up -d --build --force-recreate gateway-service-go chatbot-service-fastapi
```

Phạm vi giữ tối thiểu:

- `gateway-service-go`
- `chatbot-service-fastapi`

Không recreate `parksmart_nginx` vì sau recreate hai service đích, ingress `localhost:8080` đã trả đúng contract mới; không còn dấu hiệu route cache/proxy cache giữ behavior cũ.

## Container Evidence

| Container                 | Created                          | StartedAt                        | Health    |
| ------------------------- | -------------------------------- | -------------------------------- | --------- |
| `gateway-service-go`      | `2026-03-16T02:06:29.184475572Z` | `2026-03-16T02:06:34.440364691Z` | `healthy` |
| `chatbot-service-fastapi` | `2026-03-16T02:06:16.116480763Z` | `2026-03-16T02:06:32.812435482Z` | `healthy` |

## Kết quả tổng thể

**PASS**

Kết luận:

- Runtime hiện đã phản ánh patch mới của gateway cho refresh-shaped routes.
- Runtime hiện đã phản ánh patch mới của chatbot cho cả slash và no-slash health endpoints.
- Không còn HTML 404 ở refresh routes.
- Không còn `307` redirect hoặc `Location` lộ internal host ở chatbot health.

## Endpoint Matrix

| Endpoint                                   | Actual status | Content-Type                      | Location  | Body snippet                                                                                                                                                                     | Verdict  |
| ------------------------------------------ | ------------- | --------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| `GET /api/health`                          | `200`         | `application/json; charset=utf-8` | _(empty)_ | `{"service":"gateway-service","status":"healthy","version":"1.0.0"}`                                                                                                             | Expected |
| `POST /api/auth/login/` với credential sai | `400`         | `application/json`                | _(empty)_ | `{"nonFieldErrors":["Invalid email or password"]}`                                                                                                                               | Expected |
| `GET /api/auth/me/`                        | `403`         | `application/json`                | _(empty)_ | `{"detail":"Authentication credentials were not provided."}`                                                                                                                     | Expected |
| `POST /api/auth/logout/`                   | `200`         | `application/json; charset=utf-8` | _(empty)_ | `{"message":"Logged out successfully"}`                                                                                                                                          | Expected |
| `POST /api/auth/refresh/`                  | `404`         | `application/json; charset=utf-8` | _(empty)_ | `{"error":{"code":"ERR_NOT_FOUND","details":["/api/auth/refresh/"],"message":"Refresh endpoint is not supported in the current session-based auth flow"},"success":false}`       | Expected |
| `POST /api/auth/token/refresh/`            | `404`         | `application/json; charset=utf-8` | _(empty)_ | `{"error":{"code":"ERR_NOT_FOUND","details":["/api/auth/token/refresh/"],"message":"Refresh endpoint is not supported in the current session-based auth flow"},"success":false}` | Expected |
| `GET /api/bookings/`                       | `401`         | `application/json; charset=utf-8` | _(empty)_ | `{"detail":"Authentication credentials were not provided."}`                                                                                                                     | Expected |
| `GET /api/vehicles/`                       | `401`         | `application/json; charset=utf-8` | _(empty)_ | `{"detail":"Authentication credentials were not provided."}`                                                                                                                     | Expected |
| `GET /api/parking/health/`                 | `200`         | `application/json`                | _(empty)_ | `{"status": "ok", "service": "parking-service"}`                                                                                                                                 | Expected |
| `GET /api/chatbot/health`                  | `200`         | `application/json`                | _(empty)_ | `{"status":"healthy","service":"chatbot-service","version":"3.0.0"}`                                                                                                             | Expected |
| `GET /api/chatbot/health/`                 | `200`         | `application/json`                | _(empty)_ | `{"status":"healthy","service":"chatbot-service","version":"3.0.0"}`                                                                                                             | Expected |

## Contract Assessment

Expected theo contract hiện tại:

- Auth runtime là session-based, không support refresh token flow public; refresh-shaped routes phải fail có chủ đích bằng JSON error.
- Logout unauthenticated trả `200` là acceptable.
- Chatbot health phải support cả `/api/chatbot/health` và `/api/chatbot/health/` mà không redirect lộ internal host.

Observed sau recreate:

- Refresh routes trả JSON contract error từ gateway với `success=false` và `error.code=ERR_NOT_FOUND`.
- `POST /api/auth/logout/` vẫn `200 JSON` khi không có session.
- Cả hai chatbot health endpoints đều `200 JSON`, không có `Location`, không có redirect, không lộ host nội bộ.

## Remaining Blockers

Không còn blocker trong scope verify này.

## Notes

- Header check riêng cho chatbot health cho thấy cả hai endpoint đều trả từ server `uvicorn` với `status=200` và `location=` rỗng.
- Ingress `localhost:8080` đang phản ánh cùng behavior đúng contract sau recreate, nên runtime mismatch trước đó đã được giải quyết.
