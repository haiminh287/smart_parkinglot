# Code Review Report — BAO_CAO_PLAN.md (Post-Rewrite)

**Score: 7.0/10** | **Verdict: Approve (với khuyến nghị sửa trước nộp)**
**Date:** 2026-04-06 | Lines reviewed: 2309

---

## Summary

|               | Count     |
| ------------- | --------- |
| 🚨 Critical   | 0         |
| ⚠️ Major      | 1         |
| 💡 Minor      | 6         |
| 🗑️ Dead Code  | 1 section |
| 🏗️ Arch Drift | 0         |

---

## ⚠️ Major Issues

### [MAJ-1] Intent names không nhất quán giữa Ch2.4.2 và Ch3.5.2

- **File:** `docs/BAO_CAO_PLAN.md` — Mục 2.4.2 (~dòng 910) vs Mục 3.5.2 (~dòng 1830)
- **Category:** Consistency / Factual Accuracy
- **Problem:** Ch2.4.2 liệt kê 16 intents dùng SCREAMING_SNAKE naming (GREETING, SLOT_INQUIRY, BOOKING_CREATE, etc.), nhưng Ch3.5.2 liệt kê 16 intents dùng snake_case khác hoàn toàn:

  | Ch2.4.2             | Ch3.5.2                        | Vấn đề            |
  | ------------------- | ------------------------------ | ----------------- |
  | `SLOT_INQUIRY`      | `check_availability`           | Tên khác          |
  | `BOOKING_CREATE`    | `booking_car`, `booking_moto`  | 1 intent → tách 2 |
  | `BOOKING_CHECK`     | `check_booking_status`         | Tên khác          |
  | `BOOKING_CANCEL`    | `cancel_booking`               | Tên khác          |
  | `PRICING_INQUIRY`   | `price_inquiry`                | Tên khác          |
  | `DIRECTION_INQUIRY` | `navigation`                   | Tên khác          |
  | `PAYMENT_INQUIRY`   | `payment_info`                 | Tên khác          |
  | `INCIDENT_REPORT`   | `complaint`                    | Tên khác          |
  | `CHECKIN_INQUIRY`   | _(không có)_                   | Mất intent        |
  | `CHECKOUT_INQUIRY`  | _(không có)_                   | Mất intent        |
  | `HOURS_INQUIRY`     | _(không có)_                   | Mất intent        |
  | _(không có)_        | `find_parking`, `parking_info` | Thêm intent mới   |

- **Impact:** Người đọc không biết đâu là danh sách intent thực tế. Bảng Ch2.4.2 rất chi tiết (có ví dụ câu nói), nhưng Ch3.5.2 lại liệt kê khác — tạo ấn tượng hệ thống thiếu nhất quán.
- **Fix:** Thống nhất Ch3.5.2 dùng cùng 16 intent names của Ch2.4.2 (hoặc ngược lại), đảm bảo danh sách khớp chính xác. Nếu hệ thống thực tế dùng danh sách khác, cập nhật Ch2.4.2 cho khớp.

---

## 💡 Minor Issues

### [MIN-1] CHANGELOG section không thuộc báo cáo tốt nghiệp

- **File:** `docs/BAO_CAO_PLAN.md` ~dòng 2200+
- **Problem:** Section "CHANGELOG (So sánh với bản cũ)" là meta-documentation so sánh bản cũ/mới, không thuộc nội dung học thuật. Nếu nộp báo cáo, section này gây nhầm lẫn cho người đọc/giám khảo.
- **Fix:** Remove toàn bộ CHANGELOG section trước khi nộp chính thức. Giữ riêng ở file khác nếu cần tham chiếu.

### [MIN-2] Reference format chưa chuẩn IEEE

- **File:** References section (~dòng 1765)
- **Problem:** Dùng "[Trực tuyến]. Địa chỉ:" thay vì "[Online]. Available:" chuẩn IEEE. Thiếu ngày truy cập cụ thể (chỉ ghi "[Truy cập: 2026]" — thiếu tháng). Với báo cáo tiếng Việt có thể chấp nhận, nhưng nếu yêu cầu IEEE format thì cần sửa.
- **Fix:** Bổ sung tháng truy cập: "[Truy cập: tháng 4, 2026]". Nếu trường yêu cầu IEEE chuẩn, chuyển sang "[Online]. Available:" format.

### [MIN-3] Double horizontal rules giữa các chương

- **File:** Nhiều vị trí (~dòng 186, 798, 1054, etc.)
- **Problem:** Giữa mỗi chương có `---\n\n---` tạo 2 `<hr>` liên tiếp — thừa, nhìn trống.
- **Fix:** Chỉ giữ 1 `---` giữa các chương.

### [MIN-4] "spotlove-ai" folder name trong sơ đồ kiến trúc

- **File:** Sơ đồ kiến trúc Mục 3.1.1 (~dòng 810)
- **Problem:** Sơ đồ ghi `spotlove-ai/ — 27 trang (18 user + 9 admin)` — đây là tên folder thực tế trong codebase, không khớp tên dự án "ParkSmart". Người đọc sẽ thắc mắc "spotlove-ai là gì?".
- **Fix:** Thay `spotlove-ai/` bằng `ParkSmart Frontend/` hoặc chỉ ghi `27 trang (18 user + 9 admin)`.

### [MIN-5] Banknote vs Cash pipeline phân biệt không rõ ràng

- **File:** Mục 1.4.2b (~dòng 98) và Bảng 3.1.3
- **Problem:** Liệt kê 2 pipeline riêng biệt "Banknote Detection Pipeline (MobileNetV3)" và "Cash Recognition Pipeline (ResNet50)" nhưng không giải thích sự khác biệt giữa "banknote detection" và "cash recognition". Ch4.1.1 lại gộp thành 1 dòng "Nhận dạng tiền". Người đọc dễ nhầm lẫn.
- **Fix:** Bổ sung 1 câu giải thích: Banknote = nhận dạng loại tiền giấy từ hình ảnh tĩnh; Cash = nhận dạng mệnh giá từ camera liên tục trong phiên thanh toán (cash session). Hoặc gộp thành 1 pipeline nếu thực tế chúng cùng mục đích.

### [MIN-6] React Router thiếu version cụ thể

- **File:** Mục 2.2.3 (~dòng 410)
- **Problem:** Ghi "React Router v6" nhưng không ghi version cụ thể (ví dụ 6.x.y) trong khi tất cả dependencies khác đều có version number chính xác.
- **Fix:** Bổ sung version cụ thể từ package.json (ví dụ: React Router 6.x.x).

---

## 🗑️ Dead Content Found

| Location                            | Type                                   | Action                      |
| ----------------------------------- | -------------------------------------- | --------------------------- |
| CHANGELOG section (~dòng 2200–2309) | Meta-documentation không thuộc báo cáo | Remove trước nộp chính thức |

**Total: 1 section (~110 lines) → Cleanup needed before submission**

---

## 🏗️ Architecture Compliance

- ✅ Factual accuracy: Session-based auth (không JWT) — nhất quán xuyên suốt
- ✅ React 18.3.1 + Vite 5.4.19 SPA (không NextJS) — rõ ràng, được nhấn mạnh
- ✅ Django 5.2.12 + DRF 3.15.2 — version chính xác, nhất quán
- ✅ Gemini gemini-3-flash-preview — nhất quán
- ✅ MobileNetV3-Large multi-branch (không EfficientNet-B3) — đúng
- ✅ Service ports — nhất quán giữa bảng, sơ đồ, routing, sequence diagrams
- ✅ Version numbers — nhất quán giữa tất cả vị trí trích dẫn
- ✅ Header hierarchy (#, ##, ###, ####) — đúng cấu trúc
- ❌ Intent list — không nhất quán giữa Ch2 và Ch3 (xem MAJ-1)

---

## ✨ Positive Highlights

1. **Cấu trúc xuất sắc**: 4 chương + Phụ lục A/B/C theo chuẩn báo cáo tốt nghiệp, flow logic rõ ràng từ tổng quan → lý thuyết → hệ thống → kết luận.

2. **Cross-references chính xác**: Mọi cross-ref (Ch1→Ch3, Ch3→Ch2, Ch3→Phụ lục) đều trỏ đúng mục.

3. **Comparison tables balanced**: 5 bảng so sánh (DRF, React, ESP32, HTTP/MQTT/LoRa, LLM) đều có fair assessment — không chỉ ca ngợi lựa chọn của mình mà chỉ ra trade-offs.

4. **Ưu/nhược điểm balance tốt**: Mỗi công nghệ (Ch2.1–2.4) đều có phần nhược điểm + cách khắc phục cụ thể — thể hiện tư duy phản biện học thuật.

5. **ASCII diagrams chất lượng**: Sơ đồ kiến trúc, ERD, sequence diagrams, IoT wiring, chatbot pipeline — tất cả intact và dễ đọc.

6. **Version consistency đáng khen**: 15+ version numbers được kiểm tra, tất cả nhất quán xuyên suốt 2300 dòng.

7. **ERD + Denormalization explanation**: Giải thích rõ ràng tại sao denormalize booking table — đây là design decision quan trọng cần ghi nhận trong báo cáo.

8. **Phụ lục đầy đủ**: ~70 API endpoints, Docker Compose YAML, wiring diagrams — chứng minh hệ thống thật, không chỉ lý thuyết.

---

## 📋 Action Items (ordered by priority)

1. **[MAJ-1]** Thống nhất 16 intent names giữa Ch2.4.2 và Ch3.5.2 — chọn 1 danh sách chính xác, cập nhật cả 2 nơi.
2. **[MIN-1]** Remove CHANGELOG section (~110 lines cuối) trước khi nộp báo cáo chính thức.
3. **[MIN-4]** Thay `spotlove-ai/` bằng tên rõ nghĩa trong sơ đồ kiến trúc.
4. **[MIN-5]** Làm rõ phân biệt Banknote vs Cash pipeline (hoặc gộp nếu không khác biệt).
5. (Optional) **[MIN-2]** Bổ sung tháng truy cập trong references.
6. (Optional) **[MIN-3]** Gỡ double `---` thành single giữa các chương.
7. (Optional) **[MIN-6]** Bổ sung React Router version cụ thể.

---

## Scoring Breakdown

```
Baseline:                        8.0
Major issues (1 × -1.0):       -1.0
Minor issues (6 / 3 × -0.5):   -1.0
Bonus — thorough diagrams:      +0.5
Bonus — balanced pros/cons:     +0.5
                                ─────
Final Score:                     7.0/10
```
