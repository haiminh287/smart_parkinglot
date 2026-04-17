import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Provider } from "react-redux";
import { store } from "@/store";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { ContactWidget } from "@/components/support/ContactWidget";
import { SnowfallEffect } from "@/components/effects/SnowfallEffect";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { DevLogPanel } from "@/components/DevLogPanel";
import { PageSkeleton } from "@/components/PageSkeleton";
import { lazy, Suspense } from "react";

// Eager — critical path (first paint)
import Index from "./pages/Index";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import AuthCallbackPage from "./pages/AuthCallbackPage";
import NotFound from "./pages/NotFound";

// Lazy — user pages
const BookingPage = lazy(() => import("./pages/BookingPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));
const CamerasPage = lazy(() => import("./pages/CamerasPage"));
const MapPage = lazy(() => import("./pages/MapPage"));
const SupportPage = lazy(() => import("./pages/SupportPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const PaymentPage = lazy(() => import("./pages/PaymentPage"));
const PanicButtonPage = lazy(() => import("./pages/PanicButtonPage"));
const BanknoteDetectionPage = lazy(
  () => import("./pages/BanknoteDetectionPage"),
);
const KioskPage = lazy(() => import("./pages/KioskPage"));

// Lazy — admin pages
const AdminDashboard = lazy(() => import("./pages/AdminDashboard"));
const AdminUsersPage = lazy(() => import("./pages/admin/AdminUsersPage"));
const AdminZonesPage = lazy(() => import("./pages/admin/AdminZonesPage"));
const AdminSlotsPage = lazy(() => import("./pages/admin/AdminSlotsPage"));
const AdminCamerasPage = lazy(() => import("./pages/admin/AdminCamerasPage"));
const AdminConfigPage = lazy(() => import("./pages/admin/AdminConfigPage"));
const AdminViolationsPage = lazy(
  () => import("./pages/admin/AdminViolationsPage"),
);
const AdminESP32Page = lazy(() => import("./pages/admin/AdminESP32Page"));
const AdminRevenuePage = lazy(() => import("./pages/admin/AdminRevenuePage"));
const AdminStatsPage = lazy(() => import("./pages/admin/AdminStatsPage"));

const App = () => (
  <Provider store={store}>
    <ThemeProvider>
      <AuthProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <SnowfallEffect />
          <DevLogPanel />
          <BrowserRouter>
            <ErrorBoundary>
              <Suspense fallback={<PageSkeleton />}>
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
                  <Route
                    path="/admin/stats"
                    element={
                      <ProtectedRoute requireAdmin>
                        <AdminStatsPage />
                      </ProtectedRoute>
                    }
                  />

                  <Route path="*" element={<NotFound />} />
                </Routes>
              </Suspense>
            </ErrorBoundary>
            <ContactWidget />
          </BrowserRouter>
        </TooltipProvider>
      </AuthProvider>
    </ThemeProvider>
  </Provider>
);

export default App;
