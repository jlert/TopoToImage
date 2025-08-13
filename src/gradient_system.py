#!/usr/bin/env python3
"""
DEM Visualizer - Gradient System with QGIS Integration
Handles color gradient management, QGIS XML import/export, and elevation mapping.

This module provides QGIS-compatible gradient functionality for terrain visualization,
supporting both internal JSON format and QGIS XML/QML color ramp exchange.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
import numpy as np
from dataclasses import dataclass
import colorsys

@dataclass
class ColorStop:
    """Represents a single color stop in a gradient."""
    position: float  # 0.0 to 1.0
    red: int        # 0-255
    green: int      # 0-255  
    blue: int       # 0-255
    alpha: int = 255  # 0-255, default opaque
    
    def to_hex(self) -> str:
        """Convert to hex color string."""
        return f"#{self.red:02x}{self.green:02x}{self.blue:02x}"
    
    def to_rgba_tuple(self) -> Tuple[int, int, int, int]:
        """Convert to RGBA tuple."""
        return (self.red, self.green, self.blue, self.alpha)
    
    def to_qgis_format(self) -> str:
        """Convert to QGIS color format (R,G,B,A)."""
        return f"{self.red},{self.green},{self.blue},{self.alpha}"

@dataclass 
class Gradient:
    """Represents a complete color gradient for elevation mapping."""
    name: str
    description: str
    min_elevation: float  # meters
    max_elevation: float  # meters
    color_stops: List[ColorStop]
    discrete: bool = False  # True for discrete steps, False for smooth interpolation
    created_by: str = "DEM Visualizer"
    tags: List[str] = None
    # Special colors and advanced settings
    shadow_color: Optional[Dict[str, int]] = None  # Dict with red, green, blue, alpha keys
    no_data_color: Optional[Dict[str, int]] = None  # Dict with red, green, blue, alpha keys
    below_gradient_color: Optional[Dict[str, int]] = None  # Dict with red, green, blue, alpha keys
    gradient_type: str = "gradient"  # gradient, shaded_relief, posterized, shading_and_gradient, shading_and_posterized
    light_direction: int = 315  # 0-360 degrees
    shading_intensity: int = 50  # -1000 to 1000 (experimental range, normal 0-100)
    cast_shadows: bool = False
    shadow_drop_distance: float = 1.0
    shadow_soft_edge: int = 3
    blending_mode: str = "Multiply"  # Multiply, Overlay, Soft Light, Hard Light, Screen, Normal
    blending_strength: int = 100  # -1000 to 1000 (experimental range, normal 100)
    color_mode: str = "8-bit"  # 8-bit, 16-bit
    units: str = "meters"  # meters, percent
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        
        # Convert feet units to meters (for legacy support)
        if self.units == "feet":
            print(f"⚠️ Converting gradient '{self.name}' from feet to meters")
            self.min_elevation = self.min_elevation * 0.3048
            self.max_elevation = self.max_elevation * 0.3048
            self.units = "meters"
        
        # Validate units (only meters and percent allowed)
        if self.units not in ["meters", "percent"]:
            print(f"⚠️ Invalid units '{self.units}' for gradient '{self.name}', defaulting to meters")
            self.units = "meters"
        
        # Ensure color stops are sorted by position
        self.color_stops.sort(key=lambda stop: stop.position)
    
    def get_color_at_elevation(self, elevation: float) -> Tuple[int, int, int, int]:
        """Get RGBA color for specific elevation value."""
        if len(self.color_stops) == 0:
            return (128, 128, 128, 255)  # Gray fallback
        
        if len(self.color_stops) == 1:
            return self.color_stops[0].to_rgba_tuple()
        
        # Handle posterized gradient types with below gradient color support
        if self.gradient_type in ["posterized", "shading_and_posterized"]:
            return self._get_posterized_color_with_below_gradient(elevation)
        
        # For regular gradients, use standard logic with clamping
        # Normalize elevation to 0-1 position
        # INVERTED: Higher elevation gets lower position (top of gradient)
        position = 1.0 - (elevation - self.min_elevation) / (self.max_elevation - self.min_elevation)
        position = max(0.0, min(1.0, position))  # Clamp to 0-1
        
        # Find adjacent color stops
        if position <= self.color_stops[0].position:
            return self.color_stops[0].to_rgba_tuple()
        
        if position >= self.color_stops[-1].position:
            return self.color_stops[-1].to_rgba_tuple()
        
        # Find stops to interpolate between
        for i in range(len(self.color_stops) - 1):
            stop1 = self.color_stops[i]
            stop2 = self.color_stops[i + 1]
            
            if stop1.position <= position <= stop2.position:
                if self.discrete:
                    # Discrete mode: use color of lower stop
                    return stop1.to_rgba_tuple()
                else:
                    # Smooth interpolation
                    t = (position - stop1.position) / (stop2.position - stop1.position)
                    
                    r = int(stop1.red + t * (stop2.red - stop1.red))
                    g = int(stop1.green + t * (stop2.green - stop1.green))
                    b = int(stop1.blue + t * (stop2.blue - stop1.blue))
                    a = int(stop1.alpha + t * (stop2.alpha - stop1.alpha))
                    
                    return (r, g, b, a)
        
        return (128, 128, 128, 255)  # Fallback gray
    
    def _get_posterized_color(self, position: float) -> Tuple[int, int, int, int]:
        """
        Get color for posterized gradient type - USER'S EXPECTED BEHAVIOR.
        Based on user feedback: "Yellow + Red bands, no Blue" for test case.
        
        For the user's test case (Red 0.0, Yellow 0.5, Blue 1.0):
        - Red covers positions 0.0 to 0.5 (high elevations: 75-100%)
        - Yellow covers positions 0.5 to 1.0 (low elevations: 0-50%)  
        - Blue point exists but creates no visible band
        """
        # Handle edge cases
        if len(self.color_stops) == 0:
            return (128, 128, 128, 255)
        if len(self.color_stops) == 1:
            return self.color_stops[0].to_rgba_tuple()
        
        # USER'S EXPECTED BEHAVIOR: Each color extends to the next color
        # But the last color (Blue at 1.0) doesn't create a visible band
        
        # Find which band this position falls into
        for i in range(len(self.color_stops) - 1):
            current_stop = self.color_stops[i]
            next_stop = self.color_stops[i + 1]
            
            # If position is in this range, use the current color
            if current_stop.position <= position < next_stop.position:
                return current_stop.to_rgba_tuple()
        
        # Special case: if at or beyond the last position, use the last color
        # This ensures exact position matches work correctly
        if position >= self.color_stops[-1].position:
            return self.color_stops[-1].to_rgba_tuple()
        
        # Fallback: use first color
        return self.color_stops[0].to_rgba_tuple()
    
    def _get_posterized_color_with_below_gradient(self, elevation: float) -> Tuple[int, int, int, int]:
        """
        Get color for posterized gradient type with NEW posterized logic.
        
        NEW POSTERIZED LOGIC (simplified):
        1. Check if elevation is above max_elevation -> use "Above Posterized" color
        2. Check if elevation is below min_elevation -> use bottommost point color  
        3. Otherwise -> use standard posterized bands
        """
        # Sort color stops by position first
        sorted_stops = sorted(self.color_stops, key=lambda s: s.position)
        
        # Find the topmost point elevation (lowest position value = highest elevation)
        top_stop = sorted_stops[0]  # First position = highest elevation
        top_elevation = self.min_elevation + (1.0 - top_stop.position) * (self.max_elevation - self.min_elevation)
        
        # Check if elevation is ABOVE the topmost point
        if elevation > top_elevation:
            # Use "Above Posterized" color (below_gradient_color field) for elevations above the topmost point
            if self.below_gradient_color:
                return (
                    self.below_gradient_color.get('red', 0),
                    self.below_gradient_color.get('green', 0),
                    self.below_gradient_color.get('blue', 0),
                    self.below_gradient_color.get('alpha', 255)
                )
            else:
                # Fall back to top color stop if no above posterized color set
                return top_stop.to_rgba_tuple()
        
        # Find the bottommost point elevation (highest position value = lowest elevation)
        bottom_stop = sorted_stops[-1]  # Last position = lowest elevation
        bottom_elevation = self.min_elevation + (1.0 - bottom_stop.position) * (self.max_elevation - self.min_elevation)
        
        # Check if elevation is BELOW the bottommost point
        if elevation < bottom_elevation:
            # Use bottommost point color for all elevations below the bottommost point
            return bottom_stop.to_rgba_tuple()
        
        # For elevations within range, use standard posterized logic
        # Normalize elevation to 0-1 position
        position = 1.0 - (elevation - self.min_elevation) / (self.max_elevation - self.min_elevation)
        position = max(0.0, min(1.0, position))  # Clamp to 0-1
        
        # Use standard posterized color lookup
        return self._get_posterized_color(position)
    
    def to_dict(self) -> Dict:
        """Convert gradient to dictionary format for JSON serialization"""
        return {
            "name": self.name,
            "description": self.description,
            "min_elevation": self.min_elevation,
            "max_elevation": self.max_elevation,
            "color_stops": [
                {
                    "position": stop.position,
                    "red": stop.red,
                    "green": stop.green,
                    "blue": stop.blue,
                    "alpha": stop.alpha
                }
                for stop in self.color_stops
            ],
            "discrete": self.discrete,
            "created_by": self.created_by,
            "tags": self.tags or [],
            # Special colors
            "shadow_color": {
                "red": self.shadow_color.red,
                "green": self.shadow_color.green,
                "blue": self.shadow_color.blue,
                "alpha": self.shadow_color.alpha
            } if hasattr(self.shadow_color, 'red') else self.shadow_color,
            "no_data_color": {
                "red": self.no_data_color.red,
                "green": self.no_data_color.green,
                "blue": self.no_data_color.blue,
                "alpha": self.no_data_color.alpha
            } if hasattr(self.no_data_color, 'red') else self.no_data_color,
            "below_gradient_color": {
                "red": self.below_gradient_color.red,
                "green": self.below_gradient_color.green,
                "blue": self.below_gradient_color.blue,
                "alpha": self.below_gradient_color.alpha
            } if hasattr(self.below_gradient_color, 'red') else self.below_gradient_color,
            # Advanced settings
            "gradient_type": self.gradient_type,
            "light_direction": self.light_direction,
            "shading_intensity": self.shading_intensity,
            "cast_shadows": self.cast_shadows,
            "shadow_drop_distance": self.shadow_drop_distance,
            "shadow_soft_edge": self.shadow_soft_edge,
            "blending_mode": self.blending_mode,
            "color_mode": self.color_mode,
            "units": self.units
        }

class GradientManager:
    """Manages gradient collections with QGIS import/export capabilities."""
    
    def __init__(self, gradients_file: Optional[Path] = None):
        self.gradients_file = gradients_file or Path("gradients.json")
        self.gradients: Dict[str, Gradient] = {}
        self.load_gradients()
        
        # Load default gradients if none exist
        if not self.gradients:
            self._create_default_gradients()
    
    def _create_default_gradients(self):
        """Create default elevation gradients inspired by classic topographic maps."""
        
        # Classic Elevation (green to white)
        classic = Gradient(
            name="Classic Elevation",
            description="Traditional topographic elevation colors",
            min_elevation=0,
            max_elevation=3000,
            color_stops=[
                ColorStop(0.0, 0, 128, 0),      # Sea level: dark green
                ColorStop(0.2, 34, 139, 34),    # 600m: forest green  
                ColorStop(0.4, 154, 205, 50),   # 1200m: yellow green
                ColorStop(0.6, 205, 133, 63),   # 1800m: peru/tan
                ColorStop(0.8, 139, 90, 43),    # 2400m: saddle brown
                ColorStop(1.0, 255, 255, 255)   # 3000m: white
            ],
            tags=["elevation", "classic", "topographic"]
        )
        
        # Ocean to Alpine
        ocean_alpine = Gradient(
            name="Ocean to Alpine", 
            description="Complete bathymetry to high elevation range",
            min_elevation=-1000,
            max_elevation=5000,
            color_stops=[
                ColorStop(0.0, 8, 48, 107),     # Deep ocean: dark blue
                ColorStop(0.167, 33, 113, 181), # Shallow ocean: blue
                ColorStop(0.2, 66, 146, 198),   # Coast: light blue
                ColorStop(0.233, 198, 219, 239), # Shore: very light blue
                ColorStop(0.25, 247, 252, 185),  # Beach: pale yellow
                ColorStop(0.4, 34, 139, 34),     # Lowland: green
                ColorStop(0.6, 154, 205, 50),    # Hills: yellow green
                ColorStop(0.8, 139, 90, 43),     # Mountains: brown
                ColorStop(1.0, 255, 255, 255)    # Peaks: white
            ],
            tags=["bathymetry", "elevation", "complete"]
        )
        
        # Desert/Arid
        desert = Gradient(
            name="Desert Terrain",
            description="Warm colors for arid landscapes", 
            min_elevation=0,
            max_elevation=2000,
            color_stops=[
                ColorStop(0.0, 255, 218, 185),  # Sand: peach puff
                ColorStop(0.3, 222, 184, 135),  # Low hills: burlywood
                ColorStop(0.6, 205, 133, 63),   # Mid hills: peru
                ColorStop(0.8, 160, 82, 45),    # High hills: saddle brown
                ColorStop(1.0, 139, 69, 19)     # Peaks: dark red
            ],
            tags=["desert", "arid", "warm"]
        )
        
        # Grayscale
        grayscale = Gradient(
            name="Grayscale Elevation",
            description="Simple black to white elevation mapping",
            min_elevation=0, 
            max_elevation=3000,
            color_stops=[
                ColorStop(0.0, 0, 0, 0),        # Black
                ColorStop(1.0, 255, 255, 255)   # White
            ],
            tags=["grayscale", "simple", "monochrome"]
        )
        
        # Add to collection
        self.gradients[classic.name] = classic
        self.gradients[ocean_alpine.name] = ocean_alpine 
        self.gradients[desert.name] = desert
        self.gradients[grayscale.name] = grayscale
        
        # Save defaults
        self.save_gradients()
    
    def load_gradients(self) -> bool:
        """Load gradients from JSON file - supports both dictionary and array formats."""
        try:
            if not self.gradients_file.exists():
                return False
            
            with open(self.gradients_file, 'r') as f:
                data = json.load(f)
            
            self.gradients = {}
            
            # Support both formats:
            # Format 1: Array format {"gradients": [gradient_list]} (GradientManager.save_gradients)
            # Format 2: Dictionary format {gradient_name: gradient_data} (Save List command)
            
            if "gradients" in data and isinstance(data["gradients"], list):
                # Format 1: Array format - main gradients.json structure
                print("📁 Loading array format gradients")
                for gradient_data in data["gradients"]:
                    gradient = self._gradient_from_dict(gradient_data)
                    self.gradients[gradient.name] = gradient
            else:
                # Format 2: Dictionary format - from "Save List" command
                print("📁 Loading dictionary format gradients")
                for gradient_name, gradient_data in data.items():
                    if isinstance(gradient_data, dict) and "name" in gradient_data:
                        gradient = self._gradient_from_dict(gradient_data)
                        self.gradients[gradient.name] = gradient
            
            print(f"✅ Loaded {len(self.gradients)} gradients")
            return True
        except Exception as e:
            print(f"Error loading gradients: {e}")
            return False
    
    def save_gradients(self) -> bool:
        """Save gradients to JSON file."""
        try:
            data = {
                'version': '1.0',
                'created_by': 'DEM Visualizer',
                'gradients': [self._gradient_to_dict(g) for g in self.gradients.values()]
            }
            
            with open(self.gradients_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving gradients: {e}")
            return False
    
    def _gradient_from_dict(self, data: Dict) -> Gradient:
        """Convert dictionary to Gradient object."""
        color_stops = []
        for stop_data in data.get('color_stops', []):
            stop = ColorStop(
                position=stop_data['position'],
                red=stop_data['red'],
                green=stop_data['green'], 
                blue=stop_data['blue'],
                alpha=stop_data.get('alpha', 255)
            )
            color_stops.append(stop)
        
        return Gradient(
            name=data['name'],
            description=data.get('description', ''),
            min_elevation=data.get('min_elevation', 0),
            max_elevation=data.get('max_elevation', 1000),
            color_stops=color_stops,
            discrete=data.get('discrete', False),
            created_by=data.get('created_by', 'DEM Visualizer'),
            tags=data.get('tags', []),
            # Special colors and advanced settings
            shadow_color=data.get('shadow_color', None),
            no_data_color=data.get('no_data_color', None),
            below_gradient_color=data.get('below_gradient_color', None),
            gradient_type=data.get('gradient_type', 'gradient'),
            light_direction=data.get('light_direction', 315),
            shading_intensity=data.get('shading_intensity', 50),
            cast_shadows=data.get('cast_shadows', False),
            shadow_drop_distance=data.get('shadow_drop_distance', 1.0),
            shadow_soft_edge=data.get('shadow_soft_edge', 3),
            blending_mode=data.get('blending_mode', 'Multiply'),
            color_mode=data.get('color_mode', '8-bit'),
            units=data.get('units', 'meters')
        )
    
    def _gradient_to_dict(self, gradient: Gradient) -> Dict:
        """Convert Gradient object to dictionary."""
        return {
            'name': gradient.name,
            'description': gradient.description,
            'min_elevation': gradient.min_elevation,
            'max_elevation': gradient.max_elevation,
            'color_stops': [
                {
                    'position': stop.position,
                    'red': stop.red,
                    'green': stop.green,
                    'blue': stop.blue,
                    'alpha': stop.alpha
                }
                for stop in gradient.color_stops
            ],
            'discrete': gradient.discrete,
            'created_by': gradient.created_by,
            'tags': gradient.tags,
            # Special colors and advanced settings
            'shadow_color': gradient.shadow_color,
            'no_data_color': gradient.no_data_color,
            'below_gradient_color': gradient.below_gradient_color,
            'gradient_type': gradient.gradient_type,
            'light_direction': gradient.light_direction,
            'shading_intensity': gradient.shading_intensity,
            'cast_shadows': gradient.cast_shadows,
            'shadow_drop_distance': gradient.shadow_drop_distance,
            'shadow_soft_edge': gradient.shadow_soft_edge,
            'blending_mode': gradient.blending_mode,
            'color_mode': gradient.color_mode,
            'units': gradient.units
        }
    
    def import_qgis_xml(self, xml_file: Path) -> List[str]:
        """Import color ramps from QGIS XML file. Returns list of imported gradient names."""
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            imported_names = []
            
            # Find all colorramp elements
            for colorramp in root.findall('.//colorramp[@type="gradient"]'):
                gradient = self._parse_qgis_colorramp(colorramp)
                if gradient:
                    self.gradients[gradient.name] = gradient
                    imported_names.append(gradient.name)
            
            if imported_names:
                self.save_gradients()
            
            return imported_names
        except Exception as e:
            print(f"Error importing QGIS XML: {e}")
            return []
    
    def _parse_qgis_colorramp(self, colorramp_element: ET.Element) -> Optional[Gradient]:
        """Parse a QGIS colorramp XML element into a Gradient."""
        try:
            name = colorramp_element.get('name', 'Imported Gradient')
            
            # Parse properties
            props = {}
            for prop in colorramp_element.findall('prop'):
                key = prop.get('k')
                value = prop.get('v')
                props[key] = value
            
            # Get basic colors
            color1_str = props.get('color1', '0,0,0,255')
            color2_str = props.get('color2', '255,255,255,255')
            discrete = props.get('discrete', '0') == '1'
            
            # Parse color values
            color1 = self._parse_qgis_color(color1_str)
            color2 = self._parse_qgis_color(color2_str)
            
            # Create basic color stops
            color_stops = [
                ColorStop(0.0, *color1),
                ColorStop(1.0, *color2)
            ]
            
            # Parse intermediate stops if present
            stops_str = props.get('stops', '')
            if stops_str:
                intermediate_stops = []
                for stop_data in stops_str.split(':'):
                    if ';' in stop_data:
                        pos_str, color_str = stop_data.split(';', 1)
                        position = float(pos_str)
                        color = self._parse_qgis_color(color_str)
                        intermediate_stops.append(ColorStop(position, *color))
                
                # Insert intermediate stops
                color_stops = [color_stops[0]] + intermediate_stops + [color_stops[1]]
                color_stops.sort(key=lambda s: s.position)
            
            return Gradient(
                name=name,
                description=f"Imported from QGIS",
                min_elevation=0,  # Default range - user can adjust
                max_elevation=1000,
                color_stops=color_stops,
                discrete=discrete,
                created_by="QGIS Import",
                tags=["imported", "qgis"]
            )
        except Exception as e:
            print(f"Error parsing QGIS colorramp: {e}")
            return None
    
    def _parse_qgis_color(self, color_str: str) -> Tuple[int, int, int, int]:
        """Parse QGIS color string (R,G,B,A) to RGBA tuple."""
        try:
            parts = color_str.split(',')
            r = int(parts[0]) if len(parts) > 0 else 0
            g = int(parts[1]) if len(parts) > 1 else 0  
            b = int(parts[2]) if len(parts) > 2 else 0
            a = int(parts[3]) if len(parts) > 3 else 255
            return (r, g, b, a)
        except:
            return (0, 0, 0, 255)
    
    def export_qgis_xml(self, gradient_names: List[str], output_file: Path) -> bool:
        """Export selected gradients to QGIS-compatible XML file."""
        try:
            # Create root XML structure
            root = ET.Element('symbols')
            
            for name in gradient_names:
                if name not in self.gradients:
                    continue
                
                gradient = self.gradients[name]
                
                # Create colorramp element
                colorramp = ET.SubElement(root, 'colorramp')
                colorramp.set('type', 'gradient')
                colorramp.set('name', gradient.name)
                
                # Add properties
                if len(gradient.color_stops) >= 2:
                    # Color1 (start)
                    color1_prop = ET.SubElement(colorramp, 'prop')
                    color1_prop.set('k', 'color1')
                    color1_prop.set('v', gradient.color_stops[0].to_qgis_format())
                    
                    # Color2 (end)
                    color2_prop = ET.SubElement(colorramp, 'prop')
                    color2_prop.set('k', 'color2') 
                    color2_prop.set('v', gradient.color_stops[-1].to_qgis_format())
                    
                    # Discrete mode
                    discrete_prop = ET.SubElement(colorramp, 'prop')
                    discrete_prop.set('k', 'discrete')
                    discrete_prop.set('v', '1' if gradient.discrete else '0')
                    
                    # Intermediate stops
                    if len(gradient.color_stops) > 2:
                        stops_data = []
                        for stop in gradient.color_stops[1:-1]:  # Exclude first and last
                            stops_data.append(f"{stop.position};{stop.to_qgis_format()}")
                        
                        if stops_data:
                            stops_prop = ET.SubElement(colorramp, 'prop')
                            stops_prop.set('k', 'stops')
                            stops_prop.set('v', ':'.join(stops_data))
            
            # Write XML file
            tree = ET.ElementTree(root)
            ET.indent(tree, space="  ", level=0)  # Pretty formatting
            tree.write(output_file, encoding='utf-8', xml_declaration=True)
            
            return True
        except Exception as e:
            print(f"Error exporting QGIS XML: {e}")
            return False
    
    def get_gradient_names(self) -> List[str]:
        """Get list of all gradient names."""
        return list(self.gradients.keys())
    
    def get_gradient(self, name: str) -> Optional[Gradient]:
        """Get gradient by name."""
        return self.gradients.get(name)
    
    def add_gradient(self, gradient: Gradient) -> bool:
        """Add or update a gradient."""
        self.gradients[gradient.name] = gradient
        return self.save_gradients()
    
    def remove_gradient(self, name: str) -> bool:
        """Remove a gradient by name."""
        if name in self.gradients:
            del self.gradients[name]
            return self.save_gradients()
        return False
    
    def reorder_gradients(self, ordered_names: List[str]) -> bool:
        """Reorder gradients according to the provided list of names.
        
        Args:
            ordered_names: List of gradient names in the desired order
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate that all names exist
            for name in ordered_names:
                if name not in self.gradients:
                    print(f"❌ Gradient '{name}' not found in gradient list")
                    return False
            
            # Check that we have all gradients (no missing or extra names)
            if set(ordered_names) != set(self.gradients.keys()):
                print(f"❌ Order list doesn't match current gradients")
                return False
            
            # Store gradient ordering information
            # Since dictionaries maintain insertion order in Python 3.7+,
            # we can recreate the dictionary in the desired order
            reordered_gradients = {}
            for name in ordered_names:
                reordered_gradients[name] = self.gradients[name]
            
            self.gradients = reordered_gradients
            return self.save_gradients()
            
        except Exception as e:
            print(f"❌ Error reordering gradients: {e}")
            return False
    
    def apply_gradient_to_array(self, elevation_data: np.ndarray, gradient_name: str) -> Optional[np.ndarray]:
        """Apply gradient to elevation data array, returning RGBA image array."""
        if gradient_name not in self.gradients:
            return None
        
        gradient = self.gradients[gradient_name]
        
        # Create output array (height, width, 4) for RGBA
        height, width = elevation_data.shape
        output = np.zeros((height, width, 4), dtype=np.uint8)
        
        # Handle NaN values (no-data)
        valid_mask = ~np.isnan(elevation_data)
        
        # Apply gradient to valid pixels
        for y in range(height):
            for x in range(width):
                if valid_mask[y, x]:
                    elevation = elevation_data[y, x]
                    color = gradient.get_color_at_elevation(elevation)
                    output[y, x] = color
                else:
                    # Transparent for no-data
                    output[y, x] = (0, 0, 0, 0)
        
        return output

if __name__ == "__main__":
    # Test the gradient system
    manager = GradientManager()
    
    print(f"Loaded {len(manager.gradients)} gradients:")
    for name in manager.get_gradient_names():
        gradient = manager.get_gradient(name)
        print(f"  - {name}: {len(gradient.color_stops)} stops, {gradient.min_elevation}m to {gradient.max_elevation}m")
    
    # Test color generation
    classic = manager.get_gradient("Classic Elevation")
    if classic:
        print(f"\nClassic Elevation colors:")
        for elevation in [0, 600, 1200, 1800, 2400, 3000]:
            color = classic.get_color_at_elevation(elevation)
            print(f"  {elevation}m: RGB{color[:3]}")