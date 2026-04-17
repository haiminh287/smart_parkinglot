# Check-in → Verify Slot flow (Unity + FE)

**Ngày:** 2026-04-17
**Scope:** Tách flow check-in và verify-slot thành 2 bước user-controlled; đơn giản hoá UI web.

## Mục tiêu

1. Sau khi check-in thành công (ANPR pass), xe dừng trước ô đỗ — không tự động vào.
2. User ấn **Verify Slot** trên ESP32 Simulator → xe mới di chuyển vào ô.
3. Khi xe đã đậu, giao diện web (CamerasPage) hiển thị camera quan sát được ô đỗ của user.
4. Xoá CheckInOutPage khỏi FE — toàn bộ check-in/out đi qua Unity simulator (hoặc gate ESP32 thật sau này).

## Thay đổi chi tiết

### A. Unity — `GateFlowController.cs`

- `CheckInWithANPR()` hiện gọi `ParkingManager.Instance.OpenSlotBarrier(slotCode)` ngay sau ANPR pass. Xoá lời gọi này.
- Flow mới: ANPR pass → xe ở state `Navigating` → tự chạy đến `SlotEntrance` của ô đỗ → state đổi thành `IsAtSlotEntrance = true` → dừng.
- Xoá hoặc sửa comment/log giải thích "waiting for verify-slot".
- `VerifySlotFlow()` giữ nguyên: khi user ấn Verify Slot button → API call → `OpenSlotBarrier()` → `ProceedIntoSlot()` → state `Parking`.

**File touch:** `ParkingSimulatorUnity/Assets/Scripts/Core/Flow/GateFlowController.cs`

### B. Unity — `VirtualCameraManager.cs`

Thêm camera **`virtual-zone-garage`** phủ khu G-01..G-05:

```csharp
new VirtualCameraConfig
{
    cameraId = "virtual-zone-garage",
    displayName = "Garage Zone",
    position = new Vector3(0, 8, -32),    // before G row (Z≈-28.5)
    rotation = new Vector3(30, 0, 0),
    fieldOfView = 55f,
    ...
}
```

**File touch:** `ParkingSimulatorUnity/Assets/Scripts/Camera/VirtualCameraManager.cs`

### C. FE — Xoá CheckInOutPage

- Xoá file `spotlove-ai/src/pages/CheckInOutPage.tsx`.
- Xoá route `/check-in-out` (hoặc tương tự) trong router.
- Xoá sidebar link.
- Xoá import/service không còn dùng (nếu có — check references).

### D. FE — Slot → camera mapping

Thêm helper `getCameraForSlot(slotCode: string): string` trong `spotlove-ai/src/lib/slotCamera.ts`:

```ts
V1-01..18, V1-37..54    → virtual-zone-south
V1-19..36, V1-55..72    → virtual-zone-north
G-*                     → virtual-zone-garage
V2-*                    → virtual-f1-overview
default                 → virtual-f1-overview
```

Sử dụng trong `CamerasPage.tsx`:

- Fetch bookings của user đang login với `check_in_status = "checked_in"`.
- Với mỗi booking → render 1 card camera (slot code → camera id → `<img src="/ai/cameras/stream?camera_id=...">`).
- Section label: "🚗 Ô đỗ của bạn" đặt lên trên section "Monitoring Cameras" cũ.
- Nếu không có booking checked_in → ẩn section.

**Files touch:**
- `spotlove-ai/src/lib/slotCamera.ts` (new)
- `spotlove-ai/src/pages/CamerasPage.tsx`

## Ngoài scope

- Không thêm verify-slot button trên FE (chỉ Unity simulator).
- Không đổi backend API (`/ai/parking/esp32/verify-slot` giữ nguyên).
- Không refactor flow check-in/out khác ngoài 2 mục trên.

## Testing

- Unity Play mode: spawn xe → check-in → xe dừng trước G-01 (không tự vào) → ấn Verify Slot → barrier mở → xe vào ô. PASS.
- FE: login user có booking G-01 checked_in → CamerasPage hiển thị card camera `virtual-zone-garage`.
- FE: verify `/check-in-out` trả 404 hoặc redirect (route đã xoá).
