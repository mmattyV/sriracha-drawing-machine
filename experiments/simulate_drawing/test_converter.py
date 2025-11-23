#!/usr/bin/env python3
"""
Test script for the SVG to Plotter converter
Tests the conversion pipeline with best_result.svg
"""

import sys
import json
import asyncio
from pathlib import Path

# Add the motor_movement directory to path
sys.path.insert(0, str(Path(__file__).parent / "shyla_motor_code" / "motor_movement"))

from vector_converter import SVGToPlotter

# Configuration
SVG_FILE = Path(__file__).parent / "svgs" / "best_result.svg"
SCALE = 1.0
DRY_RUN = True  # Set to False if you want to try connecting to actual hardware


def test_svg_parsing():
    """Test SVG parsing and conversion"""
    print("=" * 70)
    print("SVG TO PLOTTER CONVERTER TEST")
    print("=" * 70)
    print()
    
    if not SVG_FILE.exists():
        print(f"❌ Error: SVG file not found: {SVG_FILE}")
        return None
    
    print(f"📄 Input file: {SVG_FILE}")
    print(f"📐 Scale: {SCALE}x")
    print()
    
    # Create converter and parse SVG
    converter = SVGToPlotter()
    
    try:
        converter.parse_svg_file(str(SVG_FILE), scale=SCALE)
    except Exception as e:
        print(f"❌ Error parsing SVG: {e}")
        return None
    
    if not converter.path_data:
        print("❌ Error: No path data extracted from SVG")
        return None
    
    print(f"✓ Successfully parsed SVG")
    print(f"✓ Extracted {len(converter.path_data)} points")
    
    # Center the drawing around origin (0, 0)
    print("🎯 Centering drawing around origin...")
    converter.center_drawing()
    print(f"✓ Drawing centered")
    print()
    
    return converter


def analyze_path_data(converter):
    """Analyze the converted path data"""
    print("=" * 70)
    print("PATH ANALYSIS")
    print("=" * 70)
    print()
    
    # Get bounds
    bounds = converter.get_bounds()
    print(f"📏 Drawing Bounds:")
    print(f"   Min X: {bounds['min_x']:.2f} units")
    print(f"   Min Y: {bounds['min_y']:.2f} units")
    print(f"   Max X: {bounds['max_x']:.2f} units")
    print(f"   Max Y: {bounds['max_y']:.2f} units")
    print(f"   Width: {bounds['width']:.2f} units")
    print(f"   Height: {bounds['height']:.2f} units")
    print()
    
    # Count pen up/down movements
    pen_down_count = sum(1 for p in converter.path_data if p.pen_down)
    pen_up_count = len(converter.path_data) - pen_down_count
    
    print(f"✏️  Movement Statistics:")
    print(f"   Pen down moves: {pen_down_count}")
    print(f"   Pen up moves: {pen_up_count}")
    print(f"   Total points: {len(converter.path_data)}")
    print()
    
    # Calculate total path length
    total_distance = 0.0
    draw_distance = 0.0
    travel_distance = 0.0
    
    for i in range(1, len(converter.path_data)):
        prev = converter.path_data[i-1]
        curr = converter.path_data[i]
        dx = curr.x - prev.x
        dy = curr.y - prev.y
        dist = (dx**2 + dy**2) ** 0.5
        total_distance += dist
        if curr.pen_down:
            draw_distance += dist
        else:
            travel_distance += dist
    
    print(f"📐 Distance Analysis:")
    print(f"   Drawing distance: {draw_distance:.2f} units")
    print(f"   Travel distance: {travel_distance:.2f} units")
    print(f"   Total distance: {total_distance:.2f} units")
    print(f"   Draw/Travel ratio: {draw_distance/total_distance*100:.1f}% drawing")
    print()
    
    # Estimate time (rough calculation)
    # Assume 10 mm/s drawing speed, 50 mm/s travel speed
    draw_time = draw_distance / 10.0  # seconds
    travel_time = travel_distance / 50.0  # seconds
    total_time = draw_time + travel_time
    
    print(f"⏱️  Estimated Time (rough):")
    print(f"   Drawing: {draw_time:.1f}s")
    print(f"   Travel: {travel_time:.1f}s")
    print(f"   Total: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print()


def show_motor_instructions(converter):
    """Show sample motor instructions"""
    print("=" * 70)
    print("MOTOR INSTRUCTIONS PREVIEW")
    print("=" * 70)
    print()
    
    instructions_json = converter.to_motor_instructions()
    instructions = json.loads(instructions_json)
    
    print(f"Total instructions: {len(instructions)}")
    print(f"JSON size: {len(instructions_json)} bytes")
    print()
    
    print("First 10 instructions:")
    for i, inst in enumerate(instructions[:10]):
        pen_status = "PEN DOWN" if inst["penDown"] else "PEN UP  "
        print(f"  {i:3d}: X={inst['x']:8.1f} Y={inst['y']:8.1f} {pen_status}")
    
    if len(instructions) > 10:
        print(f"  ... ({len(instructions) - 10} more instructions)")
    print()
    
    return instructions_json


def save_instructions(instructions_json):
    """Save motor instructions to file"""
    output_file = Path(__file__).parent / "test_output_instructions.json"
    output_file.write_text(instructions_json)
    print(f"💾 Saved instructions to: {output_file}")
    print()


async def test_plotter_connection(instructions_json):
    """Test connection to actual plotter (if available)"""
    try:
        import websockets
    except ImportError:
        print("⚠️  websockets library not installed. Skipping connection test.")
        print("   Install with: pip install websockets")
        return
    
    print("=" * 70)
    print("PLOTTER CONNECTION TEST")
    print("=" * 70)
    print()
    
    from vector_converter import PLOTTER_IP
    uri = f"ws://{PLOTTER_IP}/ws"
    
    print(f"🔌 Attempting to connect to: {uri}")
    print(f"   (This will timeout if plotter is not available)")
    print()
    
    try:
        async with asyncio.timeout(5.0):  # 5 second timeout
            async with websockets.connect(uri) as websocket:
                print("✓ Connected to plotter!")
                print()
                
                # Send instructions
                message = f"PATH:{instructions_json}"
                print(f"📤 Sending {len(message)} bytes...")
                await websocket.send(message)
                
                print("⏳ Waiting for plotter response...")
                
                # Wait for responses with timeout
                try:
                    async with asyncio.timeout(30.0):
                        async for response in websocket:
                            print(f"   Plotter: {response}")
                            if "complete" in response.lower() or "done" in response.lower():
                                print()
                                print("✅ Drawing completed successfully!")
                                break
                except asyncio.TimeoutError:
                    print()
                    print("⏱️  Response timeout (drawing may still be in progress)")
    
    except asyncio.TimeoutError:
        print("❌ Connection timeout - plotter not responding")
        print("   This is expected if the ESP32 is not powered on or not connected")
    except ConnectionRefusedError:
        print(f"❌ Connection refused at {PLOTTER_IP}")
        print("   Make sure:")
        print("   1. ESP32 is powered on")
        print("   2. ESP32 is connected to WiFi")
        print("   3. IP address is correct in vector_converter.py")
    except Exception as e:
        print(f"❌ Connection error: {e}")
    
    print()


def validate_svg_constraints(converter):
    """Validate against design doc constraints"""
    print("=" * 70)
    print("DESIGN DOC CONSTRAINTS VALIDATION")
    print("=" * 70)
    print()
    
    bounds = converter.get_bounds()
    
    # Check size constraints
    max_dimension = 220  # mm from design doc
    size_ok = bounds['width'] <= max_dimension and bounds['height'] <= max_dimension
    
    print(f"📏 Size constraints (max {max_dimension}x{max_dimension} mm):")
    print(f"   Width: {bounds['width']:.1f} mm {'✓' if bounds['width'] <= max_dimension else '❌ TOO LARGE'}")
    print(f"   Height: {bounds['height']:.1f} mm {'✓' if bounds['height'] <= max_dimension else '❌ TOO LARGE'}")
    print()
    
    # Check path complexity
    max_points = 10000  # from design doc
    points_ok = len(converter.path_data) <= max_points
    
    print(f"📊 Complexity constraints (max {max_points} points):")
    print(f"   Total points: {len(converter.path_data)} {'✓' if points_ok else '❌ TOO COMPLEX'}")
    print()
    
    # Check minimum feature size
    min_segment = 0.3  # mm from design doc
    small_segments = 0
    
    for i in range(1, len(converter.path_data)):
        prev = converter.path_data[i-1]
        curr = converter.path_data[i]
        if curr.pen_down:
            dx = curr.x - prev.x
            dy = curr.y - prev.y
            dist = (dx**2 + dy**2) ** 0.5
            if dist < min_segment and dist > 0:
                small_segments += 1
    
    print(f"🔍 Feature size check (min {min_segment} mm):")
    print(f"   Segments < {min_segment}mm: {small_segments}")
    if small_segments > 0:
        print(f"   ⚠️  Warning: {small_segments} segments are very small and may not plot well")
    else:
        print(f"   ✓ All segments are plottable size")
    print()
    
    # Overall validation
    all_ok = size_ok and points_ok and small_segments == 0
    
    if all_ok:
        print("✅ SVG passes all design constraints!")
    else:
        print("⚠️  SVG has constraint violations (see above)")
    
    print()


def main():
    """Main test function"""
    # Test 1: Parse SVG
    converter = test_svg_parsing()
    if converter is None:
        return
    
    # Test 2: Analyze path data
    analyze_path_data(converter)
    
    # Test 3: Validate constraints
    validate_svg_constraints(converter)
    
    # Test 4: Generate motor instructions
    instructions_json = show_motor_instructions(converter)
    
    # Test 5: Save instructions
    save_instructions(instructions_json)
    
    # Test 6: Try connecting to plotter (if not dry run)
    if not DRY_RUN:
        print("🚀 Attempting to connect to plotter...")
        print("   (Set DRY_RUN=True at the top of this file to skip)")
        print()
        asyncio.run(test_plotter_connection(instructions_json))
    else:
        print("=" * 70)
        print("DRY RUN MODE - Skipping plotter connection")
        print("=" * 70)
        print()
        print("To test with actual hardware:")
        print("  1. Set DRY_RUN = False at the top of this file")
        print("  2. Make sure ESP32 is powered on and connected")
        print("  3. Update PLOTTER_IP in vector_converter.py")
        print("  4. Run this script again")
        print()
    
    print("=" * 70)
    print("TEST COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    main()

