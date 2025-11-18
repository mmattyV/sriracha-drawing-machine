# Vector Drawing Plotter

A complete system to convert vector images (SVG) into stepper motor movements for a drawing machine with X and Y axis control.

## Features

- **Web-based Interface**: Upload and preview SVG files, draw manually, or load vector graphics
- **SVG Support**: Handles paths, lines, rectangles, circles, ellipses, and polygons
- **Real-time Control**: WebSocket-based communication for responsive control
- **Path Visualization**: Preview drawings before sending to the plotter
- **Manual Drawing**: Draw directly on the canvas
- **Scale Control**: Adjust drawing size with a slider
- **Motor Coordination**: Synchronized X1, X2, and Y axis stepper motors

## Hardware Requirements

- ESP32 Development Board
- 3x Stepper Motors (2 for X-axis, 1 for Y-axis)
- 3x Stepper Motor Drivers (compatible with step/direction control)
- Power Supply (appropriate for your stepper motors)
- Optional: Servo or solenoid for pen lift mechanism

### Default Pin Configuration

```
Stepper X1: Step=2,  Direction=4
Stepper X2: Step=5,  Direction=18
Stepper Y:  Step=19, Direction=21
```

## Software Requirements

- Arduino IDE with ESP32 board support
- Required Arduino Libraries:
  - `WiFi.h` (included with ESP32)
  - `AsyncTCP` (https://github.com/me-no-dev/AsyncTCP)
  - `ESPAsyncWebServer` (https://github.com/me-no-dev/ESPAsyncWebServer)
  - `AccelStepper` (https://www.airspayce.com/mikem/arduino/AccelStepper/)

### Installing Libraries

1. Open Arduino IDE
2. Go to Sketch -> Include Library -> Manage Libraries
3. Search and install:
   - AccelStepper by Mike McCauley
4. Manually install AsyncTCP and ESPAsyncWebServer:
   - Download from GitHub links above
   - Extract to Arduino/libraries folder

## Setup Instructions

### 1. Configure WiFi

Edit the WiFi credentials in `vector_plotter_main.ino`:

```cpp
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
```

### 2. Calibrate Machine Parameters

Adjust these values based on your machine's specifications:

```cpp
float STEPS_PER_MM_X = 10.0;  // Steps per millimeter for X axis
float STEPS_PER_MM_Y = 10.0;  // Steps per millimeter for Y axis
float CANVAS_WIDTH_MM = 600.0;   // Canvas width in mm
float CANVAS_HEIGHT_MM = 400.0;  // Canvas height in mm
```

To calculate STEPS_PER_MM:
```
STEPS_PER_MM = (motor_steps_per_rev × microstepping) / (belt_pitch × pulley_teeth)

Example: 200 steps/rev × 16 microsteps / (2mm pitch × 20 teeth) = 80 steps/mm
```

### 3. Configure Motor Speeds

Adjust acceleration and max speed based on your motors:

```cpp
stepper_X1.setMaxSpeed(2000.0);      // Steps per second
stepper_X1.setAcceleration(1000.0);  // Steps per second²
```

### 4. Upload to ESP32

1. Connect ESP32 via USB
2. Select correct board (Tools -> Board -> ESP32 Dev Module)
3. Select correct port (Tools -> Port)
4. Click Upload
5. Open Serial Monitor (115200 baud) to see IP address

## Using the Plotter

### Web Interface

1. Connect to the same WiFi network as ESP32
2. Open browser and navigate to the ESP32's IP address (shown in Serial Monitor)
3. The web interface will load

### Drawing Methods

#### Method 1: Manual Drawing
1. Check "Pen Down Mode"
2. Click and drag on the canvas to draw
3. Click "Send to Plotter" when ready

#### Method 2: Upload SVG
1. Click "Choose File" and select an SVG file
2. Adjust scale slider if needed (10% - 200%)
3. Preview appears on canvas
4. Click "Send to Plotter"

#### Method 3: Use Python Converter (Advanced)
```bash
# Convert SVG to JSON format
python vector_converter.py input.svg 1.0 json

# Convert SVG to G-code
python vector_converter.py input.svg 1.0 gcode
```

### Control Buttons

- **Clear Canvas**: Erase the current drawing
- **Send to Plotter**: Start drawing the current path
- **Home Motors**: Reset all motors to origin (0,0)
- **Stop**: Emergency stop all motor movement

## Python Converter Utility

The `vector_converter.py` script provides advanced SVG processing:

### Features
- Parses complex SVG paths including Bezier curves
- Converts curves to linear segments
- Handles all SVG drawing elements
- Exports to JSON or G-code format

### Usage Examples

```bash
# Basic conversion
python vector_converter.py drawing.svg

# With custom scale
python vector_converter.py drawing.svg 0.5

# Generate G-code
python vector_converter.py drawing.svg 1.0 gcode

# Half size G-code
python vector_converter.py drawing.svg 0.5 gcode
```

### Supported SVG Elements
- `<path>` - All commands (M, L, H, V, C, S, Q, T, A, Z)
- `<line>` - Straight lines
- `<rect>` - Rectangles
- `<circle>` - Circles (converted to 36 segments)
- `<ellipse>` - Ellipses (converted to 36 segments)
- `<polyline>` - Connected line segments
- `<polygon>` - Closed polylines

## Coordinate System

```
(0,0) -------- X+ -------→
  |
  |
  Y+
  |
  ↓
  
Canvas coordinates are converted to motor steps:
motor_steps_X = canvas_x × STEPS_PER_MM_X
motor_steps_Y = canvas_y × STEPS_PER_MM_Y
```

## Communication Protocol

### WebSocket Messages

**From Browser to ESP32:**
- `PATH:<json_data>` - Send drawing path
  ```json
  [
    {"x": 100, "y": 50, "penDown": false},
    {"x": 200, "y": 150, "penDown": true}
  ]
  ```
- `HOME` - Home all motors
- `STOP` - Emergency stop

**From ESP32 to Browser:**
- Status messages (text)
- Drawing progress updates

## Troubleshooting

### Motors not moving
- Check power supply
- Verify pin connections
- Check motor driver enable pins
- Adjust acceleration/speed values

### Drawing too fast/slow
- Adjust `setMaxSpeed()` and `setAcceleration()`
- Typical ranges:
  - MaxSpeed: 500-3000 steps/second
  - Acceleration: 200-2000 steps/second²

### Drawing wrong size
- Recalculate and update `STEPS_PER_MM_X` and `STEPS_PER_MM_Y`
- Verify belt/pulley specifications
- Check microstepping settings on drivers

### WiFi won't connect
- Verify SSID and password
- Check 2.4GHz WiFi (ESP32 doesn't support 5GHz)
- Move ESP32 closer to router

### Web page won't load
- Verify ESP32 IP address in Serial Monitor
- Check firewall settings
- Try different browser

### SVG not parsing correctly
- Ensure SVG uses standard elements
- Complex transforms may need simplification
- Try converting SVG to paths in Inkscape first

## Advanced Customization

### Adding Pen Lift Mechanism

Add servo control for pen up/down:

```cpp
#include <ESP32Servo.h>

Servo penServo;
const int SERVO_PIN = 23;
const int PEN_UP_ANGLE = 90;
const int PEN_DOWN_ANGLE = 45;

void setup() {
  // ... existing setup ...
  penServo.attach(SERVO_PIN);
  penServo.write(PEN_UP_ANGLE);
}

void moveToPoint(Point &p) {
  // Set pen position
  if (p.penDown) {
    penServo.write(PEN_DOWN_ANGLE);
  } else {
    penServo.write(PEN_UP_ANGLE);
  }
  delay(200); // Wait for servo to move
  
  // ... existing motor commands ...
}
```

### Multi-Color Plotting

Track color changes and pause for manual pen changes:

```cpp
struct Point {
  float x;
  float y;
  bool penDown;
  int color;  // 0=black, 1=red, 2=blue, etc.
};

// In moveToPoint():
if (p.color != currentColor) {
  // Pause and notify user
  ws.textAll("Change pen to color " + String(p.color));
  currentColor = p.color;
  // Wait for user confirmation...
}
```

### Limit Switches / Endstops

Add home detection with limit switches:

```cpp
const int X_ENDSTOP_PIN = 25;
const int Y_ENDSTOP_PIN = 26;

void homeMotors() {
  pinMode(X_ENDSTOP_PIN, INPUT_PULLUP);
  pinMode(Y_ENDSTOP_PIN, INPUT_PULLUP);
  
  // Move until endstop triggered
  while (digitalRead(X_ENDSTOP_PIN) == HIGH) {
    stepper_X1.move(-1);
    stepper_X2.move(-1);
    stepper_X1.run();
    stepper_X2.run();
  }
  
  stepper_X1.setCurrentPosition(0);
  stepper_X2.setCurrentPosition(0);
  
  // Repeat for Y axis...
}
```

## Example SVG Files

Create test drawings in Inkscape or any vector editor. Keep these guidelines:
- Simple paths work best for initial testing
- Avoid very fine details (< 1mm)
- Use single-line strokes, not filled shapes
- Convert text to paths before export

## Performance Tips

1. **Optimize Path Data**: Remove duplicate points before sending
2. **Batch Processing**: For complex drawings, process in chunks
3. **Speed vs. Accuracy**: Lower speeds = better accuracy, especially around corners
4. **Acceleration Tuning**: Start low and gradually increase until you see quality degradation

## License

This project is provided as-is for educational and personal use.

## Contributing

Feel free to fork and modify for your specific hardware configuration.

## Credits

- Built on ESP32 platform
- Uses AccelStepper library by Mike McCauley
- AsyncWebServer for ESP32 by me-no-dev
