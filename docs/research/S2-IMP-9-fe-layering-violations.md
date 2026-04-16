# Research Report: FE Layering Compliance Audit

**Task:** S2-IMP-9 | **Date:** 2026-04-15 | **Type:** Codebase

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. **32 unique violation imports** across **19 files** (pages, components, Redux slices) — importing directly from `services/api/` instead of `services/business/`
> 2. **2 business services hoàn toàn thiếu**: `ai.service.ts` và `chatbot.service.ts` — đây là 2 API modules lớn nhất chưa có wrapper
> 3. **`services/index.ts` barrel re-exports ALL api objects** (`aiApi`, `bookingApi`, etc.) — nó là "violation enabler" vì cho phép `import { adminApi } from "@/services"` giả tạo compliance
> 4. **4 Redux slices đều chứa asyncThunks gọi thẳng API** — đây là pattern phổ biến, cần quyết định: cho phép slices gọi API (vì chúng IS business logic tier) hay bắt qua business service?

---

## 2. File Inventory

### 2.1 API Layer (`services/api/`)

| File | Methods | Has Business Wrapper? |
|---|---|---|
| `auth.api.ts` | login, register, logout, getCurrentUser, getGoogleAuthUrl, getFacebookAuthUrl, forgotPassword, resetPassword | ✅ `auth.service.ts` |
| `booking.api.ts` | getBookings, createBooking, cancelBooking, checkIn, checkOut, getCurrentParking, getUpcomingBookings, getBookingStats, initiatePayment, verifyPayment, getQRCode, getPackagePricing, getRevenueSummary, getDailyRevenue, getHourlyRevenue, extendBooking | ✅ `booking.service.ts` |
| `parking.api.ts` | getLots, getZones, getSlots, checkAvailability, getFloors | ✅ `parking.service.ts` |
| `vehicle.api.ts` | (CRUD vehicles) | ✅ `vehicle.service.ts` |
| `notification.api.ts` | (CRUD notifications) | ✅ `notification.service.ts` |
| `incident.api.ts` | reportIncident, getMyIncidents, getIncident | ✅ `incident.service.ts` |
| `admin.api.ts` | getDashboardStats, getRevenueReport, getRecentActivities, getUsers, getUser, updateUser, deactivateUser, activateUser, resetNoShowCount, createLot, updateLot, createZone, updateZone, updateSlotStatus, getIncidents, updateIncidentStatus, getConfig, updateConfig, getCameras, createCamera, updateCamera, deleteCamera | ✅ `admin.service.ts` |
| **`ai.api.ts`** | detectBanknote, scanPlate, checkIn, checkOut, esp32CheckIn, esp32CheckOut, esp32VerifySlot, esp32CashPayment, getESP32Devices, getESP32DeviceLogs, getDetectionHistory | ❌ **MISSING** |
| **`chatbot.api.ts`** | sendMessage, getQuickActions, getChatMessages, getChatHistory, getActiveConversation, submitFeedback | ❌ **MISSING** |

### 2.2 Business Layer (`services/business/`)

| File | Wraps |
|---|---|
| `auth.service.ts` | auth.api.ts |
| `booking.service.ts` | booking.api.ts |
| `parking.service.ts` | parking.api.ts |
| `vehicle.service.ts` | vehicle.api.ts |
| `notification.service.ts` | notification.api.ts |
| `incident.service.ts` | incident.api.ts |
| `admin.service.ts` | admin.api.ts |
| `index.ts` | barrel export all above |

---

## 3. Violation List

### 3.1 Pages — Direct `@/services/api/` Imports (16 files, 23 imports)

| # | File | Line | Import | API Used | Needed Business Method |
|---|---|---|---|---|---|
| 1 | `pages/CheckInOutPage.tsx` | 43 | `import { aiApi } from "@/services/api/ai.api"` | `aiApi.checkIn`, `aiApi.checkOut` | `aiService.checkIn()`, `aiService.checkOut()` |
| 2 | `pages/CheckInOutPage.tsx` | 44 | `import { bookingApi } from "@/services/api/booking.api"` | (TBD — check usage) | `bookingService.*` exists |
| 3 | `pages/CheckInOutPage.tsx` | 46 | `import type { CheckInResponse, CheckOutResponse } from "@/services/api/ai.api"` | Type import | Re-export from `aiService` |
| 4 | `pages/BanknoteDetectionPage.tsx` | 29 | `import { aiApi, DENOMINATION_LABELS, DENOMINATION_COLORS } from "@/services/api/ai.api"` | `aiApi.detectBanknote` | `aiService.detectBanknote()` |
| 5 | `pages/BanknoteDetectionPage.tsx` | 33 | `import type { BanknoteRecognitionResponse, DetectionMode } from "@/services/api/ai.api"` | Type import | Re-export from `aiService` |
| 6 | `pages/DetectionHistoryPage.tsx` | 26 | `import { aiApi, type DetectionRecord } from "@/services/api/ai.api"` | `aiApi.getDetectionHistory` | `aiService.getDetectionHistory()` |
| 7 | `pages/KioskPage.tsx` | 31 | `import { aiApi } from "@/services/api/ai.api"` | `aiApi.esp32*`, `aiApi.esp32CashPayment` | `aiService.esp32CheckIn()`, etc. |
| 8 | `pages/KioskPage.tsx` | 36 | `import type { ESP32Response, GateEvent, BarrierAction } from "@/services/api/ai.api"` | Type import | Re-export from `aiService` |
| 9 | `pages/MapPage.tsx` | 20 | `import { parkingApi } from "@/services/api/parking.api"` | `parkingApi.getFloors` | `parkingService.getFloors()` (missing in service) |
| 10 | `pages/BookingPage.tsx` | 45 | `import type { Floor } from "@/services/api/parking.api"` | Type import | Re-export from `parkingService` |
| 11 | `pages/SupportPage.tsx` | 28 | `import { chatbotApi, type ChatResponse } from "@/services/api/chatbot.api"` | `chatbotApi.sendMessage`, `chatbotApi.getChatHistory`, etc. | `chatbotService.*` (MISSING) |
| 12 | `pages/PanicButtonPage.tsx` | 37 | `import type { Incident, IncidentType } from "@/services/api/incident.api"` | Type import | Re-export from `incidentService` |
| 13 | `pages/admin/AdminZonesPage.tsx` | 25 | `import { parkingApi, type Floor } from "@/services/api/parking.api"` | `parkingApi.getFloors` | `parkingService.getFloors()` / `adminService` |
| 14 | `pages/admin/AdminZonesPage.tsx` | 26 | `import { adminApi } from "@/services/api/admin.api"` | `adminApi.createZone`, etc. | `adminService.createZone()` exists |
| 15 | `pages/admin/AdminViolationsPage.tsx` | 37 | `import { incidentApi } from "@/services/api/incident.api"` | `incidentApi.getMyIncidents` (admin) | `adminService.getIncidents()` exists |
| 16 | `pages/admin/AdminUsersPage.tsx` | 42 | `import { adminApi, type User, type CreateUserData } from "@/services/api/admin.api"` | `adminApi.getUsers`, `adminApi.createUser` | `adminService.getUsers()` exists |
| 17 | `pages/admin/AdminSlotsPage.tsx` | 24 | `import { parkingApi } from "@/services/api/parking.api"` | `parkingApi.getSlots` | `parkingService.getSlotsForZone()` exists |
| 18 | `pages/admin/AdminSlotsPage.tsx` | 25 | `import { adminApi } from "@/services/api/admin.api"` | `adminApi.updateSlotStatus` | `adminService.updateSlotStatus()` exists |
| 19 | `pages/admin/AdminRevenuePage.tsx` | 37 | `import { bookingApi } from "@/services/api/booking.api"` | `bookingApi.getRevenueSummary`, `getDailyRevenue`, `getHourlyRevenue` | Need wrappers in `adminService` or `bookingService` |
| 20 | `pages/admin/AdminRevenuePage.tsx` | 42 | `import type { RevenueSummary, DailyRevenueItem, HourlyRevenueItem } from "@/services/api/booking.api"` | Type import | Re-export from business layer |
| 21 | `pages/admin/AdminESP32Page.tsx` | 34 | `import { aiApi, type ESP32DeviceInfo, type ESP32DeviceLog } from "@/services/api/ai.api"` | `aiApi.getESP32Devices`, `aiApi.getESP32DeviceLogs` | `aiService.getDevices()`, `aiService.getDeviceLogs()` |
| 22 | `pages/admin/AdminCamerasPage.tsx` | 25 | `import { adminApi } from "@/services/api/admin.api"` | `adminApi.getCameras`, `adminApi.createCamera`, etc. | `adminService.getCameras()` etc. — need to check if exists |
| 23 | `pages/admin/AdminCamerasPage.tsx` | 26 | `import { parkingApi } from "@/services/api/parking.api"` | `parkingApi.getZones` | `parkingService.getZonesForLot()` exists |

### 3.2 Pages — Indirect API via Barrel `@/services` (7 files, 7 imports)

| # | File | Line | Import | API Used |
|---|---|---|---|---|
| 24 | `pages/admin/AdminStatsPage.tsx` | 35 | `import { adminApi } from "@/services"` | `adminApi.*` |
| 25 | `pages/admin/AdminConfigPage.tsx` | 21 | `import { adminApi } from "@/services"` | `adminApi.*` |
| 26 | `pages/SettingsPage.tsx` | 23 | `import { vehicleApi, notificationApi, authApi } from "@/services"` | multiple API objects |
| 27 | `pages/PaymentPage.tsx` | 23 | `import { bookingApi } from "@/services"` | `bookingApi.*` |
| 28 | `pages/PanicButtonPage.tsx` | 32 | `import { incidentApi, bookingApi } from "@/services"` | `incidentApi.*`, `bookingApi.*` |
| 29 | `pages/AdminDashboard.tsx` | 22 | `import { adminApi } from "@/services"` | `adminApi.*` |
| 30 | `pages/CamerasPage.tsx` | 36 | `import { adminApi, bookingApi, parkingApi } from "@/services"` | 3 API objects |

### 3.3 Components — Direct API Imports (4 files, 4 imports)

| # | File | Line | Import | API Used | Needed Fix |
|---|---|---|---|---|---|
| 31 | `components/booking/AutoGuaranteeBooking.tsx` | 4 | `import { parkingApi } from '@/services/api/parking.api'` | `parkingApi.getLots` / `checkAvailability` | → `parkingService.searchNearby()` |
| 32 | `components/booking/ParkingLotSelector.tsx` | 7 | `import { parkingApi } from "@/services/api/parking.api"` | `parkingApi.getLots` | → `parkingService.searchNearby()` |
| 33 | `components/booking/PriceSummary.tsx` | 18 | `import { bookingApi, type PackagePricingResponse } from "@/services/api/booking.api"` | `bookingApi.getPackagePricing` | → `bookingService.getPackagePricing()` (MISSING in service) |
| 34 | `components/settings/AddVehicleDialog.tsx` | 13 | `import type { CreateVehicleRequest } from "@/services/api/vehicle.api"` | Type import | Re-export from `vehicleService` |

### 3.4 Components — Indirect API via Barrel `@/services` (3 files)

| # | File | Line | Import | API Used |
|---|---|---|---|---|
| 35 | `components/dashboard/SlotOverview.tsx` | 4 | `import { parkingApi } from "@/services"` | `parkingApi.*` |
| 36 | `components/dashboard/RecentBookings.tsx` | 14 | `import { bookingApi } from "@/services"` | `bookingApi.*` |
| 37 | `components/settings/AddVehicleDialog.tsx` | 12 | `import { vehicleApi } from "@/services"` | `vehicleApi.*` |

### 3.5 Redux Slices — Direct API Imports (4 files, 5 imports)

| # | File | Line | Import | Usage |
|---|---|---|---|---|
| 38 | `store/slices/authSlice.ts` | 9 | `import { authApi } from "@/services/api/auth.api"` | asyncThunks: login, register, logout, initAuth, fetchCurrentUser |
| 39 | `store/slices/authSlice.ts` | 212 | `await import("@/services/api/axios.client")` | Dynamic import in updateProfile thunk |
| 40 | `store/slices/bookingSlice.ts` | 7 | `import { bookingApi } from "@/services/api/booking.api"` | asyncThunks: fetchBookings, fetchCurrentParking |
| 41 | `store/slices/parkingSlice.ts` | 7 | `import { parkingApi } from "@/services/api/parking.api"` | asyncThunks: fetchLots, fetchZones, fetchSlots |
| 42 | `store/slices/notificationSlice.ts` | 7 | `import { notificationApi } from "@/services/api/notification.api"` | asyncThunks: fetchNotifications, markRead, markAllRead |

---

## 4. Missing Business Service Methods

### 4.1 `ai.service.ts` — Hoàn toàn CHƯA TỒN TẠI

Cần wrap toàn bộ `ai.api.ts` methods:

| Method cần tạo | Wraps | Consumers |
|---|---|---|
| `detectBanknote(image, mode)` | `aiApi.detectBanknote` | BanknoteDetectionPage |
| `scanPlate(image)` | `aiApi.scanPlate` | (potential) |
| `checkIn(image, qrData)` | `aiApi.checkIn` | CheckInOutPage |
| `checkOut(image, qrData)` | `aiApi.checkOut` | CheckInOutPage |
| `esp32CheckIn(data)` | `aiApi.esp32CheckIn` | KioskPage |
| `esp32CheckOut(data)` | `aiApi.esp32CheckOut` | KioskPage |
| `esp32VerifySlot(data)` | `aiApi.esp32VerifySlot` | KioskPage |
| `esp32CashPayment(data)` | `aiApi.esp32CashPayment` | KioskPage |
| `getDevices()` | `aiApi.getESP32Devices` | AdminESP32Page |
| `getDeviceLogs(deviceId)` | `aiApi.getESP32DeviceLogs` | AdminESP32Page |
| `getDetectionHistory(params)` | `aiApi.getDetectionHistory` | DetectionHistoryPage |

Types to re-export: `BanknoteRecognitionResponse`, `BanknoteQualityInfo`, `BanknoteDetectionInfo`, `DetectionMode`, `PlateOCRResponse`, `CheckInResponse`, `CheckOutResponse`, `ESP32Response`, `GateEvent`, `BarrierAction`, `ESP32DeviceInfo`, `ESP32DeviceLog`, `DetectionRecord`, `DENOMINATION_LABELS`, `DENOMINATION_COLORS`

### 4.2 `chatbot.service.ts` — Hoàn toàn CHƯA TỒN TẠI

Cần wrap toàn bộ `chatbot.api.ts` methods:

| Method cần tạo | Wraps | Consumers |
|---|---|---|
| `sendMessage(message, conversationId?)` | `chatbotApi.sendMessage` | SupportPage |
| `getQuickActions()` | `chatbotApi.getQuickActions` | SupportPage |
| `getChatMessages(conversationId)` | `chatbotApi.getChatMessages` | SupportPage |
| `getChatHistory()` | `chatbotApi.getChatHistory` | SupportPage |
| `getActiveConversation()` | `chatbotApi.getActiveConversation` | SupportPage |
| `submitFeedback(data)` | `chatbotApi.submitFeedback` | SupportPage |

Types to re-export: `ChatMessage`, `ChatResponse`, `QuickAction`, `Conversation`, `ActiveConversationResponse`, `FeedbackRequest`

### 4.3 Missing Methods in Existing Business Services

| Business Service | Missing Method | API Method | Consumer |
|---|---|---|---|
| `parkingService` | `getFloors(lotId)` | `parkingApi.getFloors` | MapPage, AdminZonesPage, BookingPage (type) |
| `bookingService` | `getPackagePricing()` | `bookingApi.getPackagePricing` | PriceSummary component |
| `bookingService` | `getRevenueSummary()` | `bookingApi.getRevenueSummary` | AdminRevenuePage |
| `bookingService` | `getDailyRevenue(days)` | `bookingApi.getDailyRevenue` | AdminRevenuePage |
| `bookingService` | `getHourlyRevenue()` | `bookingApi.getHourlyRevenue` | AdminRevenuePage |
| `adminService` | `getCameras()` | `adminApi.getCameras` | Need to verify in admin.service.ts |
| `adminService` | `createUser(data)` | `adminApi.createUser` | AdminUsersPage |

---

## 5. `services/index.ts` Barrel — Violation Enabler

**Problem:** `services/index.ts` re-exports ALL api-layer objects:
```ts
export { authApi, handleAuthError } from "./api/auth.api";
export { bookingApi } from "./api/booking.api";
export { parkingApi } from "./api/parking.api";
export { vehicleApi } from "./api/vehicle.api";
export { notificationApi } from "./api/notification.api";
export { incidentApi } from "./api/incident.api";
export { adminApi } from "./api/admin.api";
export { chatbotApi } from "./api/chatbot.api";
export { aiApi } from "./api/ai.api";
```

This allows pages/components to `import { adminApi } from "@/services"` — technically bypassing the `services/api/` path but still importing API-layer objects directly.

**Fix needed:** Remove all `*Api` exports from `services/index.ts`. Only export business services + types. Consumers must transition to business service methods.

---

## 6. Redux Slices — Architectural Decision Needed

All 4 Redux slices (`authSlice`, `bookingSlice`, `parkingSlice`, `notificationSlice`) contain `createAsyncThunk` that call API directly. This is standard Redux Toolkit pattern.

**Options:**
- **Option A**: Allow slices to import API — they ARE business/state management layer
- **Option B**: Move thunks to call business services instead of API directly
- **Option C**: Extract thunks out of slice files into separate thunk files that use business services

**Note**: Option A is most pragmatic (least change). Business services themselves use Redux `store.dispatch`, creating a circular dependency risk if slices also call business services. Recommend Architect decide.

---

## 7. Total Scope Summary

| Category | Files | Violation Imports |
|---|---|---|
| Pages → `services/api/*` direct | 12 | 23 |
| Pages → `@/services` barrel (API objects) | 7 | 7 |
| Components → `services/api/*` direct | 3 | 4 |
| Components → `@/services` barrel (API objects) | 3 | 3 |
| Store slices → `services/api/*` direct | 4 | 5 |
| **TOTAL** | **29 unique files** | **42 violation imports** |

### Files to create (new):
1. `services/business/ai.service.ts` — ~11 methods
2. `services/business/chatbot.service.ts` — ~6 methods

### Files to modify:
1. `services/business/parking.service.ts` — add `getFloors()`
2. `services/business/booking.service.ts` — add `getPackagePricing()`, `getRevenueSummary()`, `getDailyRevenue()`, `getHourlyRevenue()`
3. `services/business/admin.service.ts` — verify `getCameras()`, `createUser()` wrappers exist
4. `services/business/index.ts` — add exports for ai + chatbot services
5. `services/index.ts` — remove api-layer object exports, only export business services
6. **19 page files** — change API imports → business service imports
7. **4 component files** — change API imports → business service imports
8. **4 Redux slice files** — (pending Architect decision)

### Total files touched: ~31 files

---

## 8. Nguồn

| # | Source | Mô tả |
|---|---|---|
| 1 | `spotlove-ai/src/services/index.ts` | Barrel export — violation enabler |
| 2 | `spotlove-ai/src/services/business/index.ts` | Business layer exports |
| 3 | `spotlove-ai/src/services/api/*.api.ts` | All 9 API modules |
| 4 | `spotlove-ai/src/services/business/*.service.ts` | 7 existing business services |
| 5 | grep results across `src/pages/`, `src/components/`, `src/store/slices/` | Violation discovery |
