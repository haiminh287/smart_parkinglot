---
title: Định dạng biển số xe Việt Nam
category: vehicles
keywords: biển số, license plate, format, đăng ký xe
---

# Định dạng biển số xe Việt Nam

## Biển số ô tô dân sự

Định dạng: **2 số tỉnh/TP + 1-2 chữ + 4-5 số**

Ví dụ:
- `51A-12345` (Sài Gòn, xe 5 chỗ)
- `51G-888.88` (Sài Gòn, biển đẹp)
- `30A-123.45` (Hà Nội)
- `43A-001.22` (Đà Nẵng)

## Mã tỉnh/thành phố

| Mã | Tỉnh/TP |
|---|---|
| 11-19 | Hà Nội + vùng Bắc Bộ |
| 20-29 | Trung du & Miền núi Bắc |
| 30-39 | Đồng bằng Sông Hồng |
| 40-49 | Bắc Trung Bộ |
| 50-59 | Nam Trung Bộ + Tây Nguyên |
| 50-59 | TP. HCM (chủ yếu 51, 59) |
| 60-69 | Đông Nam Bộ |
| 70-99 | Đồng bằng Sông Cửu Long |

## Mã chữ cái — loại xe

- **A, B, C:** Xe cá nhân
- **D:** Xe dịch vụ (taxi, grab)
- **E:** Xe cho thuê
- **F:** Xe tải
- **G:** Biển đẹp (trả phí cao, đấu giá)
- **H:** Xe motor rời
- **K, L, M, N:** Xe máy các loại
- **T:** Xe ngoại giao
- **NN:** Xe nước ngoài
- **NG:** Xe Nghị viện, Quốc hội
- **80:** Xe cơ quan trung ương
- **QH:** Xe Quốc hội

## Biển màu

- **Nền trắng, chữ đen:** Xe cá nhân, doanh nghiệp thường
- **Nền vàng, chữ đen:** Xe kinh doanh vận tải (grab, taxi, truck)
- **Nền xanh, chữ trắng:** Xe cơ quan nhà nước
- **Nền đỏ, chữ trắng:** Xe quân đội, công an
- **Nền trắng có "NN":** Xe nước ngoài

## Biển số xe máy

Định dạng: **2 số tỉnh + 1-2 chữ + 4-5 số**

Tương tự ô tô nhưng font nhỏ hơn.

## ParkSmart OCR — xử lý biển

Hệ thống AI của ParkSmart:

1. **Detect bbox biển số** bằng YOLOv8 fine-tune trên ~2000 ảnh biển VN
2. **OCR text** bằng EasyOCR (Vietnamese language pack)
3. **Normalize:** xoá các ký tự không phải chữ/số (dấu `-`, `.`, space)
   - `51A-123.45` → `51A12345`
   - `30 A 12345` → `30A12345`
4. **Validate format:** regex `^[0-9]{2}[A-Z]{1,2}[0-9]{4,5}$`
5. **Match với booking** bằng Levenshtein distance ≤ 1 (cho phép 1 ký tự sai do OCR)

## Xử lý ký tự OCR nhầm thường gặp

- `0` ↔ `O` — số 0 và chữ O
- `1` ↔ `I` — số 1 và chữ I
- `8` ↔ `B` — số 8 và chữ B
- `5` ↔ `S` — số 5 và chữ S
- `2` ↔ `Z` — số 2 và chữ Z

ParkSmart dùng context (format ví dụ phải có 2 số đầu) + Levenshtein để tự sửa.

## Xe không biển / biển tạm

- Xe mới đăng ký chưa có biển chính thức → dùng biển tạm (dán giấy)
- ParkSmart **chưa support** OCR biển giấy — phải liên hệ staff manual

## Liên hệ

Bug OCR: bugs@parksmart.com (gửi ảnh biển bị sai + expected text)
