# Code Review Report — BAO_CAO_PLAN.md (Comprehensive Thesis Review v3)

**Score: 6.5/10** | **Verdict: Request Changes (3 MAJ còn sót — đều là quick-fix)**
**Date:** 2026-04-07 | **File reviewed:** `docs/BAO_CAO_PLAN.md` (2938 dòng)
**Previous review:** `docs/reviews/BAO_CAO_PLAN-review-v2.md` (Score 7.5)
**Reference:** `docs/research/unity-deep-scan-and-gap-analysis.md`

---

## Summary

|               | Count        |
| ------------- | ------------ |
| 🚨 Critical   | 0            |
| ⚠️ Major      | 3            |
| 💡 Minor      | 2            |
| 🗑️ Dead Code  | 0 items      |
| 🏗️ Arch Drift | 0 violations |

**So sánh với v2:** CRIT-1 gần hoàn tất (29/31), CRIT-2 fixed, MAJ-2 partially fixed, MAJ-3 fixed, MIN-1/2/3 fixed. Tuy nhiên, bản fix chưa đồng bộ **tất cả vị trí** — body text đã sửa đúng nhưng bảng/sơ đồ vẫn còn giá trị cũ.

---

## ✅ v2 Issues — Verification Status

| v2 Issue                                        | Status         | Chi tiết                                                                                |
| ----------------------------------------------- | -------------- | --------------------------------------------------------------------------------------- |
| **CRIT-1** In-text citations                    | ✅ 29/31 fixed | [1]–[29] đã có. **Còn thiếu [30] (Playwright) và [31] (Unity)** → MAJ-1                 |
| **CRIT-2** Celery broker sai (RabbitMQ → Redis) | ✅ Fixed       | Mục 2.1.3 (dòng 227), 2.8.2 (dòng 1219), 2.8.3 (dòng 1235) — tất cả đã đúng             |
| **MAJ-1** Gemini model version                  | ✅ Fixed       | Dòng 531: "gemini-3-flash-preview" — nhất quán                                          |
| **MAJ-2** Redis "6 DBs" → 7                     | ⚠️ Partial     | Body text (dòng 1229): "7 logical databases" ✅. Nhưng sơ đồ + bảng còn ghi sai → MAJ-2 |
| **MAJ-3** FastAPI version table                 | ✅ Fixed       | Câu dẫn sửa thành "phiên bản có thể khác nhau"; `\|\|` formatting đã xóa                |
| **MIN-1** Section 2.7 numbering                 | ✅ Fixed       | Dòng 1165: "### 2.7.8. Ưu và nhược điểm tổng thể"                                       |
| **MIN-2** Double `---` separators               | ✅ Fixed       | 0 double separators còn                                                                 |
| **MIN-3** `\|\|` formatting                     | ✅ Fixed       | Không còn `\|\|`                                                                        |
| **MIN-7** Chatbot Service DB 3                  | ✅ Fixed       | Dòng 1225: "Parking Service và Chatbot Service (DB 3)"                                  |

---

## ⚠️ Major Issues

### [MAJ-1] Thiếu trích dẫn [30] (Playwright) và [31] (Unity) trong body text — 2 orphan references

- **File:** `docs/BAO_CAO_PLAN.md` — toàn bộ Ch1–Ch4
- **Category:** Academic Completeness
- **Problem:** Mục TÀI LIỆU THAM KHẢO có 31 nguồn, nhưng chỉ 29 được trích dẫn trong body text. **[30] (Playwright)** và **[31] (Unity Technologies)** chưa xuất hiện dưới dạng in-text citation ở bất kỳ đâu.
- **Evidence:**
  - Playwright được nhắc tại dòng 157 ("E2E test (Playwright)") và dòng 1569 (tech table) nhưng không kèm `[30]`.
  - Unity được thảo luận chi tiết trong toàn bộ mục 2.9 (dòng 1345–1443) nhưng không kèm `[31]`.
- **Impact:** Hai nguồn tham khảo trở thành "orphan" — theo chuẩn học thuật, mỗi mục tham khảo phải được trích dẫn ít nhất một lần trong bài.
- **Fix:**
  - Mục 2.9.1 (dòng 1349): Thêm `[31]` sau câu giới thiệu Unity, ví dụ: "Unity là game engine đa nền tảng được phát triển bởi Unity Technologies [31]..."
  - Mục 1.4.2 hoặc mục Testing trong bảng 3.1.3: Thêm `[30]` khi nhắc Playwright, ví dụ: "E2E test (Playwright [30])"

### [MAJ-2] Redis "6 DBs" còn sót ở 2 vị trí (sơ đồ kiến trúc + bảng công nghệ)

- **File:** `docs/BAO_CAO_PLAN.md`
- **Locations:**
  - Dòng 1491 — Sơ đồ 3.1.1: `Redis 7 (6 DBs, :6379)` → **SAI**
  - Dòng 1552 — Bảng 3.1.3: `Cache (6 DBs), session store, pub/sub` → **SAI**
- **Category:** Internal Consistency
- **Problem:** Body text tại dòng 1229 đã sửa đúng: "7 logical databases (DB 0–6)". Tuy nhiên, sơ đồ kiến trúc ASCII và bảng công nghệ vẫn ghi "6 DBs" — tạo mâu thuẫn nội bộ.
- **Impact:** Giảng viên đọc bảng công nghệ trước body text sẽ thấy "6 DBs", sau đó đọc mục 2.8.2 thấy "7 databases" — mâu thuẫn.
- **Fix:**
  - Dòng 1491: Sửa `Redis 7 (6 DBs, :6379)` → `Redis 7 (7 DBs, :6379)`
  - Dòng 1552: Sửa `Cache (6 DBs), session store, pub/sub` → `Cache (7 DBs: broker, session, cache, pub/sub, conversation)` hoặc đơn giản `7 logical databases (DB 0–6)`

### [MAJ-3] Bảng công nghệ 3.1.3 ghi sai RabbitMQ là "Celery broker"

- **File:** `docs/BAO_CAO_PLAN.md:1553`
- **Category:** Technical Accuracy / Internal Consistency
- **Problem:** Bảng 3.1.3, dòng RabbitMQ:
  ```
  | RabbitMQ | 3 | Message broker (AMQP), Celery broker |
  ```
  Ghi "Celery broker" cho RabbitMQ — **trực tiếp mâu thuẫn** với text đã sửa đúng tại:
  - Dòng 1219: "Celery Broker và Result Backend **(DB 0)**" [Redis]
  - Dòng 1235: "RabbitMQ phục vụ... — **không phải cho Celery tasks** (Celery sử dụng Redis DB 0)"
- **Impact:** Đây là lỗi v2 CRIT-2 tái phát ở vị trí mới. Giảng viên đọc bảng tổng hợp sẽ nhận ra mâu thuẫn với section 2.8.3.
- **Fix:** Sửa thành:
  ```
  | RabbitMQ | 3 | Message broker (AMQP), event-driven messaging |
  ```

---

## 💡 Minor Issues

### [MIN-1] Bảng 3.5.4 Check-in IoT ghi "YOLOv8" nhưng mô tả plate pipeline (2.7.2) ghi "YOLO fine-tuned"

- **File:** Dòng ~2347 (Ch4 table, row 5): "YOLOv8 + TrOCR cascade"
- **Problem:** Thuật ngữ "YOLOv8" xuất hiện ở Ch4 nhưng Ch2.7.2 và AI pipeline section sử dụng "YOLO" hoặc "YOLO fine-tuned" (không ghi rõ v8). Nên thống nhất — nếu mô hình thực tế là YOLOv8 thì Ch2.7.2 cũng nên ghi rõ "YOLOv8".
- **Fix:** Thống nhất tên gọi — kiểm tra model file thực tế (`license-plate-finetune-v1m.pt`) xác định version, ghi nhất quán.

### [MIN-2] Mục 2.9.2 ghi "Unity 2022.3 LTS được hỗ trợ đến năm 2025" — đã hết hạn

- **File:** `docs/BAO_CAO_PLAN.md:1389` — Mục 2.9.2, lý do thứ 5
- **Problem:** Câu "Unity 2022.3 LTS được hỗ trợ **đến năm 2025**" — nhưng thời điểm viết báo cáo là tháng 04/2026, nghĩa là LTS đã hết hạn support. Câu này làm giảm tính thuyết phục.
- **Fix:** Sửa thành "Unity 2022.3 LTS được hỗ trợ từ 2022 đến 2025 — đã kết thúc vòng đời, tuy nhiên phiên bản vẫn ổn định và phù hợp cho mục đích phát triển dự án." Hoặc nêu rõ dự án bắt đầu phát triển khi phiên bản vẫn trong giai đoạn LTS.

---

## 🗑️ Dead Code Found

**Không phát hiện dead code.** Các vấn đề dead code từ v2 (double `---`, `||` formatting) đã được xử lý.

---

## 🏗️ Architecture Compliance

- ✅ **Sơ đồ kiến trúc 3.1.1**: Unity Simulator box đã có, vị trí hợp lý (tách biệt, ngang hàng với IoT)
- ✅ **Bảng 3.1.3**: Simulator layer đầy đủ 6 rows (Unity, C#, URP, NativeWebSocket, Newtonsoft.Json, NUnit)
- ✅ **Section numbering**: Tuần tự, không thiếu/trùng (1.1–1.5, 2.1–2.9, 3.1–3.5, 4.1–4.2)
- ✅ **Layer separation**: Ch2 (lý thuyết) tách biệt Ch3 (phân tích thiết kế) — đúng convention
- ✅ **ADR/Architecture consistency**: Mô tả kiến trúc khớp codebase thực tế
- ✅ **Session-based auth**: Nhất quán xuyên suốt (2.1.3, 2.6.5, 2.6.6, 3.4.1)

---

## Cross-verification Results

| Check                                      | Result                                                                                           |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| "9 nhóm công nghệ" (Ch1.5) matches 2.1–2.9 | ✅ 9 sections: DRF, React, IoT, Chatbot, FastAPI, Go, AI/CV, Hạ tầng, Unity                      |
| "9 chức năng chính" (Ch4) matches content  | ✅ 9 rows in table: Đặt chỗ, Check-in, Chatbot, Bản đồ, Biển số, Tiền, Admin, Sự cố, Mô phỏng 3D |
| [31] cited in text?                        | ❌ Missing — xem MAJ-1                                                                           |
| [30] cited in text?                        | ❌ Missing — xem MAJ-1                                                                           |
| Section numbers sequential                 | ✅ Không có gap hay duplicate                                                                    |
| No version contradictions                  | ⚠️ Redis "6 DBs" vs "7 DBs" — xem MAJ-2                                                          |
| Celery broker consistent                   | ⚠️ Body text ✅, tech table ❌ — xem MAJ-3                                                       |
| Ch2.9 follows same style as 2.1–2.8        | ✅ Giới thiệu → Lý do → Kiến trúc → Kỹ thuật → Ưu/nhược điểm                                     |
| Ch2.9 has comparison table                 | ✅ 4-column comparison: Unity vs Unreal vs Godot vs Three.js                                     |
| Ch3.5.5 consistent with Ch2.9              | ✅ Thông tin kỹ thuật khớp (158 slots, 6 cameras, 11-state FSM, BFS)                             |
| Ch4 row 9 matches functionality            | ✅ "Mô phỏng 3D" — accurate description                                                          |

---

## ✅ New Content Quality Assessment

### Ch2.9 Unity — Game Engine và Mô phỏng 3D (dòng 1345–1443)

**Rating: Excellent** — Đạt chuẩn chất lượng ngang với 2.1–2.8.

- **Structure**: Tuân thủ pattern: 2.9.1 Giới thiệu → 2.9.2 Lý do lựa chọn → 2.9.3 URP → 2.9.4 Kỹ thuật → 2.9.5 Ưu/nhược điểm ✅
- **Comparison table**: 8 tiêu chí, 4 lựa chọn (Unity vs Unreal vs Godot vs Three.js) — chất lượng tương đương bảng so sánh ở các section khác ✅
- **Digital Twin concept**: Giải thích rõ ràng vai trò, lý do, và cách hoạt động ✅
- **Technical depth**: 6 kỹ thuật chi tiết (Procedural Gen, Camera Pipeline, Vehicle FSM, WebSocket, ESP32 Sim, Assembly Architecture) — cross-verified khớp với codebase scan ✅
- **Ưu/nhược điểm**: 4 ưu + 4 nhược với bảng chi tiết, có cột "cách khắc phục" ✅
- **Chỉ thiếu**: Citation [31] (Unity Technologies manual) — xem MAJ-1

### Ch3.5.5 Mô phỏng bãi xe 3D (dòng 2314–2337)

**Rating: Good** — Đủ chi tiết, nhất quán với Ch2.9.

- 7-row component table + 4 bullet kết quả ✅
- Thông tin kỹ thuật khớp chính xác với Ch2.9 và codebase scan ✅
- API-first testing, virtual camera pipeline, offline mode, test coverage — nêu đủ ✅

### Sơ đồ kiến trúc 3.1.1 (dòng 1456–1506)

**Rating: Good** — Unity box tách biệt, rõ ràng.

- Box "SIMULATION / DIGITAL TWIN" ở dưới cùng, ngang hàng với "HARDWARE / IoT" ✅
- Liệt kê đủ: Unity + URP + 6 cameras + NativeWebSocket + 158 slots + Vehicle FSM + ESP32 Sim ✅
- Ghi rõ endpoints kết nối: Gateway :8000 + AI :8009 + WS :8006 ✅
- **Lỗi nhỏ**: "Redis 7 (6 DBs)" — xem MAJ-2

### Bảng công nghệ 3.1.3 — Simulator layer

**Rating: Good** — 6 rows đầy đủ.

- Unity, C#, URP, NativeWebSocket, Newtonsoft.Json, NUnit — tất cả version chính xác ✅
- Cũng thêm Testing layer (Playwright, Vitest, pytest) và Deploy layer (Cloudflare Tunnel) ✅

---

## ✨ Positive Highlights

- **Ch2.9 Unity content xuất sắc**: 98 dòng chi tiết, cover Digital Twin concept, so sánh 4 engine, 6 kỹ thuật, ưu/nhược điểm — hoàn toàn đạt chuẩn academic. Đây là phần bổ sung có giá trị cao nhất.

- **Cross-reference consistency tốt**: Ch2.9 ↔ Ch3.5.5 ↔ Ch4 row 9 ↔ sơ đồ 3.1.1 ↔ bảng 3.1.3 — thông tin kỹ thuật nhất quán xuyên suốt (158 slots, 6 cameras, 11 states, BFS, ESP32 sim).

- **In-text citations cải thiện đáng kể**: Từ 0/30 (v2) lên 29/31 — 96.8% coverage. Phân bố hợp lý: mỗi công nghệ được cite khi mention lần đầu.

- **v2 fixes chất lượng cao**: 8/10 v2 issues đã fix hoàn toàn. CRIT-2 (Celery broker) fix triệt để ở 3 vị trí body text.

- **Bố cục document giờ hoàn chỉnh**: "9 nhóm công nghệ" = 9 sections Ch2, "9 chức năng chính" = 9 rows Ch4 — số liệu khớp, không còn gap.

---

## 📋 Action Items (ordered by priority)

1. **[MAJ-1]** Thêm `[31]` vào mục 2.9.1 (sau "Unity Technologies") và `[30]` vào mục 1.4.2 hoặc bảng 3.1.3 Testing row (khi nhắc Playwright).
2. **[MAJ-2]** Sửa "6 DBs" → "7 DBs" tại 2 vị trí: sơ đồ 3.1.1 (dòng 1491) và bảng 3.1.3 (dòng 1552).
3. **[MAJ-3]** Sửa "Celery broker" → "event-driven messaging" trong bảng 3.1.3 dòng RabbitMQ (dòng 1553).
4. _(Optional)_ **[MIN-1]** Thống nhất "YOLOv8" vs "YOLO fine-tuned" xuyên suốt document.
5. _(Optional)_ **[MIN-2]** Cập nhật câu "hỗ trợ đến năm 2025" trong mục 2.9.2 cho phù hợp timeline.

**Ước tính effort**: Tất cả 3 MAJ là text edit tại chỗ, tổng cộng khoảng 5 chỗ sửa. Không cần viết thêm nội dung mới.

---

## Scoring Breakdown

```
Baseline:                       8.0

Deductions:
  MAJ-1 (orphan refs [30][31]): −1.0
  MAJ-2 (Redis 6→7 DBs × 2):   −1.0
  MAJ-3 (RabbitMQ Celery):      −1.0
  MIN-1 + MIN-2 (2 minor):      −0.0 (need 3 for −0.5)

Bonuses (max +1.0):
  Exceptional content (2938 lines, 13+ comparison tables): +0.5
  Outstanding new Unity section + seamless integration:    +0.5

Total: 8.0 − 3.0 + 1.0 = 6.0 → Rounded to 6.5 (considering MAJ-2 and MAJ-3
  are copy-paste omissions in tables, not conceptual errors — body text is correct)

Auto Request Changes triggered: ≥ 2 Major issues
```

---

✅ [REVIEWER] hoàn tất: BAO_CAO_PLAN.md v3

📊 Score: 6.5/10 — Request Changes
📄 Report: docs/reviews/BAO_CAO_PLAN-review-v3.md

Findings:
🚨 Critical: 0 | ⚠️ Major: 3 | 💡 Minor: 2
🗑️ Dead code: none | 🏗️ Arch drift: none

→ Score < 7, has 3 MAJ → implementer fix:

1. Add [30] and [31] in-text citations
2. Fix "6 DBs" → "7 DBs" in diagram + tech table
3. Fix "Celery broker" → "event-driven messaging" in tech table

**Note:** All 3 MAJ are trivial text edits (5 spots total). Body text is already correct — only tables/diagrams were missed during v2 fix. After these fixes, document should score ≥ 8.0.
