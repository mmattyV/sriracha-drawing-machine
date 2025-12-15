/*
 * Sriracha Sketcher - ESP32 Firmware
 * SSG (Sauce Simple G-code) Protocol Implementation
 * 
 * Features:
 * - Single X-motor, single Y-motor 2D gantry
 * - PWM sauce pump control with flow ramping
 * - SSG protocol with sequence numbers and acks
 * - State machine (IDLE/HOMING/READY/PRINTING/PAUSED/ERROR)
 * - Sliding window flow control
 * - Endstop-based homing
 * - Safety interlocks and watchdog
 * 
 * Design Doc: Section 5 (Firmware)
 */

#include <WiFi.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <AccelStepper.h>

// ============================================
// CONFIGURATION - Adjust for your hardware
// ============================================

// Testing mode (bypasses homing requirement - DISABLE FOR PRODUCTION!)
#define TESTING_MODE true  // Set to true to skip homing requirement

// WiFi credentials
const char* WIFI_SSID = "MAKERSPACE";
const char* WIFI_PASSWORD = "12345678";

// ==============================================
// XIAO ESP32C3 PIN MAPPING
// ==============================================
// Xiao ESP32C3 available GPIOs:
//   D0=GPIO2, D1=GPIO3, D2=GPIO4, D3=GPIO5
//   D4=GPIO6, D5=GPIO7, D6=GPIO21, D7=GPIO20
//   D8=GPIO8, D9=GPIO9, D10=GPIO10
//
// Adjust these to match YOUR wiring!
// ==============================================

// Endstop pins (active low with pullup)
#define X_ENDSTOP_PIN  20  // D7
#define Y_ENDSTOP_PIN  8   // D8

// Motor pins (Step, Direction)
#define X_STEP_PIN  2   // D0
#define X_DIR_PIN   3   // D1
#define Y_STEP_PIN  4   // D2
#define Y_DIR_PIN   5   // D3

// Sauce pump PWM
#define PUMP_PWM_PIN   21  // D6
#define PUMP_PWM_CHANNEL 0  // Not used in ESP32 core 3.x (kept for reference)
#define PUMP_PWM_FREQ   1000  // 1kHz
#define PUMP_PWM_RESOLUTION 8  // 8-bit (0-255)

// Kinematics (from config.py)
const float STEPS_PER_MM_X = 80.0;
const float STEPS_PER_MM_Y = 80.0;
const float MAX_SPEED_X = 2000.0;  // steps/sec
const float MAX_SPEED_Y = 2000.0;
const float ACCELERATION = 800.0;  // steps/sec²

// Limits (mm)
const float X_MIN = -120.0;
const float X_MAX = 120.0;
const float Y_MIN = -120.0;
const float Y_MAX = 120.0;

// Flow timing (ms)
const int SAUCE_ON_DWELL_MS = 100;
const int SAUCE_OFF_DWELL_MS = 50;

// ============================================
// STATE MACHINE
// ============================================

enum State {
  STATE_BOOT,
  STATE_IDLE,
  STATE_HOMING,
  STATE_READY,
  STATE_PRINTING,
  STATE_PAUSED,
  STATE_CLEANING,
  STATE_ERROR
};

State current_state = STATE_BOOT;
String error_message = "";

// ============================================
// MOTOR OBJECTS
// ============================================

AccelStepper stepper_X(AccelStepper::DRIVER, X_STEP_PIN, X_DIR_PIN);
AccelStepper stepper_Y(AccelStepper::DRIVER, Y_STEP_PIN, Y_DIR_PIN);

// ============================================
// WEBSOCKET SERVER
// ============================================

AsyncWebServer server(80);
AsyncWebSocket ws("/ws");

// ============================================
// COMMAND QUEUE
// ============================================

struct SSGCommand {
  uint32_t seq;        // Sequence number
  char cmd_type;       // 'G' or 'M'
  int cmd_num;         // 0, 1, 28, 3, 5, etc.
  float x, y, f;       // Parameters
  int s;               // Flow duty (0-100)
  bool has_x, has_y, has_f, has_s;
};

const int QUEUE_SIZE = 64;
SSGCommand command_queue[QUEUE_SIZE];
int queue_head = 0;
int queue_tail = 0;
int queue_count = 0;

// ============================================
// POSITION & FLOW STATE
// ============================================

float current_x_mm = 0.0;
float current_y_mm = 0.0;
int current_flow = 0;  // 0-100%
bool sauce_is_on = false;

uint32_t last_acked_seq = 0;
uint32_t expected_next_seq = 1;  // Track expected sequence for gap detection
uint32_t last_heartbeat_ms = 0;

// ============================================
// WATCHDOG
// ============================================

unsigned long last_command_ms = 0;
const unsigned long HEARTBEAT_TIMEOUT_MS = 3000;  // 3 seconds

// ============================================
// SETUP
// ============================================

void setup() {
  Serial.begin(115200);
  
  // Wait for USB CDC serial to be ready (important for Xiao ESP32C3!)
  // This waits up to 3 seconds for serial monitor to connect
  unsigned long serialStart = millis();
  while (!Serial && (millis() - serialStart < 3000)) {
    delay(10);
  }
  delay(500);  // Extra delay for stability
  
  Serial.println("\n\n=================================");
  Serial.println("Sriracha Sketcher - Booting");
  Serial.println("=================================");
  
  // Configure endstops
  pinMode(X_ENDSTOP_PIN, INPUT_PULLUP);
  pinMode(Y_ENDSTOP_PIN, INPUT_PULLUP);
  
  // Configure steppers
  stepper_X.setMaxSpeed(MAX_SPEED_X);
  stepper_X.setAcceleration(ACCELERATION);
  stepper_Y.setMaxSpeed(MAX_SPEED_Y);
  stepper_Y.setAcceleration(ACCELERATION);
  
  // Configure pump PWM (ESP32 core 3.x API)
  ledcAttach(PUMP_PWM_PIN, PUMP_PWM_FREQ, PUMP_PWM_RESOLUTION);
  ledcWrite(PUMP_PWM_PIN, 0);  // Pump off initially
  
  // Connect to WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi connection failed!");
    current_state = STATE_ERROR;
    error_message = "WiFi connection failed";
    return;
  }
  
  // Initialize WebSocket
  ws.onEvent(onWebSocketEvent);
  server.addHandler(&ws);
  server.begin();
  
  Serial.println("WebSocket server started");
  
  #if TESTING_MODE
    current_state = STATE_READY;
    Serial.println("⚠️  TESTING MODE - Homing bypassed! Machine position unknown!");
    Serial.println("System ready (no homing required)");
  #else
    current_state = STATE_IDLE;
    Serial.println("System ready - waiting for G28 (home) command");
  #endif
}

// ============================================
// MAIN LOOP
// ============================================

void loop() {
  // Clean up WebSocket clients
  ws.cleanupClients();
  
  // Watchdog: check for heartbeat timeout
  if (current_state == STATE_PRINTING) {
    if (millis() - last_command_ms > HEARTBEAT_TIMEOUT_MS) {
      Serial.println("WARNING: Heartbeat timeout - pausing and turning sauce off");
      sauce_off();
      current_state = STATE_PAUSED;
      ws.textAll("err timeout HEARTBEAT");
    }
  }
  
  // State-specific behavior
  switch (current_state) {
    case STATE_IDLE:
    case STATE_READY:
    case STATE_PAUSED:
      // Idle - just process any queued commands
      break;
      
    case STATE_HOMING:
      // Handled by homing function
      break;
      
    case STATE_PRINTING:
      // Execute queued commands
      execute_next_command();
      break;
      
    case STATE_ERROR:
      // Stay in error state until reset
      break;
  }
  
  // Always run steppers
  stepper_X.run();
  stepper_Y.run();
  
  // Send heartbeat every second
  if (millis() - last_heartbeat_ms > 1000) {
    send_telemetry();
    last_heartbeat_ms = millis();
  }
}

// ============================================
// WEBSOCKET EVENT HANDLER
// ============================================

void onWebSocketEvent(AsyncWebSocket *server, AsyncWebSocketClient *client,
                      AwsEventType type, void *arg, uint8_t *data, size_t len) {
  if (type == WS_EVT_CONNECT) {
    Serial.printf("WebSocket client #%u connected\n", client->id());
    send_status();
    
  } else if (type == WS_EVT_DISCONNECT) {
    Serial.printf("WebSocket client #%u disconnected\n", client->id());
    
    // Safety: turn sauce off on disconnect
    if (sauce_is_on) {
      sauce_off();
      Serial.println("Client disconnected - sauce turned off for safety");
    }
    
  } else if (type == WS_EVT_DATA) {
    AwsFrameInfo *info = (AwsFrameInfo*)arg;
    if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT) {
      data[len] = 0;
      String message = (char*)data;
      handle_message(message);
      last_command_ms = millis();
    }
  }
}

// ============================================
// MESSAGE HANDLER
// ============================================

void handle_message(String message) {
  message.trim();
  
  // Parse SSG command
  SSGCommand cmd;
  if (!parse_ssg_command(message, cmd)) {
    ws.textAll("err parse INVALID");
    return;
  }
  
  // Check sequence number
  if (cmd.seq != 0) {  // N0 is for special commands (manual control)
    // Duplicate detection (from retry)
    if (cmd.seq < expected_next_seq) {
      // Already processed - just ack again, don't execute
      ws.textAll("ok N" + String(cmd.seq));
      return;
    }
    
    // Gap detection (missing command)
    if (cmd.seq > expected_next_seq) {
      // Missing command(s) detected! Reject this and wait for missing one
      ws.textAll("err N" + String(cmd.seq) + " code=GAP");
      Serial.printf("ERROR: Sequence gap! Expected N%d, received N%d\n", 
                    expected_next_seq, cmd.seq);
      return;
    }
    
    // Correct sequence - increment expected
    expected_next_seq = cmd.seq + 1;
  }
  
  // Validate state for command
  if (cmd.cmd_type == 'G' && cmd.cmd_num != 28) {
    if (current_state != STATE_READY && current_state != STATE_PRINTING) {
      ws.textAll("err N" + String(cmd.seq) + " code=NOT_HOMED");
      return;
    }
  }
  
  // Execute immediate commands (non-motion)
  if (cmd.cmd_type == 'M') {
    if (cmd.cmd_num == 3) {
      // M3 S<duty> - sauce on
      execute_m3(cmd);
      ws.textAll("ok N" + String(cmd.seq));
      last_acked_seq = cmd.seq;
      return;
      
    } else if (cmd.cmd_num == 5) {
      // M5 - sauce off
      execute_m5(cmd);
      ws.textAll("ok N" + String(cmd.seq));
      last_acked_seq = cmd.seq;
      return;
      
    } else if (cmd.cmd_num == 114) {
      // M114 - report position
      report_position();
      ws.textAll("ok N" + String(cmd.seq));
      last_acked_seq = cmd.seq;
      return;
      
    } else if (cmd.cmd_num == 408) {
      // M408 - report status
      send_status();
      ws.textAll("ok N" + String(cmd.seq));
      last_acked_seq = cmd.seq;
      return;
    }
  }
  
  // G28 - homing (special handling)
  if (cmd.cmd_type == 'G' && cmd.cmd_num == 28) {
    execute_g28();
    ws.textAll("ok N" + String(cmd.seq));
    last_acked_seq = cmd.seq;
    return;
  }
  
  // Queue motion commands (G0, G1)
  if (queue_count >= QUEUE_SIZE) {
    ws.textAll("busy q=" + String(queue_count) + " state=" + state_to_string(current_state));
    return;
  }
  
  // Add to queue
  command_queue[queue_tail] = cmd;
  queue_tail = (queue_tail + 1) % QUEUE_SIZE;
  queue_count++;
  
  // Ack immediately
  ws.textAll("ok N" + String(cmd.seq));
  last_acked_seq = cmd.seq;
  
  // Start printing if not already
  if (current_state == STATE_READY) {
    current_state = STATE_PRINTING;
  }
}

// ============================================
// SSG COMMAND PARSER
// ============================================

bool parse_ssg_command(String line, SSGCommand &cmd) {
  // Format: N123 G1 X10.00 Y20.00 F600
  // or:     N124 M3 S60
  
  cmd.seq = 0;
  cmd.has_x = cmd.has_y = cmd.has_f = cmd.has_s = false;
  cmd.x = cmd.y = cmd.f = 0.0;
  cmd.s = 0;
  
  // Parse sequence number
  int n_pos = line.indexOf('N');
  if (n_pos != -1) {
    int space_pos = line.indexOf(' ', n_pos);
    cmd.seq = line.substring(n_pos + 1, space_pos).toInt();
    line = line.substring(space_pos + 1);
  }
  
  line.trim();
  
  // Parse command (G or M)
  if (line.startsWith("G")) {
    cmd.cmd_type = 'G';
    int space_pos = line.indexOf(' ');
    cmd.cmd_num = line.substring(1, space_pos == -1 ? line.length() : space_pos).toInt();
    
  } else if (line.startsWith("M")) {
    cmd.cmd_type = 'M';
    int space_pos = line.indexOf(' ');
    cmd.cmd_num = line.substring(1, space_pos == -1 ? line.length() : space_pos).toInt();
    
  } else {
    return false;
  }
  
  // Parse parameters
  int x_pos = line.indexOf('X');
  if (x_pos != -1) {
    cmd.x = line.substring(x_pos + 1).toFloat();
    cmd.has_x = true;
  }
  
  int y_pos = line.indexOf('Y');
  if (y_pos != -1) {
    cmd.y = line.substring(y_pos + 1).toFloat();
    cmd.has_y = true;
  }
  
  int f_pos = line.indexOf('F');
  if (f_pos != -1) {
    cmd.f = line.substring(f_pos + 1).toFloat();
    cmd.has_f = true;
  }
  
  int s_pos = line.indexOf('S');
  if (s_pos != -1) {
    cmd.s = line.substring(s_pos + 1).toInt();
    cmd.has_s = true;
  }
  
  return true;
}

// ============================================
// COMMAND EXECUTION
// ============================================

void execute_next_command() {
  if (queue_count == 0) {
    return;
  }
  
  // Check if motors are still moving
  if (stepper_X.distanceToGo() != 0 || 
      stepper_Y.distanceToGo() != 0) {
    return;  // Wait for current move to complete
  }
  
  // Get next command
  SSGCommand cmd = command_queue[queue_head];
  queue_head = (queue_head + 1) % QUEUE_SIZE;
  queue_count--;
  
  // Execute based on type
  if (cmd.cmd_type == 'G') {
    if (cmd.cmd_num == 0) {
      execute_g0(cmd);  // Rapid move
    } else if (cmd.cmd_num == 1) {
      execute_g1(cmd);  // Linear move
    }
  }
}

void execute_g0(SSGCommand &cmd) {
  // G0 - rapid move (sauce should be off)
  if (cmd.has_x) current_x_mm = cmd.x;
  if (cmd.has_y) current_y_mm = cmd.y;
  
  // Validate limits
  if (!check_limits(current_x_mm, current_y_mm)) {
    enter_error_state("LIMIT_EXCEEDED");
    return;
  }
  
  // Convert to steps and move
  long target_x = current_x_mm * STEPS_PER_MM_X;
  long target_y = current_y_mm * STEPS_PER_MM_Y;
  
  stepper_X.moveTo(target_x);
  stepper_Y.moveTo(target_y);
}

void execute_g1(SSGCommand &cmd) {
  // G1 - linear move (drawing)
  if (cmd.has_x) current_x_mm = cmd.x;
  if (cmd.has_y) current_y_mm = cmd.y;
  
  // Validate limits
  if (!check_limits(current_x_mm, current_y_mm)) {
    enter_error_state("LIMIT_EXCEEDED");
    return;
  }
  
  // Adjust speed if feed rate specified
  if (cmd.has_f) {
    float feed_mm_per_sec = cmd.f / 60.0;
    float speed_steps_per_sec = feed_mm_per_sec * STEPS_PER_MM_X;
    stepper_X.setMaxSpeed(speed_steps_per_sec);
    stepper_Y.setMaxSpeed(speed_steps_per_sec * STEPS_PER_MM_Y / STEPS_PER_MM_X);
  }
  
  // Convert to steps and move
  long target_x = current_x_mm * STEPS_PER_MM_X;
  long target_y = current_y_mm * STEPS_PER_MM_Y;
  
  stepper_X.moveTo(target_x);
  stepper_Y.moveTo(target_y);
}

void execute_g28() {
  // G28 - home all axes
  
  #if TESTING_MODE
    Serial.println("⚠️  TESTING MODE - Homing bypassed! Machine position unknown!");
    current_x_mm = 0.0;
    current_y_mm = 0.0;
    current_state = STATE_READY;
    expected_next_seq = 1;
    last_acked_seq = 0;
    Serial.println("System ready (no homing required)");
    return;
  #endif
  
  Serial.println("Starting homing sequence...");
  current_state = STATE_HOMING;
  
  // Turn sauce off
  sauce_off();
  
  // Phase 1: Home X axis
  Serial.println("Homing X...");
  stepper_X.setSpeed(-800);  // Move toward endstop (negative direction)
  while (digitalRead(X_ENDSTOP_PIN) == HIGH) {
    stepper_X.runSpeed();
  }
  stepper_X.setCurrentPosition(0);
  stepper_X.move(5 * STEPS_PER_MM_X);  // Back off 5mm
  while (stepper_X.distanceToGo() != 0) {
    stepper_X.run();
  }
  
  // Slow re-home X for precision
  Serial.println("Precision X homing...");
  stepper_X.setSpeed(-200);
  while (digitalRead(X_ENDSTOP_PIN) == LOW) {
    stepper_X.runSpeed();
  }
  stepper_X.setCurrentPosition(0);
  
  // Phase 2: Home Y axis
  Serial.println("Homing Y...");
  stepper_Y.setSpeed(-800);
  while (digitalRead(Y_ENDSTOP_PIN) == HIGH) {
    stepper_Y.runSpeed();
  }
  stepper_Y.setCurrentPosition(0);
  stepper_Y.move(5 * STEPS_PER_MM_Y);  // Back off 5mm
  while (stepper_Y.distanceToGo() != 0) {
    stepper_Y.run();
  }
  
  // Slow re-home Y for precision
  Serial.println("Precision Y homing...");
  stepper_Y.setSpeed(-200);
  while (digitalRead(Y_ENDSTOP_PIN) == LOW) {
    stepper_Y.runSpeed();
  }
  stepper_Y.setCurrentPosition(0);
  
  // Reset speeds to normal
  stepper_X.setMaxSpeed(MAX_SPEED_X);
  stepper_Y.setMaxSpeed(MAX_SPEED_Y);
  
  current_x_mm = 0.0;
  current_y_mm = 0.0;
  current_state = STATE_READY;
  
  // Reset sequence tracking after homing
  expected_next_seq = 1;
  last_acked_seq = 0;
  
  Serial.println("Homing complete - system ready");
}

void execute_m3(SSGCommand &cmd) {
  // M3 S<duty> - sauce on
  if (cmd.has_s) {
    current_flow = constrain(cmd.s, 0, 100);
  }
  
  sauce_on(current_flow);
  delay(SAUCE_ON_DWELL_MS);
}

void execute_m5(SSGCommand &cmd) {
  // M5 - sauce off
  sauce_off();
  delay(SAUCE_OFF_DWELL_MS);
}

// ============================================
// SAUCE CONTROL
// ============================================

void sauce_on(int duty) {
  // duty: 0-100%
  int pwm_value = map(duty, 0, 100, 0, 255);
  ledcWrite(PUMP_PWM_PIN, pwm_value);
  sauce_is_on = true;
  Serial.printf("Sauce ON: %d%% (PWM: %d)\n", duty, pwm_value);
}

void sauce_off() {
  ledcWrite(PUMP_PWM_PIN, 0);
  sauce_is_on = false;
  Serial.println("Sauce OFF");
}

// ============================================
// SAFETY & VALIDATION
// ============================================

bool check_limits(float x, float y) {
  if (x < X_MIN || x > X_MAX || y < Y_MIN || y > Y_MAX) {
    Serial.printf("ERROR: Position out of bounds: X=%.2f Y=%.2f\n", x, y);
    return false;
  }
  return true;
}

void enter_error_state(String error) {
  current_state = STATE_ERROR;
  error_message = error;
  sauce_off();
  stepper_X.stop();
  stepper_Y.stop();
  Serial.println("ERROR: " + error);
  ws.textAll("err code=" + error);
}

// ============================================
// STATUS & TELEMETRY
// ============================================

void report_position() {
  String msg = "pos X:" + String(current_x_mm, 2) + " Y:" + String(current_y_mm, 2);
  ws.textAll(msg);
}

void send_status() {
  String status = "status state=" + state_to_string(current_state) + 
                  " q=" + String(queue_count) + 
                  " flow=" + String(current_flow) +
                  " sauce=" + String(sauce_is_on ? "ON" : "OFF");
  ws.textAll(status);
}

void send_telemetry() {
  String telem = "{\"pos\":{\"x\":" + String(current_x_mm, 2) + 
                 ",\"y\":" + String(current_y_mm, 2) + 
                 "},\"flow\":" + String(current_flow) + 
                 ",\"q\":" + String(queue_count) + 
                 ",\"state\":\"" + state_to_string(current_state) + "\"}";
  ws.textAll("telemetry " + telem);
}

String state_to_string(State state) {
  switch (state) {
    case STATE_BOOT: return "BOOT";
    case STATE_IDLE: return "IDLE";
    case STATE_HOMING: return "HOMING";
    case STATE_READY: return "READY";
    case STATE_PRINTING: return "PRINTING";
    case STATE_PAUSED: return "PAUSED";
    case STATE_CLEANING: return "CLEANING";
    case STATE_ERROR: return "ERROR";
    default: return "UNKNOWN";
  }
}

