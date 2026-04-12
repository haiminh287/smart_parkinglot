# Code Review Report — DEPLOY-PARKSMART-2026-03-24

**Score: 4.0/10** | **Verdict: Request Changes**  
**Date:** 2026-03-24 | **Files reviewed: 5** (+ 2 context files: config.go, auth.go)

---

## Summary

|                  | Count          |
| ---------------- | -------------- |
| 🚨 Critical      | 0 in-scope (1 ancillary) |
| ⚠️ Major         | 3              |
| 💡 Minor         | 8              |
| 🗑️ Dead Code     | 2 items        |
| 🏗️ Arch Drift    | 0 violations   |

**Auto Request Changes triggered**: ≥ 2 Major issues  
Score formula: 8.0 − 3×1.0 (Major) − 2×0.5 (8 Minor ÷ 3 = 2 groups) = **4.0**

---

## ⚠️ Major Issues (PHẢI fix trước deploy)

### [MAJ-1] Nginx `add_header` inheritance bug — security headers bị strip khỏi static assets

- **File:** [infra/nginx/nginx.conf](../../infra/nginx/nginx.conf#L56-L73)
- **Category:** Security misconfiguration
- **Problem:** Theo đặc tả Nginx, khi một `location` block có BẤT KỲ directive `add_header` nào, toàn bộ `add_header` từ `server` block cha **KHÔNG** được kế thừa. Location `~* \.(js|css|woff2?|...)$` hiện có `add_header Cache-Control "public, immutable"` — điều này khiến **tất cả** security headers (HSTS, X-Content-Type-Options, X-Frame-Options, CSP, Referrer-Policy, Permissions-Policy) **KHÔNG được gửi** cho bất kỳ response nào là static asset.
- **Impact:** HSTS bị vắng mặt trên JS/CSS/font requests; `X-Content-Type-Options: nosniff` không được áp dụng cho static files, mở cửa MIME-sniffing attacks; Scanner (MozObservatory, SecurityHeaders.com) sẽ fail nếu scan static asset URL.
- **Fix:**
  ```nginx
  location ~* \.(js|css|woff2?|ttf|eot|ico|png|jpg|jpeg|gif|svg|webp|avif)$ {
      expires 1y;
      # Lặp lại security headers vì Nginx không kế thừa add_header từ server block
      add_header Cache-Control           "public, immutable";
      add_header X-Content-Type-Options  "nosniff"              always;
      add_header X-Frame-Options         "SAMEORIGIN"           always;
      add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
      # Bỏ CSP phức tạp ở đây nếu static assets không render HTML — OK để omit CSP
      access_log off;
  }
  ```
  Hoặc giải pháp sạch hơn: dùng `include snippets/security-headers.conf` snippet được include vào mọi location block có `add_header`.

---

### [MAJ-2] CSP `'unsafe-inline'` trong script-src và style-src — vô hiệu hoá bảo vệ XSS

- **File:** [infra/nginx/nginx.conf](../../infra/nginx/nginx.conf#L57)
- **Category:** Security — CSP bypass
- **Problem:** `script-src 'self' 'unsafe-inline'` cho phép thực thi bất kỳ inline script nào được inject bởi XSS. Directive CSP hoàn toàn vô nghĩa với mức này — kẻ tấn công có thể inject `<script>alert(1)</script>` mà không bị block. Tương tự `style-src 'unsafe-inline'` cho phép CSS injection.
- **Impact:** XSS protection của CSP bị bypass hoàn toàn. Vite production build **không cần** `'unsafe-inline'` cho scripts (bundle output là external `.js` files). Có thể xoá ngay.
- **Fix:**
  ```nginx
  # Thay: "script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
  # Bằng (Vite build không cần unsafe-inline):
  Content-Security-Policy "default-src 'self';
    connect-src 'self' https://api.ghepdoicaulong.shop wss://ws.ghepdoicaulong.shop;
    script-src 'self';
    style-src 'self' 'unsafe-inline';
    img-src 'self' data: blob:;
    font-src 'self' data:;
    object-src 'none';
    base-uri 'self';
    form-action 'self';"
  ```
  Ghi chú: `style-src 'unsafe-inline'` có thể cần giữ nếu dùng CSS-in-JS (emotion/styled-components). Cần test production build để xác nhận. Nếu không cần, xoá luôn.

---

### [MAJ-3] `proxy.go` — Không có transport timeout trên `httputil.NewSingleHostReverseProxy`

- **File:** [backend-microservices/gateway-service-go/internal/handler/proxy.go](../../backend-microservices/gateway-service-go/internal/handler/proxy.go#L51-L52)
- **Category:** Performance / Reliability — goroutine leak, DoS amplification
- **Problem:** `httputil.NewSingleHostReverseProxy(targetURL)` mặc định dùng `http.DefaultTransport` với **không có** `ResponseHeaderTimeout`. Nếu bất kỳ backend service (parking, booking, AI...) bị chậm hoặc hang, goroutine proxy sẽ bị block vô hạn. Dưới load, điều này cascade thành gateway outage tổng thể.
- **Impact:** Một slow backend → hàng trăm goroutine bị leak → gateway OOM hoặc connection exhausted → DoS condition.
- **Fix:**
  ```go
  // Sau: proxy := httputil.NewSingleHostReverseProxy(targetURL)
  // Thêm:
  proxy.Transport = &http.Transport{
      DialContext: (&net.Dialer{
          Timeout:   10 * time.Second,
          KeepAlive: 30 * time.Second,
      }).DialContext,
      ResponseHeaderTimeout: 60 * time.Second,
      TLSHandshakeTimeout:   10 * time.Second,
      IdleConnTimeout:       90 * time.Second,
      MaxIdleConnsPerHost:   32,
  }
  // Import thêm: "net" và "time"
  ```

---

## 🚨 Ancillary Critical (config.go — context của proxy.go)

### [CRIT-ANC-1] `GATEWAY_SECRET` hardcoded default, không có production validation

- **File:** [backend-microservices/gateway-service-go/internal/config/config.go](../../backend-microservices/gateway-service-go/internal/config/config.go#L44)
- **Category:** Security — Authentication bypass
- **Problem:** `GatewaySecret: strings.TrimSpace(getEnv("GATEWAY_SECRET", "gateway-internal-secret-key"))`. Nếu `GATEWAY_SECRET` env var không được set, secret mặc định là `"gateway-internal-secret-key"` — một giá trị **lộ trong source code**. Hàm `Validate()` kiểm tra SessionCookieDomain, SessionCookieSecure, và CORS trong production, nhưng **không kiểm tra** GatewaySecret khác default. Backend services tin tưởng header `X-Gateway-Secret` để xác định request đến từ gateway — anyone với source access có thể forge header này.
- **Fix** (trong `config.go` - ngoài scope nhưng phải track):
  ```go
  // Trong Validate(), sau block kiểm tra production:
  if strings.EqualFold(c.Environment, "production") {
      // ... existing checks ...
      if c.GatewaySecret == "gateway-internal-secret-key" ||
         strings.TrimSpace(c.GatewaySecret) == "" {
          return fmt.Errorf("GATEWAY_SECRET must be set to a non-default value in production")
      }
  }
  ```

---

## 💡 Minor Issues

- **[MIN-1]** [infra/cloudflare/cloudflared/config-parksmart.yml](../../infra/cloudflare/cloudflared/config-parksmart.yml#L8-L9) — Hardcoded Windows absolute path (`C:\Users\MINH\.cloudflared\...`) cho `credentials-file` và `logfile`. Non-portable cho CI/Linux deployment. Cân nhắc dùng relative path hoặc env var substitution. (Pattern consistent với `config.yml` nhưng nên fix cả hai.)

- **[MIN-2]** [infra/nginx/nginx.conf](../../infra/nginx/nginx.conf#L57) — CSP thiếu `object-src 'none'` (ngăn plugin/Flash execution) và `base-uri 'self'` (ngăn `<base>` tag injection). Cả hai là best practice cần thêm.

- **[MIN-3]** [infra/nginx/nginx.conf](../../infra/nginx/nginx.conf#L47) — `X-XSS-Protection: "1; mode=block"` là deprecated. Chrome/Firefox đã bỏ support từ lâu; IE/Edge Legacy có thể bị affected xấu. Nên replace bằng `add_header X-XSS-Protection "0" always;` (disabled, để CSP xử lý) hoặc xoá hoàn toàn.

- **[MIN-4]** [infra/nginx/nginx.conf](../../infra/nginx/nginx.conf#L52) — HSTS (`Strict-Transport-Security`) được set trong server block lắng nghe port 80 (HTTP). Theo HTTP spec, browser bỏ qua HSTS nhận qua plain HTTP. Works in practice vì Cloudflare forward header qua HTTPS edge → browser, nhưng semantically sai và misleading cho maintainer.

- **[MIN-5]** [backend-microservices/gateway-service-go/internal/handler/proxy.go](../../backend-microservices/gateway-service-go/internal/handler/proxy.go#L82) — String concatenation để build JSON error response:
  ```go
  // Fragile — if route.Name ever has special chars, produces invalid JSON
  io.WriteString(w, `{"error":"Service unavailable","service":"`+route.Name+`"}`)
  // Nên dùng:
  resp, _ := json.Marshal(map[string]string{"error": "Service unavailable", "service": route.Name})
  w.Write(resp)
  ```

- **[MIN-6]** [backend-microservices/gateway-service-go/internal/middleware/cors.go](../../backend-microservices/gateway-service-go/internal/middleware/cors.go#L42) — `AllowHeaders` thiếu `X-CSRF-Token`. Nếu CSRF middleware được thêm sau này, sẽ bị CORS preflight reject. Cân nhắc thêm phòng ngừa.

- **[MIN-7]** [infra/cloudflare/cloudflared/config-parksmart.yml](../../infra/cloudflare/cloudflared/config-parksmart.yml#L19-L22) — `originRequest` thiếu các settings production-ready: `tcpKeepAlive: 30s`, `keepAliveConnections: 10`, `idleConnTimeout: 90s`. Nếu nginx bị restart, tunnel sẽ không reconnect gracefully. Compare với cách config.yml xử lý.

- **[MIN-8]** [infra/nginx/nginx.conf](../../infra/nginx/nginx.conf#L57) — CSP `connect-src` bao gồm `https://parksmart.ghepdoicaulong.shop` — đây là redundant vì requests từ `parksmart.ghepdoicaulong.shop` đến chính nó đã được cover bởi `'self'`. Gây confusion khi đọc CSP và tăng attack surface nếu `parksmart` bị compromise.

---

## 🗑️ Dead Code Found

| File | Location | Type | Action |
|---|---|---|---|
| [handler/proxy.go](../../backend-microservices/gateway-service-go/internal/handler/proxy.go#L94-L99) | `HandleMultipartProxy()` L94-99 | Unused function — chỉ là wrapper gọi `HandleProxy(c)`, không register trong `routes.go` | Remove function |
| [middleware/auth.go](../../backend-microservices/gateway-service-go/internal/middleware/auth.go#L70-L83) | `isPublicEndpoint()` L70-83 | Defined but never called — auth middleware dùng `route.Public` từ config thay vì gọi function này | Remove function |

**Total: 2 items → Cleanup task needed: yes**

---

## 🏗️ Architecture Compliance

- ✅ ADR: Không có ADR conflicts phát hiện
- ✅ Cloudflare Tunnel pattern: `config-parksmart.yml` consistent với `config.yml` reference
- ✅ CORS production-only dev origins: Đúng — `buildAllowedOrigins` strip localhost khi `ENV=production`
- ✅ Session auth validation: AuthMiddleware properly checks Redis session trước khi proxy
- ✅ Nginx layer separation: FE serve + API proxy + WS proxy tách bạch rõ ràng
- ✅ Guard rules: `location ~ ^/(auth|bookings|...)` guard hoạt động đúng
- ⚠️ GATEWAY_SECRET production validation: Missing (xem CRIT-ANC-1)

---

## ✨ Positive Highlights

- **cors.go**: `buildAllowedOrigins()` có deduplication logic tốt với `seen` map; production check `strings.EqualFold` case-insensitive là đúng.
- **nginx.conf**: Guard rules cho backend-like paths (`/auth/`, `/bookings/`, v.v.) trả JSON error thay vì SPA fallback — rất tốt, ngăn FE nhầm gọi sai prefix.
- **proxy.go**: `ModifyResponse` redirect rewriting (`/auth/callback` → `/api/auth/callback`) — edge case được handle chủ động, ngăn redirect loop vào SPA.
- **config-parksmart.yml**: Comment header rõ ràng với HƯỚNG DẪN CHẠY cụ thể, có fallback `http_status:404` cuối ingress list.
- **config.go Validate()**: Production validation cho cookie domain, HTTPS CORS origins, và callback URL là best practice tốt — chỉ thiếu `GatewaySecret` check.
- **nginx.conf WebSocket proxy**: `proxy_read_timeout 3600s` và `Upgrade`/`Connection` headers đúng spec.
- **nginx.conf Gzip**: Config hợp lý với `gzip_min_length 1024`, đúng MIME types, `gzip_vary on`.

---

## 📋 Action Items (ordered by priority)

1. **[MAJ-2]** Xoá `'unsafe-inline'` khỏi `script-src` CSP trong nginx.conf — test Vite production build xem có cần không (rất likely không cần)
2. **[MAJ-1]** Fix `add_header` inheritance: lặp lại critical security headers (`X-Content-Type-Options`, `Strict-Transport-Security`) trong static assets location block
3. **[MAJ-3]** Thêm `http.Transport` với `ResponseHeaderTimeout: 60s` vào proxy.go `HandleProxy`
4. **[CRIT-ANC-1]** Thêm production validation cho `GATEWAY_SECRET` != default trong `config.go Validate()`
5. **[Dead code]** Remove: `HandleMultipartProxy()` trong proxy.go + `isPublicEndpoint()` trong auth.go
6. **[MIN-2]** Thêm `object-src 'none'; base-uri 'self'; form-action 'self'` vào CSP
7. **[MIN-3]** Replace `X-XSS-Protection: "1; mode=block"` → `X-XSS-Protection: "0"`
8. **(Optional)** [MIN-1] Document `credentials-file` path pattern trong README/runbook để maintainers biết cần update
9. **(Optional)** [MIN-7] Thêm `tcpKeepAlive`, `keepAliveConnections` vào `config-parksmart.yml` originRequest
