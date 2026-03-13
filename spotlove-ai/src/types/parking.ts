export type VehicleType = "Car" | "Motorbike";

export type PackageType = "hourly" | "daily" | "weekly" | "monthly" | "custom";

export type PaymentType = "online" | "on_exit";

export type CheckInStatus =
  | "checked_in"
  | "not_checked_in"
  | "checked_out"
  | "cancelled"
  | "no_show";

export type PaymentStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed"
  | "refunded"
  | "cancelled";

export interface User {
  id: string;
  username: string;
  email: string;
  avatar?: string;
  isAdmin: boolean;
  noShowCount: number; // Track bad history
  forceOnlinePayment: boolean; // Force online payment after 2 no-shows
}

export interface Vehicle {
  id: string;
  userId: string;
  licensePlate: string;
  vehicleType: VehicleType;
  name?: string;
}

export interface ParkingLot {
  id: string;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  totalSlots: number;
  availableSlots: number;
  distance?: number; // Calculated distance from user
  pricePerHour: number;
  isOpen: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Floor {
  id: string;
  parkingLot: string; // parking lot UUID (FK)
  parkingLotId?: string; // alias for backward compat
  name: string;
  level: number;
  zones: Zone[];
  createdAt?: string;
  updatedAt?: string;
}

export interface Zone {
  id: string;
  floor: string; // floor UUID (FK)
  floorId?: string; // alias
  floorLevel?: number;
  name: string;
  vehicleType: VehicleType;
  capacity: number;
  availableSlots: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface CarSlot {
  id: string;
  zone: string; // zone UUID (FK)
  zoneId?: string; // alias
  code: string;
  status: string;
  isAvailable: boolean;
  camera?: string | null; // camera UUID (FK)
  cameraId?: string; // alias
  x1?: number;
  y1?: number;
  x2?: number;
  y2?: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface Camera {
  id: string;
  name: string;
  ipAddress: string;
  port: number;
  zone?: string | null; // zone UUID (FK)
  zoneId?: string; // alias
  streamUrl?: string;
  isActive?: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface Booking {
  id: string;
  userId: string;
  vehicle: Vehicle;
  packageType: PackageType;
  startTime: string;
  endTime: string;
  floor: Floor;
  zone: Zone;
  carSlot?: CarSlot;
  paymentType: PaymentType;
  paymentStatus: PaymentStatus;
  checkInStatus: CheckInStatus;
  price: number;
  createdAt: string;
  parkingLot: ParkingLot;
}

export interface Message {
  id: string;
  senderId: string;
  receiverId: string;
  content: string;
  createdAt: string;
  isRead: boolean;
}

export interface DashboardStats {
  totalSlots: number;
  availableSlots: number;
  occupiedSlots: number;
  todayRevenue: number;
  monthlyRevenue: number;
  activeBookings: number;
  pendingBookings: number;
}

// Map Navigation Types
export type MapNodeType = "gate" | "elevator" | "road" | "slot" | "ramp";

export interface MapNode {
  id: string;
  floorId: string;
  name: string;
  x: number;
  y: number;
  nodeType: MapNodeType;
  slotId?: string;
}

export type DirectionType =
  | "straight"
  | "left"
  | "right"
  | "elevator"
  | "ramp"
  | "destination";

export interface MapEdge {
  id: string;
  startNodeId: string;
  endNodeId: string;
  distance: number;
  direction: DirectionType;
}

export interface DirectionStep {
  id: number;
  instruction: string;
  direction: DirectionType;
  distance?: string;
  node?: MapNode;
}

// Bank Payment Types
export interface BankInfo {
  bankName: string;
  bankCode: string;
  accountNumber: string;
  accountName: string;
  branch?: string;
}
