"""POST /detect-occupancy/ — YOLO11n parking-slot occupancy detection."""

import asyncio
import json

import cv2
import numpy as np
from app.engine.slot_detection import SlotBbox, get_slot_detector
from app.schemas.ai import OccupancyDetectionResponse
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

router = APIRouter()


@router.post("/detect-occupancy/", response_model=OccupancyDetectionResponse)
async def detect_parking_occupancy(
    image: UploadFile = File(..., description="Ảnh bãi xe từ camera"),
    camera_id: str = Form(..., description="Camera ID"),
    slots: str = Form(
        ...,
        description=(
            "JSON list of slot bboxes: "
            '[{"slot_id":"...","slot_code":"...","zone_id":"...",'
            '"x1":0,"y1":0,"x2":100,"y2":100}]'
        ),
    ),
):
    """
    Detect vehicle occupancy for parking slots in a camera frame.

    Uses YOLO11n if model is loaded, falls back to OpenCV edge/contour analysis.
    Slots are defined by bounding boxes (pixel coordinates) in the uploaded image.
    """
    # Parse and validate slots JSON
    try:
        slots_data = json.loads(slots)
        if not isinstance(slots_data, list):
            raise ValueError("slots must be a JSON array")
        slot_list = [
            SlotBbox(
                slot_id=str(s["slot_id"]),
                slot_code=str(s["slot_code"]),
                zone_id=str(s["zone_id"]),
                x1=int(s["x1"]),
                y1=int(s["y1"]),
                x2=int(s["x2"]),
                y2=int(s["y2"]),
            )
            for s in slots_data
        ]
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid slots JSON: {exc}")

    # Decode image
    contents = await image.read()
    img_array = np.frombuffer(contents, dtype=np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=422, detail="Cannot decode image file")

    # Run detection in thread pool (YOLO/OpenCV are sync/CPU-bound)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, get_slot_detector().detect_occupancy, frame, slot_list, camera_id
    )
    return result
