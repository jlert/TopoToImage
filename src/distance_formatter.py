#!/usr/bin/env python3
"""
Distance formatting utilities for DEM Visualizer.
Formats distances in both kilometers and miles with smart decimal precision.
"""

def format_distance_km_miles(miles_value: float) -> str:
    """
    Format a distance value to show both kilometers and miles.
    
    Args:
        miles_value: Distance value in miles
        
    Returns:
        Formatted string like "10.1 km (7.6 mi.)"
        
    Decimal rules:
    - 2 decimal places if < 1
    - 1 decimal place if >= 1 and < 100  
    - 0 decimal places if >= 100
    """
    # Convert miles to kilometers (1 mile = 1.609344 km)
    km_value = miles_value * 1.609344
    
    # Determine decimal places based on the rules
    def get_decimal_places(value):
        if value < 1:
            return 2
        elif value < 100:
            return 1
        else:
            return 0
    
    # Format kilometers
    km_decimals = get_decimal_places(km_value)
    km_formatted = f"{km_value:.{km_decimals}f}"
    
    # Format miles  
    miles_decimals = get_decimal_places(miles_value)
    miles_formatted = f"{miles_value:.{miles_decimals}f}"
    
    return f"{km_formatted} km ({miles_formatted} mi.)"

def test_formatting():
    """Test the formatting function with various values"""
    test_values = [0.05, 0.5, 0.95, 1.0, 1.5, 10.3, 25.7, 99.9, 100.0, 150.2, 1000.5]
    
    print("Testing distance formatting:")
    print("Miles Input → Formatted Output")
    print("-" * 40)
    
    for miles in test_values:
        formatted = format_distance_km_miles(miles)
        print(f"{miles:8.2f} → {formatted}")

if __name__ == "__main__":
    test_formatting()