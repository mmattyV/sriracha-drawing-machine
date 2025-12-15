# Sriracha Sketcher - Quick Reference Card

Essential commands and workflows for daily use.

---

## 🚀 Quick Start

### 1. Connect & Test
```bash
# Test connection
python -c "import asyncio; from ssg_sender import SSGSender; asyncio.run(SSGSender().connect())"

# Run calibration
python calibrate.py
```

### 2. Draw from SVG
```bash
# Dry run (test compilation only)
python test_end_to_end.py drawing.svg --dry-run

# Full draw (with hardware)
python test_end_to_end.py drawing.svg
```

---

## 📝 Common Commands

### Compile SVG to SSG
```bash
python ssg_compiler.py input.svg output.ssg
```

### Stream SSG File
```bash
python ssg_sender.py output.ssg
```

### With Custom IP
```bash
python ssg_sender.py output.ssg --ip 192.168.1.100
```

### Home Before Streaming
```bash
python ssg_sender.py output.ssg --home-first
```

---

## 🔧 SSG Commands (Manual)

### Essential Commands
| Command | Description | Example |
|---------|-------------|---------|
| `G28` | Home all axes | `N1 G28` |
| `G0` | Rapid move (sauce off) | `N2 G0 X50 Y30 F3000` |
| `G1` | Linear move (drawing) | `N3 G1 X100 Y50 F600` |
| `M3` | Sauce on | `N4 M3 S60` |
| `M5` | Sauce off | `N5 M5` |
| `M114` | Report position | `N6 M114` |
| `M408` | Report status | `N7 M408` |

### Parameter Reference
- `X`, `Y`: Position in mm
- `F`: Feed rate in mm/min (600 = 10mm/s, 3000 = 50mm/s)
- `S`: Flow duty 0-100%
- `N`: Sequence number (required for acks)

---

## 🎯 Calibration Checklist

### Steps/mm Calibration
1. Run: `python calibrate.py` → option 1 (X) or 2 (Y)
2. Measure actual movement
3. Update `config.py`:
   ```python
   STEPS_PER_MM_X = 82.5  # Your value
   STEPS_PER_MM_Y = 81.0  # Your value
   ```

### Flow Calibration
1. Run: `python calibrate.py` → option 5
2. Measure line widths
3. Adjust `SAUCE_FLOW_DEFAULT` in `config.py`

### Test Patterns
```bash
# 50mm square
python calibrate.py → option 3

# Circle
python calibrate.py → option 4

# Provided test files
python test_end_to_end.py test_square.svg
python test_end_to_end.py test_star.svg
```

---

## 🔍 Troubleshooting Quick Fixes

### Can't Connect
```bash
# Check ESP32 IP
ping 192.168.1.105

# Update config
nano config.py  # Change ESP32_IP
```

### Motors Not Moving
```python
# In config.py, reduce speeds:
FEED_RATE_DRAW = 300      # Slower drawing
ACCELERATION = 400         # Lower acceleration
```

### Wrong Direction
Swap motor wires or in firmware:
```cpp
stepper_X1.setPinsInverted(true, false, false);
```

### Drawing Wrong Size
Recalibrate steps/mm:
```bash
python calibrate.py → option 1, 2
```

### Sauce Won't Flow
```python
# In config.py, increase flow:
SAUCE_FLOW_DEFAULT = 80   # Higher duty
```

---

## 📊 File Structure

```
motor_movement/
├── firmware/
│   └── sauce_plotter.ino       # Flash to ESP32
├── config.py                    # ← EDIT THIS
├── ssg_compiler.py              # SVG → SSG
├── ssg_sender.py                # Send to ESP32
├── calibrate.py                 # Interactive tools
├── test_end_to_end.py           # Full pipeline test
├── test_square.svg              # Test pattern
├── test_star.svg                # Test pattern
├── README.md                    # Full docs
└── SETUP_GUIDE.md               # Hardware setup
```

---

## ⚙️ Configuration Values

### Edit `config.py` for your hardware

**Network:**
```python
ESP32_IP = "192.168.1.105"  # ← Your ESP32 IP
```

**Kinematics (after calibration):**
```python
STEPS_PER_MM_X = 80.0       # ← Calibrate
STEPS_PER_MM_Y = 80.0       # ← Calibrate
```

**Speeds (tune for your motors):**
```python
FEED_RATE_DRAW = 600        # Drawing: 10 mm/s
FEED_RATE_RAPID = 3000      # Rapid: 50 mm/s
ACCELERATION = 800          # mm/s²
```

**Flow (adjust for sauce):**
```python
SAUCE_FLOW_DEFAULT = 60     # 0-100%
SAUCE_ON_DWELL_MS = 100     # Delay after on
SAUCE_OFF_DWELL_MS = 50     # Delay after off
```

**Workspace:**
```python
CANVAS_WIDTH_MM = 220.0     # Your plate size
CANVAS_HEIGHT_MM = 220.0
PLATE_RADIUS_MM = 110.0     # Half diameter
```

---

## 🎨 Workflow Examples

### Example 1: Quick Test Draw
```bash
# 1. Ensure ESP32 powered and connected
# 2. Test simple pattern
python test_end_to_end.py test_square.svg

# Expected output:
# ✅ SVG compiled
# ✅ Connected to ESP32
# ✅ Homing complete
# [████████] 100%
# ✅ Drawing complete
```

### Example 2: Custom Drawing
```bash
# 1. Get SVG from image generator or Inkscape
# 2. Test compilation first
python test_end_to_end.py my_drawing.svg --dry-run

# 3. Check warnings, adjust if needed
# 4. Full run
python test_end_to_end.py my_drawing.svg
```

### Example 3: Programmatic Control
```python
import asyncio
from ssg_sender import SSGSender

async def draw_square():
    sender = SSGSender()
    await sender.connect()
    await sender.send_home()
    await asyncio.sleep(15)
    
    commands = [
        "N1 M3 S60",  # Sauce on
        "N2 G1 X25 Y0 F600",
        "N3 G1 X25 Y25 F600",
        "N4 G1 X0 Y25 F600",
        "N5 G1 X0 Y0 F600",
        "N6 M5"  # Sauce off
    ]
    
    await sender.stream_commands(commands)
    await sender.disconnect()

asyncio.run(draw_square())
```

---

## 🚨 Safety Reminders

- ✅ Always home (G28) before drawing
- ✅ Test new patterns with dry-run first
- ✅ Keep workspace clear
- ✅ Sauce turns off automatically on disconnect
- ✅ E-Stop = power off ESP32 or drivers
- ✅ Clean pump regularly

---

## 📞 Emergency Commands

### Stop Everything
```bash
# Power off ESP32 or stepper drivers
# Sauce will stop immediately
```

### Pause & Sauce Off
```python
import asyncio
from ssg_sender import SSGSender

async def emergency_stop():
    sender = SSGSender()
    await sender.connect()
    await sender.send_pause()  # Turns sauce off
    await sender.disconnect()

asyncio.run(emergency_stop())
```

### Reset After Error
1. Power cycle ESP32 (or press RESET button)
2. Wait for WiFi connection
3. Send G28 (home) command
4. Resume normal operation

---

## 📏 Units Reference

| Parameter | Unit | Example |
|-----------|------|---------|
| Position (X, Y) | mm | `X50.00` = 50mm |
| Feed rate (F) | mm/min | `F600` = 10mm/s |
| Acceleration | mm/s² | `800` = 0.8 m/s² |
| Flow duty (S) | % | `S60` = 60% PWM |
| Steps | steps | 80 steps/mm × 50mm = 4000 steps |

---

## 🔗 Quick Links

- **Full Documentation:** README.md
- **Hardware Setup:** SETUP_GUIDE.md
- **Implementation Details:** PROJECT_SUMMARY.md
- **Design Specification:** ../../DESIGN_DOC.md

---

**Keep this card handy for daily use!** 🌶️✨

*Last updated: November 2025*


