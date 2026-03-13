import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  MapPin,
  Navigation,
  ChevronDown,
  Car,
  Volume2,
  VolumeX,
  CalendarPlus,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { DirectionsPanel } from "@/components/map/DirectionsPanel";
import type { DirectionStep } from "@/types/parking";
import { useBooking, useParking } from "@/hooks";
import { useNavigate } from "react-router-dom";
import { parkingApi } from "@/services/api/parking.api";
import {
  findPathToSlot,
  type GraphNode,
  type DirectionInstruction,
} from "@/lib/dijkstra";
import type { ParkingSlot } from "@/store/slices/parkingSlice";

// ---- Types for map rendering ----
interface MapZone {
  id: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

interface MapSlot {
  id: string;
  code: string;
  isAvailable: boolean;
  x: number;
  y: number;
  zoneId: string;
}

interface MapGate {
  id: string;
  name: string;
  x: number;
  y: number;
}

interface CurrentBookingType {
  licensePlate: string;
  vehicleType: "Car" | "Motorbike";
  zone: string;
  slot: string;
  slotId: string;
  floor: number;
}

// ---- Layout helpers ----
const ZONE_WIDTH = 380;
const ZONE_HEIGHT = 280;
const ZONE_GAP = 60;
const ZONE_START_Y = 100;
const SLOT_W = 48;
const SLOT_H = 26;
const SLOTS_PER_ROW = 6; // 3 left + 3 right of center aisle
const SLOT_GAP_Y = 38;
const SLOT_START_Y = 70; // relative to zone y

// Center-aisle parking layout:
// [col0][col1][col2] | AISLE | [col3][col4][col5]
const LEFT_COL_START = 12; // zone.x + 12
const LEFT_COL_GAP = 56; // spacing between left-side slot columns
const AISLE_CENTER_OFFSET = 190; // zone.x + 190 = center of driving aisle
const RIGHT_COL_START = 210; // zone.x + 210
const RIGHT_COL_GAP = 56; // spacing between right-side slot columns

const GATE_POS = { x: 400, y: -30 };

/** Get slot X position based on column index (0-5) */
function getSlotX(zoneX: number, col: number): number {
  if (col < 3) {
    // Left side of aisle
    return zoneX + LEFT_COL_START + col * LEFT_COL_GAP;
  } else {
    // Right side of aisle
    return zoneX + RIGHT_COL_START + (col - 3) * RIGHT_COL_GAP;
  }
}

// --- Demo/fallback data when no real booking exists ---
function generateDemoData() {
  const demoZones = [
    { id: "V1", name: "Zone V1" },
    { id: "V2", name: "Zone V2" },
  ];
  const mapZones = layoutZones(demoZones);

  // Generate 20 slots per zone
  const demoSlotList: Array<{
    id: string;
    code: string;
    zone: string;
    zoneId: string;
    status: string;
  }> = [];
  for (const z of demoZones) {
    for (let i = 1; i <= 20; i++) {
      demoSlotList.push({
        id: `${z.id}-${String(i).padStart(2, "0")}`,
        code: `${z.id}-${String(i).padStart(2, "0")}`,
        zone: z.id,
        zoneId: z.id,
        status: Math.random() > 0.4 ? "available" : "occupied",
      });
    }
  }
  // Force target slot to be occupied (booked by user)
  const targetIdx = demoSlotList.findIndex((s) => s.id === "V1-16");
  if (targetIdx >= 0) demoSlotList[targetIdx].status = "occupied";

  const mapSlots = layoutSlots(demoSlotList, mapZones);

  const booking: CurrentBookingType = {
    licensePlate: "52AV-57482",
    vehicleType: "Car",
    zone: "Zone V1",
    slot: "V1-16",
    slotId: "V1-16",
    floor: 1,
  };

  return { demoZones, mapZones, demoSlotList, mapSlots, booking };
}

function layoutZones(zoneList: Array<{ id: string; name: string }>): MapZone[] {
  return zoneList.map((z, idx) => ({
    id: z.id,
    name: z.name,
    x: idx * (ZONE_WIDTH + ZONE_GAP) + 40, // offset so gate road fits
    y: ZONE_START_Y,
    width: ZONE_WIDTH,
    height: ZONE_HEIGHT,
  }));
}

function layoutSlots(
  slotList: Array<{
    id: string;
    code: string;
    zone?: string;
    zoneId?: string;
    status: string;
  }>,
  mapZones: MapZone[],
): MapSlot[] {
  // Group by zone
  const byZone: Record<string, typeof slotList> = {};
  for (const s of slotList) {
    const zId = s.zone || s.zoneId || "";
    if (!byZone[zId]) byZone[zId] = [];
    byZone[zId].push(s);
  }

  const result: MapSlot[] = [];
  for (const zone of mapZones) {
    const zoneSlots = byZone[zone.id] || [];
    zoneSlots.forEach((s, idx) => {
      const row = Math.floor(idx / SLOTS_PER_ROW);
      const col = idx % SLOTS_PER_ROW;
      result.push({
        id: s.id,
        code: s.code,
        isAvailable: s.status === "available",
        x: getSlotX(zone.x, col),
        y: zone.y + row * SLOT_GAP_Y + SLOT_START_Y,
        zoneId: s.zone || s.zoneId || "",
      });
    });
  }
  return result;
}

export default function MapPage() {
  const [selectedFloor, setSelectedFloor] = useState(1);
  const [showDirections, setShowDirections] = useState(true);
  const [isNavigating, setIsNavigating] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [carPosition, setCarPosition] = useState(GATE_POS);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [pathProgress, setPathProgress] = useState(0);
  const [currentBooking, setCurrentBooking] =
    useState<CurrentBookingType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [allSlotsLoaded, setAllSlotsLoaded] = useState(false);
  const [allSlots, setAllSlots] = useState<ParkingSlot[]>([]);
  const [isDemo, setIsDemo] = useState(false);

  const { currentParking, loadCurrentParking } = useBooking();
  const { zones, loadZones } = useParking();
  const navigate = useNavigate();
  const animFrameRef = useRef<number>(0);

  // --- Compute map layout from real data (or demo zones) ---
  const demoZonesList = useMemo(
    () =>
      isDemo
        ? [
            {
              id: "V1",
              name: "Zone V1",
              floorLevel: 1,
              availableSlots: 14,
              capacity: 20,
              vehicleType: "Car" as const,
            },
            {
              id: "V2",
              name: "Zone V2",
              floorLevel: 1,
              availableSlots: 12,
              capacity: 20,
              vehicleType: "Car" as const,
            },
          ]
        : [],
    [isDemo],
  );

  const zonesForFloor = useMemo(
    () =>
      isDemo
        ? demoZonesList.filter((z) => (z.floorLevel ?? 1) === selectedFloor)
        : zones.filter((z) => (z.floorLevel ?? 1) === selectedFloor),
    [zones, demoZonesList, isDemo, selectedFloor],
  );

  const mapZones = useMemo(() => layoutZones(zonesForFloor), [zonesForFloor]);

  const slotsForFloor = useMemo(() => {
    const floorZoneIds = new Set(zonesForFloor.map((z) => z.id));
    return allSlots.filter((s) => floorZoneIds.has(s.zone || s.zoneId || ""));
  }, [allSlots, zonesForFloor]);

  const mapSlots = useMemo(
    () => layoutSlots(slotsForFloor, mapZones),
    [slotsForFloor, mapZones],
  );

  const mapGate: MapGate = useMemo(
    () => ({
      id: "gate-main",
      name: "Lối vào chính",
      x: GATE_POS.x,
      y: GATE_POS.y,
    }),
    [],
  );

  // --- Dijkstra pathfinding ---
  const pathResult = useMemo(() => {
    if (!currentBooking || mapZones.length === 0 || mapSlots.length === 0)
      return null;

    const dijkstraZones = mapZones.map((z) => ({
      id: z.id,
      name: z.name,
      x: z.x,
      y: z.y,
      width: z.width,
      height: z.height,
    }));

    const dijkstraSlots = mapSlots.map((s) => ({
      id: s.id,
      code: s.code,
      x: s.x,
      y: s.y,
      zoneId: s.zoneId,
    }));

    return findPathToSlot(
      dijkstraZones,
      dijkstraSlots,
      currentBooking.slotId,
      GATE_POS,
    );
  }, [currentBooking, mapZones, mapSlots]);

  // Convert Dijkstra directions to DirectionStep format
  const directions: DirectionStep[] = useMemo(() => {
    if (!pathResult) return [];
    return pathResult.directions.map((d: DirectionInstruction) => ({
      id: d.id,
      instruction: d.instruction,
      direction:
        d.direction === "elevator" || d.direction === "ramp"
          ? ("straight" as const)
          : (d.direction as DirectionStep["direction"]),
      distance: d.distance,
    }));
  }, [pathResult]);

  // Path waypoints from Dijkstra
  const pathWaypoints = useMemo(() => {
    if (!pathResult) return [GATE_POS];
    return pathResult.path.map((n: GraphNode) => ({ x: n.x, y: n.y }));
  }, [pathResult]);

  // Target slot on map
  const targetSlot = useMemo(
    () => mapSlots.find((s) => s.id === currentBooking?.slotId),
    [mapSlots, currentBooking?.slotId],
  );

  // --- SVG viewbox: adapt to content ---
  const svgViewBox = useMemo(() => {
    if (mapZones.length === 0) return "0 -50 900 450";
    const maxX = Math.max(...mapZones.map((z) => z.x + z.width)) + 40;
    const maxY = Math.max(...mapZones.map((z) => z.y + z.height)) + 40;
    return `-10 -50 ${maxX + 20} ${maxY + 60}`;
  }, [mapZones]);

  // --- Static SVG path from Dijkstra nodes (with rounded corners at actual turns) ---
  const staticPathD = useMemo(() => {
    if (pathWaypoints.length < 2) return "";
    const R = 12; // corner radius
    const pts = pathWaypoints;

    // First, collapse consecutive collinear points (same X or same Y)
    // into just the endpoints, so we only keep actual turn-points.
    const cleaned: typeof pts = [pts[0]];
    for (let i = 1; i < pts.length - 1; i++) {
      const prev = cleaned[cleaned.length - 1];
      const cur = pts[i];
      const next = pts[i + 1];
      const sameX =
        Math.abs(prev.x - cur.x) < 1 && Math.abs(cur.x - next.x) < 1;
      const sameY =
        Math.abs(prev.y - cur.y) < 1 && Math.abs(cur.y - next.y) < 1;
      if (!sameX && !sameY) {
        // This is an actual turn point
        cleaned.push(cur);
      } else if (sameX || sameY) {
        // Collinear — skip (the final point in the group will be added later)
      }
    }
    cleaned.push(pts[pts.length - 1]);

    if (cleaned.length < 2) return "";

    let d = `M${cleaned[0].x},${cleaned[0].y}`;

    for (let i = 1; i < cleaned.length - 1; i++) {
      const prev = cleaned[i - 1];
      const cur = cleaned[i];
      const next = cleaned[i + 1];

      // Vectors from cur to prev/next
      const dx1 = prev.x - cur.x;
      const dy1 = prev.y - cur.y;
      const dx2 = next.x - cur.x;
      const dy2 = next.y - cur.y;
      const len1 = Math.sqrt(dx1 * dx1 + dy1 * dy1);
      const len2 = Math.sqrt(dx2 * dx2 + dy2 * dy2);

      if (len1 === 0 || len2 === 0) {
        d += ` L${cur.x},${cur.y}`;
        continue;
      }

      const r = Math.min(R, len1 / 2, len2 / 2);
      // Points just before and after the corner
      const bx = cur.x + (dx1 / len1) * r;
      const by = cur.y + (dy1 / len1) * r;
      const ax = cur.x + (dx2 / len2) * r;
      const ay = cur.y + (dy2 / len2) * r;

      d += ` L${bx},${by} Q${cur.x},${cur.y} ${ax},${ay}`;
    }

    d += ` L${cleaned[cleaned.length - 1].x},${cleaned[cleaned.length - 1].y}`;
    return d;
  }, [pathWaypoints]);

  // --- Data loading ---
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        await loadCurrentParking();
      } catch (error) {
        console.error("Failed to fetch current parking:", error);
      } finally {
        setIsLoading(false);
      }
    };
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Set booking from API — fallback to demo data when no active parking
  useEffect(() => {
    if (currentParking) {
      setCurrentBooking({
        licensePlate: currentParking.booking.licensePlate,
        vehicleType: currentParking.booking.vehicleType,
        zone: currentParking.booking.zoneName,
        slot: currentParking.booking.slotCode,
        slotId: currentParking.booking.slotId,
        floor: 1,
      });
      setIsDemo(false);
    } else if (!isLoading) {
      // No active booking → use demo data so the map is still useful
      const demo = generateDemoData();
      setCurrentBooking(demo.booking);
      setAllSlots(
        demo.demoSlotList.map(
          (s) =>
            ({
              id: s.id,
              code: s.code,
              zone: s.zoneId,
              zoneId: s.zoneId,
              zoneName: s.zone,
              floor: 1,
              vehicleType: "Car" as const,
              status: s.status as "available" | "occupied",
            }) as ParkingSlot,
        ),
      );
      setAllSlotsLoaded(true);
      setIsDemo(true);
    }
  }, [currentParking, isLoading]);

  // Load zones for the parking lot
  useEffect(() => {
    if (currentParking) {
      const lotId = currentParking.booking.lotId || "1";
      loadZones(lotId);
    }
  }, [currentParking, loadZones]);

  // Load slots for ALL zones directly from API (accumulated)
  useEffect(() => {
    if (zones.length > 0 && currentParking) {
      setAllSlotsLoaded(false);
      setAllSlots([]);
      const loadAllSlots = async () => {
        const accumulated: ParkingSlot[] = [];
        for (const zone of zones) {
          try {
            const response = await parkingApi.getSlots({ zone_id: zone.id });
            const zoneSlots: ParkingSlot[] = response.results.map(
              (slot) =>
                ({
                  ...slot,
                  zone: slot.zone || slot.zoneId || zone.id,
                  zoneId: slot.zone || slot.zoneId || zone.id,
                  zoneName: zone.name || "",
                  floor: zone.floorLevel ?? 1,
                  vehicleType: zone.vehicleType || "Car",
                }) as ParkingSlot,
            );
            accumulated.push(...zoneSlots);
          } catch (e) {
            console.error(`Failed to load slots for zone ${zone.id}:`, e);
          }
        }
        setAllSlots(accumulated);
        setAllSlotsLoaded(true);
      };
      loadAllSlots();
    }
  }, [zones, currentParking]);

  // Get unique floor levels
  const availableFloors = useMemo(() => {
    const src = isDemo ? demoZonesList : zones;
    const floors = new Set(src.map((z) => z.floorLevel ?? 1));
    if (floors.size === 0) floors.add(1);
    return Array.from(floors).sort((a, b) => a - b);
  }, [zones, demoZonesList, isDemo]);

  // Auto-select floor matching booking
  useEffect(() => {
    if (currentBooking && zones.length > 0) {
      const bookingZone = zones.find((z) => z.name === currentBooking.zone);
      if (bookingZone) {
        setSelectedFloor(bookingZone.floorLevel ?? 1);
        setCurrentBooking((prev) =>
          prev ? { ...prev, floor: bookingZone.floorLevel ?? 1 } : prev,
        );
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentBooking?.zone, zones]);

  // --- Animation ---
  const handleStartNavigation = useCallback(() => {
    setIsNavigating(true);
    setCurrentStepIndex(0);
    setCarPosition(GATE_POS);
    setPathProgress(0);
  }, []);

  const handleStopNavigation = useCallback(() => {
    setIsNavigating(false);
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
  }, []);

  useEffect(() => {
    if (!isNavigating || pathWaypoints.length < 2) {
      setCurrentStepIndex(0);
      setCarPosition(GATE_POS);
      setPathProgress(0);
      return;
    }

    let startTime: number;
    const totalDuration = 8000;
    const stepDuration =
      directions.length > 0 ? totalDuration / directions.length : totalDuration;

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      const progress = Math.min(elapsed / totalDuration, 1);
      setPathProgress(progress);

      const totalSegments = pathWaypoints.length - 1;
      const currentSegment = Math.min(
        Math.floor(progress * totalSegments),
        totalSegments - 1,
      );
      const segmentProgress = (progress * totalSegments) % 1;

      const sp = pathWaypoints[currentSegment];
      const ep = pathWaypoints[currentSegment + 1];
      const x = sp.x + (ep.x - sp.x) * segmentProgress;
      const y = sp.y + (ep.y - sp.y) * segmentProgress;
      setCarPosition({ x, y });

      const newStep = Math.min(
        Math.floor(elapsed / stepDuration),
        directions.length - 1,
      );
      setCurrentStepIndex(newStep);

      if (progress < 1) {
        animFrameRef.current = requestAnimationFrame(animate);
      } else {
        const last = pathWaypoints[pathWaypoints.length - 1];
        setCarPosition(last);
        setCurrentStepIndex(directions.length - 1);
      }
    };

    animFrameRef.current = requestAnimationFrame(animate);
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [isNavigating, pathWaypoints, directions]);

  // Animated path SVG (same collinear-collapse logic as staticPathD)
  const getAnimatedPath = () => {
    const count = Math.ceil(pathProgress * pathWaypoints.length) + 1;
    const raw = pathWaypoints.slice(0, count);
    if (raw.length < 2) return "";

    // Collapse collinear points
    const pts: typeof raw = [raw[0]];
    for (let i = 1; i < raw.length - 1; i++) {
      const prev = pts[pts.length - 1];
      const cur = raw[i];
      const next = raw[i + 1];
      const sameX =
        Math.abs(prev.x - cur.x) < 1 && Math.abs(cur.x - next.x) < 1;
      const sameY =
        Math.abs(prev.y - cur.y) < 1 && Math.abs(cur.y - next.y) < 1;
      if (!sameX && !sameY) pts.push(cur);
    }
    pts.push(raw[raw.length - 1]);

    const R = 10;
    let d = `M${pts[0].x},${pts[0].y}`;
    for (let i = 1; i < pts.length - 1; i++) {
      const prev = pts[i - 1];
      const cur = pts[i];
      const next = pts[i + 1];
      const dx1 = prev.x - cur.x,
        dy1 = prev.y - cur.y;
      const dx2 = next.x - cur.x,
        dy2 = next.y - cur.y;
      const len1 = Math.sqrt(dx1 * dx1 + dy1 * dy1);
      const len2 = Math.sqrt(dx2 * dx2 + dy2 * dy2);
      if (len1 === 0 || len2 === 0) {
        d += ` L${cur.x},${cur.y}`;
        continue;
      }
      const r = Math.min(R, len1 / 2, len2 / 2);
      const bx = cur.x + (dx1 / len1) * r,
        by = cur.y + (dy1 / len1) * r;
      const ax = cur.x + (dx2 / len2) * r,
        ay = cur.y + (dy2 / len2) * r;
      d += ` L${bx},${by} Q${cur.x},${cur.y} ${ax},${ay}`;
    }
    d += ` L${pts[pts.length - 1].x},${pts[pts.length - 1].y}`;
    return d;
  };

  // ----- Render -----

  if (isLoading) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center h-96">
          <div className="text-center space-y-3">
            <div className="inline-flex items-center justify-center h-12 w-12 rounded-xl bg-primary/10 animate-pulse">
              <MapPin className="h-6 w-6 text-primary" />
            </div>
            <p className="text-muted-foreground">Đang tải bản đồ bãi xe...</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  // Still loading (only when no demo fallback)
  if (!currentBooking) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center h-96">
          <div className="text-center space-y-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
            <p className="text-muted-foreground">Đang tải bản đồ bãi xe...</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="space-y-4 sm:space-y-6">
        {/* Demo banner */}
        {isDemo && (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400 flex items-center gap-2">
            <span>📍</span>
            <span>
              Đang hiển thị bản đồ mẫu. Hãy đặt chỗ &amp; check-in để xem bản đồ
              thực tế.
            </span>
            <Button
              size="sm"
              variant="outline"
              className="ml-auto text-xs"
              onClick={() => navigate("/booking")}
            >
              Đặt chỗ ngay
            </Button>
          </div>
        )}

        {/* Header */}
        <div className="flex flex-col gap-3 sm:gap-4 animate-fade-in">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-foreground">
              Bản đồ bãi xe
            </h1>
            <p className="mt-1 text-sm sm:text-base text-muted-foreground">
              Xem vị trí và hướng dẫn đến chỗ đậu xe (Dijkstra pathfinding)
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            {/* Floor Selector */}
            <div className="relative">
              <select
                value={selectedFloor}
                onChange={(e) => setSelectedFloor(Number(e.target.value))}
                className="appearance-none rounded-lg sm:rounded-xl border border-border bg-card px-3 sm:px-4 py-2 pr-8 sm:pr-10 text-sm font-medium focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                {availableFloors.map((f) => (
                  <option key={f} value={f}>
                    Tầng {f}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 sm:right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground pointer-events-none" />
            </div>
            <Button
              variant={showDirections ? "default" : "outline"}
              onClick={() => setShowDirections(!showDirections)}
              className="gap-2 text-sm"
              size="sm"
            >
              <Navigation className="h-4 w-4" />
              <span className="hidden sm:inline">Chỉ đường</span>
            </Button>
            {pathResult && (
              <Badge variant="secondary" className="text-xs">
                Tổng: ~{Math.round(pathResult.totalDistance / 5)}m
              </Badge>
            )}
          </div>
        </div>

        <div className="grid gap-4 lg:gap-6 lg:grid-cols-3">
          {/* Map View */}
          <div className="lg:col-span-2 space-y-4">
            <div className="rounded-xl sm:rounded-2xl border border-border bg-card p-3 sm:p-6 animate-slide-up">
              <div className="mb-3 sm:mb-4 flex items-center justify-between">
                <h3 className="font-semibold text-foreground text-sm sm:text-base">
                  Tầng {selectedFloor}
                </h3>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">
                    {currentBooking.zone} - {currentBooking.slot}
                  </Badge>
                  {isNavigating && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 sm:h-8 sm:w-8"
                      onClick={() => setSoundEnabled(!soundEnabled)}
                    >
                      {soundEnabled ? (
                        <Volume2 className="h-4 w-4" />
                      ) : (
                        <VolumeX className="h-4 w-4" />
                      )}
                    </Button>
                  )}
                </div>
              </div>

              {/* SVG Map */}
              <div className="relative w-full overflow-x-auto -mx-3 px-3 sm:mx-0 sm:px-0">
                <svg
                  viewBox={svgViewBox}
                  className="w-full h-auto"
                  style={{ minWidth: "320px", minHeight: "200px" }}
                >
                  <defs>
                    <linearGradient
                      id="pathGradient"
                      x1="0%"
                      y1="0%"
                      x2="100%"
                      y2="0%"
                    >
                      <stop
                        offset="0%"
                        stopColor="hsl(var(--primary))"
                        stopOpacity="0.3"
                      />
                      <stop
                        offset="100%"
                        stopColor="hsl(var(--primary))"
                        stopOpacity="1"
                      />
                    </linearGradient>
                    <marker
                      id="arrowMarker"
                      markerWidth="10"
                      markerHeight="10"
                      refX="9"
                      refY="3"
                      orient="auto"
                      markerUnits="strokeWidth"
                    >
                      <path d="M0,0 L0,6 L9,3 z" fill="hsl(var(--primary))" />
                    </marker>
                    <filter id="glow">
                      <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                      <feMerge>
                        <feMergeNode in="coloredBlur" />
                        <feMergeNode in="SourceGraphic" />
                      </feMerge>
                    </filter>
                    <filter id="carGlow">
                      <feGaussianBlur stdDeviation="4" result="coloredBlur" />
                      <feMerge>
                        <feMergeNode in="coloredBlur" />
                        <feMergeNode in="SourceGraphic" />
                      </feMerge>
                    </filter>
                  </defs>

                  {/* Background grid */}
                  <pattern
                    id="grid"
                    width="20"
                    height="20"
                    patternUnits="userSpaceOnUse"
                  >
                    <path
                      d="M 20 0 L 0 0 0 20"
                      fill="none"
                      stroke="hsl(var(--border))"
                      strokeWidth="0.5"
                      opacity="0.3"
                    />
                  </pattern>
                  <rect
                    x="-50"
                    y="-50"
                    width="2000"
                    height="600"
                    fill="url(#grid)"
                  />

                  {/* Zone backgrounds with center aisle */}
                  {mapZones.map((zone) => {
                    const aisleX = zone.x + AISLE_CENTER_OFFSET;
                    return (
                      <g key={zone.id}>
                        {/* Zone outer border */}
                        <rect
                          x={zone.x}
                          y={zone.y}
                          width={zone.width}
                          height={zone.height}
                          rx="12"
                          fill="hsl(var(--muted))"
                          fillOpacity="0.2"
                          stroke="hsl(var(--border))"
                          strokeWidth="2"
                        />
                        {/* Center driving aisle (visible road inside zone) */}
                        <rect
                          x={aisleX - 14}
                          y={zone.y + 50}
                          width="28"
                          height={zone.height - 60}
                          rx="6"
                          fill="hsl(var(--muted))"
                          fillOpacity="0.25"
                          stroke="hsl(var(--border))"
                          strokeWidth="1"
                          strokeDasharray="6,3"
                          opacity="0.7"
                        />
                        {/* Center line dashes on aisle */}
                        <line
                          x1={aisleX}
                          y1={zone.y + 58}
                          x2={aisleX}
                          y2={zone.y + zone.height - 16}
                          stroke="hsl(var(--border))"
                          strokeWidth="1.5"
                          strokeDasharray="8,6"
                          opacity="0.5"
                        />
                        {/* Zone title */}
                        <text
                          x={zone.x + zone.width / 2}
                          y={zone.y + 22}
                          textAnchor="middle"
                          className="text-xs font-semibold fill-muted-foreground"
                        >
                          {zone.name}
                        </text>
                        {/* Capacity */}
                        <text
                          x={zone.x + zone.width / 2}
                          y={zone.y + 40}
                          textAnchor="middle"
                          className="text-[9px] fill-muted-foreground"
                        >
                          {zonesForFloor.find((z) => z.id === zone.id)
                            ? `${zonesForFloor.find((z) => z.id === zone.id)!.availableSlots} trống / ${zonesForFloor.find((z) => z.id === zone.id)!.capacity}`
                            : ""}
                        </text>
                      </g>
                    );
                  })}

                  {/* Main road from gate to zones */}
                  {mapZones.length > 0 &&
                    (() => {
                      const roadY = GATE_POS.y + 50;
                      const firstAisle = mapZones[0].x + AISLE_CENTER_OFFSET;
                      const lastAisle =
                        mapZones[mapZones.length - 1].x + AISLE_CENTER_OFFSET;
                      return (
                        <g>
                          {/* Vertical road from gate down */}
                          <rect
                            x={GATE_POS.x - 10}
                            y={GATE_POS.y + 12}
                            width="20"
                            height={roadY - GATE_POS.y - 4}
                            rx="4"
                            fill="hsl(var(--muted))"
                            fillOpacity="0.15"
                            stroke="hsl(var(--border))"
                            strokeWidth="0.5"
                            strokeDasharray="4,3"
                            opacity="0.5"
                          />
                          {/* Horizontal main road */}
                          <rect
                            x={Math.min(firstAisle, GATE_POS.x) - 15}
                            y={roadY - 10}
                            width={
                              Math.max(lastAisle, GATE_POS.x) -
                              Math.min(firstAisle, GATE_POS.x) +
                              30
                            }
                            height="20"
                            rx="4"
                            fill="hsl(var(--muted))"
                            fillOpacity="0.12"
                            stroke="hsl(var(--border))"
                            strokeWidth="0.5"
                            strokeDasharray="4,3"
                            opacity="0.5"
                          />
                          {/* Vertical connectors from road to each zone aisle */}
                          {mapZones.map((zone) => (
                            <rect
                              key={`road-conn-${zone.id}`}
                              x={zone.x + AISLE_CENTER_OFFSET - 10}
                              y={roadY}
                              width="20"
                              height={zone.y + 50 - roadY}
                              rx="4"
                              fill="hsl(var(--muted))"
                              fillOpacity="0.12"
                              stroke="hsl(var(--border))"
                              strokeWidth="0.5"
                              strokeDasharray="4,3"
                              opacity="0.4"
                            />
                          ))}
                        </g>
                      );
                    })()}

                  {/* Static Dijkstra path (when not navigating) */}
                  {showDirections && !isNavigating && staticPathD && (
                    <path
                      d={staticPathD}
                      fill="none"
                      stroke="hsl(var(--primary))"
                      strokeWidth="4"
                      strokeDasharray="10,5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="animate-pulse"
                    >
                      <animate
                        attributeName="stroke-dashoffset"
                        values="100;0"
                        dur="2s"
                        repeatCount="indefinite"
                      />
                    </path>
                  )}

                  {/* Animated path (when navigating) */}
                  {isNavigating && (
                    <g>
                      <path
                        d={getAnimatedPath()}
                        fill="none"
                        stroke="hsl(var(--success))"
                        strokeWidth="6"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                      {staticPathD && (
                        <path
                          d={staticPathD}
                          fill="none"
                          stroke="hsl(var(--muted-foreground))"
                          strokeWidth="3"
                          strokeDasharray="5,5"
                          strokeLinecap="round"
                          opacity="0.3"
                        />
                      )}
                    </g>
                  )}

                  {/* Gate */}
                  <g>
                    <rect
                      x={mapGate.x - 40}
                      y={mapGate.y}
                      width="80"
                      height="30"
                      rx="6"
                      fill="hsl(var(--accent))"
                      fillOpacity="0.2"
                      stroke="hsl(var(--accent))"
                      strokeWidth="2"
                    />
                    <text
                      x={mapGate.x}
                      y={mapGate.y + 20}
                      textAnchor="middle"
                      className="text-xs font-medium fill-accent"
                    >
                      {mapGate.name}
                    </text>
                  </g>

                  {/* Parking slots */}
                  {mapSlots.map((slot) => {
                    const isTarget = slot.id === currentBooking.slotId;
                    return (
                      <g key={slot.id}>
                        <rect
                          x={slot.x}
                          y={slot.y}
                          width={SLOT_W}
                          height={SLOT_H}
                          rx="4"
                          fill={
                            isTarget
                              ? "hsl(var(--primary))"
                              : slot.isAvailable
                                ? "hsl(var(--success) / 0.2)"
                                : "hsl(var(--destructive) / 0.2)"
                          }
                          stroke={
                            isTarget
                              ? "hsl(var(--primary))"
                              : slot.isAvailable
                                ? "hsl(var(--success) / 0.5)"
                                : "hsl(var(--destructive) / 0.3)"
                          }
                          strokeWidth={isTarget ? "3" : "1"}
                          filter={isTarget ? "url(#glow)" : undefined}
                        />
                        <text
                          x={slot.x + SLOT_W / 2}
                          y={slot.y + 18}
                          textAnchor="middle"
                          className={cn(
                            "text-[10px] font-medium pointer-events-none",
                            isTarget
                              ? "fill-primary-foreground"
                              : slot.isAvailable
                                ? "fill-success"
                                : "fill-destructive/70",
                          )}
                        >
                          {slot.code}
                        </text>
                      </g>
                    );
                  })}

                  {/* Animated Car Icon */}
                  {isNavigating && (
                    <g
                      transform={`translate(${carPosition.x}, ${carPosition.y})`}
                      filter="url(#carGlow)"
                    >
                      <circle
                        cx="0"
                        cy="0"
                        r="12"
                        fill="hsl(var(--primary))"
                        className="animate-pulse"
                      />
                      <circle
                        cx="0"
                        cy="0"
                        r="18"
                        fill="none"
                        stroke="hsl(var(--primary))"
                        strokeWidth="2"
                        opacity="0.5"
                      >
                        <animate
                          attributeName="r"
                          values="12;24;12"
                          dur="1.5s"
                          repeatCount="indefinite"
                        />
                        <animate
                          attributeName="opacity"
                          values="0.6;0;0.6"
                          dur="1.5s"
                          repeatCount="indefinite"
                        />
                      </circle>
                      <text
                        x="0"
                        y="4"
                        textAnchor="middle"
                        className="text-[10px] fill-primary-foreground"
                      >
                        🚗
                      </text>
                    </g>
                  )}

                  {/* Target marker when not navigating */}
                  {!isNavigating && targetSlot && (
                    <g>
                      <circle
                        cx={targetSlot.x + SLOT_W + 8}
                        cy={targetSlot.y + SLOT_H / 2}
                        r="8"
                        fill="hsl(var(--primary))"
                        className="animate-pulse"
                      />
                      <text
                        x={targetSlot.x + SLOT_W + 8}
                        y={targetSlot.y + SLOT_H / 2 + 4}
                        textAnchor="middle"
                        className="text-[8px] fill-primary-foreground"
                      >
                        🚗
                      </text>
                    </g>
                  )}
                </svg>

                {/* Legend */}
                <div className="mt-3 sm:mt-4 flex flex-wrap gap-2 sm:gap-4 justify-center text-xs sm:text-sm">
                  <div className="flex items-center gap-1.5 sm:gap-2">
                    <div className="h-3 w-5 sm:h-4 sm:w-6 rounded bg-success/20 border border-success/50" />
                    <span className="text-muted-foreground">Trống</span>
                  </div>
                  <div className="flex items-center gap-1.5 sm:gap-2">
                    <div className="h-3 w-5 sm:h-4 sm:w-6 rounded bg-destructive/20 border border-destructive/30" />
                    <span className="text-muted-foreground">Đã đặt</span>
                  </div>
                  <div className="flex items-center gap-1.5 sm:gap-2">
                    <div className="h-3 w-5 sm:h-4 sm:w-6 rounded bg-primary border-2 border-primary shadow-lg shadow-primary/30" />
                    <span className="text-muted-foreground">Của bạn</span>
                  </div>
                  {isNavigating && (
                    <div className="flex items-center gap-1.5 sm:gap-2">
                      <div className="h-3 w-3 sm:h-4 sm:w-4 rounded-full bg-primary animate-pulse" />
                      <span className="text-muted-foreground">Di chuyển</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Directions Panel */}
          {showDirections && (
            <div className="animate-slide-up">
              <DirectionsPanel
                steps={directions}
                currentBooking={currentBooking}
                estimatedTime={
                  pathResult
                    ? Math.max(1, Math.round(pathResult.totalDistance / 250))
                    : 3
                }
                onStartNavigation={
                  isNavigating ? undefined : handleStartNavigation
                }
                currentStepIndex={isNavigating ? currentStepIndex : undefined}
              />
            </div>
          )}
        </div>

        {/* Navigating Indicator */}
        {isNavigating && directions.length > 0 && (
          <div className="fixed bottom-20 sm:bottom-6 left-2 right-2 sm:left-1/2 sm:right-auto sm:-translate-x-1/2 z-50 animate-fade-in">
            <div className="flex items-center gap-2 sm:gap-3 rounded-xl sm:rounded-full bg-primary px-4 sm:px-6 py-3 text-primary-foreground shadow-lg shadow-primary/30">
              <Navigation className="h-4 w-4 sm:h-5 sm:w-5 animate-pulse shrink-0" />
              <div className="flex flex-col flex-1 min-w-0">
                <span className="font-medium text-sm sm:text-base truncate">
                  Bước {currentStepIndex + 1}/{directions.length}:{" "}
                  {directions[currentStepIndex]?.instruction}
                </span>
                {directions[currentStepIndex]?.distance && (
                  <span className="text-xs opacity-80">
                    Còn {directions[currentStepIndex].distance}
                  </span>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="text-primary-foreground hover:bg-primary-foreground/20 shrink-0"
                onClick={handleStopNavigation}
              >
                Dừng
              </Button>
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
