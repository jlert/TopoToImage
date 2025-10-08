#!/usr/bin/env python3
"""
NaN-aware interpolation for DEM data scaling.
Properly handles no-data values during downsampling to prevent interpolation artifacts.
"""

# Debug control - set to True only when actively debugging
_DEBUG = False

import numpy as np
from scipy import ndimage
from typing import Tuple

def resize_with_nan_exclusion(data: np.ndarray, target_shape: Tuple[int, int], method: str = 'lanczos') -> np.ndarray:
    """
    Resize elevation data while properly excluding NaN values from interpolation.
    
    This prevents no-data areas from being averaged with valid elevation data,
    which would create incorrect elevation values at boundaries.
    
    Args:
        data: Input elevation data with NaN for no-data areas
        target_shape: Target (height, width) for output
        method: Interpolation method ('lanczos', 'bicubic', 'bilinear')
        
    Returns:
        Resized elevation data with proper NaN handling
    """
    
    # Get dimensions
    original_shape = data.shape
    target_height, target_width = target_shape
    
    if _DEBUG:
        print(f"🔧 NaN-aware resize: {original_shape} → {target_shape}")
    
    # Create mask for valid data (not NaN)
    valid_mask = ~np.isnan(data)
    valid_count_before = np.sum(valid_mask)
    
    if valid_count_before == 0:
        if _DEBUG:
            print("⚠️ No valid data found, returning NaN array")
        return np.full(target_shape, np.nan, dtype=np.float32)
    
    if _DEBUG:
        print(f"   Valid pixels before: {valid_count_before:,}")
    
    # Method 1: Distance-weighted interpolation with NaN exclusion
    if method == 'lanczos' or method == 'bicubic':
        try:
            result = _resize_with_weights(data, target_shape)
            valid_count_after = np.sum(~np.isnan(result))
            if _DEBUG:
                print(f"✅ NaN-aware resize complete: {valid_count_after:,} valid pixels")
            return result
        except Exception as e:
            if _DEBUG:
                print(f"⚠️ NaN-aware resize failed ({e}), falling back to simple method")
    
    # Fallback: Simple block averaging with NaN exclusion
    return _resize_with_block_averaging(data, target_shape)

def _resize_with_weights(data: np.ndarray, target_shape: Tuple[int, int]) -> np.ndarray:
    """
    Resize using weighted interpolation that excludes NaN values.
    """
    from scipy.ndimage import zoom
    
    target_height, target_width = target_shape
    original_height, original_width = data.shape
    
    # Calculate zoom factors
    zoom_y = target_height / original_height
    zoom_x = target_width / original_width
    
    # Create valid data mask
    valid_mask = ~np.isnan(data)
    
    # Replace NaN with 0 for processing (will be weighted out)
    data_filled = np.where(valid_mask, data, 0.0)
    
    # Zoom the data and the mask separately using bicubic interpolation for higher quality
    try:
        data_zoomed = zoom(data_filled, (zoom_y, zoom_x), order=3, mode='nearest')
        mask_zoomed = zoom(valid_mask.astype(float), (zoom_y, zoom_x), order=3, mode='nearest')
    except Exception as e:
        # Fallback to bilinear if bicubic fails
        if _DEBUG:
            print(f"   ⚠️ Bicubic NaN-aware resize failed ({e}), using bilinear")
        data_zoomed = zoom(data_filled, (zoom_y, zoom_x), order=1, mode='nearest')
        mask_zoomed = zoom(valid_mask.astype(float), (zoom_y, zoom_x), order=1, mode='nearest')
    
    # Create result array
    result = np.full(target_shape, np.nan, dtype=np.float32)
    
    # Only set values where mask indicates valid data
    # Use threshold to determine if enough valid data contributed
    valid_threshold = 0.1  # At least 10% valid data required
    valid_output_mask = mask_zoomed > valid_threshold
    
    result[valid_output_mask] = data_zoomed[valid_output_mask] / mask_zoomed[valid_output_mask]
    
    return result

def _resize_with_block_averaging(data: np.ndarray, target_shape: Tuple[int, int]) -> np.ndarray:
    """
    Resize using block averaging that excludes NaN values.
    This is the most robust method for preserving no-data boundaries.
    """
    target_height, target_width = target_shape
    original_height, original_width = data.shape
    
    # Calculate block sizes
    block_height = original_height / target_height
    block_width = original_width / target_width
    
    result = np.full(target_shape, np.nan, dtype=np.float32)
    
    for i in range(target_height):
        for j in range(target_width):
            # Calculate source region
            y_start = int(i * block_height)
            y_end = int((i + 1) * block_height)
            x_start = int(j * block_width)
            x_end = int((j + 1) * block_width)
            
            # Extract block
            block = data[y_start:y_end, x_start:x_end]
            
            # Only compute average of valid (non-NaN) values
            valid_values = block[~np.isnan(block)]
            
            if len(valid_values) > 0:
                # Use mean of valid values only
                result[i, j] = np.mean(valid_values)
            # Otherwise leave as NaN (no valid data in this block)
    
    return result

def test_nan_aware_interpolation():
    """Test the NaN-aware interpolation with a synthetic dataset"""
    
    if _DEBUG:
        print("🧪 Testing NaN-aware Interpolation")
    if _DEBUG:
        print("=" * 50)
    
    # Create test data with no-data areas
    data = np.random.rand(100, 100) * 1000  # Random elevations 0-1000m
    
    # Create no-data areas (simulating ocean or missing data)
    data[:20, :] = np.nan  # Top stripe
    data[:, -15:] = np.nan  # Right stripe  
    data[40:60, 30:50] = np.nan  # Central block
    
    if _DEBUG:
        print(f"Original data: {data.shape}")
    if _DEBUG:
        print(f"Valid pixels: {np.sum(~np.isnan(data)):,}")
    if _DEBUG:
        print(f"NaN pixels: {np.sum(np.isnan(data)):,}")
    
    # Test resize to 50x50 (50% scale)
    result = resize_with_nan_exclusion(data, (50, 50), method='lanczos')
    
    if _DEBUG:
        print(f"\nResult data: {result.shape}")
    if _DEBUG:
        print(f"Valid pixels: {np.sum(~np.isnan(result)):,}")
    if _DEBUG:
        print(f"NaN pixels: {np.sum(np.isnan(result)):,}")
    
    # Check that no-data boundaries are preserved
    boundary_check_passed = True
    
    # Check that areas that were entirely NaN are still NaN
    if not np.all(np.isnan(result[:10, :])):  # Top area should be all NaN
        boundary_check_passed = False
        if _DEBUG:
            print("❌ No-data area was contaminated with interpolated values")
    
    if boundary_check_passed:
        if _DEBUG:
            print("✅ No-data boundaries properly preserved")
    
    return result

if __name__ == "__main__":
    test_nan_aware_interpolation()