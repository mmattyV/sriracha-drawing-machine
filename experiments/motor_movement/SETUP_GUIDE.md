# Sriracha Sketcher - Complete Setup Guide

Step-by-step guide to get your Sriracha Sketcher up and running from scratch.

---

## 📋 Pre-Flight Checklist

### Required Hardware
- [ ] ESP32 dev board (any variant)
- [ ] 2× NEMA 17 stepper motors (for X1 and X2)
- [ ] 1× NEMA 17 stepper motor (for Y)
- [ ] 3× Stepper drivers (TMC2209 recommended, or A4988)
- [ ] 3× Limit switches (normally-open type)
- [ ] Peristaltic pump (12V recommended) or servo for sauce
- [ ] 12-24V power supply (3-5A minimum)
- [ ] GT2 belts and pulleys (20-tooth recommended)
- [ ] Linear rails or rods for X and Y axes
- [ ] Sauce bottle mount
- [ ] Plate holder/bed

### Required Software
- [ ] Arduino IDE 2.x (or 1.8.19+)
- [ ] Python 3.8+ with pip
- [ ] USB cable for ESP32
- [ ] Text editor for config files

### Required Skills
- [ ] Basic soldering (for connections)
- [ ] Basic Arduino programming (for firmware setup)
- [ ] Python familiarity (for backend)
- [ ] Mechanical assembly (following frame design)

---

## 🔧 Part 1: Hardware Assembly

### Step 1: Frame Assembly
1. Assemble X-axis gantry with dual motors (X1 on left, X2 on right)
2. Install Y-axis with single motor
3. Tension belts (should twang like guitar string when plucked)
4. Verify smooth motion by hand - no binding or sticking

### Step 2: Electronics Wiring

**Power Distribution:**
```
Power Supply (12-24V)
├── Stepper Driver 1 (X1) ─ VMOT+
├── Stepper Driver 2 (X2) ─ VMOT+
├── Stepper Driver 3 (Y)  ─ VMOT+
├── Pump (if 12V)
└── GND common
```

**ESP32 to Drivers:**
```
ESP32          Driver 1 (X1)    Driver 2 (X2)    Driver 3 (Y)
GPIO 2    ───> STEP
GPIO 4    ───> DIR
GPIO 5    ───────────────────> STEP
GPIO 18   ───────────────────> DIR
GPIO 19   ───────────────────────────────────> STEP
GPIO 21   ───────────────────────────────────> DIR

3.3V      ───> VDD           ───> VDD          ───> VDD
GND       ───> GND           ───> GND          ───> GND
          ───> EN → GND      ───> EN → GND     ───> EN → GND
```

**Endstops to ESP32:**
```
Limit Switch      ESP32
X1 endstop NO ──> GPIO 25 (+ GND)
X2 endstop NO ──> GPIO 26 (+ GND)
Y endstop NO  ──> GPIO 27 (+ GND)

Note: Use normally-open (NO) switches
      Firmware enables internal pullup resistors
```

**Pump to ESP32:**
```
For DC Pump (via MOSFET):
ESP32 GPIO 23 ──> MOSFET Gate
MOSFET Drain  ──> Pump (-)
Pump (+)      ──> Power supply (+)
MOSFET Source ──> Power supply GND

For Servo (direct):
ESP32 GPIO 23 ──> Servo signal (orange)
3.3V/5V       ──> Servo power (red)
GND           ──> Servo ground (brown)
```

**Motors to Drivers:**
```
Stepper Motor          Driver
Coil A1 (Black)   ───> 1A
Coil A2 (Green)   ───> 1B
Coil B1 (Red)     ───> 2A
Coil B2 (Blue)    ───> 2B

Note: Colors may vary by manufacturer
      Test with multimeter: ~1-4Ω between coil pairs
```

### Step 3: Driver Configuration

**For TMC2209:**
1. Set microstepping to 16× (MS1=HIGH, MS2=LOW via DIP switches or solder pads)
2. Adjust current: `Vref = I_rms × 2.5 × R_sense`
   - For 1.5A motors: Vref ≈ 0.9V
   - Measure with multimeter on Vref pad
3. Connect EN to GND permanently

**For A4988:**
1. Set microstepping to 16× (MS1=HIGH, MS2=HIGH, MS3=LOW)
2. Adjust current: `Vref = I_rms × 8 × R_sense`
   - For 1.5A motors: Vref ≈ 0.6V
3. Add heatsinks to driver chips
4. Connect EN to GND permanently

### Step 4: Safety Check

Before powering on:
- [ ] Double-check all wiring against diagrams
- [ ] Verify no shorts with multimeter
- [ ] Confirm motor coil resistance (1-4Ω per coil)
- [ ] Check power supply voltage (12-24V)
- [ ] Ensure endstops are wired NO (normally open)
- [ ] Verify ESP32 is not connected to power supply HV side

---

## 💻 Part 2: Software Setup

### Step 1: Install Arduino IDE

1. Download from: https://www.arduino.cc/en/software
2. Install ESP32 board support:
   - Open Arduino IDE
   - Go to **File → Preferences**
   - Add to "Additional Board Manager URLs":
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Go to **Tools → Board → Board Manager**
   - Search "esp32" and install "esp32 by Espressif Systems"

### Step 2: Install Required Libraries

In Arduino IDE:
1. Go to **Tools → Manage Libraries**
2. Install these libraries:
   - `AccelStepper` by Mike McCauley
   - `AsyncTCP` (install manually, see below)
   - `ESPAsyncWebServer` (install manually, see below)

**Manual Library Installation:**
```bash
cd ~/Arduino/libraries/

# AsyncTCP
git clone https://github.com/me-no-dev/AsyncTCP.git

# ESPAsyncWebServer
git clone https://github.com/me-no-dev/ESPAsyncWebServer.git
```

Restart Arduino IDE after manual installation.

### Step 3: Configure and Flash Firmware

1. Open `firmware/sauce_plotter.ino` in Arduino IDE

2. **Update WiFi credentials** (lines 38-39):
   ```cpp
   const char* WIFI_SSID = "YourNetworkName";
   const char* WIFI_PASSWORD = "YourPassword";
   ```

3. **Verify pin configuration** matches your wiring (lines 41-56)

4. **Adjust microstepping if not 16×** (lines 62-63):
   ```cpp
   // If using 32× microstepping:
   const float STEPS_PER_MM_X = 160.0;  // 80 × 2
   const float STEPS_PER_MM_Y = 160.0;
   ```

5. **Select board and port:**
   - **Tools → Board → ESP32 Dev Module**
   - **Tools → Port → /dev/ttyUSB0** (or COM3 on Windows)

6. **Upload:**
   - Click **Upload** button (→)
   - Wait for "Done uploading"

7. **Get IP address:**
   - Open **Tools → Serial Monitor** (115200 baud)
   - Press ESP32 RESET button
   - Note the IP address shown (e.g., `192.168.1.105`)

### Step 4: Setup Python Environment

```bash
cd motor_movement/

# Install Python dependencies
pip install -r requirements.txt

# Verify installation
python -c "import websockets; print('✓ websockets installed')"
```

### Step 5: Configure Backend

Edit `config.py`:

```python
# Line 9: Set ESP32 IP from Serial Monitor
ESP32_IP = "192.168.1.105"  # ← YOUR IP HERE

# Lines 18-19: Verify steps/mm (calibrate later)
STEPS_PER_MM_X = 80.0  # (200 × 16) / (2 × 20) = 80
STEPS_PER_MM_Y = 80.0

# Lines 24-29: Set your plate size
CANVAS_WIDTH_MM = 220.0
CANVAS_HEIGHT_MM = 220.0
PLATE_RADIUS_MM = 110.0  # Half of diameter
```

---

## ✅ Part 3: First Power-On Test

### Test 1: ESP32 Boot

1. Power on ESP32 via USB
2. Open Serial Monitor (115200 baud)
3. You should see:
   ```
   =================================
   Sriracha Sketcher - Booting
   =================================
   Connecting to WiFi...
   WiFi connected!
   IP Address: 192.168.1.105
   WebSocket server started
   System ready - waiting for G28 (home) command
   ```

**If stuck at "Connecting to WiFi":**
- Verify SSID/password (case-sensitive!)
- Confirm 2.4GHz WiFi (ESP32 doesn't support 5GHz)
- Try moving closer to router

### Test 2: WebSocket Connection

```bash
python -c "
import asyncio
from ssg_sender import SSGSender

async def test():
    sender = SSGSender()
    if await sender.connect():
        print('✅ Connection successful!')
        await sender.disconnect()
    else:
        print('❌ Connection failed')

asyncio.run(test())
"
```

**If connection fails:**
- Verify IP in config.py matches Serial Monitor
- Check firewall settings
- Confirm ESP32 and computer on same network

### Test 3: Motor Power Test

⚠️ **Safety: Remove belts from motors for initial test**

1. Power on stepper driver power supply (12-24V)
2. Motors should hold position (feel resistance when turning by hand)
3. If motors are hot after 30 seconds:
   - Power off immediately
   - Reduce driver current (lower Vref)

### Test 4: Manual Jog Test

```bash
python -c "
import asyncio
from ssg_sender import SSGSender

async def jog_test():
    sender = SSGSender()
    await sender.connect()
    
    print('Testing X axis...')
    await sender.websocket.send('N1 G0 X10.00 F600')
    await asyncio.sleep(3)
    
    print('Testing Y axis...')
    await sender.websocket.send('N2 G0 Y10.00 F600')
    await asyncio.sleep(3)
    
    print('Return to origin...')
    await sender.websocket.send('N3 G0 X0.00 Y0.00 F600')
    await asyncio.sleep(3)
    
    await sender.disconnect()
    print('✅ Jog test complete')

asyncio.run(jog_test())
"
```

**Expected behavior:**
- X motors move together in same direction
- Y motor moves smoothly
- No skipping or grinding sounds

**If motors move wrong direction:**
- Physically swap motor coil pairs OR
- Invert in firmware: `stepper_X1.setPinsInverted(true, false, false);`

**If motors skip steps:**
- Reduce speed: `F300` instead of `F600`
- Increase driver current slightly
- Check belt isn't too tight

### Test 5: Homing Test

⚠️ **Ensure endstops are properly mounted and wired**

```bash
python -c "
import asyncio
from ssg_sender import SSGSender

async def home_test():
    sender = SSGSender()
    await sender.connect()
    
    print('Starting homing sequence (G28)...')
    print('This will take ~15 seconds')
    await sender.send_home()
    await asyncio.sleep(20)
    
    await sender.disconnect()
    print('✅ Homing complete')

asyncio.run(home_test())
"
```

Watch Serial Monitor for:
```
Starting homing sequence...
Homing X1...
Homing X2...
Precision X homing...
Homing Y...
Precision Y homing...
Homing complete - system ready
```

**If homing fails:**
- Check endstop wiring (NO switches, pullup enabled)
- Verify endstops trigger when pressed (LED on driver or multimeter test)
- Confirm motors move TOWARD endstops (not away)

---

## 🎯 Part 4: Calibration

Now that basic tests pass, calibrate for precision:

### Step 1: Interactive Calibration

```bash
python calibrate.py
```

Follow the menu:
1. **Calibrate X axis** → Updates `STEPS_PER_MM_X`
2. **Calibrate Y axis** → Updates `STEPS_PER_MM_Y`
3. **Test 50mm square** → Verifies calibration
4. **Test circle** → Checks X/Y match

**Record your values:**
```python
# Add to config.py after calibration:
STEPS_PER_MM_X = 82.5  # ← Your calibrated value
STEPS_PER_MM_Y = 81.0  # ← Your calibrated value
```

### Step 2: Flow Calibration (With Sauce)

⚠️ **Only after motors are working perfectly**

1. Install pump/servo and sauce bottle
2. Run flow ladder test:
   ```bash
   python calibrate.py
   # Select option 5: Flow calibration ladder
   ```
3. Measure line widths at each flow %
4. Update `config.py` if needed

---

## 🎨 Part 5: First Drawing

### Test with Dry Run

```bash
# Test SVG compilation without hardware
python test_end_to_end.py path/to/simple.svg --dry-run
```

Review the output `.ssg` file to ensure commands look reasonable.

### Full Test Drawing

```bash
# Complete pipeline: SVG → ESP32
python test_end_to_end.py path/to/simple.svg
```

This will:
1. ✓ Compile SVG to SSG
2. ✓ Connect to ESP32
3. ✓ Home the machine
4. ✓ Stream all commands
5. ✓ Draw your image!

**Recommended first SVG:**
- Simple shape (star, heart, basic outline)
- Centered on 0,0
- Size < 100mm
- No tiny details

---

## 🐛 Common First-Time Issues

### Issue: "Connection refused"
**Cause:** Wrong IP or ESP32 not on network
**Fix:** 
```bash
# Ping ESP32
ping 192.168.1.105

# Check Serial Monitor for actual IP
# Update config.py with correct IP
```

### Issue: Motors vibrate but don't move
**Cause:** Wrong microstepping or loose coupler
**Fix:**
- Verify driver microstepping setting (should be 16×)
- Check motor shaft coupler screws are tight
- Try different `STEPS_PER_MM` value

### Issue: Drawing wrong size
**Cause:** Incorrect steps/mm calculation
**Fix:**
- Run calibration: `python calibrate.py` → option 1 & 2
- Verify belt pitch (GT2 = 2mm, usually)
- Check pulley teeth count (typically 20T)

### Issue: Sauce won't flow
**Cause:** PWM not working or pump issue
**Fix:**
- Test pump directly with 12V
- Verify GPIO 23 wiring
- Check `SAUCE_FLOW_DEFAULT` (try 80-100%)
- Ensure sauce is warm (30-40°C)

### Issue: "err code=NOT_HOMED"
**Cause:** Trying to move before homing
**Fix:**
- Always run G28 first
- Check endstops are working
- Verify homing completed successfully in Serial Monitor

---

## 📚 Next Steps

Once everything works:

1. **Practice:** Draw several test patterns to build intuition
2. **Optimize:** Tune speeds and flow for your sauce
3. **Create:** Generate custom SVGs with image_generator.ipynb
4. **Iterate:** Use the VLM critic loop for best results
5. **Share:** Document your sauce art! 🌶️

---

## 🆘 Getting Help

1. Check Serial Monitor for ESP32 error messages
2. Review README.md troubleshooting section
3. Test each component individually (motors, endstops, pump)
4. Use dry-run mode to validate SVGs before printing
5. Start with slow speeds and simple shapes

---

## ✨ Success Checklist

You're ready to plot when:
- [ ] ESP32 boots and connects to WiFi
- [ ] Python can connect via WebSocket
- [ ] All motors move in correct directions
- [ ] Homing sequence completes successfully
- [ ] X and Y axes are calibrated (steps/mm)
- [ ] Test square is accurate to ±1mm
- [ ] Pump/servo activates on M3 command
- [ ] Flow calibration ladder shows consistent lines
- [ ] End-to-end test completes without errors

**Congratulations!** Your Sriracha Sketcher is operational! 🎉

Time to make some delicious art! 🌶️🎨


