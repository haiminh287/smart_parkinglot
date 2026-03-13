import { ReactNode, useState, useEffect } from 'react';
import { AppSidebar } from './AppSidebar';
import { cn } from '@/lib/utils';
import { Menu, Wifi, WifiOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { useWebSocketConnection } from '@/hooks/useWebSocketConnection';
import { useAppSelector } from '@/store/hooks';

interface MainLayoutProps {
  children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
  // WebSocket connection - auto-connects when user is authenticated
  const { 
    isConnected, 
    isConnecting, 
    isReconnecting,
    status: wsStatus,
    reconnect 
  } = useWebSocketConnection();

  const { isAuthenticated } = useAppSelector((state) => state.auth);

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop Sidebar - Hidden on mobile */}
      <div className="hidden md:block">
        <AppSidebar />
      </div>
      
      {/* Mobile Header */}
      <div className="fixed left-0 right-0 top-0 z-50 flex h-14 items-center justify-between border-b border-border bg-background/95 backdrop-blur px-4 md:hidden">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg gradient-primary">
            <span className="text-sm font-bold text-primary-foreground">P</span>
          </div>
          <span className="font-semibold text-foreground">ParkSmart</span>
        </div>

        <div className="flex items-center gap-2">
          {/* WebSocket Status Indicator */}
          {isAuthenticated && (
            <button
              onClick={isConnected ? undefined : reconnect}
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-lg transition-colors",
                isConnected 
                  ? "text-success" 
                  : isConnecting || isReconnecting
                    ? "text-warning animate-pulse"
                    : "text-destructive hover:bg-destructive/10"
              )}
              title={
                isConnected 
                  ? "Đã kết nối realtime" 
                  : isConnecting 
                    ? "Đang kết nối..." 
                    : isReconnecting
                      ? "Đang kết nối lại..."
                      : "Mất kết nối - Nhấn để thử lại"
              }
            >
              {isConnected ? (
                <Wifi className="h-4 w-4" />
              ) : (
                <WifiOff className="h-4 w-4" />
              )}
            </button>
          )}
          
          <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="h-9 w-9">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-[280px] p-0">
              <AppSidebar />
            </SheetContent>
          </Sheet>
        </div>
      </div>

      {/* Main content */}
      <main className={cn(
        "min-h-screen transition-all duration-300",
        "pt-14 px-4 pb-6 md:pt-6 md:px-6 md:ml-64"
      )}>
        {children}
      </main>
    </div>
  );
}
