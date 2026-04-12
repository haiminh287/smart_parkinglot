/*
 * ============================================================
 *  ParkSmart — ESP32 Gate Controller
 * ============================================================
 *
 *  ESP32 kết nối WiFi, khi bấm nút:
 *    - Nút CHECK-IN  (GPIO 4)  → POST /ai/parking/esp32/check-in/
 *    - Nút CHECK-OUT (GPIO 5)  → POST /ai/parking/esp32/check-out/
 *
 *  Nhận response JSON → đọc barrier_action:
 *    "open" + check-in  → UART gửi "OPEN_1" → Arduino mở cổng vào
 *    "open" + check-out → UART gửi "OPEN_2" → Arduino mở cổng ra
 *
 *  Sau AUTO_CLOSE_SEC giây → gửi CLOSE_1 / CLOSE_2
 *
 *  Wiring:
 *    ESP32 GPIO16 (RX2) ← Arduino TX (Pin 1) [optional: receive ACK]
 *    ESP32 GPIO17 (TX2) → Arduino RX (Pin 0)
 *    ESP32 GND          → Arduino GND
 *    Button CHECK-IN    → GPIO 4 (pulled HIGH, press = LOW)
 *    Button CHECK-OUT   → GPIO 5 (pulled HIGH, press = LOW)
 *    Status LED         → GPIO 2 (built-in on most ESP32 boards)
 *
 *  Required Libraries (install via Arduino Library Manager):
 *    - ArduinoJson (v7+)
 *    - WiFi (built-in ESP32)
 *    - HTTPClient (built-in ESP32)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ═══════════════════════════════════════════════════════════════
//  CẤU HÌNH — THAY ĐỔI THEO MẠNG CỦA BẠN
// ═══════════════════════════════════════════════════════════════

// WiFi credentials
const char* WIFI_SSID     = "FPT Telecom-755C-IOT";      // ← Đổi tên WiFi
const char* WIFI_PASSWORD = "2462576d";   // ← Đổi mật khẩu WiFi

// AI Service URL — chạy local (máy tính cùng mạng WiFi)
// Thay IP bằng IP máy tính chạy AI service
const char* AI_SERVICE_BASE_URL = "http://192.168.100.194:8009";

// Gateway Secret — phải trùng với server
const char* GATEWAY_SECRET = "gateway-internal-secret-key";

// Device Token — phải trùng với ESP32_DEVICE_TOKEN trên server
const char* DEVICE_TOKEN = "your-device-token-here";

// Gate IDs
const char* GATE_IN_ID  = "GATE-IN-01";
const char* GATE_OUT_ID = "GATE-OUT-01";

// Firmware version
const char* FIRMWARE_VERSION = "v1.0.0-parksmart";

// ═══════════════════════════════════════════════════════════════
//  HARDWARE PINS
// ═══════════════════════════════════════════════════════════════

// UART2 to Arduino
#define RXD2 16  // ESP32 RX2 ← Arduino TX
#define TXD2 17  // ESP32 TX2 → Arduino RX

// Buttons (active LOW — sử dụng INPUT_PULLUP)
#define BTN_CHECK_IN  4
#define BTN_CHECK_OUT 5

// Status LED (built-in on most ESP32 dev boards)
#define LED_PIN 2

// OLED I2C
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_ADDR 0x3D

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// ═══════════════════════════════════════════════════════════════
//  CONSTANTS
// ═══════════════════════════════════════════════════════════════

#define DEBOUNCE_MS        300    // Chống rung nút nhấn
#define AUTO_CLOSE_SEC     5      // Tự đóng barrier sau 5 giây
#define HTTP_TIMEOUT_MS    30000  // HTTP timeout 30 giây (camera scan mất thời gian)
#define SERIAL_BAUD        115200 // Debug serial
#define UART2_BAUD         9600   // UART to Arduino
#define HEARTBEAT_INTERVAL 10000  // Heartbeat mỗi 10 giây (ms)

// ═══════════════════════════════════════════════════════════════
//  GLOBAL STATE
// ═══════════════════════════════════════════════════════════════

unsigned long lastBtnCheckIn  = 0;
unsigned long lastBtnCheckOut = 0;
unsigned long lastHeartbeat   = 0;

// Auto-close tracking
bool lane1Open = false;
bool lane2Open = false;
unsigned long lane1OpenTime = 0;
unsigned long lane2OpenTime = 0;

// Registration state
bool isRegistered = false;

// ═══════════════════════════════════════════════════════════════
//  UTILITY — Sanitize UART strings
// ═══════════════════════════════════════════════════════════════

/**
 * Remove non-printable and non-ASCII characters from a String.
 * UART noise (baud mismatch, electrical interference) produces
 * garbage bytes that break JSON encoding (HTTP 400).
 * Only keeps characters 0x20–0x7E (printable ASCII).
 */
String sanitizeString(const String& input) {
  String output;
  output.reserve(input.length());
  for (unsigned int i = 0; i < input.length(); i++) {
    char c = input.charAt(i);
    if (c >= 0x20 && c <= 0x7E) {
      output += c;
    }
  }
  output.trim();
  return output;
}

// ═══════════════════════════════════════════════════════════════
//  SETUP
// ═══════════════════════════════════════════════════════════════

void setup() {
  // Debug serial
  Serial.begin(SERIAL_BAUD);
  Serial.println("\n================================");
  Serial.println("ParkSmart ESP32 Gate Controller");
  Serial.println("================================");

  // UART2 → Arduino
  Serial2.begin(UART2_BAUD, SERIAL_8N1, RXD2, TXD2);

  // Button pins
  pinMode(BTN_CHECK_IN, INPUT_PULLUP);
  pinMode(BTN_CHECK_OUT, INPUT_PULLUP);

  // LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // Connect WiFi
  connectWiFi();

  // OLED INIT
  Wire.begin(21, 22); // SDA, SCL

  if(!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("OLED Fail");
    while(1);
  }
  Serial.println("OLED Done");

  display.clearDisplay();
  display.setTextSize(2);
  display.setTextColor(WHITE);
  display.setCursor(0,10);
  display.println("ParkSmart");
  display.display();

  // Register both gate devices with AI Service
  registerDevice(GATE_IN_ID);
  registerDevice(GATE_OUT_ID);

  Serial.println("\n✅ Ready! Press buttons to check-in/check-out.");
  Serial.println("  GPIO 4 = CHECK-IN  (Entry gate)");
  Serial.println("  GPIO 5 = CHECK-OUT (Exit gate)");

  // Send initial boot log
  sendLog(GATE_IN_ID, "info", "ESP32 booted. WiFi connected, OLED initialized, devices registered.");
  sendLog(GATE_OUT_ID, "info", "ESP32 booted. WiFi connected, OLED initialized, devices registered.");
}

// ═══════════════════════════════════════════════════════════════
//  MAIN LOOP
// ═══════════════════════════════════════════════════════════════

void loop() {
  unsigned long now = millis();

  // ── Check WiFi connection ─────────────────────────────────── //
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️ WiFi disconnected, reconnecting...");
    sendLog(GATE_IN_ID, "warn", "WiFi disconnected, reconnecting...");
    connectWiFi();
    if (WiFi.status() == WL_CONNECTED) {
      sendLog(GATE_IN_ID, "info", "WiFi reconnected. IP: " + WiFi.localIP().toString());
    }
  }

  // ── Periodic heartbeat ────────────────────────────────────── //
  if (now - lastHeartbeat >= HEARTBEAT_INTERVAL) {
    lastHeartbeat = now;
    sendHeartbeat(GATE_IN_ID);
    sendHeartbeat(GATE_OUT_ID);
  }

  // ── Button CHECK-IN (GPIO 4) ──────────────────────────────── //
  if (digitalRead(BTN_CHECK_IN) == LOW && (now - lastBtnCheckIn > DEBOUNCE_MS)) {
    lastBtnCheckIn = now;
    Serial.println("\n🔵 Button CHECK-IN pressed!");
    sendLog(GATE_IN_ID, "info", "Button CHECK-IN pressed (GPIO 4)");
    blinkLED(2);
    handleCheckIn();
  }

  // ── Button CHECK-OUT (GPIO 5) ─────────────────────────────── //
  if (digitalRead(BTN_CHECK_OUT) == LOW && (now - lastBtnCheckOut > DEBOUNCE_MS)) {
    lastBtnCheckOut = now;
    Serial.println("\n🔴 Button CHECK-OUT pressed!");
    sendLog(GATE_OUT_ID, "info", "Button CHECK-OUT pressed (GPIO 5)");
    blinkLED(3);
    handleCheckOut();
  }

  // ── Auto-close barriers ───────────────────────────────────── //
  if (lane1Open && (now - lane1OpenTime >= (unsigned long)AUTO_CLOSE_SEC * 1000)) {
    sendToArduino("CLOSE_1");
    lane1Open = false;
    Serial.println("🔒 Auto-close: Entry gate (CLOSE_1)");
    sendLog(GATE_IN_ID, "info", "Auto-close entry barrier after " + String(AUTO_CLOSE_SEC) + "s → UART: CLOSE_1");
  }

  if (lane2Open && (now - lane2OpenTime >= (unsigned long)AUTO_CLOSE_SEC * 1000)) {
    sendToArduino("CLOSE_2");
    lane2Open = false;
    Serial.println("🔒 Auto-close: Exit gate (CLOSE_2)");
    sendLog(GATE_OUT_ID, "info", "Auto-close exit barrier after " + String(AUTO_CLOSE_SEC) + "s → UART: CLOSE_2");
  }

  // ── Read ACK from Arduino (optional debug) ────────────────── //
  while (Serial2.available()) {
    String ack = Serial2.readStringUntil('\n');
    ack.trim();
    if (ack.length() > 0) {
      // Sanitize: remove non-printable / non-ASCII bytes (UART noise)
      String clean = sanitizeString(ack);
      if (clean.length() > 0) {
        Serial.print("📨 Arduino: ");
        Serial.println(clean);
        sendLog(GATE_IN_ID, "info", "Arduino ACK: " + clean);
      } else {
        Serial.println("📨 Arduino: (garbage data ignored)");
      }
    }
  }

  delay(50);  // Small delay to prevent busy-looping
}

// ═══════════════════════════════════════════════════════════════
//  DEVICE REGISTRATION
// ═══════════════════════════════════════════════════════════════

void registerDevice(const char* deviceId) {
  String url = String(AI_SERVICE_BASE_URL) + "/ai/parking/esp32/register";

  JsonDocument doc;
  doc["device_id"] = deviceId;
  doc["ip"] = WiFi.localIP().toString();
  doc["firmware"] = FIRMWARE_VERSION;

  JsonObject gpio = doc["gpio_config"].to<JsonObject>();
  gpio["check_in_pin"] = BTN_CHECK_IN;
  gpio["check_out_pin"] = BTN_CHECK_OUT;

  String jsonBody;
  serializeJson(doc, jsonBody);

  Serial.print("📋 Registering device: ");
  Serial.println(deviceId);

  String response = httpPost(url, jsonBody);

  if (response.length() > 0) {
    Serial.println("✅ Device registered: " + String(deviceId));
    isRegistered = true;
  } else {
    Serial.println("⚠️ Registration failed for: " + String(deviceId));
  }
}

// ═══════════════════════════════════════════════════════════════
//  HEARTBEAT
// ═══════════════════════════════════════════════════════════════

void sendHeartbeat(const char* deviceId) {
  String url = String(AI_SERVICE_BASE_URL) + "/ai/parking/esp32/heartbeat";

  JsonDocument doc;
  doc["device_id"] = deviceId;
  doc["status"] = "ready";
  doc["wifi_rssi"] = WiFi.RSSI();

  String jsonBody;
  serializeJson(doc, jsonBody);

  HTTPClient http;
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Gateway-Secret", GATEWAY_SECRET);
  http.addHeader("X-Device-Token", DEVICE_TOKEN);
  http.setTimeout(5000);  // Heartbeat timeout ngắn hơn

  int httpCode = http.POST(jsonBody);
  http.end();

  if (httpCode != 200) {
    Serial.print("⚠️ Heartbeat failed for ");
    Serial.print(deviceId);
    Serial.print(": HTTP ");
    Serial.println(httpCode);
  }
}

// ═══════════════════════════════════════════════════════════════
//  SEND LOG TO BACKEND
// ═══════════════════════════════════════════════════════════════

void sendLog(const char* deviceId, const char* level, String message) {
  // Also print locally
  Serial.print("[LOG → ");
  Serial.print(deviceId);
  Serial.print("] ");
  Serial.print(level);
  Serial.print(": ");
  Serial.println(message);

  // Send to backend
  String url = String(AI_SERVICE_BASE_URL) + "/ai/parking/esp32/log";

  JsonDocument doc;
  doc["device_id"] = deviceId;
  doc["level"] = level;
  doc["message"] = message;

  String jsonBody;
  serializeJson(doc, jsonBody);

  HTTPClient http;
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Gateway-Secret", GATEWAY_SECRET);
  http.addHeader("X-Device-Token", DEVICE_TOKEN);
  http.setTimeout(5000);  // Log timeout ngắn

  int httpCode = http.POST(jsonBody);
  http.end();

  // Don't log errors here to avoid infinite recursion
  if (httpCode < 200 || httpCode >= 300) {
    Serial.print("⚠️ Log send failed: HTTP ");
    Serial.println(httpCode);
  }
}

// ═══════════════════════════════════════════════════════════════
//  CHECK-IN HANDLER
// ═══════════════════════════════════════════════════════════════

void handleCheckIn() {
  Serial.println("📡 Calling AI service: /check-in/ ...");
  Serial.println("   (Server sẽ mở camera QR, quét mã QR, đọc biển số...)");
  sendLog(GATE_IN_ID, "info", "Calling AI service /check-in/ — waiting for QR scan & plate recognition...");

  // Build URL
  String url = String(AI_SERVICE_BASE_URL) + "/ai/parking/esp32/check-in/";

  // Build JSON body
  JsonDocument doc;
  doc["gate_id"] = GATE_IN_ID;

  String jsonBody;
  serializeJson(doc, jsonBody);

  // Call API
  String response = httpPost(url, jsonBody);

  if (response.length() == 0) {
    Serial.println("❌ No response from server!");
    sendLog(GATE_IN_ID, "error", "No response from AI service for check-in. Server may be down.");
    blinkLED(5);  // Error indicator
    return;
  }

  // Parse response
  Serial.println("📥 Response received, parsing...");
  parseAndActOnResponse(response, "check_in");
}

// ═══════════════════════════════════════════════════════════════
//  CHECK-OUT HANDLER
// ═══════════════════════════════════════════════════════════════

void handleCheckOut() {
  Serial.println("📡 Calling AI service: /check-out/ ...");
  Serial.println("   (Server sẽ mở camera QR, quét mã QR, xác nhận thanh toán...)");
  sendLog(GATE_OUT_ID, "info", "Calling AI service /check-out/ — waiting for QR scan & payment check...");

  // Build URL
  String url = String(AI_SERVICE_BASE_URL) + "/ai/parking/esp32/check-out/";

  // Build JSON body
  JsonDocument doc;
  doc["gate_id"] = GATE_OUT_ID;

  String jsonBody;
  serializeJson(doc, jsonBody);

  // Call API
  String response = httpPost(url, jsonBody);

  if (response.length() == 0) {
    Serial.println("❌ No response from server!");
    sendLog(GATE_OUT_ID, "error", "No response from AI service for check-out. Server may be down.");
    blinkLED(5);
    return;
  }

  Serial.println("📥 Response received, parsing...");
  parseAndActOnResponse(response, "check_out");
}

// ═══════════════════════════════════════════════════════════════
//  PARSE RESPONSE & CONTROL BARRIER
// ═══════════════════════════════════════════════════════════════

void parseAndActOnResponse(String& response, const char* actionType) {
  const char* currentGateId = (strcmp(actionType, "check_in") == 0) ? GATE_IN_ID : GATE_OUT_ID;

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, response);

  if (err) {
    Serial.print("❌ JSON parse error: ");
    Serial.println(err.c_str());
    sendLog(currentGateId, "error", "JSON parse error: " + String(err.c_str()));
    return;
  }

  // Extract fields (camelCase from server)
  bool success            = doc["success"] | false;
  const char* event       = doc["event"] | "unknown";
  const char* barrierAction = doc["barrierAction"] | "close";
  const char* message     = doc["message"] | "";
  const char* bookingId   = doc["bookingId"] | "";
  const char* plateText   = doc["plateText"] | "";
  float processingTime    = doc["processingTimeMs"] | 0.0;

  // Print status
  Serial.println("┌─────────────────────────────────");
  Serial.print("│ Success: ");
  Serial.println(success ? "✅ YES" : "❌ NO");
  Serial.print("│ Event:   ");
  Serial.println(event);
  Serial.print("│ Action:  ");
  Serial.println(barrierAction);
  Serial.print("│ Message: ");
  Serial.println(message);
  if (strlen(bookingId) > 0) {
    Serial.print("│ Booking: ");
    Serial.println(bookingId);
  }
  if (strlen(plateText) > 0) {
    Serial.print("│ Plate:   ");
    Serial.println(plateText);

    if (strcmp(actionType, "check_in") == 0) {
      showPlateOnOLED(plateText, "IN");
    } else {
      showPlateOnOLED(plateText, "OUT");
    }
  }
  Serial.print("│ Time:    ");
  Serial.print(processingTime, 0);
  Serial.println(" ms");
  Serial.println("└─────────────────────────────────");

  // Build detailed log message
  String logMsg = String(success ? "✅ " : "❌ ") + String(event);
  logMsg += " | barrier=" + String(barrierAction);
  if (strlen(bookingId) > 0) logMsg += " | booking=" + String(bookingId);
  if (strlen(plateText) > 0) logMsg += " | plate=" + String(plateText);
  logMsg += " | " + String(processingTime, 0) + "ms";
  logMsg += " | " + String(message);

  // Truncate if too long for API (max 500 chars)
  if (logMsg.length() > 490) {
    logMsg = logMsg.substring(0, 487) + "...";
  }

  sendLog(currentGateId, success ? "info" : "warn", logMsg);

  // ── Act on barrier_action ─────────────────────────────────── //
  if (String(barrierAction) == "open") {
    if (strcmp(actionType, "check_in") == 0) {
      // Entry gate → OPEN_1
      sendToArduino("OPEN_1");
      lane1Open = true;
      lane1OpenTime = millis();
      Serial.println("🟢 BARRIER OPEN → Entry gate (OPEN_1)");
      Serial.println("   Xe được phép vào bãi!");
      sendLog(GATE_IN_ID, "info", "🟢 BARRIER OPEN → UART: OPEN_1 sent to Arduino. Vehicle allowed to enter.");
    } else {
      // Exit gate → OPEN_2
      sendToArduino("OPEN_2");
      lane2Open = true;
      lane2OpenTime = millis();
      Serial.println("🟢 BARRIER OPEN → Exit gate (OPEN_2)");
      Serial.println("   Xe được phép ra khỏi bãi!");
      sendLog(GATE_OUT_ID, "info", "🟢 BARRIER OPEN → UART: OPEN_2 sent to Arduino. Vehicle allowed to exit.");
    }
    digitalWrite(LED_PIN, HIGH);
  } else {
    // Barrier stays closed
    Serial.println("🔴 BARRIER CLOSED — Không mở cổng");
    if (strcmp(actionType, "check_in") == 0) {
      sendToArduino("CLOSE_1");
      sendLog(GATE_IN_ID, "warn", "🔴 BARRIER CLOSED → UART: CLOSE_1. Reason: " + String(message));
    } else {
      sendToArduino("CLOSE_2");
      sendLog(GATE_OUT_ID, "warn", "🔴 BARRIER CLOSED → UART: CLOSE_2. Reason: " + String(message));
    }
    digitalWrite(LED_PIN, LOW);
  }
}

// ═══════════════════════════════════════════════════════════════
//  HTTP POST
// ═══════════════════════════════════════════════════════════════

String httpPost(String& url, String& jsonBody) {
  HTTPClient http;

  Serial.print("  → URL:  ");
  Serial.println(url);
  Serial.print("  → Body: ");
  Serial.println(jsonBody);

  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Gateway-Secret", GATEWAY_SECRET);
  http.addHeader("X-Device-Token", DEVICE_TOKEN);
  http.setTimeout(HTTP_TIMEOUT_MS);

  int httpCode = http.POST(jsonBody);

  String response = "";

  if (httpCode > 0) {
    Serial.print("  ← HTTP ");
    Serial.println(httpCode);
    response = http.getString();

    // Print truncated response for debug
    if (response.length() > 500) {
      Serial.println("  ← Response (truncated):");
      Serial.println(response.substring(0, 500));
    } else {
      Serial.println("  ← Response:");
      Serial.println(response);
    }
  } else {
    Serial.print("  ← HTTP ERROR: ");
    Serial.println(http.errorToString(httpCode));
  }

  http.end();
  return response;
}

// ═══════════════════════════════════════════════════════════════
//  UART → ARDUINO
// ═══════════════════════════════════════════════════════════════

void sendToArduino(const char* command) {
  Serial.print("📤 UART → Arduino: ");
  Serial.println(command);
  Serial2.println(command);
}

// ═══════════════════════════════════════════════════════════════
//  WIFI CONNECTION
// ═══════════════════════════════════════════════════════════════

void connectWiFi() {
  Serial.print("📶 Connecting to WiFi: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.print("✅ Connected! IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("📶 WiFi RSSI: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    Serial.println();
    Serial.println("❌ WiFi connection failed! Will retry...");
  }
}

// ═══════════════════════════════════════════════════════════════
//  LED BLINK
// ═══════════════════════════════════════════════════════════════

void blinkLED(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
    delay(100);
  }
}

// ═══════════════════════════════════════════════════════════════
//  OLED DISPLAY
// ═══════════════════════════════════════════════════════════════

void showPlateOnOLED(const char* plate, const char* gate) {
  display.clearDisplay();

  display.setTextSize(1);
  display.setCursor(0,0);
  display.print("Gate: ");
  display.println(gate);

  display.setTextSize(2);
  display.setCursor(0,20);
  display.println(plate);

  display.display();
}
