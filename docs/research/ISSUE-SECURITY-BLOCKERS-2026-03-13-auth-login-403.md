# Research Report: Root Cause 403 cho POST /api/auth/login/

**Task:** ISSUE-SECURITY-BLOCKERS-2026-03-13 | **Date:** 2026-03-15 | **Type:** Codebase

## 1) Kết luận nhanh

1. Root cause chính: Gateway chặn CORS do origin localhost không nằm trong cấu hình runtime hiện tại, nên request bị 403 trước khi vào login handler.
2. Luồng login không đi qua auth middleware của gateway, mà đi qua special route POST auth/login và forward thẳng tới auth-service.
3. Secondary risk: gateway login forward không gắn X-Gateway-Secret; hiện không gây lỗi vì auth login được đánh public ở Django middleware, nhưng là điểm dễ vỡ khi policy siết chặt.

## 2) Request path thực tế và điểm phát 403

Client gọi: POST http://localhost:8080/api/auth/login/

Luồng xử lý:
1. Vite dev proxy rewrite /api thành / và forward sang gateway.
2. Gateway catch-all route normalize path thành auth/login.
3. Gateway match special route POST auth/login và gọi HandleLogin.
4. Nếu qua được middleware CORS thì HandleLogin forward tới auth-service /auth/login/.

Điểm phát 403 chắc chắn nhất: CORS middleware ở gateway (trước router logic), vì runtime env của gateway chỉ allow production origin.

## 3) Evidence (file/path + logic)

- Frontend proxy /api -> gateway và rewrite bỏ /api:
  - [spotlove-ai/vite.config.ts](spotlove-ai/vite.config.ts#L47)
  - [spotlove-ai/vite.config.ts](spotlove-ai/vite.config.ts#L60)
- Gateway áp CORS middleware toàn cục trước route:
  - [backend-microservices/gateway-service-go/internal/router/routes.go](backend-microservices/gateway-service-go/internal/router/routes.go#L29)
- CORS middleware chỉ cho origin theo cfg.CORSAllowedOrigins:
  - [backend-microservices/gateway-service-go/internal/middleware/cors.go](backend-microservices/gateway-service-go/internal/middleware/cors.go#L14)
- Runtime env gateway hiện tại chỉ cho production origin (không có localhost):
  - [backend-microservices/gateway-service-go/.env](backend-microservices/gateway-service-go/.env#L16)
- Route login là special route của gateway:
  - [backend-microservices/gateway-service-go/internal/router/routes.go](backend-microservices/gateway-service-go/internal/router/routes.go#L63)
- HandleLogin forward sang auth-service /auth/login/:
  - [backend-microservices/gateway-service-go/internal/handler/auth.go](backend-microservices/gateway-service-go/internal/handler/auth.go#L56)
- Auth-service map /auth/login/ đúng endpoint:
  - [backend-microservices/auth-service/auth_service/urls.py](backend-microservices/auth-service/auth_service/urls.py#L13)
  - [backend-microservices/auth-service/users/urls.py](backend-microservices/auth-service/users/urls.py#L15)
- Django gateway middleware chỉ trả 403 khi non-public thiếu/khác secret; login đang là public path:
  - [backend-microservices/shared/gateway_middleware.py](backend-microservices/shared/gateway_middleware.py#L34)
  - [backend-microservices/shared/gateway_middleware.py](backend-microservices/shared/gateway_middleware.py#L45)

## 4) Root cause

Primary:
- Gateway CORS misconfiguration ở runtime local: origin thực tế localhost:8080 không nằm trong CORS_ALLOWED_ORIGINS hiện tại của gateway, dẫn đến 403 tại lớp CORS middleware.

Secondary (không phải nguyên nhân trực tiếp của lỗi hiện tại):
- HandleLogin không set header X-Gateway-Secret khi gọi auth-service, khác với ProxyHandler và OAuth callback. Điều này không gây lỗi với login hiện tại do public path, nhưng tạo risk nếu policy middleware thay đổi hoặc route/login path bị refactor.

## 5) Tác động toàn bộ API auth

- Ảnh hưởng trực tiếp khi test từ localhost origin không allow:
  - Tất cả request auth qua gateway theo đường /api/auth/* có thể fail tại CORS, không chỉ login.
- Endpoint public auth vẫn public ở auth-service, nhưng không tới được nếu bị chặn ở gateway CORS lớp ngoài.
- Endpoint protected auth như /auth/me/ còn có thêm lớp yêu cầu gateway headers/session; tuy nhiên lỗi hiện tại xuất hiện sớm hơn tại CORS.

## 6) Fix proposal tối thiểu, an toàn

Bước 1 (bắt buộc):
- Cập nhật runtime env gateway cho local dev để include localhost origins đang dùng (ví dụ localhost:8080, localhost:5173).
- Scope sửa: [backend-microservices/gateway-service-go/.env](backend-microservices/gateway-service-go/.env#L16)

Bước 2 (an toàn thêm, tránh drift):
- Đồng bộ sample env để không tái phát khi onboarding:
  - [backend-microservices/gateway-service-go/.env.example](backend-microservices/gateway-service-go/.env.example#L18)

Bước 3 (hardening nhẹ, không phá security):
- Trong HandleLogin, thêm X-Gateway-Secret khi forward sang auth-service để hành vi nhất quán với các luồng nội bộ khác.
- Scope sửa: [backend-microservices/gateway-service-go/internal/handler/auth.go](backend-microservices/gateway-service-go/internal/handler/auth.go#L61)

Bước 4 (khuyến nghị vận hành):
- Tách profile env local/prod rõ ràng, tránh dùng production CORS trong local.

## 7) Regression risks

- Nếu mở CORS wildcard hoặc mở quá rộng có thể tăng bề mặt tấn công CSRF/CORS abuse.
- Nếu thêm X-Gateway-Secret cho login nhưng vô tình log header nhạy cảm có thể lộ secret qua log.
- Nếu đổi path/login policy trong shared gateway middleware mà quên public-path list, login có thể quay lại 403.

## 8) Checklist test sau fix

1. POST từ browser localhost:8080 vào /api/auth/login/ trả 200 hoặc 400 (sai credential), không còn 403.
2. OPTIONS preflight cho /api/auth/login/ trả 200/204 và có Access-Control-Allow-Origin đúng origin local.
3. POST /api/auth/register/ và /api/auth/forgot-password/ từ local origin không 403.
4. GET /api/auth/me/ không login trả 401/403 theo auth logic, không phải CORS 403.
5. Luồng production origin hiện có vẫn pass (không regression).
6. Kiểm tra log gateway không in ra giá trị secret.

## 9) File/symbol implementer cần mở nhanh

- [backend-microservices/gateway-service-go/.env](backend-microservices/gateway-service-go/.env#L16)
- [backend-microservices/gateway-service-go/.env.example](backend-microservices/gateway-service-go/.env.example#L18)
- [backend-microservices/gateway-service-go/internal/middleware/cors.go](backend-microservices/gateway-service-go/internal/middleware/cors.go#L14)
- [backend-microservices/gateway-service-go/internal/router/routes.go](backend-microservices/gateway-service-go/internal/router/routes.go#L63)
- [backend-microservices/gateway-service-go/internal/handler/auth.go](backend-microservices/gateway-service-go/internal/handler/auth.go#L47)
- [backend-microservices/shared/gateway_middleware.py](backend-microservices/shared/gateway_middleware.py#L34)
- [backend-microservices/auth-service/users/urls.py](backend-microservices/auth-service/users/urls.py#L15)
