/*
 * ============================================================
 *  ParkSmart — Arduino Barrier Control
 * ============================================================
 *
 *  Nhận lệnh UART từ ESP32 để điều khiển 2 servo barrier:
 *    - Pin 10: Cổng VÀO (Lane 1)  — OPEN_1 / CLOSE_1
 *    - Pin 9:  Cổng RA  (Lane 2)  — OPEN_2 / CLOSE_2
 *
 *  Wiring:
 *    ESP32 GPIO17 (TX2) ──► Arduino RX (Pin 0)
 *    ESP32 GND          ──► Arduino GND
 *    Servo IN  signal   ──► Arduino Pin 10
 *    Servo OUT signal   ──► Arduino Pin 9
 *    Servo VCC          ──► 5V (external power recommended)
 *    Servo GND          ──► GND
 *
 *  Protocol (9600 baud, newline-terminated):
 *    "OPEN_1\n"   → Mở cổng vào  (servo Pin 10 → 3000μs)
 *    "CLOSE_1\n"  → Đóng cổng vào (servo Pin 10 → 1500μs)
 *    "OPEN_2\n"   → Mở cổng ra   (servo Pin 9  → 3000μs)
 *    "CLOSE_2\n"  → Đóng cổng ra  (servo Pin 9  → 1500μs)
 *
 *  Auto-close: barrier tự đóng sau AUTO_CLOSE_MS (5 giây).
 */

#include <Servo.h>

// ── Servo objects ──────────────────────────────────────────── //
Servo servoIn;   // Cổng VÀO — Pin 10
Servo servoOut;  // Cổng RA  — Pin 9

// ── Servo pulse widths (microseconds) ─────────────────────── //
// Pin 10 — Entry gate
#define OPEN_ANGLE_10   3000
#define CLOSE_ANGLE_10  1500

// Pin 9 — Exit gate
#define OPEN_ANGLE_9    3000
#define CLOSE_ANGLE_9   1500

// ── Auto-close timer (ms) ─────────────────────────────────── //
#define AUTO_CLOSE_MS   5000

// ── State tracking ────────────────────────────────────────── //
bool lane1Open = false;
bool lane2Open = false;
unsigned long lane1OpenTime = 0;
unsigned long lane2OpenTime = 0;

// ── Status LED (built-in) ─────────────────────────────────── //
#define LED_PIN 13

void setup() {
  Serial.begin(9600);

  // Attach servos with pulse range
  servoIn.attach(10, 500, 2400);
  servoOut.attach(9, 500, 2400);

  // Default: cả 2 cổng đóng
  servoIn.writeMicroseconds(CLOSE_ANGLE_10);
  servoOut.writeMicroseconds(CLOSE_ANGLE_9);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.println("ARDUINO_READY");
  Serial.println("Barrier Control v1.0 — Waiting for commands...");
}

void loop() {
  // ── Read UART command from ESP32 ────────────────────────── //
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.length() == 0) return;

    Serial.print("CMD: ");
    Serial.println(cmd);

    // ===== Lane 1 — Entry Gate — Pin 10 ===================== //
    if (cmd == "OPEN_1") {
      servoIn.writeMicroseconds(OPEN_ANGLE_10);
      lane1Open = true;
      lane1OpenTime = millis();
      digitalWrite(LED_PIN, HIGH);
      Serial.println("ACK:OPEN_1");
    }
    else if (cmd == "CLOSE_1") {
      servoIn.writeMicroseconds(CLOSE_ANGLE_10);
      lane1Open = false;
      Serial.println("ACK:CLOSE_1");
    }

    // ===== Lane 2 — Exit Gate — Pin 9 ======================= //
    else if (cmd == "OPEN_2") {
      servoOut.writeMicroseconds(OPEN_ANGLE_9);
      lane2Open = true;
      lane2OpenTime = millis();
      digitalWrite(LED_PIN, HIGH);
      Serial.println("ACK:OPEN_2");
    }
    else if (cmd == "CLOSE_2") {
      servoOut.writeMicroseconds(CLOSE_ANGLE_9);
      lane2Open = false;
      Serial.println("ACK:CLOSE_2");
    }

    // ===== Status query ==================================== //
    else if (cmd == "STATUS") {
      Serial.print("LANE1:");
      Serial.print(lane1Open ? "OPEN" : "CLOSED");
      Serial.print(",LANE2:");
      Serial.println(lane2Open ? "OPEN" : "CLOSED");
    }

    // ===== Unknown command ================================= //
    else {
      Serial.print("ERR:UNKNOWN:");
      Serial.println(cmd);
    }

    // Turn off LED if both gates closed
    if (!lane1Open && !lane2Open) {
      digitalWrite(LED_PIN, LOW);
    }
  }

  // ── Auto-close: tự đóng barrier sau 5 giây ─────────────── //
  unsigned long now = millis();

  if (lane1Open && (now - lane1OpenTime >= AUTO_CLOSE_MS)) {
    servoIn.writeMicroseconds(CLOSE_ANGLE_10);
    lane1Open = false;
    Serial.println("AUTO:CLOSE_1");
  }

  if (lane2Open && (now - lane2OpenTime >= AUTO_CLOSE_MS)) {
    servoOut.writeMicroseconds(CLOSE_ANGLE_9);
    lane2Open = false;
    Serial.println("AUTO:CLOSE_2");
  }

  if (!lane1Open && !lane2Open) {
    digitalWrite(LED_PIN, LOW);
  }
}
