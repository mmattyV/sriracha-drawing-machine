"""
Configuration for Sriracha Sketcher Motor Control System
Adjust these values for your specific hardware setup
"""

# ============================================
# ESP32 NETWORK CONFIGURATION
# ============================================
ESP32_IP = "192.168.0.126"  # Change to your ESP32's IP address
ESP32_PORT = 80
WEBSOCKET_PATH = "/ws"

# ============================================
# MACHINE DIMENSIONS & KINEMATICS
# ============================================
# Steps per millimeter (CRITICAL - affects drawing accuracy)
# Design doc example: (200 steps/rev × 16 microstep) / (2mm pitch × 20 teeth) = 80 steps/mm
STEPS_PER_MM_X = 80.0
STEPS_PER_MM_Y = 80.0

# Working area dimensions (in millimeters)
# Design doc: plate diameter ~240-280mm, so ~220mm square printable area
CANVAS_WIDTH_MM = 220.0
CANVAS_HEIGHT_MM = 220.0
CANVAS_CENTER_X = 0.0  # Center of canvas in machine coordinates
CANVAS_CENTER_Y = 0.0

# Plate profile (circular printable area)
PLATE_RADIUS_MM = 110.0  # 220mm diameter / 2

# ============================================
# MOTION PARAMETERS
# ============================================
# Feed rates (mm/min)
# Design doc: travel 50 mm/s, drawing 10-20 mm/s
FEED_RATE_RAPID = 3000  # 50 mm/s = 3000 mm/min
FEED_RATE_DRAW = 600    # 10 mm/s = 600 mm/min
FEED_RATE_DRAW_FAST = 1200  # 20 mm/s for simple lines

# Acceleration (mm/s²)
# Design doc: 600-1000 mm/s²
ACCELERATION = 800

# ============================================
# SAUCE FLOW PARAMETERS
# ============================================
# Flow duty cycle (0-100%)
SAUCE_FLOW_DEFAULT = 60  # 60% duty cycle
SAUCE_FLOW_MIN = 20      # Minimum flow (for fine details)
SAUCE_FLOW_MAX = 80      # Maximum flow (for bold lines)

# Flow timing (milliseconds)
# Design doc: min dwell 50-100ms
SAUCE_ON_DWELL_MS = 100   # Wait after turning sauce on
SAUCE_OFF_DWELL_MS = 50   # Wait after turning sauce off
FLOW_RAMP_TIME_MS = 80    # Time to ramp flow up/down

# ============================================
# PROTOCOL PARAMETERS
# ============================================
# Sliding window (design doc: 32 in-flight commands)
WINDOW_SIZE = 32

# Timeout and retry
ACK_TIMEOUT_SEC = 0.25    # 250ms per design doc
MAX_RETRIES = 3
HEARTBEAT_INTERVAL_SEC = 1.0  # 1 second per design doc

# ============================================
# PATH OPTIMIZATION
# ============================================
# Tessellation (Bezier curves to line segments)
BEZIER_MAX_ERROR_MM = 0.2  # Maximum deviation from true curve
MIN_SEGMENT_LENGTH_MM = 0.3  # Design doc: min segment 0.3mm

# Simplification (Douglas-Peucker)
SIMPLIFY_EPSILON_MM = 0.15  # Simplification tolerance

# Design constraints (design doc section 7.1)
MAX_PATHS = 100
MAX_TOTAL_LENGTH_MM = 3000  # ~3 meters total
MIN_FEATURE_SIZE_MM = 2.0   # Minimum printable feature
MAX_VERTICES = 10000

# ============================================
# HOMING PARAMETERS
# ============================================
# Design doc section 5.5: independent X1/X2 homing for squaring
HOMING_FEED_RATE = 600      # mm/min for initial homing
HOMING_FEED_RATE_SLOW = 120 # mm/min for precision re-home
HOMING_BACKOFF_MM = 5.0     # Back off distance after hitting endstop

# ============================================
# SAFETY LIMITS
# ============================================
# Soft limits (to prevent crashes)
X_MIN_MM = -120.0
X_MAX_MM = 120.0
Y_MIN_MM = -120.0
Y_MAX_MM = 120.0

# Maximum job parameters
MAX_JOB_DURATION_SEC = 1800  # 30 minutes max
MAX_COMMANDS_PER_JOB = 50000

# ============================================
# COORDINATE SYSTEM
# ============================================
# Origin at center of plate (design doc preference)
ORIGIN_AT_CENTER = True

# ============================================
# DEBUGGING & LOGGING
# ============================================
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_TELEMETRY = True
LOG_FILE = "plotter.log"

# Simulation mode (for testing without hardware)
SIMULATION_MODE = False

