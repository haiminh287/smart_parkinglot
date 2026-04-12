# Unity Parking Simulator — Test Report

🤖 🧪 [TESTER] đang thực thi: Unity Digital Twin Parking Simulator test suite

---

## Summary

| Metric           | Value                                                         |
| ---------------- | ------------------------------------------------------------- |
| Total test files | 6                                                             |
| Total test cases | 55                                                            |
| Test types       | EditMode (pure logic), PlayMode (MonoBehaviour + GameObjects) |
| Coverage targets | ≥ 80% unit                                                    |
| Framework        | NUnit.Framework + UnityEngine.TestTools                       |
| Pattern          | AAA (Arrange-Act-Assert)                                      |

---

## Test Matrix

| File                         | Tests | Type     | Covers                                                                                                                                                   |
| ---------------------------- | ----- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DataModelsTests.cs`         | 7     | EditMode | DTO serialization, JSON property mapping, JObject dynamic access, PaginatedResponse, NullValueHandling                                                   |
| `MockDataProviderTests.cs`   | 7     | EditMode | Slot generation (count, distribution, uniqueness), Vehicle data, Booking references, Floor/Zone hierarchy                                                |
| `SharedBookingStateTests.cs` | 11    | EditMode | Add/Remove bookings, event firing, plate lookup (case-insensitive), dropdown formatting, status update, clear, null guards                               |
| `WaypointGraphTests.cs`      | 14    | PlayMode | Node registration, bidirectional connections, BFS pathfinding, shortest path, disconnected nodes, nearest node, slot entrance lookup, gate lookup, clear |
| `ParkingSlotTests.cs`        | 16    | PlayMode | SlotType inference (Garage/Motorbike/Painted), status parsing (case-insensitive, null, empty, unknown), color mapping, UpdateState, Initialize           |
| `BarrierControllerTests.cs`  | 5     | PlayMode | Start closed, Open + event, Close after Open + event, OpenThenClose coroutine, isEntry flag                                                              |

---

## Assembly Definitions

| Assembly                    | Platform      | References                                                                      |
| --------------------------- | ------------- | ------------------------------------------------------------------------------- |
| `ParkingSim.Tests.EditMode` | Editor only   | ParkingSim.API, ParkingSim.Core                                                 |
| `ParkingSim.Tests.PlayMode` | All platforms | ParkingSim.API, ParkingSim.Core, UnityEngine.TestRunner, UnityEditor.TestRunner |

> **Note**: `ParkingSim.Navigation` is not a separate assembly — Navigation, Parking, and Vehicle namespaces are all compiled under `ParkingSim.Core.asmdef`.

---

## Test Naming Convention

Pattern: `should_{behavior}` or `should_{behavior}_when_{condition}`

Examples:

- `should_serialize_BookingCreateRequest_with_correct_json_properties`
- `should_return_null_for_nonexistent_plate`
- `should_find_path_with_BFS`
- `should_infer_slot_type_motorbike_overrides_G_prefix`
- `should_open_and_fire_event`

---

## Test Categories

### EditMode Tests (28 tests)

Pure logic tests that don't require Unity's game loop. Tests run instantly without frame simulation.

- **DataModelsTests** — Verifies JSON serialization contracts between Unity client and backend microservices. Critical for API compatibility.
- **MockDataProviderTests** — Validates mock data generation for offline/demo mode. Ensures slot counts, zone assignments, and data integrity.
- **SharedBookingStateTests** — Tests the singleton booking state manager. Covers CRUD operations, event system, and edge cases (null, duplicates).

### PlayMode Tests (27 tests)

Tests requiring Unity's MonoBehaviour lifecycle, GameObjects, and frame-based simulation.

- **WaypointGraphTests** — Tests the navigation graph used for vehicle pathfinding. Validates BFS algorithm, node registration, and spatial queries.
- **ParkingSlotTests** — Tests slot type inference logic and status management. Verifies color coding and state transitions.
- **BarrierControllerTests** — Tests barrier gate animation state machine. Uses `[UnityTest]` with yield returns to simulate frame updates.

---

## Edge Cases Covered

| Category             | Tests                                                                                        |
| -------------------- | -------------------------------------------------------------------------------------------- |
| Null/empty input     | ParseStatus(null), ParseStatus(""), GetBookingByPlate(null plate), InferSlotType(null, null) |
| Case insensitivity   | ParseStatus("OCCUPIED"), GetBookingByPlate("51a-224.56")                                     |
| Duplicate prevention | AddBooking same ID twice — no duplicate, no event                                            |
| Disconnected graph   | FindPath returns empty list                                                                  |
| Self-reference       | Connect(node, node) — no self-loop                                                           |
| Priority rules       | Motorbike vehicleType overrides G- prefix for SlotType                                       |
| JSON null handling   | ESP32 request NullValueHandling.Ignore omits null fields                                     |
| Concurrent state     | Singleton reset via reflection between tests                                                 |

---

## How to Run

1. Open Unity Editor (2021.3+ LTS recommended)
2. **Window → General → Test Runner**
3. Select **EditMode** or **PlayMode** tab
4. Click **"Run All"**

### CLI (Unity Test Framework):

```bash
# EditMode
Unity.exe -runTests -testPlatform EditMode -projectPath ./ParkingSimulatorUnity -testResults results.xml

# PlayMode
Unity.exe -runTests -testPlatform PlayMode -projectPath ./ParkingSimulatorUnity -testResults results.xml
```

---

## Known Limitations

1. **No real API calls** — All tests use mock data or in-memory state. Cannot test actual HTTP/WebSocket communication without running backend microservices.
2. **PlayMode requires Unity Editor** — PlayMode tests cannot run in headless CI without Unity's batch mode license.
3. **BarrierController animation timing** — Tests set `speed=1000f` via reflection to avoid slow animation waits. Real behavior uses `speed=2f`.
4. **VehicleController not unit-tested** — `VehicleController` deeply couples pathfinding, coroutines, and physics. Requires integration-level PlayMode tests with full graph + slot setup (covered by WaypointGraph + ParkingSlot tests independently).
5. **TextMeshPro dependency** — `ParkingSlot.UpdateLabel()` requires TMPro component. Tests without TMPro child simply skip label updates (null-safe).
6. **SharedBookingState singleton** — Tests use reflection to reset `Instance` between runs. If tests run in parallel (not default for Unity), singleton state could leak.

---

## File Structure

```
Assets/Tests/
├── EditMode/
│   ├── ParkingSim.Tests.EditMode.asmdef
│   ├── DataModelsTests.cs          (7 tests)
│   ├── MockDataProviderTests.cs    (7 tests)
│   └── SharedBookingStateTests.cs  (11 tests)
└── PlayMode/
    ├── ParkingSim.Tests.PlayMode.asmdef
    ├── WaypointGraphTests.cs       (14 tests)
    ├── ParkingSlotTests.cs         (16 tests)
    └── BarrierControllerTests.cs   (5 tests)
```

---

✅ [TESTER] hoàn tất: 55 tests created | 6 test files | EditMode: 25 + PlayMode: 30 | Coverage target: ≥ 80%
