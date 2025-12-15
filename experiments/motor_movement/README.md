# Motor Movement System

ESP32 firmware and Python tools for the Sriracha Sketcher.

## 📁 Files

| File | Description |
|------|-------------|
| `firmware/sauce_plotter.ino` | ESP32 firmware (flash this) |
| `config.py` | Settings (IP, speeds, dimensions) |
| `ssg_compiler.py` | SVG → SSG command converter |
| `ssg_sender.py` | WebSocket streaming client |
| `calibrate.py` | Motor/flow calibration tools |
| `test_end_to_end.py` | Full pipeline test |
| `test_motors_only.py` | Quick motor test |

## 🔧 Hardware Setup (Xiao ESP32C3)

### Pin Configuration

Edit `sauce_plotter.ino` to match your wiring:

```cpp
// Endstops
#define X_ENDSTOP_PIN  20  // D7
#define Y_ENDSTOP_PIN  8   // D8

// Motors (Step, Direction)
#define X_STEP_PIN  2   // D0
#define X_DIR_PIN   3   // D1
#define Y_STEP_PIN  4   // D2
#define Y_DIR_PIN   5   // D3

// Pump
#define PUMP_PWM_PIN  21  // D6
```

### WiFi Configuration

```cpp
const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASSWORD = "YOUR_PASSWORD";
```

## 🚀 Usage

### 1. Flash Firmware

1. Open `firmware/sauce_plotter.ino` in Arduino IDE
2. Select board: **XIAO_ESP32C3**
3. Update WiFi credentials and pins
4. Upload

### 2. Configure Python

```bash
pip install websockets matplotlib numpy svgpathtools

# Edit config.py - set ESP32_IP to match Serial Monitor output
```

### 3. Test Motors

```bash
python test_motors_only.py
```

Watch Serial Monitor for:
- `WebSocket client connected`
- Position telemetry updates
- `Sauce ON/OFF` messages

### 4. Draw an SVG

```bash
# Test with existing SVG
python test_end_to_end.py ../svgs/best_result.svg

# Or use any SVG file
python test_end_to_end.py my_drawing.svg
```

## 🧪 Testing Mode

For development without endstops, enable in firmware:

```cpp
#define TESTING_MODE true  // Bypasses homing
```

Set `false` for production with real endstops.

## 📊 Calibration

```bash
python calibrate.py
```

Options:
1. Test X/Y movement
2. Calibrate steps/mm
3. Draw test patterns (square, circle)
4. Calibrate sauce flow

## 🔍 Troubleshooting

| Problem | Solution |
|---------|----------|
| Can't connect | Check IP in config.py matches Serial Monitor |
| Motors don't move | Verify pin assignments match wiring |
| Wrong direction | Swap motor wires or invert direction pin |
| No Serial output | Wait for USB CDC ready (Xiao ESP32C3) |

## 📖 More Info

See [DESIGN_DOC.md](../../DESIGN_DOC.md) for full technical specification.
