# 🌶️ Sriracha Drawing Machine

A CNC-style drawing machine that uses sauce (sriracha, ketchup, etc.) to plot vector artwork onto food like pancakes and tortillas.

## 🎯 What It Does

1. **Generate Art** → AI creates SVG vector art from text prompts
2. **Convert to Commands** → SVG paths become motor movement instructions
3. **Stream to Hardware** → Commands sent over WiFi to ESP32
4. **Draw with Sauce** → Motors move, pump squeezes, art appears on food!

## 📁 Project Structure

```
sriracha-drawing-machine/
├── experiments/
│   ├── motor_movement/          # Motor control system
│   │   ├── firmware/            # ESP32 Arduino code
│   │   ├── config.py            # Hardware settings
│   │   ├── ssg_compiler.py      # SVG → movement commands
│   │   ├── ssg_sender.py        # WiFi streaming
│   │   └── calibrate.py         # Calibration tools
│   │
│   ├── simulate_drawing/        # Visualization tools
│   │   ├── ssg_simulator.py     # Preview drawings
│   │   └── test_svg_to_ssg.py   # Test pipeline
│   │
│   ├── image_generator.ipynb    # AI art generation (OpenAI)
│   ├── svgs/                    # Generated SVG files
│   └── pngs/                    # Preview images
│
└── DESIGN_DOC.md                # Technical specification
```

## 🔧 Hardware

- **Microcontroller**: Xiao ESP32C3
- **Motors**: 2 stepper motors (X and Y axes)
- **Endstops**: 2 limit switches for homing
- **Pump**: PWM-controlled sauce dispenser

## 🚀 Quick Start

### 1. Flash Firmware
```bash
# Open in Arduino IDE
experiments/motor_movement/firmware/sauce_plotter.ino

# Select board: XIAO_ESP32C3
# Update WiFi credentials and pin assignments
# Upload to ESP32
```

### 2. Configure Python
```bash
cd experiments/motor_movement
pip install -r requirements.txt

# Edit config.py with your ESP32's IP address
```

### 3. Test Connection
```bash
python test_motors_only.py
```

### 4. Generate & Draw
```bash
# Run the image generator notebook to create SVGs
# Then convert and draw:
python test_end_to_end.py ../svgs/best_result.svg
```

## 📖 Documentation

- **[DESIGN_DOC.md](DESIGN_DOC.md)** - Full technical specification
- **[motor_movement/README.md](experiments/motor_movement/README.md)** - Detailed setup guide

## 🛠️ Key Commands (SSG Protocol)

| Command | Description | Example |
|---------|-------------|---------|
| `G0` | Rapid move (no sauce) | `G0 X10 Y20` |
| `G1` | Draw move | `G1 X50 Y30 F600` |
| `G28` | Home machine | `G28` |
| `M3` | Sauce on | `M3 S75` (75% flow) |
| `M5` | Sauce off | `M5` |

## 📝 License

MIT
