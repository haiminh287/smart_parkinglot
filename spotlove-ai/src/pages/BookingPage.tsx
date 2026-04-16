import { useState, useMemo, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Car,
  Bike,
  Calendar,
  Clock,
  MapPin,
  CreditCard,
  ChevronRight,
  Check,
  Building2,
  QrCode,
  AlertTriangle,
  History,
  Ban,
  ShieldAlert,
  Sparkles,
  Navigation,
  Bell,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { SlotGrid } from "@/components/booking/SlotGrid";
import { MultiDayPicker } from "@/components/booking/MultiDayPicker";
import { PriceSummary } from "@/components/booking/PriceSummary";
import { BookingQRCode } from "@/components/booking/BookingQRCode";
import { ParkingLotSelector } from "@/components/booking/ParkingLotSelector";
import { AutoGuaranteeBooking } from "@/components/booking/AutoGuaranteeBooking";
import { CalendarAutoHold } from "@/components/booking/CalendarAutoHold";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { useParking, useBooking } from "@/hooks";
import { useWebSocketConnection } from "@/hooks/useWebSocketConnection";
import type { ParkingLot, VehicleType, CarSlot } from "@/types/parking";
import type { Floor } from "@/services/business";
import type { Booking } from "@/store/slices/bookingSlice";

type Step = 1 | 2 | 3 | 4 | 5;

// Local interface for saved vehicles (different from API Vehicle)
interface SavedVehicle {
  id: string;
  licensePlate: string;
  vehicleType: VehicleType;
  name: string;
  isDefault?: boolean;
}

// Step navigation config
const steps = [
  { number: 1, title: "Chọn bãi" },
  { number: 2, title: "Chọn xe" },
  { number: 3, title: "Chọn vị trí" },
  { number: 4, title: "Thời gian" },
  { number: 5, title: "Thanh toán" },
];

export default function BookingPage() {
  const navigate = useNavigate();
  const { toast } = useToast();

  // Redux hooks for parking data
  const {
    lots,
    zones,
    slots,
    selectedLot,
    selectedZone: selectedZoneObj,
    loadParkingLots,
    loadZones,
    loadSlots,
    selectLot,
    selectZone: selectZoneObj,
    isLoading: parkingLoading,
  } = useParking();

  // Redux hooks for booking
  const { create, noShowCount, isLoading: bookingLoading } = useBooking();

  // WebSocket connection for realtime slot updates
  const { subscribeToZone, unsubscribeFromZone, isConnected } =
    useWebSocketConnection();

  const [currentStep, setCurrentStep] = useState<Step>(1);
  const [selectedParkingLot, setSelectedParkingLot] =
    useState<ParkingLot | null>(null);
  const [vehicleType, setVehicleType] = useState<"Car" | "Motorbike">("Car");
  const [licensePlate, setLicensePlate] = useState("");
  const [selectedVehicleId, setSelectedVehicleId] = useState<string | null>(
    null,
  );
  const [selectedFloor, setSelectedFloor] = useState<string>("");
  const [selectedZone, setSelectedZone] = useState<string>("");
  const [selectedSlot, setSelectedSlot] = useState<any>(null); // eslint-disable-line @typescript-eslint/no-explicit-any -- TODO: Integrate with Redux slots
  const [packageType, setPackageType] = useState<
    "monthly" | "weekly" | "custom" | "hourly"
  >("monthly");
  const [selectedDates, setSelectedDates] = useState<Date[]>([]);
  const [hourlyDate, setHourlyDate] = useState<Date>(new Date());
  const [hourlyStartTime, setHourlyStartTime] = useState<string>("08:00");
  const [hourlyEndTime, setHourlyEndTime] = useState<string>("17:00");
  const [paymentMethod, setPaymentMethod] = useState<"online" | "on_exit">(
    "online",
  );
  const [showQRDialog, setShowQRDialog] = useState(false);
  const [bookingId, setBookingId] = useState<string>("");

  const [userVehicles, setUserVehicles] = useState<SavedVehicle[]>([]);
  const [floors, setFloors] = useState<Floor[]>([]);
  const [loadingVehicles, setLoadingVehicles] = useState(false);
  const [loadingFloors, setLoadingFloors] = useState(false);

  const forceOnlinePayment = noShowCount >= 2;

  useEffect(() => {
    loadParkingLots();

    const loadVehicles = async () => {
      setLoadingVehicles(true);
      try {
        const { vehicleApi } = await import("@/services");
        const response = await vehicleApi.getVehicles();
        const vehicles: SavedVehicle[] = response.results.map((v) => ({
          id: v.id,
          licensePlate: v.licensePlate,
          vehicleType: v.vehicleType,
          name: v.brand ? `${v.brand} ${v.model || ""}`.trim() : "Xe cá nhân",
          isDefault: v.isDefault || false,
        }));
        setUserVehicles(vehicles);
        // Auto-select default vehicl e
        const defaultVehicle = vehicles.find((v) => v.isDefault);
        if (defaultVehicle) {
          setSelectedVehicleId(defaultVehicle.id);
          setLicensePlate(defaultVehicle.licensePlate);
          setVehicleType(defaultVehicle.vehicleType);
        }
      } catch {
        return;
      } finally {
        setLoadingVehicles(false);
      }
    };
    loadVehicles();
  }, [loadParkingLots]);

  // When a parking lot is selected, load its floors
  useEffect(() => {
    if (selectedParkingLot) {
      const loadFloorsData = async () => {
        setLoadingFloors(true);
        try {
          const { parkingApi } = await import("@/services");
          const response = await parkingApi.getFloors({
            lot_id: selectedParkingLot.id,
          });
          setFloors(response.results);
        } catch {
          return;
        } finally {
          setLoadingFloors(false);
        }
      };
      loadFloorsData();
    }
  }, [selectedParkingLot]);

  // When a zone is selected, load its slots and subscribe to realtime updates
  useEffect(() => {
    if (selectedZone) {
      loadSlots(selectedZone);

      // Subscribe to WebSocket for realtime slot updates
      if (isConnected) {
        subscribeToZone(selectedZone);
      }

      // Cleanup: unsubscribe when zone changes or component unmounts
      return () => {
        unsubscribeFromZone(selectedZone);
      };
    }
  }, [
    selectedZone,
    loadSlots,
    isConnected,
    subscribeToZone,
    unsubscribeFromZone,
  ]);

  useEffect(() => {
    if (selectedSlot) {
      const currentSlot = slots.find((s) => s.id === selectedSlot.id);
      if (currentSlot && currentSlot.status !== "available") {
        // Clear selected slot if it's no longer available
        setSelectedSlot(null);
        toast({
          title: "Vị trí không còn trống",
          description:
            "Vị trí bạn chọn đã được đặt bởi người khác. Vui lòng chọn vị trí khác.",
          variant: "destructive",
        });
      }
    }
  }, [slots, selectedSlot, toast]);

  const filteredZones =
    floors
      .find((f) => f.id === selectedFloor)
      ?.zones.filter((z) => z.vehicleType === vehicleType) || [];

  const isMotorbike = vehicleType === "Motorbike";

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return selectedParkingLot !== null;
      case 2:
        return licensePlate.trim().length >= 5;
      case 3:
        // For motorbike: only need floor and zone
        // For car: need floor, zone, and slot
        if (isMotorbike) {
          return selectedFloor && selectedZone;
        }
        return selectedFloor && selectedZone && selectedSlot;
      case 4:
        return packageType === "custom" ? selectedDates.length > 0 : true;
      case 5:
        return true;
      default:
        return false;
    }
  };

  const handleSelectSavedVehicle = (vehicle: SavedVehicle) => {
    setSelectedVehicleId(vehicle.id);
    setLicensePlate(vehicle.licensePlate);
    setVehicleType(vehicle.vehicleType);
    // Reset location selection when changing vehicle type
    setSelectedFloor("");
    setSelectedZone("");
    setSelectedSlot(null);
  };

  const handleVehicleTypeChange = (type: "Car" | "Motorbike") => {
    setVehicleType(type);
    setSelectedVehicleId(null);
    setLicensePlate("");
    // Reset location selection when changing vehicle type
    setSelectedFloor("");
    setSelectedZone("");
    setSelectedSlot(null);
  };

  const handleSubmit = async () => {
    try {
      // Validate required fields
      if (!selectedParkingLot) {
        toast({
          title: "Thiếu thông tin",
          description: "Vui lòng chọn bãi đỗ xe",
          variant: "destructive",
        });
        return;
      }

      if (!licensePlate || licensePlate.trim().length < 5) {
        toast({
          title: "Thiếu thông tin",
          description: "Vui lòng nhập biển số xe (tối thiểu 5 ký tự)",
          variant: "destructive",
        });
        return;
      }

      if (!selectedZone) {
        toast({
          title: "Thiếu thông tin",
          description: "Vui lòng chọn tầng và zone đậu xe",
          variant: "destructive",
        });
        return;
      }

      if (!selectedParkingLot || !selectedParkingLot.id) {
        toast({
          title: "Thiếu thông tin",
          description: "Vui lòng chọn bãi đậu xe",
          variant: "destructive",
        });
        return;
      }

      let bookingData: {
        vehicleId: string;
        slotId?: string | null;
        zoneId: string;
        parkingLotId: string;
        startTime: string;
        endTime?: string | null;
        packageType: "hourly" | "daily" | "weekly" | "monthly";
        paymentMethod: "online" | "on_exit";
      };

      if (packageType === "hourly") {
        // Hourly booking with start and end time
        const startDateTime = new Date(hourlyDate);
        const [startHour, startMin] = hourlyStartTime.split(":");
        startDateTime.setHours(parseInt(startHour), parseInt(startMin), 0);

        const endDateTime = new Date(hourlyDate);
        const [endHour, endMin] = hourlyEndTime.split(":");
        endDateTime.setHours(parseInt(endHour), parseInt(endMin), 0);

        if (endDateTime <= startDateTime) {
          toast({
            title: "Thời gian không hợp lệ",
            description: "Giờ kết thúc phải sau giờ bắt đầu",
            variant: "destructive",
          });
          return;
        }

        bookingData = {
          vehicleId: selectedVehicleId || licensePlate,
          slotId: selectedSlot?.id || null,
          zoneId: selectedZone,
          parkingLotId: selectedParkingLot.id,
          startTime: startDateTime.toISOString(),
          endTime: endDateTime.toISOString(),
          packageType: "hourly",
          paymentMethod: forceOnlinePayment ? "online" : paymentMethod,
        };
      } else {
        // Monthly/Weekly/Custom booking
        const startDate = selectedDates[0] || new Date();

        let endDate: Date;
        if (packageType === "monthly") {
          endDate = new Date(startDate);
          endDate.setMonth(endDate.getMonth() + 1);
        } else if (packageType === "weekly") {
          endDate = new Date(startDate);
          endDate.setDate(endDate.getDate() + 7);
        } else {
          // custom — use last selected date
          endDate =
            selectedDates[selectedDates.length - 1] ||
            new Date(Date.now() + 3600000);
        }

        bookingData = {
          vehicleId: selectedVehicleId || licensePlate,
          slotId: selectedSlot?.id || null,
          zoneId: selectedZone,
          parkingLotId: selectedParkingLot.id,
          startTime: startDate.toISOString(),
          endTime: endDate.toISOString(),
          packageType: packageType === "custom" ? "daily" : packageType,
          paymentMethod: forceOnlinePayment ? "online" : paymentMethod,
        };
      }

      // Create booking via hook with correct field names
      const resultAction = await create(bookingData);

      // Check if fulfilled (has payload)
      if (resultAction && "payload" in resultAction && resultAction.payload) {
        const result = resultAction.payload as {
          booking: Booking;
          payment_url?: string;
          qr_code?: string;
          message: string;
        };

        const newBookingId = result.booking.id;
        setBookingId(newBookingId);

        // If online payment, redirect to payment gateway
        if (forceOnlinePayment || paymentMethod === "online") {
          // if (result.payment_url) {
          //   window.location.href = result.payment_url;
          // } else {
          navigate(`/payment?bookingId=${newBookingId}`);
          // }
        } else {
          // Show QR code for on-exit payment
          setShowQRDialog(true);
          toast({
            title: "Đặt chỗ thành công!",
            description: "Quét mã QR để check-in khi đến bãi",
          });
        }
      } else {
        throw new Error("Không thể tạo booking");
      }
    } catch (error: unknown) {
      const err = error as Error;
      toast({
        title: "Lỗi đặt chỗ",
        description: err.message || "Không thể đặt chỗ. Vui lòng thử lại.",
        variant: "destructive",
      });
    }
  };

  return (
    <MainLayout>
      <div className="mx-auto max-w-5xl space-y-6">
        {/* Header */}
        <div className="animate-fade-in">
          <h1 className="text-2xl font-bold text-foreground">Đặt chỗ giữ xe</h1>
          <p className="mt-1 text-muted-foreground">
            Chọn cách đặt chỗ phù hợp với bạn
          </p>
        </div>

        {/* Main Tabs for booking modes */}
        <Tabs defaultValue="standard" className="space-y-6">
          <TabsList className="w-full grid grid-cols-3 h-auto p-1 bg-muted/50">
            <TabsTrigger
              value="standard"
              className="gap-1.5 py-2.5 text-xs sm:text-sm data-[state=active]:gradient-primary data-[state=active]:text-primary-foreground"
            >
              <MapPin className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              <span className="hidden sm:inline">Đặt chỗ</span>
              <span className="sm:hidden">Chuẩn</span>
            </TabsTrigger>
            <TabsTrigger
              value="auto-guarantee"
              className="gap-1.5 py-2.5 text-xs sm:text-sm data-[state=active]:gradient-primary data-[state=active]:text-primary-foreground"
            >
              <Navigation className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              <span className="hidden sm:inline">Đi đâu cũng có chỗ</span>
              <span className="sm:hidden">Auto</span>
            </TabsTrigger>
            <TabsTrigger
              value="calendar-hold"
              className="gap-1.5 py-2.5 text-xs sm:text-sm data-[state=active]:gradient-primary data-[state=active]:text-primary-foreground"
            >
              <Calendar className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              <span className="hidden sm:inline">Auto-Hold</span>
              <span className="sm:hidden">Lịch</span>
            </TabsTrigger>
          </TabsList>

          {/* Standard Booking Flow */}
          <TabsContent value="standard" className="space-y-6 mt-0">
            {/* No-Show Warning Banner */}
            {noShowCount > 0 && (
              <div
                className={cn(
                  "flex items-start gap-3 rounded-2xl border p-4 animate-fade-in",
                  forceOnlinePayment
                    ? "border-destructive/50 bg-destructive/10"
                    : "border-warning/50 bg-warning/10",
                )}
              >
                <ShieldAlert
                  className={cn(
                    "h-6 w-6 shrink-0",
                    forceOnlinePayment ? "text-destructive" : "text-warning",
                  )}
                />
                <div>
                  <p
                    className={cn(
                      "font-semibold",
                      forceOnlinePayment ? "text-destructive" : "text-warning",
                    )}
                  >
                    {forceOnlinePayment
                      ? "Bắt buộc thanh toán online"
                      : "Cảnh báo vi phạm"}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    {forceOnlinePayment
                      ? `Bạn đã có ${noShowCount} lần không đến sau khi đặt chỗ. Từ bây giờ, bạn phải thanh toán online trước khi đặt.`
                      : `Bạn đã có ${noShowCount} lần không đến. Nếu vi phạm thêm 1 lần nữa, bạn sẽ bị bắt buộc thanh toán online.`}
                  </p>
                </div>
              </div>
            )}

            {/* Progress Steps */}
            <div className="flex items-center justify-between rounded-2xl border border-border bg-card p-4 overflow-x-auto">
              {steps.map((step, index) => (
                <div key={step.number} className="flex items-center">
                  <div className="flex items-center gap-2 sm:gap-3">
                    <div
                      className={cn(
                        "flex h-8 w-8 sm:h-10 sm:w-10 items-center justify-center rounded-full text-xs sm:text-sm font-semibold transition-all shrink-0",
                        currentStep === step.number
                          ? "gradient-primary text-primary-foreground shadow-glow"
                          : currentStep > step.number
                            ? "bg-success text-success-foreground"
                            : "bg-muted text-muted-foreground",
                      )}
                    >
                      {currentStep > step.number ? (
                        <Check className="h-4 w-4 sm:h-5 sm:w-5" />
                      ) : (
                        step.number
                      )}
                    </div>
                    <span
                      className={cn(
                        "hidden text-xs sm:text-sm font-medium lg:block",
                        currentStep >= step.number
                          ? "text-foreground"
                          : "text-muted-foreground",
                      )}
                    >
                      {step.title}
                    </span>
                  </div>
                  {index < steps.length - 1 && (
                    <ChevronRight className="mx-2 sm:mx-4 h-4 w-4 sm:h-5 sm:w-5 text-muted-foreground shrink-0" />
                  )}
                </div>
              ))}
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
              {/* Main Content */}
              <div className="lg:col-span-2">
                <div className="rounded-2xl border border-border bg-card p-4 sm:p-6 animate-slide-up">
                  {/* Step 1: Parking Lot Selection */}
                  {currentStep === 1 && (
                    <ParkingLotSelector
                      onSelect={setSelectedParkingLot}
                      selectedLot={selectedParkingLot}
                    />
                  )}

                  {/* Step 2: Vehicle Selection */}
                  {currentStep === 2 && (
                    <div className="space-y-6">
                      <h2 className="text-lg font-semibold">Chọn loại xe</h2>

                      <div className="grid gap-4 sm:grid-cols-2">
                        <button
                          onClick={() => handleVehicleTypeChange("Car")}
                          className={cn(
                            "flex flex-col items-center gap-4 rounded-2xl border-2 p-8 transition-all",
                            vehicleType === "Car"
                              ? "border-primary bg-primary/5 shadow-lg shadow-primary/20"
                              : "border-border hover:border-primary/50",
                          )}
                        >
                          <div
                            className={cn(
                              "flex h-20 w-20 items-center justify-center rounded-2xl",
                              vehicleType === "Car"
                                ? "gradient-primary"
                                : "bg-muted",
                            )}
                          >
                            <Car
                              className={cn(
                                "h-10 w-10",
                                vehicleType === "Car"
                                  ? "text-primary-foreground"
                                  : "text-muted-foreground",
                              )}
                            />
                          </div>
                          <div className="text-center">
                            <p className="text-lg font-semibold text-foreground">
                              Ô tô
                            </p>
                            <p className="text-sm text-muted-foreground">
                              Xe 4 bánh trở lên
                            </p>
                          </div>
                        </button>

                        <button
                          onClick={() => handleVehicleTypeChange("Motorbike")}
                          className={cn(
                            "flex flex-col items-center gap-4 rounded-2xl border-2 p-8 transition-all",
                            vehicleType === "Motorbike"
                              ? "border-accent bg-accent/5 shadow-lg shadow-accent/20"
                              : "border-border hover:border-accent/50",
                          )}
                        >
                          <div
                            className={cn(
                              "flex h-20 w-20 items-center justify-center rounded-2xl",
                              vehicleType === "Motorbike"
                                ? "gradient-accent"
                                : "bg-muted",
                            )}
                          >
                            <Bike
                              className={cn(
                                "h-10 w-10",
                                vehicleType === "Motorbike"
                                  ? "text-accent-foreground"
                                  : "text-muted-foreground",
                              )}
                            />
                          </div>
                          <div className="text-center">
                            <p className="text-lg font-semibold text-foreground">
                              Xe máy
                            </p>
                            <p className="text-sm text-muted-foreground">
                              Xe 2 bánh
                            </p>
                          </div>
                        </button>
                      </div>

                      {/* Saved Vehicles */}
                      {loadingVehicles ? (
                        <div className="flex items-center justify-center py-8">
                          <Loader2 className="h-6 w-6 animate-spin text-primary" />
                          <span className="ml-2 text-sm text-muted-foreground">
                            Loading vehicles...
                          </span>
                        </div>
                      ) : userVehicles.length > 0 ? (
                        <div className="space-y-3">
                          <div className="flex items-center gap-2">
                            <History className="h-4 w-4 text-muted-foreground" />
                            <label className="text-sm font-medium text-muted-foreground">
                              Xe đã sử dụng gần đây
                            </label>
                          </div>
                          <div className="grid gap-2 sm:grid-cols-2">
                            {userVehicles.map((vehicle) => (
                              <button
                                key={vehicle.id}
                                onClick={() =>
                                  handleSelectSavedVehicle(vehicle)
                                }
                                className={cn(
                                  "flex items-center gap-3 rounded-xl border-2 p-3 transition-all text-left relative",
                                  selectedVehicleId === vehicle.id
                                    ? "border-primary bg-primary/5"
                                    : "border-border hover:border-primary/50",
                                )}
                              >
                                {vehicle.isDefault && (
                                  <div className="absolute -top-2 -right-2 bg-primary text-primary-foreground text-xs px-2 py-0.5 rounded-full font-semibold">
                                    Mặc định
                                  </div>
                                )}
                                <div
                                  className={cn(
                                    "flex h-10 w-10 items-center justify-center rounded-lg",
                                    vehicle.vehicleType === "Car"
                                      ? "bg-primary/10 text-primary"
                                      : "bg-accent/10 text-accent",
                                  )}
                                >
                                  {vehicle.vehicleType === "Car" ? (
                                    <Car className="h-5 w-5" />
                                  ) : (
                                    <Bike className="h-5 w-5" />
                                  )}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <p className="font-mono font-semibold text-foreground">
                                    {vehicle.licensePlate}
                                  </p>
                                  <p className="text-xs text-muted-foreground truncate">
                                    {vehicle.name}
                                  </p>
                                </div>
                                {selectedVehicleId === vehicle.id && (
                                  <Check className="h-5 w-5 text-primary shrink-0" />
                                )}
                              </button>
                            ))}
                          </div>
                        </div>
                      ) : null}

                      {/* License Plate Input */}
                      <div>
                        <label className="mb-2 block text-sm font-medium">
                          Biển số xe <span className="text-destructive">*</span>
                        </label>
                        <input
                          type="text"
                          placeholder="VD: 51A-123.45"
                          value={licensePlate}
                          onChange={(e) => {
                            setLicensePlate(e.target.value.toUpperCase());
                            setSelectedVehicleId(null); // Clear selection when manually typing
                          }}
                          className="w-full rounded-xl border border-border bg-background px-4 py-3 text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 font-mono text-lg"
                        />
                        {selectedVehicleId && (
                          <p className="mt-2 text-sm text-success flex items-center gap-1">
                            <Check className="h-4 w-4" />
                            Đã chọn xe từ lịch sử
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Step 3: Location Selection */}
                  {currentStep === 3 && (
                    <div className="space-y-6">
                      <div>
                        <h2 className="text-lg font-semibold">
                          Chọn vị trí đậu xe
                        </h2>
                        {selectedParkingLot && (
                          <p className="text-sm text-muted-foreground mt-1">
                            Tại: {selectedParkingLot.name}
                          </p>
                        )}
                        {isMotorbike && (
                          <p className="mt-1 text-sm text-accent">
                            Xe máy chỉ cần chọn zone, không cần chọn ô cụ thể
                          </p>
                        )}
                      </div>

                      {/* Floor Selection */}
                      <div>
                        <label className="mb-3 block text-sm font-medium">
                          Chọn tầng
                        </label>
                        {loadingFloors ? (
                          <div className="flex items-center justify-center py-8">
                            <Loader2 className="h-6 w-6 animate-spin text-primary" />
                          </div>
                        ) : (
                          <div className="grid gap-3 sm:grid-cols-3">
                            {floors.map((floor) => {
                              const hasAvailable = floor.zones
                                .filter((z) => z.vehicleType === vehicleType)
                                .some((z) => z.availableSlots > 0);

                              return (
                                <button
                                  key={floor.id}
                                  onClick={() => {
                                    setSelectedFloor(floor.id);
                                    setSelectedZone("");
                                    setSelectedSlot(null);
                                  }}
                                  disabled={!hasAvailable}
                                  className={cn(
                                    "flex items-center gap-3 rounded-xl border-2 p-4 transition-all",
                                    selectedFloor === floor.id
                                      ? "border-primary bg-primary/5"
                                      : hasAvailable
                                        ? "border-border hover:border-primary/50"
                                        : "border-border opacity-50 cursor-not-allowed",
                                  )}
                                >
                                  <Building2 className="h-5 w-5 text-muted-foreground" />
                                  <span className="font-medium">
                                    {floor.name}
                                  </span>
                                  {!hasAvailable && (
                                    <Badge
                                      variant="secondary"
                                      className="ml-auto text-xs"
                                    >
                                      Hết chỗ
                                    </Badge>
                                  )}
                                </button>
                              );
                            })}
                          </div>
                        )}
                      </div>

                      {/* Zone Selection */}
                      {selectedFloor && (
                        <div className="animate-fade-in">
                          <label className="mb-3 block text-sm font-medium">
                            Chọn zone
                          </label>
                          <div className="grid gap-3 sm:grid-cols-2">
                            {filteredZones.map((zone) => (
                              <button
                                key={zone.id}
                                onClick={() => {
                                  setSelectedZone(zone.id);
                                  setSelectedSlot(null);
                                }}
                                disabled={zone.availableSlots === 0}
                                className={cn(
                                  "flex items-center justify-between rounded-xl border-2 p-4 transition-all",
                                  selectedZone === zone.id
                                    ? "border-primary bg-primary/5"
                                    : zone.availableSlots > 0
                                      ? "border-border hover:border-primary/50"
                                      : "border-border opacity-50 cursor-not-allowed",
                                )}
                              >
                                <div className="flex items-center gap-3">
                                  <MapPin className="h-5 w-5 text-primary" />
                                  <span className="font-medium">
                                    {zone.name}
                                  </span>
                                </div>
                                <Badge
                                  variant={
                                    zone.availableSlots > 10
                                      ? "default"
                                      : zone.availableSlots > 5
                                        ? "secondary"
                                        : "destructive"
                                  }
                                  className="text-xs"
                                >
                                  {zone.availableSlots}/{zone.capacity}
                                </Badge>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Slot Selection Grid - Only for Cars */}
                      {selectedZone && !isMotorbike && (
                        <div className="animate-fade-in">
                          <label className="mb-3 block text-sm font-medium">
                            Chọn ô đậu xe
                          </label>
                          <SlotGrid
                            zoneId={selectedZone}
                            vehicleType={vehicleType}
                            onSlotSelect={setSelectedSlot}
                            selectedSlot={selectedSlot}
                          />
                        </div>
                      )}

                      {/* Motorbike Zone Selection Confirmation */}
                      {selectedZone && isMotorbike && (
                        <div className="animate-fade-in rounded-xl bg-success/10 border border-success/20 p-4">
                          <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-success/20">
                              <Check className="h-5 w-5 text-success" />
                            </div>
                            <div>
                              <p className="font-medium text-foreground">
                                Đã chọn Zone {selectedZone}
                              </p>
                              <p className="text-sm text-muted-foreground">
                                Bạn có thể đậu xe tại bất kỳ vị trí trống nào
                                trong zone này
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Step 4: Time Selection */}
                  {currentStep === 4 && (
                    <div className="space-y-6">
                      <h2 className="text-lg font-semibold">Chọn thời gian</h2>

                      {/* Package Type */}
                      <div>
                        <label className="mb-3 block text-sm font-medium">
                          Gói đặt chỗ
                        </label>
                        <div className="grid gap-3 sm:grid-cols-3">
                          {[
                            {
                              type: "monthly" as const,
                              label: "Theo tháng",
                              desc: "Tiết kiệm nhất",
                              discount: "-20%",
                            },
                            {
                              type: "weekly" as const,
                              label: "Theo tuần",
                              desc: "7 ngày liên tiếp",
                              discount: "-10%",
                            },
                            {
                              type: "hourly" as const,
                              label: "Theo giờ",
                              desc: "Linh hoạt, tính phí theo giờ",
                            },
                            {
                              type: "custom" as const,
                              label: "Chọn ngày",
                              desc: "Linh hoạt",
                            },
                          ].map((pkg) => (
                            <button
                              key={pkg.type}
                              onClick={() => setPackageType(pkg.type)}
                              className={cn(
                                "relative flex flex-col items-center rounded-xl border-2 p-4 transition-all",
                                packageType === pkg.type
                                  ? "border-primary bg-primary/5"
                                  : "border-border hover:border-primary/50",
                              )}
                            >
                              {pkg.discount && (
                                <Badge className="absolute -right-2 -top-2 bg-success text-success-foreground">
                                  {pkg.discount}
                                </Badge>
                              )}
                              <span className="font-medium">{pkg.label}</span>
                              <span className="mt-1 text-xs text-muted-foreground">
                                {pkg.desc}
                              </span>
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Date Selection based on package */}
                      {packageType === "hourly" ? (
                        <div className="space-y-4">
                          <div>
                            <label className="mb-2 block text-sm font-medium">
                              Chọn ngày{" "}
                              <span className="text-destructive">*</span>
                            </label>
                            <div className="flex items-center gap-2 rounded-xl border border-border bg-background px-4 py-3">
                              <Calendar className="h-5 w-5 text-muted-foreground" />
                              <input
                                type="date"
                                className="flex-1 bg-transparent outline-none"
                                value={hourlyDate.toISOString().split("T")[0]}
                                onChange={(e) =>
                                  setHourlyDate(new Date(e.target.value))
                                }
                                min={new Date().toISOString().split("T")[0]}
                              />
                            </div>
                          </div>
                          <div className="grid gap-4 sm:grid-cols-2">
                            <div>
                              <label className="mb-2 block text-sm font-medium">
                                Giờ bắt đầu{" "}
                                <span className="text-destructive">*</span>
                              </label>
                              <div className="flex items-center gap-2 rounded-xl border border-border bg-background px-4 py-3">
                                <Clock className="h-5 w-5 text-muted-foreground" />
                                <input
                                  type="time"
                                  className="flex-1 bg-transparent outline-none"
                                  value={hourlyStartTime}
                                  onChange={(e) =>
                                    setHourlyStartTime(e.target.value)
                                  }
                                />
                              </div>
                            </div>
                            <div>
                              <label className="mb-2 block text-sm font-medium">
                                Giờ kết thúc{" "}
                                <span className="text-destructive">*</span>
                              </label>
                              <div className="flex items-center gap-2 rounded-xl border border-border bg-background px-4 py-3">
                                <Clock className="h-5 w-5 text-muted-foreground" />
                                <input
                                  type="time"
                                  className="flex-1 bg-transparent outline-none"
                                  value={hourlyEndTime}
                                  onChange={(e) =>
                                    setHourlyEndTime(e.target.value)
                                  }
                                />
                              </div>
                            </div>
                          </div>
                          <div className="rounded-lg bg-warning/10 border border-warning/20 p-3 text-sm text-warning-foreground">
                            <p className="font-medium">
                              ⚠️ Lưu ý về gói theo giờ:
                            </p>
                            <ul className="mt-2 space-y-1 text-xs">
                              <li>
                                • Phí quá giờ: <strong>30,000đ/giờ</strong> (so
                                với 20,000đ/giờ thường)
                              </li>
                              <li>
                                • Thanh toán online: Tự động hủy sau 15 phút nếu
                                chưa thanh toán
                              </li>
                              <li>
                                • Thanh toán khi ra: Vui lòng đến đúng giờ,
                                tránh phí phạt
                              </li>
                            </ul>
                          </div>
                        </div>
                      ) : packageType === "custom" ? (
                        <div>
                          <label className="mb-3 block text-sm font-medium">
                            Chọn ngày đậu xe{" "}
                            <span className="text-destructive">*</span>
                          </label>
                          <MultiDayPicker
                            selectedDates={selectedDates}
                            onDatesChange={setSelectedDates}
                          />
                        </div>
                      ) : (
                        <div className="grid gap-4 sm:grid-cols-2">
                          <div>
                            <label className="mb-2 block text-sm font-medium">
                              Ngày bắt đầu
                            </label>
                            <div className="flex items-center gap-2 rounded-xl border border-border bg-background px-4 py-3">
                              <Calendar className="h-5 w-5 text-muted-foreground" />
                              <input
                                type="date"
                                className="flex-1 bg-transparent outline-none"
                                defaultValue={
                                  new Date().toISOString().split("T")[0]
                                }
                              />
                            </div>
                          </div>
                          <div>
                            <label className="mb-2 block text-sm font-medium">
                              Giờ bắt đầu
                            </label>
                            <div className="flex items-center gap-2 rounded-xl border border-border bg-background px-4 py-3">
                              <Clock className="h-5 w-5 text-muted-foreground" />
                              <input
                                type="time"
                                className="flex-1 bg-transparent outline-none"
                                defaultValue="08:00"
                              />
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Step 5: Payment */}
                  {currentStep === 5 && (
                    <div className="space-y-6">
                      <h2 className="text-lg font-semibold">
                        Xác nhận & Thanh toán
                      </h2>

                      {/* Booking Summary */}
                      <div className="rounded-xl bg-muted/50 p-4 space-y-3">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Bãi xe</span>
                          <span className="font-medium">
                            {selectedParkingLot?.name}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">
                            Biển số xe
                          </span>
                          <span className="font-mono font-bold">
                            {licensePlate}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Loại xe</span>
                          <span className="font-medium">
                            {vehicleType === "Car" ? "Ô tô" : "Xe máy"}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Vị trí</span>
                          <span className="font-medium">
                            {floors.find((f) => f.id === selectedFloor)?.name ||
                              `Tầng ${selectedFloor}`}
                            {" - "}
                            {floors
                              .find((f) => f.id === selectedFloor)
                              ?.zones.find((z) => z.id === selectedZone)
                              ?.name || `Zone ${selectedZone}`}
                            {selectedSlot && ` - ${selectedSlot.code}`}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Gói</span>
                          <span className="font-medium">
                            {packageType === "monthly"
                              ? "Theo tháng"
                              : packageType === "weekly"
                                ? "Theo tuần"
                                : `${selectedDates.length} ngày`}
                          </span>
                        </div>
                      </div>

                      {/* Payment Method */}
                      <div>
                        <label className="mb-3 block text-sm font-medium">
                          Phương thức thanh toán
                        </label>

                        {/* Force online payment warning */}
                        {forceOnlinePayment && (
                          <div className="mb-3 flex items-center gap-2 rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
                            <Ban className="h-4 w-4" />
                            <span>
                              Do vi phạm quá 2 lần, bạn chỉ có thể thanh toán
                              online
                            </span>
                          </div>
                        )}

                        <div className="grid gap-3 sm:grid-cols-2">
                          <button
                            onClick={() => setPaymentMethod("online")}
                            className={cn(
                              "flex items-center gap-3 rounded-xl border-2 p-4 transition-all",
                              paymentMethod === "online"
                                ? "border-primary bg-primary/5"
                                : "border-border hover:border-primary/50",
                            )}
                          >
                            <CreditCard className="h-5 w-5 text-primary" />
                            <div className="text-left">
                              <span className="font-medium block">
                                Thanh toán online
                              </span>
                              <span className="text-xs text-muted-foreground">
                                Giữ chỗ ngay lập tức
                              </span>
                            </div>
                          </button>
                          <button
                            onClick={() =>
                              !forceOnlinePayment && setPaymentMethod("on_exit")
                            }
                            disabled={forceOnlinePayment}
                            className={cn(
                              "flex items-center gap-3 rounded-xl border-2 p-4 transition-all",
                              forceOnlinePayment
                                ? "border-border opacity-50 cursor-not-allowed"
                                : paymentMethod === "on_exit"
                                  ? "border-primary bg-primary/5"
                                  : "border-border hover:border-primary/50",
                            )}
                          >
                            <Clock className="h-5 w-5 text-muted-foreground" />
                            <div className="text-left">
                              <span className="font-medium block">
                                Thanh toán khi lấy xe
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {forceOnlinePayment
                                  ? "Không khả dụng"
                                  : "Giữ chỗ trong 3 giờ"}
                              </span>
                            </div>
                          </button>
                        </div>
                      </div>

                      {/* Warning for unpaid booking */}
                      {paymentMethod === "on_exit" && !forceOnlinePayment && (
                        <div className="flex items-start gap-3 rounded-xl bg-warning/10 border border-warning/20 p-4">
                          <AlertTriangle className="h-5 w-5 text-warning shrink-0 mt-0.5" />
                          <div>
                            <p className="font-medium text-warning">
                              Lưu ý về giữ chỗ
                            </p>
                            <p className="text-sm text-muted-foreground mt-1">
                              Chỗ sẽ được giữ trong <strong>3 giờ</strong>. Nếu
                              bạn không đến trong thời gian này, đặt chỗ sẽ tự
                              động bị hủy và được tính là 1 lần vi phạm.
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Price Summary Sidebar */}
              <div className="lg:col-span-1 order-first lg:order-last">
                <div className="lg:sticky lg:top-6">
                  <PriceSummary
                    vehicleType={vehicleType}
                    packageType={packageType}
                    selectedDates={selectedDates}
                    zone={selectedZone ? `Zone ${selectedZone}` : undefined}
                    slot={isMotorbike ? undefined : selectedSlot?.code}
                    parkingLot={selectedParkingLot?.name}
                    hourlyStartTime={
                      packageType === "hourly" ? hourlyStartTime : undefined
                    }
                    hourlyEndTime={
                      packageType === "hourly" ? hourlyEndTime : undefined
                    }
                  />
                </div>
              </div>
            </div>

            {/* Navigation Buttons */}
            <div className="flex justify-between">
              <Button
                variant="outline"
                onClick={() =>
                  setCurrentStep((prev) => Math.max(1, prev - 1) as Step)
                }
                disabled={currentStep === 1}
              >
                Quay lại
              </Button>
              <Button
                className="gradient-primary"
                onClick={() => {
                  if (currentStep < 5) {
                    setCurrentStep((prev) => Math.min(5, prev + 1) as Step);
                  } else {
                    handleSubmit();
                  }
                }}
                disabled={!canProceed()}
              >
                {currentStep === 5 ? (
                  <>
                    {paymentMethod === "online" ? (
                      <>
                        <CreditCard className="h-4 w-4 mr-2" />
                        Thanh toán ngay
                      </>
                    ) : (
                      <>
                        <QrCode className="h-4 w-4 mr-2" />
                        Xác nhận đặt chỗ
                      </>
                    )}
                  </>
                ) : (
                  <>
                    Tiếp tục
                    <ChevronRight className="h-4 w-4 ml-2" />
                  </>
                )}
              </Button>
            </div>
          </TabsContent>

          {/* Auto Guarantee Tab */}
          <TabsContent value="auto-guarantee" className="mt-0">
            <div className="rounded-2xl border border-border bg-card p-4 sm:p-6">
              <AutoGuaranteeBooking
                onComplete={(data) => {
                  toast({
                    title: "Đã giữ chỗ thành công!",
                    description: `Chỗ đã được giữ tại ${data.selectedLot?.name}`,
                  });
                  navigate("/history");
                }}
              />
            </div>
          </TabsContent>

          {/* Calendar Auto Hold Tab */}
          <TabsContent value="calendar-hold" className="mt-0">
            <div className="rounded-2xl border border-border bg-card p-4 sm:p-6">
              <CalendarAutoHold />
            </div>
          </TabsContent>
        </Tabs>
      </div>
      <Dialog open={showQRDialog} onOpenChange={setShowQRDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Đặt chỗ thành công!</DialogTitle>
          </DialogHeader>
          <BookingQRCode
            bookingId={bookingId}
            vehicleType={vehicleType}
            licensePlate={licensePlate}
            zone={`Zone ${selectedZone}`}
            slot={isMotorbike ? "Tự chọn trong zone" : selectedSlot?.code || ""}
            dates={packageType === "custom" ? selectedDates : [new Date()]}
            status="pending"
          />
          <div className="flex gap-3 mt-4">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => {
                setShowQRDialog(false);
                navigate("/history");
              }}
            >
              Xem lịch sử
            </Button>
            <Button
              className="flex-1 gradient-primary"
              onClick={() => {
                setShowQRDialog(false);
                navigate("/");
              }}
            >
              Về trang chủ
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}
