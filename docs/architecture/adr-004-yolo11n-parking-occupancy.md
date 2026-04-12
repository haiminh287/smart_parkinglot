# ADR-004: Tích hợp YOLO11n để phát hiện trạng thái ô đỗ xe

## Trạng thái: Accepted

## Bối cảnh

`SlotDetector` hiện tại dùng OpenCV thuần (Canny edge + contour + HSV color variance) để phán đoán ô đỗ có xe hay không. Phương pháp này nhạy cảm với điều kiện ánh sáng thay đổi (mưa, nắng buổi chiều, đèn parking ám), dẫn đến false positive/negative cao trong môi trường thực.

`ultralytics==8.4.18` đã có trong `requirements.txt`. Pattern YOLO singleton đã tồn tại (`plate_detector.py`, `detector.py`). Cần nâng cấp độ chính xác mà **không phá vỡ** `FrameDetectionResult` contract và `camera_monitor` worker hiện tại.

**Constraints:**
- Không thêm dependency mới
- Không thay đổi interface `FrameDetectionResult`, `SlotBbox`, `SlotDetectionResult`
- Camera monitor gọi `get_slot_detector().detect_occupancy(frame, slots, camera_id)` — phải giữ nguyên
- `yolo11n.pt` tự download lần đầu (ultralytics built-in support)

## Phương Án Xem Xét

### Option A: Thay thế hoàn toàn OpenCV bằng YOLO

- Ưu: code đơn giản hơn
- Nhược: **mất graceful fallback** — nếu model corrupt hoặc CUDA OOM thì toàn bộ detection crash. Vi phạm Fail Fast + Resilience nguyên tắc.

### Option B: YOLO như primary, OpenCV như fallback (được chọn)

- Ưu: backward compatible 100%; nếu model chưa tải về → OpenCV tiếp tục chạy; thread-safe vì model là read-only sau init
- Nhược: code phức tạp hơn một chút
- Trade-off: chấp nhận được

### Option C: Tách thành class `YoloSlotDetector` riêng

- Ưu: clean separation
- Nhược: over-engineering — camera_monitor và endpoint đều cần thay đổi; không cần thiết với 1 service

## Quyết Định

**Option B** — Extend `SlotDetector` với YOLO như primary path, OpenCV như fallback.

Lý do kỹ thuật:
1. Interface unchanged → zero breaking changes, camera_monitor không cần sửa
2. Graceful degradation: YOLO fail → OpenCV vẫn chạy
3. Singleton pattern đã có → chỉ cần thêm `yolo_model_path` param, init một lần trong lifespan
4. YOLO chạy trên **toàn bộ frame** (1 lần per frame), sau đó IoU matching cho từng slot → O(1) inference dù có 50 slot

## Hệ Quả

**Tích cực:**
- Độ chính xác cao hơn đáng kể (YOLO được train trên COCO với car/truck/bus/motorcycle)
- Không phụ thuộc vào điều kiện ánh sáng
- Auto-download `yolo11n.pt` (~6MB) lần đầu chạy → không cần thêm vào repo

**Trade-offs:**
- Inference YOLO synchronous, blocking asyncio event loop khoảng 20-80ms per frame (CPU) / 5-20ms (GPU)
- Hiện tại OpenCV cũng blocking — risk tương đương, chấp nhận được với scan_interval=30s
- Model warm-up lần đầu chậm (~1-2s) → sẽ thực hiện warm-up trong `__init__`

**Rủi ro → Mitigation:**
| Rủi ro | Mitigation |
|--------|-----------|
| `yolo11n.pt` download fail (no internet) | Graceful fallback về OpenCV, log WARNING |
| CUDA OOM trên máy yếu | `yolo11n` chỉ ~6MB, CPU mode đủ dùng |
| False negative: xe đỗ lệch bbox | IoU threshold thấp (0.15) giảm thiểu |

## Implementation Notes

- COCO vehicle class IDs: `{2: car, 3: motorcycle, 5: bus, 7: truck}`
- IoU threshold: **0.15** (thấp vì camera parking birds-eye-view, xe đỗ nghiêng → YOLO bbox overlap với slot bbox có thể nhỏ)
- YOLO conf threshold: **0.25** (standard ultralytics default, đủ filter noise)
- Pre-warm detector trong `main.py` lifespan TRƯỚC khi start camera_monitor để:
  1. Download model nếu chưa có (blocking OK tại startup)
  2. Warm-up inference (tránh slow first request)
- Không dùng `asyncio.run_in_executor` cho YOLO inference — scan interval 30s, latency không critical
