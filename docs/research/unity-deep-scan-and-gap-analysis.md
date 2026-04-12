# Research Report: Unity Project Deep Scan + BAO_CAO_PLAN Gap Analysis

**Task:** Unity deep scan + cross-reference BAO_CAO_PLAN.md | **Date:** 2026-04-07 | **Type:** Codebase + Gap Analysis

---

## 1. TL;DR — Đọc trong 60 giây

> 1. **Unity project là ứng dụng 3D Parking Simulator hoàn chỉnh** — 30+ C# scripts, 8 assembly definitions, 6 virtual cameras, procedural lot generation, vehicle state machine pathfinding, API/WebSocket integration, IMGUI overlay panels, 6 test files.
> 2. **Unity KHÔNG có mục riêng trong Ch2 (Cơ sở lý thuyết)** — chỉ được nhắc 3 lần miệng trong mục 2.6 (Go) dưới dạng "Unity simulator". Đây là GAP LỚN NHẤT.
> 3. **Ch3 cũng KHÔNG có mục kết quả nào cho Parking Simulator** — Ch3.5 có 4 kết quả (Booking, Chatbot, Map, IoT Check-in) nhưng thiếu mô phỏng 3D.
> 4. **Testing stack thiếu mục riêng trong Ch2** — NUnit (Unity), Vitest, Playwright, pytest đều tồn tại nhưng không có section "2.x Kiểm thử phần mềm".
> 5. **Cloudflare Tunnel thiếu hoàn toàn trong Ch2** — dùng thực tế nhưng không được giải thích lý thuyết.

---

## 2. Unity Technology Inventory — Đầy đủ

### 2.1 Engine & Language

| Component           | Value                                                                                        |
| ------------------- | -------------------------------------------------------------------------------------------- |
| **Unity version**   | 2022.3.62f3 (LTS)                                                                            |
| **Revision**        | 96770f904ca7                                                                                 |
| **Language**        | C# (.NET)                                                                                    |
| **Render Pipeline** | **URP 14.0.12** (Universal Render Pipeline) — 3 profiles: Balanced, HighFidelity, Performant |
| **UI System**       | Hybrid: **IMGUI** (OnGUI) for overlay panels + **TextMeshPro 3.0.7** for 3D world text       |
| **Physics**         | Unity Physics 3D (`com.unity.modules.physics`) — OverlapSphere detection for vehicles        |

### 2.2 Unity Packages (manifest.json)

| Package                                | Version | Vai trò trong ParkSmart                                                         |
| -------------------------------------- | ------- | ------------------------------------------------------------------------------- |
| `com.endel.nativewebsocket`            | git#upm | WebSocket client — real-time slot updates từ Realtime Service (:8006)           |
| `com.unity.nuget.newtonsoft-json`      | 3.2.1   | JSON serialization — API request/response, `[JsonProperty]` annotations         |
| `com.unity.render-pipelines.universal` | 14.0.12 | URP render pipeline — `_BaseColor`, `_Surface`, `_Smoothness` shader properties |
| `com.unity.test-framework`             | 1.1.33  | NUnit test runner — EditMode + PlayMode tests                                   |
| `com.unity.textmeshpro`                | 3.0.7   | Rich text rendering — Vietnamese license plates, slot labels                    |
| `com.unity.timeline`                   | 1.7.7   | Timeline animation (available, chưa dùng active)                                |
| `com.unity.ugui`                       | 1.0.0   | Unity UI system (UGUI) — base cho TMP                                           |
| `com.unity.visualscripting`            | 1.9.4   | Visual scripting (available, không dùng — code-only approach)                   |
| `com.unity.collab-proxy`               | 2.12.4  | Version control integration                                                     |
| `com.unity.ide.rider`                  | 3.0.36  | Rider IDE support                                                               |
| `com.unity.ide.visualstudio`           | 2.0.22  | VS support                                                                      |
| `com.unity.ide.vscode`                 | 1.2.5   | VS Code support                                                                 |
| `com.unity.modules.ai`                 | 1.0.0   | Unity NavMesh AI module                                                         |
| `com.unity.modules.physics`            | 1.0.0   | 3D Physics — Rigidbody, Collider, OverlapSphere                                 |
| `com.unity.modules.unitywebrequest`    | 1.0.0   | HTTP client — UnityWebRequest cho REST API calls                                |
| `com.unity.modules.screencapture`      | 1.0.0   | Screen capture — RenderTexture readback                                         |
| `com.unity.modules.imageconversion`    | 1.0.0   | EncodeToJPG/EncodeToPNG — camera frame export                                   |
| `com.unity.modules.vehicles`           | 1.0.0   | Vehicle physics module                                                          |

### 2.3 Assembly Definitions (8 asmdef files)

| Assembly                      | Namespace           | References                                                                  | Platform    |
| ----------------------------- | ------------------- | --------------------------------------------------------------------------- | ----------- |
| **ParkingSim.API**            | `ParkingSim.API`    | endel.nativewebsocket, Newtonsoft.Json.dll                                  | All         |
| **ParkingSim.Core**           | `ParkingSim`        | ParkingSim.API, Unity.TextMeshPro, Newtonsoft.Json.dll                      | All         |
| **ParkingSim.UI**             | `ParkingSim.UI`     | ParkingSim.API, ParkingSim.Core, Unity.TextMeshPro, Newtonsoft.Json.dll     | All         |
| **ParkingSim.Editor**         | `ParkingSim.Editor` | ParkingSim.API, ParkingSim.Core, ParkingSim.UI                              | Editor only |
| **ParkingSim.Tests.EditMode** | `ParkingSim.Tests`  | ParkingSim.API, ParkingSim.Core, endel.nativewebsocket, nunit.framework.dll | Editor only |
| **ParkingSim.Tests.PlayMode** | `ParkingSim.Tests`  | ParkingSim.API, ParkingSim.Core, endel.nativewebsocket, nunit.framework.dll | All         |
| **Tests 1**                   | —                   | (default test assembly)                                                     | —           |
| **Tests**                     | —                   | (default test assembly)                                                     | —           |

### 2.4 Dependency Graph (Assembly references)

```
ParkingSim.API ← (endel.nativewebsocket, Newtonsoft.Json)
    ↑
ParkingSim.Core ← (ParkingSim.API, TextMeshPro, Newtonsoft.Json)
    ↑
ParkingSim.UI ← (ParkingSim.API, ParkingSim.Core, TextMeshPro, Newtonsoft.Json)
    ↑
ParkingSim.Editor ← (ParkingSim.API, ParkingSim.Core, ParkingSim.UI) [Editor only]

ParkingSim.Tests.EditMode ← (ParkingSim.API, ParkingSim.Core, NUnit) [Editor only]
ParkingSim.Tests.PlayMode ← (ParkingSim.API, ParkingSim.Core, NUnit) [All platforms]
```

---

## 3. Unity Scripts Architecture — Full Inventory

### 3.1 Scripts Summary (30 files across 9 folders + 3 Editor files)

| Folder                  | # Files | Key Classes                                                                                                                                             | Responsibility                                                             |
| ----------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **Scripts/API/**        | 7       | ApiConfig, ApiService, AuthManager, DataModels, MockDataProvider, MockIds, SharedBookingState                                                           | HTTP/WS communication, data models, auth, mock offline mode                |
| **Scripts/Camera/**     | 7       | VirtualCameraManager, VirtualCameraStreamer, GateCameraSimulator, SlotOccupancyDetector, ParkingCameraController, VehicleTrackingCamera, IVirtualCamera | 6 virtual cameras, JPEG streaming to AI, slot detection, user camera orbit |
| **Scripts/Core/**       | 2       | ParkingManager, FloorVisibilityManager                                                                                                                  | Central orchestrator, floor show/hide                                      |
| **Scripts/Gate/**       | 0       | (empty — .gitkeep)                                                                                                                                      | Reserved for future gate logic                                             |
| **Scripts/IoT/**        | 1       | ESP32Simulator                                                                                                                                          | IMGUI panel simulating ESP32 hardware (check-in/out/cash/verify)           |
| **Scripts/Navigation/** | 2       | WaypointGraph, WaypointNode                                                                                                                             | BFS pathfinding, slot entrance mapping, gate nodes                         |
| **Scripts/Parking/**    | 3       | ParkingLotGenerator, ParkingSlot, BarrierController                                                                                                     | Procedural lot generation, slot state machine, barrier animation           |
| **Scripts/UI/**         | 4       | DashboardUI, CameraMonitorUI, BookingTestPanel                                                                                                          | IMGUI overlay panels — stats, events, camera feeds                         |
| **Scripts/Vehicle/**    | 4       | VehicleController, VehicleQueue, LicensePlateCreator, VehicleVisualEnhancer                                                                             | Vehicle state machine, queue system, 3D license plates, visual effects     |
| **Editor/**             | 3       | AutoTestRunner, PrefabBuilder, SceneBootstrapper                                                                                                        | Editor automation — scene setup, prefab creation, test runner              |

### 3.2 Key Architecture Patterns

#### 3.2.1 API Integration (How Unity connects to backend)

- **REST API**: `UnityWebRequest` → POST/GET/PATCH to Gateway (:8000) with session cookie auth
- **WebSocket**: `NativeWebSocket` → connect to `ws://localhost:8006/ws/parking` for real-time slot updates
- **AI Direct**: `UnityWebRequest` → POST JPEG frames + plate images directly to AI Service (:8009) with `X-Gateway-Secret` header
- **Auth Strategy**: Session cookie for gateway requests, `X-Gateway-Secret` header for AI service, no auth for WebSocket
- **JSON**: Newtonsoft.Json with `[JsonProperty("camelCase")]` annotations matching backend conventions
- **Error Handling**: Multi-format parser (ApiErrorResponse > DjangoErrorResponse > GatewayErrorResponse)
- **Config**: ScriptableObject `ApiConfig` — all URLs, secrets, intervals, camera settings in one asset
- **Mock Mode**: `useMockData=true` flag enables full offline operation with MockDataProvider

#### 3.2.2 Parking Simulation (How it works)

**Procedural Generation** (`ParkingLotGenerator.cs`):

- 2 floors, each with platform, pillars, lanes, waypoints
- Floor 0 (B1): 72 car slots (4 rows × 18) + 20 moto + 5 garage = 97 slots
- Floor 1: 36 car slots (2 rows × 18) + 20 moto + 5 garage = 61 slots
- Total: 158 slots generated procedurally with proper code mapping (V1-XX, V2-XX, A-XX, B-XX, C-XX, G-XX)
- Lane waypoints auto-connected, slot entrance nodes auto-registered
- Color palette: professional dark theme (FloorColor, PillarColor, WallColor, etc.)

**Vehicle Movement** (`VehicleController.cs`):

- 11-state machine: `Idle → ApproachingGate → WaitingAtGate → Entering → Navigating → Parking → Parked → Departing → WaitingAtExit → Exiting → Gone`
- Movement: `Vector3.MoveTowards` + `Quaternion.Slerp` rotation along waypoint path
- Parking: Coroutine-based alignment + backward movement into slot
- Events: `OnReachedGate`, `OnParked`, `OnReachedExit`, `OnGone`

**Navigation** (`WaypointGraph.cs` + `WaypointNode.cs`):

- Graph data structure: Dictionary-based adjacency list
- Pathfinding: BFS (Breadth-First Search) algorithm
- Node types: Gate, Lane, SlotEntrance, Ramp, Intersection
- Slot mapping: `slotEntranceMap[slotCode] → WaypointNode`
- Editor: Gizmo visualization with color-coded nodes and cyan connection lines

#### 3.2.3 Gate/Barrier Mechanism (`BarrierController.cs`)

- Configurable open/close angles (default: 0° closed, 90° open)
- `LerpAngle`-based smooth animation with configurable speed
- Events: `OnBarrierOpened`, `OnBarrierClosed`
- `OpenThenClose(delay)` coroutine for automatic gate cycles
- Entry/exit flag differentiation

#### 3.2.4 Camera System (Rendering + AI streaming)

**6 Virtual Cameras** (`VirtualCameraManager.cs`):

| Camera ID             | Display Name       | Position              | FOV | Purpose                    |
| --------------------- | ------------------ | --------------------- | --- | -------------------------- |
| `virtual-f1-overview` | Floor 1 Overview   | (0, 35, 0) top-down   | 80° | Full floor slot monitoring |
| `virtual-f2-overview` | Floor 2 Overview   | (0, 38.5, 0) top-down | 80° | Full floor slot monitoring |
| `virtual-gate-in`     | Entry Gate         | (33, 4, 2) angled     | 60° | License plate capture      |
| `virtual-gate-out`    | Exit Gate          | (-33, 4, 2) angled    | 60° | License plate capture      |
| `virtual-zone-south`  | South Zone Monitor | (0, 20, -25) angled   | 65° | Car row monitoring         |
| `virtual-zone-north`  | North Zone Monitor | (0, 20, 25) angled    | 65° | Car row monitoring         |

**Camera Pipeline** (`VirtualCameraStreamer.cs`):

1. `RenderTexture` created at configured resolution (default: 640×480)
2. `Camera.Render()` → `RenderTexture.active` → `Texture2D.ReadPixels()` → `EncodeToJPG(quality=75)`
3. HTTP POST to `{aiServiceUrl}/ai/cameras/virtual/frame` with headers `X-Camera-ID`, `X-Gateway-Secret`, `Content-Type: image/jpeg`
4. Capture loop at configurable FPS (default: 5fps)
5. Backoff logic: after 5 consecutive errors, pause 30 seconds
6. Layer 31 exclusion: camera housing mesh invisible to its own camera (`cullingMask &= ~(1 << 31)`)

**Gate Camera** (`GateCameraSimulator.cs`):

- Physics.OverlapSphere detection of vehicles at gate
- Sequential queue processing (one vehicle at a time)
- RenderTexture → PNG → API call `AIRecognizePlate`
- OCR retry on low confidence (<0.6)
- IMGUI window with status, plate text, confidence, queue size

**Slot Detection** (`SlotOccupancyDetector.cs`):

- Hybrid detection: local Physics.OverlapBox + AI YOLO11n via camera
- Auto-assign cameras to slots by proximity
- Periodic detection loop (default: 2s local, 5s AI)
- Stats tracking: available, occupied, reserved counts

#### 3.2.5 Real-time Updates (WebSocket)

- `NativeWebSocket` library connects to `ws://localhost:8006/ws/parking`
- `DispatchMessageQueue()` called in Update() for non-WebGL platforms
- Events: `OnSlotStatusUpdate`, `OnCheckinSuccess`, `OnWsError`, `OnWsConnected`, `OnWsDisconnected`
- Slot status updates trigger color changes on ParkingSlot (green→yellow→red→gray with Lerp animation)
- Polling fallback: `PollSlotsCoroutine` every `deltaPollInterval` seconds as WebSocket backup

#### 3.2.6 UI Overlay System (IMGUI)

| Panel                   | Window ID     | Features                                                                     |
| ----------------------- | ------------- | ---------------------------------------------------------------------------- |
| **DashboardUI**         | Bottom center | Stats (available/occupied/reserved), event log, FPS counter, floor controls  |
| **ESP32Simulator**      | Top-right     | Check-in/out simulation, QR scan (DroidCam), cash payment, device management |
| **GateCameraSimulator** | Right         | Plate recognition status, confidence display, manual capture button          |
| **CameraMonitorUI**     | Right         | 2×2 camera grid with live feeds, fullscreen view, demo runner                |

#### 3.2.7 Additional Features

- **LicensePlateCreator**: 3D Vietnamese license plate with blue border, red "VIỆT NAM" header, TMP text, URP/Lit materials — front, rear, and overhead roof plate
- **VehicleVisualEnhancer**: Wheel rotation, body sway, headlights, brake lights, exhaust particles, suspension bob, auto URP material fix, auto geometry creation
- **FloorVisibilityManager**: Show/hide floors, transparency toggle with URP `_Surface` property
- **VehicleQueue**: Entry/exit queues, auto spawn (interval + wave modes), Vietnamese province license plate generation
- **SharedBookingState**: Singleton booking tracking, sync from API, lookup by plate/QR/slot code

### 3.3 Test Files (6 tests)

#### EditMode Tests (3 files):

| Test File                    | What it tests                                                                                                         |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `DataModelsTests.cs`         | JSON serialization с `[JsonProperty]` — verifies camelCase output, ESP32Response deserialization with JObject details |
| `MockDataProviderTests.cs`   | Mock data generation correctness                                                                                      |
| `SharedBookingStateTests.cs` | Booking add/remove/lookup, state management                                                                           |

#### PlayMode Tests (3 files):

| Test File                   | What it tests                                                     |
| --------------------------- | ----------------------------------------------------------------- |
| `BarrierControllerTests.cs` | Barrier start closed, open/close events fire, animation completes |
| `ParkingSlotTests.cs`       | Slot state transitions, color mapping                             |
| `WaypointGraphTests.cs`     | BFS pathfinding, node registration, path reconstruction           |

#### Editor Automation:

- `AutoTestRunner.cs`: MenuItem "ParkingSim → Run All EditMode Tests", writes results to `%TEMP%\unity-parksmart-test-results.txt`

### 3.4 Editor Tools (3 files)

| Tool                | MenuItem                                    | Purpose                                                                 |
| ------------------- | ------------------------------------------- | ----------------------------------------------------------------------- |
| `SceneBootstrapper` | ParkingSim > 🏗️ Setup Full Simulation Scene | Auto-creates full scene hierarchy with all managers, camera, API config |
| `PrefabBuilder`     | ParkingSim > 🚗 Build Vehicle Prefabs       | Creates Car + Motorbike prefabs from primitives with VehicleController  |
| `AutoTestRunner`    | ParkingSim > Run All EditMode Tests         | Runs NUnit tests and writes results to temp file                        |

### 3.5 Scenes & Assets

- **Scene**: `SampleScene.unity` (main simulation scene)
- **Prefabs**: CarPrefab, MotorbikePrefab + subfolders (Building, Gates, Navigation, Slots, Vehicles)
- **URP Settings**: 3 quality tiers (Balanced, HighFidelity, Performant) each with separate Renderer Asset
- **ScriptableObject**: `Resources/ApiConfig.asset` — runtime configuration

---

## 4. Gap Analysis — BAO_CAO_PLAN.md

### 4.1 Unity in Ch2 (Cơ sở lý thuyết)

| Question                                          | Answer                                                                                                       |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Có mục riêng cho Unity trong Ch2?**             | ❌ **KHÔNG** — thiếu hoàn toàn                                                                               |
| **Unity được nhắc ở đâu trong Ch2?**              | Chỉ 3 lần trong mục 2.6 (Go): "ứng dụng Unity simulator" (dòng 951, 953, 965) — nhắc miệng, không giải thích |
| **Có giải thích URP, C#, NativeWebSocket?**       | ❌ KHÔNG                                                                                                     |
| **Có giải thích vai trò Digital Twin/Simulator?** | ❌ KHÔNG                                                                                                     |

### 4.2 Unity in Ch3 (Phân tích thiết kế)

| Question                              | Answer                                                                                                         |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Sơ đồ kiến trúc (3.1.1) có Unity?** | ❌ KHÔNG — chỉ có Frontend, Gateway, Backend, Infrastructure, IoT. Unity simulator không xuất hiện trong sơ đồ |
| **Bảng 10 microservices (3.1.2)?**    | ❌ Unity không phải microservice nên hợp lý thiếu, nhưng cần mục riêng "Hệ thống bổ trợ"                       |
| **Bảng công nghệ (3.1.3)?**           | ❌ KHÔNG có row nào cho Unity/C#/NativeWebSocket/NUnit                                                         |
| **Use Case (3.2)?**                   | ❌ Không có actor "Unity Simulator" hay use case liên quan                                                     |
| **Kết quả (3.5)?**                    | ❌ **4 mục kết quả** (Booking, Chatbot, Map, IoT) — **THIẾU mục "Mô phỏng bãi xe 3D"**                         |

### 4.3 Các công nghệ khác thiếu từ Ch2

| Công nghệ                                       | Tình trạng trong Ch2           | Ghi chú                                                              |
| ----------------------------------------------- | ------------------------------ | -------------------------------------------------------------------- |
| **Unity 2022.3 LTS**                            | ❌ Thiếu hoàn toàn             | Cần mục 2.9                                                          |
| **Universal Render Pipeline**                   | ❌ Thiếu                       | Nằm trong mục Unity                                                  |
| **NativeWebSocket**                             | ❌ Thiếu                       | Nằm trong mục Unity                                                  |
| **NUnit**                                       | ❌ Thiếu                       | Nằm trong mục Testing                                                |
| **Cloudflare Tunnel**                           | ❌ Thiếu                       | Dùng thực tế (infra/cloudflare/), cần giải thích lý thuyết tunneling |
| **Testing (Vitest, Playwright, pytest, NUnit)** | ❌ Không có mục riêng          | Ch1 (dòng 157) nhắc qua, nhưng Ch2 không giải thích                  |
| **Gunicorn**                                    | ⚠️ Nhắc qua trong 2.8.4 Docker | Không có giải thích WSGI server riêng                                |
| **Uvicorn**                                     | ⚠️ Nhắc qua trong 2.5 FastAPI  | Đề cập nhưng không sâu                                               |
| **Alembic**                                     | ✅ Có trong 2.5                | Đã giải thích                                                        |
| **Nginx**                                       | ✅ Có mục 2.8.5                | Đủ chi tiết                                                          |
| **Tesseract**                                   | ⚠️ Nhắc trong 2.7              | Nhắc nhưng không có mục riêng (phù hợp — nó chỉ là fallback)         |
| **EasyOCR**                                     | ⚠️ Nhắc trong 2.7              | Tương tự Tesseract                                                   |
| **OAuth2 (Google/Facebook)**                    | ❌ Thiếu                       | Không giải thích lý thuyết OAuth2 flow                               |

---

## 5. Recommended New Sections

### 5.1 Ch2 cần thêm

#### Mục 2.9 (MỚI): Unity — Game Engine và Mô phỏng 3D

Content outline:

1. **Giới thiệu Unity**: Game engine đa nền tảng, C#, dùng cho cả game và non-game (simulation, digital twin, AR/VR)
2. **Lý do chọn Unity cho ParkSmart**: Digital Twin concept — mô phỏng bãi xe 3D thay thế prototype phần cứng thực tế trong giai đoạn phát triển
3. **Universal Render Pipeline (URP)**: Rendering pipeline tối ưu cho performance, shader properties (`_BaseColor`, `_Surface`), 3 quality profiles
4. **Kỹ thuật sử dụng**:
   - Procedural generation (tạo bãi xe runtime từ parameters)
   - RenderTexture → JPEG encoding → HTTP streaming (virtual camera pipeline)
   - NativeWebSocket (real-time updates)
   - Newtonsoft.Json (API communication với C# `[JsonProperty]`)
   - BFS pathfinding (WaypointGraph)
   - State machine pattern (VehicleController 11 states)
   - Singleton pattern (ApiService, AuthManager, ParkingManager, etc.)
   - ScriptableObject config (ApiConfig)
5. **So sánh Unity vs alternatives**: Unreal Engine, Godot, custom Three.js
6. **Phiên bản**: Unity 2022.3.62f3 LTS, URP 14.0.12

**Key facts for writing:**

- Unity 2022.3 LTS branch — hỗ trợ dài hạn, ổn định cho production
- URP 14.0.12 thay vì Built-in RP vì: lighter weight, SRP batcher, shader graph compatible
- NativeWebSocket thay vì WebSocketSharp vì: MessagePack support, async/await, Unity Package Manager compatible
- Newtonsoft.Json 3.2.1 (Unity NuGet package) thay vì JsonUtility vì: complex nested objects, [JsonProperty] custom naming, JObject dynamic access
- 30+ C# scripts organized in 5 assemblies (ParkingSim.API, .Core, .UI, .Editor, .Tests)
- 6 test files (3 EditMode + 3 PlayMode) using NUnit framework

#### Mục 2.10 (MỚI — tùy chọn): Kiểm thử phần mềm

Content outline:

1. Lý thuyết kiểm thử: unit test, integration test, E2E test
2. Công cụ đã dùng:
   - **Vitest 3.2.4** + Testing Library (React component tests)
   - **Playwright 1.58.2** (E2E browser testing)
   - **pytest 8.3–9.0** + pytest-asyncio + pytest-django (backend Python)
   - **NUnit** via Unity Test Framework 1.1.33 (C# EditMode + PlayMode)
3. Coverage targets, test naming convention (should...when...)

### 5.2 Ch3 cần bổ sung

#### Ch3.1.1: Thêm Unity Simulator vào sơ đồ kiến trúc

Currently: Frontend → Gateway → Backend → Infrastructure → IoT
Missing: **Unity Simulator** box connecting to Gateway + AI Service + Realtime Service

#### Ch3.1.3: Thêm rows vào bảng công nghệ

| Layer         | Công nghệ       | Phiên bản                 | Vai trò                             |
| ------------- | --------------- | ------------------------- | ----------------------------------- |
| **Simulator** | Unity           | 2022.3.62f3 LTS           | 3D parking simulation, Digital Twin |
|               | C#              | .NET Standard 2.1         | Unity scripting language            |
|               | URP             | 14.0.12                   | Render pipeline                     |
|               | NativeWebSocket | git#upm                   | Real-time slot updates              |
|               | Newtonsoft.Json | 3.2.1                     | API JSON serialization              |
|               | NUnit           | via Test Framework 1.1.33 | Unit/play mode testing              |
| **Testing**   | Vitest          | 3.2.4                     | Frontend unit tests                 |
|               | Playwright      | 1.58.2                    | E2E browser testing                 |
|               | pytest          | 8.3–9.0                   | Backend Python tests                |

#### Ch3.5 (MỚI): Mục "3.5.5 Mô phỏng bãi xe 3D (Parking Simulator)"

Content:

- Mục đích: Digital Twin — mô phỏng bãi xe thực, testing AI pipeline trước khi deploy phần cứng
- Procedural lot generation: 2 tầng, 158 ô đỗ từ parameters
- 6 virtual cameras streaming JPEG frames → AI Service
- Vehicle simulation: 11-state machine, BFS pathfinding, realistic parking animation
- ESP32 Simulator: IMGUI panel thay thế phần cứng ESP32 thực cho testing
- Gate camera: Auto-detect vehicle → capture → send to AI OCR → verify booking → open barrier
- Real-time sync: WebSocket + API polling dual-mode

---

## 6. Key Facts for Writing (Exact version numbers + script names)

### Unity Versions

- Unity: **2022.3.62f3** (LTS, revision 96770f904ca7)
- URP: **14.0.12** (`com.unity.render-pipelines.universal`)
- Newtonsoft.Json: **3.2.1** (`com.unity.nuget.newtonsoft-json`)
- NativeWebSocket: **git#upm** (`com.endel.nativewebsocket`)
- TextMeshPro: **3.0.7**
- Test Framework: **1.1.33**

### Script Counts

- Total C# scripts: **30** (excluding .meta, .asmdef)
- Assemblies: **5 runtime** + **1 editor** + **2 test**
- Namespaces: ParkingSim.API, ParkingSim.Core, ParkingSim.UI, ParkingSim.Parking, ParkingSim.Vehicle, ParkingSim.Navigation, ParkingSim.Camera, ParkingSim.IoT, ParkingSim.Editor, ParkingSim.Tests
- Test files: **6** (3 EditMode + 3 PlayMode)
- Prefabs: **2** programmatic (CarPrefab, MotorbikePrefab) + subfolders for runtime generated
- Scenes: **1** (SampleScene.unity)

### Design Patterns Used

| Pattern                     | Where                                                                                                    | Implementation                                                 |
| --------------------------- | -------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| **Singleton**               | ApiService, AuthManager, ParkingManager, VirtualCameraManager, SharedBookingState, VehicleTrackingCamera | `Instance` static property + Awake() check + DontDestroyOnLoad |
| **State Machine**           | VehicleController                                                                                        | 11-state enum with Update() switch                             |
| **Observer/Event**          | Entire codebase                                                                                          | C# `event Action<T>` delegates throughout                      |
| **Strategy**                | AuthManager.ApplyAuth()                                                                                  | Different auth headers for gateway vs AI service               |
| **Command**                 | ESP32Simulator                                                                                           | IMGUI buttons triggering API coroutines                        |
| **Factory**                 | ParkingLotGenerator, PrefabBuilder                                                                       | Procedural object creation                                     |
| **Graph/BFS**               | WaypointGraph                                                                                            | Adjacency list + BFS pathfinding                               |
| **ScriptableObject Config** | ApiConfig                                                                                                | Centralized runtime configuration                              |

### API Endpoints Called from Unity

| Endpoint                         | Method   | Service                     | Unity Script             |
| -------------------------------- | -------- | --------------------------- | ------------------------ |
| `/api/auth/login/`               | POST     | Auth (:8001) via Gateway    | AuthManager.cs           |
| `/api/parking/lots/`             | GET      | Parking (:8003) via Gateway | ApiService.cs            |
| `/api/parking/slots/?lot_id=X`   | GET      | Parking via Gateway         | ApiService.cs            |
| `/api/parking/floors/?lot_id=X`  | GET      | Parking via Gateway         | ApiService.cs            |
| `/api/booking/bookings/`         | POST/GET | Booking (:8002) via Gateway | ApiService.cs            |
| `/api/vehicle/vehicles/`         | GET      | Vehicle (:8004) via Gateway | ApiService.cs            |
| `/ai/esp32/check-in`             | POST     | AI (:8009) direct           | ApiService.cs            |
| `/ai/esp32/check-out`            | POST     | AI direct                   | ApiService.cs            |
| `/ai/cameras/virtual/frame`      | POST     | AI direct                   | VirtualCameraStreamer.cs |
| `/ai/plate/recognize`            | POST     | AI direct                   | GateCameraSimulator.cs   |
| `ws://localhost:8006/ws/parking` | WS       | Realtime (:8006) direct     | ApiService.cs            |

---

## 7. ⚠️ Gotchas & Known Issues

- [ ] **[GAP — CRITICAL]** Unity KHÔNG có mục riêng trong Ch2 — cần thêm section 2.9 hoàn chỉnh
- [ ] **[GAP — CRITICAL]** Ch3.5 thiếu mục kết quả "Mô phỏng bãi xe 3D" — cần thêm 3.5.5
- [ ] **[GAP — MODERATE]** Ch3.1.1 sơ đồ kiến trúc thiếu Unity Simulator box
- [ ] **[GAP — MODERATE]** Ch3.1.3 bảng công nghệ thiếu Unity/C#/NUnit rows
- [ ] **[GAP — MODERATE]** Testing stack (Vitest, Playwright, pytest, NUnit) không có section giải thích trong Ch2
- [ ] **[GAP — MINOR]** Cloudflare Tunnel thiếu giải thích lý thuyết trong Ch2
- [ ] **[NOTE]** Gate/ folder hiện trống (.gitkeep only) — barrier logic nằm trong Parking/BarrierController
- [ ] **[NOTE]** BookingTestPanel.cs chỉ là stub (empty class with DisallowMultipleComponent)
- [ ] **[NOTE]** visual scripting + timeline packages imported but unused in code

---

## 8. Nguồn

| #   | File/Path                                                  | Mô tả                                          |
| --- | ---------------------------------------------------------- | ---------------------------------------------- |
| 1   | `ParkingSimulatorUnity/ProjectSettings/ProjectVersion.txt` | Unity version: 2022.3.62f3                     |
| 2   | `ParkingSimulatorUnity/Packages/manifest.json`             | All package dependencies                       |
| 3   | `ParkingSimulatorUnity/Assets/Scripts/**/*.cs`             | 30 C# source files                             |
| 4   | `ParkingSimulatorUnity/Assets/Editor/*.cs`                 | 3 editor scripts                               |
| 5   | `ParkingSimulatorUnity/Assets/Tests/**/*.cs`               | 6 test files                                   |
| 6   | `ParkingSimulatorUnity/Assets/**/*.asmdef`                 | 8 assembly definitions                         |
| 7   | `ParkingSimulatorUnity/Assets/Settings/URP-*.asset`        | 6 URP render pipeline assets                   |
| 8   | `docs/BAO_CAO_PLAN.md`                                     | Main report — 2797 lines, Ch2 sections 2.1–2.8 |
| 9   | `docs/research/ch2-technologies-scan.md`                   | Previous technology scan research              |
