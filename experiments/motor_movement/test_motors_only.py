#!/usr/bin/env python3
"""
Test motor movement in TESTING_MODE (no homing required)
"""

import asyncio
import config
from ssg_sender import SSGSender


async def test_motors():
    """Send simple movement commands and watch Serial Monitor"""
    
    print("="*60)
    print("MOTOR MOVEMENT TEST (TESTING MODE)")
    print("="*60)
    print(f"Connecting to {config.ESP32_IP}...")
    
    sender = SSGSender(config.ESP32_IP)
    
    if not await sender.connect():
        print("❌ Failed to connect")
        return
    
    print("✅ Connected!")
    print()
    print("⚠️  WATCH THE SERIAL MONITOR NOW!")
    print("    You should see command messages as they execute")
    print()
    await asyncio.sleep(1)
    
    # Test 1: Simple status check
    print("Test 1: Checking status...")
    await sender.websocket.send("N1 M408")
    response = await asyncio.wait_for(sender.websocket.recv(), timeout=2.0)
    print(f"  Response: {response}")
    await asyncio.sleep(1)
    
    # Test 2: Small X movement
    print("\nTest 2: Moving X+10mm (SLOW)...")
    print("  → Motors should move now!")
    await sender.websocket.send("N2 G1 X10.00 F300")
    response = await asyncio.wait_for(sender.websocket.recv(), timeout=2.0)
    print(f"  Response: {response}")
    await asyncio.sleep(3)  # Wait for move to complete
    
    # Test 3: Small Y movement  
    print("\nTest 3: Moving Y+10mm (SLOW)...")
    print("  → Motors should move now!")
    await sender.websocket.send("N3 G1 Y10.00 F300")
    response = await asyncio.wait_for(sender.websocket.recv(), timeout=2.0)
    print(f"  Response: {response}")
    await asyncio.sleep(3)
    
    # Test 4: Return to origin
    print("\nTest 4: Returning to X0 Y0...")
    await sender.websocket.send("N4 G1 X0.00 Y0.00 F300")
    response = await asyncio.wait_for(sender.websocket.recv(), timeout=2.0)
    print(f"  Response: {response}")
    await asyncio.sleep(4)
    
    # Test 5: Sauce on/off
    print("\nTest 5: Testing sauce control...")
    await sender.websocket.send("N5 M3 S50")
    response = await asyncio.wait_for(sender.websocket.recv(), timeout=2.0)
    print(f"  Sauce ON response: {response}")
    await asyncio.sleep(2)
    
    await sender.websocket.send("N6 M5")
    response = await asyncio.wait_for(sender.websocket.recv(), timeout=2.0)
    print(f"  Sauce OFF response: {response}")
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETE!")
    print("="*60)
    print("\nCheck Serial Monitor - you should see:")
    print("  - Command acknowledgements (ok N1, ok N2, etc)")
    print("  - Sauce ON/OFF messages")
    print("  - Position updates")
    print("  - Telemetry every second")
    
    await sender.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(test_motors())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

