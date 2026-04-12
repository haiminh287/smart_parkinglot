# Security Audit — Unity Digital Twin Parking Simulator

**Date:** 2026-04-01
**Auditor:** 🛡️ [SECURITY]
**Scope:** 21 C# scripts in `ParkingSimulatorUnity/Assets/Scripts/` (API, Core, Navigation, Parking, Vehicle, IoT, UI, Camera)
**Context:** Development/simulation tool — NOT a production web app. Risk assessed proportionally.

**Risk Level: LOW**
**Deploy Ready: YES** (dev tool — no production deploy concerns)

| Severity    | Count |
| ----------- | ----- |
| 🔴 Critical | 0     |
| 🟠 High     | 0     |
| 🟡 Medium   | 2     |
| 🟢 Low      | 4     |
| ℹ️ Info     | 3     |

---

## Findings

| #   | Severity  | Category               | Finding                                                                                                                                                       | File                                              | Recommendation                                                                                                                                                                                                                |
| --- | --------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- | ----------------------------------------- |
| 1   | 🟡 Medium | Secrets In Source      | Gateway secret hardcoded as ScriptableObject default: `"gateway-internal-secret-key"`. This value is baked into `.asset` files which may be committed to VCS. | `API/ApiConfig.cs:17`                             | Move to env var or `.gitignore` the `.asset` file. For a local simulator this is acceptable but avoid committing the real production secret.                                                                                  |
| 2   | 🟡 Medium | Secrets In Source      | Test credentials hardcoded as defaults: `testEmail = "test@example.com"`, `testPassword = "password"`.                                                        | `API/ApiConfig.cs:20-21`                          | Acceptable for dev tool. Ensure these are NOT real production credentials. Document these as test-only values.                                                                                                                |
| 3   | 🟢 Low    | Transport Security     | All API URLs default to `http://` (not HTTPS) and `ws://` (not WSS).                                                                                          | `API/ApiConfig.cs:10-12`                          | Expected for `localhost` development. For any non-localhost deployment, switch to `https://` and `wss://`. No SSL certificate pinning — acceptable for simulator.                                                             |
| 4   | 🟢 Low    | Logging Sensitive Data | Session cookie partially logged on successful login: `sessionCookie.Substring(0, 20) + "..."`. First 20 chars of session cookie are written to Unity console. | `API/AuthManager.cs:58-60`                        | Truncation mitigates the risk. Consider logging only presence (`"cookie received"`) instead of any cookie content for production builds.                                                                                      |
| 5   | 🟢 Low    | Logging Sensitive Data | Full WebSocket message JSON logged: `Debug.Log($"[ApiService] WS recv: {json}")`. This could include slot/booking data.                                       | `API/ApiService.cs:215`                           | Acceptable in dev. Wrap in `#if UNITY_EDITOR                                                                                                                                                                                  |     | DEBUG_MODE` to prevent in release builds. |
| 6   | 🟢 Low    | Data Exposure          | All API response bodies logged with URL + status code on both success and error paths. Error bodies may contain sensitive details.                            | `API/ApiService.cs:88-101`                        | Debug-appropriate. For release builds, reduce verbosity or conditionally compile out.                                                                                                                                         |
| 7   | ℹ️ Info   | Input Validation       | IMGUI `TextField` inputs (plate numbers, QR data, slot codes, zone IDs) are sent to API without client-side sanitization.                                     | `IoT/ESP32Simulator.cs`, `UI/BookingTestPanel.cs` | N/A risk — server-side validates all inputs. No SQL/command injection possible from Unity client. This is correct architecture (validate server-side).                                                                        |
| 8   | ℹ️ Info   | Mock Credentials       | Mock UUIDs and test data (`MockIds.cs`, `MockDataProvider.cs`) are hardcoded constants.                                                                       | `API/MockIds.cs`, `API/MockDataProvider.cs`       | Test data only — no security concern. These are deterministic UUIDs for simulator use.                                                                                                                                        |
| 9   | ℹ️ Info   | Dependency             | NativeWebSocket pinned to git branch `#upm` (no specific tag/commit). Newtonsoft.Json version 3.2.1 (Unity official package).                                 | `Packages/manifest.json`                          | NativeWebSocket (`endel/NativeWebSocket`) is a well-known, commonly-used Unity WS package. Pin to a specific commit hash for reproducibility if desired. Newtonsoft.Json is Unity's official fork — no known CVEs for v3.2.1. |

---

## Detailed Analysis

### 1. Secrets Management

| Check               | Result | Notes                                                                                                                                                                  |
| ------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hardcoded API keys  | ⚠️     | `gatewaySecret` has a default dev value in `ApiConfig.cs` (ScriptableObject). Value is `"gateway-internal-secret-key"` — clearly a dev placeholder, not a real secret. |
| Hardcoded passwords | ⚠️     | `testEmail`/`testPassword` defaults in `ApiConfig.cs`. Values are obviously test-only.                                                                                 |
| Secrets in logs     | ✅     | Cookie is truncated to 20 chars. Gateway secret is never logged. Passwords are never logged.                                                                           |
| `.env` files        | N/A    | Unity project — no `.env` mechanism. Uses `ScriptableObject` pattern which is standard Unity practice.                                                                 |
| PlayerPrefs storage | ✅     | No `PlayerPrefs` usage found anywhere — no secrets stored in player preferences.                                                                                       |

### 2. Authentication

| Check                      | Result | Notes                                                                                                                                                                                       |
| -------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cookie handling            | ✅     | Session cookie extracted from `Set-Cookie` header, stored in-memory only (not persisted to disk). Split on `;` to get just the session ID — correct behavior.                               |
| X-Gateway-Secret isolation | ✅     | The `ApplyAuth()` method properly separates: AI service calls get `X-Gateway-Secret`, all other calls get session cookie. Never sends both simultaneously. Logic in `AuthManager.cs:85-93`. |
| Credential logging         | ✅     | Neither `email` nor `password` are logged during login. Only login result status is logged.                                                                                                 |
| Logout cleanup             | ✅     | `Logout()` nulls both `sessionCookie` and `currentUser`.                                                                                                                                    |

### 3. Input Validation

| Check                    | Result | Notes                                                                                                                                                          |
| ------------------------ | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| User input sanitization  | ℹ️     | IMGUI TextFields pass raw strings to API. This is correct — server-side validation is the right boundary. No SQL/command injection possible from Unity client. |
| API parameter validation | ✅     | Empty string checks exist for plate numbers, slot codes before API calls (e.g., `ESP32Simulator.DoCheckIn` checks `string.IsNullOrEmpty(checkInPlate)`).       |
| Path traversal           | N/A    | No file system access, no `Resources.Load` with user input.                                                                                                    |

### 4. Data Exposure

| Check                   | Result | Notes                                                                                                                                                                                                                          |
| ----------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| PII in logs             | ✅     | License plates logged (acceptable for parking simulator). No user emails, passwords, or personal data logged.                                                                                                                  |
| PII in debug UI         | ✅     | IMGUI panels show license plates, slot codes, booking IDs — all operational data needed for simulation. No sensitive PII exposed.                                                                                              |
| Error message verbosity | ✅     | Error parsing cascades through multiple response formats (`ApiErrorResponse`, `DjangoErrorResponse`, `GatewayErrorResponse`) and presents user-friendly messages. Raw HTTP bodies only logged to console, not displayed in UI. |

### 5. Transport Security

| Check                  | Result | Notes                                                                                                            |
| ---------------------- | ------ | ---------------------------------------------------------------------------------------------------------------- |
| HTTPS for API calls    | ⚠️     | Defaults to `http://localhost:8000` — acceptable for local dev. ScriptableObject field allows changing to HTTPS. |
| WSS for WebSocket      | ⚠️     | Defaults to `ws://localhost:8006` — acceptable for local dev.                                                    |
| Certificate validation | N/A    | Unity's `UnityWebRequest` uses system cert store by default. No cert pinning (not required for dev tool).        |

### 6. Dependency Security

| Package                                | Source                             | Trust Level    | Notes                                                                                                      |
| -------------------------------------- | ---------------------------------- | -------------- | ---------------------------------------------------------------------------------------------------------- |
| `com.endel.nativewebsocket`            | GitHub (endel/NativeWebSocket#upm) | ✅ Medium-High | ~2.4k stars, widely used Unity WS library. No known CVEs. Pinned to `#upm` branch (not a specific commit). |
| `com.unity.nuget.newtonsoft-json`      | Unity Registry (3.2.1)             | ✅ High        | Official Unity package. Known safe version.                                                                |
| `com.unity.render-pipelines.universal` | Unity Registry (14.0.12)           | ✅ High        | Official URP package.                                                                                      |
| `com.unity.textmeshpro`                | Unity Registry (3.0.7)             | ✅ High        | Official Unity text rendering.                                                                             |

### 7. Unity-Specific Checks

| Check                           | Result | Notes                                                                                                                                                             |
| ------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Resources.Load` exploitation   | ✅     | No `Resources.Load` calls with user-controlled paths.                                                                                                             |
| `PlayerPrefs` sensitive data    | ✅     | Zero `PlayerPrefs` usage in entire codebase.                                                                                                                      |
| Debug vs Release                | ℹ️     | All `Debug.Log` calls are unconditional. In a release build, these would still execute. Consider `#if UNITY_EDITOR` or Logger with log levels.                    |
| Singleton pattern               | ✅     | Multiple singletons (`AuthManager`, `ApiService`, `ParkingManager`, `SharedBookingState`) all use proper `DontDestroyOnLoad` with duplicate instance destruction. |
| Memory cleanup                  | ✅     | `VehicleController.OnDestroy()` nulls event delegates and path references. `ApiService.OnDestroy()` disconnects WebSocket.                                        |
| `Destroy` vs `DestroyImmediate` | ✅     | `ParkingLotGenerator.ClearExisting()` correctly uses `Destroy` in play mode and `DestroyImmediate` in editor mode.                                                |

---

## STRIDE Assessment

| Threat          | Status | Notes                                                                                                                                |
| --------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| Spoofing        | ✅     | Session-based auth via gateway. AI calls use internal secret. Cannot spoof identity without valid cookie or secret.                  |
| Tampering       | ✅     | All mutations go through server APIs which validate. Unity client is not authoritative.                                              |
| Repudiation     | ✅     | All API calls logged with timestamps. Server-side audit trail exists.                                                                |
| Info Disclosure | ⚠️     | Dev-level debug logging includes cookie preview and full WS messages. Acceptable for simulator but should be conditionally compiled. |
| DoS             | ✅     | Polling intervals configurable (`deltaPollInterval = 5s`, `heartbeatInterval = 30s`). No unbounded loops or resource exhaustion.     |
| Elevation       | N/A    | Client is a simulator — no privilege model. Server enforces authorization.                                                           |

---

## OWASP Top 10 Compliance

| Category                      | Status         | Notes                                                                                                                 |
| ----------------------------- | -------------- | --------------------------------------------------------------------------------------------------------------------- |
| A01 Broken Access Control     | ✅ PASS        | Auth properly applied per-request. AI endpoints use separate secret from user endpoints. CORS is server-side concern. |
| A02 Cryptographic Failures    | ✅ PASS        | No client-side crypto. Passwords sent over HTTP to localhost (acceptable for dev). No sensitive data stored at-rest.  |
| A03 Injection                 | ✅ PASS        | No SQL, no command execution, no eval. All user input goes to REST API for server-side validation.                    |
| A04 Insecure Design           | ✅ PASS        | Clear separation: client (Unity) → gateway → microservices. Client not authoritative for any business logic.          |
| A05 Security Misconfiguration | ⚠️ PASS (note) | Default dev credentials in ScriptableObject. Acceptable for development simulator.                                    |
| A06 Vulnerable Components     | ✅ PASS        | NativeWebSocket and Newtonsoft.Json are known-safe versions. All other packages are official Unity packages.          |
| A07 Auth Failures             | ✅ PASS        | Session cookie used correctly. Gateway secret isolated to AI calls. No token/credential storage on disk.              |
| A08 Data Integrity            | ✅ PASS        | `Packages/manifest.json` lockfile exists. Packages sourced from Unity Registry or known GitHub repos.                 |
| A09 Logging Failures          | ⚠️ PASS (note) | Auth events logged. Minor concern: cookie preview in logs. No passwords, tokens, or PII in logs.                      |
| A10 SSRF                      | ✅ PASS        | No user-controlled URLs used for server-side fetches. API URLs are from ScriptableObject config only.                 |

---

## Verdict: **PASS**

| Severity    | Count |
| ----------- | ----- |
| 🔴 Critical | 0     |
| 🟠 High     | 0     |
| 🟡 Medium   | 2     |
| 🟢 Low      | 4     |
| ℹ️ Info     | 3     |

### Summary

This is a **well-structured Unity development/simulation tool** with appropriate security practices for its context:

- **No critical or high vulnerabilities found.**
- The two Medium findings (hardcoded dev secret and test credentials in `ApiConfig.cs`) are proportionally LOW risk for a local developer tool, but are flagged as Medium because they could become issues if the ScriptableObject asset is committed with production values.
- Authentication is correctly implemented with cookie-based session auth for user APIs and internal secret for AI service APIs.
- No `PlayerPrefs` abuse, no `Resources.Load` with user input, no disk-persisted secrets.
- Debug logging is verbose (expected for a simulator) — recommend conditional compilation for any release distribution.

### Recommended Actions (Non-Blocking)

1. Add `ApiConfig.asset` to `.gitignore` or document that production values should never be set in the default asset.
2. Pin `NativeWebSocket` to a specific commit hash in `manifest.json` for reproducibility.
3. Wrap verbose `Debug.Log` statements in `#if UNITY_EDITOR || DEBUG` for release builds.
4. Consider masking the cookie preview in `AuthManager.cs` login log — replace with `"cookie received"`.
