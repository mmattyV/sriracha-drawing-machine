# Migration Summary - simulate_drawing

## ✅ What Was Done

Successfully migrated plotting/simulation code to `simulate_drawing/` and updated it to work with the new SSG-based motor control system.

---

## 📦 Files Moved

From `experiments/` to `experiments/simulate_drawing/`:

1. ✅ `plot_simulator.py` (kept for reference, deprecated)
2. ✅ `test_converter.py` (kept for reference, deprecated)
3. ✅ `test_output_instructions.json` (old format example)
4. ✅ `simulation_preview.png` (old output)
5. ✅ `simulation_sequence.png` (old output)

---

## 🆕 New Files Created

### Active Tools (Use These)

**`ssg_simulator.py`** - New SSG command simulator
- Replaces `plot_simulator.py`
- Works with SSG format instead of JSON
- Parses G-code-like commands (G0, G1, M3, M5, etc.)
- Same visualization output (preview + sequence)

**`test_svg_to_ssg.py`** - New complete test pipeline
- Replaces `test_converter.py`
- Uses `motor_movement/ssg_compiler.py`
- Validates against design constraints
- Automatically generates visualizations
- Integrates with new motor control system

### Documentation

**`README.md`** - Complete documentation (~400 lines)
- Tool descriptions
- Usage examples
- Visualization guide
- Troubleshooting
- Integration workflow

**`QUICK_START.md`** - Quick reference
- 3-step setup
- Common commands
- Visual guide

**`MIGRATION_SUMMARY.md`** - This file
- What changed and why

**`requirements.txt`** - Python dependencies
```
matplotlib>=3.5.0
numpy>=1.21.0
```

---

## 🔄 Key Changes

### Old System (Deprecated)
```python
# plot_simulator.py + test_converter.py
# Used JSON format
[
  {"x": 1000, "y": 500, "penDown": true},
  {"x": 1500, "y": 800, "penDown": true}
]
# Motor steps, not mm
# From shyla_motor_code/vector_converter.py
```

### New System (Active)
```ssg
# ssg_simulator.py + test_svg_to_ssg.py
# Uses SSG format
N1 G28
N2 M3 S60
N3 G1 X50.00 Y30.00 F600
N4 G1 X75.00 Y40.00 F600
# Direct mm coordinates
# From motor_movement/ssg_compiler.py
```

---

## 🎯 Why The Changes

### 1. Design Doc Compliance
The new system follows the SSG protocol specified in DESIGN_DOC.md:
- G-code-like command format
- Sequence numbers (N)
- Acknowledgements
- Variable sauce flow (M3 S0-100)
- Proper homing (G28)

### 2. Better Integration
Works seamlessly with motor_movement:
- Same coordinate system
- Same units (mm)
- Same configuration (config.py)
- Direct pipeline: SVG → SSG → ESP32

### 3. More Features
- Variable flow control (not just pen up/down)
- Proper motion modes (G0 rapid vs G1 linear)
- Feed rate control (F parameter)
- Homing support (G28)

---

## 📝 How to Use New System

### Step 1: Install Dependencies
```bash
cd experiments/simulate_drawing
pip install -r requirements.txt
```

### Step 2: Test SVG Conversion
```bash
# From image generator
python test_svg_to_ssg.py ../svgs/best_result.svg

# From motor_movement tests
python test_svg_to_ssg.py ../motor_movement/test_square.svg
```

### Step 3: Review Visualizations
Open generated PNG files:
- `simulation_preview.png` - Shows drawing paths
- `simulation_sequence.png` - Shows drawing order

### Step 4: If OK, Send to Hardware
```bash
cd ../motor_movement
python test_end_to_end.py ../svgs/best_result.svg
```

---

## 🔗 Integration Points

### With motor_movement
```
motor_movement/
├── ssg_compiler.py      ← Used by test_svg_to_ssg.py
├── config.py            ← Used for constraints
└── test_end_to_end.py   ← Next step after simulation
```

### With image_generator
```
image_generator.ipynb
    └─> ../svgs/best_result.svg
        └─> test_svg_to_ssg.py
            └─> Visualizations ✓
                └─> test_end_to_end.py
                    └─> ESP32 Hardware
```

---

## 🗂️ Directory Structure

```
simulate_drawing/
├── 🆕 ACTIVE TOOLS
│   ├── ssg_simulator.py           # SSG visualizer
│   ├── test_svg_to_ssg.py         # Complete pipeline test
│   └── requirements.txt           # Dependencies
│
├── 📚 DOCUMENTATION
│   ├── README.md                  # Full docs
│   ├── QUICK_START.md             # Quick reference
│   └── MIGRATION_SUMMARY.md       # This file
│
└── 📦 DEPRECATED (kept for reference)
    ├── plot_simulator.py          # Old JSON simulator
    ├── test_converter.py          # Old test script
    ├── test_output_instructions.json
    ├── simulation_preview.png     # Old outputs
    └── simulation_sequence.png
```

---

## ⚠️ Breaking Changes

### If You Were Using Old Scripts

**Old way:**
```bash
python plot_simulator.py test_output_instructions.json
```

**New way:**
```bash
# Generate SSG first
cd ../motor_movement
python ssg_compiler.py input.svg output.ssg

# Then simulate
cd ../simulate_drawing
python ssg_simulator.py ../motor_movement/output.ssg

# Or use integrated test:
python test_svg_to_ssg.py input.svg
```

### If You Have Old JSON Files

The old JSON format is no longer used. Convert to SSG:

**Option 1:** Regenerate from SVG
```bash
python test_svg_to_ssg.py original.svg
```

**Option 2:** Use old simulator (deprecated)
```bash
python plot_simulator.py old_instructions.json
```

---

## ✨ Benefits

1. **Standards Compliant**: Follows G-code conventions
2. **Hardware Ready**: Direct path to ESP32
3. **More Powerful**: Variable flow, feed rates, proper modes
4. **Better Workflow**: Integrated with motor_movement
5. **Future Proof**: Designed for production use

---

## 📊 Comparison

| Feature | Old System | New System |
|---------|------------|------------|
| Format | JSON | SSG (G-code-like) |
| Coordinates | Motor steps | Millimeters |
| Flow Control | Binary (on/off) | Variable (0-100%) |
| Feed Rate | Not specified | Configurable (F param) |
| Motion Modes | Implied | Explicit (G0/G1) |
| Homing | Not supported | G28 |
| Seq Numbers | No | Yes (N) |
| Hardware Ready | No | Yes |
| Design Doc | ❌ | ✅ |

---

## 🚀 Next Steps

1. ✅ Use new tools for all future work
2. ✅ Test with your existing SVGs
3. ✅ Integrate with image_generator workflow
4. ✅ Keep old files for reference if needed
5. ⚠️ Don't use old scripts for new projects

---

## 📞 Quick Reference

### Run Simulation
```bash
python test_svg_to_ssg.py <svg_file>
```

### Visualize SSG
```bash
python ssg_simulator.py <ssg_file>
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Get Help
```bash
python test_svg_to_ssg.py --help
python ssg_simulator.py --help
```

---

## ✅ Verification Checklist

- [x] Old files moved to simulate_drawing/
- [x] New SSG simulator created
- [x] New test pipeline created
- [x] Documentation written
- [x] Requirements file added
- [x] Scripts made executable
- [x] Integration with motor_movement verified
- [x] Works with image generator SVGs

---

**Migration complete!** 🎉

Use the new tools for all simulation and visualization going forward.

*Last updated: November 2025*

