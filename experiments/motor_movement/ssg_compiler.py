#!/usr/bin/env python3
"""
SSG Compiler: SVG to Sauce Simple G-code
Converts SVG vector graphics to SSG motion commands for the Sriracha Sketcher

Following Design Doc Section 6.3 (Toolpath Compilation)
"""

import re
import math
import json
from pathlib import Path
from typing import List, Tuple, Optional
from xml.etree import ElementTree as ET
from dataclasses import dataclass

import config


@dataclass
class Point:
    """2D point with metadata"""
    x: float
    y: float
    is_move: bool = False  # True for G0 (rapid), False for G1 (draw)


@dataclass
class Path:
    """Collection of connected points forming a path"""
    points: List[Point]
    
    def length(self) -> float:
        """Calculate total path length in mm"""
        total = 0.0
        for i in range(1, len(self.points)):
            dx = self.points[i].x - self.points[i-1].x
            dy = self.points[i].y - self.points[i-1].y
            total += math.sqrt(dx*dx + dy*dy)
        return total


class SSGCompiler:
    """Compile SVG to SSG commands"""
    
    def __init__(self):
        self.paths: List[Path] = []
        self.ssg_lines: List[str] = []
        self.warnings: List[str] = []
        
    def load_svg(self, filepath: str, scale: float = 1.0) -> None:
        """
        Load and parse SVG file
        
        Args:
            filepath: Path to SVG file
            scale: Scaling factor (1.0 = 1 SVG unit = 1mm)
        """
        print(f"Loading SVG: {filepath}")
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # Parse all drawing elements
        for element in root.iter():
            tag = element.tag.split('}')[-1]  # Remove XML namespace
            
            if tag == 'path':
                self._parse_path(element.get('d', ''), scale)
            elif tag == 'line':
                self._parse_line(element, scale)
            elif tag == 'rect':
                self._parse_rect(element, scale)
            elif tag == 'circle':
                self._parse_circle(element, scale)
            elif tag == 'ellipse':
                self._parse_ellipse(element, scale)
            elif tag == 'polyline':
                self._parse_polyline(element, scale, close=False)
            elif tag == 'polygon':
                self._parse_polyline(element, scale, close=True)
        
        print(f"Parsed {len(self.paths)} paths with {sum(len(p.points) for p in self.paths)} points")
        
    def _parse_path(self, d: str, scale: float) -> None:
        """Parse SVG path 'd' attribute"""
        commands = re.findall(r'[MmLlHhVvCcSsQqTtAaZz][^MmLlHhVvCcSsQqTtAaZz]*', d)
        
        current_path = Path(points=[])
        current_x, current_y = 0.0, 0.0
        path_start_x, path_start_y = 0.0, 0.0
        
        for cmd in commands:
            cmd_type = cmd[0]
            coords_str = cmd[1:].strip()
            
            if not coords_str and cmd_type not in 'Zz':
                coords = []
            else:
                coords = [float(x) * scale for x in re.findall(r'-?\d*\.?\d+', coords_str)]
            
            # Move commands
            if cmd_type == 'M':  # Absolute move
                if current_path.points:
                    self.paths.append(current_path)
                    current_path = Path(points=[])
                current_x = coords[0]
                current_y = coords[1]
                path_start_x, path_start_y = current_x, current_y
                current_path.points.append(Point(current_x, current_y, is_move=True))
                
                # Subsequent coordinate pairs are implicit lineto
                for i in range(2, len(coords), 2):
                    current_x = coords[i]
                    current_y = coords[i+1]
                    current_path.points.append(Point(current_x, current_y, is_move=False))
            
            elif cmd_type == 'm':  # Relative move
                if current_path.points:
                    self.paths.append(current_path)
                    current_path = Path(points=[])
                current_x += coords[0]
                current_y += coords[1]
                path_start_x, path_start_y = current_x, current_y
                current_path.points.append(Point(current_x, current_y, is_move=True))
                
                for i in range(2, len(coords), 2):
                    current_x += coords[i]
                    current_y += coords[i+1]
                    current_path.points.append(Point(current_x, current_y, is_move=False))
            
            # Line commands
            elif cmd_type == 'L':  # Absolute line
                for i in range(0, len(coords), 2):
                    current_x = coords[i]
                    current_y = coords[i+1]
                    current_path.points.append(Point(current_x, current_y, is_move=False))
            
            elif cmd_type == 'l':  # Relative line
                for i in range(0, len(coords), 2):
                    current_x += coords[i]
                    current_y += coords[i+1]
                    current_path.points.append(Point(current_x, current_y, is_move=False))
            
            elif cmd_type == 'H':  # Horizontal line (absolute)
                for x in coords:
                    current_x = x
                    current_path.points.append(Point(current_x, current_y, is_move=False))
            
            elif cmd_type == 'h':  # Horizontal line (relative)
                for x in coords:
                    current_x += x
                    current_path.points.append(Point(current_x, current_y, is_move=False))
            
            elif cmd_type == 'V':  # Vertical line (absolute)
                for y in coords:
                    current_y = y
                    current_path.points.append(Point(current_x, current_y, is_move=False))
            
            elif cmd_type == 'v':  # Vertical line (relative)
                for y in coords:
                    current_y += y
                    current_path.points.append(Point(current_x, current_y, is_move=False))
            
            # Cubic Bezier
            elif cmd_type in 'Cc':
                for i in range(0, len(coords), 6):
                    if cmd_type == 'C':
                        x1, y1 = coords[i], coords[i+1]
                        x2, y2 = coords[i+2], coords[i+3]
                        x, y = coords[i+4], coords[i+5]
                    else:
                        x1 = current_x + coords[i]
                        y1 = current_y + coords[i+1]
                        x2 = current_x + coords[i+2]
                        y2 = current_y + coords[i+3]
                        x = current_x + coords[i+4]
                        y = current_y + coords[i+5]
                    
                    # Tessellate bezier curve
                    bezier_points = self._tessellate_cubic_bezier(
                        current_x, current_y, x1, y1, x2, y2, x, y
                    )
                    for bx, by in bezier_points:
                        current_path.points.append(Point(bx, by, is_move=False))
                    current_x, current_y = x, y
            
            # Quadratic Bezier
            elif cmd_type in 'Qq':
                for i in range(0, len(coords), 4):
                    if cmd_type == 'Q':
                        x1, y1 = coords[i], coords[i+1]
                        x, y = coords[i+2], coords[i+3]
                    else:
                        x1 = current_x + coords[i]
                        y1 = current_y + coords[i+1]
                        x = current_x + coords[i+2]
                        y = current_y + coords[i+3]
                    
                    # Tessellate quadratic bezier
                    bezier_points = self._tessellate_quadratic_bezier(
                        current_x, current_y, x1, y1, x, y
                    )
                    for bx, by in bezier_points:
                        current_path.points.append(Point(bx, by, is_move=False))
                    current_x, current_y = x, y
            
            # Arc (simplified to line segments)
            elif cmd_type in 'Aa':
                for i in range(0, len(coords), 7):
                    if cmd_type == 'A':
                        x, y = coords[i+5], coords[i+6]
                    else:
                        x = current_x + coords[i+5]
                        y = current_y + coords[i+6]
                    
                    # Simple linear approximation (TODO: proper arc tessellation)
                    arc_points = self._tessellate_arc(current_x, current_y, x, y, segments=20)
                    for ax, ay in arc_points:
                        current_path.points.append(Point(ax, ay, is_move=False))
                    current_x, current_y = x, y
            
            # Close path
            elif cmd_type in 'Zz':
                if current_path.points:
                    # Close back to start
                    current_path.points.append(Point(path_start_x, path_start_y, is_move=False))
                    current_x, current_y = path_start_x, path_start_y
        
        # Add final path
        if current_path.points:
            self.paths.append(current_path)
    
    def _tessellate_cubic_bezier(self, x0, y0, x1, y1, x2, y2, x3, y3) -> List[Tuple[float, float]]:
        """Adaptive tessellation of cubic Bezier curve"""
        points = []
        segments = self._estimate_bezier_segments(x0, y0, x1, y1, x2, y2, x3, y3)
        
        for i in range(1, segments + 1):
            t = i / segments
            mt = 1 - t
            x = mt**3 * x0 + 3 * mt**2 * t * x1 + 3 * mt * t**2 * x2 + t**3 * x3
            y = mt**3 * y0 + 3 * mt**2 * t * y1 + 3 * mt * t**2 * y2 + t**3 * y3
            points.append((x, y))
        return points
    
    def _tessellate_quadratic_bezier(self, x0, y0, x1, y1, x2, y2) -> List[Tuple[float, float]]:
        """Adaptive tessellation of quadratic Bezier curve"""
        points = []
        segments = max(10, int(math.sqrt((x2-x0)**2 + (y2-y0)**2) / config.BEZIER_MAX_ERROR_MM))
        
        for i in range(1, segments + 1):
            t = i / segments
            mt = 1 - t
            x = mt**2 * x0 + 2 * mt * t * x1 + t**2 * x2
            y = mt**2 * y0 + 2 * mt * t * y1 + t**2 * y2
            points.append((x, y))
        return points
    
    def _tessellate_arc(self, x0, y0, x1, y1, segments: int = 20) -> List[Tuple[float, float]]:
        """Simple linear arc approximation (placeholder)"""
        points = []
        for i in range(1, segments + 1):
            t = i / segments
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            points.append((x, y))
        return points
    
    def _estimate_bezier_segments(self, x0, y0, x1, y1, x2, y2, x3, y3) -> int:
        """Estimate number of segments needed for bezier curve"""
        # Use chord length heuristic
        chord = math.sqrt((x3-x0)**2 + (y3-y0)**2)
        control_length = (
            math.sqrt((x1-x0)**2 + (y1-y0)**2) +
            math.sqrt((x2-x1)**2 + (y2-y1)**2) +
            math.sqrt((x3-x2)**2 + (y3-y2)**2)
        )
        segments = max(10, int(control_length / config.BEZIER_MAX_ERROR_MM))
        return min(segments, 100)  # Cap at 100 segments
    
    def _parse_line(self, element, scale: float) -> None:
        """Parse SVG line element"""
        x1 = float(element.get('x1', 0)) * scale
        y1 = float(element.get('y1', 0)) * scale
        x2 = float(element.get('x2', 0)) * scale
        y2 = float(element.get('y2', 0)) * scale
        self.paths.append(Path(points=[
            Point(x1, y1, is_move=True),
            Point(x2, y2, is_move=False)
        ]))
    
    def _parse_rect(self, element, scale: float) -> None:
        """Parse SVG rectangle element"""
        x = float(element.get('x', 0)) * scale
        y = float(element.get('y', 0)) * scale
        w = float(element.get('width', 0)) * scale
        h = float(element.get('height', 0)) * scale
        self.paths.append(Path(points=[
            Point(x, y, is_move=True),
            Point(x + w, y, is_move=False),
            Point(x + w, y + h, is_move=False),
            Point(x, y + h, is_move=False),
            Point(x, y, is_move=False)
        ]))
    
    def _parse_circle(self, element, scale: float, segments: int = 36) -> None:
        """Parse SVG circle element"""
        cx = float(element.get('cx', 0)) * scale
        cy = float(element.get('cy', 0)) * scale
        r = float(element.get('r', 0)) * scale
        points = []
        for i in range(segments + 1):
            angle = (i / segments) * 2 * math.pi
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append(Point(x, y, is_move=(i == 0)))
        self.paths.append(Path(points=points))
    
    def _parse_ellipse(self, element, scale: float, segments: int = 36) -> None:
        """Parse SVG ellipse element"""
        cx = float(element.get('cx', 0)) * scale
        cy = float(element.get('cy', 0)) * scale
        rx = float(element.get('rx', 0)) * scale
        ry = float(element.get('ry', 0)) * scale
        points = []
        for i in range(segments + 1):
            angle = (i / segments) * 2 * math.pi
            x = cx + rx * math.cos(angle)
            y = cy + ry * math.sin(angle)
            points.append(Point(x, y, is_move=(i == 0)))
        self.paths.append(Path(points=points))
    
    def _parse_polyline(self, element, scale: float, close: bool = False) -> None:
        """Parse SVG polyline/polygon element"""
        points_str = element.get('points', '')
        coords = [float(x) * scale for x in re.findall(r'-?\d*\.?\d+', points_str)]
        if len(coords) < 2:
            return
        
        points = [Point(coords[0], coords[1], is_move=True)]
        for i in range(2, len(coords), 2):
            points.append(Point(coords[i], coords[i+1], is_move=False))
        
        if close and len(coords) >= 4:
            points.append(Point(coords[0], coords[1], is_move=False))
        
        self.paths.append(Path(points=points))
    
    def normalize(self) -> None:
        """
        Normalize paths: center, clip to plate, validate
        Following Design Doc Section 6.2 (SVG Normalizer)
        """
        print("Normalizing paths...")
        
        # Find bounds
        all_x = [p.x for path in self.paths for p in path.points]
        all_y = [p.y for path in self.paths for p in path.points]
        
        if not all_x:
            return
        
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        width = max_x - min_x
        height = max_y - min_y
        
        print(f"Original bounds: {width:.1f}mm × {height:.1f}mm")
        
        # Center on canvas
        offset_x = -(min_x + max_x) / 2
        offset_y = -(min_y + max_y) / 2
        
        for path in self.paths:
            for point in path.points:
                point.x += offset_x
                point.y += offset_y
        
        # Validate against plate radius
        for path in self.paths:
            for point in path.points:
                dist = math.sqrt(point.x**2 + point.y**2)
                if dist > config.PLATE_RADIUS_MM:
                    self.warnings.append(
                        f"Point ({point.x:.1f}, {point.y:.1f}) outside plate radius {config.PLATE_RADIUS_MM}mm"
                    )
        
        # Validate constraints (Design Doc 7.1)
        if len(self.paths) > config.MAX_PATHS:
            self.warnings.append(f"Too many paths: {len(self.paths)} > {config.MAX_PATHS}")
        
        total_length = sum(p.length() for p in self.paths)
        if total_length > config.MAX_TOTAL_LENGTH_MM:
            self.warnings.append(f"Total length too long: {total_length:.1f}mm > {config.MAX_TOTAL_LENGTH_MM}mm")
        
        total_vertices = sum(len(p.points) for p in self.paths)
        if total_vertices > config.MAX_VERTICES:
            self.warnings.append(f"Too many vertices: {total_vertices} > {config.MAX_VERTICES}")
        
        print(f"After normalization: {len(self.paths)} paths, {total_vertices} points, {total_length:.1f}mm total")
    
    def simplify(self) -> None:
        """
        Simplify paths using Douglas-Peucker algorithm
        Remove redundant points while preserving shape
        """
        print("Simplifying paths...")
        original_count = sum(len(p.points) for p in self.paths)
        
        for path in self.paths:
            if len(path.points) > 2:
                simplified = self._douglas_peucker(path.points, config.SIMPLIFY_EPSILON_MM)
                path.points = simplified
        
        new_count = sum(len(p.points) for p in self.paths)
        print(f"Simplified: {original_count} → {new_count} points ({100*(original_count-new_count)/original_count:.1f}% reduction)")
    
    def _douglas_peucker(self, points: List[Point], epsilon: float) -> List[Point]:
        """Douglas-Peucker line simplification algorithm"""
        if len(points) < 3:
            return points
        
        # Find point with maximum distance from line
        dmax = 0
        index = 0
        end = len(points) - 1
        
        for i in range(1, end):
            d = self._perpendicular_distance(points[i], points[0], points[end])
            if d > dmax:
                index = i
                dmax = d
        
        # If max distance > epsilon, recursively simplify
        if dmax > epsilon:
            rec1 = self._douglas_peucker(points[:index+1], epsilon)
            rec2 = self._douglas_peucker(points[index:], epsilon)
            return rec1[:-1] + rec2
        else:
            return [points[0], points[end]]
    
    def _perpendicular_distance(self, point: Point, line_start: Point, line_end: Point) -> float:
        """Calculate perpendicular distance from point to line"""
        dx = line_end.x - line_start.x
        dy = line_end.y - line_start.y
        
        if dx == 0 and dy == 0:
            return math.sqrt((point.x - line_start.x)**2 + (point.y - line_start.y)**2)
        
        t = max(0, min(1, ((point.x - line_start.x) * dx + (point.y - line_start.y) * dy) / (dx * dx + dy * dy)))
        proj_x = line_start.x + t * dx
        proj_y = line_start.y + t * dy
        
        return math.sqrt((point.x - proj_x)**2 + (point.y - proj_y)**2)
    
    def optimize_path_order(self) -> None:
        """
        Optimize path ordering using nearest-neighbor heuristic
        Reduces rapid travel time
        """
        print("Optimizing path order...")
        if len(self.paths) <= 1:
            return
        
        optimized = [self.paths[0]]
        remaining = self.paths[1:]
        
        while remaining:
            last_point = optimized[-1].points[-1]
            
            # Find nearest path
            nearest_idx = 0
            nearest_dist = float('inf')
            
            for i, path in enumerate(remaining):
                dist = math.sqrt(
                    (path.points[0].x - last_point.x)**2 +
                    (path.points[0].y - last_point.y)**2
                )
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_idx = i
            
            optimized.append(remaining.pop(nearest_idx))
        
        self.paths = optimized
        print(f"Path order optimized")
    
    def compile_to_ssg(self) -> List[str]:
        """
        Compile paths to SSG commands
        Following Design Doc Section 5.3 (Protocol)
        """
        print("Compiling to SSG...")
        self.ssg_lines = []
        n = 1  # Sequence number
        
        # Start with homing command
        self.ssg_lines.append(f"N{n} G28")
        n += 1
        
        sauce_on = False
        
        for path in self.paths:
            if not path.points:
                continue
            
            # Turn sauce on for this path
            if not sauce_on:
                self.ssg_lines.append(f"N{n} M3 S{config.SAUCE_FLOW_DEFAULT}")
                n += 1
                sauce_on = True
            
            # Generate movement commands
            for i, point in enumerate(path.points):
                if point.is_move:
                    # Rapid move with sauce off
                    if sauce_on:
                        self.ssg_lines.append(f"N{n} M5")
                        n += 1
                        sauce_on = False
                    self.ssg_lines.append(f"N{n} G0 X{point.x:.2f} Y{point.y:.2f} F{config.FEED_RATE_RAPID}")
                    n += 1
                    
                    # Turn sauce back on after move
                    self.ssg_lines.append(f"N{n} M3 S{config.SAUCE_FLOW_DEFAULT}")
                    n += 1
                    sauce_on = True
                else:
                    # Drawing move
                    self.ssg_lines.append(f"N{n} G1 X{point.x:.2f} Y{point.y:.2f} F{config.FEED_RATE_DRAW}")
                    n += 1
            
            # Turn sauce off after path
            if sauce_on:
                self.ssg_lines.append(f"N{n} M5")
                n += 1
                sauce_on = False
        
        # Final sauce off and status report
        if sauce_on:
            self.ssg_lines.append(f"N{n} M5")
            n += 1
        
        self.ssg_lines.append(f"N{n} M114")  # Report position
        
        print(f"Compiled {len(self.ssg_lines)} SSG commands")
        return self.ssg_lines
    
    def save_ssg(self, filepath: str) -> None:
        """Save SSG commands to file"""
        with open(filepath, 'w') as f:
            f.write('\n'.join(self.ssg_lines))
        print(f"Saved SSG to: {filepath}")
    
    def get_statistics(self) -> dict:
        """Get compilation statistics"""
        total_rapid = 0.0
        total_draw = 0.0
        
        for line in self.ssg_lines:
            if ' G0 ' in line:
                total_rapid += 1
            elif ' G1 ' in line:
                total_draw += 1
        
        total_length = sum(p.length() for p in self.paths)
        estimated_time = (total_draw * 60 / config.FEED_RATE_DRAW +
                         total_rapid * 60 / config.FEED_RATE_RAPID)
        
        return {
            'num_paths': len(self.paths),
            'num_commands': len(self.ssg_lines),
            'total_length_mm': total_length,
            'rapid_moves': int(total_rapid),
            'draw_moves': int(total_draw),
            'estimated_time_sec': estimated_time,
            'warnings': self.warnings
        }


def main():
    """Example usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ssg_compiler.py <input.svg> [output.ssg]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.svg', '.ssg')
    
    # Compile
    compiler = SSGCompiler()
    compiler.load_svg(input_file, scale=1.0)
    compiler.normalize()
    compiler.simplify()
    compiler.optimize_path_order()
    compiler.compile_to_ssg()
    compiler.save_ssg(output_file)
    
    # Print statistics
    stats = compiler.get_statistics()
    print("\n" + "="*60)
    print("COMPILATION STATISTICS")
    print("="*60)
    print(f"Paths: {stats['num_paths']}")
    print(f"SSG Commands: {stats['num_commands']}")
    print(f"Total Length: {stats['total_length_mm']:.1f} mm")
    print(f"Rapid Moves: {stats['rapid_moves']}")
    print(f"Draw Moves: {stats['draw_moves']}")
    print(f"Estimated Time: {stats['estimated_time_sec']:.1f} sec ({stats['estimated_time_sec']/60:.1f} min)")
    
    if stats['warnings']:
        print("\nWarnings:")
        for warning in stats['warnings']:
            print(f"  ⚠️  {warning}")


if __name__ == "__main__":
    main()

