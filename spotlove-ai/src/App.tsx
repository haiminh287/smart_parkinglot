import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Provider } from "react-redux";
import { store } from "@/store";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { ContactWidget } from "@/components/support/ContactWidget";
import { SnowfallEffect } from "@/components/effects/SnowfallEffect";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import Index from "./pages/Index";
import BookingPage from "./pages/BookingPage";
import HistoryPage from "./pages/HistoryPage";
import CamerasPage from "./pages/CamerasPage";
import MapPage from "./pages/MapPage";
import SupportPage from "./pages/SupportPage";
import SettingsPage from "./pages/SettingsPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import AuthCallbackPage from "./pages/AuthCallbackPage";
import PaymentPage from "./pages/PaymentPage";
import NotFound from "./pages/NotFound";
import PanicButtonPage from "./pages/PanicButtonPage";
import AdminUsersPage from "./pages/admin/AdminUsersPage";
import AdminZonesPage from "./pages/admin/AdminZonesPage";
import AdminSlotsPage from "./pages/admin/AdminSlotsPage";
import AdminCamerasPage from "./pages/admin/AdminCamerasPage";
import AdminConfigPage from "./pages/admin/AdminConfigPage";
import AdminDashboard from "./pages/AdminDashboard";
import BanknoteDetectionPage from "./pages/BanknoteDetectionPage";
import KioskPage from "./pages/KioskPage";
import CheckInOutPage from "./pages/CheckInOutPage";
import AdminViolationsPage from "./pages/admin/AdminViolationsPage";
import AdminESP32Page from "./pages/admin/AdminESP32Page";
import AdminRevenuePage from "./pages/admin/AdminRevenuePage";

const queryClient = new QueryClient();

const App = () => (
  <Provider store={store}>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <TooltipProvider>
            <Toaster />
            <Sonner />
            {/* Snowfall effect for dark mode */}
            <SnowfallEffect />
            <BrowserRouter>
              <ErrorBoundary>
                <Routes>
                  {/* Public Routes */}
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/register" element={<RegisterPage />} />
                  <Route path="/auth/callback" element={<AuthCallbackPage />} />

                  {/* Protected Routes */}
                  <Route
                    path="/"
                    element={
                      <ProtectedRoute>
                        <Index />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/booking"
                    element={
                      <ProtectedRoute>
                        <BookingPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/history"
                    element={
                      <ProtectedRoute>
                        <HistoryPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/cameras"
                    element={
                      <ProtectedRoute>
                        <CamerasPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/map"
                    element={
                      <ProtectedRoute>
                        <MapPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/support"
                    element={
                      <ProtectedRoute>
                        <SupportPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/settings"
                    element={
                      <ProtectedRoute>
                        <SettingsPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/payment"
                    element={
                      <ProtectedRoute>
                        <PaymentPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/panic"
                    element={
                      <ProtectedRoute>
                        <PanicButtonPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/banknote-detection"
                    element={
                      <ProtectedRoute>
                        <BanknoteDetectionPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/check-in-out"
                    element={
                      <ProtectedRoute>
                        <CheckInOutPage />
                      </ProtectedRoute>
                    }
                  />

                  {/* Public Kiosk Route (no auth required) */}
                  <Route path="/kiosk" element={<KioskPage />} />

                  {/* Admin Routes */}
                  <Route
                    path="/admin/dashboard"
                    element={
                      <ProtectedRoute requireAdmin>
                        <AdminDashboard />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/admin/users"
                    element={
                      <ProtectedRoute requireAdmin>
                        <AdminUsersPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/admin/zones"
                    element={
                      <ProtectedRoute requireAdmin>
                        <AdminZonesPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/admin/slots"
                    element={
                      <ProtectedRoute requireAdmin>
                        <AdminSlotsPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/admin/cameras"
                    element={
                      <ProtectedRoute requireAdmin>
                        <AdminCamerasPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/admin/config"
                    element={
                      <ProtectedRoute requireAdmin>
                        <AdminConfigPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/admin/violations"
                    element={
                      <ProtectedRoute requireAdmin>
                        <AdminViolationsPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/admin/esp32"
                    element={
                      <ProtectedRoute requireAdmin>
                        <AdminESP32Page />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/admin/revenue"
                    element={
                      <ProtectedRoute requireAdmin>
                        <AdminRevenuePage />
                      </ProtectedRoute>
                    }
                  />

                  <Route path="*" element={<NotFound />} />
                </Routes>
              </ErrorBoundary>
              {/* Global Contact Widget */}
              <ContactWidget />
            </BrowserRouter>
          </TooltipProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </Provider>
);

export default App;
