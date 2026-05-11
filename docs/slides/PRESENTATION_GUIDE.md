# HƯỚNG DẪN TRÌNH BÀY KHÓA LUẬN — PARKSMART

> **Mục đích**: Script chi tiết cho buổi defense KLTN.
> Tổng thời gian: **15-20 phút** trình bày + **10-15 phút** Q&A.
> File slide: `ParkSmart_KLTN_Slides.pptx` (23 slides).

---

## CHIẾN LƯỢC TỔNG THỂ

| Phần | Slide | Thời gian | Trọng tâm |
|------|-------|-----------|-----------|
| **Mở đầu** | 1-2 | 1-2' | Giới thiệu + vấn đề |
| **Mục tiêu** | 3-4 | 2' | Đề xuất giải pháp + tech stack |
| **Kiến trúc** | 5-8 | 3-4' | System design + flow |
| **AI Core** | 9-13 | 5-6' | 4 AI modules + kết quả |
| **IoT + Unity** | 14-16 | 2-3' | Hardware + Digital Twin |
| **Phân tích** | 17-19 | 2' | Khó khăn + SWOT + Roadmap |
| **Kết luận** | 20-21 | 1' | USPs + Cảm ơn |
| **Q&A** | (22-23) | 10-15' | Backup phụ lục |

**Nguyên tắc:**
1. Mỗi slide **NHÌN 5-10 giây trước khi nói** — để hội đồng quét nội dung
2. Notes Page chứa script chi tiết — dùng Presenter View (Alt+F5)
3. **Big numbers** trên slide là điểm nhấn → đọc to và rõ
4. Khi không chắc câu hỏi → "Em xin phép mở slide phụ lục 22/23 để tham chiếu"

---

## SCRIPT CHI TIẾT TỪNG SLIDE

### Slide 1 — Cover (~30s)
> "Xin chào quý hội đồng, em là **Nguyễn Hải Minh**, MSSV 2251012093, Khoa Khoa học Máy tính. Khóa luận hôm nay em trình bày đề tài: **Hệ thống quản lý Bãi đỗ xe Thông minh tích hợp IoT, AI và Digital Twin**. Em sẽ trình bày trong 15-20 phút."

**Pause** 2 giây → next slide.

---

### Slide 2 — Đặt vấn đề (~1.5')
> "Em khảo sát 3 bãi đỗ xe nội đô: Vincom Q1, The Sun Avenue, Saigon Centre. Có 5 nỗi đau chung:"

Đọc lần lượt từng card (chỉ tay):
1. **Ùn tắc cửa 30-60s/xe** — kẹt 200m giờ cao điểm
2. **Sai sót 5% giao dịch tiền mặt** — thất thoát 3-7tr/tháng
3. **Nhân sự 21-35tr/tháng** — chi phí cố định
4. **Không đặt trước 60%** — mất khách
5. **Không analytics** — sổ tay không tối ưu được

> "Cần giải pháp tự động hóa toàn diện bằng AI."

---

### Slide 3 — Các công nghệ chính + lý do (~1.5')
> "Em chọn **4 công nghệ chính**, mỗi cái có lý do cụ thể:"
- **AI Plate OCR**: thay bảo vệ check biển → tự động mở barrier
- **AI Banknote**: VN dùng cash nhiều — unique value VN
- **Chatbot RAG**: hỗ trợ user 24/7 → giảm tải support center
- **IoT + Unity**: test E2E mà chưa cần hardware → giảm chi phí prototype

> "Phạm vi: 10 microservices, web PWA, Unity Twin, deploy Cloudflare Tunnel."

---

### Slide 4 — Vì sao chọn các công nghệ này (~1.5')
Highlight **3 lý do nguyên tắc**:
- **Backend**: Django CRUD + FastAPI async AI + Go gateway latency thấp
- **AI/ML**: PyTorch + YOLO + Gemini — vì sẵn ecosystem, free tier
- **Infra**: Docker Compose đơn giản, Cloudflare Tunnel free SSL

> "Mỗi công nghệ chọn vì lý do cụ thể — không over-engineer, không chạy theo hype."

---

### Slide 5 — Kiến trúc tổng thể (~1')
> "Đây là **kiến trúc 7 layer**: Client → Cloudflare → Gateway Go → 10 microservices → RabbitMQ event bus → Realtime WebSocket → Datastore MySQL + Redis 6 DBs."

> "Điểm chốt: **1 entry point public** qua Gateway. Service nội bộ chỉ chấp nhận yêu cầu đã xác thực."

---

### Slide 6 — Vì sao Microservices (~1')
> "Em đã so sánh 3 kiến trúc: Monolith, Microservices, Serverless. Em chọn Microservices vì:"
- Scale AI service GPU độc lập
- Fault isolation (AI lỗi không sụp booking)
- Đa stack (Py+Go+JS) thể hiện skill

> "Trade-off: setup phức tạp hơn, nhưng đáng cho KLTN."

---

### Slide 7 — Event-Driven + Cache (~1')
> "2 pattern quan trọng:"
- **RabbitMQ fan-out**: booking.created → 4 consumer cùng lúc (notification, payment, analytics, chatbot)
- **Redis 6 DBs cô lập**: mỗi service 1 DB riêng

> "Lợi: async, loose coupling, fault tolerant."

---

### Slide 8 — Luồng E2E (~1')
> "Theo chân 1 user qua 3 phase:"
1. **Đặt chỗ online** — web → gateway → booking → MySQL → email QR
2. **Check-in** — camera ANPR → AI plate → match booking → barrier mở
3. **Check-out + Thanh toán** — cash scanner → AI banknote → tính phí → barrier ra

---

### Slide 9 — AI #1 Plate (~1.5')
> "Module thứ nhất: nhận diện biển số xe. Pipeline 2-stage."

Highlight 6 kỹ thuật. Đặc biệt:
- **YOLOv8**: 96% vs Classical CV chỉ 60%
- **3-engine OCR**: TrOCR primary + EasyOCR/Tesseract fallback
- **Levenshtein ≤ 1**: tolerate O↔0, I↔1

> "**Kết quả: end-to-end 94.5%, false accept dưới 0.5%, latency 2s.**"

---

### Slide 10 — AI #2 Banknote (~2')
**ĐÂY LÀ ĐIỂM ĐỘC ĐÁO** — nói chậm và rõ:

> "Đây là điểm độc đáo của em — **AI nhận diện 9 mệnh giá tiền VN, chưa bãi xe nào tại Việt Nam có**."

> "Pipeline **cascade 4 tầng** từ nhẹ → nặng. 70% case dừng ở tầng 3, trung bình chỉ 50ms — nhanh hơn 3× full deep model."

Highlight:
- **EfficientNetV2-S** + TTA × 5 + Rejection margin-based
- **Bank-grade 3-stage**: Classifier + Siamese + OneClass SVM (verify + anomaly)
- Triết lý: **"Thà từ chối còn hơn sai"** cho giao dịch tiền

> "**Accuracy 98.22% · Precision-at-accept ≥ 99.5%.**"

---

### Slide 11 — AI #3 Chatbot RAG (~1.5')
> "Module thứ ba: chatbot trợ lý ảo tiếng Việt với **RAG knowledge retrieval**."

Highlight:
- **DDD 3-layer**: Domain pure, Application logic, Infrastructure swap được
- **Gemini 2.5 Flash**: VN tốt, 200× rẻ hơn GPT-4
- **RAG ChromaDB**: trả lời FAQ từ docs thật, có citation, **giảm hallucination**
- **Hybrid Confidence** = 0.4 × LLM + 0.3 × Entity + 0.3 × Context

---

### Slide 12 — AI #4 Slot (~1')
> "Module cuối: nhận diện ô đỗ xe. Em đã thử YOLO nhưng fail vì Unity primitive khác COCO. Em chuyển sang **Classical CV** — 100% bãi trống."

Highlight:
- HSV mask + Morphology + RETR_CCOMP
- Row Reconstruction + Best-Grid Cache (xe to che viền vẫn detect được)

---

### Slide 13 — Kết quả thực nghiệm AI (~1')
> "Em đo trên test set ĐỘC LẬP, không seen during training:"
- Plate: 94.5% e2e (500 ảnh)
- Banknote: 98.22% (1500 ảnh holdout)
- Slot: 86-100% theo occupancy
- Chatbot: >93% intent accuracy

> "Phương pháp: Train/Val/Test split 70/15/15, cross-validation, so sánh baseline."

(Pointing at confusion matrix bên phải) > "Class hay nhầm là 200k và 500k do màu đỏ-tím gần nhau — rejection bù bằng yêu cầu scan lại."

---

### Slide 14 — IoT Hardware (~1.5')
> "Phần IoT: **4 ESP32 edge devices**."

(Chỉ vào 4 card lần lượt):
- GATE-IN / GATE-OUT / VERIFY-SLOT / CASH-PAY

> "**BOM thực tế ~26.5 triệu** cho bãi 50 chỗ (không phải 50tr như em ước tính ban đầu). Em đã research lại giá thị trường thực tế."

> "Vì sao ESP32? Wi-Fi tích hợp, ADC, servo control, giá 250k — sweet spot."

---

### Slide 15 — IoT Communication (~1')
> "3 luồng tương tác chính + xác thực bằng khóa định danh + heartbeat 30s. Mất tín hiệu 90s → cảnh báo offline, bảo vệ manual override."

---

### Slide 16 — Unity Digital Twin (~1.5')
> "**Điểm độc đáo thứ 2 — không đồ án KLTN VN nào có Digital Twin Unity**."

3 deployment modes: Editor / Standalone / Headless CI.

> "**Quan trọng**: Multi-Lot Flexibility — chỉ cần thay **JSON config** là ParkingLotGenerator tự regen scene. Đã hỗ trợ 4 mô hình bãi: Linear, Block, Multi-floor, Mixed."

---

### Slide 17 — Khó khăn & Bài học (~1')
> "Em gặp 6 khó khăn lớn, mỗi cái em rút ra bài học. Ví dụ YOLO fail → fallback OpenCV; Banknote v1 89% → v2 98.22% nhờ TTA+rejection..."

Tóm tắt: **"7 sprints, ~200 commits, refactor 4 god-classes."**

---

### Slide 18 — Phân tích thực tế (SWOT) (~2')

**SLIDE QUAN TRỌNG** — hội đồng sẽ hỏi nhiều về realistic deployment.

> "Em phân tích SWOT thẳng thắn."

**Điểm mạnh:**
- Tự động hóa 100% không cần bảo vệ thường trực
- AI accuracy cao trên test set
- Open-source không lock-in
- Có Unity sim test E2E mà chưa cần hardware

**Điểm yếu (THÀNH THẬT):**
- Chưa pilot trên bãi thật với user thật
- AI gặp edge case khi tiền cũ, biển bẩn
- Dependence internet ổn định
- Hardware ESP32 chưa deploy thật

**Cơ hội:** Smart parking VN sơ khai, cash culture, cloud + 5G

**Thách thức:** Pháp lý biển số, cạnh tranh vendor lớn, user adoption

> "**Câu hỏi quan trọng**: AI đủ tốt cho production chưa? — Em trả lời **CÓ** với manual override fallback. Banknote 99.5% precision đã bank-grade. Plate 94.5% + Levenshtein tolerance đảm bảo false accept < 0.5%."

> "**Unity flexibility?** — Chỉ thay JSON config là regen scene."

---

### Slide 19 — Roadmap + Business Case (~1.5')
> "6 hướng phát triển: Offline mode, LiDAR, EV charging, ML forecast, Mobile native, Multi-tenant."

> "**Business case thực tế cho bãi 50 chỗ**: Phần cứng 26.5tr một lần, vận hành 8tr/tháng (giảm 50% nhờ không cần bảo vệ thường trực), doanh thu ước tính 35tr/tháng. **Payback ~1 tháng**."

---

### Slide 20 — Đóng góp khoa học (~1.5')
**SLIDE QUAN TRỌNG** — chốt giá trị KLTN.

Đọc rõ 5 USPs:
1. AI banknote VN (UNIQUE)
2. Unity Digital Twin (UNIQUE)
3. Microservices open-source
4. Chatbot LLM + RAG
5. Precision-First AI

> "Triết lý: **Không phải làm tốt 1 thứ, mà làm tốt 1 hệ thống tích hợp**."

---

### Slide 21 — Cảm ơn + Q&A (~30s)
> "Em xin kết thúc phần trình bày. Cảm ơn hội đồng đã lắng nghe. Em sẵn sàng nhận câu hỏi. Demo live tại parksmart chấm ghepdoicaulong chấm shop."

---

### Slides 22-23 — Phụ lục Q&A (backup)
**Không hiển thị mặc định**. Chỉ mở khi hội đồng hỏi đúng câu tương ứng.

---

## XỬ LÝ TÌNH HUỐNG

### Khi hội đồng hỏi câu khó:
1. **Lặp lại câu hỏi** ("Câu hỏi của thầy/cô là...") — để chắc hiểu đúng
2. Suy nghĩ 3 giây trước khi trả lời
3. Nếu không biết: "Đây là câu hỏi hay, em chưa nghiên cứu đầy đủ. Em sẽ ghi nhận và tìm hiểu thêm."
4. **Không bịa**. Trung thực = điểm cộng.

### Câu hỏi gay góc dự kiến:
- "AI 94% có đủ cho production?" → **Mở slide 18 SWOT** + Manual override fallback
- "Đã deploy hardware ESP32 thật chưa?" → **CHƯA**. Unity simulator validate contract 100% pass. Sprint sau: alpha 1 bãi pilot.
- "Bãi giữ xe không người an toàn?" → Multi-layer: camera 24/7 + insurance + manual override
- "Tiền giả AI biết?" → KHÔNG — out of scope KLTN. Hardware cần UV/IR sensor + model riêng.
- "Chi phí thực tế?" → **Mở slide 14** — 26.5tr. KLTN demo dùng Unity simulator + Mini-PC sẵn có.

### Câu hỏi về competitor:
- "Vincom đã có AI?" → Một số bãi có ANPR cho VIP, nhưng KHÔNG có AI tiền + Digital Twin
- "Sao không dùng Hikvision SDK?" → Lock-in vendor. Open-source approach của em fork và deploy được

---

## CHUẨN BỊ TRƯỚC DEFENSE

### Ngày trước:
- [ ] Mở file `.pptx` trong PowerPoint, kiểm tra hiển thị
- [ ] Test Presenter View (Alt+F5) — notes hiện không?
- [ ] Bật demo live `https://parksmart.ghepdoicaulong.shop` — chạy ổn?
- [ ] Cài đặt Cloudflared trên máy laptop để demo live
- [ ] Backup video screen-record 5-7 phút demo full flow (phòng net hỏng)

### Sáng defense:
- [ ] Đến phòng sớm 30 phút
- [ ] Test máy chiếu — slide rõ chữ, video play được
- [ ] Kết nối tablet/phone làm dự phòng nếu laptop sự cố
- [ ] Mang USB chứa file slide (backup file Google Drive)

### Trong khi defense:
- [ ] Đứng thẳng, nhìn về phía hội đồng (không quay lưng vào slide)
- [ ] Nói chậm hơn 20% so với bình thường
- [ ] Pause 2-3 giây sau mỗi điểm quan trọng
- [ ] Nhấn mạnh con số bằng giọng + chỉ tay vào slide
- [ ] Khi không chắc → bình tĩnh, nghĩ trước nói

### Sau Q&A:
- [ ] Cảm ơn hội đồng
- [ ] Ghi lại câu hỏi khó để improve
- [ ] Xin email nếu cần follow-up

---

## ĐIỂM CHỐT 3 GIÁ TRỊ CẦN GHI ĐIỂM

1. **AI nhận diện tiền VN — UNIQUE** (nhấn mạnh trong slide 10, 20)
2. **Unity Digital Twin — UNIQUE** (nhấn mạnh trong slide 16, 20)
3. **Hệ thống tích hợp end-to-end** (nhấn mạnh trong slide 8, 18)

→ Nhớ: thầy cô chấm điểm DỰA TRÊN GIÁ TRỊ KHÁC BIỆT, không phải chi tiết kỹ thuật.

---

**Chúc bạn defense thành công! 🎓**
