#!/usr/bin/env python3
"""
SSG Simulator - Visualize SSG commands using matplotlib
Shows G1 paths (drawing with sauce) and G0 paths (rapid travel) in different colors

Works with the new SSG-based motor control system
"""

import re
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import sys
import numpy as np
from matplotlib.colors import LinearSegmentedColormap


class SSGSimulator:
    """Simulate and visualize SSG (Sauce Simple G-code) commands"""
    
    def __init__(self, ssg_file):
        """Initialize simulator with SSG file"""
        self.ssg_file = Path(ssg_file)
        self.commands = []
        self.positions = []  # List of (x, y, is_drawing) tuples
        self.load_ssg()
    
    def load_ssg(self):
        """Load SSG commands from file"""
        print(f"📄 Loading SSG from: {self.ssg_file}")
        
        with open(self.ssg_file, 'r') as f:
            self.commands = [line.strip() for line in f if line.strip()]
        
        print(f"✓ Loaded {len(self.commands)} commands")
        print()
    
    def parse_ssg_command(self, line):
        """Parse a single SSG command line"""
        # Remove sequence number if present (N123)
        if line.startswith('N'):
            parts = line.split(' ', 1)
            if len(parts) > 1:
                line = parts[1]
        
        # Parse command type
        cmd_match = re.match(r'^([GM])(\d+)', line)
        if not cmd_match:
            return None
        
        cmd_type = cmd_match.group(1)
        cmd_num = int(cmd_match.group(2))
        
        # Parse parameters
        params = {}
        
        x_match = re.search(r'X([-+]?\d*\.?\d+)', line)
        if x_match:
            params['x'] = float(x_match.group(1))
        
        y_match = re.search(r'Y([-+]?\d*\.?\d+)', line)
        if y_match:
            params['y'] = float(y_match.group(1))
        
        f_match = re.search(r'F([-+]?\d*\.?\d+)', line)
        if f_match:
            params['f'] = float(f_match.group(1))
        
        s_match = re.search(r'S([-+]?\d*\.?\d+)', line)
        if s_match:
            params['s'] = float(s_match.group(1))
        
        return {
            'type': cmd_type,
            'num': cmd_num,
            'params': params
        }
    
    def simulate(self):
        """
        Simulate SSG commands to extract positions
        Returns list of (x, y, is_drawing) tuples
        """
        print("🎮 Simulating SSG commands...")
        
        current_x = 0.0
        current_y = 0.0
        sauce_on = False
        positions = []
        
        # Add starting position
        positions.append((current_x, current_y, False))
        
        for cmd_line in self.commands:
            cmd = self.parse_ssg_command(cmd_line)
            
            if not cmd:
                continue
            
            if cmd['type'] == 'G':
                if cmd['num'] == 0:  # G0 - Rapid (sauce off)
                    if 'x' in cmd['params']:
                        current_x = cmd['params']['x']
                    if 'y' in cmd['params']:
                        current_y = cmd['params']['y']
                    positions.append((current_x, current_y, False))
                
                elif cmd['num'] == 1:  # G1 - Linear (drawing)
                    if 'x' in cmd['params']:
                        current_x = cmd['params']['x']
                    if 'y' in cmd['params']:
                        current_y = cmd['params']['y']
                    positions.append((current_x, current_y, sauce_on))
                
                elif cmd['num'] == 28:  # G28 - Home
                    current_x = 0.0
                    current_y = 0.0
                    positions.append((current_x, current_y, False))
            
            elif cmd['type'] == 'M':
                if cmd['num'] == 3:  # M3 - Sauce on
                    sauce_on = True
                elif cmd['num'] == 5:  # M5 - Sauce off
                    sauce_on = False
        
        self.positions = positions
        print(f"✓ Simulated {len(positions)} positions")
        print()
        
        return positions
    
    def analyze(self):
        """Analyze the simulated path"""
        if not self.positions:
            return
        
        drawing_count = sum(1 for _, _, is_drawing in self.positions if is_drawing)
        travel_count = len(self.positions) - drawing_count
        
        x_coords = [x for x, _, _ in self.positions]
        y_coords = [y for _, y, _ in self.positions]
        
        stats = {
            'total': len(self.positions),
            'drawing': drawing_count,
            'travel': travel_count,
            'min_x': min(x_coords),
            'max_x': max(x_coords),
            'min_y': min(y_coords),
            'max_y': max(y_coords),
            'width': max(x_coords) - min(x_coords),
            'height': max(y_coords) - min(y_coords)
        }
        
        print("📊 Path Analysis:")
        print(f"   Total positions: {stats['total']}")
        print(f"   Drawing positions: {stats['drawing']}")
        print(f"   Travel positions: {stats['travel']}")
        print()
        print(f"📏 Bounds (in mm):")
        print(f"   X: {stats['min_x']:.2f} to {stats['max_x']:.2f} (width: {stats['width']:.2f})")
        print(f"   Y: {stats['min_y']:.2f} to {stats['max_y']:.2f} (height: {stats['height']:.2f})")
        print()
        
        return stats
    
    def plot(self, show_travel=True, show_grid=True, show_plate=True):
        """
        Plot the simulated path - Standard view
        
        Args:
            show_travel: Show rapid travel moves (G0)
            show_grid: Show grid lines
            show_plate: Show plate boundary (220mm circle)
        """
        print("🎨 Generating standard visualization...")
        
        if not self.positions:
            self.simulate()
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 12))
        
        # Separate drawing and travel segments
        current_segment = []
        drawing_segments = []
        travel_segments = []
        
        for i, (x, y, is_drawing) in enumerate(self.positions):
            current_segment.append((x, y))
            
            # When state changes or end of positions
            if i < len(self.positions) - 1:
                next_is_drawing = self.positions[i + 1][2]
                if is_drawing != next_is_drawing:
                    # Segment complete
                    if is_drawing:
                        drawing_segments.append(current_segment[:])
                    else:
                        travel_segments.append(current_segment[:])
                    current_segment = [current_segment[-1]]  # Start next at current point
            else:
                # Last position
                if is_drawing:
                    drawing_segments.append(current_segment)
                else:
                    travel_segments.append(current_segment)
        
        # Plot drawing segments (G1 with sauce - red/sauce color)
        for segment in drawing_segments:
            if len(segment) > 1:
                xs, ys = zip(*segment)
                ax.plot(xs, ys, 'r-', linewidth=3.0, label='Drawing (G1, sauce on)', 
                       solid_capstyle='round', zorder=3, alpha=0.8)
        
        # Plot travel segments (G0 rapid - blue dashed)
        if show_travel:
            for segment in travel_segments:
                if len(segment) > 1:
                    xs, ys = zip(*segment)
                    ax.plot(xs, ys, 'b--', linewidth=1.0, alpha=0.5, 
                           label='Travel (G0, rapid)', zorder=2)
        
        # Mark start point (green)
        start_x, start_y, _ = self.positions[0]
        ax.plot(start_x, start_y, 'go', markersize=12, 
               label='Start', zorder=5, markeredgecolor='darkgreen', markeredgewidth=2)
        
        # Mark end point (black)
        end_x, end_y, _ = self.positions[-1]
        ax.plot(end_x, end_y, 'ko', markersize=12, 
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
        ax.set_title('SSG Simulation - Standard View', fontsize=16, fontweight='bold', pad=20)
        
        # Grid
        if show_grid:
            ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            ax.set_axisbelow(True)
        
        # Set axis limits to show full plate area
        if show_plate:
            ax.set_xlim(-120, 120)
            ax.set_ylim(-120, 120)
        else:
            all_x = [x for x, _, _ in self.positions]
            all_y = [y for _, y, _ in self.positions]
            padding = 20  # mm
            ax.set_xlim(min(all_x) - padding, max(all_x) + padding)
            ax.set_ylim(min(all_y) - padding, max(all_y) + padding)
        
        # Remove duplicate labels in legend
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), 
                 loc='upper right', fontsize=11, framealpha=0.95)
        
        # Add info text
        drawing_count = sum(1 for _, _, is_drawing in self.positions if is_drawing)
        info_text = (
            f"Total SSG commands: {len(self.commands)}\n"
            f"Positions: {len(self.positions)}\n"
            f"Drawing: {drawing_count} positions\n"
            f"Travel: {len(self.positions) - drawing_count} positions"
        )
        ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
               fontsize=11, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9))
        
        plt.tight_layout()
        
        # Save figure
        output_file = self.ssg_file.parent / "simulation_preview.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"💾 Saved visualization to: {output_file}")
        
        return fig, ax
    
    def plot_time_sequence(self):
        """
        Create a time-sequence visualization showing drawing order
        Uses color gradient to show the drawing sequence
        """
        print("🎨 Generating time-sequence visualization...")
        
        if not self.positions:
            self.simulate()
        
        fig, ax = plt.subplots(figsize=(12, 12))
        
        # Create colormap from blue (start) to red (end)
        colors = ['blue', 'cyan', 'green', 'yellow', 'orange', 'red']
        n_bins = 100
        cmap = LinearSegmentedColormap.from_list('drawing_time', colors, N=n_bins)
        
        # Plot each segment with time-based color
        for i in range(len(self.positions) - 1):
            x1, y1, is_drawing1 = self.positions[i]
            x2, y2, is_drawing2 = self.positions[i + 1]
            
            if is_drawing1 or is_drawing2:
                # Calculate time fraction (0 to 1)
                time_fraction = i / len(self.positions)
                color = cmap(time_fraction)
                
                ax.plot([x1, x2], [y1, y2], 
                       color=color, linewidth=2.5, 
                       solid_capstyle='round', zorder=3)
        
        # Add colorbar to show time
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 1))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Drawing Progress (Start → End)', fontsize=12, fontweight='bold')
        
        # Mark start and end
        start_x, start_y, _ = self.positions[0]
        end_x, end_y, _ = self.positions[-1]
        ax.plot(start_x, start_y, 'o', color='blue', markersize=15, 
               label='Start', zorder=5, markeredgecolor='white', markeredgewidth=2)
        ax.plot(end_x, end_y, 'o', color='red', markersize=15, 
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
        output_file = self.ssg_file.parent / "simulation_sequence.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"💾 Saved sequence visualization to: {output_file}")
        
        return fig, ax


def main():
    """Main function"""
    print("=" * 70)
    print("SSG SIMULATOR (MATPLOTLIB)")
    print("=" * 70)
    print()
    
    # Get SSG file
    if len(sys.argv) > 1:
        ssg_file = sys.argv[1]
    else:
        # Default to test output
        ssg_file = Path(__file__).parent / "test_output.ssg"
    
    if not Path(ssg_file).exists():
        print(f"❌ Error: SSG file not found: {ssg_file}")
        print()
        print("Usage: python ssg_simulator.py [file.ssg]")
        print()
        print("Example:")
        print("  python ssg_simulator.py ../motor_movement/test_square_output.ssg")
        print("  python ssg_simulator.py test_output.ssg")
        return
    
    # Create simulator
    sim = SSGSimulator(ssg_file)
    
    # Simulate
    sim.simulate()
    
    # Analyze
    sim.analyze()
    
    # Plot standard view
    print("Creating standard visualization...")
    fig1, ax1 = sim.plot(show_travel=True, show_grid=True, show_plate=True)
    
    # Plot time-sequence view
    print("Creating time-sequence visualization...")
    fig2, ax2 = sim.plot_time_sequence()
    
    print()
    print("=" * 70)
    print("SIMULATION COMPLETE!")
    print("=" * 70)
    print()
    print("Two visualizations created:")
    print("  1. simulation_preview.png - Standard view with sauce on/off")
    print("  2. simulation_sequence.png - Time-based color gradient")
    print()
    print("📺 Displaying plots...")
    plt.show()


if __name__ == "__main__":
    main()


