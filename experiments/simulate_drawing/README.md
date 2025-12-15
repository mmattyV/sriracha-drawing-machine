# Simulate Drawing - SSG Visualization Tools

Tools for simulating and visualizing SSG (Sauce Simple G-code) commands before sending to hardware.

## 📁 Files

### Core Tools

**`ssg_simulator.py`** - SSG command simulator and visualizer
- Parses SSG (.ssg) files
- Simulates command execution
- Generates matplotlib visualizations
- Shows drawing paths (G1) vs. rapid moves (G0)
- Time-sequence color gradient view

**`test_svg_to_ssg.py`** - Complete SVG → SSG test pipeline
- Compiles SVG to SSG using motor_movement/ssg_compiler.py
- Validates against design constraints
- Generates visualizations automatically
- Shows command preview

### Legacy Files (for reference)

**`plot_simulator.py`** - Old JSON-based simulator (deprecated)
- Works with old vector_converter.py format
- Kept for reference

**`test_converter.py`** - Old test script (deprecated)
- Uses old shyla_motor_code system
- Kept for reference

---

## 🚀 Quick Start

### Install Dependencies
```bash
pip install matplotlib numpy
```

### Test SVG → SSG Pipeline

**From image generator output:**
```bash
python test_svg_to_ssg.py ../svgs/best_result.svg
```

**From motor_movement test patterns:**
```bash
python test_svg_to_ssg.py ../motor_movement/test_square.svg
python test_svg_to_ssg.py ../motor_movement/test_star.svg
```

**Output:**
- `<name>_output.ssg` - SSG command file
- `simulation_preview.png` - Standard view (red=drawing, blue=travel)
- `simulation_sequence.png` - Time-sequence gradient

### Simulate Existing SSG File

```bash
python ssg_simulator.py ../motor_movement/test_square_output.ssg
```

---

## 📊 What Gets Visualized

### Standard View (simulation_preview.png)
- **Red solid lines**: Drawing paths (G1 commands with sauce on)
- **Blue dashed lines**: Rapid travel (G0 commands, sauce off)
- **Green circle**: Start position
- **Black circle**: End position
- **Gray dotted circle**: Plate boundary (220mm diameter)
- **Light gray circle**: Safe drawing area (200mm diameter)

### Time-Sequence View (simulation_sequence.png)
- **Blue → Cyan → Green → Yellow → Orange → Red**: Drawing progress over time
- Shows the order in which paths are drawn
- Useful for understanding path optimization

---

## 🔍 Detailed Usage

### test_svg_to_ssg.py

Complete end-to-end test of the SVG compilation pipeline.

**Basic usage:**
```bash
python test_svg_to_ssg.py <input.svg>
```

**With custom output name:**
```bash
python test_svg_to_ssg.py ../svgs/drawing.svg --output my_test
# Creates: my_test.ssg, simulation_preview.png, simulation_sequence.png
```

**What it does:**
1. ✅ Loads SVG file
2. ✅ Compiles to SSG using ssg_compiler.py
3. ✅ Validates size and complexity constraints
4. ✅ Shows command preview
5. ✅ Simulates execution
6. ✅ Generates two visualization images

**Output example:**
```
SVG TO SSG CONVERSION TEST
========================================
📄 Input:  ../svgs/best_result.svg
📄 Output: best_result_output.ssg

STEP 1: COMPILING SVG
----------------------------------------
Loading SVG: ../svgs/best_result.svg
Parsed 12 paths with 487 points
...
✅ Compilation Results:
   Paths: 12
   SSG Commands: 245
   Total length: 850.0 mm
   Estimated time: 95.0s (1.6 min)

STEP 2: DESIGN CONSTRAINTS VALIDATION
----------------------------------------
📏 Drawing size: 180.0mm × 175.0mm
   Max allowed: 220.0mm × 220.0mm
   ✅ Size OK
   Max distance from center: 98.5mm
   Plate radius: 110.0mm
   ✅ Fits within plate

STEP 3: SSG COMMAND PREVIEW
----------------------------------------
First 15 commands:
  N1 G28
  N2 M3 S60
  N3 G1 X-50.00 Y40.50 F600
  ...

STEP 4: SIMULATION & VISUALIZATION
----------------------------------------
🎮 Simulating SSG commands...
✓ Simulated 247 positions
...
✅ Visualizations saved
```

### ssg_simulator.py

Standalone simulator for SSG files.

**Basic usage:**
```bash
python ssg_simulator.py <file.ssg>
```

**Example:**
```bash
# Simulate a compiled SSG file
python ssg_simulator.py best_result_output.ssg

# Display plots interactively
# (plt.show() at end)
```

**What it does:**
1. Parses SSG commands (G0, G1, G28, M3, M5, etc.)
2. Simulates motion and sauce state
3. Extracts position list with drawing state
4. Generates two PNG visualizations
5. Shows interactive matplotlib plots

**Command support:**
- `G0` - Rapid move (blue dashed lines)
- `G1` - Linear move (red solid lines if sauce on)
- `G28` - Home to origin
- `M3` - Sauce on (enables drawing)
- `M5` - Sauce off (disables drawing)
- `M114`, `M408` - Ignored (status commands)

---

## 🎨 Visualization Examples

### Good Drawing (Centered, Fits Plate)
```
simulation_preview.png shows:
- All paths within gray circle
- Minimal blue dashed lines (efficient)
- Start and end close together
- Even distribution across plate
```

### Problems to Watch For

**Too Large:**
- Red lines extend beyond gray circle
- ⚠️ Will hit endstops or go off plate

**Inefficient Path:**
- Lots of long blue dashed lines
- ⚠️ Slow, wastes time on travel

**Off-Center:**
- Drawing bunched to one side
- ⚠️ May be clipped by plate edge

**Fix:** Adjust SVG or use ssg_compiler's normalize() more aggressively

---

## 🔧 Integration with Motor Control

### Workflow

```
1. Generate SVG
   └─> image_generator.ipynb
       └─> ../svgs/best_result.svg

2. Test & Visualize
   └─> python test_svg_to_ssg.py ../svgs/best_result.svg
       └─> best_result_output.ssg
       └─> simulation_preview.png ← Review this!
       └─> simulation_sequence.png

3. If looks good, send to hardware
   └─> python ../motor_movement/test_end_to_end.py ../svgs/best_result.svg
       └─> Compiles & streams to ESP32
```

### Manual SSG Creation

You can also create SSG files manually:

```ssg
N1 G28
N2 M3 S60
N3 G1 X25.00 Y0.00 F600
N4 G1 X25.00 Y25.00 F600
N5 G1 X0.00 Y25.00 F600
N6 G1 X0.00 Y0.00 F600
N7 M5
N8 G0 X0.00 Y0.00 F3000
```

Then visualize:
```bash
python ssg_simulator.py my_square.ssg
```

---

## 📐 Coordinate System

Both tools use the same coordinate system as motor_movement:
- **Origin (0,0)**: Center of plate
- **+X**: Right
- **+Y**: Up
- **Units**: millimeters (mm)
- **Plate boundary**: 110mm radius (220mm diameter)

---

## ⚙️ Configuration

The simulator uses values from `../motor_movement/config.py`:
- `CANVAS_WIDTH_MM` - Max drawing width
- `CANVAS_HEIGHT_MM` - Max drawing height
- `PLATE_RADIUS_MM` - Plate boundary circle

To change visualization defaults, edit the plot() functions in `ssg_simulator.py`.

---

## 🐛 Troubleshooting

### Import Error: "No module named ssg_compiler"
**Fix:** Run from simulate_drawing directory, or ensure motor_movement is in parent:
```bash
cd experiments/simulate_drawing
python test_svg_to_ssg.py ../svgs/file.svg
```

### Matplotlib Not Found
**Fix:**
```bash
pip install matplotlib numpy
```

### SSG File Empty or Invalid
**Check:**
- File exists and has .ssg extension
- Commands start with N (sequence number)
- Contains G or M commands

### Visualization Shows Nothing
**Possible causes:**
- All G0 commands (no G1 drawing)
- M3 never called (sauce never turned on)
- Positions all at origin

**Debug:**
- Check SSG file manually
- Look at command preview in test output
- Verify SVG compiled correctly

---

## 📚 Related Files

### Dependencies
- `../motor_movement/ssg_compiler.py` - SVG → SSG compiler
- `../motor_movement/config.py` - Hardware configuration

### Input Files
- `../svgs/*.svg` - SVG files from image generator
- `../motor_movement/test_*.svg` - Test patterns

### Output Files
- `*.ssg` - SSG command files
- `simulation_preview.png` - Standard visualization
- `simulation_sequence.png` - Time-sequence visualization

---

## 💡 Tips

1. **Always simulate before hardware**: Catch issues visually
2. **Check both views**: Standard shows paths, sequence shows order
3. **Watch for red outside circle**: Will fail on hardware
4. **Lots of blue lines = inefficient**: Consider path optimization
5. **Use with motor_movement tests**: Great for learning SSG format

---

## 🔄 Differences from Old System

### Old (plot_simulator.py + test_converter.py)
- Used JSON format: `[{"x": 100, "y": 50, "penDown": true}, ...]`
- Works with shyla_motor_code/vector_converter.py
- Binary pen up/down (no variable flow)
- Steps in motor coordinates

### New (ssg_simulator.py + test_svg_to_ssg.py)
- Uses SSG format: `N1 G1 X50.00 Y30.00 F600`
- Works with motor_movement/ssg_compiler.py
- Variable sauce flow (M3 S0-100)
- Direct mm coordinates
- Matches design doc protocol

**The old files are kept for reference but deprecated.**

---

## 📈 Example Output

```bash
$ python test_svg_to_ssg.py ../svgs/best_result.svg

SVG TO SSG CONVERSION TEST
========================================

STEP 1: COMPILING SVG
✅ Paths: 12, Commands: 245, Length: 850mm

STEP 2: VALIDATION
✅ Size: 180×175mm (fits 220×220mm plate)
✅ Max radius: 98.5mm (within 110mm plate)
✅ Complexity: 245 commands (under limit)

STEP 3: PREVIEW
N1 G28
N2 M3 S60
N3 G1 X-50.00 Y40.50 F600
...

STEP 4: VISUALIZATION
🎨 Generating visualizations...
💾 Saved: simulation_preview.png
💾 Saved: simulation_sequence.png

✅ TEST COMPLETE!
```

---

**Ready to simulate!** 🎨✨

Use these tools to visualize and validate your drawings before sending to hardware.


