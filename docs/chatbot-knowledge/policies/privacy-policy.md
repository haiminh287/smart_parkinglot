---
title: Chính sách bảo mật dữ liệu
category: policies
keywords: privacy, bảo mật, GDPR, dữ liệu cá nhân, biển số, camera
---

# Chính sách bảo mật ParkSmart

## Dữ liệu thu thập

### Thông tin đăng ký
- Họ tên, email, số điện thoại
- Mật khẩu (mã hóa bcrypt, không thể reverse)
- Địa chỉ (không bắt buộc)

### Thông tin xe
- Biển số, loại xe, màu xe
- Ảnh biển số (do camera AI chụp khi check-in/out)

### Thông tin giao dịch
- Lịch sử booking, check-in/out time
- Phương thức thanh toán (không lưu số thẻ đầy đủ, chỉ 4 số cuối)
- Doanh thu ẩn danh cho analytics

### Camera footage
- Camera gate: ghi biển số + ảnh xe đi qua
- Camera slot: ghi trạng thái đậu xe
- **Không dùng nhận diện mặt** — chỉ object detection
- Lưu trữ 30 ngày rồi tự xoá

## Dùng dữ liệu làm gì

1. **Vận hành bãi:** Verify biển số, mở barrier, tính tiền
2. **Notification:** Gửi email/push khi booking confirm, gần hết giờ, thanh toán
3. **Support:** Khi user chat chatbot, dùng lịch sử để trả lời context
4. **Analytics:** Thống kê ẩn danh (giờ cao điểm, occupancy) — không lộ user cá nhân
5. **AI training:** Biển số đã mask → train OCR model

## KHÔNG làm gì

- ❌ Không bán data cho quảng cáo
- ❌ Không chia sẻ với bên thứ 3 (trừ khi có lệnh tòa án)
- ❌ Không nhận diện mặt user
- ❌ Không track GPS khi user không đang trong bãi

## Quyền của user

Theo luật An ninh mạng VN 2018 + GDPR (tham khảo):

1. **Quyền truy cập:** Xem toàn bộ data đã lưu → API `/users/me/data-export`
2. **Quyền sửa:** Chỉnh thông tin qua Settings
3. **Quyền xoá:** Yêu cầu xoá tài khoản + data qua `privacy@parksmart.com` (xử lý ≤ 30 ngày)
4. **Quyền hạn chế:** Tạm ngưng xử lý data (freeze account)
5. **Quyền portability:** Export JSON toàn bộ data của mình

## Bảo mật kỹ thuật

- **HTTPS toàn bộ:** Cloudflare SSL + HSTS
- **Password:** bcrypt cost factor 12
- **Session:** HttpOnly cookie, SameSite=Lax, Secure flag production
- **API:** Gateway secret + session check, không expose service trực tiếp
- **Database:** MySQL với user riêng cho mỗi service (least privilege)
- **Backup:** Daily, mã hóa AES-256, lưu 30 ngày

## Vi phạm bảo mật

Nếu phát hiện data breach:

- Thông báo user trong vòng 72h qua email
- Công bố trên website (nếu ảnh hưởng > 100 user)
- Phối hợp cơ quan chức năng

## Cookies

ParkSmart dùng cookie cho:
- `session_id` — authentication, bắt buộc
- `preferences` — theme, ngôn ngữ (tùy chọn)

**KHÔNG dùng** tracking cookie của bên thứ 3.

## Liên hệ DPO (Data Protection Officer)

privacy@parksmart.com

Mọi thắc mắc về data sẽ được phản hồi trong vòng 7 ngày làm việc.
