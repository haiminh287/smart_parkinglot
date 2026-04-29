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

from app.routers.camera import _buffer_lock, _virtual_frame_buffer

router = APIRouter()
logger = logging.getLogger(__name__)

_STALE_THRESHOLD_S = 10.0


# Cache grid "tốt nhất từng thấy" — khi xe to chèn qua viền slot bên cạnh,
# frame hiện tại có thể detect ít hơn. Fallback về cache giữ đủ 72 slot
# bằng cách re-classify status tại vị trí slot đã biết.
_BEST_GRID_CACHE: List[dict] = []


def _reconstruct_missing_slots_in_rows(cells: List[dict], hsv: np.ndarray) -> List[dict]:
    """Group cells by row (Y), interpolate missing slots along X.

    Logic: V1 layout là grid đều. Nếu 1 hàng có 15/18 slot detected thì
    3 slot bị xe che vẫn phải ở vị trí đoán được từ median spacing.
    Thêm các slot nội suy + classify status từ HSV patch.
    """
    if len(cells) < 10:
        return cells

    # Cluster by Y: 2 cell cùng row nếu Y center gần nhau (< 0.5 * slot height)
    import statistics
    heights = [c["y2"] - c["y1"] for c in cells]
    med_h = statistics.median(heights)
    row_gap = med_h * 0.5

    cells_sorted = sorted(cells, key=lambda c: (c["y1"] + c["y2"]) / 2)
    rows: List[List[dict]] = []
    for c in cells_sorted:
        cy = (c["y1"] + c["y2"]) / 2
        placed = False
        for row in rows:
            row_cy = (row[0]["y1"] + row[0]["y2"]) / 2
            if abs(cy - row_cy) < row_gap:
                row.append(c)
                placed = True
                break
        if not placed:
            rows.append([c])

    img_h, img_w = hsv.shape[:2]
    out: List[dict] = []
    for row in rows:
        out.extend(row)
        if len(row) < 3:
            continue
        # Sort by X, find median width + median step (center-to-center)
        row_sorted = sorted(row, key=lambda c: c["x1"])
        widths = [c["x2"] - c["x1"] for c in row_sorted]
        med_w = statistics.median(widths)
        centers_x = [(c["x1"] + c["x2"]) / 2 for c in row_sorted]
        steps = [centers_x[i + 1] - centers_x[i] for i in range(len(centers_x) - 1)]
        if not steps:
            continue
        med_step = statistics.median(steps)
        if med_step <= 0 or med_w <= 0:
            continue

        # Y range common to row
        y1_med = int(statistics.median([c["y1"] for c in row_sorted]))
        y2_med = int(statistics.median([c["y2"] for c in row_sorted]))

        # Scan gaps: nếu 2 cell liền kề cách nhau > 1.7 * med_step → có slot ở giữa
        for i in range(len(row_sorted) - 1):
            gap = centers_x[i + 1] - centers_x[i]
            n_missing = int(round(gap / med_step)) - 1
            if n_missing < 1:
                continue
            for m in range(1, n_missing + 1):
                cx = int(centers_x[i] + m * med_step)
                cy = (y1_med + y2_med) // 2
                w = int(med_w)
                h = y2_med - y1_med
                x1 = max(cx - w // 2, 0)
                x2 = min(cx + w // 2, img_w - 1)
                status, _ = _classify_slot_status(hsv, cx, cy, w, h)
                out.append({
                    "x1": x1, "y1": y1_med,
                    "x2": x2, "y2": y2_med,
                    "status": status,
                    "confidence": 0.7,
                })
    return out


def _iou(a: dict, b: dict) -> float:
    x1 = max(a["x1"], b["x1"]); y1 = max(a["y1"], b["y1"])
    x2 = min(a["x2"], b["x2"]); y2 = min(a["y2"], b["y2"])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    area_a = (a["x2"] - a["x1"]) * (a["y2"] - a["y1"])
    area_b = (b["x2"] - b["x1"]) * (b["y2"] - b["y1"])
    return inter / max(area_a + area_b - inter, 1)


def _classify_slot_status(hsv: np.ndarray, cx: int, cy: int, w: int, h: int) -> tuple:
    """Sample patch ở giữa slot và phân trạng thái dựa trên HSV.

    Unity slot floor màu xanh lá (available). Khi có xe đỗ lên, thân xe
    (màu random) phủ lên nên patch center không còn là green → occupied.

    Returns (status, confidence_adjustment)
    """
    img_h, img_w = hsv.shape[:2]
    # Patch 40% kích thước slot ở giữa để tránh dính vào đường viền cam
    pw = max(int(w * 0.35), 3)
    ph = max(int(h * 0.35), 3)
    x1 = max(cx - pw // 2, 0); x2 = min(cx + pw // 2 + 1, img_w)
    y1 = max(cy - ph // 2, 0); y2 = min(cy + ph // 2 + 1, img_h)
    patch = hsv[y1:y2, x1:x2]
    if patch.size == 0:
        return "available", 0.0

    h_ch = patch[:, :, 0]; s_ch = patch[:, :, 1]; v_ch = patch[:, :, 2]
    # Tỷ lệ pixel "green floor" trong patch
    green_px = ((h_ch >= 35) & (h_ch <= 95) & (s_ch > 40) & (v_ch > 40))
    green_ratio = float(green_px.mean())
    orange_px = ((h_ch >= 3) & (h_ch <= 30) & (s_ch > 80))
    orange_ratio = float(orange_px.mean())
    # Dark / nền đen (xà, cột, aisle) — không phải xe → coi là available an toàn
    dark_px = (v_ch < 50)
    dark_ratio = float(dark_px.mean())

    # >55% green → trống (ngưỡng nhẹ hơn vì xe có thể che 1 góc slot
    # mà chưa chắc đã occupy — nhưng xe che >50% là rõ ràng đang đỗ)
    if green_ratio > 0.55:
        return "available", 0.0
    # >40% orange → reserved (ô đã book chưa vào)
    if orange_ratio > 0.4:
        return "occupied", 0.0
    # Toàn patch đen (xà/cột/aisle), không có green → không phải xe
    if dark_ratio > 0.75 and green_ratio < 0.05:
        return "available", 0.0
    # Còn lại: xe thân phủ lên >45% slot → occupied
    return "occupied", 0.0


def _detect_slots_by_orange(frame: np.ndarray) -> List[dict]:
    """Detect ô đỗ xe bằng cách tìm các cell kín bao bởi đường viền CAM.

    Logic:
      1. Orange mask → morph close để nối gap trong viền
      2. Dilate nhẹ để grid kín hoàn toàn
      3. Invert → mỗi cell kín = 1 blob trắng riêng
      4. findContours → filter theo size + rectangularity
      5. Sample center HSV phân green=available / khác=occupied

    Returns: list of dict {x1,y1,x2,y2, status, confidence}
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    img_h, img_w = frame.shape[:2]
    img_area = img_h * img_w

    # Orange viền slot (Unity Unlit shader → H ~19-23, S >150, V >90).
    # Giữ upper=24 vì anti-alias mép đẩy H lên tới 23.
    orange_mask = cv2.inRange(hsv, (5, 100, 90), (24, 255, 255))

    # Close gap nhỏ ở corner giao cap+divider, dilate nhẹ đảm bảo khép kín
    kernel3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    grid = cv2.morphologyEx(orange_mask, cv2.MORPH_CLOSE, kernel3, iterations=2)
    grid = cv2.dilate(grid, kernel3, iterations=1)

    # RETR_CCOMP → hierarchy 2 lớp: outer=nhóm viền, child=HỐ bên trong
    # (mỗi slot là 1 hố vì viền cam bao quanh). Invert approach thất bại vì
    # các aisle giữa row nối tất cả cell thành 1 blob.
    contours, hierarchy = cv2.findContours(grid, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return []
    hierarchy = hierarchy[0]  # shape (N,4)

    slots: List[dict] = []
    for i, c in enumerate(contours):
        # parent != -1 → đây là inner hole của orange grid = slot interior
        if hierarchy[i][3] == -1:
            continue
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        # Slot chiếm 0.04%–2% tổng area; 0.04 là mức chặn noise mà vẫn
        # giữ slot xa camera kích thước nhỏ.
        if area < img_area * 0.0004 or area > img_area * 0.02:
            continue
        aspect = max(w, h) / max(min(w, h), 1)
        # Slot parking tỷ lệ 1.5–2.5 nhưng allow rộng hơn cho camera nghiêng
        if aspect > 3.5:
            continue
        # Rectangularity: contour phải lấp >55% bounding box (loại chắp vá)
        contour_area = cv2.contourArea(c)
        if contour_area / max(area, 1) < 0.55:
            continue

        cx, cy = x + w // 2, y + h // 2
        status, _ = _classify_slot_status(hsv, cx, cy, w, h)
        slots.append({
            "x1": int(x), "y1": int(y), "x2": int(x + w), "y2": int(y + h),
            "status": status,
            "confidence": 0.85,
        })

    # NMS để loại duplicate từ contour lồng nhau
    slots.sort(key=lambda s: -(s["x2"] - s["x1"]) * (s["y2"] - s["y1"]))
    kept: List[dict] = []
    for s in slots:
        if all(_iou(s, k) < 0.3 for k in kept):
            kept.append(s)

    # Row reconstruction: bù slot bị xe che hoàn toàn (cell không form).
    # Classify giờ đã treat dark patch như available → không false positive.
    kept = _reconstruct_missing_slots_in_rows(kept, hsv)

    # ── Grid cache fallback: xe to che viền cam bên cạnh khiến 2 cell
    # merge → filter size loại bỏ → slot mất. Nếu frame tốt từng thấy grid
    # đầy đủ hơn, bù bằng vị trí cache + re-classify status tại đó.
    global _BEST_GRID_CACHE
    if len(kept) > len(_BEST_GRID_CACHE):
        _BEST_GRID_CACHE = [dict(s) for s in kept]  # deep copy

    if _BEST_GRID_CACHE and len(kept) < len(_BEST_GRID_CACHE):
        filled: List[dict] = []
        for cached in _BEST_GRID_CACHE:
            match = next((k for k in kept if _iou(k, cached) > 0.3), None)
            if match:
                filled.append(match)
            else:
                # Slot bị che viền — re-classify status ngay tại vị trí cache
                w = cached["x2"] - cached["x1"]
                h = cached["y2"] - cached["y1"]
                cx = cached["x1"] + w // 2
                cy = cached["y1"] + h // 2
                status, _ = _classify_slot_status(hsv, cx, cy, w, h)
                filled.append({**cached, "status": status, "confidence": 0.75})
        return filled

    return kept


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

    boxes: List[VehicleBox] = []

    # Detect slots qua orange grid + sample center HSV phân status
    slots = _detect_slots_by_orange(frame)
    total_slots = len(slots)
    occupied = sum(1 for s in slots if s["status"] == "occupied")
    available = total_slots - occupied
    method = "opencv_orange_grid"
    logger.info(
        "detect-overview-live: camera=%s slots=%d occupied=%d available=%d",
        camera_id, total_slots, occupied, available,
    )

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
