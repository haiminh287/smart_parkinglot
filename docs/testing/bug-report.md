## Bug Report: BUG-FE-REGRESSION-001

### Mức độ: High

### Mô tả

Regression ở FE test suite sau đợt fix `SupportPage`: test fallback local response không còn match output UI hiện tại.

### Steps to Reproduce

1. Vào thư mục `spotlove-ai`.
2. Chạy `npm run test`.
3. Quan sát test fail ở `src/test/support-page.test.tsx`.

### Expected Behavior

Case `falls back to local response on API error` pass theo behavior fallback đã định nghĩa.

### Actual Behavior

Test fail với thông báo không tìm thấy text `/Bảng giá dịch vụ/`.

### Error Logs

`Unable to find an element with the text: /Bảng giá dịch vụ/` tại `src/test/support-page.test.tsx:291`.

### Environment

- Node version: dùng runtime local hiện tại
- OS: Windows
- Dependencies: theo `spotlove-ai/package.json`

### Screenshots / Evidence

- Log từ `vitest` trong session test hiện tại.

---

## Bug Report: BUG-BE-ENV-DB-002

### Mức độ: High

### Mô tả

Backend integration tests cho chatbot/payment bị chặn do DB access không hợp lệ trong môi trường test sau khi đã đồng bộ gateway secret.

### Steps to Reproduce

1. Vào service `backend-microservices/chatbot-service-fastapi` hoặc `backend-microservices/payment-service-fastapi`.
2. Set env tối thiểu:
   - `DB_USER=test_user`
   - `DB_PASSWORD=test_password`
   - `GATEWAY_SECRET=gateway-internal-secret-key`
3. Chạy pytest (`-q`, payment dùng thêm `--maxfail=1` để xác nhận nhanh).

### Expected Behavior

Tests không bị fail vì kết nối DB; các case business chạy qua tầng router/service.

### Actual Behavior

Nhiều case fail với lỗi SQLAlchemy/PyMySQL `OperationalError (1045) Access denied`.

### Error Logs

- Chatbot: `14 failed, 77 passed, 1 warning` với lỗi `Access denied for user 'test_user'@'localhost'`.
- Payment (xác nhận nhanh): `1 failed, 1 passed, 1 warning` (`--maxfail=1`) với lỗi `Access denied for user 'test_user'@'172.20.0.1'`.

### Environment

- Python: 3.10.5
- OS: Windows
- Test runner: pytest 9.0.2

### Screenshots / Evidence

- Pytest output logs từ session regression hiện tại.

---

## Bug Report: BUG-BE-DJANGO-SMOKE-003

### Mức độ: High

### Mô tả

Smoke check sau backend dependency remediation cho `booking-service` fail khi boot Django app do thiếu module `celery`.

### Steps to Reproduce

1. Vào thư mục `backend-microservices/booking-service`.
2. Chạy `..\venv\Scripts\python.exe manage.py check`.
3. Quan sát exception khi import `booking_service.celery`.

### Expected Behavior

`manage.py check` hoàn tất với `System check identified no issues` tương tự các Django services còn lại.

### Actual Behavior

Lệnh fail với `ModuleNotFoundError: No module named 'celery'`.

### Error Logs

- `booking_service/__init__.py` import `.celery`
- `booking_service/celery.py` import `from celery import Celery`
- Runtime: `ModuleNotFoundError: No module named 'celery'`

### Environment

- Python: backend venv tại `backend-microservices/venv`
- OS: Windows
- Command: `python manage.py check`

### Screenshots / Evidence

- `docs/testing/backend-django-manage-check.txt`
