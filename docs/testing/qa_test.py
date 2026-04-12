import urllib.request
import urllib.error
import json
import sys

BASE = "https://parksmart.ghepdoicaulong.shop"
UA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept": "application/json, text/html, */*"
}

results = []

def req(method, path, body=None, extra_headers=None):
    if extra_headers is None:
        extra_headers = {}
    url = BASE + path
    data = body.encode() if body else None
    headers = {**UA_HEADERS, **extra_headers}
    if body:
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=15)
        code = resp.status
        ct = resp.headers.get("Content-Type", "")
        cors_origin = resp.headers.get("Access-Control-Allow-Origin", "")
        body_text = resp.read().decode(errors="replace")
        return code, ct, body_text, cors_origin
    except urllib.error.HTTPError as e:
        ct = e.headers.get("Content-Type", "")
        cors_origin = e.headers.get("Access-Control-Allow-Origin", "")
        try:
            body_text = e.read().decode(errors="replace")
        except Exception:
            body_text = ""
        return e.code, ct, body_text, cors_origin
    except Exception as ex:
        return 0, "", str(ex), ""

def check(label, code, ct, body, cors, exp_code=None, exp_codes=None, must_json=True, must_contain=None, must_not_html=True, must_cors=False):
    failures = []
    if exp_code and code != exp_code:
        failures.append(f"status={code} expected {exp_code}")
    if exp_codes and code not in exp_codes:
        failures.append(f"status={code} expected one of {exp_codes}")
    if must_json and "json" not in ct.lower():
        failures.append(f"CT not JSON: {ct!r}")
    if must_not_html and "text/html" in ct.lower():
        failures.append(f"CT is HTML (not allowed): {ct!r}")
    if must_contain and must_contain not in body:
        failures.append(f"body missing {must_contain!r}")
    if must_cors and not cors:
        failures.append("Missing Access-Control-Allow-Origin header")
    verdict = "PASS" if not failures else "FAIL"
    results.append((verdict, label, code, ct[:40], body[:150], failures))
    return verdict

# ============================================================
# GROUP 1: Infrastructure Smoke
# ============================================================
print("\n=== GROUP 1: Infrastructure Smoke ===")

code, ct, body, cors = req("GET", "/")
check("GET /", code, ct, body, cors, exp_code=200, must_json=False, must_not_html=False)

code, ct, body, cors = req("GET", "/nginx-health")
check("GET /nginx-health", code, ct, body, cors, exp_code=200, must_json=False, must_not_html=False)

code, ct, body, cors = req("GET", "/api/health")
check("GET /api/health", code, ct, body, cors, exp_code=200, must_json=True)

code, ct, body, cors = req("GET", "/api/chatbot/health")
check("GET /api/chatbot/health", code, ct, body, cors, exp_code=200, must_json=True)

code, ct, body, cors = req("GET", "/api/chatbot/health/")
v = "PASS" if code == 200 and "json" in ct.lower() else "FAIL"
failures = []
if code != 200: failures.append(f"status={code} expected 200")
if "json" not in ct.lower(): failures.append(f"CT not JSON: {ct!r}")
results.append((v, "GET /api/chatbot/health/ (no 307)", code, ct[:40], body[:150], failures))

code, ct, body, cors = req("GET", "/api/parking/health/")
check("GET /api/parking/health/", code, ct, body, cors, exp_code=200, must_json=True)

# ============================================================
# GROUP 2: Auth API Contract
# ============================================================
print("=== GROUP 2: Auth API Contract ===")

# 2a: invalid creds -> 400/401 JSON (not 403/HTML)
code, ct, body, cors = req("POST", "/api/auth/login/", json.dumps({"username": "bad_user_qa", "password": "bad_pass_qa"}))
v = "PASS" if code in (400, 401) and "json" in ct.lower() else "FAIL"
failures = []
if code not in (400, 401): failures.append(f"status={code} expected 400 or 401")
if "json" not in ct.lower(): failures.append(f"CT not JSON: {ct!r}")
results.append((v, "POST /api/auth/login/ (invalid creds)", code, ct[:40], body[:150], failures))

# 2b: GET /api/auth/me/ unauthenticated -> 401/403 JSON
code, ct, body, cors = req("GET", "/api/auth/me/")
check("GET /api/auth/me/ (no auth)", code, ct, body, cors, exp_codes=[401, 403], must_json=True)

# 2c: POST /api/auth/logout/ -> 200/204 JSON (idempotent)
code, ct, body, cors = req("POST", "/api/auth/logout/")
v = "PASS" if code in (200, 204) else "FAIL"
failures = []
if code not in (200, 204): failures.append(f"status={code} expected 200 or 204")
results.append((v, "POST /api/auth/logout/ (idempotent)", code, ct[:40], body[:150], failures))

# 2d: POST /api/auth/refresh/ -> 404 JSON with ERR_NOT_FOUND
code, ct, body, cors = req("POST", "/api/auth/refresh/")
failures = []
if code != 404: failures.append(f"status={code} expected 404")
if "json" not in ct.lower(): failures.append(f"CT not JSON: {ct!r}")
if "ERR_NOT_FOUND" not in body: failures.append("body missing ERR_NOT_FOUND")
v = "PASS" if not failures else "FAIL"
results.append((v, "POST /api/auth/refresh/ (ERR_NOT_FOUND)", code, ct[:40], body[:150], failures))

# 2e: OPTIONS /api/auth/login/ preflight CORS
code, ct, body, cors = req("OPTIONS", "/api/auth/login/", extra_headers={
    "Origin": "https://parksmart.ghepdoicaulong.shop",
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "Content-Type"
})
v = "PASS" if code in (200, 204) and cors else "FAIL"
failures = []
if code not in (200, 204): failures.append(f"status={code} expected 200/204")
if not cors: failures.append("Missing ACAO header")
results.append((v, "OPTIONS /api/auth/login/ (CORS preflight)", code, ct[:40], body[:150], failures))
print(f"  CORS header value: {cors!r}")

# ============================================================
# GROUP 3: Domain Endpoints (unauthorized)
# ============================================================
print("=== GROUP 3: Domain Endpoints (unauthorized) ===")

code, ct, body, cors = req("GET", "/api/bookings/")
check("GET /api/bookings/ (no auth)", code, ct, body, cors, exp_code=401, must_json=True)

code, ct, body, cors = req("GET", "/api/vehicles/")
check("GET /api/vehicles/ (no auth)", code, ct, body, cors, exp_code=401, must_json=True)

code, ct, body, cors = req("GET", "/api/parking/")
v = "PASS" if code in (200, 401) and "json" in ct.lower() else "FAIL"
failures = []
if code not in (200, 401): failures.append(f"status={code} expected 200 or 401")
if "json" not in ct.lower(): failures.append(f"CT not JSON (should never be HTML): {ct!r}")
results.append((v, "GET /api/parking/ (no HTML)", code, ct[:40], body[:150], failures))

code, ct, body, cors = req("GET", "/api/notifications/")
check("GET /api/notifications/ (no auth)", code, ct, body, cors, exp_code=401, must_json=True)

# ============================================================
# GROUP 4: Guard Test (no SPA fallback)
# ============================================================
print("=== GROUP 4: Guard Test (no SPA fallback) ===")

code, ct, body, cors = req("GET", "/auth/me")
failures = []
if code != 404: failures.append(f"status={code} expected 404")
if "json" not in ct.lower(): failures.append(f"CT not JSON: {ct!r}")
v = "PASS" if not failures else "FAIL"
results.append((v, "GET /auth/me (guard, no SPA)", code, ct[:40], body[:150], failures))

code, ct, body, cors = req("GET", "/bookings/")
failures = []
if code != 404: failures.append(f"status={code} expected 404")
if "json" not in ct.lower(): failures.append(f"CT not JSON: {ct!r}")
v = "PASS" if not failures else "FAIL"
results.append((v, "GET /bookings/ (guard, no SPA)", code, ct[:40], body[:150], failures))

# ============================================================
# GROUP 5: FE Render Check
# ============================================================
print("=== GROUP 5: FE Render Check ===")

code, ct, body, cors = req("GET", "/")
failures = []
if code != 200: failures.append(f"status={code} expected 200")
valid_html = '<div id="root">' in body or 'script' in body.lower()
if not valid_html: failures.append("HTML missing <div id='root'> or script tag")
v = "PASS" if not failures else "FAIL"
results.append((v, "GET / (valid SPA HTML)", code, ct[:40], body[:200], failures))

# chatbot health no-307 already tested in group 1

# ============================================================
# PRINT RESULTS
# ============================================================
print("\n" + "="*90)
print(f"{'VERDICT':<6} {'TEST LABEL':<50} {'STATUS':<7} {'CONTENT-TYPE':<40}")
print("="*90)
pass_count = 0
fail_count = 0
for (v, label, code, ct, body, failures) in results:
    tag = f"[{v}]"
    print(f"{tag:<7} {label:<50} {code:<7} {ct:<40}")
    if failures:
        for f in failures:
            print(f"        !! {f}")
        print(f"        >> {body[:120]!r}")
    if v == "PASS":
        pass_count += 1
    else:
        fail_count += 1

print("="*90)
print(f"TOTAL: {pass_count+fail_count} | PASS: {pass_count} | FAIL: {fail_count}")
if fail_count == 0:
    print("OVERALL VERDICT: PASS")
else:
    print("OVERALL VERDICT: FAIL")
