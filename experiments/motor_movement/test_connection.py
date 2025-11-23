#!/usr/bin/env python3
"""
Simple connection test - verifies basic WebSocket communication
"""

import asyncio
import config
from ssg_sender import SSGSender


async def test_connection():
    """Test basic ESP32 connection and commands"""
    
    print("="*60)
    print("ESP32 CONNECTION TEST")
    print("="*60)
    print()
    
    sender = SSGSender(config.ESP32_IP)
    
    # Test 1: Connect
    print("Test 1: Connecting to ESP32...")
    if not await sender.connect():
        print("❌ Failed to connect")
        return
    print("✅ Connected!")
    await asyncio.sleep(1)
    
    # Test 2: Request status
    print("\nTest 2: Requesting status...")
    try:
        await sender.websocket.send("N0 M408")
        response = await asyncio.wait_for(sender.websocket.recv(), timeout=2.0)
        print(f"✅ Response: {response}")
    except asyncio.TimeoutError:
        print("❌ No response (timeout)")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    await asyncio.sleep(1)
    
    # Test 3: Request position
    print("\nTest 3: Requesting position...")
    try:
        await sender.websocket.send("N0 M114")
        response = await asyncio.wait_for(sender.websocket.recv(), timeout=2.0)
        print(f"✅ Response: {response}")
    except asyncio.TimeoutError:
        print("❌ No response (timeout)")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    await asyncio.sleep(1)
    
    # Test 4: Simple sauce on/off
    print("\nTest 4: Testing sauce control...")
    try:
        # Sauce on
        await sender.websocket.send("N0 M3 S30")
        response = await asyncio.wait_for(sender.websocket.recv(), timeout=2.0)
        print(f"  M3 response: {response}")
        
        await asyncio.sleep(2)
        
        # Sauce off
        await sender.websocket.send("N0 M5")
        response = await asyncio.wait_for(sender.websocket.recv(), timeout=2.0)
        print(f"  M5 response: {response}")
        
        print("✅ Sauce control works!")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    await asyncio.sleep(1)
    
    # Test 5: Disconnect
    print("\nTest 5: Disconnecting...")
    await sender.disconnect()
    print("✅ Disconnected cleanly")
    
    print("\n" + "="*60)
    print("CONNECTION TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    try:
        asyncio.run(test_connection())
    except KeyboardInterrupt:
        print("\n\nTest cancelled")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

