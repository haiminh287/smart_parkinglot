import { useState, useEffect } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Settings,
  DollarSign,
  Clock,
  Bell,
  Shield,
  Database,
  Save,
  RefreshCw,
  MessageCircle,
  Phone,
  ExternalLink,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import { adminService } from "@/services/business";
import { toast } from "sonner";

interface PricingConfig {
  carHourly: number;
  carDaily: number;
  carMonthly: number;
  motorbikeHourly: number;
  motorbikeDaily: number;
  motorbikeMonthly: number;
}

interface SystemConfig {
  bookingHoldTime: number; // hours
  maxBookingsPerUser: number;
  autoCheckoutTime: number; // hours after end time
  maintenanceMode: boolean;
}

interface SupportConfig {
  zaloLink: string;
  facebookLink: string;
  telegramLink: string;
  hotline: string;
  email: string;
  workingHoursWeekday: string;
  workingHoursWeekend: string;
}

interface RawAdminConfig {
  pricePerHourCar?: number;
  pricePerHourMotorbike?: number;
  holdTimeMinutes?: number;
  maxNoShowCount?: number;
  autoCancelMinutes?: number;
  pricing?: {
    car_per_hour?: number;
    motorbike_per_hour?: number;
  };
  booking?: {
    hold_time_minutes?: number;
    max_no_show_count?: number;
    auto_cancel_minutes?: number;
  };
}

interface AdminConfigUpdatePayload {
  pricing: {
    car_per_hour: number;
    motorbike_per_hour: number;
    currency: string;
  };
  booking: {
    hold_time_minutes: number;
    max_no_show_count: number;
    auto_cancel_minutes: number;
  };
}

export default function AdminConfigPage() {
  const { toast: toastHook } = useToast();
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<
    "pricing" | "system" | "notifications" | "support"
  >("pricing");

  const [pricing, setPricing] = useState<PricingConfig>({
    carHourly: 15000,
    carDaily: 100000,
    carMonthly: 2000000,
    motorbikeHourly: 5000,
    motorbikeDaily: 30000,
    motorbikeMonthly: 500000,
  });

  const [system, setSystem] = useState<SystemConfig>({
    bookingHoldTime: 3,
    maxBookingsPerUser: 5,
    autoCheckoutTime: 2,
    maintenanceMode: false,
  });

  const [notifications, setNotifications] = useState({
    emailBookingConfirm: true,
    emailPaymentReminder: true,
    smsCheckIn: true,
    pushNotifications: true,
    adminAlerts: true,
  });

  const [support, setSupport] = useState<SupportConfig>({
    zaloLink: "https://zalo.me/0909123456",
    facebookLink: "https://m.me/parksmart",
    telegramLink: "https://t.me/parksmart_support",
    hotline: "1900 1234 56",
    email: "support@parksmart.vn",
    workingHoursWeekday: "7:00 - 22:00",
    workingHoursWeekend: "8:00 - 20:00",
  });

  // Load config from API
  useEffect(() => {
    const loadConfig = async () => {
      setIsLoading(true);
      try {
        const config = (await adminService.getConfig()) as RawAdminConfig;

        // Map API response to local state - handle both flat and nested formats
        const carPerHour =
          config.pricePerHourCar || config.pricing?.car_per_hour || 15000;
        const motorbikePerHour =
          config.pricePerHourMotorbike ||
          config.pricing?.motorbike_per_hour ||
          5000;
        const holdMinutes =
          config.holdTimeMinutes || config.booking?.hold_time_minutes || 15;
        const maxNoShow =
          config.maxNoShowCount || config.booking?.max_no_show_count || 2;
        const autoCancel =
          config.autoCancelMinutes || config.booking?.auto_cancel_minutes || 30;

        setPricing({
          carHourly: carPerHour,
          carDaily: carPerHour * 8,
          carMonthly: carPerHour * 8 * 25,
          motorbikeHourly: motorbikePerHour,
          motorbikeDaily: motorbikePerHour * 8,
          motorbikeMonthly: motorbikePerHour * 8 * 25,
        });

        setSystem({
          bookingHoldTime:
            holdMinutes >= 60 ? Math.floor(holdMinutes / 60) : holdMinutes,
          maxBookingsPerUser: maxNoShow,
          autoCheckoutTime:
            autoCancel >= 60 ? Math.floor(autoCancel / 60) : autoCancel,
          maintenanceMode: false,
        });

        toast.success("Đã tải cấu hình hệ thống");
      } catch (error) {
        console.error("Failed to load config:", error);
        toast.info("Sử dụng cấu hình mặc định");
      } finally {
        setIsLoading(false);
      }
    };

    loadConfig();
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const payload: AdminConfigUpdatePayload = {
        pricing: {
          car_per_hour: pricing.carHourly,
          motorbike_per_hour: pricing.motorbikeHourly,
          currency: "VND",
        },
        booking: {
          hold_time_minutes: system.bookingHoldTime * 60,
          max_no_show_count: system.maxBookingsPerUser,
          auto_cancel_minutes: system.autoCheckoutTime * 60,
        },
      };

      await adminService.updateConfig(payload);

      toast.success("Đã lưu cấu hình hệ thống");
      toastHook({
        title: "Đã lưu cấu hình",
        description: "Các thay đổi đã được áp dụng thành công.",
      });
    } catch (error) {
      console.error("Failed to save config:", error);
      toast.error("Không thể lưu cấu hình");
      toastHook({
        title: "Lỗi",
        description: "Không thể lưu cấu hình. Vui lòng thử lại.",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const tabs = [
    { id: "pricing" as const, label: "Bảng giá", icon: DollarSign },
    { id: "system" as const, label: "Hệ thống", icon: Settings },
    { id: "notifications" as const, label: "Thông báo", icon: Bell },
    { id: "support" as const, label: "Liên hệ hỗ trợ", icon: MessageCircle },
  ];

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between animate-fade-in">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Cấu hình hệ thống
            </h1>
            <p className="mt-1 text-muted-foreground">
              Quản lý giá cả, thông số và thông báo
            </p>
          </div>
          <Button
            className="gradient-primary gap-2"
            onClick={handleSave}
            disabled={isSaving || isLoading}
          >
            {isSaving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Đang lưu...
              </>
            ) : (
              <>
                <Save className="h-4 w-4" />
                Lưu thay đổi
              </>
            )}
          </Button>
        </div>

        <div className="flex flex-col gap-6 lg:flex-row">
          {/* Tabs */}
          <div className="w-full lg:w-64 shrink-0">
            <div className="rounded-2xl border border-border bg-card p-2 overflow-x-auto">
              <div className="flex lg:flex-col gap-1 min-w-max lg:min-w-0">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      "flex items-center gap-2 lg:gap-3 rounded-xl px-3 lg:px-4 py-2 lg:py-3 text-left text-xs lg:text-sm font-medium transition-all whitespace-nowrap lg:w-full",
                      activeTab === tab.id
                        ? "gradient-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                  >
                    <tab.icon className="h-4 w-4 lg:h-5 lg:w-5 shrink-0" />
                    <span className="hidden sm:inline lg:inline">
                      {tab.label}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1">
            {isLoading ? (
              <div className="rounded-2xl border border-border bg-card p-6 flex items-center justify-center min-h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <div className="rounded-2xl border border-border bg-card p-6 animate-slide-up">
                {/* Pricing Tab */}
                {activeTab === "pricing" && (
                  <div className="space-y-6">
                    <div>
                      <h2 className="text-lg font-semibold text-foreground">
                        Bảng giá ô tô
                      </h2>
                      <p className="text-sm text-muted-foreground">
                        Cấu hình giá cho xe ô tô
                      </p>
                    </div>

                    <div className="grid gap-4 sm:grid-cols-3">
                      <div>
                        <label className="block text-sm font-medium mb-1.5">
                          Giá/giờ (VNĐ)
                        </label>
                        <input
                          type="number"
                          value={pricing.carHourly}
                          onChange={(e) =>
                            setPricing({
                              ...pricing,
                              carHourly: Number(e.target.value),
                            })
                          }
                          className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1.5">
                          Giá/ngày (VNĐ)
                        </label>
                        <input
                          type="number"
                          value={pricing.carDaily}
                          onChange={(e) =>
                            setPricing({
                              ...pricing,
                              carDaily: Number(e.target.value),
                            })
                          }
                          className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1.5">
                          Giá/tháng (VNĐ)
                        </label>
                        <input
                          type="number"
                          value={pricing.carMonthly}
                          onChange={(e) =>
                            setPricing({
                              ...pricing,
                              carMonthly: Number(e.target.value),
                            })
                          }
                          className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                        />
                      </div>
                    </div>

                    <div className="border-t border-border pt-6">
                      <h2 className="text-lg font-semibold text-foreground">
                        Bảng giá xe máy
                      </h2>
                      <p className="text-sm text-muted-foreground">
                        Cấu hình giá cho xe máy
                      </p>
                    </div>

                    <div className="grid gap-4 sm:grid-cols-3">
                      <div>
                        <label className="block text-sm font-medium mb-1.5">
                          Giá/giờ (VNĐ)
                        </label>
                        <input
                          type="number"
                          value={pricing.motorbikeHourly}
                          onChange={(e) =>
                            setPricing({
                              ...pricing,
                              motorbikeHourly: Number(e.target.value),
                            })
                          }
                          className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1.5">
                          Giá/ngày (VNĐ)
                        </label>
                        <input
                          type="number"
                          value={pricing.motorbikeDaily}
                          onChange={(e) =>
                            setPricing({
                              ...pricing,
                              motorbikeDaily: Number(e.target.value),
                            })
                          }
                          className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1.5">
                          Giá/tháng (VNĐ)
                        </label>
                        <input
                          type="number"
                          value={pricing.motorbikeMonthly}
                          onChange={(e) =>
                            setPricing({
                              ...pricing,
                              motorbikeMonthly: Number(e.target.value),
                            })
                          }
                          className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                        />
                      </div>
                    </div>

                    <div className="rounded-xl bg-muted/50 p-4">
                      <p className="text-sm text-muted-foreground">
                        💡 <strong>Mẹo:</strong> Giá tháng nên được đặt thấp hơn
                        ~20% so với giá ngày x 30 để khuyến khích người dùng
                        đăng ký gói dài hạn.
                      </p>
                    </div>
                  </div>
                )}

                {/* System Tab */}
                {activeTab === "system" && (
                  <div className="space-y-6">
                    <div>
                      <h2 className="text-lg font-semibold text-foreground">
                        Cấu hình hệ thống
                      </h2>
                      <p className="text-sm text-muted-foreground">
                        Các thông số hoạt động của hệ thống
                      </p>
                    </div>

                    <div className="space-y-4">
                      <div className="flex items-center justify-between rounded-xl border border-border bg-background p-4">
                        <div className="flex items-center gap-4">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                            <Clock className="h-5 w-5 text-primary" />
                          </div>
                          <div>
                            <p className="font-medium text-foreground">
                              Thời gian giữ chỗ
                            </p>
                            <p className="text-sm text-muted-foreground">
                              Thời gian giữ chỗ khi chưa thanh toán
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            value={system.bookingHoldTime}
                            onChange={(e) =>
                              setSystem({
                                ...system,
                                bookingHoldTime: Number(e.target.value),
                              })
                            }
                            className="w-20 rounded-lg border border-border bg-card px-3 py-2 text-center focus:border-primary focus:outline-none"
                          />
                          <span className="text-muted-foreground">giờ</span>
                        </div>
                      </div>

                      <div className="flex items-center justify-between rounded-xl border border-border bg-background p-4">
                        <div className="flex items-center gap-4">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                            <Database className="h-5 w-5 text-primary" />
                          </div>
                          <div>
                            <p className="font-medium text-foreground">
                              Số booking tối đa/người
                            </p>
                            <p className="text-sm text-muted-foreground">
                              Giới hạn booking đang hoạt động
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            value={system.maxBookingsPerUser}
                            onChange={(e) =>
                              setSystem({
                                ...system,
                                maxBookingsPerUser: Number(e.target.value),
                              })
                            }
                            className="w-20 rounded-lg border border-border bg-card px-3 py-2 text-center focus:border-primary focus:outline-none"
                          />
                          <span className="text-muted-foreground">booking</span>
                        </div>
                      </div>

                      <div className="flex items-center justify-between rounded-xl border border-border bg-background p-4">
                        <div className="flex items-center gap-4">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                            <RefreshCw className="h-5 w-5 text-primary" />
                          </div>
                          <div>
                            <p className="font-medium text-foreground">
                              Auto checkout
                            </p>
                            <p className="text-sm text-muted-foreground">
                              Tự động checkout sau thời gian kết thúc
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            value={system.autoCheckoutTime}
                            onChange={(e) =>
                              setSystem({
                                ...system,
                                autoCheckoutTime: Number(e.target.value),
                              })
                            }
                            className="w-20 rounded-lg border border-border bg-card px-3 py-2 text-center focus:border-primary focus:outline-none"
                          />
                          <span className="text-muted-foreground">giờ</span>
                        </div>
                      </div>

                      <div className="flex items-center justify-between rounded-xl border border-warning/30 bg-warning/5 p-4">
                        <div className="flex items-center gap-4">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-warning/10">
                            <Shield className="h-5 w-5 text-warning" />
                          </div>
                          <div>
                            <p className="font-medium text-foreground">
                              Chế độ bảo trì
                            </p>
                            <p className="text-sm text-muted-foreground">
                              Tạm ngưng nhận booking mới
                            </p>
                          </div>
                        </div>
                        <button
                          onClick={() =>
                            setSystem({
                              ...system,
                              maintenanceMode: !system.maintenanceMode,
                            })
                          }
                          className={cn(
                            "relative h-6 w-11 rounded-full transition-colors",
                            system.maintenanceMode ? "bg-warning" : "bg-muted",
                          )}
                        >
                          <div
                            className={cn(
                              "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform",
                              system.maintenanceMode
                                ? "translate-x-5"
                                : "translate-x-0.5",
                            )}
                          />
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Notifications Tab */}
                {activeTab === "notifications" && (
                  <div className="space-y-6">
                    <div>
                      <h2 className="text-lg font-semibold text-foreground">
                        Cấu hình thông báo
                      </h2>
                      <p className="text-sm text-muted-foreground">
                        Quản lý các loại thông báo gửi đến người dùng
                      </p>
                    </div>

                    <div className="space-y-4">
                      {[
                        {
                          key: "emailBookingConfirm",
                          label: "Email xác nhận booking",
                          desc: "Gửi email khi đặt chỗ thành công",
                        },
                        {
                          key: "emailPaymentReminder",
                          label: "Email nhắc thanh toán",
                          desc: "Nhắc nhở khi sắp hết thời gian giữ chỗ",
                        },
                        {
                          key: "smsCheckIn",
                          label: "SMS check-in",
                          desc: "Gửi SMS khi xe check-in",
                        },
                        {
                          key: "pushNotifications",
                          label: "Push notifications",
                          desc: "Thông báo đẩy trên trình duyệt",
                        },
                        {
                          key: "adminAlerts",
                          label: "Cảnh báo admin",
                          desc: "Thông báo cho admin khi có sự cố",
                        },
                      ].map((item) => (
                        <div
                          key={item.key}
                          className="flex items-center justify-between rounded-xl border border-border bg-background p-4"
                        >
                          <div className="flex items-center gap-4">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                              <Bell className="h-5 w-5 text-primary" />
                            </div>
                            <div>
                              <p className="font-medium text-foreground">
                                {item.label}
                              </p>
                              <p className="text-sm text-muted-foreground">
                                {item.desc}
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={() =>
                              setNotifications((prev) => ({
                                ...prev,
                                [item.key]:
                                  !prev[item.key as keyof typeof notifications],
                              }))
                            }
                            className={cn(
                              "relative h-6 w-11 rounded-full transition-colors",
                              notifications[
                                item.key as keyof typeof notifications
                              ]
                                ? "bg-primary"
                                : "bg-muted",
                            )}
                          >
                            <div
                              className={cn(
                                "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform",
                                notifications[
                                  item.key as keyof typeof notifications
                                ]
                                  ? "translate-x-5"
                                  : "translate-x-0.5",
                              )}
                            />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Support Tab */}
                {activeTab === "support" && (
                  <div className="space-y-6">
                    <div>
                      <h2 className="text-lg font-semibold text-foreground">
                        Cấu hình liên hệ hỗ trợ
                      </h2>
                      <p className="text-sm text-muted-foreground">
                        Quản lý thông tin liên hệ hiển thị cho người dùng
                      </p>
                    </div>

                    <div className="space-y-4">
                      {/* Zalo */}
                      <div className="flex items-center justify-between rounded-xl border border-border bg-background p-4">
                        <div className="flex items-center gap-4">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10">
                            <MessageCircle className="h-5 w-5 text-blue-500" />
                          </div>
                          <div>
                            <p className="font-medium text-foreground">Zalo</p>
                            <p className="text-sm text-muted-foreground">
                              Link chat Zalo nhân viên
                            </p>
                          </div>
                        </div>
                        <input
                          type="text"
                          value={support.zaloLink}
                          onChange={(e) =>
                            setSupport({ ...support, zaloLink: e.target.value })
                          }
                          placeholder="https://zalo.me/..."
                          className="w-64 rounded-lg border border-border bg-card px-3 py-2 text-sm focus:border-primary focus:outline-none"
                        />
                      </div>

                      {/* Facebook */}
                      <div className="flex items-center justify-between rounded-xl border border-border bg-background p-4">
                        <div className="flex items-center gap-4">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600/10">
                            <ExternalLink className="h-5 w-5 text-blue-600" />
                          </div>
                          <div>
                            <p className="font-medium text-foreground">
                              Facebook Messenger
                            </p>
                            <p className="text-sm text-muted-foreground">
                              Link Messenger fanpage
                            </p>
                          </div>
                        </div>
                        <input
                          type="text"
                          value={support.facebookLink}
                          onChange={(e) =>
                            setSupport({
                              ...support,
                              facebookLink: e.target.value,
                            })
                          }
                          placeholder="https://m.me/..."
                          className="w-64 rounded-lg border border-border bg-card px-3 py-2 text-sm focus:border-primary focus:outline-none"
                        />
                      </div>

                      {/* Telegram */}
                      <div className="flex items-center justify-between rounded-xl border border-border bg-background p-4">
                        <div className="flex items-center gap-4">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-sky-500/10">
                            <ExternalLink className="h-5 w-5 text-sky-500" />
                          </div>
                          <div>
                            <p className="font-medium text-foreground">
                              Telegram
                            </p>
                            <p className="text-sm text-muted-foreground">
                              Link chat Telegram
                            </p>
                          </div>
                        </div>
                        <input
                          type="text"
                          value={support.telegramLink}
                          onChange={(e) =>
                            setSupport({
                              ...support,
                              telegramLink: e.target.value,
                            })
                          }
                          placeholder="https://t.me/..."
                          className="w-64 rounded-lg border border-border bg-card px-3 py-2 text-sm focus:border-primary focus:outline-none"
                        />
                      </div>

                      {/* Hotline */}
                      <div className="flex items-center justify-between rounded-xl border border-border bg-background p-4">
                        <div className="flex items-center gap-4">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                            <Phone className="h-5 w-5 text-primary" />
                          </div>
                          <div>
                            <p className="font-medium text-foreground">
                              Hotline
                            </p>
                            <p className="text-sm text-muted-foreground">
                              Số điện thoại hỗ trợ
                            </p>
                          </div>
                        </div>
                        <input
                          type="text"
                          value={support.hotline}
                          onChange={(e) =>
                            setSupport({ ...support, hotline: e.target.value })
                          }
                          placeholder="1900 xxxx xx"
                          className="w-64 rounded-lg border border-border bg-card px-3 py-2 text-sm focus:border-primary focus:outline-none"
                        />
                      </div>

                      {/* Email */}
                      <div className="flex items-center justify-between rounded-xl border border-border bg-background p-4">
                        <div className="flex items-center gap-4">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/10">
                            <MessageCircle className="h-5 w-5 text-accent" />
                          </div>
                          <div>
                            <p className="font-medium text-foreground">Email</p>
                            <p className="text-sm text-muted-foreground">
                              Email hỗ trợ khách hàng
                            </p>
                          </div>
                        </div>
                        <input
                          type="email"
                          value={support.email}
                          onChange={(e) =>
                            setSupport({ ...support, email: e.target.value })
                          }
                          placeholder="support@example.com"
                          className="w-64 rounded-lg border border-border bg-card px-3 py-2 text-sm focus:border-primary focus:outline-none"
                        />
                      </div>
                    </div>

                    <div className="border-t border-border pt-6">
                      <h2 className="text-lg font-semibold text-foreground">
                        Giờ làm việc
                      </h2>
                      <p className="text-sm text-muted-foreground">
                        Thời gian nhân viên hỗ trợ trực tiếp
                      </p>
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <label className="block text-sm font-medium mb-1.5">
                          Thứ 2 - Thứ 6
                        </label>
                        <input
                          type="text"
                          value={support.workingHoursWeekday}
                          onChange={(e) =>
                            setSupport({
                              ...support,
                              workingHoursWeekday: e.target.value,
                            })
                          }
                          placeholder="7:00 - 22:00"
                          className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1.5">
                          Thứ 7 - Chủ nhật
                        </label>
                        <input
                          type="text"
                          value={support.workingHoursWeekend}
                          onChange={(e) =>
                            setSupport({
                              ...support,
                              workingHoursWeekend: e.target.value,
                            })
                          }
                          placeholder="8:00 - 20:00"
                          className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none"
                        />
                      </div>
                    </div>

                    <div className="rounded-xl bg-muted/50 p-4">
                      <p className="text-sm text-muted-foreground">
                        💡 <strong>Lưu ý:</strong> Các thông tin này sẽ hiển thị
                        trên trang Hỗ trợ cho người dùng. Đảm bảo các link và số
                        điện thoại chính xác.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
