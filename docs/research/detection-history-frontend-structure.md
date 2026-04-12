# Research Report: Web Frontend Structure for Detection History Page

**Date:** 2026-04-11 | **Type:** Codebase Analysis

---

## 1. TL;DR — Đọc trong 60 giây

> 1. **Router**: `react-router-dom` v6 in `App.tsx`. Add `<Route path="/detection-history">` wrapped in `<ProtectedRoute>`.
> 2. **Backend API đã có**: `GET /ai/parking/detections/` — paginated, filterable (plate_text, date_from, date_to, action). Returns `{total, page, page_size, results}`.
> 3. **UI Stack**: shadcn/ui + Tailwind + lucide-react icons. All components (`Table`, `Badge`, `Button`, `Select`, `Input`, `Pagination`) already available in `components/ui/`.
> 4. **Sidebar**: `components/layout/AppSidebar.tsx` — add 1 object to `userNavItems` or `adminNavItems` array.
> 5. **API pattern**: `apiClient.get(url, { params })` — Axios instance with auth cookies auto-attached.

---

## 2. Routing — `App.tsx`

**File:** `spotlove-ai/src/App.tsx`

**Pattern:** `react-router-dom` v6 with `<BrowserRouter>` → `<Routes>` → `<Route>`.

**Protected route pattern:**

```tsx
import DetectionHistoryPage from "./pages/DetectionHistoryPage";

<Route
  path="/detection-history"
  element={
    <ProtectedRoute>
      {" "}
      {/* or <ProtectedRoute requireAdmin> for admin-only */}
      <DetectionHistoryPage />
    </ProtectedRoute>
  }
/>;
```

**Key imports at top of App.tsx:**

- `ProtectedRoute` from `@/components/layout/ProtectedRoute`
- Page component default-imported from `./pages/XxxPage`

---

## 3. Page Pattern — Reference: `HistoryPage.tsx` + `AdminViolationsPage.tsx`

**Structure every page follows:**

```tsx
import { useState, useEffect, useCallback } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
// ... lucide-react icons

export default function DetectionHistoryPage() {
  const { toast } = useToast();
  const [data, setData] = useState<Detection[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiCall(params);
      setData(response.results);
    } catch (error) {
      toast({ title: "Lỗi", description: "...", variant: "destructive" });
    } finally {
      setIsLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="animate-fade-in">
          <h1 className="text-2xl font-bold text-foreground">Title</h1>
          <p className="mt-1 text-muted-foreground">Subtitle</p>
        </div>
        {/* Filters + Content */}
      </div>
    </MainLayout>
  );
}
```

**Key points:**

- Wrap everything in `<MainLayout>` (provides sidebar + mobile nav)
- Data fetching via `useState` + `useEffect` + `useCallback` (NOT react-query in pages — consistent pattern)
- Toast for errors via `useToast()` hook
- Loading state: `Loader2` icon from lucide with `animate-spin`
- Tailwind classes: `space-y-6`, `animate-fade-in`, `rounded-2xl`, `border`, `bg-card`

---

## 4. API Client Pattern

**Axios client:** `services/api/axios.client.ts`

```
Base URL: "/api" (dev, proxied by Vite) or VITE_API_URL + "/api" (prod)
Auth: HTTP-only cookies (withCredentials: true)
CSRF: auto-attached from cookie
Timeout: 30000ms
```

**AI API file:** `services/api/ai.api.ts`

**Pattern for a GET with query params:**

```ts
import apiClient from "./axios.client";

// Response type
export interface DetectionRecord {
  id: number;
  plateText: string;
  confidence: number;
  decision: string;
  imageUrl: string | null;
  bbox: number[] | null;
  cameraId: string | null;
  action: string;                // "scan" | "check_in" | "check_out"
  predictionType: string;
  createdAt: string;
  processingTimeMs: number | null;
}

export interface DetectionHistoryResponse {
  total: number;
  page: number;
  pageSize: number;
  results: DetectionRecord[];
}

export interface DetectionHistoryParams {
  page?: number;
  pageSize?: number;
  plateText?: string;
  dateFrom?: string;    // ISO date "2026-04-11"
  dateTo?: string;
  action?: string;      // "scan" | "check_in" | "check_out"
}

// In aiApi object:
getDetectionHistory: async (params?: DetectionHistoryParams): Promise<DetectionHistoryResponse> => {
  const queryParams: Record<string, string> = {};
  if (params?.page) queryParams.page = String(params.page);
  if (params?.pageSize) queryParams.page_size = String(params.pageSize);
  if (params?.plateText) queryParams.plate_text = params.plateText;
  if (params?.dateFrom) queryParams.date_from = params.dateFrom;
  if (params?.dateTo) queryParams.date_to = params.dateTo;
  if (params?.action) queryParams.action = params.action;

  const response = await apiClient.get<DetectionHistoryResponse>(
    "/ai/parking/detections/",
    { params: queryParams },
  );
  return response.data;
},
```

**NOTE:** Backend `parking_router` at `/ai/parking/detections/` returns **snake_case** keys (NOT camelCase — FastAPI, not Django). Frontend needs to map: `plate_text` → `plateText`, etc.

---

## 5. Backend API — Already Exists

**Endpoint:** `GET /ai/parking/detections/`  
**File:** `ai-service-fastapi/app/routers/metrics.py` (line ~122)

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int (≥1) | Page number, default 1 |
| `page_size` | int (1-100) | Items per page, default 20 |
| `plate_text` | string | LIKE search on plate text |
| `date_from` | date (ISO) | Filter from date |
| `date_to` | date (ISO) | Filter to date |
| `action` | string | "scan", "check_in", "check_out" |

**Response structure:**

```json
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "id": 42,
      "plate_text": "51F-123.45",
      "confidence": 0.92,
      "decision": "check_in_success",
      "image_url": "/ai/images/plates/abc.jpg",
      "bbox": [100, 200, 300, 400],
      "camera_id": "gate-cam-1",
      "action": "check_in",
      "prediction_type": "check_in_success",
      "created_at": "2026-04-11T10:30:00",
      "processing_time_ms": 245.3
    }
  ]
}
```

---

## 6. Sidebar / Navigation

**File:** `spotlove-ai/src/components/layout/AppSidebar.tsx`

**Pattern — just add an object to the array:**

```ts
import { ScanSearch } from "lucide-react"; // or Eye, History, etc.

const userNavItems = [
  // ... existing items
  { icon: ScanSearch, label: "Nhận diện", path: "/detection-history" },
  // ...
];

// For admin sidebar:
const adminNavItems = [
  // ... existing items
  { icon: ScanSearch, label: "Lịch sử nhận diện", path: "/detection-history" },
];
```

Each item is `{ icon: LucideIcon, label: string, path: string }`. Active state highlighting is automatic via `location.pathname === item.path`.

---

## 7. UI Component Library

**Stack:** shadcn/ui (Radix primitives) + Tailwind CSS + lucide-react icons

**Available components in `components/ui/`:**

| Component                                                                 | File             | Use for                             |
| ------------------------------------------------------------------------- | ---------------- | ----------------------------------- |
| `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell` | `table.tsx`      | Data table                          |
| `Badge`                                                                   | `badge.tsx`      | Status tags (success/warning/error) |
| `Button`                                                                  | `button.tsx`     | Actions, filters                    |
| `Input`                                                                   | `input.tsx`      | Search field                        |
| `Select`, `SelectTrigger`, `SelectContent`, `SelectItem`                  | `select.tsx`     | Filter dropdowns                    |
| `Pagination`                                                              | `pagination.tsx` | Page navigation                     |
| `Dialog`                                                                  | `dialog.tsx`     | Detail modal / image preview        |
| `Card`                                                                    | `card.tsx`       | Stats cards, container              |
| `Skeleton`                                                                | `skeleton.tsx`   | Loading placeholders                |
| `Tabs`                                                                    | `tabs.tsx`       | Tab filters                         |
| `Calendar`                                                                | `calendar.tsx`   | Date picker (react-day-picker)      |

**Icon library:** `lucide-react` — all icons imported individually: `import { Camera, Search, Filter } from "lucide-react"`

**Utility:** `cn()` from `@/lib/utils` — merges Tailwind classes (clsx + tailwind-merge)

---

## 8. Types Pattern

**File:** `spotlove-ai/src/types/parking.ts`

Types are defined as:

- **Interface-based** TypeScript types
- Exported individually
- String union types for enums: `export type VehicleType = "Car" | "Motorbike";`

For AI-specific types, they're defined **inline in the API file** (`ai.api.ts`), not in `types/`. This is the pattern to follow for detection history types.

---

## 9. Files/Modules Liên Quan

| File                               | Mục đích                                              | Tái dụng?                |
| ---------------------------------- | ----------------------------------------------------- | ------------------------ |
| `services/api/ai.api.ts`           | AI API client — add `getDetectionHistory` method here | Yes — extend             |
| `services/api/axios.client.ts`     | Axios base client, pagination types                   | Yes — import `apiClient` |
| `components/layout/MainLayout.tsx` | Page wrapper with sidebar                             | Yes — wrap page          |
| `components/layout/AppSidebar.tsx` | Sidebar nav items                                     | Yes — add nav entry      |
| `App.tsx`                          | Router definitions                                    | Yes — add route          |
| `components/ui/table.tsx`          | shadcn Table components                               | Yes — import             |
| `components/ui/badge.tsx`          | Status badges                                         | Yes — import             |
| `components/ui/pagination.tsx`     | Pagination controls                                   | Yes — import             |
| `pages/AdminViolationsPage.tsx`    | Best list+filter+dialog reference page                | Reference pattern        |
| `pages/HistoryPage.tsx`            | Booking history with stats+cards                      | Reference pattern        |

---

## 10. Checklist cho Implementer

- [ ] Add types + `getDetectionHistory()` to `services/api/ai.api.ts`
- [ ] Create `pages/DetectionHistoryPage.tsx` following MainLayout + fetch pattern
- [ ] Add route in `App.tsx` with `<ProtectedRoute>`
- [ ] Add nav item in `AppSidebar.tsx` (`userNavItems` and/or `adminNavItems`)
- [ ] No new packages needed — all UI components already exist
- [ ] Backend endpoint already exists: `GET /ai/parking/detections/`
- [ ] Note: Backend returns **snake_case** — map to camelCase in frontend types
- [ ] Pattern reference: use `AdminViolationsPage.tsx` as closest template (list+filter+dialog)

---

## 11. Nguồn

| #   | File/URL                                              | Mô tả                                            |
| --- | ----------------------------------------------------- | ------------------------------------------------ |
| 1   | `spotlove-ai/src/App.tsx`                             | Router definitions                               |
| 2   | `spotlove-ai/src/components/layout/AppSidebar.tsx`    | Sidebar nav items                                |
| 3   | `spotlove-ai/src/components/layout/MainLayout.tsx`    | Page layout wrapper                              |
| 4   | `spotlove-ai/src/services/api/ai.api.ts`              | AI API client                                    |
| 5   | `spotlove-ai/src/services/api/axios.client.ts`        | Axios base + pagination types                    |
| 6   | `spotlove-ai/src/services/api/endpoints.ts`           | Endpoint constants                               |
| 7   | `spotlove-ai/src/pages/HistoryPage.tsx`               | Reference: list page pattern                     |
| 8   | `spotlove-ai/src/pages/admin/AdminViolationsPage.tsx` | Reference: table+filter+dialog pattern           |
| 9   | `ai-service-fastapi/app/routers/metrics.py`           | Backend detection history endpoint               |
| 10  | `spotlove-ai/package.json`                            | Dependencies (shadcn, react-router, axios, etc.) |
