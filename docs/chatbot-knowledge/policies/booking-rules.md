---
title: Quy định đặt chỗ giữ xe
category: policies
keywords: đặt chỗ, booking, rules, grace period, đi trễ, đi sớm, thời gian
---

# Quy định đặt chỗ ParkSmart

## Loại package thời gian

| Package | Thời lượng | Giá ô tô | Giá xe máy |
|---|---|---|---|
| **Hourly (theo giờ)** | Tối thiểu 1h, tối đa 12h/ngày | 20.000đ/giờ | 5.000đ/giờ |
| **Daily (ngày)** | 0h-23h59 | 200.000đ/ngày | 50.000đ/ngày |
| **Weekly (tuần)** | 7 ngày liên tiếp | 1.000.000đ/tuần | 250.000đ/tuần |
| **Monthly (tháng)** | 30 ngày liên tiếp | 3.500.000đ/tháng | 900.000đ/tháng |

## Giờ check-in / check-out

- **Đến sớm (grace period):** Cho phép vào bãi **tối đa 15 phút trước** `start_time`
- **Đến muộn:** Nếu đến sau `start_time` + 30 phút mà chưa check-in → booking tự động chuyển thành **no-show**, slot được release
- **Trả sớm (check-out trước end_time):** Được phép — hệ thống tính tiền theo thời gian thực tế (hourly)
- **Trả trễ (overtime):** Sau `end_time` + 30 phút → tính phí late fee **1.5× giá giờ** cho mỗi giờ overtime

## Grace period chi tiết

```
[start_time - 15p] ────── [start_time] ────── [start_time + 30p] ────── [end_time] ────── [end_time + 30p] ────── trễ hơn
     ↑ cho vào sớm         ↑ giờ chính thức     ↑ no-show nếu chưa đến    ↑ phải ra         ↑ bắt đầu tính late fee
```

## Booking nhiều ngày (multi-day)

Package `daily` chỉ cover 1 ngày. Muốn đỗ 5 ngày → chọn `custom` + pick 5 ngày trong lịch.

**Lưu ý:** Xe phải ra trước 23h59 mỗi ngày, ngày hôm sau check-in lại. Nếu muốn để xe qua đêm → chọn package weekly/monthly.

## Loại xe được hỗ trợ

- ✅ Ô tô (sedan, SUV, hatchback) — tối đa 5 chỗ
- ✅ Xe máy (scooter, underbone, naked)
- ✅ Xe điện (EV có ổ sạc ở slot được chỉ định)
- ⚠️ Xe bán tải (pickup) — chỉ một số bãi có slot đủ dài
- ❌ Xe tải > 3.5 tấn — không hỗ trợ
- ❌ Xe container, xe khách — không hỗ trợ

## Biển số xe

- Chỉ nhận biển Việt Nam theo định dạng: 2 số + 1-2 chữ + 4-5 số (ví dụ: `51A-12345`, `30A-123.45`)
- Xe không biển / biển nước ngoài → liên hệ staff để đăng ký manual

## Giới hạn số booking đồng thời

- Mỗi tài khoản: tối đa **5 booking active** cùng lúc (active = not_checked_in hoặc checked_in)
- Nếu vượt → phải hủy booking cũ hoặc check-out xe trước khi đặt mới

## Thay đổi booking

- **Gia hạn thời gian (extend):** Được — tại page History bấm "Gia hạn" + nhập thêm X giờ. Phí gia hạn = X giờ × giá hourly
- **Đổi slot:** Không — phải hủy booking cũ + đặt mới
- **Đổi xe:** Không — booking gắn chặt với 1 xe cụ thể

## Liên hệ

support@parksmart.com — phản hồi 24/7
