#!/usr/bin/env python3
"""
Enhanced coordinate validation system for DEM Visualizer
Handles coordinate clamping, pixel grid snapping, DMS parsing, and formatting
"""

import re
from typing import Tuple, Optional, Dict
from coordinate_converter import CoordinateConverter

class CoordinateValidator:
    """
    Comprehensive coordinate validation and formatting system
    """
    
    def __init__(self):
        # DMS parsing regex patterns
        self.dms_patterns = [
            # 45°30'15"N, 45°30'15"W, etc.
            r'^(-?\d+)°(\d+)\'(\d+(?:\.\d+)?)\"([NSEW])$',
            # 45°30'15.5"N
            r'^(-?\d+)°(\d+)\'(\d+(?:\.\d+)?)\"([NSEW])$',
            # 45°30"N (no minutes)
            r'^(-?\d+)°(\d+)\"([NSEW])$',
            # 45°N (degrees only)
            r'^(-?\d+)°([NSEW])$',
            # -45.5 (plain decimal)
            r'^(-?\d+(?:\.\d+)?)$'
        ]
    
    def snap_to_pixel_grid(self, coordinate: float, database_bounds: Dict, 
                          is_longitude: bool) -> float:
        """
        Snap coordinate to pixel grid boundaries
        
        Args:
            coordinate: The coordinate to snap
            database_bounds: Dict with 'west', 'north', 'east', 'south', 'width_pixels', 'height_pixels'
            is_longitude: True for longitude (west/east), False for latitude (north/south)
            
        Returns:
            Snapped coordinate
        """
        try:
            # Get database info
            db_west = database_bounds.get('west', 0)
            db_north = database_bounds.get('north', 0) 
            db_east = database_bounds.get('east', 0)
            db_south = database_bounds.get('south', 0)
            width_pixels = database_bounds.get('width_pixels', 0)
            height_pixels = database_bounds.get('height_pixels', 0)
            
            if width_pixels <= 0 or height_pixels <= 0:
                return coordinate
            
            if is_longitude:
                # Longitude (west/east)
                degrees_per_pixel = abs(db_east - db_west) / width_pixels
                offset = coordinate - db_west
                pixel_number = round(offset / degrees_per_pixel)
                snapped = db_west + (pixel_number * degrees_per_pixel)
            else:
                # Latitude (north/south)
                degrees_per_pixel = abs(db_north - db_south) / height_pixels
                offset = coordinate - db_south  # Distance from south boundary
                pixel_number = round(offset / degrees_per_pixel)
                snapped = db_south + (pixel_number * degrees_per_pixel)
            
            return snapped
            
        except Exception as e:
            print(f"Warning: Could not snap to pixel grid: {e}")
            return coordinate
    
    def clamp_to_database_bounds(self, coordinate: float, database_bounds: Dict,
                                is_longitude: bool, other_longitude: Optional[float] = None) -> float:
        """
        Clamp coordinate to database boundaries with meridian-crossing awareness
        
        Args:
            coordinate: The coordinate to clamp
            database_bounds: Dict with boundary information
            is_longitude: True for longitude, False for latitude
            other_longitude: For longitude validation, the other longitude coordinate to determine crossing limits
            
        Returns:
            Clamped coordinate
        """
        if is_longitude:
            # Longitude bounds
            west = database_bounds.get('west', -180)
            east = database_bounds.get('east', 180)
            
            # Handle wrap-around for global databases
            db_width = abs(east - west)
            
            if db_width >= 359.99:  # Use tolerance for floating-point precision
                # Global database - use meridian-crossing aware limits
                if other_longitude is not None:
                    # Calculate maximum allowed span (360°) from the other coordinate
                    min_allowed = other_longitude - 360.0
                    max_allowed = other_longitude + 360.0
                    
                    # Clamp to the 360° range centered on the other coordinate
                    return max(min_allowed, min(max_allowed, coordinate))
                else:
                    # No other coordinate provided - allow extended range for global databases
                    # This provides reasonable limits while allowing meridian crossing
                    return max(-540.0, min(540.0, coordinate))
            else:
                # Regional database - clamp to bounds
                return max(west, min(east, coordinate))
        else:
            # Latitude bounds
            north = database_bounds.get('north', 90)
            south = database_bounds.get('south', -90)
            return max(south, min(north, coordinate))
    
    def parse_coordinate_input(self, input_text: str) -> Optional[float]:
        """
        Parse coordinate input in various formats (decimal, DMS)
        
        Args:
            input_text: User input string
            
        Returns:
            Parsed coordinate as float, or None if invalid
        """
        if not input_text or not input_text.strip():
            return None
            
        input_text = input_text.strip().upper()
        
        # Try DMS patterns first
        for pattern in self.dms_patterns:
            match = re.match(pattern, input_text)
            if match:
                return self._parse_dms_match(match)
        
        # Try plain decimal
        try:
            return float(input_text)
        except ValueError:
            return None
    
    def _parse_dms_match(self, match) -> Optional[float]:
        """Parse a DMS regex match into decimal degrees"""
        groups = match.groups()
        
        if len(groups) == 1:
            # Plain decimal: (-?\d+(?:\.\d+)?)
            return float(groups[0])
        elif len(groups) == 2:
            # Degrees only: 45°N
            degrees = float(groups[0])
            direction = groups[1]
            if direction in ['S', 'W']:
                degrees = -degrees
            return degrees
        elif len(groups) == 3:
            # Degrees and minutes: 45°30"N
            degrees = float(groups[0])
            minutes = float(groups[1])
            direction = groups[2]
            
            # Validate ranges
            if minutes >= 60:
                return None
                
            decimal = degrees + minutes/60.0
            if direction in ['S', 'W']:
                decimal = -decimal
            return decimal
        elif len(groups) == 4:
            # Full DMS: 45°30'15"N
            degrees = float(groups[0])
            minutes = float(groups[1])
            seconds = float(groups[2])
            direction = groups[3]
            
            # Validate ranges
            if minutes >= 60 or seconds >= 60:
                return None
                
            decimal = degrees + minutes/60.0 + seconds/3600.0
            if direction in ['S', 'W']:
                decimal = -decimal
            return decimal
        
        return None
    
    def validate_and_format_coordinate(self, input_text: str, database_bounds: Dict,
                                     is_longitude: bool, use_dms: bool = False, 
                                     other_longitude: Optional[float] = None) -> Tuple[float, str]:
        """
        Complete coordinate validation pipeline
        
        Args:
            input_text: User input
            database_bounds: Database boundary information
            is_longitude: True for longitude, False for latitude
            use_dms: True to format output as DMS
            other_longitude: For longitude validation, the other longitude coordinate for meridian-crossing limits
            
        Returns:
            Tuple of (validated_coordinate, formatted_text)
        """
        # Parse input
        parsed = self.parse_coordinate_input(input_text)
        if parsed is None:
            # Invalid input - return original
            return 0.0, input_text
        
        # Clamp to database bounds with meridian-crossing awareness
        clamped = self.clamp_to_database_bounds(parsed, database_bounds, is_longitude, other_longitude)
        
        # Snap to pixel grid (but skip for global databases with extended coordinates)
        if is_longitude:
            db_west = database_bounds.get('west', -180)
            db_east = database_bounds.get('east', 180)
            db_width = abs(db_east - db_west)
            
            # For global databases, only snap coordinates within database bounds
            if db_width >= 359.99 and (clamped < db_west or clamped > db_east):
                # Extended coordinate on global database - don't snap to pixel grid
                snapped = clamped
            else:
                # Normal coordinate or regional database - apply pixel snapping
                snapped = self.snap_to_pixel_grid(clamped, database_bounds, is_longitude)
        else:
            # Always snap latitude coordinates
            snapped = self.snap_to_pixel_grid(clamped, database_bounds, is_longitude)
        
        # Format output with clean display
        formatted = self.format_coordinate_clean(snapped, is_longitude, use_dms)
        
        return snapped, formatted
    
    def format_coordinate_clean(self, coordinate: float, is_longitude: bool, 
                              use_dms: bool = False) -> str:
        """
        Format coordinate with clean decimal display (remove trailing zeros)
        
        Args:
            coordinate: Coordinate value
            is_longitude: True for longitude, False for latitude
            use_dms: True to format as DMS
            
        Returns:
            Formatted coordinate string
        """
        if use_dms:
            return CoordinateConverter.format_coordinate(coordinate, is_longitude, True)
        else:
            # Clean decimal formatting
            if abs(coordinate - round(coordinate)) < 1e-10:
                # Essentially a whole number
                return f"{coordinate:.0f}"
            else:
                # Has decimals - remove trailing zeros
                formatted = f"{coordinate:.6f}".rstrip('0').rstrip('.')
                return formatted

# Global validator instance
coordinate_validator = CoordinateValidator()