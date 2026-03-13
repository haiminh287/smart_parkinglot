/**
 * Dijkstra's Algorithm for Parking Map Navigation
 * Generates shortest path from gate to target parking slot
 */

export interface GraphNode {
  id: string;
  x: number;
  y: number;
  type:
    | "gate"
    | "road"
    | "intersection"
    | "zone-entry"
    | "slot"
    | "elevator"
    | "lane";
  label?: string;
}

export interface GraphEdge {
  from: string;
  to: string;
  weight: number; // distance in pixels (proxy for meters)
}

export interface PathResult {
  path: GraphNode[];
  totalDistance: number;
  directions: DirectionInstruction[];
}

export interface DirectionInstruction {
  id: number;
  instruction: string;
  direction:
    | "straight"
    | "left"
    | "right"
    | "destination"
    | "elevator"
    | "ramp";
  distance?: string;
  nodeId?: string;
}

/**
 * Build a navigation graph from zones and slots layout.
 *
 * REAL parking-lot topology — center-aisle design:
 *
 *                        Gate
 *                         │ (V)
 *                      Road-main
 *           ┌─────────────┼─────────────┐ (H) main road
 *           │                           │
 *      Zone-aisle-top              Zone-aisle-top
 *           │ (V)                       │ (V)
 *     ┌─────┼─────┐              ┌─────┼─────┐
 *     │  AISLE    │              │  AISLE    │
 *  L-slots  │  R-slots       L-slots  │  R-slots
 *     │  row-0   │              │  row-0   │
 *  L-slots  │  R-slots       L-slots  │  R-slots
 *     │  row-1   │              │  row-1   │
 *     └─────┴─────┘              └─────┴─────┘
 *
 * The driving aisle runs DOWN THE CENTER of each zone.
 * Slots are on LEFT and RIGHT sides of the aisle.
 * Path goes: gate → road → zone-aisle → lane-row → short LEFT/RIGHT turn → slot
 * The path NEVER crosses through other slots.
 */
export function buildParkingGraph(
  zones: Array<{
    id: string;
    name: string;
    x: number;
    y: number;
    width: number;
    height: number;
  }>,
  slots: Array<{
    id: string;
    code: string;
    x: number;
    y: number;
    zoneId: string;
  }>,
  gatePosition: { x: number; y: number },
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];

  const AISLE_CENTER = 190; // center of aisle relative to zone.x (must match MapPage AISLE_CENTER_OFFSET)
  const SLOT_W = 48;

  // Gate node
  const gateNode: GraphNode = {
    id: "gate-main",
    x: gatePosition.x,
    y: gatePosition.y,
    type: "gate",
    label: "Cổng chính",
  };
  nodes.push(gateNode);

  // Main road Y: between gate and zones
  const roadY = gatePosition.y + 50;
  const roadNode: GraphNode = {
    id: "road-main",
    x: gatePosition.x,
    y: roadY,
    type: "road",
    label: "Đường chính",
  };
  nodes.push(roadNode);
  addBidirectional(edges, gateNode, roadNode);

  // For each zone: road-junction → aisle-top → lane-rows → slots
  zones.forEach((zone, idx) => {
    const SLOTS_PER_ROW = 6;
    const SLOT_START_Y_OFFSET = 70;
    const SLOT_GAP_Y = 38;

    const aisleX = zone.x + AISLE_CENTER;
    const zoneSlots = slots.filter((s) => s.zoneId === zone.id);
    const numRows = Math.ceil(zoneSlots.length / SLOTS_PER_ROW);

    // Junction on the main road at the aisle X
    const junctionId = `junction-${zone.id}`;
    const junctionNode: GraphNode = {
      id: junctionId,
      x: aisleX,
      y: roadY,
      type: "intersection",
      label: `Ngã rẽ ${zone.name}`,
    };
    nodes.push(junctionNode);

    // Connect junction to road or previous junction (horizontal)
    if (idx === 0) {
      addBidirectional(edges, roadNode, junctionNode);
    } else {
      const prevJunctionId = `junction-${zones[idx - 1].id}`;
      const prevJunction = nodes.find((n) => n.id === prevJunctionId)!;
      addBidirectional(edges, prevJunction, junctionNode);
    }

    // Aisle entry (top of driving aisle inside zone)
    const aisleTopId = `aisle-top-${zone.id}`;
    const aisleTopY = zone.y + 55;
    const aisleTopNode: GraphNode = {
      id: aisleTopId,
      x: aisleX,
      y: aisleTopY,
      type: "zone-entry",
      label: zone.name,
    };
    nodes.push(aisleTopNode);
    addBidirectional(edges, junctionNode, aisleTopNode); // vertical down

    // Lane-row nodes along the center aisle
    for (let row = 0; row < numRows; row++) {
      const laneId = `lane-${zone.id}-row-${row}`;
      const laneY = zone.y + SLOT_START_Y_OFFSET + row * SLOT_GAP_Y + 13;
      const laneNode: GraphNode = {
        id: laneId,
        x: aisleX,
        y: laneY,
        type: "lane",
        label: `Hàng ${row + 1}`,
      };
      nodes.push(laneNode);

      // Connect vertically along aisle
      if (row === 0) {
        addBidirectional(edges, aisleTopNode, laneNode);
      } else {
        const prevLaneId = `lane-${zone.id}-row-${row - 1}`;
        const prevLane = nodes.find((n) => n.id === prevLaneId)!;
        addBidirectional(edges, prevLane, laneNode);
      }
    }

    // Slot nodes — connected with SHORT horizontal from their lane-row
    zoneSlots.forEach((slot, slotIdx) => {
      const row = Math.floor(slotIdx / SLOTS_PER_ROW);
      const col = slotIdx % SLOTS_PER_ROW;
      const isLeftSide = col < 3;

      // Slot center position
      const slotCenterX = slot.x + SLOT_W / 2;
      const slotCenterY = slot.y + 13;

      const slotNode: GraphNode = {
        id: `slot-${slot.id}`,
        x: slotCenterX,
        y: slotCenterY,
        type: "slot",
        label: slot.code,
      };
      nodes.push(slotNode);

      const laneId = `lane-${zone.id}-row-${row}`;
      const laneNode = nodes.find((n) => n.id === laneId)!;

      // Connect: aisle lane → slot (short horizontal, LEFT or RIGHT)
      // Path goes from center aisle to the NEAREST edge of the slot
      addBidirectional(edges, laneNode, slotNode);

      // Connect adjacent slots on the SAME SIDE only (left-to-left, right-to-right)
      if (isLeftSide && col > 0) {
        const prevSlotId = `slot-${zoneSlots[slotIdx - 1].id}`;
        const prevSlot = nodes.find((n) => n.id === prevSlotId);
        if (prevSlot) addBidirectional(edges, prevSlot, slotNode);
      }
      if (!isLeftSide && col > 3) {
        const prevSlotId = `slot-${zoneSlots[slotIdx - 1].id}`;
        const prevSlot = nodes.find((n) => n.id === prevSlotId);
        if (prevSlot) addBidirectional(edges, prevSlot, slotNode);
      }
    });
  });

  return { nodes, edges };
}

/** Add bidirectional edge between two nodes */
function addBidirectional(
  edges: GraphEdge[],
  a: GraphNode,
  b: GraphNode,
): void {
  const w = distance(a, b);
  edges.push({ from: a.id, to: b.id, weight: w });
  edges.push({ from: b.id, to: a.id, weight: w });
}

/**
 * Dijkstra's shortest path algorithm
 */
export function dijkstra(
  nodes: GraphNode[],
  edges: GraphEdge[],
  startId: string,
  endId: string,
): { path: string[]; distance: number } | null {
  const dist: Record<string, number> = {};
  const prev: Record<string, string | null> = {};
  const visited = new Set<string>();

  // Build adjacency list
  const adj: Record<string, Array<{ to: string; weight: number }>> = {};
  for (const node of nodes) {
    dist[node.id] = Infinity;
    prev[node.id] = null;
    adj[node.id] = [];
  }
  for (const edge of edges) {
    if (!adj[edge.from]) adj[edge.from] = [];
    adj[edge.from].push({ to: edge.to, weight: edge.weight });
  }

  dist[startId] = 0;

  // Simple priority queue using array
  const queue = [startId];

  while (queue.length > 0) {
    // Find node with minimum distance
    queue.sort((a, b) => dist[a] - dist[b]);
    const u = queue.shift()!;

    if (visited.has(u)) continue;
    visited.add(u);

    if (u === endId) break;

    for (const neighbor of adj[u] || []) {
      if (visited.has(neighbor.to)) continue;
      const alt = dist[u] + neighbor.weight;
      if (alt < dist[neighbor.to]) {
        dist[neighbor.to] = alt;
        prev[neighbor.to] = u;
        queue.push(neighbor.to);
      }
    }
  }

  if (dist[endId] === Infinity) return null;

  // Reconstruct path
  const path: string[] = [];
  let current: string | null = endId;
  while (current !== null) {
    path.unshift(current);
    current = prev[current];
  }

  return { path, distance: dist[endId] };
}

/**
 * Generate human-readable direction instructions from path.
 * Filters out redundant consecutive "straight" segments and
 * only emits instructions at meaningful decision points.
 */
export function generateDirections(
  pathIds: string[],
  nodes: GraphNode[],
): DirectionInstruction[] {
  const instructions: DirectionInstruction[] = [];
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  let stepId = 1;

  for (let i = 0; i < pathIds.length; i++) {
    const node = nodeMap.get(pathIds[i]);
    if (!node) continue;

    const prevNode = i > 0 ? nodeMap.get(pathIds[i - 1]) : null;
    const nextNode =
      i < pathIds.length - 1 ? nodeMap.get(pathIds[i + 1]) : null;

    let direction: DirectionInstruction["direction"] = "straight";
    let instruction = "";
    let dist = "";

    if (node.type === "gate") {
      instruction = "Từ cổng chính, đi thẳng vào bãi xe";
      direction = "straight";
      if (nextNode) dist = `${Math.round(distance(node, nextNode) / 5)}m`;
    } else if (node.type === "road") {
      // Main road — only emit if there is a meaningful turn
      if (nextNode) {
        direction = prevNode
          ? getTurnDirection(prevNode, node, nextNode)
          : "straight";
        instruction = "Đi thẳng theo đường chính";
        dist = `${Math.round(distance(node, nextNode) / 5)}m`;
      }
    } else if (node.type === "intersection") {
      if (prevNode && nextNode) {
        direction = getTurnDirection(prevNode, node, nextNode);
        const dirLabel =
          direction === "left"
            ? "Rẽ trái"
            : direction === "right"
              ? "Rẽ phải"
              : "Đi thẳng";
        instruction = `${dirLabel} tại ${node.label || "ngã rẽ"}`;
      } else {
        instruction = `Đi tới ${node.label || "ngã rẽ"}`;
      }
      if (nextNode) dist = `${Math.round(distance(node, nextNode) / 5)}m`;
    } else if (node.type === "zone-entry") {
      instruction = `Vào khu vực ${node.label || ""}`;
      if (prevNode) direction = getSimpleDirection(prevNode, node);
      if (nextNode) dist = `${Math.round(distance(node, nextNode) / 5)}m`;
    } else if (node.type === "lane") {
      if (prevNode && nextNode) {
        direction = getTurnDirection(prevNode, node, nextNode);
        if (prevNode.type === "zone-entry" || prevNode.type === "lane") {
          // Only emit if next is a slot (meaning we're turning into the row)
          // or if this is a lane→lane transition the user should know about
          if (nextNode.type === "slot") {
            const dirLabel =
              direction === "left"
                ? "Rẽ trái"
                : direction === "right"
                  ? "Rẽ phải"
                  : "Đi thẳng";
            instruction = `${dirLabel} vào ${node.label || "làn đậu xe"}`;
          } else if (nextNode.type === "lane") {
            instruction = `Đi tới ${nextNode.label || "hàng tiếp theo"}`;
            direction = "straight";
          } else {
            instruction = `Đi theo ${node.label || "làn"}`;
          }
        } else {
          instruction = `Đi theo ${node.label || "làn"}`;
        }
      } else {
        instruction = `Đi theo ${node.label || "làn"}`;
      }
      if (nextNode) dist = `${Math.round(distance(node, nextNode) / 5)}m`;
    } else if (node.type === "slot") {
      instruction = `Đến vị trí đậu xe ${node.label || ""}`;
      direction = "destination";
    } else if (node.type === "elevator") {
      instruction = `Đi thang máy`;
      direction = "elevator";
    }

    if (instruction) {
      instructions.push({
        id: stepId++,
        instruction,
        direction,
        distance: dist || undefined,
        nodeId: node.id,
      });
    }
  }

  return instructions;
}

/**
 * Full pathfinding: build graph → find path → generate directions
 */
export function findPathToSlot(
  zones: Array<{
    id: string;
    name: string;
    x: number;
    y: number;
    width: number;
    height: number;
  }>,
  slots: Array<{
    id: string;
    code: string;
    x: number;
    y: number;
    zoneId: string;
  }>,
  targetSlotId: string,
  gatePosition: { x: number; y: number } = { x: 380, y: -20 },
): PathResult | null {
  const { nodes, edges } = buildParkingGraph(zones, slots, gatePosition);

  const targetNodeId = `slot-${targetSlotId}`;
  const result = dijkstra(nodes, edges, "gate-main", targetNodeId);

  if (!result) return null;

  const pathNodes = result.path
    .map((id) => nodes.find((n) => n.id === id))
    .filter(Boolean) as GraphNode[];

  const directions = generateDirections(result.path, nodes);

  return {
    path: pathNodes,
    totalDistance: result.distance,
    directions,
  };
}

// ---- Helper functions ----

function distance(
  a: { x: number; y: number },
  b: { x: number; y: number },
): number {
  return Math.sqrt(Math.pow(a.x - b.x, 2) + Math.pow(a.y - b.y, 2));
}

function getTurnDirection(
  prev: { x: number; y: number },
  current: { x: number; y: number },
  next: { x: number; y: number },
): "straight" | "left" | "right" {
  // Cross product to determine turn direction
  const dx1 = current.x - prev.x;
  const dy1 = current.y - prev.y;
  const dx2 = next.x - current.x;
  const dy2 = next.y - current.y;
  const cross = dx1 * dy2 - dy1 * dx2;

  if (Math.abs(cross) < 10) return "straight";
  return cross > 0 ? "right" : "left";
}

function getSimpleDirection(
  prev: { x: number; y: number },
  current: { x: number; y: number },
): "straight" | "left" | "right" {
  const dx = current.x - prev.x;
  const dy = current.y - prev.y;
  if (Math.abs(dy) > Math.abs(dx)) return "straight";
  return dx > 0 ? "right" : "left";
}
