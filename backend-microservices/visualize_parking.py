"""
Parking occupancy visualization:
  - Calls detect-occupancy API with parking_lot.jpg
  - Draws slot bounding boxes colored by status
  - Saves annotated image to test_images/parking_annotated.jpg
"""
import json
import os
import sys
import requests
import cv2
import numpy as np

BASE_AI = "http://localhost:8009"
GW = {"X-Gateway-Secret": os.getenv("GATEWAY_SECRET", "changeme-secret")}
IMG_IN  = "/tmp/parking_lot.jpg"
IMG_OUT = "/tmp/parking_annotated.jpg"

# parking_lot.jpg: 1300×953px — bboxes dựa trên vạch kẻ cam thực tế (16 slots, 2 rows)
SLOTS = [
    # Row A (top row, slots A1-A8)
    {"slot_id": "s1",  "slot_code": "A1", "x1": 0,    "y1": 130, "x2": 160,  "y2": 460},
    {"slot_id": "s2",  "slot_code": "A2", "x1": 160,  "y1": 130, "x2": 315,  "y2": 460},
    {"slot_id": "s3",  "slot_code": "A3", "x1": 315,  "y1": 130, "x2": 475,  "y2": 460},
    {"slot_id": "s4",  "slot_code": "A4", "x1": 475,  "y1": 130, "x2": 630,  "y2": 460},
    {"slot_id": "s5",  "slot_code": "A5", "x1": 630,  "y1": 130, "x2": 785,  "y2": 460},
    {"slot_id": "s6",  "slot_code": "A6", "x1": 785,  "y1": 130, "x2": 940,  "y2": 460},
    {"slot_id": "s7",  "slot_code": "A7", "x1": 940,  "y1": 130, "x2": 1100, "y2": 460},
    {"slot_id": "s8",  "slot_code": "A8", "x1": 1100, "y1": 130, "x2": 1300, "y2": 460},
    # Row B (bottom row, slots B1-B8)
    {"slot_id": "s9",  "slot_code": "B1", "x1": 0,    "y1": 495, "x2": 155,  "y2": 870},
    {"slot_id": "s10", "slot_code": "B2", "x1": 155,  "y1": 495, "x2": 310,  "y2": 870},
    {"slot_id": "s11", "slot_code": "B3", "x1": 310,  "y1": 495, "x2": 465,  "y2": 870},
    {"slot_id": "s12", "slot_code": "B4", "x1": 465,  "y1": 495, "x2": 620,  "y2": 870},
    {"slot_id": "s13", "slot_code": "B5", "x1": 620,  "y1": 495, "x2": 780,  "y2": 870},
    {"slot_id": "s14", "slot_code": "B6", "x1": 780,  "y1": 495, "x2": 940,  "y2": 870},
    {"slot_id": "s15", "slot_code": "B7", "x1": 940,  "y1": 495, "x2": 1100, "y2": 870},
    {"slot_id": "s16", "slot_code": "B8", "x1": 1100, "y1": 495, "x2": 1260, "y2": 870},
]

STATUS_COLORS = {
    "available": (0, 200, 0),    # green
    "occupied":  (0, 0, 220),    # red (BGR)
    "unknown":   (0, 165, 255),  # orange
}

def main():
    if not os.path.exists(IMG_IN):
        print(f"ERROR: {IMG_IN} not found", file=sys.stderr)
        sys.exit(1)

    # --- Call API ---
    with open(IMG_IN, "rb") as f:
        resp = requests.post(
            BASE_AI + "/ai/parking/detect-occupancy/",
            data={"camera_id": "cam-viz-001", "slots": json.dumps(SLOTS)},
            files={"image": ("parking.jpg", f, "image/jpeg")},
            headers=GW,
            timeout=30,
        )

    if resp.status_code != 200:
        print(f"API error {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
        sys.exit(1)

    result = resp.json()
    slot_results = {s["slotCode"]: s for s in result.get("slots", [])}

    print(f"Detection method : {result.get('detectionMethod')}")
    print(f"Total slots      : {result.get('totalSlots')}")
    print(f"Available        : {result.get('totalAvailable')}")
    print(f"Occupied         : {result.get('totalOccupied')}")
    print(f"Processing time  : {result.get('processingTimeMs')} ms")
    print()

    # --- Load image ---
    img = cv2.imread(IMG_IN)
    if img is None:
        print(f"ERROR: cannot decode {IMG_IN}", file=sys.stderr)
        sys.exit(1)

    h, w = img.shape[:2]
    # Add a semi-transparent overlay for boxes
    overlay = img.copy()

    for slot in SLOTS:
        code = slot["slot_code"]
        x1, y1, x2, y2 = slot["x1"], slot["y1"], slot["x2"], slot["y2"]

        sr = slot_results.get(code, {})
        status = sr.get("status", "unknown")
        conf   = sr.get("confidence", 0.0)
        method = sr.get("method", "?")

        color = STATUS_COLORS.get(status, STATUS_COLORS["unknown"])

        # Filled semi-transparent box
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
        print(f"  Slot {code}: status={status}  conf={conf:.3f}  method={method}")

    # Blend overlay at 25% opacity
    cv2.addWeighted(overlay, 0.25, img, 0.75, 0, img)

    # Draw solid borders and labels on top
    for slot in SLOTS:
        code = slot["slot_code"]
        x1, y1, x2, y2 = slot["x1"], slot["y1"], slot["x2"], slot["y2"]

        sr = slot_results.get(code, {})
        status = sr.get("status", "unknown")
        conf   = sr.get("confidence", 0.0)

        color = STATUS_COLORS.get(status, STATUS_COLORS["unknown"])
        dark  = tuple(max(0, c - 60) for c in color)

        # Border (3px)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)

        # Label background
        label = f"{code}  {status.upper()}  {conf:.0%}"
        font       = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.65
        thickness  = 2
        (lw, lh), bl = cv2.getTextSize(label, font, font_scale, thickness)

        pad = 6
        lx, ly = x1 + 8, y1 + lh + pad + 8
        cv2.rectangle(img, (lx - pad, ly - lh - pad), (lx + lw + pad, ly + bl + pad), dark, -1)
        cv2.putText(img, label, (lx, ly), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    # Legend (bottom-right corner)
    legend_items = [("AVAILABLE", (0, 200, 0)), ("OCCUPIED", (0, 0, 220)), ("UNKNOWN", (0, 165, 255))]
    lx_base, ly_base = w - 200, h - 20
    for i, (lbl, col) in enumerate(reversed(legend_items)):
        ly = ly_base - i * 28
        cv2.rectangle(img, (lx_base, ly - 14), (lx_base + 20, ly + 4), col, -1)
        cv2.putText(img, lbl, (lx_base + 26, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

    # Title
    title = f"ParkSmart — Slot Detection ({result.get('detectionMethod', '?')})"
    cv2.putText(img, title, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(img, title, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30),    1, cv2.LINE_AA)

    cv2.imwrite(IMG_OUT, img)
    print(f"\nAnnotated image saved: {IMG_OUT}")


if __name__ == "__main__":
    main()
