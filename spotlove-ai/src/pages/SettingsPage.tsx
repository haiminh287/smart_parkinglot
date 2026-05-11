import { useState, useEffect } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  User,
  Bell,
  Shield,
  CreditCard,
  Sun,
  Moon,
  Smartphone,
  Mail,
  Car,
  Plus,
  Trash2,
  Edit2,
  Check,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/contexts/use-theme";
import {
  vehicleService,
  notificationService,
  authService,
} from "@/services/business";
import { useAuth } from "@/contexts/use-auth";
import { useToast } from "@/hooks/use-toast";
import { AddVehicleDialog } from "@/components/settings/AddVehicleDialog";
import type { NotificationType } from "@/store/slices/notificationSlice";

interface Vehicle {
  id: string;
  licensePlate: string;
  vehicleType: "Car" | "Motorbike";
  name?: string;
  brand?: string;
  model?: string;
  isDefault: boolean;
}

type SettingsTab =
  | "profile"
  | "vehicles"
  | "notifications"
  | "appearance"
  | "security";

const tabs = [
  { id: "profile" as const, label: "Hồ sơ", icon: User },
  { id: "vehicles" as const, label: "Phương tiện", icon: Car },
  { id: "notifications" as const, label: "Thông báo", icon: Bell },
  { id: "appearance" as const, label: "Giao diện", icon: Sun },
  { id: "security" as const, label: "Bảo mật", icon: Shield },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loadingVehicles, setLoadingVehicles] = useState(false);
  const { theme, setTheme } = useTheme();
  const { user } = useAuth();
  const { toast } = useToast();
  const [showAddVehicle, setShowAddVehicle] = useState(false);

  const [notifications, setNotifications] = useState({
    email: true,
    push: true,
    sms: false,
    bookingReminder: true,
    promotions: false,
  });
  const [loadingPreferences, setLoadingPreferences] = useState(false);

  // Password change states
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);

  // Fetch vehicles on mount
  useEffect(() => {
    const fetchVehicles = async () => {
      setLoadingVehicles(true);
      try {
        const response = await vehicleService.getAll();
        setVehicles(response.results);
      } catch (error) {
        console.error("Failed to fetch vehicles:", error);
        toast({
          title: "Lỗi",
          description: "Không thể tải danh sách phương tiện",
          variant: "destructive",
        });
      } finally {
        setLoadingVehicles(false);
      }
    };

    fetchVehicles();
  }, [toast]);

  // Fetch notification preferences
  useEffect(() => {
    const fetchPreferences = async () => {
      setLoadingPreferences(true);
      try {
        const prefs = await notificationService.getPreferences();
        setNotifications({
          email: prefs.emailEnabled,
          push: prefs.pushEnabled,
          sms: false, // Backend doesn't have SMS yet
          bookingReminder: (prefs.types as string[]).includes("booking"),
          promotions: (prefs.types as string[]).includes("promotion"),
        });
      } catch (error) {
        console.error("Failed to fetch preferences:", error);
      } finally {
        setLoadingPreferences(false);
      }
    };

    if (activeTab === "notifications") {
      fetchPreferences();
    }
  }, [activeTab]);

  const handleDeleteVehicle = async (vehicleId: string) => {
    try {
      await vehicleService.delete(vehicleId);
      setVehicles(vehicles.filter((v) => v.id !== vehicleId));
      toast({
        title: "Thành công",
        description: "Đã xóa phương tiện",
      });
    } catch (error) {
      console.error("Failed to delete vehicle:", error);
      toast({
        title: "Lỗi",
        description: "Không thể xóa phương tiện",
        variant: "destructive",
      });
    }
  };

  const handleSetDefaultVehicle = async (vehicleId: string) => {
    try {
      const result = await vehicleService.setDefault(vehicleId);
      if (result.success && result.vehicle) {
        setVehicles(
          vehicles.map((v) => ({
            ...v,
            isDefault: v.id === result.vehicle!.id,
          })),
        );
        toast({
          title: "Thành công",
          description: "Đã đặt làm phương tiện mặc định",
        });
      }
    } catch (error) {
      console.error("Failed to set default:", error);
      toast({
        title: "Lỗi",
        description: "Không thể đặt làm mặc định",
        variant: "destructive",
      });
    }
  };

  const handleUpdateNotificationPreference = async (
    key: string,
    value: boolean,
  ) => {
    setNotifications((prev) => ({ ...prev, [key]: value }));

    try {
      const types: string[] = [];
      if (notifications.bookingReminder) types.push("booking");
      if (notifications.promotions) types.push("promotion");

      await notificationService.updatePreferences({
        pushEnabled: key === "push" ? value : notifications.push,
        emailEnabled: key === "email" ? value : notifications.email,
        types: types as NotificationType[],
      });

      toast({
        title: "Thành công",
        description: "Đã cập nhật cài đặt thông báo",
      });
    } catch (error) {
      console.error("Failed to update preferences:", error);
      toast({
        title: "Lỗi",
        description: "Không thể cập nhật cài đặt",
        variant: "destructive",
      });
    }
  };

  const handleChangePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      toast({
        title: "Lỗi",
        description: "Vui lòng điền đầy đủ thông tin",
        variant: "destructive",
      });
      return;
    }

    if (newPassword !== confirmPassword) {
      toast({
        title: "Lỗi",
        description: "Mật khẩu xác nhận không khớp",
        variant: "destructive",
      });
      return;
    }

    setChangingPassword(true);
    try {
      await authService.changePassword(currentPassword, newPassword);

      toast({
        title: "Thành công",
        description: "Mật khẩu đã được cập nhật",
      });

      // Clear fields
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (error) {
      console.error("Failed to change password:", error);
      toast({
        title: "Lỗi",
        description: "Không thể đổi mật khẩu. Kiểm tra lại mật khẩu hiện tại.",
        variant: "destructive",
      });
    } finally {
      setChangingPassword(false);
    }
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="animate-fade-in">
          <h1 className="text-2xl font-bold text-foreground">Cài đặt</h1>
          <p className="mt-1 text-muted-foreground">
            Quản lý tài khoản và tùy chỉnh ứng dụng
          </p>
        </div>

        <div className="flex flex-col gap-6 lg:flex-row">
          {/* Tabs Sidebar */}
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
            <div className="rounded-2xl border border-border bg-card p-6 animate-slide-up">
              {/* Profile Tab */}
              {activeTab === "profile" && (
                <div className="space-y-6">
                  <h2 className="text-lg font-semibold text-foreground">
                    Thông tin cá nhân
                  </h2>

                  {/* Avatar */}
                  <div className="flex items-center gap-4">
                    <div className="relative">
                      <div className="flex h-20 w-20 items-center justify-center rounded-2xl gradient-primary text-3xl font-bold text-primary-foreground">
                        {user?.username?.charAt(0).toUpperCase() || "U"}
                      </div>
                      <button className="absolute -bottom-1 -right-1 flex h-8 w-8 items-center justify-center rounded-full border-2 border-card bg-accent text-accent-foreground">
                        <Edit2 className="h-4 w-4" />
                      </button>
                    </div>
                    <div>
                      <p className="font-semibold text-foreground">
                        {user?.username || "Người dùng"}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {user?.email || "user@email.com"}
                      </p>
                    </div>
                  </div>

                  {/* Form Fields */}
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="mb-2 block text-sm font-medium">
                        Họ và tên
                      </label>
                      <input
                        type="text"
                        defaultValue={user?.username || ""}
                        className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>
                    <div>
                      <label className="mb-2 block text-sm font-medium">
                        Số điện thoại
                      </label>
                      <input
                        type="tel"
                        defaultValue={user?.phone || ""}
                        className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="mb-2 block text-sm font-medium">
                        Email
                      </label>
                      <input
                        type="email"
                        defaultValue={user?.email || ""}
                        className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                        disabled
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="mb-2 block text-sm font-medium">
                        Địa chỉ
                      </label>
                      <input
                        type="text"
                        defaultValue={user?.address || ""}
                        className="w-full rounded-xl border border-border bg-background px-4 py-2.5 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                    </div>
                  </div>

                  <Button variant="hero" disabled>
                    Lưu thay đổi (Coming soon)
                  </Button>
                </div>
              )}

              {/* Vehicles Tab */}
              {activeTab === "vehicles" && (
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold text-foreground">
                      Phương tiện của tôi
                    </h2>
                    <Button
                      variant="accent"
                      size="sm"
                      className="gap-2"
                      onClick={() => setShowAddVehicle(true)}
                    >
                      <Plus className="h-4 w-4" />
                      Thêm xe
                    </Button>
                  </div>

                  {loadingVehicles ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-primary" />
                      <span className="ml-2 text-muted-foreground">
                        Đang tải...
                      </span>
                    </div>
                  ) : vehicles.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <Car className="h-12 w-12 text-muted-foreground/50 mb-3" />
                      <p className="text-muted-foreground">
                        Chưa có phương tiện nào
                      </p>
                      <Button
                        variant="accent"
                        size="sm"
                        className="gap-2 mt-4"
                        onClick={() => setShowAddVehicle(true)}
                      >
                        <Plus className="h-4 w-4" />
                        Thêm xe đầu tiên
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {vehicles.map((vehicle) => (
                        <div
                          key={vehicle.id}
                          className="flex items-center justify-between rounded-xl border border-border bg-background p-4"
                        >
                          <div className="flex items-center gap-4">
                            <div
                              className={cn(
                                "flex h-12 w-12 items-center justify-center rounded-xl",
                                vehicle.vehicleType === "Car"
                                  ? "bg-primary/10 text-primary"
                                  : "bg-accent/10 text-accent",
                              )}
                            >
                              {vehicle.vehicleType === "Car" ? "🚗" : "🏍️"}
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <p className="font-semibold text-foreground">
                                  {vehicle.licensePlate}
                                </p>
                                {vehicle.isDefault && (
                                  <Badge className="bg-success/10 text-success">
                                    Mặc định
                                  </Badge>
                                )}
                              </div>
                              <p className="text-sm text-muted-foreground">
                                {vehicle.brand && vehicle.model
                                  ? `${vehicle.brand} ${vehicle.model}`
                                  : vehicle.name || ""}
                                {(vehicle.brand ||
                                  vehicle.model ||
                                  vehicle.name) &&
                                  " • "}
                                {vehicle.vehicleType === "Car"
                                  ? "Ô tô"
                                  : "Xe máy"}
                              </p>
                            </div>
                          </div>
                          <div className="flex gap-2">
                            {!vehicle.isDefault && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() =>
                                  handleSetDefaultVehicle(vehicle.id)
                                }
                                className="text-xs"
                              >
                                Đặt mặc định
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDeleteVehicle(vehicle.id)}
                              className="text-destructive hover:text-destructive"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Notifications Tab */}
              {activeTab === "notifications" && (
                <div className="space-y-6">
                  <h2 className="text-lg font-semibold text-foreground">
                    Cài đặt thông báo
                  </h2>

                  {loadingPreferences ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-primary" />
                      <span className="ml-2 text-muted-foreground">
                        Đang tải...
                      </span>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {[
                        {
                          key: "email",
                          label: "Email",
                          desc: "Nhận thông báo qua email",
                          icon: Mail,
                        },
                        {
                          key: "push",
                          label: "Thông báo đẩy",
                          desc: "Nhận thông báo trên trình duyệt",
                          icon: Bell,
                        },
                        {
                          key: "sms",
                          label: "SMS",
                          desc: "Nhận thông báo qua tin nhắn (Coming soon)",
                          icon: Smartphone,
                        },
                        {
                          key: "bookingReminder",
                          label: "Nhắc nhở booking",
                          desc: "Nhắc nhở trước khi đến giờ đặt",
                          icon: Car,
                        },
                        {
                          key: "promotions",
                          label: "Khuyến mãi",
                          desc: "Nhận thông tin ưu đãi và khuyến mãi",
                          icon: CreditCard,
                        },
                      ].map((item) => (
                        <div
                          key={item.key}
                          className="flex items-center justify-between rounded-xl border border-border bg-background p-4"
                        >
                          <div className="flex items-center gap-4">
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                              <item.icon className="h-5 w-5 text-primary" />
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
                              handleUpdateNotificationPreference(
                                item.key,
                                !notifications[
                                  item.key as keyof typeof notifications
                                ],
                              )
                            }
                            disabled={item.key === "sms"}
                            className={cn(
                              "relative h-6 w-11 rounded-full transition-colors",
                              notifications[
                                item.key as keyof typeof notifications
                              ]
                                ? "bg-primary"
                                : "bg-muted",
                              item.key === "sms" &&
                                "opacity-50 cursor-not-allowed",
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
                  )}
                </div>
              )}

              {/* Appearance Tab */}
              {activeTab === "appearance" && (
                <div className="space-y-6">
                  <h2 className="text-lg font-semibold text-foreground">
                    Giao diện
                  </h2>

                  <div>
                    <label className="mb-3 block text-sm font-medium">
                      Chế độ hiển thị
                    </label>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <button
                        onClick={() => setTheme("light")}
                        className={cn(
                          "flex items-center gap-4 rounded-xl border-2 p-4 transition-all",
                          theme === "light"
                            ? "border-primary bg-primary/5"
                            : "border-border hover:border-primary/50",
                        )}
                      >
                        <div
                          className={cn(
                            "flex h-12 w-12 items-center justify-center rounded-xl",
                            theme === "light"
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted",
                          )}
                        >
                          <Sun className="h-6 w-6" />
                        </div>
                        <div className="text-left">
                          <p className="font-medium text-foreground">
                            Chế độ sáng
                          </p>
                          <p className="text-sm text-muted-foreground">
                            Giao diện sáng, dễ nhìn ban ngày
                          </p>
                        </div>
                        {theme === "light" && (
                          <Check className="ml-auto h-5 w-5 text-primary" />
                        )}
                      </button>

                      <button
                        onClick={() => setTheme("dark")}
                        className={cn(
                          "flex items-center gap-4 rounded-xl border-2 p-4 transition-all",
                          theme === "dark"
                            ? "border-primary bg-primary/5"
                            : "border-border hover:border-primary/50",
                        )}
                      >
                        <div
                          className={cn(
                            "flex h-12 w-12 items-center justify-center rounded-xl",
                            theme === "dark"
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted",
                          )}
                        >
                          <Moon className="h-6 w-6" />
                        </div>
                        <div className="text-left">
                          <p className="font-medium text-foreground">
                            Chế độ tối
                          </p>
                          <p className="text-sm text-muted-foreground">
                            Giao diện tối, dễ nhìn ban đêm
                          </p>
                        </div>
                        {theme === "dark" && (
                          <Check className="ml-auto h-5 w-5 text-primary" />
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Security Tab */}
              {activeTab === "security" && (
                <div className="space-y-6">
                  <h2 className="text-lg font-semibold text-foreground">
                    Bảo mật
                  </h2>

                  <div className="space-y-4">
                    <div className="rounded-xl border border-border bg-background p-4">
                      <h3 className="font-medium text-foreground">
                        Đổi mật khẩu
                      </h3>
                      <p className="mb-4 text-sm text-muted-foreground">
                        Cập nhật mật khẩu để bảo vệ tài khoản
                      </p>
                      <div className="space-y-3">
                        <input
                          type="password"
                          placeholder="Mật khẩu hiện tại"
                          value={currentPassword}
                          onChange={(e) => setCurrentPassword(e.target.value)}
                          className="w-full rounded-xl border border-border bg-card px-4 py-2.5 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                        />
                        <input
                          type="password"
                          placeholder="Mật khẩu mới"
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          className="w-full rounded-xl border border-border bg-card px-4 py-2.5 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                        />
                        <input
                          type="password"
                          placeholder="Xác nhận mật khẩu mới"
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          className="w-full rounded-xl border border-border bg-card px-4 py-2.5 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                        />
                      </div>
                      <Button
                        variant="hero"
                        className="mt-4 gap-2"
                        onClick={handleChangePassword}
                        disabled={changingPassword}
                      >
                        {changingPassword && (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        )}
                        Cập nhật mật khẩu
                      </Button>
                    </div>

                    <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4">
                      <h3 className="font-medium text-destructive">
                        Xóa tài khoản
                      </h3>
                      <p className="mb-4 text-sm text-muted-foreground">
                        Xóa vĩnh viễn tài khoản và tất cả dữ liệu liên quan
                      </p>
                      <Button variant="destructive" size="sm" disabled>
                        Xóa tài khoản
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Add Vehicle Dialog */}
      <AddVehicleDialog
        open={showAddVehicle}
        onOpenChange={setShowAddVehicle}
        onVehicleAdded={(vehicle) => {
          setVehicles((prev) => [...prev, vehicle]);
        }}
      />
    </MainLayout>
  );
}
