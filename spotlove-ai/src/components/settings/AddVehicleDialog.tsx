import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Car, Bike, Loader2, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { vehicleApi } from "@/services";
import type { CreateVehicleRequest } from "@/services/api/vehicle.api";
import { useToast } from "@/hooks/use-toast";

interface AddVehicleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onVehicleAdded: (vehicle: {
    id: string;
    licensePlate: string;
    vehicleType: "Car" | "Motorbike";
    name?: string;
    brand?: string;
    model?: string;
    isDefault: boolean;
  }) => void;
}

export function AddVehicleDialog({
  open,
  onOpenChange,
  onVehicleAdded,
}: AddVehicleDialogProps) {
  const { toast } = useToast();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState<CreateVehicleRequest>({
    licensePlate: "",
    vehicleType: "Car",
    brand: "",
    model: "",
    color: "",
    isDefault: false,
  });

  const handleSubmit = async () => {
    if (!formData.licensePlate.trim()) {
      toast({
        title: "Lỗi",
        description: "Vui lòng nhập biển số xe",
        variant: "destructive",
      });
      return;
    }

    // Basic Vietnam license plate validation
    const plateRegex = /^[0-9]{2}[A-Z]{1,2}[-.\s]?[0-9]{3,5}[.\s]?[0-9]{0,2}$/i;
    if (!plateRegex.test(formData.licensePlate.replace(/\s/g, ""))) {
      toast({
        title: "Lỗi",
        description: "Biển số xe không hợp lệ (VD: 51F-123.45)",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);
    try {
      const vehicle = await vehicleApi.createVehicle({
        ...formData,
        licensePlate: formData.licensePlate.trim().toUpperCase(),
      });

      onVehicleAdded({
        id: vehicle.id,
        licensePlate: vehicle.licensePlate,
        vehicleType: vehicle.vehicleType,
        brand: vehicle.brand,
        model: vehicle.model,
        isDefault: vehicle.isDefault,
      });

      toast({
        title: "Thành công",
        description: `Đã thêm xe ${vehicle.licensePlate}`,
      });

      // Reset form
      setFormData({
        licensePlate: "",
        vehicleType: "Car",
        brand: "",
        model: "",
        color: "",
        isDefault: false,
      });
      onOpenChange(false);
    } catch (error: unknown) {
      console.error("Failed to add vehicle:", error);
      const err = error as {
        response?: { data?: { message?: string; licensePlate?: string[] } };
      };
      const message =
        err.response?.data?.licensePlate?.[0] ||
        err.response?.data?.message ||
        "Không thể thêm phương tiện. Vui lòng thử lại.";
      toast({
        title: "Lỗi",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5 text-primary" />
            Thêm phương tiện mới
          </DialogTitle>
          <DialogDescription>
            Nhập thông tin phương tiện để đăng ký vào hệ thống
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-2">
          {/* Vehicle Type Selection */}
          <div>
            <label className="mb-2 block text-sm font-medium">
              Loại phương tiện
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() =>
                  setFormData((prev) => ({ ...prev, vehicleType: "Car" }))
                }
                className={cn(
                  "flex items-center gap-3 rounded-xl border-2 p-3 transition-all",
                  formData.vehicleType === "Car"
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50",
                )}
              >
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-lg",
                    formData.vehicleType === "Car"
                      ? "bg-primary/10 text-primary"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  <Car className="h-5 w-5" />
                </div>
                <span className="font-medium text-sm">Ô tô</span>
              </button>
              <button
                type="button"
                onClick={() =>
                  setFormData((prev) => ({ ...prev, vehicleType: "Motorbike" }))
                }
                className={cn(
                  "flex items-center gap-3 rounded-xl border-2 p-3 transition-all",
                  formData.vehicleType === "Motorbike"
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50",
                )}
              >
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-lg",
                    formData.vehicleType === "Motorbike"
                      ? "bg-primary/10 text-primary"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  <Bike className="h-5 w-5" />
                </div>
                <span className="font-medium text-sm">Xe máy</span>
              </button>
            </div>
          </div>

          {/* License Plate */}
          <div>
            <label className="mb-2 block text-sm font-medium">
              Biển số xe <span className="text-destructive">*</span>
            </label>
            <input
              type="text"
              value={formData.licensePlate}
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  licensePlate: e.target.value.toUpperCase(),
                }))
              }
              placeholder="VD: 51F-123.45"
              className="w-full rounded-xl border border-border bg-background px-4 py-2.5 font-mono text-lg uppercase focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>

          {/* Brand & Model */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-2 block text-sm font-medium">Hãng xe</label>
              <input
                type="text"
                value={formData.brand || ""}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, brand: e.target.value }))
                }
                placeholder="VD: Toyota"
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium">Model</label>
              <input
                type="text"
                value={formData.model || ""}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, model: e.target.value }))
                }
                placeholder="VD: Camry"
                className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
          </div>

          {/* Color */}
          <div>
            <label className="mb-2 block text-sm font-medium">Màu sắc</label>
            <input
              type="text"
              value={formData.color || ""}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, color: e.target.value }))
              }
              placeholder="VD: Trắng"
              className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>

          {/* Set as default */}
          <label className="flex items-center gap-3 cursor-pointer">
            <button
              type="button"
              onClick={() =>
                setFormData((prev) => ({ ...prev, isDefault: !prev.isDefault }))
              }
              className={cn(
                "relative h-6 w-11 rounded-full transition-colors",
                formData.isDefault ? "bg-primary" : "bg-muted",
              )}
            >
              <div
                className={cn(
                  "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform",
                  formData.isDefault ? "translate-x-5" : "translate-x-0.5",
                )}
              />
            </button>
            <span className="text-sm font-medium">
              Đặt làm phương tiện mặc định
            </span>
          </label>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Hủy
            </Button>
            <Button
              className="flex-1 gradient-primary"
              onClick={handleSubmit}
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Đang thêm...
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4 mr-2" />
                  Thêm xe
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
