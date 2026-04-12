using System.Collections.Generic;
using UnityEngine;
using ParkingSim.Navigation;

namespace ParkingSim.Parking
{
    public class ParkingLotGenerator : MonoBehaviour
    {
        [Header("Floor Settings")]
        public int numberOfFloors = 1;
        public float floorHeight = 3.5f;

        [Header("Painted Slots")]
        public int paintedSlotsPerRow = 18;   // 18/row × 4 rows = 72 → covers Zone V1 fully
        public int paintedRows = 2;
        public float slotWidth = 2.5f;
        public float slotDepth = 5f;

        [Header("Garage Slots")]
        public int garageSlotCount = 5;
        public float garageWidth = 3f;
        public float garageDepth = 6f;
        public float garageHeight = 2.5f;

        [Header("Motorbike Slots")]
        public int motorbikeSlotCount = 20;
        public float motorbikeWidth = 1f;
        public float motorbikeDepth = 2f;

        [Header("Layout")]
        public float laneWidth = 6f;
        public float platformWidth = 70f;   // widened for 18 slots × 2.5 m + margins
        public float platformDepth = 60f;   // deepened for 4 row-pairs + outer aisles
        public float pillarSpacing = 8f;

        [Header("References")]
        public WaypointGraph waypointGraph;

        public Dictionary<string, ParkingSlot> slotRegistry = new Dictionary<string, ParkingSlot>();

        // Professional color palette
        private static readonly Color FloorColor = new Color(0.25f, 0.25f, 0.28f);
        private static readonly Color PillarColor = new Color(0.78f, 0.76f, 0.73f);
        private static readonly Color WallColor = new Color(0.72f, 0.70f, 0.67f);
        private static readonly Color RampColor = new Color(0.35f, 0.37f, 0.42f);
        private static readonly Color GateColor = new Color(0.15f, 0.22f, 0.45f);
        private static readonly Color OrangeLineColor = new Color(1f, 0.5f, 0f);
        private static readonly Color WhiteLineColor = Color.white;
        private static readonly Color YellowLine = new Color(1f, 0.85f, 0f);
        private static readonly Color CurbColor = new Color(0.6f, 0.6f, 0.6f);
        private static readonly Color GroundColor = new Color(0.18f, 0.25f, 0.15f);
        private static readonly Color CeilingColor = new Color(0.82f, 0.80f, 0.78f);
        private static readonly Color BlackColor = new Color(0.08f, 0.08f, 0.08f);
        private static readonly Color LightEmission = new Color(1f, 0.95f, 0.8f);
        private static readonly Color SignGreen = new Color(0f, 0.8f, 0.2f);
        private static readonly Color SignRed = new Color(0.9f, 0.1f, 0.1f);
        private static readonly Color RoadColor = new Color(0.3f, 0.3f, 0.32f);

        public void Generate()
        {
            ClearExisting();
            slotRegistry.Clear();
            if (waypointGraph != null) waypointGraph.Clear();

            int globalPaintedIdx = 0;
            int globalGarageIdx = 0;
            int globalMotoIdx = 0;

            var allLaneNodes = new List<List<WaypointNode>>();

            for (int level = 0; level < numberOfFloors; level++)
            {
                float yBase = level * floorHeight;
                var floorParent = new GameObject($"Floor_{level + 1}");
                floorParent.transform.SetParent(transform);
                floorParent.transform.localPosition = Vector3.zero;

                CreateFloorPlatform(floorParent.transform, yBase);
                CreatePillars(floorParent.transform, yBase, level == 0 ? 4 : 2);

                var laneNodes = CreateLaneWaypoints(yBase, floorParent.transform);
                allLaneNodes.Add(laneNodes);

                float carZoneStartX = -platformWidth / 2f + 8f;
                float carZoneZ = 0f;
                float aisleHalfWidth = laneWidth / 2f;

                // ── Slot code mapping to match DB zones ──────────────────────────────
                // Floor 0  → DB B1    : 4 rows × 18 = 72 V1 car slots (V1-01..V1-72)
                //                       covers occupied range V1-46..V1-70 in rows 3 & 4
                //            Zone V2  : moto V2-01..V2-20
                // Floor 1  → DB Tầng 1: 2 rows: row1=A-01..A-18 (Zone A), row2=B-01..B-18 (Zone B)
                //            Zone C moto : C-01..C-20
                // Garage slots do not exist in DB — kept as G-xx (stay Available colour)
                string carPrefix1, carPrefix2, motoPrefix;
                int carRow1Start, carRow2Start, motoStart;

                if (level == 0)
                {
                    carPrefix1 = "V1"; carRow1Start = 1;
                    carPrefix2 = "V1"; carRow2Start = paintedSlotsPerRow + 1;
                    motoPrefix  = "V2"; motoStart    = 1;
                }
                else
                {
                    carPrefix1 = "A";  carRow1Start = 1;
                    carPrefix2 = "B";  carRow2Start = 1;
                    motoPrefix  = "C"; motoStart    = 1;
                }

                // Row 1: inner south (z-negative side of center aisle)
                float zRow1 = carZoneZ - aisleHalfWidth - slotDepth / 2f;   // ≈ -5.5
                for (int i = 0; i < paintedSlotsPerRow; i++)
                {
                    string code = $"{carPrefix1}-{(carRow1Start + i):D2}";
                    float x = carZoneStartX + i * slotWidth;
                    CreatePaintedSlot(floorParent.transform, code, "Car",
                        new Vector3(x, yBase + 0.12f, zRow1), i == paintedSlotsPerRow - 1);
                }

                // Row 2: inner north (z-positive side of center aisle)
                float zRow2 = carZoneZ + aisleHalfWidth + slotDepth / 2f;   // ≈ +5.5
                for (int i = 0; i < paintedSlotsPerRow; i++)
                {
                    string code = $"{carPrefix2}-{(carRow2Start + i):D2}";
                    float x = carZoneStartX + i * slotWidth;
                    CreatePaintedSlot(floorParent.transform, code, "Car",
                        new Vector3(x, yBase + 0.12f, zRow2), i == paintedSlotsPerRow - 1);
                }
                globalPaintedIdx += paintedSlotsPerRow;

                // Rows 3 & 4 — outer bays (level 0 / B1 only)
                // Back of row1 = zRow1 - slotDepth/2 = -8.  Outer aisle z ∈ [-14, -8].
                // Row 3 center = -8 - laneWidth - slotDepth/2 = -8 - 6 - 2.5 = -16.5
                // Symmetric on north side.
                if (level == 0)
                {
                    float zRow3 = zRow1 - slotDepth / 2f - laneWidth - slotDepth / 2f; // -16.5
                    float zRow4 = zRow2 + slotDepth / 2f + laneWidth + slotDepth / 2f; // +16.5

                    int row3Start = 2 * paintedSlotsPerRow + 1; // V1-37
                    int row4Start = 3 * paintedSlotsPerRow + 1; // V1-55

                    for (int i = 0; i < paintedSlotsPerRow; i++)
                    {
                        float x = carZoneStartX + i * slotWidth;
                        CreatePaintedSlot(floorParent.transform,
                            $"V1-{(row3Start + i):D2}", "Car",
                            new Vector3(x, yBase + 0.12f, zRow3), i == paintedSlotsPerRow - 1);
                        CreatePaintedSlot(floorParent.transform,
                            $"V1-{(row4Start + i):D2}", "Car",
                            new Vector3(x, yBase + 0.12f, zRow4), i == paintedSlotsPerRow - 1);
                    }

                    // Outer aisle dashed-line markings
                    float aY = yBase + 0.11f;
                    float zAisleS = zRow1 - slotDepth / 2f - laneWidth / 2f; // -11
                    float zAisleN = zRow2 + slotDepth / 2f + laneWidth / 2f; // +11
                    int lc = Mathf.FloorToInt(platformWidth / 4f);
                    for (int i = 0; i < lc; i++)
                    {
                        float lx = -platformWidth / 2f + 3f + i * 4f;
                        var lnS = CreateQuadWorld(floorParent.transform, "AisleLine_S",
                            new Vector3(lx, aY, zAisleS), new Vector3(2f, 0.15f, 1f));
                        SetColor(lnS, YellowLine);
                        var lnN = CreateQuadWorld(floorParent.transform, "AisleLine_N",
                            new Vector3(lx, aY, zAisleN), new Vector3(2f, 0.15f, 1f));
                        SetColor(lnN, YellowLine);
                    }
                }

                // Garage slots — use G-xx (no DB zone, default Available colour)
                float garageStartX = platformWidth / 2f - 8f - garageSlotCount * garageWidth;
                for (int i = 0; i < garageSlotCount; i++)
                {
                    string code = $"G-{(globalGarageIdx + i + 1):D2}";
                    float x = garageStartX + i * garageWidth;
                    float z = -platformDepth / 2f + garageDepth / 2f + 2f;
                    CreateGarageSlot(floorParent.transform, code, "Car",
                        new Vector3(x, yBase, z));
                }
                globalGarageIdx += garageSlotCount;

                // Motorbike zone
                int motoCols = 10;
                float motoStartX = platformWidth / 2f - 8f - motoCols * motorbikeWidth;
                float motoStartZ = platformDepth / 2f - 3f;
                for (int i = 0; i < motorbikeSlotCount; i++)
                {
                    int col = i % motoCols;
                    int row = i / motoCols;
                    string code = $"{motoPrefix}-{(motoStart + i):D2}";
                    float x = motoStartX + col * motorbikeWidth;
                    float z = motoStartZ - row * motorbikeDepth;
                    CreateMotorbikeSlot(floorParent.transform, code,
                        new Vector3(x, yBase + 0.12f, z));
                }
                globalMotoIdx += motorbikeSlotCount;
            }

            // Gates at floor 0
            CreateGate(transform, "GATE-IN-01", new Vector3(platformWidth / 2f, 0f, 0f), true);
            CreateGate(transform, "GATE-OUT-01", new Vector3(-platformWidth / 2f, 0f, 0f), false);

            // Ramp between floors
            if (numberOfFloors > 1)
            {
                for (int level = 0; level < numberOfFloors - 1; level++)
                    CreateRamp(transform, level);
            }

            // Environment decoration
            CreateEnvironment();

            // Generate waypoint graph
            if (waypointGraph != null)
                GenerateWaypointGraph(allLaneNodes);
        }

        public ParkingSlot GetSlotByCode(string code)
        {
            slotRegistry.TryGetValue(code, out var slot);
            return slot;
        }

        // ─────────── Geometry Creation ───────────

        private void CreateFloorPlatform(Transform parent, float y)
        {
            // Main asphalt slab
            CreateCube(parent, "FloorPlatform",
                new Vector3(0f, y, 0f), new Vector3(platformWidth, 0.2f, platformDepth), FloorColor);

            // Perimeter curbs (raised strips around edges)
            float cH = 0.15f, cW = 0.25f, cy = y + cH / 2f + 0.1f;
            CreateCube(parent, "Curb_N", new Vector3(0f, cy, platformDepth / 2f),
                new Vector3(platformWidth, cH, cW), CurbColor);
            CreateCube(parent, "Curb_S", new Vector3(0f, cy, -platformDepth / 2f),
                new Vector3(platformWidth, cH, cW), CurbColor);
            CreateCube(parent, "Curb_E", new Vector3(platformWidth / 2f, cy, 0f),
                new Vector3(cW, cH, platformDepth), CurbColor);
            CreateCube(parent, "Curb_W", new Vector3(-platformWidth / 2f, cy, 0f),
                new Vector3(cW, cH, platformDepth), CurbColor);

            // Yellow dashed center lane lines
            float laneY = y + 0.11f;
            int lineCount = Mathf.FloorToInt(platformWidth / 4f);
            for (int i = 0; i < lineCount; i++)
            {
                float lx = -platformWidth / 2f + 3f + i * 4f;
                var ln = CreateQuadWorld(parent, "LaneLine",
                    new Vector3(lx, laneY, 0f), new Vector3(2f, 0.15f, 1f));
                SetColor(ln, YellowLine);
            }

            // Directional arrows at quarter points
            CreateDirectionalArrow(parent, new Vector3(-platformWidth / 4f, laneY, 0f));
            CreateDirectionalArrow(parent, new Vector3(platformWidth / 4f, laneY, 0f));
        }

        private void CreateDirectionalArrow(Transform parent, Vector3 pos)
        {
            var shaft = CreateQuadWorld(parent, "ArrowShaft", pos, new Vector3(1.4f, 0.25f, 1f));
            SetColor(shaft, WhiteLineColor);
            var hL = CreateQuadWorld(parent, "ArrowHL",
                pos + new Vector3(0.9f, 0f, 0.22f), new Vector3(0.7f, 0.14f, 1f));
            hL.transform.localRotation = Quaternion.Euler(90f, 30f, 0f);
            SetColor(hL, WhiteLineColor);
            var hR = CreateQuadWorld(parent, "ArrowHR",
                pos + new Vector3(0.9f, 0f, -0.22f), new Vector3(0.7f, 0.14f, 1f));
            hR.transform.localRotation = Quaternion.Euler(90f, -30f, 0f);
            SetColor(hR, WhiteLineColor);
        }

        private void CreatePillars(Transform parent, float y, int numCarRows = 2)
        {
            float aisleHalf = laneWidth / 2f;

            // Z lines: behind inner rows only (keeps aisles clear)
            float behindInner = aisleHalf + slotDepth + 1.5f; // 9.5
            float[] zLines = { -behindInner, behindInner }; // skip center — keeps driving lane clear

            // X positions: every 6 slots + platform edges
            float carStart = -platformWidth / 2f + 5f;
            int stepSlots = 6;
            var xList = new System.Collections.Generic.List<float>();
            xList.Add(-platformWidth / 2f + 1.5f);
            for (int i = stepSlots; i < paintedSlotsPerRow; i += stepSlots)
            {
                float bx = carStart + i * slotWidth - slotWidth * 0.5f;
                xList.Add(bx);
            }
            xList.Add(platformWidth / 2f - 1.5f);

            foreach (float pz in zLines)
            {
                foreach (float px in xList)
                {
                    CreateCube(parent, "Pillar",
                        new Vector3(px, y + floorHeight / 2f, pz),
                        new Vector3(0.4f, floorHeight, 0.4f), PillarColor);
                }
            }
        }

        private void CreatePaintedSlot(Transform parent, string code, string vType, Vector3 pos, bool isLastInRow = false)
        {
            var slotGo = new GameObject($"Slot_{code}");
            slotGo.transform.SetParent(parent);
            slotGo.transform.position = pos;

            // Slot floor indicator (colored by ParkingSlot status) — MUST be first child
            var floorGo = GameObject.CreatePrimitive(PrimitiveType.Quad);
            floorGo.name = "SlotFloor";
            floorGo.transform.SetParent(slotGo.transform);
            floorGo.transform.localPosition = new Vector3(0f, 0.01f, 0f);
            floorGo.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
            floorGo.transform.localScale = new Vector3(slotWidth * 0.92f, slotDepth * 0.92f, 1f);
            var urpShader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            var floorMat = new Material(urpShader);
            floorMat.SetFloat("_Surface", 1f);
            floorMat.SetFloat("_Blend", 0f);
            floorMat.SetOverrideTag("RenderType", "Transparent");
            floorMat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
            floorMat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            floorMat.SetInt("_ZWrite", 0);
            floorMat.renderQueue = 3000;
            floorMat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            Color initialColor = new Color(0.2f, 0.8f, 0.2f, 0.55f);
            floorMat.color = initialColor;
            if (floorMat.HasProperty("_BaseColor")) floorMat.SetColor("_BaseColor", initialColor);
            floorGo.GetComponent<Renderer>().sharedMaterial = floorMat;
            Object.Destroy(floorGo.GetComponent<MeshCollider>());

            // Shared divider lines: only left side + top/bottom per slot
            // Adjacent slots share borders (left of slot N+1 = right of slot N)
            float hw = slotWidth * 0.5f, hd = slotDepth * 0.5f;
            float bW = 0.08f;   // thin line width
            float bH = 0.02f;   // flat
            float yOff = bH * 0.5f + 0.005f;

            // West divider (every slot gets its left edge)
            CreateCube(slotGo.transform, "Divider_W",
                pos + new Vector3(-hw, yOff, 0f),
                new Vector3(bW, bH, slotDepth), OrangeLineColor);

            // If last slot in row, also draw East edge
            if (isLastInRow)
            {
                CreateCube(slotGo.transform, "Divider_E",
                    pos + new Vector3(hw, yOff, 0f),
                    new Vector3(bW, bH, slotDepth), OrangeLineColor);
            }

            // North/South horizontal cap lines
            CreateCube(slotGo.transform, "Cap_N",
                pos + new Vector3(0f, yOff, hd),
                new Vector3(slotWidth, bH, bW), OrangeLineColor);
            CreateCube(slotGo.transform, "Cap_S",
                pos + new Vector3(0f, yOff, -hd),
                new Vector3(slotWidth, bH, bW), OrangeLineColor);

            // Mini barrier gate at slot entrance (south side)
            CreateCube(slotGo.transform, "SlotBarrierPost",
                pos + new Vector3(-hw + 0.15f, 0.15f, -hd),
                new Vector3(0.1f, 0.3f, 0.1f), BlackColor);
            CreateCube(slotGo.transform, "SlotBarrierArm",
                pos + new Vector3(0f, 0.28f, -hd),
                new Vector3(slotWidth * 0.8f, 0.05f, 0.05f), SignRed);

            var slot = slotGo.AddComponent<ParkingSlot>();
            slot.Initialize(code, vType);
            slotRegistry[code] = slot;
            CreateSlotLabel(slotGo.transform, code, pos.y + 0.05f);
        }

        private void CreateGarageSlot(Transform parent, string code, string vType, Vector3 pos)
        {
            var slotGo = new GameObject($"Slot_{code}");
            slotGo.transform.SetParent(parent);
            slotGo.transform.position = pos;
            float wt = 0.1f, hy = garageHeight / 2f;
            Color sideColor = new Color(WallColor.r * 0.95f, WallColor.g * 0.92f, WallColor.b * 0.90f);
            CreateCubeLocal(slotGo.transform, "Wall_Back",
                new Vector3(0f, hy, -garageDepth / 2f), new Vector3(garageWidth, garageHeight, wt), WallColor);
            CreateCubeLocal(slotGo.transform, "Wall_Left",
                new Vector3(-garageWidth / 2f, hy, 0f), new Vector3(wt, garageHeight, garageDepth), sideColor);
            CreateCubeLocal(slotGo.transform, "Wall_Right",
                new Vector3(garageWidth / 2f, hy, 0f), new Vector3(wt, garageHeight, garageDepth), sideColor);
            CreateQuadLocal(slotGo.transform, "FloorMark",
                new Vector3(0f, 0.02f, 0f), new Vector3(garageWidth * 0.9f, garageDepth * 0.9f, 1f));
            // Light fixture sphere on back wall
            var light = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            light.name = "LightFixture";
            light.transform.SetParent(slotGo.transform);
            light.transform.localPosition = new Vector3(0f, garageHeight - 0.3f, -garageDepth / 2f + 0.15f);
            light.transform.localScale = new Vector3(0.2f, 0.2f, 0.2f);
            SetEmissiveColor(light, LightEmission, LightEmission, 1.5f);
            var slot = slotGo.AddComponent<ParkingSlot>();
            slot.Initialize(code, vType);
            slotRegistry[code] = slot;
            CreateSlotLabel(slotGo.transform, code, pos.y + garageHeight + 0.3f);
        }

        private void CreateMotorbikeSlot(Transform parent, string code, Vector3 pos)
        {
            var slotGo = new GameObject($"Slot_{code}");
            slotGo.transform.SetParent(parent);
            slotGo.transform.position = pos;
            CreateQuadLocal(slotGo.transform, "SlotMarking", Vector3.zero,
                new Vector3(motorbikeWidth * 0.9f, motorbikeDepth * 0.9f, 1f));
            SetColor(slotGo.transform.GetChild(0).gameObject, WhiteLineColor);
            var slot = slotGo.AddComponent<ParkingSlot>();
            slot.Initialize(code, "Motorbike");
            slotRegistry[code] = slot;
            CreateSlotLabel(slotGo.transform, code, pos.y + 0.05f, 1.2f);
        }

        private void CreateSlotLabel(Transform parent, string code, float yOffset, float fontSize = 2.2f)
        {
            var labelGo = new GameObject("Label");
            labelGo.transform.SetParent(parent);
            labelGo.transform.localPosition = new Vector3(0f, yOffset - parent.position.y + 0.15f, 0f);
            labelGo.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);

            var tmp = labelGo.AddComponent<TMPro.TextMeshPro>();
            tmp.text = code;
            tmp.fontSize = fontSize;
            tmp.fontStyle = TMPro.FontStyles.Bold;
            tmp.alignment = TMPro.TextAlignmentOptions.Center;
            tmp.color = Color.white;
            tmp.outlineWidth = 0.2f;
            tmp.outlineColor = new Color32(0, 0, 0, 220);

            var rt = tmp.GetComponent<RectTransform>();
            rt.sizeDelta = new Vector2(4f, 2f);
        }

        private void CreateGate(Transform parent, string gateId, Vector3 pos, bool isEntry)
        {
            var g = new GameObject($"Gate_{gateId}");
            g.transform.SetParent(parent);
            g.transform.position = pos;

            // Direction multiplier: entry faces inward (-X), exit faces outward (+X)
            float dir = isEntry ? 1f : -1f;

            // === 1. Gate Posts (narrower lane: 3.5m between posts) ===
            CreateCubeLocal(g.transform, "GatePost_L",
                new Vector3(0f, 1.5f, -1.75f), new Vector3(0.35f, 3f, 0.35f), GateColor);
            CreateCubeLocal(g.transform, "GatePost_R",
                new Vector3(0f, 1.5f, 1.75f), new Vector3(0.35f, 3f, 0.35f), GateColor);

            // === 2. Barrier Arm (pivot + arm child for BarrierController animation) ===
            var armPivot = new GameObject($"BarrierArmPivot_{gateId}");
            armPivot.transform.SetParent(g.transform);
            armPivot.transform.localPosition = new Vector3(0f, 2.6f, -1.6f); // at left post

            CreateCubeLocalRet(armPivot.transform, "ArmBar",
                new Vector3(0f, 0f, 1.6f), new Vector3(0.08f, 0.08f, 3.2f),
                isEntry ? new Color(0f, 0.7f, 0f) : new Color(0.8f, 0f, 0f));

            // Barrier arm pivot post (visual)
            CreateCubeLocal(g.transform, "ArmPivot",
                new Vector3(0f, 1.5f, -1.6f), new Vector3(0.2f, 2.2f, 0.2f), BlackColor);

            // === 3. Overhead Canopy (covers gate + stopping zone) ===
            CreateCubeLocal(g.transform, "GateCanopy",
                new Vector3(dir * 2f, 3.5f, 0f), new Vector3(7f, 0.12f, 5f), CeilingColor);

            // Canopy support pillars (4 corners)
            float canopyX = dir * 2f;
            CreateCubeLocal(g.transform, "CanopyPillar_FL",
                new Vector3(canopyX - 3.3f, 1.75f, -2.3f), new Vector3(0.15f, 3.5f, 0.15f), PillarColor);
            CreateCubeLocal(g.transform, "CanopyPillar_FR",
                new Vector3(canopyX - 3.3f, 1.75f, 2.3f), new Vector3(0.15f, 3.5f, 0.15f), PillarColor);
            CreateCubeLocal(g.transform, "CanopyPillar_BL",
                new Vector3(canopyX + 3.3f, 1.75f, -2.3f), new Vector3(0.15f, 3.5f, 0.15f), PillarColor);
            CreateCubeLocal(g.transform, "CanopyPillar_BR",
                new Vector3(canopyX + 3.3f, 1.75f, 2.3f), new Vector3(0.15f, 3.5f, 0.15f), PillarColor);

            // === 4. Vehicle Stopping Bay (3m outside barrier) ===
            float bayX = dir * 3.5f;

            // Stop line (thick white line on ground)
            CreateCubeLocal(g.transform, "StopLine",
                new Vector3(bayX - dir * 1.5f, 0.02f, 0f),
                new Vector3(0.2f, 0.02f, 3f), WhiteLineColor);

            // Bay outline (dashed lane marking on ground)
            for (int i = 0; i < 3; i++)
            {
                float dashX = bayX + dir * (i * 1.2f - 1.2f);
                CreateCubeLocal(g.transform, "BayDash_L",
                    new Vector3(dashX, 0.015f, -1.6f),
                    new Vector3(0.8f, 0.02f, 0.1f), WhiteLineColor);
                CreateCubeLocal(g.transform, "BayDash_R",
                    new Vector3(dashX, 0.015f, 1.6f),
                    new Vector3(0.8f, 0.02f, 0.1f), WhiteLineColor);
            }

            // "STOP" ground text
            var stopLabel = new GameObject("StopText");
            stopLabel.transform.SetParent(g.transform);
            stopLabel.transform.localPosition = new Vector3(bayX, 0.025f, 0f);
            stopLabel.transform.localRotation = Quaternion.Euler(90f, isEntry ? -90f : 90f, 0f);
            var stopTmp = stopLabel.AddComponent<TMPro.TextMeshPro>();
            stopTmp.text = "STOP";
            stopTmp.fontSize = 3f;
            stopTmp.fontStyle = TMPro.FontStyles.Bold;
            stopTmp.alignment = TMPro.TextAlignmentOptions.Center;
            stopTmp.color = WhiteLineColor;
            stopTmp.outlineWidth = 0.2f;
            stopTmp.outlineColor = new Color32(0, 0, 0, 200);
            var stopRt = stopTmp.GetComponent<RectTransform>();
            stopRt.sizeDelta = new Vector2(3f, 1.5f);

            // === 5. QR Scanner Kiosk (driver side) ===
            float kioskZ = isEntry ? -2.2f : 2.2f;

            // Kiosk pole
            CreateCubeLocal(g.transform, "KioskPole",
                new Vector3(bayX, 0.55f, kioskZ), new Vector3(0.12f, 1.1f, 0.12f), GateColor);

            // Kiosk head (screen/terminal)
            CreateCubeLocalRet(g.transform, "KioskScreen",
                new Vector3(bayX, 1.15f, kioskZ), new Vector3(0.4f, 0.5f, 0.3f), BlackColor);

            // Kiosk screen face (green/illuminated)
            CreateCubeLocal(g.transform, "KioskScreenFace",
                new Vector3(bayX, 1.15f, kioskZ + (isEntry ? 0.16f : -0.16f)),
                new Vector3(0.32f, 0.42f, 0.02f), new Color(0.1f, 0.4f, 0.2f));

            // QR label
            var qrLabel = new GameObject("QRLabel");
            qrLabel.transform.SetParent(g.transform);
            qrLabel.transform.localPosition = new Vector3(bayX, 1.5f, kioskZ);
            var qrTmp = qrLabel.AddComponent<TMPro.TextMeshPro>();
            qrTmp.text = "QR SCAN";
            qrTmp.fontSize = 1f;
            qrTmp.alignment = TMPro.TextAlignmentOptions.Center;
            qrTmp.color = Color.white;
            qrTmp.fontStyle = TMPro.FontStyles.Bold;
            var qrRt = qrTmp.GetComponent<RectTransform>();
            qrRt.sizeDelta = new Vector2(1.5f, 0.5f);

            // === 6. ANPR Camera (License Plate Recognition) ===
            float camZ = isEntry ? 1.8f : -1.8f;

            // Camera pole
            var camPole = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            camPole.name = "ANPRPole";
            camPole.transform.SetParent(g.transform);
            camPole.transform.localPosition = new Vector3(bayX - dir * 1f, 1.5f, camZ);
            camPole.transform.localScale = new Vector3(0.08f, 1.5f, 0.08f);
            SetColor(camPole, PillarColor);

            // Camera housing (angled box)
            var camHousing = CreateCubeLocalRet(g.transform, "ANPRCamera",
                new Vector3(bayX - dir * 1f, 3.1f, camZ),
                new Vector3(0.35f, 0.2f, 0.25f), BlackColor);
            camHousing.transform.localRotation = Quaternion.Euler(30f, isEntry ? -90f : 90f, 0f);

            // Camera lens (small cylinder)
            var camLens = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            camLens.name = "ANPRLens";
            camLens.transform.SetParent(g.transform);
            camLens.transform.localPosition = new Vector3(bayX - dir * 1.15f, 3.1f, camZ);
            camLens.transform.localScale = new Vector3(0.1f, 0.06f, 0.1f);
            camLens.transform.localRotation = Quaternion.Euler(0f, 0f, 90f);
            SetColor(camLens, new Color(0.2f, 0.2f, 0.3f));

            // Camera indicator light (red LED)
            var camLight = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            camLight.name = "CamLED";
            camLight.transform.SetParent(g.transform);
            camLight.transform.localPosition = new Vector3(bayX - dir * 1f, 3.25f, camZ);
            camLight.transform.localScale = new Vector3(0.06f, 0.06f, 0.06f);
            SetEmissiveColor(camLight, new Color(0.5f, 0f, 0f), Color.red, 2f);

            // === 7. Traffic Light ===
            float tlZ = isEntry ? -1.75f : 1.75f;

            // Traffic light housing
            CreateCubeLocal(g.transform, "TrafficLightBox",
                new Vector3(0f, 3.0f, tlZ), new Vector3(0.25f, 0.6f, 0.25f), BlackColor);

            // Red light
            var redLight = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            redLight.name = "RedLight";
            redLight.transform.SetParent(g.transform);
            redLight.transform.localPosition = new Vector3(0f, 3.15f, tlZ);
            redLight.transform.localScale = new Vector3(0.12f, 0.12f, 0.12f);
            SetEmissiveColor(redLight, new Color(0.3f, 0f, 0f), SignRed, 1.5f);

            // Green light
            var greenLight = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            greenLight.name = "GreenLight";
            greenLight.transform.SetParent(g.transform);
            greenLight.transform.localPosition = new Vector3(0f, 2.9f, tlZ);
            greenLight.transform.localScale = new Vector3(0.12f, 0.12f, 0.12f);
            SetEmissiveColor(greenLight, new Color(0f, 0.08f, 0f), new Color(0f, 0.2f, 0f), 0.5f);

            // === 8. Height Limit Bar ===
            CreateCubeLocal(g.transform, "HeightBar",
                new Vector3(0f, 2.9f, 0f), new Vector3(0.06f, 0.06f, 3.5f), YellowLine);
            CreateCubeLocal(g.transform, "HeightSign",
                new Vector3(0f, 2.9f, -2f), new Vector3(0.8f, 0.35f, 0.05f), BlackColor);
            var hLbl = new GameObject("HeightLabel");
            hLbl.transform.SetParent(g.transform);
            hLbl.transform.localPosition = new Vector3(0f, 2.9f, -2.03f);
            var hTmp = hLbl.AddComponent<TMPro.TextMeshPro>();
            hTmp.text = "2.1m";
            hTmp.fontSize = 1.2f;
            hTmp.alignment = TMPro.TextAlignmentOptions.Center;
            hTmp.color = YellowLine;
            var hRt = hTmp.GetComponent<RectTransform>();
            hRt.sizeDelta = new Vector2(1f, 0.5f);

            // === 9. LED Sign (ENTRY/EXIT) ===
            Color signBase = isEntry ? new Color(0f, 0.15f, 0f) : new Color(0.15f, 0f, 0f);
            Color signEmit = isEntry ? SignGreen : SignRed;
            var signGo = CreateCubeLocalRet(g.transform, "GateSign",
                new Vector3(dir * 0.5f, 3.8f, 0f), new Vector3(2.5f, 0.6f, 0.05f), signBase);
            SetEmissiveColor(signGo, signBase, signEmit, 2f);
            var lbl = new GameObject("GateLabel");
            lbl.transform.SetParent(g.transform);
            lbl.transform.localPosition = new Vector3(dir * 0.5f, 3.8f, -0.03f);
            var tmp = lbl.AddComponent<TMPro.TextMeshPro>();
            tmp.text = isEntry ? "ENTRY" : "EXIT";
            tmp.fontSize = 2f;
            tmp.alignment = TMPro.TextAlignmentOptions.Center;
            tmp.color = Color.white;
            tmp.fontStyle = TMPro.FontStyles.Bold;
            var lblRt = tmp.GetComponent<RectTransform>();
            lblRt.sizeDelta = new Vector2(3f, 1f);

            // === 10. Speed Bumps (on approach road OUTSIDE gate) ===
            for (int i = 0; i < 3; i++)
            {
                Color bCol = (i % 2 == 0) ? YellowLine : BlackColor;
                CreateCubeLocal(g.transform, "SpeedBump",
                    new Vector3(dir * (5f + i * 0.5f), 0.04f, 0f),
                    new Vector3(0.18f, 0.08f, 3f), bCol);
            }

            // === 11. Lane Guide Bollards ===
            for (int i = 0; i < 4; i++)
            {
                float bx = dir * (2f + i * 1.5f);
                // Left bollard
                var bollardL = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                bollardL.name = "BollardL";
                bollardL.transform.SetParent(g.transform);
                bollardL.transform.localPosition = new Vector3(bx, 0.35f, -2f);
                bollardL.transform.localScale = new Vector3(0.12f, 0.35f, 0.12f);
                SetColor(bollardL, YellowLine);

                // Right bollard
                var bollardR = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                bollardR.name = "BollardR";
                bollardR.transform.SetParent(g.transform);
                bollardR.transform.localPosition = new Vector3(bx, 0.35f, 2f);
                bollardR.transform.localScale = new Vector3(0.12f, 0.35f, 0.12f);
                SetColor(bollardR, YellowLine);
            }

            // === 12. Ticket Booth (security booth) ===
            float boothZ = isEntry ? -3f : 3f;
            CreateCubeLocal(g.transform, "TicketBooth",
                new Vector3(dir * 1.5f, 0.9f, boothZ), new Vector3(1.5f, 1.8f, 1.5f), GateColor);
            CreateCubeLocal(g.transform, "BoothRoof",
                new Vector3(dir * 1.5f, 1.9f, boothZ), new Vector3(1.8f, 0.08f, 1.8f), CeilingColor);
            // Booth window
            CreateCubeLocal(g.transform, "BoothWindow",
                new Vector3(dir * 1.5f, 1.1f, boothZ + (isEntry ? 0.76f : -0.76f)),
                new Vector3(0.8f, 0.5f, 0.02f), new Color(0.6f, 0.85f, 1f, 0.5f));
        }

        private void CreateRamp(Transform parent, int fromLevel)
        {
            float yB = fromLevel * floorHeight + 0.1f, yT = (fromLevel + 1) * floorHeight;
            float rLen = 12f, rW = 4f, rZ = -platformDepth / 2f + 3f;
            var rampGo = new GameObject($"Ramp_{fromLevel + 1}_to_{fromLevel + 2}");
            rampGo.transform.SetParent(parent);
            float hDiff = yT - yB;
            float aLen = Mathf.Sqrt(rLen * rLen + hDiff * hDiff);
            float angle = Mathf.Atan2(hDiff, rLen) * Mathf.Rad2Deg;
            // Ramp surface
            var surf = CreateCube(rampGo.transform, "RampSurface",
                new Vector3(0f, (yB + yT) / 2f, rZ), new Vector3(rW, 0.15f, aLen), RampColor);
            surf.transform.localRotation = Quaternion.Euler(angle, 0f, 0f);
            // Side walls (thicker than old rails)
            for (int s = -1; s <= 1; s += 2)
            {
                var wall = CreateCube(rampGo.transform, s < 0 ? "Wall_L" : "Wall_R",
                    new Vector3(s * rW / 2f, (yB + yT) / 2f + 0.3f, rZ),
                    new Vector3(0.2f, 0.8f, aLen), CurbColor);
                wall.transform.localRotation = Quaternion.Euler(angle, 0f, 0f);
            }
            // Anti-slip yellow strips across ramp
            int stripCount = 8;
            for (int i = 0; i < stripCount; i++)
            {
                float t = (i + 1f) / (stripCount + 1f);
                float sy = Mathf.Lerp(yB, yT, t) + 0.09f;
                float szo = rZ - aLen / 2f + t * aLen;
                var strip = CreateCube(rampGo.transform, "AntiSlip",
                    new Vector3(0f, sy, szo), new Vector3(rW * 0.85f, 0.02f, 0.15f), YellowLine);
                strip.transform.localRotation = Quaternion.Euler(angle, 0f, 0f);
            }
            // Chevron arrow at midpoint
            float midY = (yB + yT) / 2f + 0.12f;
            var chev = CreateQuadWorld(rampGo.transform, "Chevron",
                new Vector3(0f, midY, rZ), new Vector3(1f, 0.5f, 1f));
            chev.transform.localRotation = Quaternion.Euler(90f + angle, 0f, 0f);
            SetColor(chev, WhiteLineColor);
        }

        private void CreateEnvironment()
        {
            var env = new GameObject("Environment");
            env.transform.SetParent(transform);
            env.transform.localPosition = Vector3.zero;
            // Ground plane (grass/earth below structure)
            CreateCube(env.transform, "GroundPlane",
                new Vector3(0f, -0.15f, 0f),
                new Vector3(platformWidth + 30f, 0.1f, platformDepth + 30f), GroundColor);
            // Perimeter walls (N/S sides)
            float totalH = numberOfFloors * floorHeight;
            float wt = 0.15f;
            CreateCube(env.transform, "PerimWall_N",
                new Vector3(0f, totalH / 2f, platformDepth / 2f + wt / 2f),
                new Vector3(platformWidth, totalH, wt), WallColor);
            CreateCube(env.transform, "PerimWall_S",
                new Vector3(0f, totalH / 2f, -platformDepth / 2f - wt / 2f),
                new Vector3(platformWidth, totalH, wt), WallColor);
            // Ceiling slabs between floors (not above top floor)
            for (int level = 0; level < numberOfFloors - 1; level++)
            {
                float cy = (level + 1) * floorHeight - 0.05f;
                CreateCube(env.transform, $"Ceiling_{level + 1}",
                    new Vector3(0f, cy, 0f),
                    new Vector3(platformWidth - 0.5f, 0.1f, platformDepth - 0.5f), CeilingColor);
            }
            // Light posts at 4 corners
            float lightH = totalH + 1f;
            float lpx = platformWidth / 2f - 1f, lpz = platformDepth / 2f - 1f;
            float[][] lCorners = {
                new[]{-lpx, -lpz}, new[]{lpx, -lpz},
                new[]{-lpx, lpz}, new[]{lpx, lpz}
            };
            foreach (var lc in lCorners)
            {
                var pole = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
                pole.name = "LightPole";
                pole.transform.SetParent(env.transform);
                pole.transform.position = new Vector3(lc[0], lightH / 2f, lc[1]);
                pole.transform.localScale = new Vector3(0.12f, lightH / 2f, 0.12f);
                SetColor(pole, PillarColor);
                var head = GameObject.CreatePrimitive(PrimitiveType.Cube);
                head.name = "LightHead";
                head.transform.SetParent(env.transform);
                head.transform.position = new Vector3(lc[0], lightH, lc[1]);
                head.transform.localScale = new Vector3(0.5f, 0.25f, 0.5f);
                SetEmissiveColor(head, LightEmission, LightEmission, 2f);
            }
            // Entry/exit roads leading to gates
            float roadLen = 15f;
            CreateCube(env.transform, "Road_Entry",
                new Vector3(platformWidth / 2f + roadLen / 2f, -0.05f, 0f),
                new Vector3(roadLen, 0.1f, 5f), RoadColor);
            CreateCube(env.transform, "Road_Exit",
                new Vector3(-platformWidth / 2f - roadLen / 2f, -0.05f, 0f),
                new Vector3(roadLen, 0.1f, 5f), RoadColor);
            // Road center dashes
            for (int i = 0; i < 5; i++)
            {
                float dx = 1.5f + i * 3f;
                CreateCube(env.transform, "RoadDash",
                    new Vector3(platformWidth / 2f + dx, -0.01f, 0f),
                    new Vector3(1.5f, 0.02f, 0.12f), YellowLine);
                CreateCube(env.transform, "RoadDash",
                    new Vector3(-platformWidth / 2f - dx, -0.01f, 0f),
                    new Vector3(1.5f, 0.02f, 0.12f), YellowLine);
            }
        }

        // ─────────── Utilities ───────────

        private List<WaypointNode> CreateLaneWaypoints(float y, Transform parent)
        {
            var nodes = new List<WaypointNode>();
            float sx = -platformWidth / 2f + 3f, ex = platformWidth / 2f - 3f;
            int n = 8;
            float step = (ex - sx) / (n - 1);
            for (int i = 0; i < n; i++)
            {
                var type = (i == 0 || i == n - 1) ? WaypointNode.NodeType.Intersection : WaypointNode.NodeType.Lane;
                nodes.Add(CreateWaypointNode(parent, new Vector3(sx + i * step, y + 0.1f, 0f), type, null));
            }
            return nodes;
        }

        private void GenerateWaypointGraph(List<List<WaypointNode>> allLaneNodes)
        {
            // Gate waypoints at stopping bay position (3.5m outside gate structure)
            // so vehicles stop AT the bay, not inside the gate
            var entryNode = CreateWaypointNode(transform, new Vector3(platformWidth / 2f + 3.5f, 0.1f, 0f),
                WaypointNode.NodeType.Gate, "GATE-IN-01");
            var exitNode = CreateWaypointNode(transform, new Vector3(-platformWidth / 2f - 3.5f, 0.1f, 0f),
                WaypointNode.NodeType.Gate, "GATE-OUT-01");

            if (allLaneNodes.Count > 0 && allLaneNodes[0].Count > 0)
            {
                var f0 = allLaneNodes[0];
                waypointGraph.Connect(entryNode, f0[f0.Count - 1]);
                waypointGraph.Connect(exitNode, f0[0]);
            }

            foreach (var lane in allLaneNodes)
                for (int i = 0; i < lane.Count - 1; i++)
                    waypointGraph.Connect(lane[i], lane[i + 1]);

            foreach (var kvp in slotRegistry)
            {
                var slot = kvp.Value;
                if (slot == null) continue;
                var ep = slot.transform.position + new Vector3(0f, 0.1f, 0f);
                ep.z += (slot.transform.position.z < 0f ? 1f : -1f) * (slotDepth / 2f + 1f);
                var sn = CreateWaypointNode(slot.transform.parent, ep, WaypointNode.NodeType.SlotEntrance, kvp.Key);
                var near = waypointGraph.GetNearestLaneNode(ep);
                if (near != null)
                    waypointGraph.Connect(sn, near);
            }

            if (allLaneNodes.Count > 1)
            {
                float rZ = -platformDepth / 2f - 1f;
                for (int f = 0; f < allLaneNodes.Count - 1; f++)
                {
                    float yB = f * floorHeight + 0.1f, yT = (f + 1) * floorHeight + 0.1f;
                    var bn = CreateWaypointNode(transform, new Vector3(0f, yB, rZ), WaypointNode.NodeType.Ramp, null);
                    var tn = CreateWaypointNode(transform, new Vector3(0f, yT, rZ), WaypointNode.NodeType.Ramp, null);
                    waypointGraph.Connect(bn, tn);
                    ConnectNearest(bn, allLaneNodes[f]);
                    ConnectNearest(tn, allLaneNodes[f + 1]);
                }
            }
        }

        private void ConnectNearest(WaypointNode node, List<WaypointNode> laneNodes)
        {
            WaypointNode best = null; float min = float.MaxValue;
            foreach (var ln in laneNodes)
            {
                float d = Vector3.SqrMagnitude(ln.transform.position - node.transform.position);
                if (d < min) { min = d; best = ln; }
            }
            if (best != null) waypointGraph.Connect(node, best);
        }

        private WaypointNode CreateWaypointNode(Transform parent, Vector3 pos,
            WaypointNode.NodeType type, string slotCode)
        {
            var go = new GameObject($"WP_{type}_{slotCode ?? nextWpId().ToString()}");
            go.transform.SetParent(parent);
            go.transform.position = pos;

            var node = go.AddComponent<WaypointNode>();
            node.nodeType = type;
            node.associatedSlotCode = slotCode;
            waypointGraph.RegisterNode(node);

            return node;
        }

        private int _wpCounter;
        private int nextWpId() => _wpCounter++;

        // ─────────── Geometry Helpers ───────────

        private void ClearExisting()
        {
            for (int i = transform.childCount - 1; i >= 0; i--)
            {
                var child = transform.GetChild(i);
                if (Application.isPlaying)
                    Destroy(child.gameObject);
                else
                    DestroyImmediate(child.gameObject);
            }
        }

        private static GameObject CreateCube(Transform parent, string name, Vector3 worldPos, Vector3 scale, Color color)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(parent);
            go.transform.position = worldPos;
            go.transform.localScale = scale;
            SetColor(go, color);
            return go;
        }

        private static void CreateCubeLocal(Transform parent, string name, Vector3 localPos, Vector3 scale, Color color)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(parent);
            go.transform.localPosition = localPos;
            go.transform.localScale = scale;
            SetColor(go, color);
        }

        private static GameObject CreateCubeLocalRet(Transform parent, string name,
            Vector3 localPos, Vector3 scale, Color color)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(parent);
            go.transform.localPosition = localPos;
            go.transform.localScale = scale;
            SetColor(go, color);
            return go;
        }

        private static void CreateQuadLocal(Transform parent, string name, Vector3 localPos, Vector3 scale)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Quad);
            go.name = name;
            go.transform.SetParent(parent);
            go.transform.localPosition = localPos;
            go.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
            go.transform.localScale = scale;
        }

        private static GameObject CreateQuadWorld(Transform parent, string name, Vector3 worldPos, Vector3 scale)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Quad);
            go.name = name;
            go.transform.SetParent(parent);
            go.transform.position = worldPos;
            go.transform.localRotation = Quaternion.Euler(90f, 0f, 0f);
            go.transform.localScale = scale;
            return go;
        }

        private static void SetColor(GameObject go, Color color)
        {
            var r = go.GetComponent<Renderer>();
            if (r == null) return;
            var mat = r.material;
            if (mat.HasProperty("_BaseColor")) mat.SetColor("_BaseColor", color);
            else mat.color = color;
        }

        private static void SetEmissiveColor(GameObject go, Color baseColor, Color emissiveColor, float intensity = 2f)
        {
            var r = go.GetComponent<Renderer>();
            if (r == null) return;
            var mat = r.material;
            mat.color = baseColor;
            mat.EnableKeyword("_EMISSION");
            mat.SetColor("_EmissionColor", emissiveColor * intensity);
        }
    }
}
