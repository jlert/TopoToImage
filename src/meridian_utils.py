#!/usr/bin/env python3
"""
Meridian Crossing Utilities for DEM Visualizer

Handles prime meridian crossing calculations and coordinate normalization
for both single-file and multi-file database systems.
"""

import numpy as np
from typing import Tuple, List, Optional, NamedTuple


class LongitudeSpan(NamedTuple):
    """Represents a longitude span that may cross the prime meridian"""
    width_degrees: float
    crosses_meridian: bool
    region1_west: float
    region1_east: float
    region2_west: Optional[float] = None
    region2_east: Optional[float] = None


def normalize_longitude(lon: float) -> float:
    """Normalize longitude to [-180, 180) range (exclusive of 180)"""
    while lon > 180:
        lon -= 360
    while lon <= -180:
        lon += 360
    # Special case: keep -180 as -180 (don't convert to 180)
    # This preserves full world bounds (-180° to 180°) correctly
    if abs(lon - 180.0) < 1e-10:  # Very close to 180°
        lon = -180.0
    return lon


def calculate_longitude_span(west: float, east: float) -> LongitudeSpan:
    """
    Calculate longitude span handling prime meridian crossing
    
    Args:
        west: Western longitude (any range, will be normalized)  
        east: Eastern longitude (any range, will be normalized)
        
    Returns:
        LongitudeSpan with width and region information
    """
    # Store original values for crossing detection
    original_west = west
    original_east = east
    
    # Special case: Full world bounds (-180° to 180°)
    # Handle this before normalization to avoid normalize_longitude converting 180° to -180°
    if (abs(original_west - (-180.0)) < 0.01 and abs(original_east - 180.0) < 0.01):
        return LongitudeSpan(
            width_degrees=360.0,
            crosses_meridian=True,
            region1_west=-180.0,
            region1_east=180.0,
            region2_west=None,  # Full world has no second region
            region2_east=None
        )
    
    # Special case: Half-world spans ending at 180° (e.g., 0° to 180°)
    # These don't cross meridian but normalize_longitude converts 180° to -180°
    if abs(original_east - 180.0) < 0.01 and original_west >= -180.0 and original_west <= 180.0:
        # Calculate width using original values
        width = original_east - original_west
        if width > 0 and width <= 180:
            return LongitudeSpan(
                width_degrees=width,
                crosses_meridian=False,
                region1_west=original_west,
                region1_east=original_east
            )
    
    # Detect intended meridian crossing BEFORE normalization
    intended_crossing = False
    
    # Rule 1: If east > 180, it's really west longitude → crossing  
    if original_east > 180:
        intended_crossing = True
    # Rule 2: If west < -180, it's really east longitude → crossing   
    elif original_west < -180:
        intended_crossing = True
    
    # Normalize inputs for standard processing
    west = normalize_longitude(west)
    east = normalize_longitude(east)
    
    # Rule 3: After normalization, check if west > east (standard crossing)
    if west > east:
        intended_crossing = True
    
    if not intended_crossing:
        # No meridian crossing
        if west == east:
            # Same longitude - no span
            return LongitudeSpan(
                width_degrees=0.0,
                crosses_meridian=False,
                region1_west=west,
                region1_east=east
            )
        else:
            # Normal case: west < east
            return LongitudeSpan(
                width_degrees=east - west,
                crosses_meridian=False,
                region1_west=west,
                region1_east=east
            )
    else:
        # Meridian crossing detected
        if west > east:
            # Standard crossing: west=170°, east=-170° → width=20°
            width = (180 - west) + (east + 180)
        else:
            # Special case where original coordinates indicated crossing
            # but normalized coordinates don't (e.g., -162° to 200.5°E)
            # Calculate the eastward span across the meridian
            width = (180 - west) + (east + 180)
        
        return LongitudeSpan(
            width_degrees=width,
            crosses_meridian=True,
            region1_west=west,
            region1_east=180.0,
            region2_west=-180.0,
            region2_east=east
        )


def map_longitude_to_array_x(lon: float, bounds_west: float, bounds_east: float, 
                           array_width: int, crosses_meridian: bool = False) -> int:
    """
    Map longitude coordinate to array X position handling meridian crossing
    
    Args:
        lon: Longitude to map
        bounds_west: Western boundary of the array coverage
        bounds_east: Eastern boundary of the array coverage  
        array_width: Width of the array in pixels
        crosses_meridian: Whether the bounds cross the prime meridian
        
    Returns:
        X coordinate in the array
    """
    # Special case: full world bounds (-180° to 180°)
    if (abs(bounds_west - (-180.0)) < 0.01 and abs(bounds_east - 180.0) < 0.01):
        # Full world: linear mapping from -180° to 180° (360° span)
        # Don't normalize longitude for full world bounds to preserve the 360° span
        if lon > 180.0:
            lon -= 360.0
        elif lon < -180.0:
            lon += 360.0
        # Map -180° to 180° linearly across array width
        relative_pos = (lon + 180.0) / 360.0
        return int(relative_pos * array_width)
    
    lon = normalize_longitude(lon)
    bounds_west = normalize_longitude(bounds_west)
    bounds_east = normalize_longitude(bounds_east)
    
    if not crosses_meridian:
        # Normal case: simple linear mapping
        if bounds_east == bounds_west:
            return 0
        return int((lon - bounds_west) / (bounds_east - bounds_west) * array_width)
    else:
        # Meridian crossing case
        if lon >= bounds_west:
            # Longitude is in the western region (170° to 180°)
            western_width = 180 - bounds_west
            total_width = calculate_longitude_span(bounds_west, bounds_east).width_degrees
            relative_pos = (lon - bounds_west) / total_width
        else:
            # Longitude is in the eastern region (-180° to east)
            western_width = 180 - bounds_west
            eastern_pos = lon + 180  # Convert to positive offset from -180°
            total_width = calculate_longitude_span(bounds_west, bounds_east).width_degrees
            relative_pos = (western_width + eastern_pos) / total_width
            
        return int(relative_pos * array_width)


def split_meridian_crossing_bounds(west: float, north: float, east: float, south: float) -> List[Tuple[float, float, float, float]]:
    """
    Split bounds that cross the prime meridian into two non-crossing regions
    
    Args:
        west, north, east, south: Geographic bounds
        
    Returns:
        List of (west, north, east, south) tuples for each region
    """
    span = calculate_longitude_span(west, east)
    
    if not span.crosses_meridian:
        # No crossing - return original bounds
        return [(west, north, east, south)]
    else:
        # Crossing - return two regions
        return [
            (span.region1_west, north, span.region1_east, south),  # Western region
            (span.region2_west, north, span.region2_east, south)   # Eastern region
        ]


def calculate_meridian_crossing_output_dimensions(west: float, east: float, pixels_per_degree: float) -> Tuple[int, bool]:
    """
    Calculate output array width handling meridian crossing
    
    Args:
        west: Western longitude
        east: Eastern longitude 
        pixels_per_degree: Resolution in pixels per degree
        
    Returns:
        (width_pixels, crosses_meridian)
    """
    span = calculate_longitude_span(west, east)
    width_pixels = int(span.width_degrees * pixels_per_degree)
    return width_pixels, span.crosses_meridian


def test_meridian_utils():
    """Test the meridian crossing utilities"""
    print("🧪 Testing Meridian Crossing Utilities")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        ("Normal span", 10.0, 20.0, 10.0, False),
        ("Pacific crossing", 170.0, -170.0, 20.0, True),
        ("Bering Sea", 160.0, -160.0, 40.0, True),
        ("Date line", 179.0, -179.0, 2.0, True),
        ("Small crossing", 179.5, -179.5, 1.0, True),
    ]
    
    for name, west, east, expected_width, expected_crossing in test_cases:
        span = calculate_longitude_span(west, east)
        
        print(f"\n📊 {name}:")
        print(f"   Input: west={west}°, east={east}°")
        print(f"   Expected: width={expected_width}°, crosses={expected_crossing}")
        print(f"   Calculated: width={span.width_degrees}°, crosses={span.crosses_meridian}")
        
        if abs(span.width_degrees - expected_width) < 0.01 and span.crosses_meridian == expected_crossing:
            print(f"   ✅ PASS")
        else:
            print(f"   ❌ FAIL")
            
        if span.crosses_meridian:
            print(f"   Regions: [{span.region1_west}°, {span.region1_east}°] and [{span.region2_west}°, {span.region2_east}°]")
    
    # Test coordinate mapping
    print(f"\n🧭 Testing Coordinate Mapping:")
    
    # Pacific crossing example: west=170°, east=-170° (20° span)
    west, east = 170.0, -170.0
    array_width = 200  # 10 pixels per degree
    
    test_longitudes = [170.0, 175.0, 180.0, -180.0, -175.0, -170.0]
    expected_x = [0, 50, 100, 100, 150, 200]
    
    for i, lon in enumerate(test_longitudes):
        x = map_longitude_to_array_x(lon, west, east, array_width, crosses_meridian=True)
        exp = expected_x[i]
        status = "✅" if abs(x - exp) <= 1 else "❌"  # Allow 1 pixel tolerance
        print(f"   {status} lon={lon}° → x={x} (expected ~{exp})")
    
    print(f"\n🎉 Meridian utilities test complete!")


if __name__ == "__main__":
    test_meridian_utils()