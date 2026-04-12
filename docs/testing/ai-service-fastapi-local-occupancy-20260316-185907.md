# AI Service Local Occupancy Validation

- Timestamp: 2026-03-16 18:59:07
- Workspace: C:/Users/MINH/Documents/Zalo_Received_Files/Project_Main
- Service: backend-microservices/ai-service-fastapi

## 1) Service Restart (Local Python/Uvicorn)

- Existing listener on port 8009 before restart: none
- Existing ai-service uvicorn process before restart: none
- Started process PID: 510672
- Active listener after startup:
  - PID: 513576
  - Port: 8009
- Health check:
  - URL: http://localhost:8009/health/
  - HTTP: 200
  - Body: {"status":"healthy","service":"ai-service","version":"1.0.0"}

## 2) POST /ai/parking/detect-occupancy/

- URL: http://localhost:8009/ai/parking/detect-occupancy/
- Method: POST
- Auth header: X-Gateway-Secret (configured runtime gateway secret)
- Content-Type: multipart/form-data
- Payload summary:
  - image: backend-microservices/ai-service-fastapi/test_annotated.jpg
  - camera_id: cam-local-01
  - slots JSON:
    [{"slot_id":"slot-1","slot_code":"A1","zone_id":"z1","x1":0,"y1":0,"x2":640,"y2":640}]

## 3) Response

- HTTP status code: 200
- Response body:
  {"cameraId":"cam-local-01","totalSlots":1,"totalAvailable":1,"totalOccupied":0,"detectionMethod":"yolo11n","processingTimeMs":517.5,"slots":[{"slotId":"slot-1","slotCode":"A1","zoneId":"z1","status":"available","confidence":0.922,"method":"yolo11n_iou"}]}

- Required fields:
  - detectionMethod: yolo11n
  - totalSlots: 1
  - totalAvailable: 1
  - totalOccupied: 0

## 4) Verdict

- PASS
- Condition: detectionMethod == "yolo11n"
- Actual: "yolo11n"
