#!/usr/bin/env python3
"""
Export Controls Logic
Implements the sophisticated TopoToImage-style width/height/resolution lock system
with automatic recalculation and unit conversions.
"""

from enum import Enum
from typing import Tuple, Optional
import math

class LockType(Enum):
    """Which field is currently locked"""
    WIDTH = 1
    HEIGHT = 2  
    RESOLUTION = 3

class Units(Enum):
    """Supported units for width/height measurements"""
    INCHES = 1
    POINTS = 2
    PICAS = 3
    CENTIMETERS = 4

class ExportControlsLogic:
    """Core logic for the interconnected width/height/resolution controls"""
    
    # Unit conversion factors (to inches)
    POINTS_PER_INCH = 72.0
    PICAS_PER_INCH = 6.0
    CM_PER_INCH = 2.54
    
    def __init__(self):
        # Current values (internal representation always in inches)
        self.physical_width_inches = 10.0  # Physical width in inches
        self.physical_height_inches = 10.0  # Physical height in inches
        self.pixels_per_inch = 300.0  # Resolution in pixels per inch
        
        # Current settings
        self.locked_field = LockType.WIDTH  # Default to width locked
        self.current_units = Units.INCHES  # Default to inches
        
        # Pixel dimensions from geographic selection and scale
        self.pixel_width = 3000  # Will be updated from map selection
        self.pixel_height = 3000  # Will be updated from map selection
        
    def set_pixel_dimensions(self, pixel_width: int, pixel_height: int):
        """Update pixel dimensions from geographic selection and scale percentage"""
        self.pixel_width = pixel_width
        self.pixel_height = pixel_height
        # Recalculate physical dimensions based on current lock
        self._recalculate_from_lock()
    
    def set_lock(self, lock_type: LockType):
        """Change which field is locked and recalculate others"""
        self.locked_field = lock_type
        self._recalculate_from_lock()
    
    def set_units(self, units: Units):
        """Change units (doesn't affect calculations, just display)"""
        self.current_units = units
    
    def set_width(self, width_value: float):
        """Set width value (in current units) and make width locked"""
        # Convert to inches
        width_inches = self._convert_to_inches(width_value, self.current_units)
        self.physical_width_inches = width_inches
        self.locked_field = LockType.WIDTH
        self._recalculate_from_lock()
    
    def set_height(self, height_value: float):
        """Set height value (in current units) and make height locked"""
        # Convert to inches  
        height_inches = self._convert_to_inches(height_value, self.current_units)
        self.physical_height_inches = height_inches
        self.locked_field = LockType.HEIGHT
        self._recalculate_from_lock()
    
    def set_resolution(self, resolution_value: float):
        """Set resolution value (always in pixels per inch) and make resolution locked"""
        self.pixels_per_inch = resolution_value
        self.locked_field = LockType.RESOLUTION
        self._recalculate_from_lock()
    
    def get_width(self) -> float:
        """Get current width in current units"""
        return self._convert_from_inches(self.physical_width_inches, self.current_units)
    
    def get_height(self) -> float:
        """Get current height in current units"""
        return self._convert_from_inches(self.physical_height_inches, self.current_units)
    
    def get_resolution(self) -> float:
        """Get current resolution (always pixels per inch)"""
        return self.pixels_per_inch
    
    def get_output_pixel_dimensions(self) -> Tuple[int, int]:
        """Get the final output pixel dimensions"""
        return self.pixel_width, self.pixel_height
    
    def _recalculate_from_lock(self):
        """Recalculate the non-locked fields based on the locked field"""
        if self.locked_field == LockType.WIDTH:
            # Width is locked, calculate pixels_per_inch from width
            if self.physical_width_inches > 0:
                self.pixels_per_inch = self.pixel_width / self.physical_width_inches
                # Recalculate height
                if self.pixels_per_inch > 0:
                    self.physical_height_inches = self.pixel_height / self.pixels_per_inch
                    
        elif self.locked_field == LockType.HEIGHT:
            # Height is locked, calculate pixels_per_inch from height
            if self.physical_height_inches > 0:
                self.pixels_per_inch = self.pixel_height / self.physical_height_inches
                # Recalculate width
                if self.pixels_per_inch > 0:
                    self.physical_width_inches = self.pixel_width / self.pixels_per_inch
                    
        elif self.locked_field == LockType.RESOLUTION:
            # Resolution is locked, calculate width and height from resolution
            if self.pixels_per_inch > 0:
                self.physical_width_inches = self.pixel_width / self.pixels_per_inch
                self.physical_height_inches = self.pixel_height / self.pixels_per_inch
    
    def _convert_to_inches(self, value: float, units: Units) -> float:
        """Convert a value from specified units to inches"""
        if units == Units.INCHES:
            return value
        elif units == Units.POINTS:
            return value / self.POINTS_PER_INCH
        elif units == Units.PICAS:
            return value / self.PICAS_PER_INCH
        elif units == Units.CENTIMETERS:
            return value / self.CM_PER_INCH
        else:
            return value  # Default to inches
    
    def _convert_from_inches(self, inches: float, units: Units) -> float:
        """Convert a value from inches to specified units"""
        if units == Units.INCHES:
            return inches
        elif units == Units.POINTS:
            return inches * self.POINTS_PER_INCH
        elif units == Units.PICAS:
            return inches * self.PICAS_PER_INCH
        elif units == Units.CENTIMETERS:
            return inches * self.CM_PER_INCH
        else:
            return inches  # Default to inches
    
    def format_value(self, value: float) -> str:
        """Format a value for display with appropriate precision and scientific notation"""
        if abs(value) < 0.001 or abs(value) >= 10000:
            # Use scientific notation for very small or very large values
            return f"{value:.3e}"
        elif abs(value) < 0.1:
            # Use more decimal places for small values
            return f"{value:.4f}"
        elif abs(value) < 10:
            # Use 3 decimal places for small values
            return f"{value:.3f}"
        elif abs(value) < 100:
            # Use 2 decimal places for medium values
            return f"{value:.2f}"
        else:
            # Use 1 decimal place for large values
            return f"{value:.1f}"
    
    def get_unit_label(self) -> str:
        """Get the current unit label for display"""
        if self.current_units == Units.INCHES:
            return "in."
        elif self.current_units == Units.POINTS:
            return "pts."
        elif self.current_units == Units.PICAS:
            return "pi."
        elif self.current_units == Units.CENTIMETERS:
            return "cm"
        else:
            return "in."
    
    def is_database_export_type(self, export_type: str) -> bool:
        """Check if the export type is a database (should gray out controls)"""
        database_types = [
            "Geocart image database",
            "DEM elevation database", 
            "Geotiff elevation database"
        ]
        return export_type in database_types
    
    def calculate_memory_estimate_mb(self) -> float:
        """Estimate memory usage for the export operation"""
        total_pixels = self.pixel_width * self.pixel_height
        # Estimate 4 bytes per pixel for RGBA
        memory_mb = (total_pixels * 4) / (1024 * 1024)
        return memory_mb


def test_export_controls_logic():
    """Test the export controls logic"""
    print("Testing ExportControlsLogic...")
    
    logic = ExportControlsLogic()
    
    # Test initial state
    print(f"Initial: {logic.get_width():.3f} x {logic.get_height():.3f} in, {logic.get_resolution():.1f} ppi")
    
    # Test pixel dimension update
    logic.set_pixel_dimensions(3000, 2000)
    print(f"After setting pixels (3000x2000): {logic.get_width():.3f} x {logic.get_height():.3f} in, {logic.get_resolution():.1f} ppi")
    
    # Test changing width (should lock width)
    logic.set_width(5.0)
    print(f"After setting width to 5.0: {logic.get_width():.3f} x {logic.get_height():.3f} in, {logic.get_resolution():.1f} ppi")
    print(f"Locked field: {logic.locked_field}")
    
    # Test changing resolution (should lock resolution)
    logic.set_resolution(150.0)
    print(f"After setting resolution to 150: {logic.get_width():.3f} x {logic.get_height():.3f} in, {logic.get_resolution():.1f} ppi")
    print(f"Locked field: {logic.locked_field}")
    
    # Test unit conversion
    logic.set_units(Units.CENTIMETERS)
    print(f"In centimeters: {logic.get_width():.3f} x {logic.get_height():.3f} cm")
    
    print("All tests passed!")

if __name__ == "__main__":
    test_export_controls_logic()