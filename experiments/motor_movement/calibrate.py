#!/usr/bin/env python3
"""
Calibration tools for Sriracha Sketcher
Helps calibrate steps/mm, flow curves, and test patterns
"""

import asyncio
import sys
from pathlib import Path

import config
from ssg_sender import SSGSender


class Calibrator:
    """Interactive calibration helper"""
    
    def __init__(self, esp32_ip: str = None):
        self.sender = SSGSender(esp32_ip)
    
    async def connect(self):
        """Connect to ESP32"""
        return await self.sender.connect()
    
    async def disconnect(self):
        """Disconnect from ESP32"""
        await self.sender.disconnect()
    
    async def calibrate_steps_per_mm(self, axis: str = 'X'):
        """
        Calibrate steps/mm for an axis
        
        Process:
        1. Home the machine
        2. Move 100mm
        3. Measure actual distance
        4. Calculate new steps/mm
        """
        print(f"\n{'='*60}")
        print(f"CALIBRATING STEPS/MM FOR {axis} AXIS")
        print('='*60)
        print()
        print("This will:")
        print("1. Home the machine")
        print(f"2. Move {axis}=100mm")
        print("3. You measure the actual distance traveled")
        print("4. Calculate correct steps/mm value")
        print()
        
        input("Press Enter to start, or Ctrl-C to cancel...")
        
        # Home first
        print("\nHoming...")
        await self.sender.send_home()
        await asyncio.sleep(15)  # Wait for homing
        
        # Move 100mm
        print(f"\nMoving {axis}+100mm...")
        if axis == 'X':
            cmd = "N1 G0 X100.00 F3000"
        else:
            cmd = "N1 G0 Y100.00 F3000"
        
        await self.sender.websocket.send(cmd)
        await asyncio.sleep(5)  # Wait for move
        
        print("\n" + "="*60)
        print("MEASUREMENT")
        print("="*60)
        print("Use a ruler or caliper to measure how far the axis ACTUALLY moved.")
        print("Measure from the starting position (after homing) to current position.")
        print()
        
        actual_distance = float(input("Enter actual distance traveled (in mm): "))
        
        if actual_distance <= 0:
            print("Invalid measurement")
            return
        
        # Calculate new steps/mm
        commanded_distance = 100.0
        current_steps_per_mm = config.STEPS_PER_MM_X if axis == 'X' else config.STEPS_PER_MM_Y
        
        new_steps_per_mm = current_steps_per_mm * (commanded_distance / actual_distance)
        
        print("\n" + "="*60)
        print("CALIBRATION RESULTS")
        print("="*60)
        print(f"Commanded distance: {commanded_distance} mm")
        print(f"Actual distance: {actual_distance} mm")
        print(f"Error: {abs(commanded_distance - actual_distance):.2f} mm ({abs(100*(commanded_distance-actual_distance)/commanded_distance):.1f}%)")
        print()
        print(f"Current STEPS_PER_MM_{axis}: {current_steps_per_mm}")
        print(f"New STEPS_PER_MM_{axis}: {new_steps_per_mm:.2f}")
        print()
        print("Update config.py with the new value:")
        print(f"  STEPS_PER_MM_{axis} = {new_steps_per_mm:.2f}")
        print()
    
    async def test_square(self, size: float = 50.0):
        """
        Draw a test square to verify calibration
        
        Args:
            size: Size of square in mm
        """
        print(f"\n{'='*60}")
        print(f"TEST PATTERN: {size}mm SQUARE")
        print('='*60)
        print()
        
        input("Press Enter to start, or Ctrl-C to cancel...")
        
        # Generate square commands
        commands = [
            "N1 G28",  # Home
            "N2 M3 S60",  # Sauce on (or pen down)
            f"N3 G1 X0.00 Y0.00 F600",
            f"N4 G1 X{size:.2f} Y0.00 F600",
            f"N5 G1 X{size:.2f} Y{size:.2f} F600",
            f"N6 G1 X0.00 Y{size:.2f} F600",
            f"N7 G1 X0.00 Y0.00 F600",
            "N8 M5",  # Sauce off
            "N9 G0 X0.00 Y0.00 F3000"
        ]
        
        print(f"Streaming {len(commands)} commands...")
        success = await self.sender.stream_commands(commands)
        
        if success:
            print(f"\n✅ Square complete!")
            print(f"Measure the square:")
            print(f"  - Should be {size}mm × {size}mm")
            print(f"  - Corners should be square (90°)")
            print(f"  - Lines should be straight")
        else:
            print("\n❌ Test failed")
    
    async def test_circle(self, radius: float = 30.0, segments: int = 36):
        """
        Draw a test circle to verify calibration
        
        Args:
            radius: Radius in mm
            segments: Number of segments to approximate circle
        """
        print(f"\n{'='*60}")
        print(f"TEST PATTERN: CIRCLE (radius={radius}mm)")
        print('='*60)
        print()
        
        input("Press Enter to start, or Ctrl-C to cancel...")
        
        # Generate circle commands
        import math
        commands = ["N1 G28", "N2 M3 S60"]
        n = 3
        
        for i in range(segments + 1):
            angle = (i / segments) * 2 * math.pi
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            commands.append(f"N{n} G1 X{x:.2f} Y{y:.2f} F600")
            n += 1
        
        commands.append(f"N{n} M5")
        commands.append(f"N{n+1} G0 X0.00 Y0.00 F3000")
        
        print(f"Streaming {len(commands)} commands...")
        success = await self.sender.stream_commands(commands)
        
        if success:
            print(f"\n✅ Circle complete!")
            print(f"Measure the circle:")
            print(f"  - Diameter should be {radius*2}mm")
            print(f"  - Should be round, not oval")
        else:
            print("\n❌ Test failed")
    
    async def test_flow_ladder(self):
        """
        Draw flow calibration ladder
        Tests different flow rates (20%, 40%, 60%, 80%)
        """
        print(f"\n{'='*60}")
        print("FLOW CALIBRATION LADDER")
        print('='*60)
        print()
        print("This will draw 4 horizontal lines at different flow rates:")
        print("  Line 1: 20% flow")
        print("  Line 2: 40% flow")
        print("  Line 3: 60% flow")
        print("  Line 4: 80% flow")
        print()
        print("After drawing, measure the line widths to create flow curve.")
        print()
        
        input("Press Enter to start, or Ctrl-C to cancel...")
        
        # Generate ladder commands
        commands = ["N1 G28"]
        n = 2
        
        flows = [20, 40, 60, 80]
        line_length = 50.0
        spacing = 15.0
        
        for i, flow in enumerate(flows):
            y = i * spacing
            
            commands.append(f"N{n} G0 X0.00 Y{y:.2f} F3000")
            n += 1
            
            commands.append(f"N{n} M3 S{flow}")
            n += 1
            
            commands.append(f"N{n} G1 X{line_length:.2f} Y{y:.2f} F600")
            n += 1
            
            commands.append(f"N{n} M5")
            n += 1
        
        commands.append(f"N{n} G0 X0.00 Y0.00 F3000")
        
        print(f"Streaming {len(commands)} commands...")
        success = await self.sender.stream_commands(commands)
        
        if success:
            print(f"\n✅ Flow ladder complete!")
            print("\nMeasure the line widths:")
            print("  Line 1 (20%): ___ mm")
            print("  Line 2 (40%): ___ mm")
            print("  Line 3 (60%): ___ mm")
            print("  Line 4 (80%): ___ mm")
            print()
            print("Update config.py FLOW_CURVE with measured values")
        else:
            print("\n❌ Test failed")


# ============================================
# INTERACTIVE MENU
# ============================================

async def interactive_menu():
    """Interactive calibration menu"""
    
    print("\n" + "="*60)
    print("SRIRACHA SKETCHER CALIBRATION TOOL")
    print("="*60)
    print()
    
    # Get ESP32 IP
    ip = input(f"ESP32 IP address [{config.ESP32_IP}]: ").strip()
    if not ip:
        ip = config.ESP32_IP
    
    # Create calibrator
    cal = Calibrator(esp32_ip=ip)
    
    # Connect
    print(f"\nConnecting to {ip}...")
    if not await cal.connect():
        print("Failed to connect")
        return
    
    print("Connected!")
    
    # Main menu loop
    while True:
        print("\n" + "="*60)
        print("CALIBRATION MENU")
        print("="*60)
        print("1. Calibrate X axis steps/mm")
        print("2. Calibrate Y axis steps/mm")
        print("3. Test square pattern (50mm)")
        print("4. Test circle pattern (30mm radius)")
        print("5. Flow calibration ladder")
        print("6. Request status")
        print("0. Exit")
        print()
        
        choice = input("Select option: ").strip()
        
        try:
            if choice == '1':
                await cal.calibrate_steps_per_mm('X')
            elif choice == '2':
                await cal.calibrate_steps_per_mm('Y')
            elif choice == '3':
                await cal.test_square(50.0)
            elif choice == '4':
                await cal.test_circle(30.0)
            elif choice == '5':
                await cal.test_flow_ladder()
            elif choice == '6':
                await cal.sender.request_status()
                await asyncio.sleep(0.5)
            elif choice == '0':
                break
            else:
                print("Invalid option")
        
        except KeyboardInterrupt:
            print("\n\nOperation cancelled")
        except Exception as e:
            print(f"\nError: {e}")
    
    # Disconnect
    await cal.disconnect()
    print("\nGoodbye!")


if __name__ == "__main__":
    try:
        asyncio.run(interactive_menu())
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)


