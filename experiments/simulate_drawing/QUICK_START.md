# Quick Start - Simulate Drawing

Get started visualizing SSG commands in 3 steps!

## 1️⃣ Install Dependencies

```bash
cd simulate_drawing
pip install -r requirements.txt
```

## 2️⃣ Test with Example SVG

```bash
# Test with motor_movement's test square
python test_svg_to_ssg.py ../motor_movement/test_square.svg
```

**Output:**
- `test_square_output.ssg` - SSG commands
- `simulation_preview.png` - Visual preview
- `simulation_sequence.png` - Time sequence

## 3️⃣ View the Results

Open the PNG files to see your drawing visualized!

---

## Common Tasks

### Visualize SVG from Image Generator
```bash
python test_svg_to_ssg.py ../svgs/best_result.svg
```

### Simulate Existing SSG File
```bash
python ssg_simulator.py my_drawing.ssg
```

### Test Different Patterns
```bash
# Square
python test_svg_to_ssg.py ../motor_movement/test_square.svg

# Star
python test_svg_to_ssg.py ../motor_movement/test_star.svg
```

---

## What You'll See

### simulation_preview.png
- **Red lines** = Drawing (sauce on)
- **Blue dashed** = Travel (sauce off)
- **Green dot** = Start
- **Black dot** = End
- **Gray circle** = Plate boundary

### simulation_sequence.png
- **Color gradient** = Drawing order
- **Blue** = Start
- **Red** = End

---

## Troubleshooting

**Module not found error?**
- Make sure you're in the `simulate_drawing` directory
- The script looks for `../motor_movement/ssg_compiler.py`

**Matplotlib not installed?**
```bash
pip install matplotlib numpy
```

---

## Next Steps

1. ✅ Visualize and validate your SVG
2. ✅ Check it fits within plate boundary
3. ✅ If looks good, send to hardware:
   ```bash
   cd ../motor_movement
   python test_end_to_end.py ../svgs/your_drawing.svg
   ```

---

**See README.md for complete documentation!**


