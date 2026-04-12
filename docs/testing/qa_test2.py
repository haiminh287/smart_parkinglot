import urllib.request
import urllib.error
import json
import socket
import ssl
import hashlib
import base64
import os

BASE = "https://parksmart.ghepdoicaulong.shop"
UA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Accept": "application/json, text/html, */*"
}

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
        all_headers = dict(resp.headers)
        body_text = resp.read().decode(errors="replace")
        return code, all_headers, body_text
    except urllib.error.HTTPError as e:
        all_headers = dict(e.headers)
        try:
            body_text = e.read().decode(errors="replace")
        except Exception:
            body_text = ""
        return e.code, all_headers, body_text
    except Exception as ex:
        return 0, {}, str(ex)

# ============================================================
# CORS Deep Dive
# ============================================================
print("=== CORS Deep Analysis ===")
code, hdrs, body = req("OPTIONS", "/api/auth/login/", extra_headers={
    "Origin": "https://parksmart.ghepdoicaulong.shop",
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "Content-Type, Authorization"
})
print(f"Status: {code}")
print(f"All response headers related to CORS:")
for k, v in hdrs.items():
    if "access-control" in k.lower() or "cors" in k.lower() or "origin" in k.lower() or "vary" in k.lower():
        print(f"  {k}: {v}")
print(f"Body snippet: {body[:200]}")

print("\n--- CORS with different Origin ---")
code2, hdrs2, body2 = req("OPTIONS", "/api/auth/login/", extra_headers={
    "Origin": "https://other-site.com",
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "Content-Type"
})
print(f"Status: {code2}")
for k, v in hdrs2.items():
    if "access-control" in k.lower() or "vary" in k.lower():
        print(f"  {k}: {v}")

# Test if Cloudflare strips CORS headers
print("\n--- Check /api/health CORS headers ---")
code3, hdrs3, body3 = req("OPTIONS", "/api/health", extra_headers={
    "Origin": "https://parksmart.ghepdoicaulong.shop",
    "Access-Control-Request-Method": "GET"
})
print(f"Status: {code3}")
for k, v in hdrs3.items():
    if "access-control" in k.lower() or "vary" in k.lower():
        print(f"  {k}: {v}")

# Also check GET /api/health CORS
code4, hdrs4, body4 = req("GET", "/api/health", extra_headers={
    "Origin": "https://parksmart.ghepdoicaulong.shop"
})
print(f"\n--- GET /api/health with Origin header ---")
print(f"Status: {code4}")
for k, v in hdrs4.items():
    if "access-control" in k.lower() or "vary" in k.lower():
        print(f"  {k}: {v}")

# ============================================================
# GROUP 6: WebSocket Check
# ============================================================
print("\n=== GROUP 6: WebSocket Check ===")

WS_PATHS = [
    "/ws/parking",
    "/ws/parking/",
    "/ws/",
    "/ws",
]

def ws_handshake(host, path):
    """Attempt a basic WebSocket handshake over TLS."""
    try:
        context = ssl.create_default_context()
        sock = socket.create_connection((host, 443), timeout=10)
        tls_sock = context.wrap_socket(sock, server_hostname=host)
        
        key = base64.b64encode(os.urandom(16)).decode()
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"Origin: https://{host}\r\n"
            f"User-Agent: Mozilla/5.0\r\n"
            f"\r\n"
        )
        tls_sock.sendall(handshake.encode())
        response = b""
        tls_sock.settimeout(5)
        try:
            while True:
                chunk = tls_sock.recv(1024)
                if not chunk:
                    break
                response += chunk
                if b"\r\n\r\n" in response:
                    break
        except socket.timeout:
            pass
        tls_sock.close()
        resp_text = response.decode(errors="replace")
        first_line = resp_text.split("\r\n")[0] if resp_text else "(empty)"
        return first_line, resp_text[:300]
    except Exception as ex:
        return f"ERR: {ex}", ""

host = "parksmart.ghepdoicaulong.shop"
for path in WS_PATHS:
    first_line, full = ws_handshake(host, path)
    print(f"  WS {path} -> {first_line}")
    if "101" in first_line:
        print(f"  [PASS] WebSocket upgraded successfully")
    elif "ERR" in first_line:
        print(f"  [INFO] Connection error: {first_line}")
    else:
        # show status code
        code_ws = first_line.split(" ")[1] if len(first_line.split(" ")) > 1 else "?"
        print(f"  [INFO] HTTP {code_ws} — WS not available on this path")

# ============================================================
# DETAILED BODY INSPECTION (FE HTML)
# ============================================================
print("\n=== FE HTML Body Detail ===")
code, hdrs, body = req("GET", "/")
print(f"Status: {code}")
has_root = '<div id="root">' in body
has_script = '<script' in body.lower()
has_vite = 'vite' in body.lower() or 'assets/' in body.lower()
print(f"  has <div id='root'>: {has_root}")
print(f"  has <script: {has_script}")
print(f"  has vite/assets: {has_vite}")
print(f"  body snippet:\n{body[:400]}")

# ============================================================
# EXTRA: Check 307 redirect behavior
# ============================================================
print("\n=== Redirect Check (no-redirect) ===")
import http.client

def check_no_redirect(path):
    conn = http.client.HTTPSConnection("parksmart.ghepdoicaulong.shop", timeout=10)
    conn.request("GET", path, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, */*"
    })
    resp = conn.getresponse()
    loc = resp.getheader("Location", "")
    ct = resp.getheader("Content-Type", "")
    print(f"  GET {path} -> {resp.status} | Location:{loc!r} | CT:{ct}")
    conn.close()

check_no_redirect("/api/chatbot/health")
check_no_redirect("/api/chatbot/health/")
check_no_redirect("/api/parking/health")
check_no_redirect("/api/parking/health/")
