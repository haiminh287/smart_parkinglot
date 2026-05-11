---
title: Xử lý sự cố thường gặp
category: faq
keywords: troubleshooting, sự cố, lỗi, barrier, cổng, QR, OCR
---

# Xử lý sự cố ParkSmart

## Sự cố check-in

### Barrier không mở sau khi bấm nút

**Chẩn đoán:**
1. Xem màn hình ESP32 có hiển thị kết quả gì không
2. Check LED: đỏ = fail, xanh = success

**Nguyên nhân + cách xử lý:**

| Thông báo | Nguyên nhân | Cách xử lý |
|---|---|---|
| "Booking không tồn tại" | QR hết hạn hoặc booking đã check-in | Kiểm tra lại booking trong app |
| "Biển số không khớp" | AI đọc biển sai hoặc xe khác | Lùi xe lại, tiến gần camera hơn, thử lại |
| "Chưa đến giờ đặt" | Đến sớm hơn 15p | Chờ thêm vài phút hoặc đổi booking |
| "Không đọc được biển số" | Biển bẩn, nghiêng, mờ | Lau biển, chỉnh xe thẳng |
| "Lỗi hệ thống" | Backend / network down | Gọi bảo vệ mở manual |

### QR code hết hạn

QR code có TTL 48h. Sau thời gian đó, mở app → **Lịch sử → Booking → Refresh QR** để tạo QR mới.

### Camera OCR đọc biển sai

- Tiến xe gần hơn (cách camera 2-3m)
- Chỉnh xe thẳng (không nghiêng)
- Ban đêm: bật đèn pha
- Nếu 3 lần vẫn fail → gọi staff nhập manual

## Sự cố check-out

### Không tìm thấy booking khi check-out

- Xe chưa check-in → phải check-in trước
- Xe của người khác → staff phối hợp

### Không trả được tiền mặt (AI reject)

- Tờ tiền mới (chưa update model) → bấm "Thử lại" với tờ khác
- Tờ tiền cũ bị nhăn → dùng tờ khác
- Ánh sáng kém → di chuyển gần đèn
- Cuối cùng: bấm **"Cần trợ giúp"** → staff override

### Payment MoMo báo thành công nhưng barrier không mở

- Đợi 30s (có thể backend xử lý chậm)
- Nếu vẫn không mở: chụp màn hình xác nhận MoMo → đưa staff
- Support sẽ hoàn tiền nếu không thể giải quyết trong 10 phút

### Phí overtime quá cao

Công thức: `(actual_end - booked_end) × 1.5 × hourly_rate`

Ví dụ: booking 10h-12h, ra lúc 13h30 → overtime 1h30 → phí thêm `1.5h × 1.5 × 20k = 45k`

Nếu bạn cho rằng phí sai → yêu cầu audit log qua support.

## Sự cố app / web

### Không login được

1. Kiểm tra email + password đúng
2. Nếu "account locked" → quên mật khẩu → reset
3. Nếu "email not verified" → check hộp thư (cả spam) → click link verify
4. Browser không nhận cookie → thử Chrome/Edge + tắt extension ad-block

### App load chậm

- Refresh trang (Ctrl+F5)
- Clear cache browser
- Network slow → thử mạng khác
- Nếu nhiều user cùng vào → giờ cao điểm, chờ 5 phút

### Notification không nhận được

- Settings → Notifications → bật On
- Allow permission browser (icon chuông cạnh address bar)
- Telegram bot: `/start` với bot `@ParkSmartBot` để link account

## Sự cố xe trong bãi

### Xe bị xước / móp

- Báo ngay bảo vệ tại bãi
- Chụp ảnh biên bản
- Yêu cầu xem camera từ lúc xe vào → ra
- Nếu xác định người khác gây → họ bồi thường qua bảo hiểm
- Nếu không xác định được → gửi khiếu nại về claims@parksmart.com

### Xe bị trộm

- Báo bảo vệ + công an khu vực ngay
- ParkSmart cung cấp footage camera 30 ngày gần nhất
- Làm đơn yêu cầu bồi thường (nếu mua gói premium có bảo hiểm)

### Quên đồ trong xe

- Nhân viên lễ tân có dịch vụ gửi đồ hộ (100k/lượt)
- Liên hệ bãi trực tiếp, cung cấp biển + slot code

## Sự cố tài khoản

### Không nhận được email

- Check spam
- Email đăng ký sai (typo) → chat support để sửa
- Email bị bounce (gmail từ chối) → dùng email khác

### Force online payment (no-show > 3 lần)

Tình huống: bạn cancel quá nhiều → hệ thống block không cho pay on-exit.

**Cách dỡ block:**
- Chờ 30 ngày không no-show → tự unlock
- Liên hệ support giải thích lý do → admin review manual

## Khi nào liên hệ hotline?

**Gọi 1900-PARKSMART (24/7):**
- Xe hỏng, mất, bị đụng trong bãi
- Không ra khỏi bãi được (barrier stuck)
- Thanh toán bị lỗi > 15 phút
- Cháy, nổ, sự cố nghiêm trọng

**KHÔNG gọi hotline:**
- Hỏi chính sách → dùng chatbot
- Quên password → tự reset trong app
- Đặt chỗ → tự làm trên web

## Emergency button (trong app)

Kích hoạt trên home screen → gọi direct bảo vệ gần nhất + GPS location. Dùng khi:
- Bị đe doạ
- Bị đụng nặng, chấn thương
- Cháy nổ
