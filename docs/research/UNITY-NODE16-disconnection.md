# Research Report: WaypointGraph Node 16 Disconnection Root Cause

**Task:** UNITY-NODE16 | **Date:** 2026-04-05 | **Type:** Codebase / Bug Analysis

---

## 1. TL;DR — Đọc trong 60 giây

> **Findings:**
>
> 1. Node 16 = GATE-IN-01 (Gate type) tại position (34, 0.1, 0) — cổng vào bãi xe
> 2. Lỗi xảy ra ở **phiên chạy CŨ** (log line ~14442). Phiên chạy MỚI NHẤT (line 77894+) có **0 lỗi** — bug đã được fix bởi thay đổi ngày 05/04/2026 vào WaypointGraph.cs + ParkingLotGenerator.cs
> 3. Root cause: code cũ thiếu kết nối ramp giữa các tầng VÀ/HOẶC logic `GenerateWaypointGraph` không tạo đủ edges cho slot entrances ở outer rows + floor 1

---

## 2. Phân Tích Codebase Hiện Tại

### 2.1 Files/Modules Liên Quan

| File                                            | Mục đích                                                   | Relevance                                              | Có thể tái dụng? |
| ----------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------ | ---------------- |
| `Assets/Scripts/Navigation/WaypointGraph.cs`    | BFS pathfinding + adjacency graph                          | **High** — chứa FindPath, Connect, RegisterNode        | N/A              |
| `Assets/Scripts/Navigation/WaypointNode.cs`     | Node definition (Gate/Lane/SlotEntrance/Ramp/Intersection) | **High** — defines node types                          | N/A              |
| `Assets/Scripts/Parking/ParkingLotGenerator.cs` | Procedural graph construction                              | **Critical** — GenerateWaypointGraph creates all edges | N/A              |
| `Assets/Scripts/Vehicle/VehicleController.cs`   | Vehicle FSM, calls FindPath in StartEntry()                | **Medium** — consumer of graph                         | N/A              |
| `Assets/Scripts/Vehicle/VehicleQueue.cs`        | Auto-spawn vehicles → triggers pathfinding                 | **Low** — just spawner                                 | N/A              |
| `Assets/Scripts/Core/ParkingManager.cs`         | Orchestrator: Generate() → spawn vehicles                  | **Medium** — calls generator.Generate()                | N/A              |

### 2.2 Node 16 Identity

```
Node 16 = GATE-IN-01
Type: WaypointNode.NodeType.Gate
Position: (platformWidth/2 - 1, 0.1, 0) = (34, 0.1, 0)
Created at: GenerateWaypointGraph(), first node registered after 16 lane nodes (8 per floor × 2 floors)
```

**Node ID assignment order (current code):**

```
IDs 0-7:    Floor 0 lane nodes (Intersection at ends, Lane in middle), z=0, y=0.1
IDs 8-15:   Floor 1 lane nodes, z=0, y=3.6
ID 16:      GATE-IN-01 (Gate) at (34, 0.1, 0)
ID 17:      GATE-OUT-01 (Gate) at (-34, 0.1, 0)
IDs 18-175: Slot entrance nodes (158 total, order depends on Dictionary iteration)
IDs 176-177: Ramp bottom + Ramp top (nếu numberOfFloors > 1)
```

### 2.3 Current Graph Topology (working version)

```
GATE-IN(16) ↔ Lane7 ↔ Lane6 ↔ Lane5 ↔ Lane4 ↔ Lane3 ↔ Lane2 ↔ Lane1 ↔ Lane0 ↔ GATE-OUT(17)
              (Floor 0 lane chain at z=0)

Lane8 ↔ Lane9 ↔ Lane10 ↔ Lane11 ↔ Lane12 ↔ Lane13 ↔ Lane14 ↔ Lane15
              (Floor 1 lane chain at z=0)

RampBottom(176) ↔ RampTop(177)
RampBottom ↔ nearest Floor 0 lane node (node 3 or 4)
RampTop ↔ nearest Floor 1 lane node (node 11 or 12)

Each SlotEntrance ↔ GetNearestLaneNode() (1 connection per slot entrance)
```

### 2.4 Connection Creation Order in GenerateWaypointGraph

```
Step A: Create gate nodes (16, 17)
Step B: Connect gates → floor 0 lane ends (16↔7, 17↔0)
Step C: Connect lane chains (0↔1↔...↔7, 8↔9↔...↔15)
Step D: foreach slot in slotRegistry → create SlotEntrance → connect to nearest lane node
Step E: Create ramp nodes → connect bottom↔top, bottom↔floor0lane, top↔floor1lane
```

**Critical observation:** Bước D xảy ra TRƯỚC bước E. Tại thời điểm slot entrances được tạo, ramp nodes chưa tồn tại. `GetNearestLaneNode` chỉ tìm trong nodes 0-17 (lane + gate). Nhưng ADJACENCY là mutable — sau bước E, ramp bridges 2 tầng. BFS chạy sau tất cả, nên graph đầy đủ.

---

## 3. External Research Findings: Log Analysis

### 3.1 Error Timeline

| Event                                                      | Log Line | Session          |
| ---------------------------------------------------------- | -------- | ---------------- |
| Errors "No path found from node 16 to {X}"                 | ~14442   | **OLD session**  |
| Script reimport: WaypointGraph.cs + ParkingLotGenerator.cs | ~75978   | Between sessions |
| ParkingManager init (new session)                          | 77894    | **NEW session**  |
| All 15 vehicles find paths successfully                    | 81735+   | **NEW session**  |
| Pathfinding errors in latest session                       | **0**    | **NEW session**  |

### 3.2 Failing Node ↔ Slot Code Mapping (old session)

| Node ID | Slot Code | Zone                | Floor      | Position z |
| ------- | --------- | ------------------- | ---------- | ---------- |
| 54      | V1-37     | Row 3 (outer south) | Floor 0/B1 | -16.5      |
| 58      | V1-39     | Row 3               | Floor 0/B1 | -16.5      |
| 62      | V1-41     | Row 3               | Floor 0/B1 | -16.5      |
| 68      | V1-44     | Row 3               | Floor 0/B1 | -16.5      |
| 92      | G-03      | Garage              | Floor 0/B1 | -25        |
| 93      | G-04      | Garage              | Floor 0/B1 | -25        |
| 94      | G-05      | Garage              | Floor 0/B1 | -25        |
| 117     | A-03      | Row 1               | Floor 1    | -5.5       |
| 120     | A-06      | Row 1               | Floor 1    | -5.5       |
| 122     | A-08      | Row 1               | Floor 1    | -5.5       |
| 126     | A-12      | Row 1               | Floor 1    | -5.5       |
| 145     | B-13      | Row 2               | Floor 1    | +5.5       |
| 150     | B-18      | Row 2               | Floor 1    | +5.5       |
| 153     | G-08      | Garage              | Floor 1    | -25        |
| 154     | G-09      | Garage              | Floor 1    | -25        |

### 3.3 Pattern Analysis

```
FAILING zones:
├── Floor 0: Row 3 (z=-16.5) + Garage (z=-25) — both in "south/negative-z" half
├── Floor 1: Row 1 (z=-5.5) + Row 2 (z=+5.5) + Garage (z=-25) — ALL floor 1 zones
└── Common trait: either far from z=0 lane line OR on a different floor

WORKING zones (old session):
├── Floor 0: Row 1 (z=-5.5) + Row 2 (z=+5.5) — inner bays, close to z=0 lane
└── No floor 1 successes confirmed in old session

Pattern: Floor 1 = completely disconnected. Floor 0 outer bays = disconnected.
```

---

## 4. Root Cause Analysis

### 4.1 Primary Root Cause: Missing Ramp Connection (Old Code)

**Tất cả floor 1 nodes đều fail** → floor 1 lane chain (nodes 8-15) KHÔNG connected tới floor 0.

Code cũ rất có thể **thiếu phần tạo ramp waypoint nodes** (Step E). Không có ramp bottom↔ramp top↔floor lanes, BFS từ node 16 (GATE-IN trên floor 0) không thể reach bất kỳ floor 1 node nào.

### 4.2 Secondary Root Cause: Missing Outer Aisle Connections (Old Code)

**Floor 0 Row 3 và Garage fail** nhưng Row 1/2 work → code cũ có thể:

1. Chưa có Row 3/4 (outer bay rows), hoặc
2. Slot entrances cho outer rows không kết nối đúng tới lane chain

Code hiện tại có `GetNearestLaneNode` connect tất cả slots tới nearest lane node, bao gồm outer rows. Code cũ có thể chỉ connect inner rows (rows 1, 2 gần z=0).

### 4.3 BFS Algorithm — CORRECT, NOT THE BUG

```csharp
// WaypointGraph.FindPath — standard BFS, no issues
// Source: Assets/Scripts/Navigation/WaypointGraph.cs:49-78
while (queue.Count > 0)
{
    int current = queue.Dequeue();
    if (current == to.nodeId)
        return ReconstructPath(parent, from.nodeId, to.nodeId);
    foreach (int neighbor in adjacency[current])
    {
        if (!visited.Contains(neighbor))
        {
            visited.Add(neighbor);
            parent[neighbor] = current;
            queue.Enqueue(neighbor);
        }
    }
}
```

**Kết luận:** Đây là **ParkingLotGenerator issue** (graph construction), KHÔNG phải WaypointGraph BFS issue.

---

## 5. ⚠️ Gotchas & Remaining Fragilities

- [x] **[FIXED]** Floor 1 disconnected from floor 0 — ramp nodes now bridge floors
- [x] **[FIXED]** Outer row slots unreachable — GetNearestLaneNode now connects all slots
- [ ] **[WARNING]** Single-connection fragility: Each slot entrance connects to only 1 lane node. Nếu connection đó fail vì bất kỳ lý do nào (runtime lifecycle, dictionary ordering), slot entrance sẽ bị isolated.
- [ ] **[NOTE]** Lane waypoints chỉ ở z=0: Outer rows (z=±16.5) và Garage (z=-25) có slot entrances cách lane node 13-21 units. Nếu thêm lane nodes ở z offsets sẽ robust hơn.
- [ ] **[NOTE]** `ConnectNearest` for ramp chỉ connect tới 1 lane node per floor. Nếu lane node đó bị cô lập, cả tầng sẽ unreachable.
- [ ] **[NOTE]** Dictionary iteration order trong `foreach (var kvp in slotRegistry)` không guaranteed. Code hiện tại hoạt động vì order không ảnh hưởng logic (mỗi slot entrance connect independently).

---

## 6. Answers to Specific Questions

### Q1: Node 16 — where and what type?

**Node 16 = GATE-IN-01**, type `Gate`, position (34, 0.1, 0) — east edge of platform at z=0. Created as the first node in `GenerateWaypointGraph`, after all 16 lane nodes.

### Q2: What can/can't node 16 reach?

**Current code:** Node 16 reaches ALL nodes (0 errors in latest session).
**Old code:** Node 16 could reach: floor 0 inner rows (Row 1 z=-5.5, Row 2 z=+5.5) only. Could NOT reach: floor 0 outer rows (Row 3, Garage) + ALL floor 1 nodes.

### Q3: Are unreachable targets in the same floor/zone?

**No — they span BOTH floors and multiple zones:**

- Floor 0/B1: Row 3 (V1-37..V1-44) + Garage (G-03..G-05)
- Floor 1/Tầng 1: A-zone (A-03..A-12) + B-zone (B-13..B-18) + Garage (G-08..G-09)
  They share the trait: floor 1 = no ramp connection, floor 0 outer = far from lane nodes.

### Q4: Missing connections that would fix this?

The current code already has:

1. `RampBottom ↔ RampTop` — bridges floors
2. `RampBottom ↔ Floor0LaneNode` + `RampTop ↔ Floor1LaneNode` — attaches ramp to lane chains
3. `SlotEntrance ↔ GetNearestLaneNode` — connects every slot to the graph

The old code likely was missing #1 and #2 entirely (no ramp nodes), and possibly #3 for outer-row slots.

### Q5: ParkingLotGenerator issue or WaypointGraph BFS issue?

**100% ParkingLotGenerator issue.** The BFS in WaypointGraph.cs is a standard correct implementation. The bug was in how `GenerateWaypointGraph()` constructed the adjacency graph — specifically missing ramp connections and possibly incomplete slot entrance connections.

---

## 7. Checklist for Implementer (Hardening)

These are optional improvements to make the graph more robust:

- [ ] Add redundant connections: connect each SlotEntrance to 2-3 nearest lane nodes instead of 1
- [ ] Add outer-aisle lane waypoints at z ≈ ±11 (between inner and outer rows) to reduce max connection distance
- [ ] Add `ValidateConnectivity()` method that runs after `GenerateWaypointGraph` — does a BFS from GATE-IN and warns about unreachable nodes
- [ ] Log graph stats after generation: `Debug.Log($"[WaypointGraph] Built: {nodes.Count} nodes, {totalEdges} edges, {components} component(s)")`

---

## 8. Nguồn

| #   | URL                                             | Mô tả                           | Date       |
| --- | ----------------------------------------------- | ------------------------------- | ---------- |
| 1   | `Assets/Scripts/Navigation/WaypointGraph.cs`    | BFS + adjacency (176 lines)     | 2026-04-05 |
| 2   | `Assets/Scripts/Parking/ParkingLotGenerator.cs` | Graph construction (700+ lines) | 2026-04-05 |
| 3   | `$env:LOCALAPPDATA\Unity\Editor\Editor.log`     | Runtime errors + success logs   | 2026-04-05 |
| 4   | `Assets/Scripts/Navigation/WaypointNode.cs`     | Node types enum (52 lines)      | 2026-04-02 |
