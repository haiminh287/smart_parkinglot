import { useMemo, useEffect, useState } from "react";
import { format } from "date-fns";
import { vi } from "date-fns/locale";
import {
  Calculator,
  Car,
  Bike,
  Calendar,
  MapPin,
  Clock,
  Tag,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  bookingApi,
  type PackagePricingResponse,
} from "@/services/api/booking.api";

interface PriceSummaryProps {
  vehicleType: "Car" | "Motorbike";
  packageType: "monthly" | "weekly" | "custom" | "hourly";
  selectedDates: Date[];
  zone?: string;
  slot?: string;
  parkingLot?: string;
  hourlyStartTime?: string;
  hourlyEndTime?: string;
}

// Fallback prices used only when API call fails
const FALLBACK_PRICES = {
  Car: {
    monthly: 1200000,
    weekly: 400000,
    daily: 80000,
    hourly: 15000,
  },
  Motorbike: {
    monthly: 300000,
    weekly: 100000,
    daily: 20000,
    hourly: 5000,
  },
};

const DISCOUNTS = {
  monthly: 0,
  weekly: 0,
  custom: 0,
  hourly: 0,
};

export function PriceSummary({
  vehicleType,
  packageType,
  selectedDates,
  zone,
  slot,
  parkingLot,
  hourlyStartTime,
  hourlyEndTime,
}: PriceSummaryProps) {
  const [pricingData, setPricingData] = useState<PackagePricingResponse[]>([]);
  const [pricingLoading, setPricingLoading] = useState(true);

  // Fetch pricing from API on mount
  useEffect(() => {
    const fetchPricing = async () => {
      try {
        setPricingLoading(true);
        const data = await bookingApi.getPackagePricing();
        setPricingData(data);
      } catch (error) {
        console.warn("Failed to fetch pricing, using fallback:", error);
      } finally {
        setPricingLoading(false);
      }
    };
    fetchPricing();
  }, []);

  // Build prices map from API data, falling back to hardcoded
  const prices = useMemo(() => {
    const result = { ...FALLBACK_PRICES };
    for (const item of pricingData) {
      const vt = item.vehicleType as "Car" | "Motorbike";
      const pt = item.packageType as keyof typeof FALLBACK_PRICES.Car;
      if (result[vt] && pt in result[vt]) {
        result[vt][pt] = item.price;
      }
    }
    return result;
  }, [pricingData]);
  const priceDetails = useMemo(() => {
    let basePrice: number;
    let hoursCount = 0;

    if (packageType === "hourly" && hourlyStartTime && hourlyEndTime) {
      // Calculate hours between start and end time
      const [startHour, startMin] = hourlyStartTime.split(":").map(Number);
      const [endHour, endMin] = hourlyEndTime.split(":").map(Number);
      const startMinutes = startHour * 60 + startMin;
      const endMinutes = endHour * 60 + endMin;
      hoursCount = Math.ceil((endMinutes - startMinutes) / 60);
      basePrice = prices[vehicleType].hourly * hoursCount;
    } else if (packageType === "custom") {
      basePrice = prices[vehicleType].daily * selectedDates.length;
    } else if (packageType === "weekly") {
      basePrice = prices[vehicleType].weekly;
    } else {
      basePrice = prices[vehicleType].monthly;
    }

    const discount = DISCOUNTS[packageType];
    const discountAmount = basePrice * discount;
    const finalPrice = basePrice - discountAmount;

    return {
      basePrice,
      discount,
      discountAmount,
      finalPrice,
      pricePerDay: prices[vehicleType].daily,
      pricePerHour: prices[vehicleType].hourly,
      daysCount: selectedDates.length,
      hoursCount,
    };
  }, [
    vehicleType,
    packageType,
    selectedDates,
    hourlyStartTime,
    hourlyEndTime,
    prices,
  ]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("vi-VN", {
      style: "currency",
      currency: "VND",
    }).format(amount);
  };

  return (
    <div className="rounded-xl sm:rounded-2xl border border-border bg-card p-4 sm:p-6 space-y-4 sm:space-y-6">
      <div className="flex items-center gap-2 sm:gap-3">
        <div className="flex h-8 w-8 sm:h-10 sm:w-10 items-center justify-center rounded-lg sm:rounded-xl bg-primary/10 shrink-0">
          <Calculator className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
        </div>
        <div className="min-w-0">
          <h3 className="font-semibold text-foreground text-sm sm:text-base">
            Chi tiết đơn hàng
          </h3>
          <p className="text-xs sm:text-sm text-muted-foreground">
            Tổng tiền dự kiến
          </p>
        </div>
      </div>

      {/* Booking Details */}
      <div className="space-y-2 sm:space-y-3">
        <div className="flex items-center justify-between text-xs sm:text-sm">
          <span className="flex items-center gap-1.5 sm:gap-2 text-muted-foreground">
            {vehicleType === "Car" ? (
              <Car className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            ) : (
              <Bike className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            )}
            Loại xe
          </span>
          <span className="font-medium">
            {vehicleType === "Car" ? "Ô tô" : "Xe máy"}
          </span>
        </div>

        {parkingLot && (
          <div className="flex items-center justify-between text-xs sm:text-sm">
            <span className="flex items-center gap-1.5 sm:gap-2 text-muted-foreground">
              <MapPin className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              Bãi xe
            </span>
            <span className="font-medium truncate max-w-[100px] sm:max-w-[150px]">
              {parkingLot}
            </span>
          </div>
        )}

        {zone && (
          <div className="flex items-center justify-between text-xs sm:text-sm">
            <span className="flex items-center gap-1.5 sm:gap-2 text-muted-foreground">
              <MapPin className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              Vị trí
            </span>
            <span className="font-medium">
              {zone}
              {slot ? ` - ${slot}` : ""}
            </span>
          </div>
        )}

        <div className="flex items-center justify-between text-xs sm:text-sm">
          <span className="flex items-center gap-1.5 sm:gap-2 text-muted-foreground">
            <Tag className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
            Gói dịch vụ
          </span>
          <span className="font-medium">
            {packageType === "monthly"
              ? "Tháng"
              : packageType === "weekly"
                ? "Tuần"
                : packageType === "hourly"
                  ? "Theo giờ"
                  : "Theo ngày"}
          </span>
        </div>

        {packageType === "hourly" && hourlyStartTime && hourlyEndTime && (
          <div className="flex items-center justify-between text-xs sm:text-sm">
            <span className="flex items-center gap-1.5 sm:gap-2 text-muted-foreground">
              <Clock className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              Thời gian
            </span>
            <span className="font-medium">
              {hourlyStartTime} - {hourlyEndTime}
            </span>
          </div>
        )}

        {packageType === "custom" && selectedDates.length > 0 && (
          <div className="flex items-center justify-between text-xs sm:text-sm">
            <span className="flex items-center gap-1.5 sm:gap-2 text-muted-foreground">
              <Calendar className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              Số ngày
            </span>
            <span className="font-medium">{selectedDates.length} ngày</span>
          </div>
        )}

        {packageType === "custom" && selectedDates.length > 0 && (
          <div className="flex items-center justify-between text-xs sm:text-sm">
            <span className="flex items-center gap-1.5 sm:gap-2 text-muted-foreground">
              <Clock className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
              Đơn giá
            </span>
            <span className="font-medium">
              {formatCurrency(priceDetails.pricePerDay)}/ngày
            </span>
          </div>
        )}
      </div>

      <div className="border-t border-border pt-3 sm:pt-4 space-y-2 sm:space-y-3">
        {/* Base price */}
        <div className="flex items-center justify-between text-xs sm:text-sm">
          <span className="text-muted-foreground">Thành tiền</span>
          <span className="font-medium">
            {formatCurrency(priceDetails.basePrice)}
          </span>
        </div>

        {/* Discount */}
        {priceDetails.discount > 0 && (
          <div className="flex items-center justify-between text-xs sm:text-sm">
            <span className="text-success">
              Giảm giá ({priceDetails.discount * 100}%)
            </span>
            <span className="font-medium text-success">
              -{formatCurrency(priceDetails.discountAmount)}
            </span>
          </div>
        )}

        {/* Final price */}
        <div className="flex items-center justify-between pt-2 sm:pt-3 border-t border-dashed border-border">
          <span className="text-sm sm:text-lg font-semibold text-foreground">
            Tổng cộng
          </span>
          <span className="text-lg sm:text-2xl font-bold text-primary">
            {formatCurrency(priceDetails.finalPrice)}
          </span>
        </div>
      </div>

      {/* Note */}
      <p className="text-[10px] sm:text-xs text-muted-foreground bg-muted/50 rounded-lg p-2 sm:p-3">
        * Giá trên là giá dự kiến. Giá thực tế có thể thay đổi tùy theo thời
        gian đậu thực tế.
      </p>
    </div>
  );
}
