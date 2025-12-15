# Hardware Configuration Update

## Changes Made

The firmware has been updated from a **dual X-motor gantry** setup to a **single X-motor** setup to match your actual hardware.

## Your Hardware Setup

- **1 X motor** - moves gantry left/right (horizontal)
- **1 Y motor** - moves gantry forward/back (depth)
- **1 PWM pump** - sauce dispensing
- **2 endstops** - X and Y limit switches for homing

**Total: 2 stepper motors + 1 pump**

## Pin Configuration

Update these in `firmware/sauce_plotter.ino` to match your wiring:

```cpp
// Motor pins (Step, Direction)
#define X_STEP_PIN  32
#define X_DIR_PIN   33
#define Y_STEP_PIN  14
#define Y_DIR_PIN   27

// Endstop pins (active low with pullup)
#define X_ENDSTOP_PIN  15
#define Y_ENDSTOP_PIN  16

// Sauce pump PWM
#define PUMP_PWM_PIN  23
```

## What Was Changed

### Firmware (`sauce_plotter.ino`)

1. **Removed X2 motor** - now only `stepper_X` and `stepper_Y`
2. **Simplified homing** - removed auto-squaring logic (no longer needed)
3. **Updated all movement commands** - only move X and Y (not X1, X2, Y)
4. **Pin definitions** - removed X2_STEP_PIN, X2_DIR_PIN, X2_ENDSTOP_PIN

### Homing Sequence (G28)

**Old (dual X-motor):**
- Home X1 independently
- Home X2 independently  
- Precision re-home both together (auto-squaring)
- Home Y

**New (single X-motor):**
- Home X axis
- Precision re-home X
- Home Y axis
- Precision re-home Y

Much simpler! ✅

## Testing Mode

`TESTING_MODE` is currently **enabled** in the firmware:

```cpp
#define TESTING_MODE true
```

This allows you to test movement **without endstops connected**. The firmware will skip homing and assume position 0,0.

**For production use:** Set to `false` and connect your endstop switches.

## Next Steps

1. **Flash the updated firmware** to your ESP32
2. **Verify pin connections** match the pin definitions above
3. **Test with** `python test_motors_only.py`
4. **When ready:** Connect endstops and set `TESTING_MODE false`

## No Changes Needed

These files work correctly as-is:
- `config.py` - already hardware-agnostic
- `ssg_compiler.py` - SVG to SSG conversion (2D only)
- `ssg_sender.py` - WiFi communication
- `calibrate.py` - calibration tools
- `test_end_to_end.py` - full pipeline test

## Summary

Your system is now properly configured for:
- ✅ Single X motor (horizontal movement)
- ✅ Single Y motor (depth movement)  
- ✅ 2D movement only (no Z-axis)
- ✅ PWM sauce pump control
- ✅ Simple homing with 2 endstops

This is actually a **simpler and more common** CNC plotter configuration! 🎯

