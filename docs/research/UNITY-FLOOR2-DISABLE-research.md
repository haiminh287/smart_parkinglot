# Research Report: Disable Tầng 2 (Floor 2) trong Unity Parking Simulator

**Task:** UNITY-FLOOR2-DISABLE | **Date:** 2026-04-09 | **Type:** Codebase

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. **Master switch**: `ParkingLotGenerator.numberOfFloors = 2` (line 10) → đổi thành `1` sẽ loại bỏ toàn bộ Floor 2 geometry, slots (A-xx, B-xx, C-xx), ramp, ceiling
> 2. **Camera enum** cần cleanup: `ParkingCameraController.CameraMode.FloorF2` (line 7) phải skip/xóa, cùng keybinding `Alpha3` và HUD label `3:F2`
> 3. **Không cần sửa** FloorVisibilityManager hay DashboardUI — chúng đọc `numberOfFloors` tự động
> 4. Backend DB xác nhận: Tầng 2 (level=2) chỉ có Zone C + Zone D (cả hai = Motorbike), không có Car zone

---

## 2. Phân Tích Codebase Hiện Tại

### 2.1 Files/Modules Liên Quan

| File                                               | Mục đích                           | Relevance  | Cần sửa?                                         |
| -------------------------------------------------- | ---------------------------------- | ---------- | ------------------------------------------------ |
| `Assets/Scripts/Parking/ParkingLotGenerator.cs`    | Tạo geometry tất cả floors + slots | **HIGH**   | **YES** — đổi `numberOfFloors`                   |
| `Assets/Scripts/Camera/ParkingCameraController.cs` | Camera mode switching + HUD        | **HIGH**   | **YES** — xóa/skip FloorF2                       |
| `Assets/Scripts/API/MockDataProvider.cs`           | Mock data cho floors/slots         | **MEDIUM** | **YES** — xóa Floor 2 mock data                  |
| `Assets/Scripts/API/MockIds.cs`                    | Constant IDs cho mock entities     | **MEDIUM** | Optional — có thể giữ unused                     |
| `Assets/Scripts/Core/FloorVisibilityManager.cs`    | Floor show/hide toggle             | **LOW**    | **NO** — adaptively reads `numberOfFloors`       |
| `Assets/Scripts/UI/DashboardUI.cs`                 | Dashboard floor buttons            | **LOW**    | **NO** — adaptively reads `GetFloorCount()`      |
| `Assets/Editor/SceneBootstrapper.cs`               | Scene wiring                       | **LOW**    | **NO** — không hardcode floor count              |
| `Assets/Scripts/API/ApiService.cs`                 | API calls + mock fallback          | **LOW**    | **NO** — floor data fetched from API/mock        |
| `Assets/Scripts/Core/ParkingManager.cs`            | Orchestration + slot mapping       | **LOW**    | **NO** — maps by slot code, unused codes ignored |

### 2.2 Architecture: How Floors Are Created

**ParkingLotGenerator.Generate()** (line 68-213):

```csharp
// Source: Assets/Scripts/Parking/ParkingLotGenerator.cs:10
public int numberOfFloors = 2;  // ← MASTER SWITCH

// Source: line 71-72
for (int level = 0; level < numberOfFloors; level++)
{
    float yBase = level * floorHeight;
    var floorParent = new GameObject($"Floor_{level + 1}");
    // Creates: FloorPlatform, Pillars, Lane waypoints, Painted slots, Garage slots, Motorbike slots
}
```

**Floor 0 (level=0)** generates:

- Slot codes: `V1-01..V1-72` (4 rows × 18 car slots) + `V2-01..V2-20` (motorbike) + `G-01..G-10` (garage)
- Extra rows 3 & 4 only on level 0 (lines 140-170)

**Floor 1 (level=1)** generates:

- Slot codes: `A-01..A-18` (row 1) + `B-01..B-18` (row 2) + `C-01..C-20` (motorbike)
- No extra rows 3 & 4

**Ramp** (lines 206-210): Only created when `numberOfFloors > 1`

**Environment** (line 550): Perimeter walls height = `numberOfFloors * floorHeight`, ceiling slabs between floors

### 2.3 Camera Mode System

```csharp
// Source: Assets/Scripts/Camera/ParkingCameraController.cs:7
public enum CameraMode { Overview, FloorB1, FloorF2, GateEntry, GateExit }

// Keybindings (line 116-118):
if (Input.GetKeyDown(KeyCode.Alpha1)) SetMode(CameraMode.Overview);
if (Input.GetKeyDown(KeyCode.Alpha2)) SetMode(CameraMode.FloorB1);
if (Input.GetKeyDown(KeyCode.Alpha3)) SetMode(CameraMode.FloorF2);  // ← This triggers F2 view

// Camera position for FloorF2 (line 170-173):
case CameraMode.FloorF2:
    targetPosition = new Vector3(targetPosition.x, 3.5f, targetPosition.z);  // y=3.5 = floorHeight
    distance = 30f;
    verticalAngle = 50f;
    break;

// HUD labels (line 198-200):
string[] labels = { "1:Overview", "2:B1", "3:F2", "G:Gate", "TAB:Cycle" };
CameraMode[] modes = { CameraMode.Overview, CameraMode.FloorB1, CameraMode.FloorF2, ... };

// CycleMode (line 195): iterates ALL enum values including FloorF2
```

### 2.4 Floor Visibility UI

```csharp
// Source: Assets/Scripts/UI/DashboardUI.cs:370-378
private void DrawFloorControls()
{
    int totalFloors = ... GetFloorCount() ...;  // reads generator.numberOfFloors
    for (int i = 0; i < totalFloors; i++)
    {
        // Creates F1, F2 buttons dynamically
        if (GUILayout.Button(label)) floorManager.ShowFloor(i);
    }
}
```

**FloorVisibilityManager** (line 19): `totalFloors = generator.numberOfFloors;` — auto-adapts.

### 2.5 Mock Data for Floor 2

```csharp
// Source: Assets/Scripts/API/MockDataProvider.cs:142-169
new FloorData
{
    Id = MockIds.FLOOR_2,       // "00000000-0000-0000-0001-000000000002"
    Level = 2, Name = "Floor 2",
    Zones = new List<ZoneData>
    {
        // Car Painted F2 (ZONE_CAR_PAINTED_F2)
        // Car Garage F2 (ZONE_CAR_GARAGE_F2)
        // Motorbike F2 (ZONE_MOTO_F2)
    }
}

// Mock SLOTS for Floor 1 (level=1) — lines 49-93:
// A-01..A-18, B-01..B-18 (ZONE_CAR_PAINTED_F2), C-01..C-20 (ZONE_MOTO_F2)
```

### 2.6 Backend DB Reality (from seed_user_test_data.py)

```python
# Source: backend-microservices/seed_user_test_data.py:46-63
"parksmart": {
    "floor_tang2_id": "30098e7d...",   "floor_tang2_level": 2,
    "floor_tang3_id": "610fbad6...",   "floor_tang3_level": 3,
}

ZONES = {
    "C": {"type": "Motorbike", "floor_level": 2},  # Tầng 2 — Motorbike ONLY
    "D": {"type": "Motorbike", "floor_level": 2},  # Tầng 2 — Motorbike ONLY
    "E": {"type": "Car",       "floor_level": 3},  # Tầng 3 — Car zone
}
```

**Xác nhận: Tầng 2 trong real backend = chỉ Motorbike (Zone C + D). Không có Car zone.**

### 2.7 Potential Conflicts

- **SlotOccupancyDetector**: Finds all slots via `ParkingLotGenerator.slotRegistry` — fewer slots if Floor 2 removed, no breakage
- **VehicleQueue**: Uses `FindObjectOfType<ParkingLotGenerator>()` — works regardless of floor count
- **ParkingManager.MapApiDataToSlots()**: Maps by slot code — F2 slots from API just won't match, logs warning but doesn't crash
- **MockDataProvider.GenerateMockSlots()**: Still generates A/B/C slots — they won't match any slot in registry, silently ignored
- **VirtualCameraManager**: Camera IDs (f1-overview, f2-overview) — f2-overview won't have geometry to capture

---

## 3. So Sánh Phương Án

| Tiêu chí          | Option A: numberOfFloors=1            | Option B: Hide Floor_2 at runtime          | Option C: Filter floors by vehicleType |
| ----------------- | ------------------------------------- | ------------------------------------------ | -------------------------------------- |
| Effort            | **Minimal** — 1 line + camera cleanup | Medium — keep generation, SetActive(false) | High — add filtering logic             |
| Reversible        | Yes — change back to 2                | Yes — toggle visibility                    | Yes — remove filter                    |
| Performance       | Better — fewer GameObjects            | Same — objects exist but hidden            | Same                                   |
| Side effects      | No ramp, no ceiling slab, fewer slots | Ramp exists but goes to hidden floor       | Complex logic, risk of bugs            |
| Mock data cleanup | Optional                              | Not needed                                 | Needs zone type filtering              |

**Note**: Option A là đơn giản nhất cho mục đích "focus Car testing".

---

## 4. ⚠️ Gotchas & Known Issues

- [x] **[NOTE]** Mock data mismatch: `MockDataProvider` có Car zones cho F2 (Painted F2, Garage F2) nhưng real backend chỉ có Motorbike zones. Mock data sẽ tạo phantom slots (A-xx, B-xx, C-xx) mà không match geometry khi `numberOfFloors=1`
- [x] **[NOTE]** Camera `f2-overview` (VirtualCameraManager): Nếu AI detection dùng camera này, sẽ capture empty space
- [x] **[WARNING]** `ParkingCameraController.CycleMode()` dùng `System.Enum.GetValues` — nếu FloorF2 vẫn trong enum nhưng Floor 2 không tồn tại, camera sẽ target y=3.5 vào không gian trống
- [x] **[NOTE]** Ramp sẽ không tạo khi `numberOfFloors=1` (điều kiện line 206: `if (numberOfFloors > 1)`) — OK, mong muốn

---

## 5. Checklist cho Implementer

### Bắt buộc sửa

- [ ] **`Assets/Scripts/Parking/ParkingLotGenerator.cs:10`**
  - Đổi `public int numberOfFloors = 2;` → `public int numberOfFloors = 1;`

- [ ] **`Assets/Scripts/Camera/ParkingCameraController.cs`**
  - Line 7: Remove `FloorF2` from enum hoặc skip nó
  - Line 118: Remove/comment `if (Input.GetKeyDown(KeyCode.Alpha3)) SetMode(CameraMode.FloorF2);`
  - Line 170-173: Remove case `CameraMode.FloorF2`
  - Line 198-200: Remove `"3:F2"` from HUD labels, remove `CameraMode.FloorF2` from modes array

### Nên sửa (clean mock data)

- [ ] **`Assets/Scripts/API/MockDataProvider.cs`**
  - Lines 49-93: Remove A-xx, B-xx, C-xx slot generation (Floor 1 slots)
  - Lines 142-169: Remove second `FloorData` entry (Floor 2)
  - HOẶC: giữ nguyên — mock slots won't match, silently ignored

### Tùy chọn

- [ ] **`Assets/Scripts/API/MockIds.cs`**: Remove `FLOOR_2`, `ZONE_*_F2` constants nếu mock data đã xóa
- [ ] **VirtualCameraManager**: Disable `f2-overview` camera nếu đang gửi frames lên AI

### Không cần sửa

- FloorVisibilityManager — auto adapts
- DashboardUI — auto adapts (floor buttons loop `numberOfFloors`)
- ParkingManager — slot mapping ignores unmatched codes
- SceneBootstrapper — no floor count hardcode
- ApiService — floor data from API/mock, UI/manager reads whatever comes back

---

## 6. Nguồn

| #   | File                                               | Mô tả                     | Lines                        |
| --- | -------------------------------------------------- | ------------------------- | ---------------------------- |
| 1   | `Assets/Scripts/Parking/ParkingLotGenerator.cs`    | Floor generation master   | 10, 68-213                   |
| 2   | `Assets/Scripts/Camera/ParkingCameraController.cs` | Camera modes + HUD        | 7, 116-118, 165-173, 198-200 |
| 3   | `Assets/Scripts/API/MockDataProvider.cs`           | Mock floor/slot data      | 49-93, 110-169               |
| 4   | `Assets/Scripts/API/MockIds.cs`                    | Floor/zone IDs            | 9-19                         |
| 5   | `Assets/Scripts/Core/FloorVisibilityManager.cs`    | Floor visibility control  | 7-85                         |
| 6   | `Assets/Scripts/UI/DashboardUI.cs`                 | Dashboard floor UI        | 370-383                      |
| 7   | `Assets/Scripts/Core/ParkingManager.cs`            | Slot mapping orchestrator | 130-145, 486-505             |
| 8   | `Assets/Editor/SceneBootstrapper.cs`               | Scene wiring              | 129-237                      |
| 9   | `backend-microservices/seed_user_test_data.py`     | Backend DB seed           | 46-68                        |
