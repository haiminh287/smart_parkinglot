import { useState, useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Car, Footprints, ArrowUp, Building2 } from "lucide-react";
import type { MapNode, MapEdge, DirectionStep } from "@/types/parking";

interface SlotData {
  id: string;
  code: string;
  isAvailable: boolean;
  x: number;
  y: number;
  zoneId: string;
}

interface ZoneData {
  id: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

interface GateData {
  id: string;
  name: string;
  x: number;
  y: number;
  type: "gate";
}

interface ElevatorData {
  id: string;
  name: string;
  x: number;
  y: number;
  type: "elevator";
}

interface InteractiveMapProps {
  floorLevel: number;
  targetSlot?: string;
  showPath?: boolean;
  nodes: MapNode[];
  edges: MapEdge[];
  currentPath?: DirectionStep[];
  zones?: ZoneData[];
  slots?: SlotData[];
  gates?: GateData[];
  elevators?: ElevatorData[];
}

export function InteractiveMap({
  floorLevel,
  targetSlot,
  showPath = false,
  nodes,
  edges,
  currentPath,
  zones = [],
  slots = [],
  gates = [],
  elevators = [],
}: InteractiveMapProps) {
  const [hoveredSlot, setHoveredSlot] = useState<string | null>(null);

  // Find target slot position
  const targetSlotData = useMemo(() => {
    return slots.find((s) => s.code === targetSlot);
  }, [targetSlot, slots]);

  // Generate path line coordinates
  const pathCoordinates = useMemo(() => {
    if (!showPath || !targetSlotData || gates.length === 0) return null;

    const gate = gates[0];
    return {
      start: { x: gate.x, y: gate.y + 40 },
      waypoints: [
        { x: gate.x, y: 50 },
        { x: targetSlotData.x + 25, y: 50 },
      ],
      end: { x: targetSlotData.x + 25, y: targetSlotData.y },
    };
  }, [showPath, targetSlotData, gates]);

  return (
    <div className="relative w-full overflow-x-auto">
      <svg
        viewBox="-50 -50 900 350"
        className="w-full min-w-[600px] h-auto"
        style={{ minHeight: "300px" }}
      >
        <defs>
          {/* Gradient for path */}
          <linearGradient id="pathGradient" x1="0%" y1="0%" x2="100%" y2="0%">
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

          {/* Arrow marker */}
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

          {/* Glow filter */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Background grid */}
        <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
          <path
            d="M 20 0 L 0 0 0 20"
            fill="none"
            stroke="hsl(var(--border))"
            strokeWidth="0.5"
            opacity="0.3"
          />
        </pattern>
        <rect x="-50" y="-50" width="900" height="350" fill="url(#grid)" />

        {/* Zone backgrounds */}
        {zones.map((zone) => (
          <g key={zone.id}>
            <rect
              x={zone.x}
              y={zone.y}
              width={zone.width}
              height={zone.height}
              rx="12"
              fill="hsl(var(--muted))"
              fillOpacity="0.3"
              stroke="hsl(var(--border))"
              strokeWidth="2"
            />
            <text
              x={zone.x + zone.width / 2}
              y={zone.y + 25}
              textAnchor="middle"
              className="text-xs font-semibold fill-muted-foreground"
            >
              {zone.name}
            </text>
          </g>
        ))}

        {/* Path animation */}
        {showPath && pathCoordinates && (
          <g>
            {/* Path line */}
            <path
              d={`M${pathCoordinates.start.x},${pathCoordinates.start.y} 
                  ${pathCoordinates.waypoints.map((w) => `L${w.x},${w.y}`).join(" ")} 
                  L${pathCoordinates.end.x},${pathCoordinates.end.y}`}
              fill="none"
              stroke="hsl(var(--primary))"
              strokeWidth="4"
              strokeDasharray="10,5"
              strokeLinecap="round"
              markerEnd="url(#arrowMarker)"
              className="animate-pulse"
            >
              <animate
                attributeName="stroke-dashoffset"
                values="100;0"
                dur="2s"
                repeatCount="indefinite"
              />
            </path>
          </g>
        )}

        {/* Gate */}
        {gates.map((gate) => (
          <g key={gate.id}>
            <rect
              x={gate.x - 40}
              y={gate.y}
              width="80"
              height="30"
              rx="6"
              fill="hsl(var(--accent))"
              fillOpacity="0.2"
              stroke="hsl(var(--accent))"
              strokeWidth="2"
            />
            <text
              x={gate.x}
              y={gate.y + 20}
              textAnchor="middle"
              className="text-xs font-medium fill-accent"
            >
              {gate.name}
            </text>
          </g>
        ))}

        {/* Elevator */}
        {elevators.map((elev) => (
          <g key={elev.id}>
            <rect
              x={elev.x}
              y={elev.y}
              width="50"
              height="50"
              rx="8"
              fill="hsl(var(--secondary))"
              stroke="hsl(var(--border))"
              strokeWidth="2"
            />
            <text
              x={elev.x + 25}
              y={elev.y + 30}
              textAnchor="middle"
              className="text-[10px] font-medium fill-secondary-foreground"
            >
              🛗
            </text>
          </g>
        ))}

        {/* Parking slots */}
        {slots.map((slot) => {
          const isTarget = slot.code === targetSlot;
          const isHovered = slot.id === hoveredSlot;

          return (
            <g
              key={slot.id}
              onMouseEnter={() => setHoveredSlot(slot.id)}
              onMouseLeave={() => setHoveredSlot(null)}
              className="cursor-pointer"
            >
              <rect
                x={slot.x}
                y={slot.y}
                width="50"
                height="28"
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
                strokeWidth={isTarget ? "3" : isHovered ? "2" : "1"}
                filter={isTarget ? "url(#glow)" : undefined}
                className="transition-all duration-200"
              />
              <text
                x={slot.x + 25}
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
              {isTarget && (
                <g>
                  <circle
                    cx={slot.x + 45}
                    cy={slot.y + 5}
                    r="8"
                    fill="hsl(var(--primary))"
                    className="animate-pulse"
                  />
                  <text
                    x={slot.x + 45}
                    y={slot.y + 9}
                    textAnchor="middle"
                    className="text-[8px] fill-primary-foreground"
                  >
                    🚗
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="mt-4 flex flex-wrap gap-4 justify-center text-sm">
        <div className="flex items-center gap-2">
          <div className="h-4 w-6 rounded bg-success/20 border border-success/50" />
          <span className="text-muted-foreground">Còn trống</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-4 w-6 rounded bg-destructive/20 border border-destructive/30" />
          <span className="text-muted-foreground">Đã đặt</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-4 w-6 rounded bg-primary border-2 border-primary shadow-lg shadow-primary/30" />
          <span className="text-muted-foreground">Vị trí của bạn</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-4 w-6 rounded bg-accent/20 border border-accent" />
          <span className="text-muted-foreground">Lối vào</span>
        </div>
      </div>
    </div>
  );
}
