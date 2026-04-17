/**
 * Map slot code → virtual camera id that best covers that slot.
 *
 * Layout reference (Unity VirtualCameraManager + ParkingLotGenerator):
 * - V1-01..18, V1-37..54 (south rows)  → virtual-zone-south
 * - V1-19..36, V1-55..72 (north rows)  → virtual-zone-north
 * - G-01..05              (garage row) → virtual-zone-garage
 * - V2-*                  (motorbike)  → virtual-f1-overview (no zone cam)
 * - unknown                            → virtual-f1-overview
 */
export function getCameraForSlot(slotCode: string | null | undefined): string {
  if (!slotCode) return "virtual-f1-overview";
  const code = slotCode.trim().toUpperCase();

  if (code.startsWith("G-")) return "virtual-zone-garage";
  if (code.startsWith("V2-")) return "virtual-f1-overview";

  if (code.startsWith("V1-")) {
    const num = parseInt(code.slice(3), 10);
    if (!Number.isFinite(num)) return "virtual-f1-overview";
    const isSouth = (num >= 1 && num <= 18) || (num >= 37 && num <= 54);
    return isSouth ? "virtual-zone-south" : "virtual-zone-north";
  }

  return "virtual-f1-overview";
}

/** Build the AI service stream URL for a camera id. */
export function getCameraStreamUrl(cameraId: string, fps = 5): string {
  return `/ai/cameras/stream?camera_id=${encodeURIComponent(cameraId)}&fps=${fps}`;
}
