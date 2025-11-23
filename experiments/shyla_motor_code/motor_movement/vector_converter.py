#!/usr/bin/env python3
"""
SVG to Plotter Sender
Converts an SVG file to motor instructions and sends to ESP32 plotter via WebSocket
"""

import json
import re
import math
import asyncio
import websockets
from xml.etree import ElementTree as ET
from typing import List

# ============== CONFIGURATION ==============
PLOTTER_IP = "192.168.1.105"  # Change this to your ESP32's IP address
STEPS_PER_MM_X = 10.0
STEPS_PER_MM_Y = 10.0
# ===========================================


class Point:
    def __init__(self, x: float, y: float, pen_down: bool = True):
        self.x = x
        self.y = y
        self.pen_down = pen_down
    
    def to_dict(self):
        return {"x": self.x, "y": self.y, "penDown": self.pen_down}


class SVGToPlotter:
    def __init__(self):
        self.path_data: List[Point] = []
    
    def parse_svg_file(self, filepath: str, scale: float = 1.0):
        """Parse an SVG file and extract path data"""
        print(f"Parsing {filepath}...")
        
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # Process all drawing elements
        for element in root.iter():
            tag = element.tag.split('}')[-1]  # Remove namespace
            
            if tag == 'path':
                self.parse_path(element.get('d', ''), scale)
            elif tag == 'line':
                self.parse_line(element, scale)
            elif tag == 'rect':
                self.parse_rect(element, scale)
            elif tag == 'circle':
                self.parse_circle(element, scale)
            elif tag == 'ellipse':
                self.parse_ellipse(element, scale)
            elif tag == 'polyline':
                self.parse_polyline(element, scale, close=False)
            elif tag == 'polygon':
                self.parse_polyline(element, scale, close=True)
        
        print(f"Extracted {len(self.path_data)} points")
    
    def parse_path(self, d: str, scale: float = 1.0):
        """Parse SVG path data"""
        commands = re.findall(r'[MmLlHhVvCcSsQqTtAaZz][^MmLlHhVvCcSsQqTtAaZz]*', d)
        
        current_x = 0.0
        current_y = 0.0
        
        for cmd in commands:
            cmd_type = cmd[0]
            coords_str = cmd[1:].strip()
            
            if not coords_str and cmd_type not in 'Zz':
                coords = []
            else:
                coords = [float(x) for x in re.findall(r'-?\d*\.?\d+', coords_str)]
            
            # Move commands
            if cmd_type == 'M':
                current_x = coords[0] * scale
                current_y = coords[1] * scale
                self.path_data.append(Point(current_x, current_y, pen_down=False))
                for i in range(2, len(coords), 2):
                    current_x = coords[i] * scale
                    current_y = coords[i+1] * scale
                    self.path_data.append(Point(current_x, current_y, pen_down=True))
            
            elif cmd_type == 'm':
                current_x += coords[0] * scale
                current_y += coords[1] * scale
                self.path_data.append(Point(current_x, current_y, pen_down=False))
                for i in range(2, len(coords), 2):
                    current_x += coords[i] * scale
                    current_y += coords[i+1] * scale
                    self.path_data.append(Point(current_x, current_y, pen_down=True))
            
            # Line commands
            elif cmd_type == 'L':
                for i in range(0, len(coords), 2):
                    current_x = coords[i] * scale
                    current_y = coords[i+1] * scale
                    self.path_data.append(Point(current_x, current_y, pen_down=True))
            
            elif cmd_type == 'l':
                for i in range(0, len(coords), 2):
                    current_x += coords[i] * scale
                    current_y += coords[i+1] * scale
                    self.path_data.append(Point(current_x, current_y, pen_down=True))
            
            elif cmd_type == 'H':
                for x in coords:
                    current_x = x * scale
                    self.path_data.append(Point(current_x, current_y, pen_down=True))
            
            elif cmd_type == 'h':
                for x in coords:
                    current_x += x * scale
                    self.path_data.append(Point(current_x, current_y, pen_down=True))
            
            elif cmd_type == 'V':
                for y in coords:
                    current_y = y * scale
                    self.path_data.append(Point(current_x, current_y, pen_down=True))
            
            elif cmd_type == 'v':
                for y in coords:
                    current_y += y * scale
                    self.path_data.append(Point(current_x, current_y, pen_down=True))
            
            # Cubic Bezier
            elif cmd_type in 'Cc':
                for i in range(0, len(coords), 6):
                    if cmd_type == 'C':
                        x1, y1 = coords[i] * scale, coords[i+1] * scale
                        x2, y2 = coords[i+2] * scale, coords[i+3] * scale
                        x, y = coords[i+4] * scale, coords[i+5] * scale
                    else:
                        x1 = current_x + coords[i] * scale
                        y1 = current_y + coords[i+1] * scale
                        x2 = current_x + coords[i+2] * scale
                        y2 = current_y + coords[i+3] * scale
                        x = current_x + coords[i+4] * scale
                        y = current_y + coords[i+5] * scale
                    
                    for bx, by in self.bezier_cubic(current_x, current_y, x1, y1, x2, y2, x, y):
                        self.path_data.append(Point(bx, by, pen_down=True))
                    current_x, current_y = x, y
            
            # Quadratic Bezier
            elif cmd_type in 'Qq':
                for i in range(0, len(coords), 4):
                    if cmd_type == 'Q':
                        x1, y1 = coords[i] * scale, coords[i+1] * scale
                        x, y = coords[i+2] * scale, coords[i+3] * scale
                    else:
                        x1 = current_x + coords[i] * scale
                        y1 = current_y + coords[i+1] * scale
                        x = current_x + coords[i+2] * scale
                        y = current_y + coords[i+3] * scale
                    
                    for bx, by in self.bezier_quadratic(current_x, current_y, x1, y1, x, y):
                        self.path_data.append(Point(bx, by, pen_down=True))
                    current_x, current_y = x, y
            
            # Arc
            elif cmd_type in 'Aa':
                for i in range(0, len(coords), 7):
                    rx, ry = coords[i] * scale, coords[i+1] * scale
                    if cmd_type == 'A':
                        x, y = coords[i+5] * scale, coords[i+6] * scale
                    else:
                        x = current_x + coords[i+5] * scale
                        y = current_y + coords[i+6] * scale
                    
                    for ax, ay in self.arc_to_lines(current_x, current_y, x, y):
                        self.path_data.append(Point(ax, ay, pen_down=True))
                    current_x, current_y = x, y
            
            # Close path
            elif cmd_type in 'Zz':
                if len(self.path_data) > 0:
                    for p in reversed(self.path_data):
                        if not p.pen_down:
                            self.path_data.append(Point(p.x, p.y, pen_down=True))
                            break
    
    def bezier_cubic(self, x0, y0, x1, y1, x2, y2, x3, y3, segments=20):
        """Approximate cubic Bezier with line segments"""
        points = []
        for i in range(1, segments + 1):
            t = i / segments
            mt = 1 - t
            x = mt**3 * x0 + 3 * mt**2 * t * x1 + 3 * mt * t**2 * x2 + t**3 * x3
            y = mt**3 * y0 + 3 * mt**2 * t * y1 + 3 * mt * t**2 * y2 + t**3 * y3
            points.append((x, y))
        return points
    
    def bezier_quadratic(self, x0, y0, x1, y1, x2, y2, segments=15):
        """Approximate quadratic Bezier with line segments"""
        points = []
        for i in range(1, segments + 1):
            t = i / segments
            mt = 1 - t
            x = mt**2 * x0 + 2 * mt * t * x1 + t**2 * x2
            y = mt**2 * y0 + 2 * mt * t * y1 + t**2 * y2
            points.append((x, y))
        return points
    
    def arc_to_lines(self, x0, y0, x, y, segments=20):
        """Approximate arc with line segments"""
        points = []
        for i in range(1, segments + 1):
            t = i / segments
            px = x0 + (x - x0) * t
            py = y0 + (y - y0) * t
            points.append((px, py))
        return points
    
    def parse_line(self, element, scale: float = 1.0):
        x1 = float(element.get('x1', 0)) * scale
        y1 = float(element.get('y1', 0)) * scale
        x2 = float(element.get('x2', 0)) * scale
        y2 = float(element.get('y2', 0)) * scale
        self.path_data.append(Point(x1, y1, pen_down=False))
        self.path_data.append(Point(x2, y2, pen_down=True))
    
    def parse_rect(self, element, scale: float = 1.0):
        x = float(element.get('x', 0)) * scale
        y = float(element.get('y', 0)) * scale
        w = float(element.get('width', 0)) * scale
        h = float(element.get('height', 0)) * scale
        self.path_data.append(Point(x, y, pen_down=False))
        self.path_data.append(Point(x + w, y, pen_down=True))
        self.path_data.append(Point(x + w, y + h, pen_down=True))
        self.path_data.append(Point(x, y + h, pen_down=True))
        self.path_data.append(Point(x, y, pen_down=True))
    
    def parse_circle(self, element, scale: float = 1.0, segments: int = 36):
        cx = float(element.get('cx', 0)) * scale
        cy = float(element.get('cy', 0)) * scale
        r = float(element.get('r', 0)) * scale
        for i in range(segments + 1):
            angle = (i / segments) * 2 * math.pi
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            self.path_data.append(Point(x, y, pen_down=(i > 0)))
    
    def parse_ellipse(self, element, scale: float = 1.0, segments: int = 36):
        cx = float(element.get('cx', 0)) * scale
        cy = float(element.get('cy', 0)) * scale
        rx = float(element.get('rx', 0)) * scale
        ry = float(element.get('ry', 0)) * scale
        for i in range(segments + 1):
            angle = (i / segments) * 2 * math.pi
            x = cx + rx * math.cos(angle)
            y = cy + ry * math.sin(angle)
            self.path_data.append(Point(x, y, pen_down=(i > 0)))
    
    def parse_polyline(self, element, scale: float = 1.0, close: bool = False):
        points_str = element.get('points', '')
        coords = [float(x) for x in re.findall(r'-?\d*\.?\d+', points_str)]
        if len(coords) < 2:
            return
        self.path_data.append(Point(coords[0] * scale, coords[1] * scale, pen_down=False))
        for i in range(2, len(coords), 2):
            self.path_data.append(Point(coords[i] * scale, coords[i+1] * scale, pen_down=True))
        if close and len(coords) >= 4:
            self.path_data.append(Point(coords[0] * scale, coords[1] * scale, pen_down=True))
    
    def center_drawing(self):
        """Center the drawing around origin (0, 0)"""
        if not self.path_data:
            return
        
        # Get current bounds
        bounds = self.get_bounds()
        
        # Calculate center offset
        center_x = (bounds['min_x'] + bounds['max_x']) / 2.0
        center_y = (bounds['min_y'] + bounds['max_y']) / 2.0
        
        # Translate all points to center
        for point in self.path_data:
            point.x -= center_x
            point.y -= center_y
    
    def to_motor_instructions(self) -> str:
        """Convert path data to JSON motor instructions"""
        instructions = []
        for point in self.path_data:
            instructions.append({
                "x": point.x * STEPS_PER_MM_X,
                "y": point.y * STEPS_PER_MM_Y,
                "penDown": point.pen_down
            })
        return json.dumps(instructions)
    
    def get_bounds(self):
        """Get bounding box of the drawing"""
        if not self.path_data:
            return None
        xs = [p.x for p in self.path_data]
        ys = [p.y for p in self.path_data]
        return {
            "min_x": min(xs),
            "min_y": min(ys),
            "max_x": max(xs),
            "max_y": max(ys),
            "width": max(xs) - min(xs),
            "height": max(ys) - min(ys)
        }


async def send_to_plotter(svg_file: str, scale: float = 1.0):
    """Parse SVG and send to ESP32 plotter via WebSocket"""
    
    # Parse SVG file
    converter = SVGToPlotter()
    converter.parse_svg_file(svg_file, scale)
    
    if not converter.path_data:
        print("Error: No path data extracted from SVG")
        return
    
    # Center the drawing around origin
    print("Centering drawing around origin (0, 0)...")
    converter.center_drawing()
    
    # Show drawing info
    bounds = converter.get_bounds()
    print(f"Drawing size: {bounds['width']:.1f} x {bounds['height']:.1f} units")
    print(f"Centered bounds: X={bounds['min_x']:.1f} to {bounds['max_x']:.1f}, Y={bounds['min_y']:.1f} to {bounds['max_y']:.1f}")
    
    # Connect to plotter
    uri = f"ws://{PLOTTER_IP}/ws"
    print(f"Connecting to plotter at {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            
            # Send motor instructions
            instructions = converter.to_motor_instructions()
            message = f"PATH:{instructions}"
            
            print(f"Sending {len(converter.path_data)} movement instructions...")
            await websocket.send(message)
            
            # Wait for responses
            print("Waiting for plotter...")
            async for response in websocket:
                print(f"Plotter: {response}")
                if "complete" in response.lower():
                    print("Drawing finished!")
                    break
    
    except ConnectionRefusedError:
        print(f"Error: Could not connect to plotter at {PLOTTER_IP}")
        print("Make sure the ESP32 is powered on and connected to WiFi")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python svg_to_plotter.py <file.svg> [scale]")
        print()
        print("Examples:")
        print("  python svg_to_plotter.py drawing.svg")
        print("  python svg_to_plotter.py drawing.svg 2.0")
        print()
        print(f"Current plotter IP: {PLOTTER_IP}")
        print("Edit PLOTTER_IP at the top of this file to change it")
        sys.exit(1)
    
    svg_file = sys.argv[1]
    scale = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    
    asyncio.run(send_to_plotter(svg_file, scale))