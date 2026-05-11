"""
ParkSmart AI Slot Detection — Comprehensive Test Script
========================================================
Tests the AI service virtual camera + occupancy detection pipeline.
Targets: http://localhost:8009

Usage:
    python test_ai_detection_unity.py
"""

import json
import os
import sys
import time
from pathlib import Path

import cv2
import httpx
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────── #

BASE_URL = os.environ.get("AI_SERVICE_URL", "http://localhost:8009")
GATEWAY_SECRET = os.environ.get("GATEWAY_SECRET")
if not GATEWAY_SECRET:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    GATEWAY_SECRET = os.environ.get("GATEWAY_SECRET")
    if not GATEWAY_SECRET:
        raise RuntimeError("GATEWAY_SECRET env var required. Set it or create ../.env")
AUTH_HEADERS = {"X-Gateway-Secret": GATEWAY_SECRET}

SCRIPT_DIR = Path(__file__).resolve().parent
MEDIA_DIR = SCRIPT_DIR / "media"

VIRTUAL_CAMERAS = [
    "virtual-f1-overview",
    "virtual-f2-overview",
    "virtual-gate-in",
    "virtual-gate-out",
    "virtual-zone-south",
    "virtual-zone-north",
]

# ── Helpers ───────────────────────────────────────────────────────────────── #

_pass_count = 0
_fail_count = 0


def section(title: str) -> None:
    print(f"\n{'=' * 64}")
    print(f"  {title}")
    print(f"{'=' * 64}")


def ok(tag: str, detail: str = "") -> None:
    global _pass_count
    _pass_count += 1
    msg = f"  [PASS] ✅  {tag}"
    if detail:
        msg += f"\n         {detail}"
    print(msg)


def fail(tag: str, detail: str = "") -> None:
    global _fail_count
    _fail_count += 1
    msg = f"  [FAIL] ❌  {tag}"
    if detail:
        msg += f"\n         {detail}"
    print(msg)


import math


def _world_to_pixel(
    wx: float,
    wz: float,
    cam_y: float,
    img_w: int,
    img_h: int,
    fov_v_deg: float,
) -> tuple[int, int]:
    """Project world XZ position to pixel coordinates for overhead camera.

    Camera: position (0, cam_y, 0), rotation (90,0,0) = looking straight down.
    Camera right = world +X, camera-up-in-screen = world +Z.
    Screen Y increases downward (top=+Z, bottom=-Z).
    """
    aspect = img_w / img_h
    half_fov_v = math.radians(fov_v_deg / 2.0)
    half_world_z = cam_y * math.tan(half_fov_v)  # world units visible top-to-bottom / 2
    half_world_x = half_world_z * aspect  # world units visible left-to-right / 2
    px = int((wx + half_world_x) / (2 * half_world_x) * img_w)
    py = int((half_world_z - wz) / (2 * half_world_z) * img_h)
    return px, py


def generate_parking_lot_slot_bboxes(
    level: int = 0,  # 0 = B1 (4 rows × 18), 1 = Tang1 (2 rows × 18)
    img_w: int = 640,
    img_h: int = 480,
    cam_y: float = 35.0,  # F1 camera y=35, F2 camera y=38.5
    fov_v_deg: float = 80.0,  # vertical FOV in degrees
    floor_y: float = 0.0,  # world Y of the floor surface
    lot_z_offset: float = 0.0,  # world Z offset of ParkingLotGenerator transform.
    # Tune if bboxes appear shifted N/S: positive = lots more north
) -> list[dict]:
    """Generate pixel bounding boxes for every car slot using ParkingLotGenerator geometry.

    Matches ParkingLotGenerator.cs:
      platformWidth=70, slotWidth=2.5, slotDepth=5, laneWidth=6
      carZoneStartX = -platformWidth/2 + 8 = -27
      zRow1 = -5.5, zRow2 = +5.5
      zRow3 = -16.5 (B1 only), zRow4 = +16.5 (B1 only)

    Calibration notes:
      - Inner rows aligned → lot_z_offset correct (or use default 0.0)
      - Outer rows appear over dark areas → slot floor opacity too low in Unity
        (fix: ParkingLotGenerator.cs line ~329: change 0.35f alpha → 0.55f)
      - If all rows appear shifted N/S: measure actual slot pixel centre, solve for lot_z_offset
    """
    # Parking lot parameters
    SLOT_W = 2.5
    SLOT_D = 5.0
    LANE_W = 6.0
    PLATFORM_W = 70.0
    AISLE_HALF = LANE_W / 2.0
    SLOTS_PER_ROW = 18
    START_X = -PLATFORM_W / 2.0 + 8.0  # = -27

    # Effective camera height above floor
    eff_cam_y = cam_y - floor_y

    # Row Z centers (local to ParkingLotGenerator, then add lot_z_offset for world position)
    z_row1 = -(AISLE_HALF + SLOT_D / 2.0) + lot_z_offset  # -5.5 (+ offset)
    z_row2 = +(AISLE_HALF + SLOT_D / 2.0) + lot_z_offset  # +5.5 (+ offset)

    rows: list[tuple[float, str, str, int]] = [
        (
            z_row1,
            "V1" if level == 0 else "A",
            "B1-inner-S" if level == 0 else "F1-A",
            1,
        ),
        (
            z_row2,
            "V1" if level == 0 else "B",
            "B1-inner-N" if level == 0 else "F1-B",
            SLOTS_PER_ROW + 1 if level == 0 else 1,
        ),
    ]
    if level == 0:
        z_row3 = z_row1 - SLOT_D / 2.0 - LANE_W - SLOT_D / 2.0  # -16.5 (+ offset)
        z_row4 = z_row2 + SLOT_D / 2.0 + LANE_W + SLOT_D / 2.0  # +16.5 (+ offset)
        rows += [
            (z_row3, "V1", "B1-outer-S", 2 * SLOTS_PER_ROW + 1),
            (z_row4, "V1", "B1-outer-N", 3 * SLOTS_PER_ROW + 1),
        ]

    # Half slot extents in world units
    hw = SLOT_W / 2.0  # 1.25 m
    hd = SLOT_D / 2.0  # 2.5 m

    bboxes: list[dict] = []
    for z_center, prefix, zone_id, idx_start in rows:
        for i in range(SLOTS_PER_ROW):
            x_center = START_X + i * SLOT_W
            slot_num = idx_start + i
            slot_code = f"{prefix}-{slot_num:02d}"

            # Project the 4 corners
            px_min, py_min = _world_to_pixel(
                x_center - hw, z_center + hd, eff_cam_y, img_w, img_h, fov_v_deg
            )
            px_max, py_max = _world_to_pixel(
                x_center + hw, z_center - hd, eff_cam_y, img_w, img_h, fov_v_deg
            )

            # Clamp to image bounds
            x1 = max(0, min(px_min, px_max))
            y1 = max(0, min(py_min, py_max))
            x2 = min(img_w - 1, max(px_min, px_max))
            y2 = min(img_h - 1, max(py_min, py_max))

            if x2 <= x1 or y2 <= y1:  # skip out-of-frame slots
                continue

            bboxes.append(
                {
                    "slot_id": f"{prefix.lower()}-{slot_num:03d}",
                    "slot_code": slot_code,
                    "zone_id": zone_id,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                }
            )

    return bboxes


def get_unity_snapshot(client: httpx.Client, camera_id: str) -> bytes | None:
    """Fetch the latest Unity camera frame from the AI service buffer.

    Returns JPEG bytes, or None if no frame is available (Unity not streaming).
    """
    try:
        r = client.get("/ai/cameras/snapshot", params={"camera_id": camera_id})
        if r.status_code == 200 and len(r.content) > 100:
            return r.content
        return None
    except Exception:
        return None


# ── Test Steps ────────────────────────────────────────────────────────────── #


def test_health(client: httpx.Client) -> bool:
    section("1. Health Check")
    try:
        r = client.get("/health/")
        data = r.json()
        if r.status_code == 200:
            ok("GET /health/", f"status={data.get('status', '?')}")
            return True
        fail("GET /health/", f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as exc:
        fail("GET /health/", str(exc))
    return False


def test_push_frame(client: httpx.Client, camera_id: str, jpeg_data: bytes) -> bool:
    """Push a single JPEG frame for a virtual camera."""
    try:
        r = client.post(
            "/ai/cameras/frame",
            content=jpeg_data,
            headers={
                **AUTH_HEADERS,
                "X-Camera-ID": camera_id,
                "Content-Type": "image/jpeg",
            },
        )
        if r.status_code == 200 and r.json().get("success"):
            ok(f"Push frame → {camera_id}", f"{len(jpeg_data)} bytes")
            return True
        fail(f"Push frame → {camera_id}", f"HTTP {r.status_code}: {r.text[:200]}")
    except Exception as exc:
        fail(f"Push frame → {camera_id}", str(exc))
    return False


def test_snapshot(
    client: httpx.Client, camera_id: str, save_path: Path
) -> bytes | None:
    """Retrieve snapshot for a virtual camera, save to disk, return bytes."""
    try:
        r = client.get("/ai/cameras/snapshot", params={"camera_id": camera_id})
        if r.status_code == 200 and len(r.content) > 100:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(r.content)
            ok(
                f"Snapshot ← {camera_id}",
                f"saved → {save_path.name} ({len(r.content):,} bytes)",
            )
            return r.content
        fail(
            f"Snapshot ← {camera_id}",
            f"HTTP {r.status_code} — Unity not streaming or buffer empty",
        )
    except Exception as exc:
        fail(f"Snapshot ← {camera_id}", str(exc))
    return None


def test_detect_occupancy(
    client: httpx.Client,
    jpeg_data: bytes,
    slots: list[dict],
    camera_id: str = "virtual-f1-overview",
    result_filename: str = "unity_detection_result.json",
) -> dict | None:
    """Call detect-occupancy with a Unity camera frame and return the response dict."""
    section("4. AI Detect Occupancy (Unity Camera Frame)")
    print(f"     camera_id : {camera_id}")
    print(f"     frame size: {len(jpeg_data):,} bytes")
    print(f"     bboxes    : {len(slots)} slots")
    try:
        r = client.post(
            "/ai/parking/detect-occupancy/",
            files={"image": ("unity_frame.jpg", jpeg_data, "image/jpeg")},
            data={"camera_id": camera_id, "slots": json.dumps(slots)},
            headers=AUTH_HEADERS,
            timeout=60.0,
        )
        if r.status_code == 200:
            data = r.json()
            total = data.get("totalSlots", data.get("total_slots", 0))
            avail = data.get("totalAvailable", data.get("total_available", 0))
            occup = data.get("totalOccupied", data.get("total_occupied", 0))
            method = data.get("detectionMethod", data.get("detection_method", "?"))
            ms = data.get("processingTimeMs", data.get("processing_time_ms", 0))
            ok(
                "POST /ai/parking/detect-occupancy/",
                f"total={total}  available={avail}  occupied={occup}  "
                f"method={method}  time={ms:.1f}ms",
            )
            result_path = MEDIA_DIR / result_filename
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            ok("Saved result JSON", str(result_path))
            return data
        fail(
            "POST /ai/parking/detect-occupancy/",
            f"HTTP {r.status_code}: {r.text[:300]}",
        )
    except Exception as exc:
        fail("POST /ai/parking/detect-occupancy/", str(exc))
    return None


def draw_annotated_image(
    image_bytes: bytes,
    detection_result: dict,
    slot_bboxes: list[dict],
    output_path: Path,
    title: str = "",
) -> bool:
    """Draw bounding boxes on a Unity camera frame based on AI detection results."""
    section("5. Draw Annotated Detection Image")
    try:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            fail("Decode image", "cv2.imdecode returned None")
            return False

        color_map = {
            "available": (0, 200, 0),  # green (BGR)
            "occupied": (0, 0, 220),  # red
            "unknown": (0, 200, 220),  # yellow
        }

        bbox_map = {s["slot_id"]: s for s in slot_bboxes}

        slot_list = detection_result.get("slots", [])
        for slot in slot_list:
            status = slot.get("status", "unknown")
            code = slot.get("slotCode", slot.get("slot_code", "?"))
            conf = slot.get("confidence", 0.0)

            # Get bbox from the original slot definitions
            slot_id = slot.get("slotId", slot.get("slot_id", ""))
            bbox = bbox_map.get(slot_id, {})
            x1 = bbox.get("x1", 0)
            y1 = bbox.get("y1", 0)
            x2 = bbox.get("x2", 0)
            y2 = bbox.get("y2", 0)

            color = color_map.get(status, (128, 128, 128))
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

            label = f"{code} {conf:.0%}"
            font_scale = 0.35
            thickness = 1
            (tw, th), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
            )
            cv2.rectangle(img, (x1, y1 - th - 4), (x1 + tw + 2, y1), color, -1)
            cv2.putText(
                img,
                label,
                (x1 + 1, y1 - 3),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (255, 255, 255),
                thickness,
            )

        # Draw title overlay
        if title:
            cv2.putText(
                img, title, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), img)
        ok("Annotated image saved", str(output_path))
        return True
    except Exception as exc:
        fail("Draw annotated image", str(exc))
        return False


def test_all_virtual_cameras(client: httpx.Client) -> tuple[int, int]:
    """Get snapshot for all 6 virtual cameras (Unity must be streaming)."""
    section("6. All Virtual Cameras — Snapshots from Unity")
    snapped = 0
    for cam_id in VIRTUAL_CAMERAS:
        snap_path = MEDIA_DIR / f"unity_snapshot_{cam_id.replace('virtual-', '')}.jpg"
        result = test_snapshot(client, cam_id, snap_path)
        if result is not None:
            snapped += 1
    return snapped


# ── Main ──────────────────────────────────────────────────────────────────── #


def main() -> int:
    print("ParkSmart AI Detection Test — Unity Camera Mode")
    print(f"Target: {BASE_URL}")
    print("Source: Live Unity virtual camera snapshots\n")

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    # Pre-generate slot bboxes (B1 = 72 car slots, F1 camera at y=35)
    b1_slots = generate_parking_lot_slot_bboxes(
        level=0, img_w=640, img_h=480, cam_y=35.0, fov_v_deg=80.0, floor_y=0.0
    )
    f1_slots = generate_parking_lot_slot_bboxes(
        level=1, img_w=640, img_h=480, cam_y=38.5, fov_v_deg=80.0, floor_y=4.5
    )
    print(f"  B1 car slot bboxes: {len(b1_slots)} slots")
    print(f"  F1 car slot bboxes: {len(f1_slots)} slots")

    health_ok = False
    snapshot_f1: bytes | None = None
    snapshot_f2: bytes | None = None
    detection_result: dict | None = None
    detection_result_f2: dict | None = None
    snapped_count = 0
    annotated_ok = False
    annotated_path = MEDIA_DIR / "unity_detection_annotated_b1.jpg"

    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        # 1. Health
        health_ok = test_health(client)
        if not health_ok:
            print(
                "\n❌ AI service not responding. Make sure it's running on port 8009."
            )
            return 1

        # 2. Get F1 overview snapshot from Unity
        section("2. Fetch Unity F1 Overview Snapshot")
        snap_path_f1 = MEDIA_DIR / "unity_snapshot_f1-overview.jpg"
        snapshot_f1 = test_snapshot(client, "virtual-f1-overview", snap_path_f1)
        if snapshot_f1 is None:
            print("\n  ⚠️  No frame in AI service buffer for virtual-f1-overview.")
            print(
                "      → Make sure Unity is in Play Mode and has been running for a few seconds."
            )
            print("      → VirtualCameraStreamer sends frames every 0.2s (5 FPS).")
            return 1

        # 3. Get F2 overview snapshot from Unity
        section("3. Fetch Unity F2 Overview Snapshot")
        snap_path_f2 = MEDIA_DIR / "unity_snapshot_f2-overview.jpg"
        snapshot_f2 = test_snapshot(client, "virtual-f2-overview", snap_path_f2)

        # 4. Detect occupancy — B1 from F1 camera
        detection_result = test_detect_occupancy(
            client,
            snapshot_f1,
            b1_slots,
            camera_id="virtual-f1-overview",
            result_filename="unity_detection_result_b1.json",
        )

        # 4b. Detect occupancy — Floor 1 from F2 camera (if available)
        if snapshot_f2 is not None:
            detection_result_f2 = test_detect_occupancy(
                client,
                snapshot_f2,
                f1_slots,
                camera_id="virtual-f2-overview",
                result_filename="unity_detection_result_f1.json",
            )

        # 5. Annotate B1 result
        if detection_result:
            annotated_ok = draw_annotated_image(
                snapshot_f1,
                detection_result,
                b1_slots,
                annotated_path,
                title="B1 — YOLO11n",
            )
        if detection_result_f2 and snapshot_f2:
            ann_f2 = MEDIA_DIR / "unity_detection_annotated_f1.jpg"
            draw_annotated_image(
                snapshot_f2,
                detection_result_f2,
                f1_slots,
                ann_f2,
                title="F1 — YOLO11n",
            )

        # 6. All camera snapshots
        snapped_count = test_all_virtual_cameras(client)

    # ── 7. Summary ────────────────────────────────────────────────────────── #
    section("7. Summary Report")
    print(f"  AI Service:    {'OK' if health_ok else 'FAIL'}")
    print(
        f"  Unity frames:  F1={'OK' if snapshot_f1 else 'NO DATA'}, "
        f"F2={'OK' if snapshot_f2 else 'NO DATA'}"
    )
    print(f"  Snapshots:     {snapped_count}/{len(VIRTUAL_CAMERAS)} cameras")

    for label, result, json_file in [
        ("B1 (F1 cam)", detection_result, "unity_detection_result_b1.json"),
        ("F1 (F2 cam)", detection_result_f2, "unity_detection_result_f1.json"),
    ]:
        if result:
            total = result.get("totalSlots", result.get("total_slots", 0))
            avail = result.get("totalAvailable", result.get("total_available", 0))
            occup = result.get("totalOccupied", result.get("total_occupied", 0))
            method = result.get("detectionMethod", result.get("detection_method", "?"))
            ms = result.get("processingTimeMs", result.get("processing_time_ms", 0))
            print(f"  {label}: {total} slots — {occup} occupied, {avail} available")
            print(f"           method={method}  time={ms:.0f}ms")
            print(f"           JSON → {MEDIA_DIR / json_file}")
        else:
            print(f"  {label}: SKIPPED / NO DATA")

    print(f"  Annotated B1: {annotated_path if annotated_ok else 'NOT CREATED'}")
    print()
    print(f"  Total: {_pass_count} passed, {_fail_count} failed")
    print("=" * 64)

    return 0 if _fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
