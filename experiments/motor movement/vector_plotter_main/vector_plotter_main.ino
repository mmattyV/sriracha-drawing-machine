#include <WiFi.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <AccelStepper.h>
#include <ESP32Servo.h>
#include <vector>

// Define stepper motors
AccelStepper stepper_X(1, 2, 4);    // X-axis motor (Step pin 2, Direction pin 4)
AccelStepper stepper_Y(1, 5, 18);   // Y-axis motor (Step pin 5, Direction pin 18)

// Define servo motor for pen lift
Servo penServo;
const int SERVO_PIN = 19;          // Servo control pin
const int PEN_UP_ANGLE = 90;       // Servo angle when pen is up
const int PEN_DOWN_ANGLE = 45;     // Servo angle when pen is down
const int PEN_MOVE_DELAY = 200;    // Delay (ms) after pen movement

// Current pen state
bool currentPenDown = false;

// WiFi credentials
const char* ssid = "MAKERSPACE";
const char* password = "12345678";

// Server objects
AsyncWebServer server(80);
AsyncWebSocket ws("/ws");

// Drawing state variables
struct Point {
  float x;
  float y;
  bool penDown;
};

std::vector<Point> drawingPath;
int currentPathIndex = 0;
bool isDrawing = false;
bool newPathReceived = false;

// Scaling factors (adjust based on your machine's dimensions)
float STEPS_PER_MM_X = 10.0;  // Steps per millimeter for X axis
float STEPS_PER_MM_Y = 10.0;  // Steps per millimeter for Y axis
float CANVAS_WIDTH_MM = 600.0;   // Canvas width in mm
float CANVAS_HEIGHT_MM = 400.0;  // Canvas height in mm

// Current position
float currentX = 0;
float currentY = 0;

const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<title>Vector Drawing Plotter</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { font-family: Arial; margin: 20px; }
  .topnav { background-color: #333; color: white; padding: 15px; }
  .content { margin-top: 20px; }
  canvas { border: 2px solid #333; cursor: crosshair; display: block; margin: 10px 0; }
  button { padding: 10px 20px; margin: 5px; font-size: 16px; cursor: pointer; }
  .controls { margin: 15px 0; }
  #status { padding: 10px; margin: 10px 0; background: #f0f0f0; border-radius: 5px; }
  .file-input { margin: 10px 0; }
</style>
</head>
<body>
<div class="topnav">
  <h2>Vector Drawing Plotter Control</h2>
</div>
<div class="content">
  <div class="controls">
    <button onclick="clearCanvas()">Clear Canvas</button>
    <button onclick="sendPath()">Send to Plotter</button>
    <button onclick="homeMotors()">Home Motors</button>
    <button onclick="stopPlotter()">Stop</button>
  </div>
  
  <div class="file-input">
    <label>Upload SVG File: </label>
    <input type="file" id="svgFile" accept=".svg" onchange="loadSVG(event)">
  </div>
  
  <div class="controls">
    <label>
      <input type="checkbox" id="penToggle" checked> Pen Down Mode
    </label>
    <span style="margin-left: 20px;">Scale: </span>
    <input type="range" id="scaleSlider" min="10" max="200" value="100" oninput="updateScale(this.value)">
    <span id="scaleValue">100%</span>
  </div>
  
  <canvas id="canvas" width="800" height="600"></canvas>
  
  <div id="status">Status: Ready</div>
</div>

<script>
var gateway = `ws://${window.location.hostname}/ws`;
var websocket;
var canvas = document.getElementById('canvas');
var ctx = canvas.getContext('2d');
var isDrawing = false;
var lastX = 0;
var lastY = 0;
var pathData = [];
var scaleFactor = 1.0;

window.addEventListener('load', onload);

function onload(event) {
  initWebSocket();
  initCanvas();
}

function initWebSocket() {
  console.log('Trying to open a WebSocket connection...');
  websocket = new WebSocket(gateway);
  websocket.onopen = onOpen;
  websocket.onclose = onClose;
  websocket.onmessage = onMessage;
}

function onOpen(event) {
  console.log('Connection opened');
  updateStatus('Connected to plotter');
}

function onClose(event) {
  console.log('Connection closed');
  updateStatus('Disconnected - reconnecting...');
  setTimeout(initWebSocket, 2000);
}

function onMessage(event) {
  console.log('Message:', event.data);
  updateStatus(event.data);
}

function initCanvas() {
  ctx.strokeStyle = '#000';
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  
  // Mouse events for manual drawing
  canvas.addEventListener('mousedown', startDrawing);
  canvas.addEventListener('mousemove', draw);
  canvas.addEventListener('mouseup', stopDrawing);
  canvas.addEventListener('mouseout', stopDrawing);
}

function startDrawing(e) {
  if (!document.getElementById('penToggle').checked) return;
  isDrawing = true;
  const pos = getMousePos(canvas, e);
  lastX = pos.x;
  lastY = pos.y;
  pathData.push({x: pos.x, y: pos.y, penDown: true});
}

function draw(e) {
  if (!isDrawing) return;
  const pos = getMousePos(canvas, e);
  
  ctx.beginPath();
  ctx.moveTo(lastX, lastY);
  ctx.lineTo(pos.x, pos.y);
  ctx.stroke();
  
  pathData.push({x: pos.x, y: pos.y, penDown: true});
  lastX = pos.x;
  lastY = pos.y;
}

function stopDrawing() {
  if (isDrawing) {
    pathData.push({x: lastX, y: lastY, penDown: false});
  }
  isDrawing = false;
}

function getMousePos(canvas, evt) {
  var rect = canvas.getBoundingClientRect();
  return {
    x: evt.clientX - rect.left,
    y: evt.clientY - rect.top
  };
}

function clearCanvas() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  pathData = [];
  updateStatus('Canvas cleared');
}

function sendPath() {
  if (pathData.length === 0) {
    updateStatus('No path data to send');
    return;
  }
  
  // Convert path data to JSON and send via websocket
  const jsonData = JSON.stringify(pathData);
  websocket.send('PATH:' + jsonData);
  updateStatus('Sending path data (' + pathData.length + ' points)...');
}

function homeMotors() {
  websocket.send('HOME');
  updateStatus('Homing motors...');
}

function stopPlotter() {
  websocket.send('STOP');
  updateStatus('Stop command sent');
}

function updateScale(value) {
  scaleFactor = value / 100;
  document.getElementById('scaleValue').value = value + '%';
}

function updateStatus(message) {
  document.getElementById('status').innerHTML = 'Status: ' + message;
}

function loadSVG(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = function(e) {
    const svgText = e.target.result;
    parseSVG(svgText);
  };
  reader.readAsText(file);
}

function parseSVG(svgText) {
  // Parse SVG and extract path data
  const parser = new DOMParser();
  const svgDoc = parser.parseFromString(svgText, 'image/svg+xml');
  const paths = svgDoc.querySelectorAll('path, line, polyline, polygon, rect, circle, ellipse');
  
  clearCanvas();
  pathData = [];
  
  paths.forEach(element => {
    if (element.tagName === 'path') {
      parseSVGPath(element.getAttribute('d'));
    } else if (element.tagName === 'line') {
      parseSVGLine(element);
    } else if (element.tagName === 'rect') {
      parseSVGRect(element);
    } else if (element.tagName === 'circle') {
      parseSVGCircle(element);
    }
  });
  
  // Draw the parsed path on canvas
  redrawCanvas();
  updateStatus('SVG loaded: ' + pathData.length + ' points');
}

function parseSVGPath(d) {
  // Basic SVG path parser for M (move) and L (line) commands
  const commands = d.match(/[MLHVZmlhvz][^MLHVZmlhvz]*/g);
  let currentX = 0, currentY = 0;
  
  commands.forEach(cmd => {
    const type = cmd[0];
    const coords = cmd.slice(1).trim().split(/[\s,]+/).map(Number);
    
    if (type === 'M' || type === 'm') {
      currentX = type === 'M' ? coords[0] : currentX + coords[0];
      currentY = type === 'M' ? coords[1] : currentY + coords[1];
      pathData.push({x: currentX * scaleFactor, y: currentY * scaleFactor, penDown: false});
    } else if (type === 'L' || type === 'l') {
      for (let i = 0; i < coords.length; i += 2) {
        currentX = type === 'L' ? coords[i] : currentX + coords[i];
        currentY = type === 'L' ? coords[i+1] : currentY + coords[i+1];
        pathData.push({x: currentX * scaleFactor, y: currentY * scaleFactor, penDown: true});
      }
    }
  });
}

function parseSVGLine(element) {
  const x1 = parseFloat(element.getAttribute('x1'));
  const y1 = parseFloat(element.getAttribute('y1'));
  const x2 = parseFloat(element.getAttribute('x2'));
  const y2 = parseFloat(element.getAttribute('y2'));
  
  pathData.push({x: x1 * scaleFactor, y: y1 * scaleFactor, penDown: false});
  pathData.push({x: x2 * scaleFactor, y: y2 * scaleFactor, penDown: true});
}

function parseSVGRect(element) {
  const x = parseFloat(element.getAttribute('x') || 0);
  const y = parseFloat(element.getAttribute('y') || 0);
  const w = parseFloat(element.getAttribute('width'));
  const h = parseFloat(element.getAttribute('height'));
  
  pathData.push({x: x * scaleFactor, y: y * scaleFactor, penDown: false});
  pathData.push({x: (x+w) * scaleFactor, y: y * scaleFactor, penDown: true});
  pathData.push({x: (x+w) * scaleFactor, y: (y+h) * scaleFactor, penDown: true});
  pathData.push({x: x * scaleFactor, y: (y+h) * scaleFactor, penDown: true});
  pathData.push({x: x * scaleFactor, y: y * scaleFactor, penDown: true});
}

function parseSVGCircle(element) {
  const cx = parseFloat(element.getAttribute('cx'));
  const cy = parseFloat(element.getAttribute('cy'));
  const r = parseFloat(element.getAttribute('r'));
  const segments = 36;
  
  for (let i = 0; i <= segments; i++) {
    const angle = (i / segments) * 2 * Math.PI;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    pathData.push({x: x * scaleFactor, y: y * scaleFactor, penDown: i > 0});
  }
}

function redrawCanvas() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.beginPath();
  
  pathData.forEach((point, index) => {
    if (point.penDown && index > 0) {
      ctx.lineTo(point.x, point.y);
    } else {
      ctx.moveTo(point.x, point.y);
    }
  });
  
  ctx.stroke();
}
</script>
</body>
</html>
)rawliteral";

void initWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi ..");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print('.');
    delay(1000);
  }
  Serial.println();
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

void handleWebSocketMessage(void *arg, uint8_t *data, size_t len) {
  AwsFrameInfo *info = (AwsFrameInfo*)arg;
  if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT) {
    data[len] = 0;
    String message = (char*)data;
    
    Serial.println("Received: " + message);
    
    if (message.startsWith("PATH:")) {
      // Parse JSON path data
      String jsonData = message.substring(5);
      parsePathData(jsonData);
      newPathReceived = true;
      ws.textAll("Path received, starting draw...");
    } 
    else if (message == "HOME") {
      homeMotors();
      ws.textAll("Homing complete");
    }
    else if (message == "STOP") {
      stopDrawing();
      ws.textAll("Stopped");
    }
  }
}

void parsePathData(String jsonData) {
  // Clear existing path
  drawingPath.clear();
  currentPathIndex = 0;
  
  // Simple JSON parser for path data
  // Format: [{"x":100,"y":50,"penDown":true}, ...]
  int startPos = 0;
  
  while (startPos < jsonData.length()) {
    int objStart = jsonData.indexOf('{', startPos);
    if (objStart == -1) break;
    
    int objEnd = jsonData.indexOf('}', objStart);
    if (objEnd == -1) break;
    
    String obj = jsonData.substring(objStart, objEnd + 1);
    
    // Extract x value
    int xPos = obj.indexOf("\"x\":");
    int xStart = xPos + 4;
    int xEnd = obj.indexOf(',', xStart);
    if (xEnd == -1) xEnd = obj.indexOf('}', xStart);
    float x = obj.substring(xStart, xEnd).toFloat();
    
    // Extract y value
    int yPos = obj.indexOf("\"y\":");
    int yStart = yPos + 4;
    int yEnd = obj.indexOf(',', yStart);
    if (yEnd == -1) yEnd = obj.indexOf('}', yStart);
    float y = obj.substring(yStart, yEnd).toFloat();
    
    // Extract penDown value
    int penPos = obj.indexOf("\"penDown\":");
    bool penDown = false;
    if (penPos != -1) {
      penDown = obj.indexOf("true", penPos) != -1;
    }
    
    // Convert canvas coordinates to machine coordinates (steps)
    Point p;
    p.x = x * STEPS_PER_MM_X;  // Convert to steps
    p.y = y * STEPS_PER_MM_Y;
    p.penDown = penDown;
    
    drawingPath.push_back(p);
    
    startPos = objEnd + 1;
  }
  
  Serial.print("Parsed ");
  Serial.print(drawingPath.size());
  Serial.println(" points");
}

void homeMotors() {
  Serial.println("Homing motors...");
  
  // Lift pen first
  penServo.write(PEN_UP_ANGLE);
  currentPenDown = false;
  delay(PEN_MOVE_DELAY);
  
  // Reset stepper positions
  stepper_X.setCurrentPosition(0);
  stepper_Y.setCurrentPosition(0);
  currentX = 0;
  currentY = 0;
  isDrawing = false;
}

void stopDrawing() {
  isDrawing = false;
  stepper_X.stop();
  stepper_Y.stop();
  
  // Lift pen when stopping
  penServo.write(PEN_UP_ANGLE);
  currentPenDown = false;
  
  Serial.println("Drawing stopped");
}

void moveToPoint(Point &p) {
  long targetX = (long)p.x;
  long targetY = (long)p.y;
  
  // Control pen servo based on penDown state
  if (p.penDown && !currentPenDown) {
    // Lower pen
    penServo.write(PEN_DOWN_ANGLE);
    currentPenDown = true;
    delay(PEN_MOVE_DELAY);
  } else if (!p.penDown && currentPenDown) {
    // Raise pen
    penServo.write(PEN_UP_ANGLE);
    currentPenDown = false;
    delay(PEN_MOVE_DELAY);
  }
  
  // Move stepper motors
  stepper_X.moveTo(targetX);
  stepper_Y.moveTo(targetY);
  
  Serial.print("Moving to: X=");
  Serial.print(targetX);
  Serial.print(" Y=");
  Serial.print(targetY);
  Serial.print(" Pen=");
  Serial.println(p.penDown ? "DOWN" : "UP");
}

void onEvent(AsyncWebSocket *server, AsyncWebSocketClient *client, AwsEventType type,
             void *arg, uint8_t *data, size_t len) {
  switch (type) {
    case WS_EVT_CONNECT:
      Serial.printf("WebSocket client #%u connected from %s\n", client->id(),
                    client->remoteIP().toString().c_str());
      break;
    case WS_EVT_DISCONNECT:
      Serial.printf("WebSocket client #%u disconnected\n", client->id());
      break;
    case WS_EVT_DATA:
      handleWebSocketMessage(arg, data, len);
      break;
    case WS_EVT_PONG:
    case WS_EVT_ERROR:
      break;
  }
}

void initWebSocket() {
  ws.onEvent(onEvent);
  server.addHandler(&ws);
}

void setup() {
  Serial.begin(115200);
  
  initWiFi();
  initWebSocket();
  
  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
    request->send_P(200, "text/html", index_html);
  });
  
  server.begin();
  
  // Configure stepper motors
  stepper_X.setMaxSpeed(2000.0);
  stepper_X.setAcceleration(1000.0);
  stepper_Y.setMaxSpeed(2000.0);
  stepper_Y.setAcceleration(1000.0);
  
  // Configure servo motor
  penServo.attach(SERVO_PIN);
  penServo.write(PEN_UP_ANGLE);  // Start with pen up
  currentPenDown = false;
  
  Serial.println("Vector Plotter Ready");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  ws.cleanupClients();
  
  // If new path received, start drawing
  if (newPathReceived && !isDrawing) {
    isDrawing = true;
    currentPathIndex = 0;
    newPathReceived = false;
    
    if (drawingPath.size() > 0) {
      moveToPoint(drawingPath[0]);
    }
  }
  
  // Drawing state machine
  if (isDrawing && currentPathIndex < drawingPath.size()) {
    // Check if motors have reached target
    if (stepper_X.distanceToGo() == 0 && stepper_Y.distanceToGo() == 0) {
      currentPathIndex++;
      
      if (currentPathIndex < drawingPath.size()) {
        moveToPoint(drawingPath[currentPathIndex]);
      } else {
        isDrawing = false;
        // Lift pen when drawing complete
        penServo.write(PEN_UP_ANGLE);
        currentPenDown = false;
        Serial.println("Drawing complete!");
        ws.textAll("Drawing complete");
      }
    }
  }
  
  // Run stepper motors
  stepper_X.run();
  stepper_Y.run();
}
