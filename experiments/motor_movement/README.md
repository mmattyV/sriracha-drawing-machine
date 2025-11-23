# Sriracha Sketcher - Motor Control System

Complete motor control and firmware system for the Sriracha Sketcher sauce drawing machine.

**Design Doc**: Based on [DESIGN_DOC.md](../../DESIGN_DOC.md) - Full SSG protocol implementation

## 📁 Project Structure

```
motor_movement/
├── firmware/
│   └── sauce_plotter.ino      # ESP32 firmware (SSG protocol)
├── config.py                   # Hardware configuration
├── ssg_compiler.py             # SVG → SSG compiler
├── ssg_sender.py               # WebSocket streaming client
├── calibrate.py                # Interactive calibration tools
├── test_end_to_end.py          # Complete pipeline test
└── README.md                   # This file
```

## 🎯 Features

### Firmware (ESP32)
- ✅ **SSG Protocol**: Full G-code-like command set (G0, G1, G28, M3, M5, M114, M408)
- ✅ **Dual X-Motor**: Independent X1/X2 homing for gantry auto-squaring
- ✅ **PWM Sauce Control**: Variable flow rate (0-100%) with ramp-in/out
- ✅ **State Machine**: IDLE → HOMING → READY → PRINTING → PAUSED/ERROR
- ✅ **Sequence Numbers**: Every command tracked with acks
- ✅ **Sliding Window**: 64-command queue for smooth streaming
- ✅ **Safety Features**: Auto sauce-off on disconnect, endstops, watchdog
- ✅ **Telemetry**: Real-time position, queue, flow status

### Python Backend
- ✅ **SVG Parser**: Handles paths, curves, shapes (Bezier tessellation)
- ✅ **Path Optimization**: Douglas-Peucker simplification, nearest-neighbor ordering
- ✅ **SSG Compiler**: Converts SVG to SSG commands with validation
- ✅ **WebSocket Streamer**: Sliding window protocol with acks/retries
- ✅ **Calibration Tools**: Interactive steps/mm, flow, test patterns
- ✅ **End-to-End Testing**: Complete pipeline validation

---

## 🚀 Quick Start

### 1. Hardware Setup

**Required Hardware:**
- ESP32 dev board
- 2× Stepper motors for X axis (X1, X2)
- 1× Stepper motor for Y axis
- 2-3× Stepper drivers (TMC2209 recommended, A4988 budget option)
- Peristaltic pump or servo squeeze bottle for sauce
- 3× Limit switches (X1, X2, Y endstops)
- 12-24V power supply

**Wiring:**
```
ESP32 Pins:
  X1: Step=2,  Dir=4,  Endstop=25
  X2: Step=5,  Dir=18, Endstop=26
  Y:  Step=19, Dir=21, Endstop=27
  Pump PWM: Pin=23

Stepper Driver:
  STEP → ESP32 step pin
  DIR  → ESP32 dir pin
  EN   → GND (always enabled)
  VDD  → 3.3V
  GND  → GND
  VMOT → 12-24V
  A1, A2, B1, B2 → Motor coils

Endstops:
  NO (Normally Open) switches
  Connected between ESP32 pin and GND
  Internal pullup enabled in firmware
```

### 2. Flash ESP32 Firmware

**Prerequisites:**
- Arduino IDE with ESP32 support
- Required libraries:
  - WiFi (built-in)
  - AsyncTCP: https://github.com/me-no-dev/AsyncTCP
  - ESPAsyncWebServer: https://github.com/me-no-dev/ESPAsyncWebServer
  - AccelStepper: Available in Arduino Library Manager

**Steps:**
1. Open `firmware/sauce_plotter.ino` in Arduino IDE
2. Configure WiFi credentials (lines 38-39):
   ```cpp
   const char* WIFI_SSID = "YOUR_WIFI_SSID";
   const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
   ```
3. Review hardware configuration (lines 41-56)
4. Select board: **Tools → Board → ESP32 Dev Module**
5. Select port: **Tools → Port → /dev/ttyUSB0** (or your port)
6. Click **Upload**
7. Open Serial Monitor (115200 baud) to see IP address

### 3. Configure Python Backend

**Install Dependencies:**
```bash
pip install websockets
```

**Configure Settings:**

Edit `config.py`:
```python
# Set your ESP32's IP address (from Serial Monitor)
ESP32_IP = "192.168.1.105"

# Calibrate steps/mm (see Calibration section)
STEPS_PER_MM_X = 80.0
STEPS_PER_MM_Y = 80.0

# Adjust speeds if needed
FEED_RATE_RAPID = 3000  # mm/min (50 mm/s)
FEED_RATE_DRAW = 600    # mm/min (10 mm/s)
```

### 4. Test the System

**Option A: Dry Run (No Hardware)**
```bash
# Test SVG compilation only
python test_end_to_end.py path/to/drawing.svg --dry-run
```

**Option B: Full Hardware Test**
```bash
# Complete pipeline: SVG → SSG → ESP32
python test_end_to_end.py path/to/drawing.svg
```

This will:
1. Compile SVG to SSG
2. Connect to ESP32
3. Home the machine (G28)
4. Stream all commands
5. Report statistics

---

## 🔧 Calibration

Run the interactive calibration tool:

```bash
python calibrate.py
```

**Menu Options:**

### 1. Calibrate Steps/mm (X or Y)
Process:
1. Homes the machine
2. Commands 100mm movement
3. You measure actual distance
4. Calculates correct `STEPS_PER_MM`

**Formula:**
```
STEPS_PER_MM = (steps_per_rev × microstepping) / (belt_pitch × pulley_teeth)

Example with NEMA17 + GT2 belt:
  (200 steps/rev × 16 microstep) / (2mm pitch × 20 teeth) = 80 steps/mm
```

### 2. Test Square Pattern
Draws a 50mm square to verify:
- X/Y axes are calibrated correctly
- Corners are square (90°)
- No skew or distortion

### 3. Test Circle Pattern
Draws a 60mm diameter circle to verify:
- X and Y have same scaling
- No oval distortion
- Smooth curves

### 4. Flow Calibration Ladder
Draws 4 lines at different flow rates (20%, 40%, 60%, 80%).
Measure line widths to tune flow control.

---

## 📝 SSG Command Reference

### Motion Commands

**G0 - Rapid Move (sauce off)**
```
N123 G0 X50.00 Y30.00 F3000
```
- `X`, `Y`: Target position in mm
- `F`: Feed rate in mm/min

**G1 - Linear Move (drawing)**
```
N124 G1 X100.00 Y50.00 F600
```
- Same as G0 but for drawing with sauce on

**G28 - Home All Axes**
```
N1 G28
```
- Homes X1, X2 independently (auto-squaring)
- Then homes Y
- Sets position to (0, 0)

### Flow Commands

**M3 - Sauce On**
```
N125 M3 S60
```
- `S`: Flow duty cycle 0-100%

**M5 - Sauce Off**
```
N126 M5
```

### Status Commands

**M114 - Report Position**
```
N127 M114
```
Response: `pos X:50.00 Y:30.00`

**M408 - Report Status**
```
N128 M408
```
Response: `status state=PRINTING q=12 flow=60 sauce=ON`

### Responses

**Acknowledgement:**
```
ok N123
```

**Error:**
```
err N124 code=LIMIT_EXCEEDED
```

**Busy (queue full):**
```
busy q=64 state=PRINTING
```

**Telemetry (every 1 second):**
```
telemetry {"pos":{"x":50.0,"y":30.0},"flow":60,"q":12,"state":"PRINTING"}
```

---

## 🔬 Usage Examples

### Example 1: Compile SVG to SSG

```bash
python ssg_compiler.py drawing.svg output.ssg
```

Output:
```
Loading SVG: drawing.svg
Parsed 5 paths with 234 points
Normalizing paths...
Original bounds: 150.0mm × 120.0mm
After normalization: 5 paths, 234 points, 850.0mm total
Simplifying paths...
Simplified: 234 → 187 points (20.1% reduction)
Optimizing path order...
Compiling to SSG...
Compiled 195 SSG commands
Saved SSG to: output.ssg

==================================================
COMPILATION STATISTICS
==================================================
Paths: 5
SSG Commands: 195
Total Length: 850.0 mm
Rapid Moves: 8
Draw Moves: 182
Estimated Time: 95.0 sec (1.6 min)
```

### Example 2: Stream SSG File to ESP32

```bash
python ssg_sender.py output.ssg
```

Output:
```
Connecting to ws://192.168.1.105:80/ws...
Connected!
Loaded 195 commands from output.ssg

Streaming 195 commands...
Window size: 32
Ack timeout: 0.25s
============================================================
[████████████████████████████████████████] 100.0% (195/195)

Waiting for final acknowledgements...

============================================================
STREAMING STATISTICS
============================================================
Total sent: 195
Total acked: 195
Total retries: 0
Success rate: 100.0%
Elapsed time: 98.5s
Throughput: 2.0 commands/sec

✅ Streaming completed successfully!
```

### Example 3: Manual Command Sending

```python
import asyncio
from ssg_sender import SSGSender

async def manual_test():
    sender = SSGSender()
    await sender.connect()
    
    # Home
    await sender.send_home()
    await asyncio.sleep(15)
    
    # Draw a small square
    commands = [
        "N1 M3 S60",
        "N2 G1 X10.00 Y0.00 F600",
        "N3 G1 X10.00 Y10.00 F600",
        "N4 G1 X0.00 Y10.00 F600",
        "N5 G1 X0.00 Y0.00 F600",
        "N6 M5"
    ]
    
    await sender.stream_commands(commands)
    await sender.disconnect()

asyncio.run(manual_test())
```

---

## 🐛 Troubleshooting

### Motors Not Moving

**Symptom:** Commands accepted but motors don't move

**Solutions:**
1. Check power supply voltage (12-24V)
2. Verify stepper driver EN pin is grounded
3. Check motor wiring (coil pairs: A1-A2, B1-B2)
4. Increase driver current potentiometer
5. Test with slow speeds first (`FEED_RATE_DRAW = 300`)

### Wrong Movement Direction

**Symptom:** Motors move backward or gantry racks

**Solutions:**
1. Swap motor coil pairs (A↔B)
2. Or invert direction in firmware:
   ```cpp
   stepper_X1.setPinsInverted(true, false, false);
   ```

### Position Drift / Skipped Steps

**Symptom:** Drawing position drifts over time

**Solutions:**
1. Reduce speed: `FEED_RATE_DRAW = 300`
2. Reduce acceleration: `ACCELERATION = 400`
3. Increase motor driver current
4. Check belt tension (should be snug, not loose)
5. Check for mechanical binding

### WiFi Connection Failed

**Symptom:** ESP32 stuck at "Connecting to WiFi..."

**Solutions:**
1. Verify SSID and password (case-sensitive!)
2. Check 2.4GHz WiFi (ESP32 doesn't support 5GHz)
3. Move ESP32 closer to router
4. Check router MAC filter/security settings

### Sauce Not Flowing

**Symptom:** Motors work but no sauce

**Solutions:**
1. Verify pump PWM pin connection (Pin 23)
2. Check pump power supply
3. Increase flow rate: `SAUCE_FLOW_DEFAULT = 80`
4. Test pump directly: `ledcWrite(0, 200);` in firmware
5. Check pump tubing for clogs

### "err code=LIMIT_EXCEEDED"

**Symptom:** Commands rejected with LIMIT error

**Solutions:**
1. Check soft limits in config.py:
   ```python
   X_MIN = -120.0
   X_MAX = 120.0
   Y_MIN = -120.0
   Y_MAX = 120.0
   ```
2. Home machine first (G28)
3. Verify drawing is centered and scaled correctly

### Heartbeat Timeout

**Symptom:** "WARNING: Heartbeat timeout - pausing"

**Solutions:**
1. Check WiFi stability (weak signal?)
2. Reduce `WINDOW_SIZE` in config.py: `WINDOW_SIZE = 16`
3. Increase timeout in firmware: `HEARTBEAT_TIMEOUT_MS = 5000`
4. Check computer not going to sleep during streaming

---

## 🔒 Safety Features

### Automatic Safety Triggers

1. **Disconnect Safety**: Sauce automatically turns off if WebSocket disconnects
2. **Heartbeat Watchdog**: Pauses and turns sauce off if no commands for 3 seconds
3. **Endstop Protection**: Stops motion if endstop hit during print
4. **Soft Limits**: Rejects commands outside defined workspace
5. **Error State**: Requires homing after any error condition

### Manual Controls

**Emergency Stop:**
- Power off ESP32 or stepper drivers
- Sauce will stop immediately

**Pause Printing:**
```python
await sender.send_pause()  # Turns sauce off
```

**Resume After Pause:**
- Send M3 command to turn sauce back on
- Continue sending motion commands

---

## 📊 Performance Tuning

### Speed Optimization

**For faster (but less precise) drawing:**
```python
# config.py
FEED_RATE_DRAW = 1200  # 20 mm/s
ACCELERATION = 1000
```

**For higher quality (slower):**
```python
# config.py
FEED_RATE_DRAW = 360   # 6 mm/s
ACCELERATION = 600
BEZIER_MAX_ERROR_MM = 0.1  # More curve points
```

### Path Optimization

**Reduce command count:**
```python
# config.py
SIMPLIFY_EPSILON_MM = 0.3  # More aggressive simplification
MIN_SEGMENT_LENGTH_MM = 0.5  # Filter tiny segments
```

**Trade-offs:**
- Higher epsilon = fewer points but less detail
- Longer min segment = faster but may lose small features

### Flow Tuning

**Adjust for sauce viscosity:**
```python
# config.py
SAUCE_FLOW_DEFAULT = 70    # Increase for thicker sauce
SAUCE_ON_DWELL_MS = 150    # Longer dwell for slow-starting pump
FLOW_RAMP_TIME_MS = 120    # Slower ramp for smoother lines
```

---

## 🧪 Testing & Validation

### Unit Tests

Test individual components:

```bash
# Test SVG parsing only
python -c "from ssg_compiler import SSGCompiler; c = SSGCompiler(); c.load_svg('test.svg'); print(f'{len(c.paths)} paths loaded')"

# Test WebSocket connection only
python -c "import asyncio; from ssg_sender import SSGSender; asyncio.run(SSGSender().connect())"
```

### Integration Tests

```bash
# Dry run (compilation only)
python test_end_to_end.py test_pattern.svg --dry-run

# Full hardware test
python test_end_to_end.py test_pattern.svg
```

### Acceptance Tests (MVP)

From Design Doc Section 12:
- ✅ Draw recognizable shape in <3 min
- ✅ Corner overshoot <0.5mm at 10mm/s
- ✅ Sauce on/off within 100ms

---

## 📚 Additional Resources

### Design Document
- [../../DESIGN_DOC.md](../../DESIGN_DOC.md) - Complete system architecture

### Hardware Specifications
- ESP32: 240MHz dual-core, WiFi, 520KB RAM
- TMC2209: Silent stepper driver, 256 microstep, UART config
- NEMA 17: 1.8° step angle, 200 steps/rev, 40-60 N·cm torque
- GT2 Belt: 2mm pitch, 6mm width, fiberglass core

### Useful Links
- AccelStepper library: http://www.airspayce.com/mikem/arduino/AccelStepper/
- AsyncWebServer: https://github.com/me-no-dev/ESPAsyncWebServer
- SVG Path Spec: https://www.w3.org/TR/SVG/paths.html

---

## 🤝 Contributing

This is a complete implementation following the design doc. Key areas for future enhancement:

1. **Vision Feedback** (Design Doc v2): Camera alignment for precise plate positioning
2. **Advanced Flow Control**: Dynamic flow adjustment based on speed
3. **Multi-Tool Support**: Multiple sauce colors/types
4. **Web UI**: Browser-based control panel
5. **OTA Updates**: Wireless firmware updates

---

## 📄 License

This project is part of the Sriracha Sketcher system. See main repository for license.

---

## 💡 Tips & Best Practices

### For Best Results

1. **Always home first**: Run G28 before every print
2. **Test patterns**: Use calibration squares/circles to validate setup
3. **Start slow**: Begin with `FEED_RATE_DRAW = 300`, increase gradually
4. **Clean regularly**: Purge pump between prints to prevent clogs
5. **Backup configs**: Save working config.py values
6. **Monitor first print**: Watch initial layers for issues

### Common Mistakes to Avoid

- ❌ Not homing before print (positions will be wrong)
- ❌ Setting speeds too high (causes skipped steps)
- ❌ Forgetting to update `ESP32_IP` in config
- ❌ Using wrong microstepping in steps/mm calculation
- ❌ Not centering drawings (goes off plate edge)
- ❌ Ignoring compiler warnings about size constraints

### Pro Tips

- 🎯 Use `--dry-run` to validate SVGs before printing
- 🎯 Keep sauce warm (30-40°C) for consistent flow
- 🎯 Add `M5` (sauce off) before long rapid moves
- 🎯 Run flow calibration ladder weekly
- 🎯 Save successful `.ssg` files for reprinting
- 🎯 Use SerialMonitor during development to see real-time logs

---

**Ready to plot with sauce!** 🌶️✨

For questions or issues, check the troubleshooting section or review the Design Doc.

