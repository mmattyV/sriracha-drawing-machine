#!/usr/bin/env python3
"""
Test script for SVG to SSG conversion pipeline
Tests the new SSG-based motor control system with visualization

This script:
1. Loads an SVG file
2. Compiles it to SSG commands
3. Saves the SSG file
4. Simulates and visualizes the result
"""

import sys
from pathlib import Path

# Add motor_movement to path
sys.path.insert(0, str(Path(__file__).parent.parent / "motor_movement"))

from ssg_compiler import SSGCompiler
import config


def test_svg_to_ssg_pipeline(svg_file: str, output_name: str = None):
    """
    Complete test of SVG → SSG conversion with visualization
    
    Args:
        svg_file: Path to input SVG file
        output_name: Optional output filename (without extension)
    """
    svg_path = Path(svg_file)
    
    if not svg_path.exists():
        print(f"❌ Error: SVG file not found: {svg_file}")
        return False
    
    # Generate output filename
    if output_name:
        ssg_file = Path(__file__).parent / f"{output_name}.ssg"
    else:
        ssg_file = Path(__file__).parent / f"{svg_path.stem}_output.ssg"
    
    print("=" * 70)
    print("SVG TO SSG CONVERSION TEST")
    print("=" * 70)
    print()
    print(f"📄 Input:  {svg_path}")
    print(f"📄 Output: {ssg_file}")
    print()
    
    # Step 1: Compile SVG to SSG
    print("STEP 1: COMPILING SVG")
    print("-" * 70)
    
    compiler = SSGCompiler()
    
    try:
        compiler.load_svg(str(svg_path), scale=1.0)
        compiler.normalize()
        compiler.simplify()
        compiler.optimize_path_order()
        ssg_commands = compiler.compile_to_ssg()
        compiler.save_ssg(str(ssg_file))
        
        # Get statistics
        stats = compiler.get_statistics()
        
        print()
        print("✅ Compilation Results:")
        print(f"   Paths: {stats['num_paths']}")
        print(f"   SSG Commands: {stats['num_commands']}")
        print(f"   Total length: {stats['total_length_mm']:.1f} mm")
        print(f"   Rapid moves: {stats['rapid_moves']}")
        print(f"   Draw moves: {stats['draw_moves']}")
        print(f"   Estimated time: {stats['estimated_time_sec']:.1f}s ({stats['estimated_time_sec']/60:.1f} min)")
        
        if stats['warnings']:
            print()
            print("⚠️  Warnings:")
            for warning in stats['warnings']:
                print(f"   • {warning}")
        
        print()
        
    except Exception as e:
        print(f"❌ Compilation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 2: Validate against design constraints
    print()
    print("STEP 2: DESIGN CONSTRAINTS VALIDATION")
    print("-" * 70)
    
    # Bounds check
    all_x = [p.x for path in compiler.paths for p in path.points]
    all_y = [p.y for path in compiler.paths for p in path.points]
    
    if all_x and all_y:
        width = max(all_x) - min(all_x)
        height = max(all_y) - min(all_y)
        
        print(f"📏 Drawing size: {width:.1f}mm × {height:.1f}mm")
        print(f"   Max allowed: {config.CANVAS_WIDTH_MM}mm × {config.CANVAS_HEIGHT_MM}mm")
        
        if width <= config.CANVAS_WIDTH_MM and height <= config.CANVAS_HEIGHT_MM:
            print("   ✅ Size OK")
        else:
            print("   ⚠️  WARNING: Drawing may be too large for plate!")
        
        # Check plate radius
        import math
        max_dist = max(math.sqrt(x**2 + y**2) for x, y in zip(all_x, all_y))
        print(f"   Max distance from center: {max_dist:.1f}mm")
        print(f"   Plate radius: {config.PLATE_RADIUS_MM}mm")
        
        if max_dist <= config.PLATE_RADIUS_MM:
            print("   ✅ Fits within plate")
        else:
            print("   ⚠️  WARNING: Some points outside plate boundary!")
    
    # Complexity check
    print()
    print(f"📊 Complexity:")
    print(f"   Total commands: {stats['num_commands']}")
    print(f"   Max allowed: {config.MAX_COMMANDS_PER_JOB}")
    
    if stats['num_commands'] <= config.MAX_COMMANDS_PER_JOB:
        print("   ✅ Complexity OK")
    else:
        print("   ⚠️  WARNING: Too many commands!")
    
    print()
    
    # Step 3: Show preview of SSG commands
    print()
    print("STEP 3: SSG COMMAND PREVIEW")
    print("-" * 70)
    print()
    print("First 15 commands:")
    for i, cmd in enumerate(ssg_commands[:15]):
        print(f"  {cmd}")
    
    if len(ssg_commands) > 15:
        print(f"  ... ({len(ssg_commands) - 15} more commands)")
    
    print()
    
    # Step 4: Simulate and visualize
    print()
    print("STEP 4: SIMULATION & VISUALIZATION")
    print("-" * 70)
    print()
    
    try:
        from ssg_simulator import SSGSimulator
        
        # Create simulator
        sim = SSGSimulator(ssg_file)
        
        # Simulate
        sim.simulate()
        sim.analyze()
        
        # Generate visualizations
        print()
        print("Generating visualizations...")
        sim.plot(show_travel=True, show_grid=True, show_plate=True)
        sim.plot_time_sequence()
        
        print()
        print("✅ Visualizations saved:")
        print(f"   • {ssg_file.parent / 'simulation_preview.png'}")
        print(f"   • {ssg_file.parent / 'simulation_sequence.png'}")
        
    except ImportError:
        print("⚠️  matplotlib not installed - skipping visualization")
        print("   Install with: pip install matplotlib")
    except Exception as e:
        print(f"⚠️  Visualization failed: {e}")
    
    print()
    
    # Summary
    print("=" * 70)
    print("✅ TEST COMPLETE!")
    print("=" * 70)
    print()
    print("Output files created:")
    print(f"  • {ssg_file}")
    print(f"  • {ssg_file.parent / 'simulation_preview.png'}")
    print(f"  • {ssg_file.parent / 'simulation_sequence.png'}")
    print()
    print("Next steps:")
    print("  1. Review the visualizations")
    print("  2. If OK, use with test_end_to_end.py:")
    print(f"     python ../motor_movement/test_end_to_end.py {svg_path}")
    print()
    
    return True


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test SVG to SSG conversion with visualization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with best_result.svg from image generator
  python test_svg_to_ssg.py ../svgs/best_result.svg
  
  # Test with specific output name
  python test_svg_to_ssg.py ../svgs/best_result.svg --output my_test
  
  # Test with motor_movement test patterns
  python test_svg_to_ssg.py ../motor_movement/test_square.svg
        """
    )
    
    parser.add_argument("svg_file", help="Input SVG file")
    parser.add_argument("--output", "-o", help="Output name (without .ssg extension)")
    
    args = parser.parse_args()
    
    success = test_svg_to_ssg_pipeline(args.svg_file, args.output)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

