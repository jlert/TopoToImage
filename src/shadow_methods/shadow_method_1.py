#!/usr/bin/env python3
"""
Shadow Method 1: Ray-Casting Algorithm

This is the current shadow calculation method that was previously embedded 
in terrain_renderer.py. It uses a ray-casting approach with post-process 
motion blur for soft edges.

Algorithm: For each pixel, cast a ray toward the light source to check 
if any terrain blocks the light path.

Performance: O(n³) complexity - can be very slow for large datasets
Visual Quality: Motion blur can cause shadows to creep onto lit slopes
"""

import numpy as np
import math
from typing import Optional


class ShadowMethod1:
    """
    Ray-casting shadow calculation method.
    
    This method casts rays from each pixel toward the light source to determine
    if the pixel is in shadow. Soft edges are applied using directional motion blur.
    """
    
    def __init__(self):
        """Initialize ShadowMethod1"""
        pass
    
    def calculate_shadows(
        self,
        elevation_data: np.ndarray,
        light_direction: int = 315,
        shadow_drop_distance: float = 1.0,
        shadow_soft_edge: int = 3,
        cell_size: float = 1.0,
        progress_callback: Optional[callable] = None
    ) -> np.ndarray:
        """
        Calculate cast shadows using ray-casting algorithm.
        
        Algorithm: For each pixel, cast a ray in the light direction. If any terrain 
        along the ray is higher than (current_elevation - drop_distance), the pixel is in shadow.
        
        Args:
            elevation_data: 2D numpy array of elevation values
            light_direction: Light direction in degrees (0-360)
            shadow_drop_distance: Shadow threshold - LOWER values = LONGER shadows (0.1-10.0)
            shadow_soft_edge: Size of soft edge blur in pixels
            cell_size: Size of each cell in elevation units (for future use)
            progress_callback: Optional callback for progress reporting
            
        Returns:
            2D numpy array with shadow values (0.0 = no shadow, 1.0 = full shadow)
        """
        height, width = elevation_data.shape
        shadow_map = np.zeros((height, width), dtype=np.float32)
        
        print(f"🌑 ShadowMethod1: drop_distance={shadow_drop_distance}, light_dir={light_direction}°")
        
        # Ray-casting approach: cast rays FROM terrain TOWARDS light source
        # to see if terrain blocks the light path (flipped direction)
        shadow_direction = (light_direction + 180) % 360  # Cast shadows opposite to light
        light_rad = math.radians(shadow_direction)
        light_dx = -math.sin(light_rad)   # Direction TOWARDS light source
        light_dy = math.cos(light_rad)    # Direction TOWARDS light source
        
        # For each pixel, cast a ray TOWARDS the light source to see if it's blocked
        print(f"   Ray-casting for {height:,} rows × {width:,} columns = {height*width:,} pixels")
        
        for y in range(height):
            # Report progress every 1% of rows (or every row if less than 100 rows total)
            if progress_callback and (y % max(1, height // 100) == 0 or y == height - 1):
                progress = y / height if height > 0 else 1.0
                progress_callback(progress)
            
            for x in range(width):
                current_elevation = elevation_data[y, x]
                
                # Treat no-data areas as elevation 0 (sea level) for shadow calculations
                if np.isnan(current_elevation):
                    current_elevation = 0.0
                
                is_in_shadow = False
                
                # Cast ray TOWARDS light source to check if terrain blocks the light path
                max_distance = max(width, height)  # Maximum shadow distance
                
                for distance in range(1, max_distance):
                    # Calculate position to check (TOWARDS light source)
                    check_x = x - (light_dx * distance)  # Reverse direction
                    check_y = y - (light_dy * distance)  # Reverse direction
                    
                    # Convert to integer pixel coordinates
                    px = int(round(check_x))
                    py = int(round(check_y))
                    
                    # Check bounds
                    if px < 0 or px >= width or py < 0 or py >= height:
                        break  # Reached edge, can see light
                    
                    # Get elevation at check position
                    check_elevation = elevation_data[py, px]
                    
                    # Treat no-data areas as elevation 0 (sea level) for shadow calculations
                    if np.isnan(check_elevation):
                        check_elevation = 0.0
                    
                    # Calculate what elevation would block light at this distance
                    # Lower drop_distance = light ray rises more gently = longer shadows
                    light_ray_elevation = current_elevation + (distance * shadow_drop_distance)
                    
                    # If intervening terrain is higher than the light ray, it blocks light
                    if check_elevation > light_ray_elevation:
                        is_in_shadow = True
                        break
                
                shadow_map[y, x] = 1.0 if is_in_shadow else 0.0
        
        # Apply soft edge effect if enabled
        if shadow_soft_edge > 0:
            shadow_map = self._apply_soft_edge(shadow_map, light_direction, shadow_soft_edge)
        
        print(f"🌑 ShadowMethod1 complete: {np.sum(shadow_map > 0)} pixels in shadow")
        return shadow_map
    
    def _apply_soft_edge(self, shadow_map: np.ndarray, light_direction: int, soft_edge_size: int) -> np.ndarray:
        """
        Apply soft edge effect to shadows (like Photoshop motion blur in light direction).
        
        Args:
            shadow_map: 2D array with shadow values (0.0 to 1.0)
            light_direction: Direction of light in degrees
            soft_edge_size: Size of soft edge in pixels
            
        Returns:
            Shadow map with soft edges applied
        """
        try:
            from scipy import ndimage
        except ImportError:
            print("⚠️ scipy not available for ShadowMethod1 soft edges")
            return shadow_map
        
        # Calculate blur direction (opposite of light direction)
        blur_rad = math.radians(light_direction + 180)  # Opposite direction
        blur_dx = math.sin(blur_rad) * soft_edge_size
        blur_dy = -math.cos(blur_rad) * soft_edge_size
        
        # Create motion blur kernel
        kernel_size = soft_edge_size * 2 + 1
        kernel = np.zeros((kernel_size, kernel_size))
        
        # Draw line in blur direction
        center = soft_edge_size
        for i in range(soft_edge_size + 1):
            x = int(center + blur_dx * i / soft_edge_size)
            y = int(center + blur_dy * i / soft_edge_size)
            if 0 <= x < kernel_size and 0 <= y < kernel_size:
                kernel[y, x] = 1.0
        
        # Normalize kernel
        if np.sum(kernel) > 0:
            kernel = kernel / np.sum(kernel)
        
        # Apply motion blur to shadow map
        try:
            blurred_shadow_map = ndimage.convolve(shadow_map, kernel, mode='constant', cval=0.0)
            return blurred_shadow_map
        except Exception as e:
            print(f"⚠️ ShadowMethod1 soft edge failed: {e}")
            return shadow_map
    
    def get_method_info(self) -> dict:
        """
        Return information about this shadow method.
        
        Returns:
            Dictionary with method information
        """
        return {
            'name': 'ShadowMethod1',
            'algorithm': 'Ray-casting',
            'complexity': 'O(n³)',
            'soft_edge_method': 'Motion blur post-process',
            'advantages': ['360° light direction support', 'Conceptually simple'],
            'disadvantages': ['Very slow for large datasets', 'Motion blur creep on lit slopes'],
            'recommended_use': 'Small datasets or when 360° precision is required'
        }