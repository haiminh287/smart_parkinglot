# Runtime verification after 403-login patch

Timestamp: 2026-03-15T18:57:54.8900081+07:00

| Base | Method | Endpoint | Status | Content-Type | Body preview |
|---|---|---|---:|---|---|
| http://localhost:8080 | GET | /api/health | 200 | application/json; charset=utf-8 | {"service":"gateway-service","status":"healthy","version":"1.0.0"} |
| http://localhost:8080 | POST | /api/auth/login/ | 400 | application/json | {"nonFieldErrors":["Invalid email or password"]} |
| http://localhost:8080 | GET | /api/auth/me/ | 403 | application/json | {"detail":"Authentication credentials were not provided."} |
| http://localhost:8080 | POST | /api/auth/refresh/ | 404 | text/html; charset=utf-8 |  <!doctype html> <html lang="en"> <head>   <title>Not Found</title> </head> <body>   <h1>Not Found</h1><p>The requested resource was not found on this server.</... |
| http://localhost:8080 | POST | /api/auth/logout/ | 200 | application/json; charset=utf-8 | {"message":"Logged out successfully"} |
| http://localhost:8080 | GET | /api/bookings/ | 401 | application/json; charset=utf-8 | {"detail":"Authentication credentials were not provided."} |
| http://localhost:8080 | GET | /api/parking/health/ | 200 | application/json | {"status": "ok", "service": "parking-service"} |
| http://localhost:8080 | GET | /api/chatbot/health | -1 | request-error | No such host is known. (chatbot-service-fastapi:8008) |
| http://localhost:8000 | GET | /api/health | 200 | application/json; charset=utf-8 | {"service":"gateway-service","status":"healthy","version":"1.0.0"} |
| http://localhost:8000 | POST | /api/auth/login/ | 400 | application/json | {"nonFieldErrors":["Invalid email or password"]} |

## Raw JSON

```json
[
  {
    "BaseUrl": "http://localhost:8080",
    "Method": "GET",
    "Endpoint": "/api/health",
    "Status": 200,
    "ContentType": [
      "application/json; charset=utf-8"
    ],
    "BodyPreview": "{\"service\":\"gateway-service\",\"status\":\"healthy\",\"version\":\"1.0.0\"}"
  },
  {
    "BaseUrl": "http://localhost:8080",
    "Method": "POST",
    "Endpoint": "/api/auth/login/",
    "Status": 400,
    "ContentType": [
      "application/json"
    ],
    "BodyPreview": "{\"nonFieldErrors\":[\"Invalid email or password\"]}"
  },
  {
    "BaseUrl": "http://localhost:8080",
    "Method": "GET",
    "Endpoint": "/api/auth/me/",
    "Status": 403,
    "ContentType": [
      "application/json"
    ],
    "BodyPreview": "{\"detail\":\"Authentication credentials were not provided.\"}"
  },
  {
    "BaseUrl": "http://localhost:8080",
    "Method": "POST",
    "Endpoint": "/api/auth/refresh/",
    "Status": 404,
    "ContentType": [
      "text/html; charset=utf-8"
    ],
    "BodyPreview": " <!doctype html> <html lang=\"en\"> <head>   <title>Not Found</title> </head> <body>   <h1>Not Found</h1><p>The requested resource was not found on this server.</..."
  },
  {
    "BaseUrl": "http://localhost:8080",
    "Method": "POST",
    "Endpoint": "/api/auth/logout/",
    "Status": 200,
    "ContentType": [
      "application/json; charset=utf-8"
    ],
    "BodyPreview": "{\"message\":\"Logged out successfully\"}"
  },
  {
    "BaseUrl": "http://localhost:8080",
    "Method": "GET",
    "Endpoint": "/api/bookings/",
    "Status": 401,
    "ContentType": [
      "application/json; charset=utf-8"
    ],
    "BodyPreview": "{\"detail\":\"Authentication credentials were not provided.\"}"
  },
  {
    "BaseUrl": "http://localhost:8080",
    "Method": "GET",
    "Endpoint": "/api/parking/health/",
    "Status": 200,
    "ContentType": [
      "application/json"
    ],
    "BodyPreview": "{\"status\": \"ok\", \"service\": \"parking-service\"}"
  },
  {
    "BaseUrl": "http://localhost:8080",
    "Method": "GET",
    "Endpoint": "/api/chatbot/health",
    "Status": -1,
    "ContentType": "request-error",
    "BodyPreview": "No such host is known. (chatbot-service-fastapi:8008)"
  },
  {
    "BaseUrl": "http://localhost:8000",
    "Method": "GET",
    "Endpoint": "/api/health",
    "Status": 200,
    "ContentType": [
      "application/json; charset=utf-8"
    ],
    "BodyPreview": "{\"service\":\"gateway-service\",\"status\":\"healthy\",\"version\":\"1.0.0\"}"
  },
  {
    "BaseUrl": "http://localhost:8000",
    "Method": "POST",
    "Endpoint": "/api/auth/login/",
    "Status": 400,
    "ContentType": [
      "application/json"
    ],
    "BodyPreview": "{\"nonFieldErrors\":[\"Invalid email or password\"]}"
  }
]
```

## Manual recheck for chatbot health path behavior

- GET /api/chatbot/health -> 307 Temporary Redirect, Location: http://chatbot-service-fastapi:8008/chatbot/health/
- GET /api/chatbot/health/ -> 200 OK, Content-Type: application/json, body: {"status":"healthy","service":"chatbot-service","version":"3.0.0"}
