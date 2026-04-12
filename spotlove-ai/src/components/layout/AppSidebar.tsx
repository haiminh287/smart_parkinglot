import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  CalendarPlus,
  History,
  MapPin,
  Camera,
  MessageCircle,
  Settings,
  Car,
  Sun,
  Moon,
  LogOut,
  Users,
  Cog,
  Shield,
  AlertTriangle,
  Banknote,
  ScanLine,
  ScanSearch,
  Cpu,
  DollarSign,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/contexts/use-theme";
import { useAuth } from "@/contexts/use-auth";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { useNavigate } from "react-router-dom";

const userNavItems = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/" },
  { icon: CalendarPlus, label: "Đặt chỗ", path: "/booking" },
  { icon: ScanLine, label: "Check In/Out", path: "/check-in-out" },
  { icon: History, label: "Lịch sử", path: "/history" },
  { icon: MapPin, label: "Bản đồ", path: "/map" },
  { icon: Camera, label: "Camera", path: "/cameras" },
  { icon: ScanSearch, label: "Nhận diện BS", path: "/detection-history" },
  { icon: AlertTriangle, label: "Panic", path: "/panic" },
  { icon: Banknote, label: "Nhận diện tiền", path: "/banknote-detection" },
  { icon: MessageCircle, label: "Hỗ trợ", path: "/support" },
  { icon: Settings, label: "Cài đặt", path: "/settings" },
];

const adminNavItems = [
  { icon: LayoutDashboard, label: "Dashboard", path: "/admin/dashboard" },
  { icon: DollarSign, label: "Doanh thu", path: "/admin/revenue" },
  { icon: Users, label: "Người dùng", path: "/admin/users" },
  { icon: MapPin, label: "Quản lý Zone", path: "/admin/zones" },
  { icon: Car, label: "Quản lý Slot", path: "/admin/slots" },
  { icon: Camera, label: "Camera", path: "/admin/cameras" },
  { icon: Shield, label: "Vi phạm", path: "/admin/violations" },
  { icon: Cpu, label: "ESP32 IoT", path: "/admin/esp32" },
  { icon: Cog, label: "Cấu hình", path: "/admin/config" },
];

export function AppSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { user, logout, isAuthenticated } = useAuth();

  // Default to userNavItems if role not loaded yet
  const navItems = user?.role === "admin" ? adminNavItems : userNavItems;

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 h-screen border-r border-sidebar-border bg-sidebar transition-all duration-300 ease-in-out",
        "w-full md:w-64",
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between border-b border-sidebar-border px-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl gradient-primary shadow-glow">
            <Car className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="font-bold text-lg text-sidebar-foreground">
            ParkSmart
          </span>
        </div>
      </div>

      {/* User Info */}
      {user && (
        <div className="border-b border-sidebar-border p-3">
          <div className="flex items-center gap-3">
            <Avatar className="h-10 w-10">
              <AvatarImage src={user.avatar} alt={user.username} />
              <AvatarFallback className="bg-primary text-primary-foreground">
                {user.username.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-sidebar-foreground truncate">
                {user.username}
              </p>
              <div className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className={cn(
                    "text-xs",
                    user.role === "admin"
                      ? "bg-destructive/10 text-destructive border-destructive/20"
                      : "bg-primary/10 text-primary border-primary/20",
                  )}
                >
                  <Shield className="h-3 w-3 mr-1" />
                  {user.role === "admin" ? "Admin" : "User"}
                </Badge>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav
        className="flex flex-col gap-1 p-3 overflow-y-auto"
        style={{ maxHeight: "calc(100vh - 200px)" }}
      >
        {user?.role === "admin" && (
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-3 py-2">
            Quản trị
          </p>
        )}
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
                isActive
                  ? "gradient-primary text-primary-foreground shadow-md"
                  : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
              )}
            >
              <item.icon
                className={cn(
                  "h-5 w-5 shrink-0",
                  isActive && "text-primary-foreground",
                )}
              />
              <span>{item.label}</span>
            </NavLink>
          );
        })}

        {/* User section link for admin */}
        {user?.role === "admin" && (
          <>
            <div className="my-2 border-t border-sidebar-border" />
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-3 py-2">
              Tài khoản
            </p>
          </>
        )}
        {user?.role === "admin" && (
          <NavLink
            to="/settings"
            className={cn(
              "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
              location.pathname === "/settings"
                ? "gradient-primary text-primary-foreground shadow-md"
                : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
            )}
          >
            <Settings
              className={cn(
                "h-5 w-5 shrink-0",
                location.pathname === "/settings" && "text-primary-foreground",
              )}
            />
            <span>Cài đặt</span>
          </NavLink>
        )}
      </nav>

      {/* Bottom Section */}
      <div className="absolute bottom-0 left-0 right-0 border-t border-sidebar-border p-3">
        <div className="flex gap-2 flex-row">
          <Button
            variant="ghost"
            size="default"
            onClick={toggleTheme}
            className="text-sidebar-foreground hover:bg-sidebar-accent flex-1"
          >
            {theme === "dark" ? (
              <>
                <Sun className="h-4 w-4" />
                <span className="ml-2">Sáng</span>
              </>
            ) : (
              <>
                <Moon className="h-4 w-4" />
                <span className="ml-2">Tối</span>
              </>
            )}
          </Button>
          <Button
            variant="ghost"
            size="default"
            onClick={handleLogout}
            className="text-sidebar-foreground hover:bg-destructive/10 hover:text-destructive flex-1"
          >
            <LogOut className="h-4 w-4" />
            <span className="ml-2">Đăng xuất</span>
          </Button>
        </div>
      </div>
    </aside>
  );
}
