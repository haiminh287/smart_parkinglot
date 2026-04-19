"""GET /ai/parking/detect-overview-live/ — Realtime car count trên camera tổng.

Đọc frame mới nhất từ virtual camera buffer, chạy YOLO detect xe (COCO
classes 2/3/5/7) và trả về số xe đang có trong bãi. Admin dashboard poll
endpoint này để biết realtime occupancy.
"""

import logging
import time
from typing import List, Optional

import cv2
import httpx
import numpy as np
from app.config import settings
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from app.engine.slot_detection import VEHICLE_CLASS_IDS, get_slot_detector
from app.routers.camera import _buffer_lock, _virtual_frame_buffer

router = APIRouter()
logger = logging.getLogger(__name__)

_STALE_THRESHOLD_S = 10.0


def _detect_slots_by_orange(frame: np.ndarray) -> List[dict]:
    """Detect ô đỗ qua khung viền CAM. Unity slot có divider/cap lines màu cam.
    Sau đó kiểm tra từng slot xem có xe bên trong không (dựa trên màu sắc
    bên trong slot: sàn xanh = trống, có màu khác = occupied).

    Returns: list of dict {x1,y1,x2,y2, status: 'occupied'|'available', confidence}
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    # Cam line marker — range rộng để chịu được shadow + lighting khác nhau.
    # Hue 3-35 (cam → vàng cam), S>60 (không phải xám), V>80 (không quá tối).
    orange_mask = cv2.inRange(hsv, (3, 60, 80), (35, 255, 255))
    # Close gap để nối các đoạn line bị đứt do bóng, rồi dilate để line dày hơn
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    orange_mask = cv2.morphologyEx(orange_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
    orange_mask = cv2.dilate(orange_mask, kernel, iterations=1)

    # Find filled slot regions — invert mask + floodfill không work tốt cho rect
    # → dùng contour hierarchy: tìm rect đóng bên trong các đường cam.
    contours, hierarchy = cv2.findContours(orange_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    img_h, img_w = frame.shape[:2]
    img_area = img_h * img_w
    slots: List[dict] = []
    seen_rects = set()

    # Dùng Hough rectangles: lấy bounding rect của từng contour, filter size
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        # Slot ~ 0.2% đến 2% tổng area
        if area < img_area * 0.0015 or area > img_area * 0.03:
            continue
        aspect = max(w, h) / max(min(w, h), 1)
        if aspect > 3.5:
            continue
        # Dedupe rects gần giống nhau
        key = (x // 10, y // 10, w // 10, h // 10)
        if key in seen_rects:
            continue
        seen_rects.add(key)

        # Sample HSV ở center để check occupancy
        cx, cy = x + w // 2, y + h // 2
        roi = hsv[max(0, cy - 6):cy + 6, max(0, cx - 6):cx + 6]
        if roi.size == 0:
            continue
        mean_h, mean_s, mean_v = roi[..., 0].mean(), roi[..., 1].mean(), roi[..., 2].mean()
        # Sàn slot xanh lá: H~35-85, S~80-200
        is_empty = 35 <= mean_h <= 85 and mean_s > 60
        status = "available" if is_empty else "occupied"
        slots.append({
            "x1": x, "y1": y, "x2": x + w, "y2": y + h,
            "status": status,
            "confidence": 0.8,
        })
    return slots


class VehicleBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    class_id: int


class LiveOverviewResponse(BaseModel):
    camera_id: str
    frame_age_seconds: float
    total_vehicles: int
    boxes: List[VehicleBox]
    detection_method: str
    processing_time_ms: float
    # Ground truth từ DB để so sánh
    db_total_slots: Optional[int] = None
    db_occupied: Optional[int] = None
    db_available: Optional[int] = None


async def _fetch_db_slot_stats() -> dict:
    """Query parking-service để biết ground truth."""
    url = f"{settings.PARKING_SERVICE_URL}/parking/slots/"
    headers = {"X-Gateway-Secret": settings.GATEWAY_SECRET, "X-User-ID": "system"}
    params = {"limit": 500}
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                return {}
            data = resp.json()
            results = data.get("results", [])
            total = data.get("count", len(results))
            occupied = sum(1 for s in results if s.get("status") in ("occupied", "reserved"))
            available = sum(1 for s in results if s.get("status") == "available")
            return {"total": total, "occupied": occupied, "available": available}
    except Exception:
        return {}


@router.get("/detect-overview-live/", response_model=LiveOverviewResponse)
async def detect_overview_live(
    camera_id: str = Query("virtual-f1-overview", description="Camera nào để detect"),
) -> LiveOverviewResponse:
    """Đếm số xe trên frame mới nhất của camera tổng.

    Không yêu cầu upload — đọc thẳng từ buffer. Dùng cho admin dashboard
    để hiển thị realtime occupancy.
    """
    t0 = time.time()

    with _buffer_lock:
        vf = _virtual_frame_buffer.get(camera_id)

    if vf is None:
        raise HTTPException(
            status_code=404,
            detail=f"Chưa có frame nào cho camera '{camera_id}'. Unity chưa stream?",
        )

    frame_age = time.monotonic() - vf.timestamp
    if frame_age > _STALE_THRESHOLD_S:
        logger.warning(
            "Frame stale: camera=%s age=%.1fs", camera_id, frame_age
        )

    img_array = np.frombuffer(vf.jpeg_data, dtype=np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=422, detail="Không decode được frame")

    detector = get_slot_detector()
    boxes: List[VehicleBox] = []
    method = "opencv_fallback"

    # Detect slots qua orange border + check occupancy từng slot
    slots = _detect_slots_by_orange(frame)
    occupied = sum(1 for s in slots if s["status"] == "occupied")
    method = "opencv_slot_detection"

    for s in slots:
        boxes.append(VehicleBox(
            x1=s["x1"], y1=s["y1"], x2=s["x2"], y2=s["y2"],
            confidence=s["confidence"],
            class_id=1 if s["status"] == "occupied" else 0,  # 1=occupied, 0=available
        ))

    db = await _fetch_db_slot_stats()
    return LiveOverviewResponse(
        camera_id=camera_id,
        frame_age_seconds=round(frame_age, 2),
        total_vehicles=occupied,
        boxes=boxes,
        detection_method=method,
        processing_time_ms=round((time.time() - t0) * 1000, 1),
        db_total_slots=db.get("total"),
        db_occupied=db.get("occupied"),
        db_available=db.get("available"),
    )


@router.get("/detect-overview-annotated/")
async def detect_overview_annotated(
    camera_id: str = Query("virtual-f1-overview"),
) -> Response:
    """Trả frame camera tổng với bounding boxes YOLO vẽ overlay lên — admin
    dashboard refresh periodic để xem AI đang detect đúng không."""
    with _buffer_lock:
        vf = _virtual_frame_buffer.get(camera_id)
    if vf is None:
        raise HTTPException(status_code=404, detail=f"No frame for camera {camera_id}")

    img_array = np.frombuffer(vf.jpeg_data, dtype=np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=422, detail="Cannot decode frame")

    # Orange-border slot detection + occupancy check per slot
    slots = _detect_slots_by_orange(frame)
    total = len(slots)
    occupied = sum(1 for s in slots if s["status"] == "occupied")
    available = total - occupied

    for s in slots:
        x1, y1, x2, y2 = s["x1"], s["y1"], s["x2"], s["y2"]
        if s["status"] == "occupied":
            color = (0, 0, 230)  # đỏ
            label = "OCCUPIED"
        else:
            color = (0, 220, 0)  # xanh
            label = "FREE"
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        cv2.rectangle(frame, (x1, y1 - th - 4), (x1 + tw + 4, y1), color, -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 3),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

    # Top-left summary banner
    banner = f"AI: {total} slots | {occupied} occupied | {available} free"
    cv2.rectangle(frame, (0, 0), (420, 28), (0, 0, 0), -1)
    cv2.putText(
        frame, banner, (8, 20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1, cv2.LINE_AA,
    )

    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ok:
        raise HTTPException(status_code=500, detail="Encode fail")
    return Response(
        content=buf.tobytes(),
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
