# Runtime Smoke Verification — Chatbot Health + Refresh Contract

**Ngày:** 2026-03-15

**Scope:** verify runtime cuối sau patch `chatbot health` + `refresh contract`

**Runtime action đã thực hiện:** restart tối thiểu 2 service bị ảnh hưởng trực tiếp

- `gateway-service-go`
- `chatbot-service-fastapi`

**Probe path:** `localhost:8080` qua Vite proxy. Do Vite chặn host header `host.docker.internal`, evidence được lấy bằng probe container gọi `http://host.docker.internal:8080/...` với header `Host: localhost:8080` để đi đúng tuyến runtime của `localhost:8080`.

## Kết quả tổng thể

**FAIL**

Lý do fail:

- `POST /api/auth/refresh/` và `POST /api/auth/token/refresh/` không trả JSON contract error từ gateway như patch mong đợi; runtime hiện trả HTML 404 từ downstream Django/Gunicorn.
- `GET /api/chatbot/health` chưa trả trực tiếp `200 JSON`; runtime hiện vẫn redirect `307` sang `/chatbot/health/` với `Location` nội bộ `http://chatbot-service-fastapi:8008/...`.
- Hai dấu hiệu trên cho thấy runtime container hiện tại chưa phản ánh patch mới, dù đã restart process.

## Endpoint Matrix

| Endpoint                                   | Actual status | Content-Type                      | Body snippet                                                         | Verdict    |
| ------------------------------------------ | ------------- | --------------------------------- | -------------------------------------------------------------------- | ---------- |
| `GET /api/health`                          | `200`         | `application/json; charset=utf-8` | `{"service":"gateway-service","status":"healthy","version":"1.0.0"}` | Expected   |
| `POST /api/auth/login/` với credential sai | `400`         | `application/json`                | `{"nonFieldErrors":["Invalid email or password"]}`                   | Expected   |
| `GET /api/auth/me/`                        | `403`         | `application/json`                | `{"detail":"Authentication credentials were not provided."}`         | Expected   |
| `POST /api/auth/logout/`                   | `200`         | `application/json; charset=utf-8` | `{"message":"Logged out successfully"}`                              | Expected   |
| `POST /api/auth/refresh/`                  | `404`         | `text/html; charset=utf-8`        | `<!doctype html><html lang="en"><head><title>Not Found</title>...`   | Unexpected |
| `POST /api/auth/token/refresh/`            | `404`         | `text/html; charset=utf-8`        | `<!doctype html><html lang="en"><head><title>Not Found</title>...`   | Unexpected |
| `GET /api/bookings/`                       | `401`         | `application/json; charset=utf-8` | `{"detail":"Authentication credentials were not provided."}`         | Expected   |
| `GET /api/vehicles/`                       | `401`         | `application/json; charset=utf-8` | `{"detail":"Authentication credentials were not provided."}`         | Expected   |
| `GET /api/parking/health/`                 | `200`         | `application/json`                | `{"status": "ok", "service": "parking-service"}`                     | Expected   |
| `GET /api/chatbot/health`                  | `307`         | _(empty)_                         | `Location: http://chatbot-service-fastapi:8008/chatbot/health/`      | Unexpected |
| `GET /api/chatbot/health/`                 | `200`         | `application/json`                | `{"status":"healthy","service":"chatbot-service","version":"3.0.0"}` | Expected   |

## Contract Assessment Sau Patch

Expected theo contract hiện tại:

- Auth runtime dùng gateway session cookie, nên hai refresh endpoint public không còn được support và phải fail rõ ràng từ gateway.
- Chatbot health phải support cả `/api/chatbot/health` và `/api/chatbot/health/`.

Unexpected tại runtime hiện tại:

- `POST /api/auth/refresh/`
- `POST /api/auth/token/refresh/`
- `GET /api/chatbot/health`

## Remaining Blockers

- `gateway-service-go` đang chạy runtime chưa expose JSON `ERR_NOT_FOUND` cho refresh routes như patch mô tả.
- `chatbot-service-fastapi` đang chạy runtime chưa serve trực tiếp route no-slash `/chatbot/health`.
- Chỉ restart container là chưa đủ; cần rebuild/recreate image của `gateway-service-go` và `chatbot-service-fastapi`, rồi rerun smoke matrix.
