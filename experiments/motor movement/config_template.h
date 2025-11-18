/*
 * PLOTTER CONFIGURATION FILE
 * Copy these settings into your main .ino file and adjust for your machine
 */

// ============================================
// WIFI CONFIGURATION
// ============================================
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";


// ============================================
// STEPPER MOTOR PIN CONFIGURATION
// ============================================
// Format: AccelStepper(interface, stepPin, directionPin)
// Interface 1 = Step/Direction driver

// X-axis motors (typically two motors for gantry synchronization)
AccelStepper stepper_X1(1, 2, 4);    // Step pin 2, Direction pin 4
AccelStepper stepper_X2(1, 5, 18);   // Step pin 5, Direction pin 18

// Y-axis motor
AccelStepper stepper_Y(1, 19, 21);   // Step pin 19, Direction pin 21


// ============================================
// MACHINE DIMENSIONS & CALIBRATION
// ============================================

// Steps per millimeter (CRITICAL - affects drawing accuracy)
// Formula: (steps_per_rev × microstepping) / (belt_pitch_mm × pulley_teeth)
// Example: (200 × 16) / (2 × 20) = 80 steps/mm
float STEPS_PER_MM_X = 10.0;    // Adjust based on your machine
float STEPS_PER_MM_Y = 10.0;    // Adjust based on your machine

// Working area dimensions (in millimeters)
float CANVAS_WIDTH_MM = 600.0;
float CANVAS_HEIGHT_MM = 400.0;


// ============================================
// MOTOR SPEED & ACCELERATION
// ============================================
// Units: steps per second

// Maximum speed (steps/second)
// Start low (500-1000) and increase gradually
// Typical range: 500-3000
float MAX_SPEED_X = 2000.0;
float MAX_SPEED_Y = 2000.0;

// Acceleration (steps/second²)
// Lower = smoother, higher = faster movements
// Typical range: 200-2000
float ACCELERATION_X = 1000.0;
float ACCELERATION_Y = 1000.0;


// ============================================
// OPTIONAL: PEN LIFT SERVO
// ============================================
// Uncomment and configure if using servo for pen lift

// #include <ESP32Servo.h>
// Servo penServo;
// const int SERVO_PIN = 23;
// const int PEN_UP_ANGLE = 90;      // Servo angle for pen up
// const int PEN_DOWN_ANGLE = 45;    // Servo angle for pen down
// const int PEN_DELAY_MS = 200;     // Wait time after servo movement


// ============================================
// OPTIONAL: LIMIT SWITCHES / ENDSTOPS
// ============================================
// Uncomment and configure if using endstops for homing

// const int X_MIN_ENDSTOP = 25;
// const int X_MAX_ENDSTOP = 26;
// const int Y_MIN_ENDSTOP = 27;
// const int Y_MAX_ENDSTOP = 32;


// ============================================
// MOTOR DIRECTION INVERSION
// ============================================
// If motors move in wrong direction, set to true

bool INVERT_X1_DIR = false;
bool INVERT_X2_DIR = false;
bool INVERT_Y_DIR = false;


// ============================================
// ADVANCED SETTINGS
// ============================================

// Enable/disable motors when idle (saves power, may reduce holding torque)
bool DISABLE_WHEN_IDLE = false;

// Backlash compensation (experimental)
// Set to 0 to disable
int BACKLASH_X_STEPS = 0;
int BACKLASH_Y_STEPS = 0;

// Drawing quality vs speed
// Higher = smoother curves but slower
int CURVE_SEGMENTS = 20;  // Bezier curve approximation segments
int CIRCLE_SEGMENTS = 36; // Circle approximation segments


// ============================================
// COORDINATE SYSTEM CONFIGURATION
// ============================================

// Origin location (where is 0,0?)
enum Origin {
  TOP_LEFT,      // 0,0 at top-left (typical for graphics)
  BOTTOM_LEFT,   // 0,0 at bottom-left (typical for CNC)
  CENTER         // 0,0 at center of working area
};

Origin ORIGIN_LOCATION = TOP_LEFT;


// ============================================
// COMMON STEPPER MOTOR SPECS
// ============================================
/*
NEMA 17 (most common):
- Steps per revolution: 200 (1.8° per step)
- Microstepping options: 1, 2, 4, 8, 16, 32
- Typical holding torque: 40-60 N·cm

GT2 Belt (most common):
- Belt pitch: 2mm
- Common pulley teeth: 16, 20

EXAMPLE CALCULATIONS:

1. Basic setup (no microstepping):
   STEPS_PER_MM = 200 / (2 × 20) = 5 steps/mm

2. With 16x microstepping:
   STEPS_PER_MM = (200 × 16) / (2 × 20) = 80 steps/mm

3. Lead screw (2mm pitch):
   STEPS_PER_MM = (200 × 16) / 2 = 1600 steps/mm

To find your value:
1. Command motor to move 1000 steps
2. Measure actual distance traveled
3. STEPS_PER_MM = 1000 / measured_distance_mm
*/


// ============================================
// TROUBLESHOOTING GUIDE
// ============================================
/*
PROBLEM: Motors not moving
- Check power supply voltage and current capacity
- Verify motor driver enable pins
- Check wiring connections
- Test with simple movement code

PROBLEM: Wrong movement direction
- Set INVERT_X_DIR or INVERT_Y_DIR to true
- Or swap motor coil wiring

PROBLEM: Skipped steps / position loss
- Reduce MAX_SPEED and ACCELERATION
- Increase motor driver current (within motor specs)
- Check for mechanical binding
- Verify power supply can handle peak current

PROBLEM: Drawing wrong size
- Recalculate STEPS_PER_MM
- Verify microstepping settings on driver
- Check belt tension

PROBLEM: Noisy or vibrating motors
- Reduce speed and acceleration
- Check microstepping configuration
- Verify motor mounting is secure
- Adjust motor driver current

PROBLEM: Position drift over time
- Enable motor holding when idle
- Add mechanical spring tension
- Consider adding endstops for re-homing
*/
