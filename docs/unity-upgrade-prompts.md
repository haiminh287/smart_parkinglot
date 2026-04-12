# 🎮 Unity Smart Parking Simulator — Professional Upgrade Prompts
> Sử dụng các prompt này với GitHub Copilot, ChatGPT-4, hoặc Claude để generate code Unity C# chính xác.

---

## PROMPT 1 — Vehicle Visual Enhancement (Fix Màu Hồng + Xe Nhìn Thật)

```
Tôi đang làm Unity 2022 LTS với URP (Universal Render Pipeline).
Project: Smart Parking Lot Simulator.

Tạo script C# tên `VehicleVisualEnhancer.cs` trong namespace `ParkingSim.Vehicle`, 
attach vào CarPrefab (đã có VehicleController + Rigidbody kinematic).

YÊU CẦU:
1. Fix material pink: tất cả Renderer trong children, đổi shader sang URP/Lit nếu cần.
2. Wheel rotation: 4 Transform references (WheelFL, WheelFR, WheelBL, WheelBR).
   - Lấy tốc độ từ `VehicleController.CurrentSpeed` (float, m/s)
   - Xoay wheels quanh trục X: `wheelDiameter = 0.6f`, rpm = speed/circumference*60
3. Body sway khi rẽ:
   - Lấy `Vector3 angularVelocity` từ VehicleController
   - Lean body Z: `Mathf.LerpAngle(currentLean, -turnRate * 3f, Time.deltaTime * 5f)`
4. Headlights: 2 Light (PointLight hoặc SpotLight) ở đầu xe, bật khi game start, brightness pulse nhẹ.
5. Brake lights: MeshRenderer ở đuôi xe, đổi emissive color đỏ sáng khi dừng.
6. Exhaust particle: ParticleSystem nhỏ ở đuôi xe, emit khi speed > 0.5f.
7. Suspension bob: transform root xe nhún lên xuống 0.02f amplitude, frequency = speed * 2.

Context files (đã có trong project):
- VehicleController.cs có: `public float CurrentSpeed`, `public VehicleState state`
- Prefab structure: Vehicle → Body, WheelFL, WheelFR, WheelBL, WheelBR, LightsParent

Viết code đầy đủ, không dùng GetComponent trong Update() — cache tất cả trong Awake/Start.
```

---

## PROMPT 2 — Vehicle Tracking Camera (Camera Theo Dõi Từng Xe)

```
Unity 2022 LTS + URP. Smart Parking Lot Simulator.

Tạo `VehicleTrackingCamera.cs` trong namespace `ParkingSim.Camera`.

Yêu cầu hành vi:
- Singleton: `public static VehicleTrackingCamera Instance`
- `TrackVehicle(VehicleController target)`: camera bắt đầu follow xe này
- `StopTracking()`: camera trả về overview position
- Camera position: offset `(0, 8, -15)` relative to vehicle's transform (not world)
- Look-ahead: LookAt về `target.transform.position + target.transform.forward * 5f`
- Smooth damp: `SmoothDamp` position với smoothTime = 0.3f
- FOV zoom: khi xe dừng tại cổng → zoom in FOV từ 60 → 40 trong 1s (Coroutine)
- Auto-return to overview: 5s sau khi vehicle.state == Parked → gọi StopTracking()
- Shake effect: khi gate barrier drop → `CameraShake(duration=0.3f, magnitude=0.1f)`

Camera switch:
- Phím [TAB]: toggle overview ↔ tracking mode
- Phím [V]: focus vehicle tracking camera vào xe gần entry gate nhất

Integration với ParkingManager:
- Khi ParkingManager.SpawnVehicle() → gọi VehicleTrackingCamera.Instance.TrackVehicle(vehicle)

Camera UI overlay (OnGUI):
- Góc trên phải: "🎥 TRACKING: [plate]" label khi đang track
- Tin nhắn trạng thái: "Vehicle at Gate", "Navigating", "Parked" với màu sắc

Không dùng Cinemachine — viết pure Unity Camera code.
```

---

## PROMPT 3 — Gate Camera AI Detection (Camera Cổng Vào Detect Biển Số)

```
Unity 2022 LTS + URP. Smart Parking Simulator.

Nâng cấp `GateCameraSimulator.cs` (đã có trong project) với các cải tiến:

HIỆN TẠI: detect khi state == ApproachingGate (xe đang di chuyển, chưa dừng)
FIX: detect khi state == WaitingAtGate (xe đã dừng trước cổng)

Thêm các tính năng sau:

1. CAMERA ANIMATION UI (OnGUI):
   - Tạo camera preview texture (640x480) hiển thị ngay góc dưới phải màn hình
   - Border glow màu xanh khi idle, nhấp nháy đỏ khi đang scan
   - Progress bar + text: "📸 Scanning..." → spinner animation (ký tự rotate ⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏)
   - Khi có kết quả: hiển thị plate text to, với green glow nếu confidence > 0.85

2. AI DETECTION SEQUENCE (thay thế CaptureAndRecognize):
   - Frame 1: RenderTexture snapshot → fake "motion blur" bằng cách blend 2 frames
   - Gọi apiService.AIRecognizePlate() với timeout 5s
   - Nếu confidence < 0.6: retry 1 lần với enhanced brightness (+20%)
   - Nếu vẫn fail: fallback dùng vehicle.plateNumber với confidence = 0f
   - Log format: "[GateCam] 📷 Captured → 🧠 OCR → ✅ 51A-123.45 (94%)"

3. BIỂN SỐ OVERLAY:
   - Vẽ rectangle highlight màu xanh lá quanh vùng biển số (estimate vị trí trong frame)
   - Text recognized plate to rõ bên trên rectangle

4. MULTI-VEHICLE QUEUE:
   - Queue `Queue<VehicleController>` — detect lần lượt, không bỏ sót xe
   - Nếu có 2 xe cùng ở gate zone → xử lý từng cái, cách nhau 2s

5. ESP32 INTEGRATION:
   - Sau khi detect xong → gọi `esp32Simulator.SetPlateFromCamera(plate)`
   - Phát âm thanh beep ngắn: `AudioSource.PlayOneShot(beepClip)`

Dependencies cần inject (SerializeField): ApiService, ESP32Simulator, AudioClip beepClip.
Viết đầy đủ, không truncate code.
```

---

## PROMPT 4 — Parking Lot Camera Overview (Camera Bao Quát Hiển Thị Đủ Ô Đỗ)

```
Unity 2022 LTS. Smart Parking Simulator.

Nâng cấp `ParkingCameraController.cs` để hiển thị đầy đủ bãi đỗ xe.

PROBLEM: Camera distance = 60, verticalAngle = 60 → không thấy đường kẻ ô đỗ.

FIXES:
1. Default overview: distance = 45, verticalAngle = 55, horizontalAngle = 30
   → Góc nghiêng nhẹ để thấy layout rõ nhưng vẫn thấy ô đỗ xe

2. Thêm Camera Mode Enum:
   enum CameraMode { Overview, GateEntry, GateExit, VehicleTracking, FloorView }

3. Phím shortcuts:
   [1] = Overview toàn bãi (distance 45, angle 55)
   [2] = Floor 1 zoom (distance 30, y=5)
   [3] = Floor 2 zoom (distance 30, y=8.5)
   [G] = Gate Entry camera (position 35, 4, 0 looking left)
   [TAB] = cycle camera modes
   [F] = FocusOn vehicle gần cursor nhất (raycast)
   [R] = Reset về overview

4. Smooth transitions:
   - Khi switch mode: lerp position + rotation trong 1s (Coroutine)
   - Không teleport đột ngột

5. Edge scrolling (optional, [SerializeField] bool enableEdgeScrolling):
   - Di chuột ra rìa màn hình → pan camera

6. Mini HUD (OnGUI):
   - Góc dưới trái: "[1]Overview [2]B1 [3]F2 [G]Gate [TAB]Cycle"
   - Current mode indicator với màu

7. Gizmos (Editor only): Vẽ frustum của camera vào Scene view

Giữ nguyên: ISMouseOverGUI, ProcessMouseInput (orbit, pan, zoom).
```

---

## PROMPT 5 — Vehicle Queue Auto-Spawn (Xe Chạy Liên Tục Real-Time)

```
Unity 2022 LTS. Smart Parking Simulator.

Nâng cấp `VehicleQueue.cs` để xe spawn và chạy liên tục tự động.

YÊU CẦU:

1. AUTO-SPAWN MODE:
   [SerializeField] bool autoSpawnEnabled = true
   [SerializeField] float spawnIntervalMin = 15f
   [SerializeField] float spawnIntervalMax = 45f
   
   Coroutine tự spawn xe với random plate + random available slot.

2. PLATE GENERATOR:
   Tạo private string GenerateRandomPlate():
   - Format: "51A-xxx.xx" (Vietnamese style)
   - 51A, 51B, 30A, 29A, 77A (random tỉnh)
   - Số ngẫu nhiên xxx.xx
   
3. BOOKING SIMULATION:
   Nếu `config.useMockData = true`:
   - Random chọn 1 slot Available từ generator.slotRegistry
   - Spawn vehicle thẳng vào slot đó (skip API call)
   
   Nếu `config.useMockData = false`:
   - Gọi API tạo booking trước, sau đó spawn

4. VEHICLE POOL (Object Pooling):
   - Pool 10 CarPrefab, 5 MotorbikePrefab sẵn
   - GetFromPool() / ReturnToPool() thay vì Instantiate/Destroy
   - Khi xe Gone → return to pool, reset transform + state

5. WAVE MODE:
   [SerializeField] bool waveMode = false
   - Spawn 3-5 xe cùng lúc mỗi 60s (morning/evening rush simulation)

6. DEPARTURE SIMULATION:
   - 30% xe rời đi sau 10-20s (quick stop)
   - 50% xe rời đi sau 30-60s (normal)
   - 20% xe ở lại 120-300s (long stay)

7. UI PANEL (OnGUI):
   - "Vehicles spawned: X / departed: Y"
   - Button "[+] Spawn Car", "[+] Spawn Motorbike"
   - Toggle "Auto Spawn" checkbox

Dependencies: ParkingManager, ParkingLotGenerator, ApiService.
```

---

## PROMPT 6 — Database Seed Khớp Unity + Playwright Booking Test

```python
# PROMPT cho Python developer

"""
Tạo 2 files:

1. seed_unity_compatible_data.py
   - Seed database với parking slots CHÍNH XÁC khớp với Unity ParkingLotGenerator.cs
   - Slots cần tạo:
     * parking_lot_id: [lấy từ env PARKING_LOT_ID]
     * Zone B1 (floor_number=0): V1-01..V1-72 (car), V2-01..V2-20 (motorbike), G-01..G-05 (garage)
     * Zone Tầng 1 (floor_number=1): A-01..A-18, B-01..B-18 (car), C-01..C-20 (motorbike), G-06..G-10
     * Status: 80% Available, 15% Occupied, 5% Reserved
     
   - Với slots Occupied: tạo booking kèm theo
     * vehicle_type: Car hoặc Motorbike theo slot type
     * license_plate: format "51A-xxx.xx" 
     * check_in_time: cách đây 1-2 giờ
     
2. test_playwright_full_booking.py
   - Dùng Playwright Python (playwright.sync_api)
   - Test scenario:

   STEP 1: Login user
   page.goto("http://localhost:3000/login")
   # điền email/password từ env TEST_USER_EMAIL, TEST_USER_PASSWORD
   
   STEP 2: Tạo booking
   # Chọn bãi đỗ xe, chọn slot V1-05 (Available), confirm booking
   # Ghi lại booking_id, qr_data
   
   STEP 3: Verify WebSocket event
   # Kết nối WebSocket ws://localhost:8000/ws/parking
   # Chờ event: {"type": "checkin_success", "slot_code": "V1-05"}
   
   STEP 4: Verify slot status via API
   r = requests.get(f"{API_BASE}/parking/slots/?code=V1-05")
   assert r.json()["results"][0]["status"] == "occupied"
   
   STEP 5: Checkout
   # Gọi API checkout với booking_id
   # Verify slot trở về "available"
   
   STEP 6: (Optional) Run in loop
   # Lặp 3 lần với các slots khác nhau: V1-01, A-05, V2-03

Đọc credentials từ .env file. Dùng BASE_URL từ env.
Viết đầy đủ, có assertions rõ ràng, in kết quả pass/fail.
"""
```

---

## PROMPT 7 — License Plate 3D Object (Biển Số Xe Đẹp Thật)

```
Unity 2022 LTS + URP + TextMeshPro.

Tạo `LicensePlateCreator.cs` - static helper class trong namespace ParkingSim.Vehicle.

Hàm tạo biển số 3D cho xe:
public static GameObject CreateVietnamesePlate(Transform vehicleTransform, string plateText, bool isRear)

Cấu trúc biển số Việt Nam:
- Background: Quad 0.33m × 0.14m màu trắng (biển xe con)
- Border viền xanh dương dày 2px
- Phía trên: "VIỆT NAM" font nhỏ màu đỏ + dải xanh
- Text chính: plateText, TextMeshPro font Bold, màu đen
  * Font: Roboto Mono hoặc Inter Bold
  * Alignment Center, padding phù hợp
- Embossed effect: dùng normal map nếu có, hoặc offset text layer
- Position nếu isRear: local (0, 0.5f, -1.4f), rotation Y=180
- Position nếu !isRear: local (0, 0.5f, 1.4f)

Material:
- Shader: URP/Lit
- Smoothness: 0.3 (matte giấy)
- Không emissive (biển số thường, không có đèn)

Thêm function để update text realtime:
public static void UpdatePlateText(GameObject plateObject, string newText)

Gọi từ ParkingManager.AttachPlateText() — thay thế implementation cũ.
```

---

## PROMPT 8 — Slot Detection Camera System (Camera Detect Trạng Thái Ô Đỗ)

```
Unity 2022 LTS + URP. Smart Parking Lot Simulator.

Nâng cấp `SlotOccupancyDetector.cs` để tích hợp camera-based detection thay vì chỉ Physics.OverlapBox.

YÊU CẦU:

1. ZONE CAMERAS:
   - Mỗi zone (V1 South, V1 North, A, B) có 1 VirtualCameraStreamer riêng
   - Camera chụp full zone mỗi 5s
   - Gửi image lên API: POST /ai/detect-slots
   - API trả về: [{slot_code, is_occupied, confidence}]
   
2. HYBRID DETECTION (Physics + AI):
   - Physics.OverlapBox: realtime, 0.5s interval → cho visual update ngay
   - AI Camera: mỗi 5s → confirm/correct physics detection
   - Nếu AI và Physics mâu thuẫn → trust AI nếu confidence > 0.8
   
3. SLOT STATUS VISUAL:
   Khi slot đổi trạng thái → animate:
   - Available (xanh): glow pulse xanh lá nhẹ
   - Occupied (đỏ): fade in màu đỏ từ từ
   - Reserved (vàng): blink chậm màu vàng
   - Wrong slot (tím): strobe mạnh + gọi alert

4. DETECTION LOG UI:
   [SerializeField] bool showDetectionLog = true
   - Panel nhỏ giữa màn hình khi có thay đổi:
     "📍 V1-05: Available → Occupied [51A-123.45] [98%]"
   - Fade out sau 3s

5. STATISTICS:
   - Expose: int TotalAvailable, TotalOccupied, TotalReserved
   - OnDetectionChanged event để Dashboard subscribe

6. CAMERA ASSIGNMENT (dùng SlotOccupancyDetector.AssignSlotsToCamera()):
   // Tự động assign dựa trên slot code prefix
   private void AutoAssignCameras():
     "V1" slots → "virtual-zone-south" hoặc "virtual-zone-north" tùy Z position
     "A","B" slots → "virtual-f2-overview"
     "V2","C" moto → zone camera tương ứng

Không thay đổi interface ISlotOccupancyDetector.
```

---

## PROMPT 9 — Dashboard UI (Bảng Điều Khiển Chuyên Nghiệp)

```
Unity 2022 LTS + UGUI + TextMeshPro. Smart Parking Simulator.

Nâng cấp `DashboardUI.cs` với thiết kế HUD chuyên nghiệp.

LAYOUT (Canvas Screen Space Overlay):
┌─────────────────────────────────────┐
│ [Logo 🅿️ ParkSmart]    [Clock] [FPS]│  ← Header bar, dark blue gradient
├──────────┬──────────┬───────────────┤
│ 🟢 Avail │ 🔴 Occ  │ 🟡 Reserved   │  ← Stats row, animated numbers
│   45     │   27    │    8          │
├──────────┴──────────┴───────────────┤
│ 📹 Gate Camera Feed      [Fullscreen]│  ← Camera preview 320×180
│ Status: ✅ 51A-123.45 (94%)        │
├─────────────────────────────────────┤
│ 🚗 Active Vehicles: [list 3 items]  │  ← Scrolling list
│  51A-123.45 → V1-05 [Navigating]   │
│  30A-456.78 → A-12 [Parked] 8m ago │
├─────────────────────────────────────┤
│ 📋 Recent Events (last 5):         │  ← Event log
│  10:45 ✅ 30A-456.78 checked in    │
│  10:43 🚗 51A-123.45 spawned       │
└─────────────────────────────────────┘

YÊU CẦU KỸ THUẬT:
- Nền: dark blue-gray `#1a2332`, opacity 85%
- Font: TextMeshPro với font Inter (import từ Google Fonts hoặc built-in)
- Số stats: animate count up/down khi thay đổi (DOTween style bằng Coroutine)
- Camera preview: RawImage hiển thị RenderTexture từ VirtualCameraStreamer "virtual-gate-in"
- Event log: ScrollRect với ContentSizeFitter, auto-scroll xuống
- Responsive: tự co lại nếu màn hình < 1280px
- Drag: có thể kéo panel ra chỗ khác
- Phím [H]: toggle show/hide dashboard

Events subscribe:
- ParkingManager.OnStatusMessage → thêm vào event log
- SlotOccupancyDetector.OnDetectionChanged → cập nhật stats
- VehicleController.OnParked → thêm event "parked"
```

---

## PROMPT 10 — Full Scene Setup Guide (Hướng Dẫn Lắp Ráp Scene)

```
Unity 2022 LTS. Hướng dẫn setup SampleScene.unity hoàn chỉnh sau khi có tất cả scripts.

HIERARCHY STRUCTURE:
═══════════════════════════════
🎬 SampleScene
├── 📷 Main Camera
│   ├── Component: Camera (FOV 60)
│   ├── Component: ParkingCameraController (distance=45, verticalAngle=55)
│   └── Component: VehicleTrackingCamera
│
├── 💡 Lighting
│   ├── Directional Light (Intensity 1.2, angle 45°)
│   └── [ReflectionProbe] (baked, covers parking area)
│
├── 🏢 ParkingLot [ParkingManager Component]
│   ├── Component: ParkingManager (Manager chính)
│   ├── Component: ParkingLotGenerator
│   ├── Component: WaypointGraph
│   ├── Component: VehicleQueue
│   ├── Component: SlotOccupancyDetector
│   └── 📍 VehicleSpawnPoint (position = 45, 0, 0)
│
├── 📷 CameraSystem
│   ├── Component: VirtualCameraManager
│   └── Component: GateCameraSimulator
│
├── 🚧 Gates
│   ├── Gate_GATE-IN-01
│   │   └── Component: BarrierController
│   └── Gate_GATE-OUT-01
│       └── Component: BarrierController
│
├── 🌐 Services
│   ├── Component: ApiService
│   ├── Component: ApiConfig (useMockData=false, ...URLs)
│   ├── Component: AuthManager
│   └── Component: ESP32Simulator
│
├── 🎮 UI
│   ├── Canvas (Screen Space Overlay, scale 1920x1080)
│   │   ├── DashboardPanel (Component: DashboardUI)
│   │   └── CameraMonitorPanel (Component: CameraMonitorUI)
│   └── EventSystem
│
└── 📦 VehiclePool
    ├── [10x] CarPrefab_Pool_01..10 (inactive)
    └── [5x] MotorbikePrefab_Pool_01..05 (inactive)

INSPECTOR WIRING:
ParkingManager fields:
  - apiService → Services/ApiService
  - authManager → Services/AuthManager  
  - generator → ParkingLot (ParkingLotGenerator)
  - waypointGraph → ParkingLot (WaypointGraph)
  - entryBarrier → Gates/Gate_GATE-IN-01 (BarrierController)
  - exitBarrier → Gates/Gate_GATE-OUT-01 (BarrierController)
  - vehicleQueue → ParkingLot (VehicleQueue)
  - carPrefab → Assets/Prefabs/CarPrefab.prefab
  - motorbikePrefab → Assets/Prefabs/MotorbikePrefab.prefab
  - vehicleSpawnPoint → ParkingLot/VehicleSpawnPoint
  - virtualCameraManager → CameraSystem (VirtualCameraManager)
  - slotOccupancyDetector → ParkingLot (SlotOccupancyDetector)

GateCameraSimulator:
  - gateCamera → CameraSystem/VirtualCamera_virtual-gate-in (Camera component)
  - capturePoint → Gates/Gate_GATE-IN-01 (Transform)
  - captureRadius = 4f
  - esp32Simulator → Services/ESP32Simulator
  - apiService → Services/ApiService

POST-SETUP CHECKLIST:
□ Layer 31 tạo trong Project Settings → Physics (tên "CameraHousing")
□ Camera Main có tag "MainCamera"
□ VehicleSpawnPoint ở ngoài cổng vào (x=45, y=0, z=0)
□ URP Asset assigned trong Project Settings → Graphics
□ Physics: Gravity = -9.81, Default Contact Offset = 0.01
□ TextMeshPro: Window → TextMeshPro → Import TMP Essential Resources
□ ApiConfig.targetParkingLotId khớp với DB (check seed_unity_compatible_data.py output)
```

---

## TIPS SỬ DỤNG PROMPTS

1. **Cho GitHub Copilot**: Mở file target → paste prompt vào comment đầu file → Copilot sẽ autocomplete
2. **Cho Claude/ChatGPT**: Paste nguyên prompt + thêm "Output format: complete C# file, no truncation"
3. **Context**: Luôn kèm theo các class hiện tại quan trọng (VehicleController.cs, ParkingManager.cs)
4. **Iteration**: Sau khi generate xong 1 prompt → test compile → nếu lỗi → paste error + "Fix this Unity error"

## THÔNG TIN PROJECT

- Unity version: 2022.3 LTS
- Render Pipeline: URP  
- Packages: TextMeshPro, Newtonsoft.Json
- Backend: FastAPI + Django + MySQL
- WebSocket: Realtime slot updates
