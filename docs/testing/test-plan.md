# Test Plan — Regression sau fix critical/prompt integration (2026-03-13)

## Test Scope

- Frontend changed areas: `SupportPage`, `vite.config`, `websocket service`.
- Frontend quick broad checks: Vitest unit/integration hiện có, FE build (`vite build`).
- Backend changed areas: `chatbot-service-fastapi` config, `payment-service-fastapi` config, `.env.example`.
- Backend quick regression: `pytest` cho chatbot/payment với env tối thiểu để thỏa guard bảo mật mới.

## Test Strategy

1. **Unit/Integration (FE)**
   - Chạy `npm run test` tại `spotlove-ai` để bắt regression logic/UI cơ bản.
2. **Build Verification (FE)**
   - Chạy `npm run build` để bắt lỗi bundling/config do thay đổi Vite/WebSocket.
3. **Service-focused Integration (BE)**
   - Chạy `pytest` tại:
     - `backend-microservices/chatbot-service-fastapi`
     - `backend-microservices/payment-service-fastapi`
   - Inject env test tối thiểu: `DB_USER`, `DB_PASSWORD`, `GATEWAY_SECRET` (dummy values, non-secret).
4. **Coverage Collection**
   - FE: thử chạy coverage qua Vitest nếu plugin/scripting hỗ trợ.
   - BE: lấy coverage nếu test setup service có hỗ trợ sẵn.

## Test Data / Env

- FE: không cần dữ liệu production; chạy theo test fixtures hiện có.
- BE env tối thiểu (test-only):
  - `DB_USER=test_user`
  - `DB_PASSWORD=test_password`
  - `GATEWAY_SECRET=test_gateway_secret`
- Không dùng API key thật hoặc credentials thật.

## Risk Areas

- Guard mới trong `Settings` (Pydantic `Field(..., min_length=1)`) có thể làm fail import app nếu thiếu env.
- Thay đổi `vite.config` có thể gây lỗi alias/build chunking ở production bundle.
- WebSocket service thay đổi có thể ảnh hưởng reconnect flow và runtime env resolution.
- Chưa tìm thấy `docs/api/openapi.yaml` tại path chuẩn; kiểm thử API sẽ dựa trên test hiện hữu trong repo.
