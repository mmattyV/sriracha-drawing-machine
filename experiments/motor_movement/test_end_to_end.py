#!/usr/bin/env python3
"""
End-to-end test for Sriracha Sketcher
Tests the complete pipeline: SVG → SSG → ESP32
"""

import asyncio
import sys
from pathlib import Path

from ssg_compiler import SSGCompiler
from ssg_sender import SSGSender
import config


async def test_complete_pipeline(svg_file: str, esp32_ip: str = None):
    """
    Complete pipeline test: SVG → SSG compilation → ESP32 streaming
    
    Args:
        svg_file: Path to input SVG file
        esp32_ip: ESP32 IP address (optional, uses config default)
    """
    print("\n" + "="*70)
    print("SRIRACHA SKETCHER - END-TO-END TEST")
    print("="*70)
    print()
    
    # Step 1: Compile SVG to SSG
    print("STEP 1: COMPILING SVG TO SSG")
    print("-"*70)
    
    compiler = SSGCompiler()
    
    try:
        compiler.load_svg(svg_file, scale=1.0)
        compiler.normalize()
        compiler.simplify()
        compiler.optimize_path_order()
        ssg_commands = compiler.compile_to_ssg()
        
        # Save SSG file
        ssg_file = svg_file.replace('.svg', '_output.ssg')
        compiler.save_ssg(ssg_file)
        
        # Print stats
        stats = compiler.get_statistics()
        print()
        print("Compilation Results:")
        print(f"  Paths: {stats['num_paths']}")
        print(f"  Commands: {stats['num_commands']}")
        print(f"  Total length: {stats['total_length_mm']:.1f} mm")
        print(f"  Estimated time: {stats['estimated_time_sec']:.1f}s ({stats['estimated_time_sec']/60:.1f} min)")
        
        if stats['warnings']:
            print("\n  Warnings:")
            for warning in stats['warnings']:
                print(f"    ⚠️  {warning}")
        
        print(f"\n✅ SSG compiled successfully: {ssg_file}")
        
    except Exception as e:
        print(f"\n❌ Compilation failed: {e}")
        return False
    
    # Step 2: Connect to ESP32
    print("\n" + "="*70)
    print("STEP 2: CONNECTING TO ESP32")
    print("-"*70)
    
    sender = SSGSender(esp32_ip=esp32_ip or config.ESP32_IP)
    
    # Set up callbacks
    last_progress = -1
    
    def on_progress(progress, acked, total):
        nonlocal last_progress
        current_progress = int(progress * 10)
        if current_progress != last_progress:
            bar_length = 50
            filled = int(bar_length * progress)
            bar = '█' * filled + '░' * (bar_length - filled)
            print(f"\r  [{bar}] {progress*100:.1f}% ({acked}/{total})", end='')
            last_progress = current_progress
    
    def on_telemetry(data):
        # Update position display (optional)
        pass
    
    def on_error(msg):
        print(f"\n  ❌ ESP32 Error: {msg}")
    
    sender.on_progress = on_progress
    sender.on_telemetry = on_telemetry
    sender.on_error = on_error
    
    if not await sender.connect():
        print(f"\n❌ Failed to connect to ESP32 at {sender.uri}")
        print("\nTroubleshooting:")
        print("  1. Check ESP32 is powered on")
        print("  2. Verify WiFi connection")
        print("  3. Confirm IP address in config.py")
        print("  4. Check firewall settings")
        return False
    
    print(f"✅ Connected to ESP32 at {sender.uri}")
    
    # Step 3: Home the machine
    print("\n" + "="*70)
    print("STEP 3: HOMING MACHINE")
    print("-"*70)
    
    print("Sending G28 (home all axes)...")
    await sender.send_home()
    
    print("Waiting for homing to complete (15 seconds)...")
    await asyncio.sleep(15)
    
    print("✅ Homing complete")
    
    # Step 4: Stream SSG commands
    print("\n" + "="*70)
    print("STEP 4: STREAMING SSG COMMANDS")
    print("-"*70)
    print()
    
    success = await sender.stream_commands(ssg_commands)
    
    if success:
        print("\n\n✅ Streaming complete!")
    else:
        print("\n\n❌ Streaming failed")
    
    # Step 5: Disconnect
    print("\n" + "="*70)
    print("STEP 5: CLEANUP")
    print("-"*70)
    
    await sender.disconnect()
    print("✅ Disconnected from ESP32")
    
    # Final summary
    print("\n" + "="*70)
    if success:
        print("✅ END-TO-END TEST PASSED")
    else:
        print("❌ END-TO-END TEST FAILED")
    print("="*70)
    print()
    
    return success


async def dry_run_test(svg_file: str):
    """
    Dry run test: compile SVG and validate, but don't send to ESP32
    
    Args:
        svg_file: Path to input SVG file
    """
    print("\n" + "="*70)
    print("DRY RUN TEST - SVG COMPILATION ONLY")
    print("="*70)
    print()
    
    compiler = SSGCompiler()
    
    try:
        print("Loading and compiling SVG...")
        compiler.load_svg(svg_file, scale=1.0)
        compiler.normalize()
        compiler.simplify()
        compiler.optimize_path_order()
        ssg_commands = compiler.compile_to_ssg()
        
        # Save SSG file
        ssg_file = svg_file.replace('.svg', '_dryrun.ssg')
        compiler.save_ssg(ssg_file)
        
        # Print detailed stats
        stats = compiler.get_statistics()
        
        print("\n" + "="*70)
        print("COMPILATION RESULTS")
        print("="*70)
        print(f"Paths: {stats['num_paths']}")
        print(f"SSG Commands: {stats['num_commands']}")
        print(f"Total Length: {stats['total_length_mm']:.1f} mm")
        print(f"Rapid Moves: {stats['rapid_moves']}")
        print(f"Draw Moves: {stats['draw_moves']}")
        print(f"Estimated Time: {stats['estimated_time_sec']:.1f}s ({stats['estimated_time_sec']/60:.1f} min)")
        
        print(f"\nOutput saved to: {ssg_file}")
        
        if stats['warnings']:
            print("\n⚠️  WARNINGS:")
            for warning in stats['warnings']:
                print(f"  • {warning}")
        else:
            print("\n✅ No warnings - drawing should be printable")
        
        # Show first few commands
        print("\n" + "="*70)
        print("FIRST 10 SSG COMMANDS:")
        print("="*70)
        for i, cmd in enumerate(ssg_commands[:10]):
            print(f"  {cmd}")
        if len(ssg_commands) > 10:
            print(f"  ... ({len(ssg_commands) - 10} more commands)")
        
        print("\n✅ Dry run complete")
        return True
        
    except Exception as e:
        print(f"\n❌ Compilation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================
# CLI INTERFACE
# ============================================

async def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="End-to-end test for Sriracha Sketcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (compile only, don't send to ESP32)
  python test_end_to_end.py drawing.svg --dry-run
  
  # Full test (compile and send to ESP32)
  python test_end_to_end.py drawing.svg
  
  # Full test with custom IP
  python test_end_to_end.py drawing.svg --ip 192.168.1.100
        """
    )
    
    parser.add_argument("svg_file", help="Input SVG file")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Compile only, don't send to ESP32")
    parser.add_argument("--ip", help="ESP32 IP address (overrides config.py)")
    
    args = parser.parse_args()
    
    # Check file exists
    if not Path(args.svg_file).exists():
        print(f"❌ File not found: {args.svg_file}")
        return 1
    
    # Run test
    try:
        if args.dry_run:
            success = await dry_run_test(args.svg_file)
        else:
            success = await test_complete_pipeline(args.svg_file, args.ip)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

