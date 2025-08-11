#!/usr/bin/env python3
"""
Coordinate format conversion utilities
Converts between decimal degrees and degrees/minutes/seconds format
Based on original TopoToImage BASIC code
"""

import re
import math

class CoordinateConverter:
    """Handles conversion between decimal degrees and DMS format"""
    
    @staticmethod
    def float_to_dms(decimal_degrees, is_longitude=True):
        """
        Convert decimal degrees to degrees/minutes/seconds format
        
        Args:
            decimal_degrees: Float value (e.g., -123.456789)
            is_longitude: True for longitude (E/W), False for latitude (N/S)
        
        Returns:
            String in format like "123°27'24.4404\"W" or "45°30'15.2\"N"
        """
        # Determine hemisphere
        if is_longitude:
            hemisphere = "E" if decimal_degrees >= 0 else "W"
        else:
            hemisphere = "N" if decimal_degrees >= 0 else "S"
        
        # Work with absolute value
        abs_degrees = abs(decimal_degrees)
        
        # Extract degrees (integer part)
        degrees = int(abs_degrees)
        
        # Extract minutes
        minutes_float = (abs_degrees - degrees) * 60
        minutes = int(minutes_float)
        
        # Extract seconds
        seconds_float = (minutes_float - minutes) * 60
        
        # Round seconds to 4 decimal places (like original BASIC code)
        seconds = round(seconds_float, 4)
        
        # Handle edge case where rounding pushes seconds to 60
        if seconds >= 60:
            seconds = 0
            minutes += 1
            if minutes >= 60:
                minutes = 0
                degrees += 1
        
        # Format the string
        if seconds == int(seconds):
            # No decimal places needed
            return f"{degrees}°{minutes:02d}'{int(seconds):02d}\"{hemisphere}"
        else:
            # Include decimal places
            return f"{degrees}°{minutes:02d}'{seconds:06.3f}\"{hemisphere}"
    
    @staticmethod
    def dms_to_float(dms_string):
        """
        Convert DMS format string to decimal degrees
        
        Args:
            dms_string: String like "123°27'24.44\"W" or "-123.456" or "123.456W"
        
        Returns:
            Float decimal degrees (negative for W/S hemispheres)
        """
        if not dms_string or not isinstance(dms_string, str):
            return 0.0
        
        # Clean up the input string
        dms_string = dms_string.strip()
        
        # Check if it's already a simple decimal number
        try:
            # Try to parse as simple float first
            if '°' not in dms_string and "'" not in dms_string and '"' not in dms_string:
                # Simple decimal format, possibly with N/S/E/W suffix
                numeric_part = re.sub(r'[NSEW]', '', dms_string.upper())
                decimal_value = float(numeric_part)
                
                # Check for hemisphere indicators
                if any(char in dms_string.upper() for char in ['W', 'S']):
                    decimal_value = -abs(decimal_value)
                
                return decimal_value
        except ValueError:
            pass
        
        # Parse DMS format
        try:
            # Initialize values
            degrees = 0
            minutes = 0
            seconds = 0
            is_negative = False
            
            # Check for negative indicators
            upper_dms = dms_string.upper()
            if any(char in upper_dms for char in ['W', 'S', '-']):
                is_negative = True
            
            # Remove negative sign for parsing
            clean_string = dms_string.replace('-', ' ')
            
            # Find degree symbol
            degree_pos = clean_string.find('°')
            if degree_pos > 0:
                degrees = float(clean_string[:degree_pos])
                remaining = clean_string[degree_pos + 1:]
            else:
                # No degree symbol, treat entire string as degrees
                # Remove any non-numeric characters except decimal point
                numeric_only = re.sub(r'[^0-9.-]', '', clean_string)
                if numeric_only:
                    degrees = float(numeric_only)
                remaining = ""
            
            # Find minute symbol
            if remaining:
                minute_pos = remaining.find("'")
                if minute_pos > 0:
                    minutes = float(remaining[:minute_pos])
                    remaining = remaining[minute_pos + 1:]
                elif remaining:
                    # No minute symbol but have remaining text
                    # Try to extract numeric value as minutes
                    numeric_part = re.search(r'[\d.]+', remaining)
                    if numeric_part:
                        minutes = float(numeric_part.group())
                        # Update remaining to exclude parsed minutes
                        remaining = remaining[numeric_part.end():]
                    else:
                        remaining = ""
            
            # Find second symbol
            if remaining:
                second_pos = remaining.find('"')
                if second_pos > 0:
                    seconds = float(remaining[:second_pos])
                elif remaining:
                    # No second symbol but have remaining numeric text
                    numeric_part = re.search(r'[\d.]+', remaining)
                    if numeric_part:
                        seconds = float(numeric_part.group())
            
            # Calculate decimal degrees
            decimal_degrees = degrees + (minutes / 60.0) + (seconds / 3600.0)
            
            # Apply negative sign if needed
            if is_negative:
                decimal_degrees = -abs(decimal_degrees)
            
            return decimal_degrees
            
        except (ValueError, AttributeError) as e:
            # If parsing fails, return 0 and possibly beep/warn
            print(f"Warning: Could not parse coordinate '{dms_string}': {e}")
            return 0.0
    
    @staticmethod
    def format_coordinate(decimal_degrees, is_longitude=True, use_dms=True):
        """
        Format coordinate in either decimal or DMS format
        
        Args:
            decimal_degrees: Float coordinate value
            is_longitude: True for longitude, False for latitude
            use_dms: True for DMS format, False for decimal format
        
        Returns:
            Formatted string
        """
        if use_dms:
            return CoordinateConverter.float_to_dms(decimal_degrees, is_longitude)
        else:
            # Decimal format without degree symbol
            return f"{decimal_degrees:.6f}"
    
    @staticmethod
    def parse_coordinate(coord_string):
        """
        Parse coordinate string in either format
        
        Args:
            coord_string: Input string in any supported format
        
        Returns:
            Float decimal degrees
        """
        return CoordinateConverter.dms_to_float(coord_string)

# Test the converter
if __name__ == "__main__":
    converter = CoordinateConverter()
    
    # Test cases
    test_values = [
        (-123.456789, True),   # Longitude
        (45.123456, False),    # Latitude
        (-89.999999, False),   # Near south pole
        (179.999999, True),    # Near dateline
    ]
    
    print("=== Coordinate Converter Test ===")
    
    for decimal, is_lon in test_values:
        dms = converter.float_to_dms(decimal, is_lon)
        back_to_decimal = converter.dms_to_float(dms)
        
        coord_type = "Longitude" if is_lon else "Latitude"
        print(f"{coord_type}: {decimal} → {dms} → {back_to_decimal}")
        print(f"  Accuracy: {abs(decimal - back_to_decimal):.10f} degrees")
        print()