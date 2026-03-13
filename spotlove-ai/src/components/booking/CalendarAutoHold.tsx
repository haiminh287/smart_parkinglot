import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Calendar,
  Clock,
  Bell,
  Link2,
  CheckCircle,
  AlertCircle,
  Settings,
  MapPin,
  Car,
  ChevronRight,
  RefreshCw,
  AlertTriangle,
  Sparkles,
  TrendingDown,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Calendar provider icons
const GoogleCalendarIcon = () => (
  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none">
    <rect
      x="3"
      y="4"
      width="18"
      height="18"
      rx="2"
      stroke="currentColor"
      strokeWidth="2"
    />
    <path d="M3 9h18" stroke="currentColor" strokeWidth="2" />
    <path
      d="M9 4V2M15 4V2"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
    />
    <rect x="7" y="12" width="3" height="3" rx="0.5" fill="#4285F4" />
    <rect x="11" y="12" width="3" height="3" rx="0.5" fill="#EA4335" />
    <rect x="7" y="16" width="3" height="3" rx="0.5" fill="#FBBC04" />
    <rect x="11" y="16" width="3" height="3" rx="0.5" fill="#34A853" />
  </svg>
);

const AppleCalendarIcon = () => (
  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
    <path d="M19.5 3h-3V1.5h-1.5V3h-6V1.5H7.5V3h-3C3.675 3 3 3.675 3 4.5v15c0 .825.675 1.5 1.5 1.5h15c.825 0 1.5-.675 1.5-1.5v-15c0-.825-.675-1.5-1.5-1.5zM19.5 19.5h-15V7.5h15v12z" />
    <path d="M12 9.75c-1.657 0-3 1.343-3 3s1.343 3 3 3 3-1.343 3-3-1.343-3-3-3z" />
  </svg>
);

interface CalendarEvent {
  id: string;
  title: string;
  location: string;
  startTime: string;
  needsParking: boolean;
  parkingStatus: "pending" | "reserved" | "declined";
  minutesUntil?: number;
}

interface AINotification {
  id: string;
  type: "reminder" | "almost_full" | "pre_arrival";
  title: string;
  message: string;
  eventId?: string;
  timestamp: string;
  dismissed: boolean;
}

interface CalendarConnection {
  provider: "google" | "apple";
  name: string;
  email: string;
  connected: boolean;
  icon: React.ComponentType;
  color: string;
}

const calendarProviders: CalendarConnection[] = [
  {
    provider: "google",
    name: "Google Calendar",
    email: "user@gmail.com",
    connected: true,
    icon: GoogleCalendarIcon,
    color: "bg-blue-500",
  },
  {
    provider: "apple",
    name: "Apple Calendar",
    email: "",
    connected: false,
    icon: AppleCalendarIcon,
    color: "bg-gray-800",
  },
];

export function CalendarAutoHold() {
  const [autoHoldEnabled, setAutoHoldEnabled] = useState(true);
  const [reminderTime, setReminderTime] = useState(20); // minutes before
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [connections, setConnections] = useState(calendarProviders);
  const [notifications, setNotifications] = useState<AINotification[]>([]);

  // Simulate AI notifications
  useEffect(() => {
    if (!autoHoldEnabled) return;

    // Simulate "before meeting" reminder
    const timer1 = setTimeout(() => {
      const upcomingEvent = events.find(
        (e) => e.minutesUntil && e.minutesUntil <= 25 && !e.needsParking,
      );
      if (upcomingEvent) {
        setNotifications((prev) => [
          ...prev,
          {
            id: `reminder-${upcomingEvent.id}`,
            type: "reminder",
            title: "🔔 Bạn cần giữ chỗ gửi xe không?",
            message: `"${upcomingEvent.title}" tại ${upcomingEvent.location} sau ${upcomingEvent.minutesUntil} phút.`,
            eventId: upcomingEvent.id,
            timestamp: new Date().toISOString(),
            dismissed: false,
          },
        ]);
      }
    }, 2000);

    // Simulate "almost full" prediction
    const timer2 = setTimeout(() => {
      setNotifications((prev) => [
        ...prev,
        {
          id: "almost-full-1",
          type: "almost_full",
          title: "⚠️ Bãi Vincom Center sắp đầy",
          message:
            "AI dự đoán: Còn ~15 chỗ, sẽ hết trong 20 phút nữa. Nên giữ chỗ ngay!",
          timestamp: new Date().toISOString(),
          dismissed: false,
        },
      ]);
    }, 4000);

    // Simulate "pre-arrival" warning
    const timer3 = setTimeout(() => {
      const reservedEvent = events.find((e) => e.parkingStatus === "reserved");
      if (reservedEvent) {
        setNotifications((prev) => [
          ...prev,
          {
            id: `pre-arrival-${reservedEvent.id}`,
            type: "pre_arrival",
            title: "⏰ Còn 15 phút tới giờ hẹn",
            message: `Bãi đỗ tại ${reservedEvent.location} đang giữ chỗ cho bạn. Hãy di chuyển ngay!`,
            eventId: reservedEvent.id,
            timestamp: new Date().toISOString(),
            dismissed: false,
          },
        ]);
      }
    }, 6000);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
    };
  }, [autoHoldEnabled, events]);

  const handleToggleConnection = (provider: "google" | "apple") => {
    setConnections((prev) =>
      prev.map((c) =>
        c.provider === provider
          ? {
              ...c,
              connected: !c.connected,
              email: c.connected ? "" : "user@example.com",
            }
          : c,
      ),
    );
  };

  const handleToggleParking = (eventId: string) => {
    setEvents((prev) =>
      prev.map((e) =>
        e.id === eventId
          ? {
              ...e,
              needsParking: !e.needsParking,
              parkingStatus: "pending" as const,
            }
          : e,
      ),
    );
  };

  const handleQuickReserve = (eventId: string) => {
    setEvents((prev) =>
      prev.map((e) =>
        e.id === eventId
          ? { ...e, needsParking: true, parkingStatus: "reserved" as const }
          : e,
      ),
    );
    // Dismiss related notification
    setNotifications((prev) =>
      prev.map((n) => (n.eventId === eventId ? { ...n, dismissed: true } : n)),
    );
  };

  const handleDismissNotification = (notifId: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === notifId ? { ...n, dismissed: true } : n)),
    );
  };

  const connectedCount = connections.filter((c) => c.connected).length;
  const activeNotifications = notifications.filter((n) => !n.dismissed);

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-xl sm:rounded-2xl bg-gradient-to-r from-orange-500 to-pink-500 p-4 sm:p-6 text-white">
        <div className="relative z-10">
          <Badge className="bg-white/20 text-white border-0 mb-2 sm:mb-3 text-[10px] sm:text-xs">
            <Bell className="h-2.5 w-2.5 sm:h-3 sm:w-3 mr-1" />
            Calendar-aware
          </Badge>
          <h2 className="text-lg sm:text-2xl font-bold mb-1 sm:mb-2">
            Auto-Hold theo lịch 📅
          </h2>
          <p className="text-sm sm:text-base text-white/80 max-w-md">
            Kết nối lịch cá nhân, tự động nhắc giữ chỗ trước mỗi cuộc họp.
          </p>
        </div>
        <Calendar className="absolute right-4 sm:right-6 bottom-4 sm:bottom-6 h-16 w-16 sm:h-24 sm:w-24 text-white/10" />
      </div>

      {/* AI Notifications */}
      {activeNotifications.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <h3 className="font-semibold text-foreground text-sm sm:text-base">
              Thông báo AI
            </h3>
            <Badge variant="outline" className="text-xs">
              {activeNotifications.length}
            </Badge>
          </div>

          {activeNotifications.map((notif) => (
            <div
              key={notif.id}
              className={cn(
                "animate-fade-in rounded-xl border-2 p-3 sm:p-4",
                notif.type === "reminder" && "border-primary/50 bg-primary/5",
                notif.type === "almost_full" &&
                  "border-yellow-500/50 bg-yellow-500/10",
                notif.type === "pre_arrival" &&
                  "border-blue-500/50 bg-blue-500/10",
              )}
            >
              <div className="flex items-start gap-3">
                <div
                  className={cn(
                    "flex h-9 w-9 sm:h-10 sm:w-10 shrink-0 items-center justify-center rounded-lg sm:rounded-xl",
                    notif.type === "reminder" && "bg-primary/20",
                    notif.type === "almost_full" && "bg-yellow-500/20",
                    notif.type === "pre_arrival" && "bg-blue-500/20",
                  )}
                >
                  {notif.type === "reminder" && (
                    <Bell className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
                  )}
                  {notif.type === "almost_full" && (
                    <TrendingDown className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-600" />
                  )}
                  {notif.type === "pre_arrival" && (
                    <Clock className="h-4 w-4 sm:h-5 sm:w-5 text-blue-600" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-foreground text-sm sm:text-base">
                    {notif.title}
                  </p>
                  <p className="text-xs sm:text-sm text-muted-foreground mt-1">
                    {notif.message}
                  </p>
                  <div className="flex flex-wrap gap-2 mt-2 sm:mt-3">
                    {notif.type === "reminder" && notif.eventId && (
                      <>
                        <Button
                          size="sm"
                          className="gradient-primary text-xs h-8"
                          onClick={() => handleQuickReserve(notif.eventId!)}
                        >
                          ✓ YES - Giữ chỗ
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-xs h-8"
                          onClick={() => handleDismissNotification(notif.id)}
                        >
                          Không, cảm ơn
                        </Button>
                      </>
                    )}
                    {notif.type === "almost_full" && (
                      <>
                        <Button
                          size="sm"
                          className="gradient-primary text-xs h-8"
                        >
                          Giữ chỗ ngay
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-xs h-8"
                          onClick={() => handleDismissNotification(notif.id)}
                        >
                          Bỏ qua
                        </Button>
                      </>
                    )}
                    {notif.type === "pre_arrival" && (
                      <>
                        <Button
                          size="sm"
                          className="bg-blue-500 hover:bg-blue-600 text-xs h-8"
                        >
                          Xem chỉ đường
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-xs h-8"
                          onClick={() => handleDismissNotification(notif.id)}
                        >
                          OK
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Calendar Connections */}
      <div className="rounded-xl sm:rounded-2xl border border-border bg-card p-4 sm:p-5">
        <div className="flex items-center justify-between mb-3 sm:mb-4">
          <div>
            <h3 className="font-semibold text-foreground text-sm sm:text-base">
              Kết nối lịch
            </h3>
            <p className="text-xs sm:text-sm text-muted-foreground">
              {connectedCount > 0
                ? `Đã kết nối ${connectedCount} lịch`
                : "Chưa kết nối lịch nào"}
            </p>
          </div>
          <Link2 className="h-4 w-4 sm:h-5 sm:w-5 text-muted-foreground" />
        </div>

        <div className="space-y-2 sm:space-y-3">
          {connections.map((connection) => (
            <div
              key={connection.provider}
              className={cn(
                "flex items-center justify-between rounded-lg sm:rounded-xl border p-3 sm:p-4 transition-all",
                connection.connected
                  ? "border-primary/20 bg-primary/5"
                  : "border-border",
              )}
            >
              <div className="flex items-center gap-2 sm:gap-3">
                <div
                  className={cn(
                    "flex h-8 w-8 sm:h-10 sm:w-10 items-center justify-center rounded-lg text-white",
                    connection.color,
                  )}
                >
                  <connection.icon />
                </div>
                <div className="min-w-0">
                  <p className="font-medium text-foreground text-sm sm:text-base">
                    {connection.name}
                  </p>
                  {connection.connected ? (
                    <p className="text-xs sm:text-sm text-green-600 truncate">
                      {connection.email}
                    </p>
                  ) : (
                    <p className="text-xs sm:text-sm text-muted-foreground">
                      Chưa kết nối
                    </p>
                  )}
                </div>
              </div>
              <Button
                variant={connection.connected ? "outline" : "default"}
                size="sm"
                onClick={() => handleToggleConnection(connection.provider)}
                className={cn(
                  "text-xs h-8",
                  !connection.connected && "gradient-primary",
                )}
              >
                {connection.connected ? "Ngắt" : "Kết nối"}
              </Button>
            </div>
          ))}
        </div>
      </div>

      {/* Auto-Hold Settings */}
      <div className="rounded-xl sm:rounded-2xl border border-border bg-card p-4 sm:p-5">
        <div className="flex items-center justify-between mb-3 sm:mb-4">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="flex h-8 w-8 sm:h-10 sm:w-10 items-center justify-center rounded-lg bg-primary/10">
              <Settings className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground text-sm sm:text-base">
                Tự động nhắc giữ chỗ
              </h3>
              <p className="text-xs sm:text-sm text-muted-foreground">
                Nhắc bạn trước mỗi cuộc họp
              </p>
            </div>
          </div>
          <Switch
            checked={autoHoldEnabled}
            onCheckedChange={setAutoHoldEnabled}
          />
        </div>

        {autoHoldEnabled && (
          <div className="mt-3 sm:mt-4 pt-3 sm:pt-4 border-t border-border space-y-3 sm:space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-muted-foreground" />
                <span className="text-xs sm:text-sm text-foreground">
                  Nhắc trước cuộc họp
                </span>
              </div>
              <select
                value={reminderTime}
                onChange={(e) => setReminderTime(Number(e.target.value))}
                className="rounded-lg border border-border bg-background px-2 sm:px-3 py-1 sm:py-1.5 text-xs sm:text-sm focus:border-primary focus:outline-none"
              >
                <option value={15}>15 phút</option>
                <option value={20}>20 phút</option>
                <option value={30}>30 phút</option>
                <option value={45}>45 phút</option>
                <option value={60}>1 giờ</option>
              </select>
            </div>

            <div className="rounded-lg sm:rounded-xl bg-muted/50 p-3">
              <p className="text-xs sm:text-sm text-muted-foreground">
                💡 Khi có cuộc họp, bạn sẽ nhận thông báo: <br />
                <span className="font-medium text-foreground">
                  "Bạn cần giữ chỗ gửi xe không?" → 1 chạm YES
                </span>
              </p>
            </div>

            {/* AI Features */}
            <div className="space-y-2">
              <p className="text-xs sm:text-sm font-medium text-foreground flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                Tính năng AI
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div className="flex items-center gap-2 rounded-lg bg-yellow-500/10 border border-yellow-500/20 p-2 sm:p-3">
                  <AlertTriangle className="h-4 w-4 text-yellow-600 shrink-0" />
                  <span className="text-xs text-foreground">
                    Dự đoán "sắp hết chỗ"
                  </span>
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-blue-500/10 border border-blue-500/20 p-2 sm:p-3">
                  <Clock className="h-4 w-4 text-blue-600 shrink-0" />
                  <span className="text-xs text-foreground">
                    Nhắc 15 phút trước khi tới
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Upcoming Events */}
      <div className="rounded-xl sm:rounded-2xl border border-border bg-card p-4 sm:p-5">
        <div className="flex items-center justify-between mb-3 sm:mb-4">
          <div>
            <h3 className="font-semibold text-foreground text-sm sm:text-base">
              Sự kiện sắp tới
            </h3>
            <p className="text-xs sm:text-sm text-muted-foreground">
              Từ lịch của bạn
            </p>
          </div>
          <Button variant="ghost" size="sm" className="gap-1.5 h-8 text-xs">
            <RefreshCw className="h-3.5 w-3.5" />
            Đồng bộ
          </Button>
        </div>

        <div className="space-y-2 sm:space-y-3">
          {events.map((event) => (
            <div
              key={event.id}
              className="rounded-lg sm:rounded-xl border border-border bg-background p-3 sm:p-4"
            >
              <div className="flex items-start justify-between mb-2 sm:mb-3 gap-2">
                <div className="min-w-0">
                  <h4 className="font-medium text-foreground text-sm sm:text-base truncate">
                    {event.title}
                  </h4>
                  <div className="flex items-center gap-2 mt-1 text-xs sm:text-sm text-muted-foreground">
                    <MapPin className="h-3 w-3 shrink-0" />
                    <span className="truncate">{event.location}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-xs sm:text-sm text-muted-foreground">
                    <Clock className="h-3 w-3 shrink-0" />
                    <span>
                      {new Date(event.startTime).toLocaleTimeString("vi-VN", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                      {event.minutesUntil && (
                        <span className="text-primary ml-1">
                          (còn {event.minutesUntil} phút)
                        </span>
                      )}
                    </span>
                  </div>
                </div>

                {event.parkingStatus === "reserved" ? (
                  <Badge className="bg-green-500/10 text-green-600 border-green-500/20 text-[10px] sm:text-xs shrink-0">
                    <CheckCircle className="h-2.5 w-2.5 sm:h-3 sm:w-3 mr-1" />
                    Đã giữ
                  </Badge>
                ) : event.needsParking ? (
                  <Badge className="bg-yellow-500/10 text-yellow-600 border-yellow-500/20 text-[10px] sm:text-xs shrink-0">
                    <AlertCircle className="h-2.5 w-2.5 sm:h-3 sm:w-3 mr-1" />
                    Chờ
                  </Badge>
                ) : null}
              </div>

              <div className="flex items-center justify-between pt-2 sm:pt-3 border-t border-border">
                <div className="flex items-center gap-2">
                  <Switch
                    checked={event.needsParking}
                    onCheckedChange={() => handleToggleParking(event.id)}
                    disabled={event.parkingStatus === "reserved"}
                  />
                  <span className="text-xs sm:text-sm text-muted-foreground">
                    {event.needsParking ? "Cần chỗ" : "Không cần"}
                  </span>
                </div>

                {event.needsParking && event.parkingStatus !== "reserved" && (
                  <Button
                    size="sm"
                    className="gap-1 sm:gap-1.5 text-xs h-8"
                    onClick={() => handleQuickReserve(event.id)}
                  >
                    <Car className="h-3.5 w-3.5" />
                    <span className="hidden sm:inline">Giữ ngay</span>
                    <ChevronRight className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>

        {events.length === 0 && (
          <div className="text-center py-6 sm:py-8">
            <Calendar className="h-10 w-10 sm:h-12 sm:w-12 mx-auto text-muted-foreground/50" />
            <p className="mt-2 text-sm text-muted-foreground">
              Không có sự kiện nào sắp tới
            </p>
          </div>
        )}
      </div>

      {/* Quick Actions Preview */}
      <div className="rounded-xl sm:rounded-2xl border border-dashed border-primary/30 bg-primary/5 p-4 sm:p-5">
        <div className="flex items-start gap-3 sm:gap-4">
          <div className="flex h-10 w-10 sm:h-12 sm:w-12 shrink-0 items-center justify-center rounded-lg sm:rounded-xl bg-primary/10">
            <Bell className="h-5 w-5 sm:h-6 sm:w-6 text-primary" />
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-foreground text-sm sm:text-base">
              Thông báo mẫu
            </p>
            <p className="text-xs sm:text-sm text-muted-foreground mt-1">
              "Họp team Marketing" tại Vincom Center sau 20 phút. Bạn cần giữ
              chỗ gửi xe không?
            </p>
            <div className="flex flex-wrap gap-2 mt-2 sm:mt-3">
              <Button size="sm" className="gradient-primary text-xs h-8">
                ✓ YES - Giữ chỗ
              </Button>
              <Button size="sm" variant="outline" className="text-xs h-8">
                Không, cảm ơn
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
