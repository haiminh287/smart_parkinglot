---
title: Phương thức thanh toán
category: policies
keywords: thanh toán, payment, MoMo, VNPay, cash, tiền mặt, thẻ, hoàn tiền, hóa đơn
---

# Phương thức thanh toán ParkSmart

## 3 lựa chọn thanh toán

### 1. Thanh toán online trước (Prepaid)

- **MoMo:** quét QR trong app → trừ tiền tức thì
- **VNPay / ZaloPay / ShopeePay:** tương tự QR
- **Thẻ tín dụng/ghi nợ:** Visa, Mastercard, JCB, thẻ nội địa ATM
- **Chuyển khoản ngân hàng:** hiển thị thông tin ngân hàng trong booking detail

**Ưu điểm:** Vào bãi không cần xếp hàng trả tiền, barrier mở nhanh.

### 2. Thanh toán tại cổng (On-exit) — Cash

- Khi ra khỏi bãi, dừng tại cổng exit
- Popup hiện số tiền cần trả + gợi ý mệnh giá
- Đưa tiền mặt vào ô thu → **AI nhận diện mệnh giá tự động** (9 mệnh giá: 1k/2k/5k/10k/20k/50k/100k/200k/500k)
- Đủ tiền → barrier mở + thối tiền tự động

**Ưu điểm:** Không cần chuẩn bị thanh toán online trước, user có tiền mặt.

### 3. Thanh toán tại cổng — Thẻ

Tap thẻ NFC / quẹt thẻ tại POS → trừ tiền → mở cổng.

## Hoàn tiền

| Nguyên nhân | Thời gian hoàn | Hình thức |
|---|---|---|
| Hủy booking | 1-3 ngày làm việc | Về ví/thẻ đã thanh toán |
| Bãi đóng cửa đột xuất | Ngay lập tức | Voucher + chuyển khoản |
| Thanh toán trùng | 24h | Tự động refund |
| Cash quá tiền | Ngay tại cổng | Thối tiền ngay |

## Hóa đơn thuế VAT

- Booking ≥ 100.000đ → hệ thống tự động xuất hóa đơn điện tử
- User nhập MST công ty ở phần **Settings → Thông tin doanh nghiệp**
- Hóa đơn gửi về email đã đăng ký
- Liên hệ kế toán: billing@parksmart.com

## Bảo mật thanh toán

- ParkSmart không lưu số thẻ ở server
- Mọi giao dịch đi qua cổng thanh toán được cấp PCI DSS (VNPay, MoMo)
- Session HTTPS + HttpOnly cookie → không bị đánh cắp trong browser

## Xử lý lỗi thanh toán

**Trường hợp: Trả tiền mặt nhưng AI nhận diện sai**

- Nếu AI từ chối tờ tiền (không nhận ra) → popup hiện "Không nhận diện được — chụp lại"
- Nếu cần thiết, ấn nút **"Cần trợ giúp"** → gọi staff trực
- Staff có thể override manual nếu user không thể thanh toán AI

**Trường hợp: MoMo báo fail nhưng tiền đã bị trừ**

- Bình tĩnh, liên hệ hotline 1900-PARKSMART
- Cung cấp `booking_id` + mã giao dịch MoMo
- Hoàn tiền trong 24h hoặc mở barrier manual ngay

## Liên hệ

Hỗ trợ thanh toán: billing@parksmart.com
Báo sự cố: 1900-PARKSMART
