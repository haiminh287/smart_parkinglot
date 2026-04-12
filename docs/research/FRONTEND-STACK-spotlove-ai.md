# Research Report: Frontend Tech Stack — spotlove-ai/

**Task:** Frontend Analysis | **Date:** 2026-04-06 | **Type:** Codebase

---

## 1. TL;DR — Đọc trong 60 giây

> **KẾT LUẬN: Frontend KHÔNG phải Next.js. Vẫn là React 18 + Vite 5 SPA.**
>
> 1. **100% React + Vite SPA** — package name = `vite_react_shadcn_ts`, build = `vite build`, entry = `index.html` + `main.tsx`, không có bất kỳ Next.js dependency, config, hay file-system routing nào.
> 2. **shadcn/ui (50+ components)** + Radix UI primitives + TailwindCSS 3.4 + Lucide icons.
> 3. **Redux Toolkit + React Query** dual state management — Redux cho global state (auth, parking, booking, websocket, notification), React Query cho server state caching.
> 4. **Axios** + centralized API client với CSRF protection, cookie-based auth (Django OAuth2).
> 5. **Origin: Lovable.dev** — generated project (meta tags, `lovable-tagger` devDep), đã customized significantly.

---

## 2. Verdict: NextJS hay React+Vite?

### Bằng chứng KHÔNG phải Next.js:

| Check                                | Kết quả                                                                   |
| ------------------------------------ | ------------------------------------------------------------------------- |
| `next` in dependencies?              | ❌ KHÔNG có                                                               |
| `next.config.js/ts/mjs` exists?      | ❌ KHÔNG tồn tại                                                          |
| `app/` directory (Next App Router)?  | ❌ KHÔNG có                                                               |
| `pages/` = Next.js file routing?     | ❌ Là `src/pages/` — chỉ là convention folder, không phải Next.js routing |
| `getServerSideProps/getStaticProps`? | ❌ Không có                                                               |
| Entry point                          | `index.html` + `src/main.tsx` → `createRoot()` → pure client-side SPA     |
| Build command                        | `vite build` (không phải `next build`)                                    |
| Dev command                          | `vite` (không phải `next dev`)                                            |
| Package name                         | `vite_react_shadcn_ts`                                                    |
| `components.json` → `rsc: false`     | Xác nhận không dùng React Server Components                               |

### Bằng chứng LÀ React + Vite SPA:

- `vite@^5.4.19` + `@vitejs/plugin-react-swc@^3.11.0` (SWC compiler)
- `react@^18.3.1` + `react-dom@^18.3.1`
- `react-router-dom@^6.30.1` — client-side routing via `<BrowserRouter>`
- `src/main.tsx` → `createRoot(document.getElementById("root")!).render(<App />)`
- `index.html` ở root (Vite SPA pattern)

---

## 3. All Dependencies (with versions)

### 3.1 Core Framework

| Package                    | Version | Mục đích                |
| -------------------------- | ------- | ----------------------- |
| `react`                    | ^18.3.1 | UI framework            |
| `react-dom`                | ^18.3.1 | DOM renderer            |
| `react-router-dom`         | ^6.30.1 | Client-side routing     |
| `typescript`               | ^5.8.3  | Type system             |
| `vite`                     | ^5.4.19 | Build tool + dev server |
| `@vitejs/plugin-react-swc` | ^3.11.0 | React SWC transform     |

### 3.2 State Management

| Package                 | Version | Mục đích                           |
| ----------------------- | ------- | ---------------------------------- |
| `@reduxjs/toolkit`      | ^2.11.2 | Global state (RTK)                 |
| `react-redux`           | ^9.2.0  | React-Redux bindings               |
| `@tanstack/react-query` | ^5.83.0 | Server state / data fetching cache |

**Redux Slices:** `authSlice`, `parkingSlice`, `bookingSlice`, `notificationSlice`, `websocketSlice`

### 3.3 UI Component Library — shadcn/ui + Radix UI

| Package                           | Version |
| --------------------------------- | ------- |
| `@radix-ui/react-accordion`       | ^1.2.11 |
| `@radix-ui/react-alert-dialog`    | ^1.14   |
| `@radix-ui/react-avatar`          | ^1.1.10 |
| `@radix-ui/react-checkbox`        | ^1.3.2  |
| `@radix-ui/react-dialog`          | ^1.1.14 |
| `@radix-ui/react-dropdown-menu`   | ^2.1.15 |
| `@radix-ui/react-hover-card`      | ^1.1.14 |
| `@radix-ui/react-label`           | ^2.1.7  |
| `@radix-ui/react-navigation-menu` | ^1.2.13 |
| `@radix-ui/react-popover`         | ^1.1.14 |
| `@radix-ui/react-progress`        | ^1.1.7  |
| `@radix-ui/react-radio-group`     | ^1.3.7  |
| `@radix-ui/react-scroll-area`     | ^1.2.9  |
| `@radix-ui/react-select`          | ^2.2.5  |
| `@radix-ui/react-separator`       | ^1.1.7  |
| `@radix-ui/react-slider`          | ^1.3.5  |
| `@radix-ui/react-slot`            | ^1.2.3  |
| `@radix-ui/react-switch`          | ^1.2.5  |
| `@radix-ui/react-tabs`            | ^1.1.12 |
| `@radix-ui/react-toast`           | ^1.2.14 |
| `@radix-ui/react-toggle`          | ^1.1.9  |
| `@radix-ui/react-toggle-group`    | ^1.1.10 |
| `@radix-ui/react-tooltip`         | ^1.2.7  |
| `@radix-ui/react-aspect-ratio`    | ^1.1.7  |
| `@radix-ui/react-collapsible`     | ^1.1.11 |
| `@radix-ui/react-context-menu`    | ^2.2.15 |
| `@radix-ui/react-menubar`         | ^1.1.15 |

**shadcn/ui config** (`components.json`): style=default, baseColor=slate, cssVariables=true, rsc=false

**50+ UI components** in `src/components/ui/` (accordion, alert-dialog, avatar, badge, breadcrumb, button, calendar, card, carousel, chart, checkbox, collapsible, command, context-menu, dialog, drawer, dropdown-menu, form, hover-card, input-otp, input, label, menubar, navigation-menu, pagination, popover, progress, radio-group, resizable, scroll-area, select, separator, sheet, sidebar, skeleton, slider, sonner, switch, table, tabs, textarea, toast, toaster, toggle, toggle-group, tooltip)

### 3.4 Styling

| Package                    | Version  | Mục đích                       |
| -------------------------- | -------- | ------------------------------ |
| `tailwindcss`              | ^3.4.17  | Utility-first CSS              |
| `tailwindcss-animate`      | ^1.0.7   | Animation utilities            |
| `@tailwindcss/typography`  | ^0.5.16  | Prose styling (devDep)         |
| `autoprefixer`             | ^10.4.21 | PostCSS autoprefixer           |
| `postcss`                  | ^8.5.6   | CSS processing                 |
| `class-variance-authority` | ^0.7.1   | Variant-based classes (shadcn) |
| `clsx`                     | ^2.1.1   | className merging              |
| `tailwind-merge`           | ^2.6.0   | TW class dedup                 |

### 3.5 API & Data Communication

| Package                 | Version | Mục đích                    |
| ----------------------- | ------- | --------------------------- |
| `axios`                 | ^1.13.2 | HTTP client                 |
| `@supabase/supabase-js` | ^2.91.0 | Supabase (Google/FB OAuth?) |

**Custom WebSocket service** — native WebSocket (no Socket.IO), connects to `realtime-service-go` port 8006.

### 3.6 Forms & Validation

| Package               | Version  | Mục đích              |
| --------------------- | -------- | --------------------- |
| `react-hook-form`     | ^7.61.1  | Form state management |
| `@hookform/resolvers` | ^3.10.0  | Validator integration |
| `zod`                 | ^3.25.76 | Schema validation     |

### 3.7 Feature Libraries

| Package                  | Version  | Mục đích                |
| ------------------------ | -------- | ----------------------- |
| `recharts`               | ^2.15.4  | Charts/graphs (admin)   |
| `date-fns`               | ^3.6.0   | Date manipulation       |
| `lucide-react`           | ^0.462.0 | Icon library            |
| `sonner`                 | ^1.7.4   | Toast notifications     |
| `vaul`                   | ^0.9.9   | Drawer component        |
| `cmdk`                   | ^1.1.1   | Command palette         |
| `embla-carousel-react`   | ^8.6.0   | Carousel                |
| `react-day-picker`       | ^8.10.1  | Date picker             |
| `react-resizable-panels` | ^2.1.9   | Resizable panels        |
| `input-otp`              | ^1.4.2   | OTP input               |
| `qrcode.react`           | ^4.2.0   | QR code generation      |
| `js-cookie`              | ^3.0.5   | Cookie management       |
| `next-themes`            | ^0.3.0   | Dark/light theme toggle |

> ⚠️ **NOTE**: `next-themes` is NOT a Next.js dependency. It works with any React app for theme switching. The `ThemeProvider` wraps the app in `contexts/ThemeContext.tsx`.

### 3.8 Testing

| Package                     | Version | Mục đích              |
| --------------------------- | ------- | --------------------- |
| `vitest`                    | ^3.2.4  | Unit test runner      |
| `@testing-library/react`    | ^16.0.0 | Component testing     |
| `@testing-library/jest-dom` | ^6.6.0  | DOM matchers          |
| `jsdom`                     | ^20.0.3 | Browser env for tests |
| `@playwright/test`          | ^1.58.2 | E2E testing           |

### 3.9 Dev Tools

| Package                       | Version | Mục đích                     |
| ----------------------------- | ------- | ---------------------------- |
| `eslint`                      | ^9.32.0 | Linting                      |
| `typescript-eslint`           | ^8.38.0 | TS ESLint plugin             |
| `eslint-plugin-react-hooks`   | ^5.2.0  | Hooks rules                  |
| `eslint-plugin-react-refresh` | ^0.4.20 | HMR rules                    |
| `lovable-tagger`              | ^1.1.13 | Lovable.dev component tagger |

---

## 4. Architecture Overview

### 4.1 Routing — React Router DOM v6 (Client-Side)

```
<BrowserRouter>
  <Routes>
    {/* Public */}
    /login         → LoginPage
    /register      → RegisterPage
    /auth/callback → AuthCallbackPage

    {/* Protected (ProtectedRoute wrapper) */}
    /              → Index (UserDashboard)
    /booking       → BookingPage
    /history       → HistoryPage
    /cameras       → CamerasPage
    /map           → MapPage
    /support       → SupportPage
    /settings      → SettingsPage
    /payment       → PaymentPage
    /kiosk         → KioskPage
    /checkin       → CheckInOutPage
    /banknote      → BanknoteDetectionPage
    /panic         → PanicButtonPage

    {/* Admin Routes */}
    /admin           → AdminDashboard
    /admin/users     → AdminUsersPage
    /admin/zones     → AdminZonesPage
    /admin/slots     → AdminSlotsPage
    /admin/cameras   → AdminCamerasPage
    /admin/config    → AdminConfigPage
    /admin/violations→ AdminViolationsPage
    /admin/esp32     → AdminESP32Page
    /admin/revenue   → AdminRevenuePage

    /*             → NotFound
  </Routes>
</BrowserRouter>
```

### 4.2 State Management — Dual Pattern

```
Redux Toolkit (global state)          │  TanStack React Query (server cache)
──────────────────────────────────────│──────────────────────────────────────
store/slices/authSlice.ts             │  QueryClientProvider wraps app
store/slices/parkingSlice.ts          │  Used for API data fetching/caching
store/slices/bookingSlice.ts          │
store/slices/notificationSlice.ts     │
store/slices/websocketSlice.ts        │
                                      │
Redux handles: auth state, parking    │  React Query handles: server state
lot data, booking state, WebSocket    │  caching, background refetch,
connection state, notifications       │  pagination
```

### 4.3 Service Layer Architecture

```
src/services/
├── api/                    ← Pure HTTP layer (snake_case params — Django REST)
│   ├── axios.client.ts     ← Centralized Axios instance + interceptors
│   ├── endpoints.ts        ← All API endpoint URLs
│   ├── auth.api.ts
│   ├── booking.api.ts
│   ├── parking.api.ts
│   ├── vehicle.api.ts
│   ├── notification.api.ts
│   ├── incident.api.ts
│   ├── admin.api.ts
│   ├── ai.api.ts
│   └── chatbot.api.ts
│
├── business/               ← Business logic layer (camelCase — internal)
│   ├── auth.service.ts     ← Dispatches Redux + calls API
│   ├── booking.service.ts
│   ├── parking.service.ts
│   ├── vehicle.service.ts
│   ├── notification.service.ts
│   ├── incident.service.ts
│   └── admin.service.ts
│
└── websocket.service.ts    ← Native WebSocket to realtime-service-go:8006
```

**API Client config**: Axios with `withCredentials: true` (HTTP-only cookies), CSRF token from cookie, 30s timeout, base URL `/api` → Vite proxy → gateway:8000.

### 4.4 Auth Approach

- **Cookie-based auth** (HTTP-only cookies, Django OAuth2)
- **Supabase JS** present → likely for Google/Facebook OAuth redirect
- **AuthContext** wraps Redux auth state for backward compatibility
- **ProtectedRoute** component guards authenticated pages
- Supports: Email/Password, Google OAuth, Facebook OAuth
- CSRF protection via `csrftoken` cookie

### 4.5 Component Structure

```
src/components/
├── ui/               ← 50+ shadcn/ui components (generated via CLI)
├── booking/          ← Booking-specific components
├── dashboard/        ← Dashboard widgets
├── effects/          ← Visual effects (SnowfallEffect)
├── layout/           ← AppSidebar, MainLayout, ProtectedRoute
├── map/              ← Map-related components
├── settings/         ← Settings page components
├── support/          ← Support/contact widgets
├── ErrorBoundary.tsx
└── NavLink.tsx
```

### 4.6 Dev Server Proxy Config (vite.config.ts)

```
/ai/cameras → AI service (localhost:8009) — camera streams bypass gateway
/api/*      → Gateway (localhost:8000) — all API requests
/ws/*       → WebSocket (ws://localhost:8006) — realtime service
```

---

## 5. Testing Setup

### 5.1 Unit Tests — Vitest + Testing Library

- Config: `vitest.config.ts` — jsdom environment, globals enabled
- Setup: `src/test/setup.ts`
- Tests: `src/test/*.test.{ts,tsx}` (11 test files)
- Includes: api tests, component tests, smoke tests

### 5.2 E2E Tests — Playwright

- Config: `playwright.config.ts` — baseURL `localhost:8080`
- Tests: `e2e/*.spec.ts` (9 spec files + global-setup)
- Covers: admin, booking, dashboard, history, public pages, user pages, API endpoints
- Auth state stored in `e2e/.auth/`

---

## 6. Directory Structure Overview

```
spotlove-ai/
├── index.html                    ← Vite SPA entry (Lovable.dev generated)
├── package.json                  ← "vite_react_shadcn_ts"
├── vite.config.ts                ← Vite 5 + SWC + proxy config
├── vitest.config.ts              ← Unit test config
├── playwright.config.ts          ← E2E test config
├── tsconfig.json                 ← Base TS config (path aliases @/*)
├── tsconfig.app.json             ← App TS config (ES2020, react-jsx)
├── tsconfig.node.json            ← Node TS config
├── tailwind.config.ts            ← TW3 + shadcn theme tokens
├── postcss.config.js             ← TW + autoprefixer
├── eslint.config.js              ← ESLint 9 flat config
├── components.json               ← shadcn/ui CLI config (rsc: false)
├── public/                       ← Static assets
├── e2e/                          ← Playwright E2E tests (9 specs)
├── src/
│   ├── main.tsx                  ← React entry (createRoot)
│   ├── App.tsx                   ← Router + providers
│   ├── index.css                 ← Global styles + CSS variables
│   ├── App.css
│   ├── vite-env.d.ts
│   ├── pages/                    ← Page components (18 pages + 9 admin)
│   │   ├── admin/                ← Admin pages
│   │   ├── Index.tsx             ← Home/Dashboard
│   │   ├── LoginPage.tsx
│   │   ├── BookingPage.tsx
│   │   └── ...
│   ├── components/               ← Reusable components
│   │   ├── ui/                   ← 50+ shadcn/ui components
│   │   ├── layout/               ← AppSidebar, MainLayout, ProtectedRoute
│   │   ├── booking/
│   │   ├── dashboard/
│   │   ├── map/
│   │   ├── settings/
│   │   ├── support/
│   │   └── effects/
│   ├── store/                    ← Redux Toolkit store
│   │   ├── index.ts              ← configureStore
│   │   ├── hooks.ts              ← typed useAppDispatch/useAppSelector
│   │   └── slices/               ← 5 slices (auth, parking, booking, notification, websocket)
│   ├── services/                 ← Service layer
│   │   ├── api/                  ← HTTP calls (11 files)
│   │   ├── business/             ← Business logic (8 files)
│   │   └── websocket.service.ts
│   ├── hooks/                    ← Custom hooks (8 files)
│   ├── contexts/                 ← React contexts (auth + theme)
│   ├── lib/                      ← Utilities (dijkstra.ts, utils.ts)
│   ├── types/                    ← TypeScript types (parking.ts)
│   ├── integrations/             ← Empty (placeholder)
│   └── test/                     ← Test files (11 tests + setup)
└── playwright-report/            ← E2E test reports
```

---

## 7. ⚠️ Gotchas & Notable Findings

- [ ] **[IMPORTANT]** User claims "changed to NextJS" — **this is INCORRECT**. Codebase là 100% React+Vite SPA. Không có dấu hiệu migration sang Next.js nào.
- [ ] **[NOTE]** `next-themes@^0.3.0` dependency có thể gây nhầm lẫn — đây là thư viện theme switching, **KHÔNG** phải Next.js framework.
- [ ] **[NOTE]** `@supabase/supabase-js@^2.91.0` present — dùng cho OAuth social login (Google/Facebook), không phải primary DB.
- [ ] **[NOTE]** Origin: **Lovable.dev** (AI-generated project) — `index.html` meta tags, `lovable-tagger` devDep. Đã customized nặng.
- [ ] **[NOTE]** `tsconfig` có `strict: false`, `noImplicitAny: false`, `strictNullChecks: false` — TypeScript rất lỏng, nhiều runtime risks.
- [ ] **[NOTE]** WebSocket service dùng native WebSocket (không Socket.IO), protocol format Django Channels `{ type, data }`.
- [ ] **[NOTE]** `tailwind.config.ts` content array có `./pages/**`, `./components/**`, `./app/**` — đây là template mặc định shadcn, không có nghĩa có `app/` directory Next.js.

---

## 8. Summary Table

| Aspect            | Technology                                     |
| ----------------- | ---------------------------------------------- |
| **Framework**     | React 18.3 (NOT Next.js)                       |
| **Build Tool**    | Vite 5.4 + SWC                                 |
| **Language**      | TypeScript 5.8                                 |
| **Routing**       | React Router DOM v6 (client-side)              |
| **State: Global** | Redux Toolkit 2.11                             |
| **State: Server** | TanStack React Query 5.83                      |
| **UI Library**    | shadcn/ui + Radix UI primitives                |
| **Styling**       | Tailwind CSS 3.4 + CSS variables               |
| **Icons**         | Lucide React                                   |
| **Forms**         | React Hook Form 7.61 + Zod 3.25                |
| **HTTP Client**   | Axios 1.13 (cookie-based, CSRF)                |
| **WebSocket**     | Native WebSocket (no Socket.IO)                |
| **Auth**          | Cookie-based (Django OAuth2) + Supabase social |
| **Charts**        | Recharts 2.15                                  |
| **Theme**         | next-themes 0.3 (dark/light)                   |
| **Unit Tests**    | Vitest 3.2 + Testing Library + jsdom           |
| **E2E Tests**     | Playwright 1.58                                |
| **Linting**       | ESLint 9 + typescript-eslint                   |
| **Dev Port**      | 8080 (Vite dev server)                         |

---

## 9. Nguồn

| #   | Source                        | Mô tả                         |
| --- | ----------------------------- | ----------------------------- |
| 1   | `spotlove-ai/package.json`    | Dependencies & scripts        |
| 2   | `spotlove-ai/vite.config.ts`  | Build & proxy config          |
| 3   | `spotlove-ai/src/App.tsx`     | Router & provider tree        |
| 4   | `spotlove-ai/src/main.tsx`    | Entry point (createRoot)      |
| 5   | `spotlove-ai/components.json` | shadcn/ui config (rsc:false)  |
| 6   | `spotlove-ai/src/store/`      | Redux store architecture      |
| 7   | `spotlove-ai/src/services/`   | Service layer architecture    |
| 8   | `spotlove-ai/index.html`      | Vite SPA entry (Lovable meta) |
