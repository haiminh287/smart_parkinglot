# Research Report: Auth Refresh, Logout, and Chatbot Health Contract

**Task:** ISSUE-SECURITY-BLOCKERS-2026-03-13 | **Date:** 2026-03-15 | **Type:** Mixed

---

## 1. TL;DR — Đọc trong 60 giây

> **Architect/Implementer cần biết ngay:**
>
> 1. Runtime hiện tại **không có refresh endpoint canonical nào**. FE chỉ còn khai báo stale constant `/auth/token/refresh/`, nhưng không có callsite/interceptor nào dùng.
> 2. `POST /auth/logout/` trả `200` khi unauthenticated là **chủ đích idempotent**, vì cả auth-service lẫn gateway đều clear session/cookie theo best-effort và luôn trả thành công.
> 3. Chatbot health qua gateway nên coi **`/chatbot/health/` là canonical path**. Request thiếu trailing slash dễ nhận `307` từ FastAPI/Starlette; gateway proxy hiện chỉ rewrite `Location` dạng relative nên có thể làm lộ internal host nếu upstream trả absolute redirect URL.

---

## 2. Phân Tích Codebase Hiện Tại

### 2.1 Files/Modules Liên Quan

| File | Mục đích | Relevance | Có thể tái dụng? |
| --- | --- | --- | --- |
| `backend-microservices/auth-service/users/urls.py` | Khai báo auth endpoints thực tế | High | Yes — source of truth cho auth-service |
| `backend-microservices/auth-service/users/views.py` | Hành vi logout/current-user | High | Yes |
| `backend-microservices/auth-service/auth_service/urls.py` | Mount `/auth/` và health aliases | High | Yes |
| `backend-microservices/gateway-service-go/internal/router/routes.go` | Quyết định special routes + bypass auth/health | High | Yes |
| `backend-microservices/gateway-service-go/internal/handler/auth.go` | Gateway login/logout/session behavior | High | Yes |
| `backend-microservices/gateway-service-go/internal/handler/proxy.go` | Reverse proxy path + redirect rewrite | High | Yes |
| `backend-microservices/gateway-service-go/internal/config/config.go` | Normalize `/api/*` và service route mapping | High | Yes |
| `spotlove-ai/src/services/api/endpoints.ts` | FE endpoint constants | High | Yes |
| `spotlove-ai/src/services/api/auth.api.ts` | FE auth callsites thực tế | High | Yes |
| `spotlove-ai/src/services/api/axios.client.ts` | Base URL `/api` + interceptor behavior | High | Yes |
| `spotlove-ai/src/store/slices/authSlice.ts` | FE auth flow thực tế | High | Yes |
| `backend-microservices/chatbot-service-fastapi/app/main.py` | Health routes chatbot thực tế | High | Yes |
| `backend-microservices/chatbot-service-fastapi/app/middleware/gateway_auth.py` | Exempt paths cho health | High | Yes |
| `backend-microservices/chatbot-service-fastapi/tests/test_smoke.py` | Service-local canonical health expectation | High | Yes |
| `backend-microservices/auth-service/README.md` | Docs cũ, hiện lệch contract | Medium | No — cần cập nhật hoặc bỏ dòng stale |
| `docs/04_FRONTEND_BACKEND_API_OVERVIEW.md` | Docs tổng hợp hiện lệch contract refresh | Medium | No — cần cập nhật |

### 2.2 Pattern Đang Dùng

```py
# Source: backend-microservices/auth-service/users/urls.py
urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('me/', views.CurrentUserView.as_view(), name='current-user'),
]
```

```py
# Source: backend-microservices/auth-service/users/views.py
class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        response = Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        response.delete_cookie('sessionid')
        return response
```

```go
// Source: backend-microservices/gateway-service-go/internal/router/routes.go
if method == http.MethodPost {
    if cleanPath == "auth/login/" || cleanPath == "auth/login" {
        authHandler.HandleLogin(c)
        return
    }
    if cleanPath == "auth/logout/" || cleanPath == "auth/logout" {
        authHandler.HandleLogout(c)
        return
    }
}
```

```go
// Source: backend-microservices/gateway-service-go/internal/handler/auth.go
func (h *AuthHandler) HandleLogout(c *gin.Context) {
    sessionID, _ := c.Cookie("session_id")
    if sessionID != "" {
        _ = h.store.DeleteSession(sessionID)
    }
    h.clearSessionCookie(c)
    targetURL := h.cfg.AuthServiceURL + "/auth/logout/"
    httpReq, _ := http.NewRequest("POST", targetURL, nil)
    client := &http.Client{Timeout: 5 * time.Second}
    client.Do(httpReq) // Best-effort, ignore errors
    c.JSON(http.StatusOK, gin.H{"message": "Logged out successfully"})
}
```

```ts
// Source: spotlove-ai/src/services/api/endpoints.ts
AUTH: {
  LOGIN: "/auth/login/",
  REGISTER: "/auth/register/",
  LOGOUT: "/auth/logout/",
  REFRESH_TOKEN: "/auth/token/refresh/",
  ME: "/auth/me/",
}
```

```ts
// Source: spotlove-ai/src/services/api/auth.api.ts
logout: async (): Promise<void> => {
  await apiClient.post("/auth/logout/");
},
```

```ts
// Source: spotlove-ai/src/services/api/axios.client.ts
const rawApiUrl = (import.meta.env.VITE_API_URL as string | undefined)?.trim() || "/api";
...
const apiClient = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
});
```

```py
# Source: backend-microservices/chatbot-service-fastapi/app/main.py
@app.get("/health/")
@app.get("/chatbot/health/")
async def health_check():
    return {"status": "healthy", "service": "chatbot-service", "version": "3.0.0"}
```

```go
// Source: backend-microservices/gateway-service-go/internal/handler/proxy.go
proxy.ModifyResponse = func(resp *http.Response) error {
    location := resp.Header.Get("Location")
    if location == "" {
        return nil
    }
    if strings.HasPrefix(location, "/") && !strings.HasPrefix(location, "/api/") {
        trimmed := strings.TrimPrefix(location, "/")
        resp.Header.Set("Location", fmt.Sprintf("/api/%s", trimmed))
    }
    return nil
}
```

### 2.3 Potential Conflicts

- Docs vẫn quảng bá refresh flow theo JWT (`/auth/token/refresh/`) nhưng runtime auth đang là gateway session + Redis, không có refresh route tương ứng.
- FE comment trong `authSlice.ts` vẫn nhắc “cookies for token storage / OAuth2 HTTP-only”, gây hiểu nhầm với session-based contract hiện tại.
- Hidden/full smoke nào gọi `/chatbot/health` không slash có thể bị `307` từ upstream và lộ internal host qua `Location` header.

### 2.4 Dependencies Đã Có (tránh install trùng)

- Không cần thư viện mới để fix issue này.
- Vấn đề là contract drift giữa code runtime, FE constants, docs, và smoke path.

---

## 3. Contract Facts

### 3.1 Canonical refresh endpoint hiện tại là gì?

**Không có canonical refresh endpoint đang được implement trong runtime hiện tại.**

Facts:
- `users/urls.py` không khai báo `token/refresh/`, `refresh/`, hay `token/verify/`.
- `auth_service/urls.py` chỉ mount `path('auth/', include('users.urls'))`.
- Gateway `routes.go` chỉ special-case `auth/login` và `auth/logout`; không có nhánh refresh.
- `AuthMiddleware` public path list cũng không có refresh.
- FE không có `authApi.refresh()`, không có Axios 401-refresh interceptor.

### 3.2 Có route nào support `/api/auth/refresh/` không?

**Không.**

Facts:
- External `/api/auth/refresh/` sau normalize ở gateway thành `auth/refresh/`.
- Gateway sẽ không special-case path này; request đi qua auth middleware rồi proxy sang auth-service.
- Auth-service không có `path('refresh/', ...)` hay alias tương đương, nên kết quả logic là `404` nếu vượt qua gateway auth.
- Stale FE/docs hiện nhắc `/auth/token/refresh/`, không phải `/auth/refresh/`.

### 3.3 FE thực tế đang gọi endpoint nào cho refresh?

**Không có callsite runtime nào đang gọi refresh.**

Facts:
- FE chỉ còn constant `ENDPOINTS.AUTH.REFRESH_TOKEN = "/auth/token/refresh/"`.
- `auth.api.ts` chỉ gọi `login`, `register`, `logout`, `google`, `facebook`, `me`.
- `axios.client.ts` không có response interceptor refresh token.
- Nếu ai đó dùng stale constant này trong tương lai, với `baseURL=/api` request thực tế sẽ là **`/api/auth/token/refresh/`**, nhưng hiện tại code runtime không dùng.

### 3.4 Logout `200` khi unauthenticated là chủ đích idempotent hay lệch contract?

**Đây là chủ đích idempotent, không phải lệch contract.**

Facts:
- Auth-service `LogoutView` dùng `AllowAny`, luôn gọi `logout(request)`, delete cookie, rồi trả `200`.
- Gateway `HandleLogout` luôn clear `session_id`, best-effort delete Redis session nếu có, best-effort forward xuống auth-service, rồi luôn trả `200`.
- Đây là pattern “clear whatever exists, success either way”, phù hợp cho logout idempotent.

### 3.5 Chatbot health canonical path có slash hay không?

Phân biệt theo tầng:
- **Service-local canonical:** `/health/` trong `chatbot-service-fastapi/tests/test_smoke.py`.
- **Gateway/public canonical:** `/chatbot/health/` theo `app.main.py`, `gateway_auth.py`, và docs gateway-facing hiện có.

**Kết luận practical cho full API smoke qua gateway:** dùng **`/chatbot/health/` có trailing slash**.

### 3.6 Redirect `307` lộ internal host xuất phát từ đâu?

**Nguồn gốc là FastAPI/Starlette trailing-slash redirect ở upstream, kết hợp với reverse proxy hiện không rewrite absolute `Location`.**

Flow:
1. Client gọi `/chatbot/health` không slash.
2. Gateway normalize/proxy path y nguyên thành `/chatbot/health` đến chatbot service.
3. FastAPI chỉ định nghĩa route `/chatbot/health/`, nên Starlette phát `307 Temporary Redirect` sang path có slash.
4. `httputil.NewSingleHostReverseProxy` đã set request host về internal target host.
5. `proxy.ModifyResponse` chỉ rewrite `Location` khi header bắt đầu bằng `/`; nếu upstream trả absolute URL thì internal host không bị rewrite và bị lộ ra ngoài.

---

## 4. So Sánh Phương Án

| Tiêu chí | Option A: Bỏ refresh khỏi contract + sửa smoke path | Option B: Implement refresh endpoint mới | Option C: Giữ docs cũ, chỉ vá redirect |
| --- | --- | --- | --- |
| Độ đúng với runtime hiện tại | High | Low-Med | Low |
| Patch size | Small | Medium-Large | Small |
| Rủi ro behavior drift | Low | High | Medium |
| Giải quyết hidden smoke health | Yes | No | Yes |
| Giải quyết contract drift auth | Yes | Partial | No |

**Note**: Facts nghiêng mạnh về Option A cho patch tối thiểu đúng contract hiện có.

---

## 5. ⚠️ Gotchas & Known Issues

- [ ] **[WARNING]** `backend-microservices/auth-service/README.md` đang ghi `POST /auth/token/refresh/`, nhưng route thật không tồn tại.
- [ ] **[WARNING]** `docs/04_FRONTEND_BACKEND_API_OVERVIEW.md` vẫn mô tả JWT refresh flow + `/auth/token/refresh/`, lệch với gateway-session runtime.
- [ ] **[WARNING]** `spotlove-ai/src/services/api/endpoints.ts` còn stale constant refresh; dù chưa được gọi, nó tạo hiểu nhầm contract.
- [ ] **[NOTE]** `spotlove-ai/src/store/slices/authSlice.ts` còn comment “token storage / OAuth2 HTTP-only”, không còn phản ánh đúng runtime session flow.
- [ ] **[NOTE]** Health path không slash có thể vẫn “work” nếu follow redirect, nhưng đây không phải canonical path tốt cho smoke vì có risk lộ internal host.

---

## 6. Recommended Fix Set

### Must-fix

1. **Chuẩn hóa contract auth là session-based, không có refresh endpoint.**
   - Xóa hoặc deprecate constant refresh khỏi FE config.
   - Xóa/cập nhật docs đang ghi `POST /auth/token/refresh/` và JWT refresh flow.

2. **Chuẩn hóa chatbot health smoke dùng trailing slash.**
   - Mọi smoke qua gateway dùng `GET /chatbot/health/`.
   - Nếu có direct service smoke thì dùng `GET /health/`.

3. **Chặn tình huống lộ internal host khi client hit health path không slash.**
   - Minimal code patch hợp lý nhất: thêm alias không slash cho health trong chatbot service (`/health` và `/chatbot/health`) để không phát sinh `307`.
   - Đây nhỏ hơn và ít rủi ro hơn so với sửa toàn bộ reverse-proxy redirect handling.

### Can-keep

1. **Giữ logout trả `200` khi unauthenticated.**
   - Đây là hành vi idempotent hợp lý và đã được implement nhất quán.

2. **Giữ gateway special-case logout hiện tại.**
   - Không cần ép logout vào auth middleware hay đổi thành `401` khi thiếu session.

3. **Giữ dual health paths hiện tại ở chatbot service (`/health/` và `/chatbot/health/`).**
   - Chỉ cần thêm no-slash alias nếu muốn loại `307` cho smoke/edge proxy.

---

## 7. File Paths Cần Sửa

### Must-fix

- `spotlove-ai/src/services/api/endpoints.ts`
- `backend-microservices/auth-service/README.md`
- `docs/04_FRONTEND_BACKEND_API_OVERVIEW.md`
- `backend-microservices/chatbot-service-fastapi/app/main.py`
- Bất kỳ smoke/spec ngoài repo nào đang gọi `/chatbot/health` không slash; trong repo hiện chưa thấy callsite đó ở `spotlove-ai/e2e/api-endpoints.spec.ts`

### Can-keep

- `backend-microservices/auth-service/users/views.py`
- `backend-microservices/gateway-service-go/internal/handler/auth.go`
- `backend-microservices/gateway-service-go/internal/router/routes.go`

---

## 8. Checklist cho Implementer

- [ ] Remove/deprecate `REFRESH_TOKEN` constant khỏi FE nếu không còn consumer.
- [ ] Cập nhật docs auth flow từ “JWT refresh” sang “gateway session, không có refresh endpoint”.
- [ ] Nếu muốn eliminate `307`, thêm no-slash aliases cho chatbot health trong `app/main.py`.
- [ ] Đảm bảo smoke gateway dùng `/chatbot/health/`.
- [ ] Không đổi contract logout `200` khi unauthenticated.

---

## 9. Nguồn

| # | URL/Path | Mô tả | Version | Date |
| --- | --- | --- | --- | --- |
| 1 | `backend-microservices/auth-service/users/urls.py` | Auth routes thực tế | repo | 2026-03-15 |
| 2 | `backend-microservices/auth-service/users/views.py` | Logout behavior thực tế | repo | 2026-03-15 |
| 3 | `backend-microservices/auth-service/auth_service/urls.py` | Mount auth + health aliases | repo | 2026-03-15 |
| 4 | `backend-microservices/gateway-service-go/internal/router/routes.go` | Gateway health/auth dispatch | repo | 2026-03-15 |
| 5 | `backend-microservices/gateway-service-go/internal/handler/auth.go` | Gateway logout semantics | repo | 2026-03-15 |
| 6 | `backend-microservices/gateway-service-go/internal/handler/proxy.go` | Redirect rewrite behavior | repo | 2026-03-15 |
| 7 | `backend-microservices/gateway-service-go/internal/config/config.go` | `/api` normalize + service mapping | repo | 2026-03-15 |
| 8 | `spotlove-ai/src/services/api/endpoints.ts` | FE stale refresh constant | repo | 2026-03-15 |
| 9 | `spotlove-ai/src/services/api/auth.api.ts` | FE auth callsites thực tế | repo | 2026-03-15 |
| 10 | `spotlove-ai/src/services/api/axios.client.ts` | FE baseURL/interceptor facts | repo | 2026-03-15 |
| 11 | `spotlove-ai/src/store/slices/authSlice.ts` | FE auth flow comments/state | repo | 2026-03-15 |
| 12 | `backend-microservices/chatbot-service-fastapi/app/main.py` | Chatbot health routes | repo | 2026-03-15 |
| 13 | `backend-microservices/chatbot-service-fastapi/app/middleware/gateway_auth.py` | Health exempt paths | repo | 2026-03-15 |
| 14 | `backend-microservices/chatbot-service-fastapi/tests/test_smoke.py` | Canonical service-local health test | repo | 2026-03-15 |
| 15 | `backend-microservices/auth-service/README.md` | Docs stale refresh contract | repo | 2026-03-15 |
| 16 | `docs/04_FRONTEND_BACKEND_API_OVERVIEW.md` | Docs stale JWT refresh flow | repo | 2026-03-15 |
