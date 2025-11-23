#!/usr/bin/env python3
"""
Plotter Simulator - Visualize motor instructions using matplotlib
Shows pen-down paths (drawing) and pen-up paths (travel) in different colors
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import sys
import numpy as np
from matplotlib.colors import LinearSegmentedColormap


class PlotterSimulator:
    def __init__(self, instructions_file):
        """Initialize simulator with instruction file"""
        self.instructions_file = Path(instructions_file)
        self.instructions = []
        self.load_instructions()
    
    def load_instructions(self):
        """Load motor instructions from JSON file"""
        print(f"📄 Loading instructions from: {self.instructions_file}")
        
        with open(self.instructions_file, 'r') as f:
            self.instructions = json.load(f)
        
        print(f"✓ Loaded {len(self.instructions)} instructions")
        print()
    
    def analyze_instructions(self):
        """Analyze the instruction set"""
        if not self.instructions:
            return
        
        pen_down_count = sum(1 for inst in self.instructions if inst['penDown'])
        pen_up_count = len(self.instructions) - pen_down_count
        
        x_coords = [inst['x'] for inst in self.instructions]
        y_coords = [inst['y'] for inst in self.instructions]
        
        stats = {
            'total': len(self.instructions),
            'pen_down': pen_down_count,
            'pen_up': pen_up_count,
            'min_x': min(x_coords),
            'max_x': max(x_coords),
            'min_y': min(y_coords),
            'max_y': max(y_coords),
            'width': max(x_coords) - min(x_coords),
            'height': max(y_coords) - min(y_coords)
        }
        
        print("📊 Instruction Analysis:")
        print(f"   Total moves: {stats['total']}")
        print(f"   Drawing moves (pen down): {stats['pen_down']}")
        print(f"   Travel moves (pen up): {stats['pen_up']}")
        print()
        print(f"📏 Bounds (in motor steps):")
        print(f"   X: {stats['min_x']:.1f} to {stats['max_x']:.1f} (width: {stats['width']:.1f})")
        print(f"   Y: {stats['min_y']:.1f} to {stats['max_y']:.1f} (height: {stats['height']:.1f})")
        print()
        
        return stats
    
    def plot(self, show_travel=True, show_grid=True, show_plate=True, steps_per_mm=10.0):
        """
        Plot the instructions - Standard view with pen up/down
        
        Args:
            show_travel: Show pen-up travel moves
            show_grid: Show grid lines
            show_plate: Show plate boundary (220mm circle)
            steps_per_mm: Motor steps per mm for scale conversion
        """
        print("🎨 Generating standard visualization...")
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 12))
        
        # Convert steps to mm for display
        instructions_mm = [
            {
                'x': inst['x'] / steps_per_mm,
                'y': inst['y'] / steps_per_mm,
                'penDown': inst['penDown']
            }
            for inst in self.instructions
        ]
        
        # Separate pen-down and pen-up segments
        current_segment = []
        pen_down_segments = []
        pen_up_segments = []
        
        for i, inst in enumerate(instructions_mm):
            current_segment.append((inst['x'], inst['y']))
            
            # When pen state changes or end of instructions
            if i < len(instructions_mm) - 1:
                next_inst = instructions_mm[i + 1]
                if inst['penDown'] != next_inst['penDown']:
                    # Segment complete
                    if inst['penDown']:
                        pen_down_segments.append(current_segment[:])
                    else:
                        pen_up_segments.append(current_segment[:])
                    current_segment = [current_segment[-1]]  # Start next segment at current point
            else:
                # Last instruction
                if inst['penDown']:
                    pen_down_segments.append(current_segment)
                else:
                    pen_up_segments.append(current_segment)
        
        # Plot pen-down segments (drawing - red/sauce color)
        for segment in pen_down_segments:
            if len(segment) > 1:
                xs, ys = zip(*segment)
                ax.plot(xs, ys, 'r-', linewidth=2.5, label='Drawing (pen down)', 
                       solid_capstyle='round', zorder=3)
        
        # Plot pen-up segments (travel - blue dashed)
        if show_travel:
            for segment in pen_up_segments:
                if len(segment) > 1:
                    xs, ys = zip(*segment)
                    ax.plot(xs, ys, 'b--', linewidth=1.0, alpha=0.5, 
                           label='Travel (pen up)', zorder=2)
        
        # Mark start point (green)
        start = instructions_mm[0]
        ax.plot(start['x'], start['y'], 'go', markersize=12, 
               label='Start', zorder=5, markeredgecolor='darkgreen', markeredgewidth=2)
        
        # Mark end point (black)
        end = instructions_mm[-1]
        ax.plot(end['x'], end['y'], 'ko', markersize=12, 
               label='End', zorder=5, markeredgecolor='white', markeredgewidth=2)
        
        # Show plate boundary (220mm diameter circle centered at origin)
        if show_plate:
            plate_radius = 110  # mm (220mm diameter)
            circle = patches.Circle((0, 0), plate_radius, 
                                   fill=False, edgecolor='gray', 
                                   linewidth=2, linestyle=':', 
                                   label='Plate boundary (220mm)')
            ax.add_patch(circle)
            
            # Show safe drawing area (slightly smaller)
            safe_radius = 100  # mm
            safe_circle = patches.Circle((0, 0), safe_radius, 
                                        fill=False, edgecolor='lightgray', 
                                        linewidth=1, linestyle=':', 
                                        alpha=0.5)
            ax.add_patch(safe_circle)
        
        # Configure axes
        ax.set_aspect('equal')
        ax.set_xlabel('X (mm)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Y (mm)', fontsize=12, fontweight='bold')
        ax.set_title('Plotter Simulation - Standard View', fontsize=16, fontweight='bold', pad=20)
        
        # Grid
        if show_grid:
            ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            ax.set_axisbelow(True)
        
        # Set axis limits to show full plate area
        if show_plate:
            ax.set_xlim(-120, 120)
            ax.set_ylim(-120, 120)
        else:
            all_x = [inst['x'] for inst in instructions_mm]
            all_y = [inst['y'] for inst in instructions_mm]
            padding = 20  # mm
            ax.set_xlim(min(all_x) - padding, max(all_x) + padding)
            ax.set_ylim(min(all_y) - padding, max(all_y) + padding)
        
        # Remove duplicate labels in legend
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), 
                 loc='upper right', fontsize=11, framealpha=0.95)
        
        # Add info text
        info_text = (
            f"Total moves: {len(self.instructions)}\n"
            f"Drawing: {sum(1 for i in instructions_mm if i['penDown'])} moves\n"
            f"Travel: {sum(1 for i in instructions_mm if not i['penDown'])} moves"
        )
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
               fontsize=11, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9))
        
        plt.tight_layout()
        
        # Save figure
        output_file = self.instructions_file.parent / "simulation_preview.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"💾 Saved visualization to: {output_file}")
        
        return fig, ax
    
    def plot_time_sequence(self, steps_per_mm=10.0):
        """
        Create a time-sequence visualization showing drawing order
        Uses color gradient to show the drawing sequence
        """
        print("🎨 Generating time-sequence visualization...")
        
        fig, ax = plt.subplots(figsize=(12, 12))
        
        # Convert to mm
        instructions_mm = [
            {
                'x': inst['x'] / steps_per_mm,
                'y': inst['y'] / steps_per_mm,
                'penDown': inst['penDown']
            }
            for inst in self.instructions
        ]
        
        # Create colormap from blue (start) to red (end)
        colors = ['blue', 'cyan', 'green', 'yellow', 'orange', 'red']
        n_bins = 100
        cmap = LinearSegmentedColormap.from_list('drawing_time', colors, N=n_bins)
        
        # Plot each segment with time-based color
        for i in range(len(instructions_mm) - 1):
            curr = instructions_mm[i]
            next_inst = instructions_mm[i + 1]
            
            if curr['penDown']:
                # Calculate time fraction (0 to 1)
                time_fraction = i / len(instructions_mm)
                color = cmap(time_fraction)
                
                ax.plot([curr['x'], next_inst['x']], 
                       [curr['y'], next_inst['y']], 
                       color=color, linewidth=2.5, 
                       solid_capstyle='round', zorder=3)
        
        # Add colorbar to show time
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 1))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Drawing Progress (Start → End)', fontsize=12, fontweight='bold')
        
        # Mark start and end
        start = instructions_mm[0]
        end = instructions_mm[-1]
        ax.plot(start['x'], start['y'], 'o', color='blue', markersize=15, 
               label='Start', zorder=5, markeredgecolor='white', markeredgewidth=2)
        ax.plot(end['x'], end['y'], 'o', color='red', markersize=15, 
               label='End', zorder=5, markeredgecolor='white', markeredgewidth=2)
        
        # Show plate boundary
        plate_radius = 110
        circle = patches.Circle((0, 0), plate_radius, 
                               fill=False, edgecolor='gray', 
                               linewidth=2, linestyle=':', 
                               label='Plate boundary')
        ax.add_patch(circle)
        
        ax.set_aspect('equal')
        ax.set_xlabel('X (mm)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Y (mm)', fontsize=12, fontweight='bold')
        ax.set_title('Drawing Sequence (Color = Time)', fontsize=16, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-120, 120)
        ax.set_ylim(-120, 120)
        ax.legend(loc='upper right', fontsize=11, framealpha=0.95)
        
        plt.tight_layout()
        
        # Save
        output_file = self.instructions_file.parent / "simulation_sequence.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"💾 Saved sequence visualization to: {output_file}")
        
        return fig, ax


def main():
    """Main function"""
    print("=" * 70)
    print("PLOTTER SIMULATOR (MATPLOTLIB)")
    print("=" * 70)
    print()
    
    # Get instructions file
    if len(sys.argv) > 1:
        instructions_file = sys.argv[1]
    else:
        # Default to test output
        instructions_file = Path(__file__).parent / "test_output_instructions.json"
    
    if not Path(instructions_file).exists():
        print(f"❌ Error: Instructions file not found: {instructions_file}")
        print()
        print("Usage: python plot_simulator.py [instructions.json]")
        print()
        print("Example:")
        print("  python plot_simulator.py test_output_instructions.json")
        return
    
    # Create simulator
    sim = PlotterSimulator(instructions_file)
    
    # Analyze
    sim.analyze_instructions()
    
    # Plot standard view
    print("Creating standard visualization...")
    fig1, ax1 = sim.plot(show_travel=True, show_grid=True, show_plate=True, steps_per_mm=10.0)
    
    # Plot time-sequence view
    print("Creating time-sequence visualization...")
    fig2, ax2 = sim.plot_time_sequence(steps_per_mm=10.0)
    
    print()
    print("=" * 70)
    print("SIMULATION COMPLETE!")
    print("=" * 70)
    print()
    print("Two visualizations created:")
    print("  1. simulation_preview.png - Standard view with pen up/down")
    print("  2. simulation_sequence.png - Time-based color gradient")
    print()
    print("📺 Displaying plots...")
    plt.show()


if __name__ == "__main__":
    main()
