---
title: Câu hỏi thường gặp (FAQ)
category: faq
keywords: FAQ, câu hỏi, đăng ký, đặt chỗ, thanh toán, hủy, check-in
---

# Câu hỏi thường gặp

## 1. Đăng ký & Tài khoản

### Làm sao đăng ký tài khoản ParkSmart?

1. Vào web `parksmart.ghepdoicaulong.shop/register`
2. Điền email + mật khẩu (≥ 8 ký tự, có số + chữ hoa)
3. Kiểm tra email → click link xác thực
4. Đăng nhập + thêm xe (biển số, loại)

Hoặc đăng ký nhanh qua **Google OAuth / Facebook OAuth**.

### Quên mật khẩu?

Vào trang login → click **"Quên mật khẩu"** → nhập email → nhận link reset trong 5 phút.

### Muốn đổi email đăng ký?

Vào **Settings → Account** → đổi email. Hệ thống gửi OTP về email cũ + mới để xác nhận.

### Bao nhiêu tài khoản / 1 người?

- Chính sách: 1 người = 1 tài khoản
- Vi phạm: nếu phát hiện nhiều account từ cùng thiết bị + IP → admin có thể khoá

## 2. Đặt chỗ

### Đặt chỗ trước bao xa?

- **Tối thiểu:** 15 phút trước start_time
- **Tối đa:** 30 ngày trước (xa hơn không cho phép để tránh spam)

### Có thể đặt nhiều booking cùng lúc?

Có — tối đa **5 booking active** / tài khoản.

### Booking có bị ăn cắp slot của người khác không?

Không — khi đặt thành công, slot `status=reserved` → người khác không đặt được. Bạn có full quyền cho tới khi `end_time + 30p`.

### Đặt nhầm giờ → sửa thế nào?

Không sửa được. **Hủy booking cũ + đặt mới**. Phí hủy theo chính sách.

## 3. Check-in / Check-out

### Đến sớm có vào được không?

Được — cho phép vào **tối đa 15 phút trước** start_time.

### Đến trễ thì sao?

- Đến sau start_time 30p → booking tự động **no-show**, slot bị release, mất 100% tiền
- Đến sớm hơn 15p → vẫn cho vào bình thường

### Biển số xe khác với booking?

Nếu AI đọc biển sai 1 ký tự → hệ thống vẫn accept (Levenshtein ≤ 1). Nếu khác 2+ ký tự → reject, phải liên hệ staff.

### Không có QR code thì sao?

QR tự tạo khi đặt booking. Mở app ParkSmart → **Lịch sử → Booking hiện tại → Show QR**. Hoặc staff có thể verify bằng biển số.

### Trả xe sớm có được giảm tiền?

Chỉ package `hourly` được tính theo thời gian thực. Daily/weekly/monthly → trả trước cũng vẫn tính full.

## 4. Thanh toán

### Chấp nhận phương thức nào?

- Online trước: MoMo, VNPay, ZaloPay, ShopeePay, thẻ Visa/Master/JCB, chuyển khoản
- Tại cổng: Cash (tiền mặt), thẻ tap NFC

### Tiền mặt có được không?

Có — AI nhận diện 9 mệnh giá VND (1k/2k/5k/10k/20k/50k/100k/200k/500k).

### AI nhận diện sai tiền → sao giải quyết?

- Nếu AI từ chối tờ tiền → popup yêu cầu chụp lại
- Nếu sau 3 lần vẫn fail → ấn **"Cần trợ giúp"** → gọi staff override manual
- Không bao giờ hệ thống tự trừ tiền sai (precision ≥ 99.5%)

### Có hóa đơn VAT không?

Có — booking ≥ 100k tự động xuất hóa đơn điện tử. Thêm MST công ty ở **Settings → Thông tin doanh nghiệp**.

## 5. Hủy / Hoàn tiền

### Chính sách hủy?

- Trước start_time 30p: miễn phí, hoàn 100%
- Trong 30p trước start_time: phí 10%, hoàn 90%
- No-show: mất 100%

### Bao lâu nhận lại tiền?

- MoMo/VNPay: 1-3 ngày làm việc
- Thẻ tín dụng: 5-7 ngày
- Cash: phải đến quầy lễ tân nhận mặt

## 6. Kỹ thuật

### App có chạy offline không?

- Xem lịch sử booking: Có (PWA cache)
- Đặt booking mới: Không (cần internet)
- Check-in: Cần — barrier phụ thuộc backend

### Có app mobile native không?

Hiện tại chỉ **PWA** (Progressive Web App). Add to Home Screen trên iOS/Android được. Native app đang planning.

### Chatbot dùng AI gì?

Google Gemini (tiếng Việt OK) + Chroma vector database cho FAQ. Có thể trả câu hỏi về chính sách, bãi xe, biển số.

## 7. Xe đặc biệt

### Xe điện có trạm sạc?

Có — tại Vincom Tower, ParkSmart Tower, Saigon Centre. Sạc 3.500đ/kWh.

### Xe 7 chỗ / SUV lớn?

Được — nhưng slot thường có thể chật. Nên chọn **slot garage** (3m × 6m) hoặc zone EV lớn hơn.

### Xe không biển?

Liên hệ staff manual. Chưa auto OCR được.

## 8. Khẩn cấp

### Xe bị trộm / hư hại trong bãi?

1. Báo ngay cho bảo vệ
2. Cung cấp biển số + thời gian
3. Yêu cầu xem footage camera
4. Liên hệ hotline 1900-PARKSMART (24/7)

### Quên xe trong bãi quá hạn?

- Overtime: tính 1.5× giá hourly
- Nếu > 48h không ra → ParkSmart khoá xe + gọi user qua SĐT đăng ký
- Chi phí cứu hộ + giải phóng: 500.000đ + tiền phạt quá hạn

### Liên hệ khẩn cấp

- **Hotline:** 1900-PARKSMART (24/7, free)
- **Emergency button:** trong app, kích hoạt → gọi trực tiếp bảo vệ gần nhất
