"""GET /ai/parking/detect-overview-live/ — Realtime car count trên camera tổng.

Đọc frame mới nhất từ virtual camera buffer, chạy YOLO detect xe (COCO
classes 2/3/5/7) và trả về số xe đang có trong bãi. Admin dashboard poll
endpoint này để biết realtime occupancy.
"""

import logging
import time
from typing import List, Optional

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from app.engine.slot_detection import VEHICLE_CLASS_IDS, get_slot_detector
from app.routers.camera import _buffer_lock, _virtual_frame_buffer

router = APIRouter()
logger = logging.getLogger(__name__)

_STALE_THRESHOLD_S = 10.0


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

    yolo = getattr(detector, "_yolo_model", None)
    if yolo is not None:
        try:
            results = yolo.predict(
                frame, conf=0.25, iou=0.4, verbose=False, classes=list(VEHICLE_CLASS_IDS)
            )
            method = "yolo11n"
            if results and len(results) > 0:
                r = results[0]
                if r.boxes is not None:
                    for b in r.boxes:
                        xyxy = b.xyxy[0].tolist()
                        boxes.append(
                            VehicleBox(
                                x1=int(xyxy[0]),
                                y1=int(xyxy[1]),
                                x2=int(xyxy[2]),
                                y2=int(xyxy[3]),
                                confidence=float(b.conf[0]),
                                class_id=int(b.cls[0]),
                            )
                        )
        except Exception as exc:
            logger.warning("YOLO detect fail: %s — fallback edge count 0", exc)

    return LiveOverviewResponse(
        camera_id=camera_id,
        frame_age_seconds=round(frame_age, 2),
        total_vehicles=len(boxes),
        boxes=boxes,
        detection_method=method,
        processing_time_ms=round((time.time() - t0) * 1000, 1),
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

    detector = get_slot_detector()
    yolo = getattr(detector, "_yolo_model", None)
    count = 0
    if yolo is not None:
        try:
            results = yolo.predict(
                frame, conf=0.25, iou=0.4, verbose=False, classes=list(VEHICLE_CLASS_IDS)
            )
            if results and len(results) > 0:
                r = results[0]
                if r.boxes is not None:
                    for b in r.boxes:
                        xyxy = b.xyxy[0].tolist()
                        x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
                        conf = float(b.conf[0])
                        # Green box + conf label
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 0), 2)
                        label = f"car {conf:.0%}"
                        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), (0, 220, 0), -1)
                        cv2.putText(
                            frame, label, (x1 + 2, y1 - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA,
                        )
                        count += 1
        except Exception as exc:
            logger.warning("YOLO annotate fail: %s", exc)

    # Top-left summary banner
    banner = f"AI detected: {count} vehicle(s) | YOLO11n"
    cv2.rectangle(frame, (0, 0), (340, 28), (0, 0, 0), -1)
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
