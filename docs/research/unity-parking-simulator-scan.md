# Research Report: Unity Parking Simulator — Full Project Scan

**Task:** Unity Project Scan | **Date:** 2026-04-01 | **Type:** Codebase

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
> 1. **Project gần như TRỐNG HOÀN TOÀN** — chỉ là Unity 2022.3 URP template mặc định, chưa có bất kỳ game code nào.
> 2. **Không có Scripts** (ngoài 2 file template TutorialInfo của Unity), không có Prefabs, không có Materials, không có Resources.
> 3. **Mọi feature cần build từ zero**: API integration, waypoint navigation, mock mode, multi-floor, car controller — tất cả chưa tồn tại.

---

## 2. Cấu Trúc Thư Mục

### 2.1 Root Structure

```
ParkingSimulatorUnity/
├── Assets/
│   ├── Scenes/
│   │   └── SampleScene.unity          ← Scene mặc định (Camera + Light + Volume)
│   ├── Settings/
│   │   ├── SampleSceneProfile.asset
│   │   ├── URP-Balanced.asset + Renderer
│   │   ├── URP-HighFidelity.asset + Renderer
│   │   └── URP-Performant.asset + Renderer
│   ├── TutorialInfo/
│   │   ├── Icons/
│   │   ├── Layout.wlt
│   │   └── Scripts/
│   │       ├── Readme.cs              ← Unity template ScriptableObject
│   │       └── Editor/
│   │           └── ReadmeEditor.cs    ← Unity template Custom Editor
│   ├── Readme.asset
│   └── UniversalRenderPipelineGlobalSettings.asset
├── Packages/
│   ├── manifest.json
│   └── packages-lock.json
├── ProjectSettings/                   ← 25 standard Unity settings files
├── UserSettings/
├── Library/   (gitignored)
├── Temp/      (gitignored)
├── Logs/      (gitignored)
├── ParkingSimulatorUnity.sln
├── Assembly-CSharp.csproj
├── Assembly-CSharp-Editor.csproj
└── .vsconfig
```

### 2.2 QUAN TRỌNG — Thư mục KHÔNG TỒN TẠI

| Thư mục mong đợi      | Trạng thái     | Ý nghĩa                              |
|------------------------|----------------|---------------------------------------|
| `Assets/Scripts/`      | ❌ KHÔNG CÓ    | Không có game logic code nào          |
| `Assets/Prefabs/`      | ❌ KHÔNG CÓ    | Không có prefab nào (xe, bãi đỗ...)   |
| `Assets/Materials/`    | ❌ KHÔNG CÓ    | Không có materials custom             |
| `Assets/Resources/`    | ❌ KHÔNG CÓ    | Không có runtime-loaded assets        |
| `Assets/Models/`       | ❌ KHÔNG CÓ    | Không có 3D models                    |
| `Assets/Textures/`     | ❌ KHÔNG CÓ    | Không có textures                     |
| `Assets/UI/`           | ❌ KHÔNG CÓ    | Không có UI elements                  |
| `Assets/Animations/`   | ❌ KHÔNG CÓ    | Không có animations                   |

---

## 3. Scripts Analysis

### 3.1 Tổng số scripts: **2** (cả 2 là Unity template, không phải code custom)

#### 3.1.1 `Readme.cs`

| Thuộc tính    | Giá trị                    |
|---------------|----------------------------|
| Class name    | `Readme`                   |
| Base class    | `ScriptableObject`         |
| Namespace     | None (global)              |
| Mục đích      | Unity template Welcome tab |
| Public fields | `icon`, `title`, `sections`, `loadedLayout` |
| API calls     | Không                      |
| WebSocket     | Không                      |
| Dependencies  | UnityEngine                |

#### 3.1.2 `ReadmeEditor.cs`

| Thuộc tính    | Giá trị                    |
|---------------|----------------------------|
| Class name    | `ReadmeEditor`             |
| Base class    | `Editor`                   |
| Namespace     | None (global)              |
| Mục đích      | Custom inspector cho Readme |
| Attributes    | `[CustomEditor]`, `[InitializeOnLoad]` |
| API calls     | Không                      |
| WebSocket     | Không                      |
| Dependencies  | UnityEditor, System.IO, System.Reflection |

**Kết luận**: Cả 2 files là standard Unity URP template files. KHÔNG phải code parking simulator.

---

## 4. Scene Files

### 4.1 `SampleScene.unity` (10.7 KB)

**Hierarchy (3 GameObjects):**

| GameObject         | Components                                    | Transform Position   |
|-------------------|-----------------------------------------------|---------------------|
| Main Camera       | Camera, AudioListener, UniversalAdditionalCameraData | (0, 1, -10)       |
| Directional Light | Light (type=Directional, intensity=2, shadows=on), UniversalAdditionalLightData | (0, 3, 0), rot=(50°, -30°, 0°) |
| Global Volume     | Volume (isGlobal=true, profile=SampleSceneProfile) | (0, 0, 0)         |

**Kết luận**: Scene mặc định của URP template. Không có terrain, parking lot model, xe, UI, hay bất kỳ game object nào custom.

---

## 5. Package Dependencies (manifest.json)

### 5.1 Custom Packages (user-added)

| Package                                   | Version | Mục đích                    |
|------------------------------------------|---------|-----------------------------|
| `com.unity.render-pipelines.universal`   | 14.0.12 | URP render pipeline         |
| `com.unity.textmeshpro`                 | 3.0.7   | Text rendering              |
| `com.unity.collab-proxy`                | 2.12.4  | Unity Collaborate           |
| `com.unity.ide.rider`                   | 3.0.36  | JetBrains Rider integration |
| `com.unity.ide.visualstudio`            | 2.0.22  | VS integration              |
| `com.unity.ide.vscode`                  | 1.2.5   | VSCode integration          |
| `com.unity.test-framework`              | 1.1.33  | Unit testing                |
| `com.unity.timeline`                    | 1.7.7   | Timeline animations         |
| `com.unity.ugui`                        | 1.0.0   | Unity UI                    |
| `com.unity.visualscripting`             | 1.9.4   | Visual scripting            |

### 5.2 Built-in Modules (35 total)

Standard Unity modules including: `ai`, `animation`, `audio`, `physics`, `vehicles`, `unitywebrequest`, `jsonserialize`, `video`, `vr`, `xr`, etc.

### 5.3 THIẾU — Packages cần thêm cho Parking Simulator

| Package cần                                    | Lý do                                    |
|-----------------------------------------------|------------------------------------------|
| `com.unity.inputsystem`                       | New Input System cho điều khiển xe       |
| `com.unity.cinemachine`                       | Camera follow/orbit cho xe               |
| `com.unity.probuilder` (optional)             | Prototype bãi đỗ nhanh                  |
| `com.unity.ai.navigation`                     | NavMesh cho AI waypoint navigation       |
| NativeWebSocket / WebSocketSharp (NuGet)      | WebSocket connection tới realtime-service |

---

## 6. Project Settings

### 6.1 Unity Version

```
Unity 2022.3.62f3 (LTS)
```

### 6.2 Player Settings

| Setting              | Value                  |
|---------------------|------------------------|
| Product Name        | ParkingSimulatorUnity  |
| Company Name        | DefaultCompany         |
| Color Space         | Linear (m_ActiveColorSpace=1) |
| Default Resolution  | 1024 × 768            |
| Web Resolution      | 960 × 600             |
| Orientation         | Auto Rotation          |
| Target Device       | 2 (Desktop)            |
| Multithreaded Rendering | On                 |

### 6.3 Render Pipeline

- **Type**: Universal Render Pipeline (URP) 14.0.12
- **Quality Levels**: 3 tiers (Balanced, HighFidelity, Performant)
- **Post Processing**: Enabled on Main Camera

### 6.4 Assembly Definitions

**Không có** `.asmdef` files custom. Chỉ có default Assembly-CSharp.

### 6.5 Prefabs

**Không có** prefab nào trong project.

---

## 7. So sánh Plan vs Thực tế

### 7.1 Feature Status — TOÀN BỘ CHƯA CÓ

| Feature Expected                | Trạng thái    | Chi tiết                                     |
|--------------------------------|---------------|----------------------------------------------|
| Car Controller (movement)      | ❌ CHƯA CÓ   | Không có script điều khiển xe                |
| Parking Lot 3D Environment     | ❌ CHƯA CÓ   | Scene trống, không có model bãi đỗ           |
| Waypoint Navigation System     | ❌ CHƯA CÓ   | Không có NavMesh, waypoint, pathfinding      |
| Multi-floor Support            | ❌ CHƯA CÓ   | Không có floor switching / elevator logic     |
| API Integration                | ❌ CHƯA CÓ   | Không có HTTP client, endpoint calls          |
| WebSocket Connection           | ❌ CHƯA CÓ   | Không có WS library hay connection code       |
| Mock Mode                      | ❌ CHƯA CÓ   | Không có mock data hay offline mode           |
| Slot Visualization             | ❌ CHƯA CÓ   | Không có slot objects, colors, indicators     |
| UI (HUD, menus, status)        | ❌ CHƯA CÓ   | Không có Canvas, buttons, text elements       |
| Camera System                  | ❌ CHƯA CÓ   | Chỉ có default static camera                 |
| Vehicle Models                 | ❌ CHƯA CÓ   | Không có 3D car models/prefabs               |
| License Plate Display          | ❌ CHƯA CÓ   | Không có text rendering trên xe              |
| Parking Sensor Simulation      | ❌ CHƯA CÓ   | Không có sensor/trigger logic                |
| Barrier Gate Animation         | ❌ CHƯA CÓ   | Không có barrier model hay animator          |
| Minimap                        | ❌ CHƯA CÓ   | Không có minimap camera/UI                   |
| Sound Effects                  | ❌ CHƯA CÓ   | Không có audio clips hay manager             |

### 7.2 Scripts Cần Implement (Ước tính từ plan)

Dựa trên `PARKING_SYSTEM_PLAN.md` (ParkSmart v4.0) và frontend MapPage.tsx flow:

```
Assets/Scripts/
├── Core/
│   ├── GameManager.cs              ← Singleton, game state management
│   ├── ApiManager.cs               ← HTTP calls to backend (UnityWebRequest)
│   ├── WebSocketManager.cs         ← WS connection to realtime-service-go :8006
│   ├── MockDataProvider.cs         ← Mock mode for offline/demo
│   └── ConfigManager.cs            ← ENV/config loading (API base URL, etc.)
│
├── Vehicle/
│   ├── CarController.cs            ← WASD/Arrow movement, physics-based
│   ├── CarSetup.cs                 ← Vehicle configuration (color, plate, type)
│   └── LicensePlateDisplay.cs      ← TextMeshPro on car body
│
├── Parking/
│   ├── ParkingLotManager.cs        ← Load lot data, manage zones/floors
│   ├── ParkingSlot.cs              ← Individual slot (status, color, trigger)
│   ├── ParkingZone.cs              ← Zone grouping slots
│   ├── FloorManager.cs             ← Multi-floor switching (elevator/ramp)
│   └── BarrierGate.cs              ← Entry/exit gate animation + logic
│
├── Navigation/
│   ├── WaypointSystem.cs           ← Waypoint graph definition
│   ├── NavigationManager.cs        ← Pathfinding (A* or NavMesh)
│   ├── NavigationArrow.cs          ← 3D directional arrow indicator
│   └── MinimapController.cs        ← Minimap camera + UI overlay
│
├── Camera/
│   ├── CameraController.cs         ← Follow cam / orbit cam / top-down
│   └── CameraSwitcher.cs           ← Switch between camera modes
│
├── UI/
│   ├── HUDManager.cs               ← Speed, slot info, navigation hints
│   ├── BookingInfoPanel.cs         ← Show current booking details
│   ├── SlotStatusPanel.cs          ← Available/occupied overlay
│   └── MenuManager.cs              ← Main menu, settings, quit
│
└── Sensors/
    ├── ParkingSensor.cs            ← Proximity detection (raycast/trigger)
    └── CheckInOutTrigger.cs        ← Gate trigger zones
```

---

## 8. Code Quality Assessment

**N/A** — Không có code custom nào để đánh giá. Hai files template:
- ✅ Naming conventions OK (PascalCase classes, camelCase fields)
- ⚠️ ReadmeEditor.cs: sử dụng reflection (`GetMethod`, `Invoke`) — anti-pattern nhưng là code Unity-generated, không phải custom code

---

## 9. API Integration Requirements

Dựa trên backend hiện tại (PARKING_SYSTEM_PLAN.md):

### 9.1 REST API Endpoints cần gọi

| Endpoint                           | Method | Mục đích                        |
|-----------------------------------|--------|----------------------------------|
| `/parking/lots/`                  | GET    | Lấy danh sách bãi đỗ           |
| `/parking/floors/?lot_id=X`      | GET    | Lấy tầng của bãi               |
| `/parking/zones/?floor_id=X`     | GET    | Lấy zones theo tầng            |
| `/parking/slots/?zone_id=X`      | GET    | Lấy slots theo zone            |
| `/parking/slots/{id}/`           | PATCH  | Cập nhật slot status            |
| `/booking/bookings/current-parking/` | GET | Lấy booking hiện tại           |
| `/booking/bookings/{id}/check-in/`   | POST | Check-in                       |
| `/booking/bookings/{id}/check-out/`  | POST | Check-out                      |

### 9.2 Auth Headers cần

```
X-Gateway-Secret: gateway-internal-secret-key
X-User-ID: {uuid}
X-User-Email: {email}
```

### 9.3 WebSocket

- **URL**: `ws://localhost:8006/ws` (realtime-service-go)
- Events: `slot_status_changed`, `booking_updated`, `vehicle_entered`, `vehicle_exited`

### 9.4 API Base URL (Gateway)

```
http://localhost:8000 (dev)
https://api.ghepdoicaulong.shop (prod)
```

---

## 10. ⚠️ Gotchas & Known Issues

- [ ] **[BLOCKER]** Project hoàn toàn trống — cần build mọi thứ từ zero
- [ ] **[BLOCKER]** Không có 3D models (car, parking lot, barriers) — cần tạo hoặc import asset store
- [ ] **[WARNING]** `com.unity.modules.vehicles` đã include nhưng Vehicle module bị legacy — nên dùng custom physics-based controller
- [ ] **[WARNING]** Không có `com.unity.inputsystem` — hiện dùng old Input Manager. Nên thêm New Input System
- [ ] **[WARNING]** Không có `com.unity.ai.navigation` package — cần add cho NavMesh-based waypoint
- [ ] **[NOTE]** Unity 2022.3.62 LTS là stable. URP 14 là đúng version cho 2022.3
- [ ] **[NOTE]** Linear color space đã set — đúng cho URP
- [ ] **[NOTE]** `.gitignore` đã có entries cho Library/, Temp/, Logs/, obj/, Build/

---

## 11. Nguồn

| # | Source                          | Mô tả                              |
|---|--------------------------------|-------------------------------------|
| 1 | Project filesystem scan        | Direct file listing & reading       |
| 2 | `PARKING_SYSTEM_PLAN.md`       | ParkSmart v4.0 system plan          |
| 3 | `Packages/manifest.json`       | Unity package dependencies          |
| 4 | `ProjectSettings/`             | Unity project configuration         |
| 5 | `Assets/Scenes/SampleScene.unity` | Scene hierarchy analysis         |
| 6 | Backend codebase               | API endpoints & data models         |

---

## 12. Kết Luận

**Unity project `ParkingSimulatorUnity` là một URP template mặc định hoàn toàn, chưa có bất kỳ implementation nào.**

Ước lượng effort:
- **Script System**: ~20-25 scripts cần viết
- **3D Assets**: Cần car models, parking lot model, barriers, signs, road markings
- **UI**: HUD, menus, booking info panels
- **Integration**: API client, WebSocket, mock mode
- **Navigation**: Waypoint graph, pathfinding, directional indicators

Project hiện tại = **0% completion** so với requirements cho một parking simulator.
