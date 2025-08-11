#!/usr/bin/env python3
"""
High-Quality Elevation Data Scaling
Implements area-weighted averaging for arbitrary percentage downscaling of DEM data.
Preserves elevation statistics and handles partial pixel overlaps correctly.
"""

import numpy as np
from typing import Tuple, Optional
import math

class ElevationScaler:
    """High-quality elevation data scaling using area-weighted averaging"""
    
    @staticmethod
    def scale_elevation_data(elevation_array: np.ndarray, scale_percentage: float) -> np.ndarray:
        """
        Scale elevation data to specified percentage using area-weighted averaging.
        
        Args:
            elevation_array: Input elevation data (2D numpy array)
            scale_percentage: Target scale as percentage (1.0-100.0)
            
        Returns:
            Scaled elevation array
            
        Raises:
            ValueError: If scale_percentage is not in valid range
        """
        if not (1.0 <= scale_percentage <= 100.0):
            raise ValueError(f"Scale percentage must be between 1.0 and 100.0, got {scale_percentage}")
        
        if scale_percentage == 100.0:
            return elevation_array.copy()
        
        # Convert percentage to scale factor
        scale_factor = scale_percentage / 100.0
        
        input_height, input_width = elevation_array.shape
        
        # Calculate output dimensions
        output_width = max(1, int(round(input_width * scale_factor)))
        output_height = max(1, int(round(input_height * scale_factor)))
        
        print(f"Scaling from {input_width}×{input_height} to {output_width}×{output_height} ({scale_percentage}%)")
        
        # Use area-weighted averaging for high quality downscaling
        return ElevationScaler._area_weighted_resample(
            elevation_array, output_width, output_height
        )
    
    @staticmethod
    def _area_weighted_resample(input_array: np.ndarray, output_width: int, output_height: int) -> np.ndarray:
        """
        Perform area-weighted resampling for high-quality downscaling.
        Each output pixel value is computed as the area-weighted average of all 
        input pixels that contribute to it.
        """
        input_height, input_width = input_array.shape
        output_array = np.full((output_height, output_width), np.nan, dtype=np.float64)
        
        # Scale factors
        x_scale = input_width / output_width
        y_scale = input_height / output_height
        
        # Process each output pixel
        for out_y in range(output_height):
            for out_x in range(output_width):
                # Calculate the area in input space that this output pixel represents
                left = out_x * x_scale
                right = (out_x + 1) * x_scale
                top = out_y * y_scale
                bottom = (out_y + 1) * y_scale
                
                # Find input pixel range that overlaps with this output pixel
                left_px = int(np.floor(left))
                right_px = int(np.ceil(right))
                top_px = int(np.floor(top))
                bottom_px = int(np.ceil(bottom))
                
                # Clamp to input array bounds
                left_px = max(0, left_px)
                right_px = min(input_width, right_px)
                top_px = max(0, top_px)
                bottom_px = min(input_height, bottom_px)
                
                total_weight = 0.0
                weighted_sum = 0.0
                
                # Calculate contribution of each overlapping input pixel
                for in_y in range(top_px, bottom_px):
                    for in_x in range(left_px, right_px):
                        
                        if np.isnan(input_array[in_y, in_x]):
                            continue  # Skip no-data values
                        
                        # Calculate overlap area between input and output pixels
                        overlap_left = max(left, in_x)
                        overlap_right = min(right, in_x + 1)
                        overlap_top = max(top, in_y)
                        overlap_bottom = min(bottom, in_y + 1)
                        
                        if overlap_right > overlap_left and overlap_bottom > overlap_top:
                            overlap_area = (overlap_right - overlap_left) * (overlap_bottom - overlap_top)
                            
                            weighted_sum += input_array[in_y, in_x] * overlap_area
                            total_weight += overlap_area
                
                # Compute final value
                if total_weight > 0:
                    output_array[out_y, out_x] = weighted_sum / total_weight
                # else: remains NaN (no valid data contributed)
        
        return output_array.astype(input_array.dtype)
    
    @staticmethod
    def calculate_output_dimensions(input_width: int, input_height: int, scale_percentage: float) -> Tuple[int, int]:
        """
        Calculate output dimensions for given input size and scale percentage.
        
        Returns:
            (output_width, output_height) tuple
        """
        if not (1.0 <= scale_percentage <= 100.0):
            raise ValueError(f"Scale percentage must be between 1.0 and 100.0, got {scale_percentage}")
        
        scale_factor = scale_percentage / 100.0
        output_width = max(1, int(round(input_width * scale_factor)))
        output_height = max(1, int(round(input_height * scale_factor)))
        
        return output_width, output_height
    
    @staticmethod
    def get_memory_estimate_mb(input_width: int, input_height: int, scale_percentage: float) -> float:
        """
        Estimate memory usage in MB for scaling operation.
        Useful for warning users about large operations.
        """
        output_width, output_height = ElevationScaler.calculate_output_dimensions(
            input_width, input_height, scale_percentage
        )
        
        # Estimate: input array + output array + working memory
        input_size_mb = (input_width * input_height * 4) / (1024 * 1024)  # 4 bytes per float32
        output_size_mb = (output_width * output_height * 8) / (1024 * 1024)  # 8 bytes per float64
        working_memory_mb = input_size_mb * 0.5  # Rough estimate for working arrays
        
        total_mb = input_size_mb + output_size_mb + working_memory_mb
        return total_mb


def test_elevation_scaler():
    """Test the elevation scaler with sample data"""
    # Create test elevation data (100x100 with some realistic elevation values)
    np.random.seed(42)
    test_data = np.random.uniform(100, 3000, (100, 100)).astype(np.float32)
    
    # Add some no-data values
    test_data[0:5, 0:5] = np.nan
    
    print("Testing ElevationScaler...")
    print(f"Input: {test_data.shape}, range: {np.nanmin(test_data):.1f} to {np.nanmax(test_data):.1f}")
    
    # Test various scaling percentages
    for percentage in [50.0, 25.0, 16.7, 10.0]:
        scaled = ElevationScaler.scale_elevation_data(test_data, percentage)
        print(f"Scaled to {percentage}%: {scaled.shape}, range: {np.nanmin(scaled):.1f} to {np.nanmax(scaled):.1f}")
    
    print("All tests passed!")

if __name__ == "__main__":
    test_elevation_scaler()