#!/usr/bin/env python3
"""
Shadow Method 3: 360° Bresenham Height-Propagation Algorithm

This implements a full 360° shadow calculation method using height propagation
along Bresenham line paths for arbitrary light directions.

Algorithm: Bresenham line algorithm + height propagation (based on ShadowMethod2)
Performance: O(n²) complexity - maintains ShadowMethod2 performance with 360° support
Visual Quality: Pixel-perfect shadows for any light direction using integer-only math
"""

import numpy as np
import math
from typing import Optional, List, Tuple


class ShadowMethod3:
    """
    360° Bresenham height-propagation shadow calculation method.
    
    This method uses Bresenham line algorithm to trace exact pixel paths
    for any shadow direction, then applies height propagation along those
    paths (similar to ShadowMethod2 but for arbitrary angles).
    """
    
    def __init__(self):
        """Initialize ShadowMethod3"""
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
        Calculate cast shadows using 360° Bresenham height-propagation algorithm.
        
        This method uses Bresenham line algorithm to trace exact pixel paths
        for any shadow direction, then applies height propagation along those
        paths (similar to ShadowMethod2 but for arbitrary angles).
        
        Args:
            elevation_data: 2D numpy array of elevation values
            light_direction: Light direction in degrees (0-360°, any angle supported)
            shadow_drop_distance: Shadow threshold - controls shadow length and softness
            shadow_soft_edge: Soft edge distance in pixels (integrated into calculation)
            cell_size: Size of each cell in elevation units (for future use)
            progress_callback: Optional callback for progress reporting
            
        Returns:
            2D numpy array with shadow values (0.0 = no shadow, 1.0 = full shadow)
        """
        height, width = elevation_data.shape
        shadow_map = np.zeros((height, width), dtype=np.float32)
        
        # No snapping - use exact light direction for 360° support
        exact_direction = light_direction % 360
        
        # Use light direction directly (180° flip from the working version)
        shadow_direction = exact_direction
        
        print(f"🌑 ShadowMethod3: drop_distance={shadow_drop_distance}, light_dir={light_direction}° → shadow_dir={shadow_direction}° (Bresenham 360°)")
        print(f"   Bresenham height-propagation for {height:,} rows × {width:,} columns = {height*width:,} pixels")
        
        # Convert shadow direction to Bresenham integer direction vector
        dx, dy = self._angle_to_bresenham_vector(shadow_direction)
        
        print(f"   Bresenham vector: ({dx}, {dy}) for {shadow_direction}°")
        
        # Handle NaN values by treating them as elevation 0 (sea level)
        clean_elevation = np.copy(elevation_data)
        clean_elevation[np.isnan(clean_elevation)] = 0.0
        
        # Calculate soft edge parameters (similar to ShadowMethod2)
        if shadow_soft_edge > 0:
            shadow_gray_step = 1.0 / shadow_soft_edge  # Gradient step for soft edges
        else:
            shadow_gray_step = 1.0  # No soft edges - binary shadows
        
        # Use Bresenham height-propagation algorithm
        shadow_map = self._calculate_bresenham_shadows(
            clean_elevation, dx, dy, shadow_direction, shadow_drop_distance, 
            shadow_gray_step, progress_callback
        )
        
        print(f"🌑 ShadowMethod3 complete: {np.sum(shadow_map > 0)} pixels in shadow")
        return shadow_map
    
    def _angle_to_bresenham_vector(self, degrees: float) -> Tuple[int, int]:
        """
        Convert angle to Bresenham-compatible direction vector.
        
        Uses integer-only math to generate exact pixel stepping directions
        for any angle, suitable for Bresenham line algorithm.
        
        NOTE: This project uses geographical angles (North=0°, clockwise)
        
        Args:
            degrees: Angle in degrees (0-360) in geographical convention
            
        Returns:
            Tuple of (dx, dy) as integers for Bresenham line stepping
        """
        # Convert geographical angle to mathematical angle
        # Geographical: North=0°, clockwise
        # Mathematical: East=0°, counter-clockwise
        math_angle = (90 - degrees) % 360
        radians = math.radians(math_angle)
        
        # Get floating point direction
        float_dx = math.cos(radians)
        float_dy = -math.sin(radians)  # Negative because image Y increases downward
        
        # For Bresenham lines, we need the direction from start to end point
        # Use a fixed distance and calculate end point offset
        distance = 100  # Fixed distance for consistent step calculation
        
        # Calculate integer end point offset
        end_dx = int(round(float_dx * distance))
        end_dy = int(round(float_dy * distance))
        
        # Ensure we have non-zero movement for any angle
        if end_dx == 0 and end_dy == 0:
            # Should not happen for any valid angle, but safety check
            end_dx = 1
        
        return end_dx, end_dy
    
    def _get_edge_starting_points(self, shadow_direction: float, width: int, height: int) -> List[Tuple[int, int]]:
        """
        Determine edge starting points for Bresenham lines based on shadow direction.
        
        For shadow propagation, we start from the edges where shadows *come from*
        (the edges opposite to where shadows are cast).
        
        NOTE: This project uses geographical angles (North=0°, clockwise)
        
        Args:
            shadow_direction: Shadow casting direction in degrees (geographical)
            width: Image width in pixels
            height: Image height in pixels
            
        Returns:
            List of (x, y) coordinates along appropriate image edges
        """
        starting_points = []
        
        # Convert geographical angle to mathematical angle
        math_angle = (90 - shadow_direction) % 360
        shadow_rad = math.radians(math_angle)
        shadow_dx = math.cos(shadow_rad)
        shadow_dy = -math.sin(shadow_rad)  # Negative because image Y increases downward
        
        # Start from the edges where shadows should originate
        # For proper shadow direction, we need to start from the light source side
        
        if shadow_dx < -0.1:  # Shadows cast westward, start from EAST edge (light from east)
            for y in range(height):
                starting_points.append((width - 1, y))
        
        if shadow_dx > 0.1:  # Shadows cast eastward, start from WEST edge (light from west)
            for y in range(height):
                starting_points.append((0, y))
        
        if shadow_dy > 0.1:  # Shadows cast southward, start from NORTH edge (light from north)
            for x in range(width):
                starting_points.append((x, 0))
        
        if shadow_dy < -0.1:  # Shadows cast northward, start from SOUTH edge (light from south)
            for x in range(width):
                starting_points.append((x, height - 1))
        
        return starting_points
    
    def _bresenham_line(self, x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
        """
        Generate pixel coordinates along a line using Bresenham algorithm.
        
        This is the core Bresenham line algorithm that generates exact pixel
        paths for any direction using integer-only math.
        
        Args:
            x0, y0: Starting point coordinates
            x1, y1: Ending point coordinates
            
        Returns:
            List of (x, y) tuples representing exact pixel path
        """
        points = []
        
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        
        x_step = 1 if x0 < x1 else -1
        y_step = 1 if y0 < y1 else -1
        
        error = dx - dy
        
        x, y = x0, y0
        
        while True:
            points.append((x, y))
            
            if x == x1 and y == y1:
                break
            
            error2 = 2 * error
            
            if error2 > -dy:
                error -= dy
                x += x_step
            
            if error2 < dx:
                error += dx
                y += y_step
        
        return points
    
    def _calculate_bresenham_shadows(
        self,
        elevation_data: np.ndarray,
        dx: int, dy: int,
        shadow_direction: float,
        drop_distance: float,
        shadow_gray_step: float,
        progress_callback: Optional[callable] = None
    ) -> np.ndarray:
        """
        Calculate shadows using Bresenham line algorithm + height propagation.
        
        This is the core algorithm that combines Bresenham lines with height
        propagation to achieve O(n²) performance with 360° support.
        """
        height, width = elevation_data.shape
        shadow_map = np.zeros((height, width), dtype=np.float32)
        
        # Get starting points along appropriate edges
        starting_points = self._get_edge_starting_points(shadow_direction, width, height)
        
        print(f"   Shadow direction: {shadow_direction}°, starting from {len(starting_points)} edge points")
        
        # Calculate target points for Bresenham lines
        # We need to determine how far to extend lines in the shadow direction
        max_extent = max(width, height) * 2  # Generous extent to cover entire image
        
        if not starting_points:
            return shadow_map

        # Every line uses the same direction and length, so the Bresenham step
        # pattern is identical for all of them — only the starting point differs.
        # Compute the shared pixel-offset sequence once, then advance all lines
        # in lockstep with array operations instead of looping per line.
        end_dx = dx * max_extent // max(abs(dx), abs(dy), 1)
        end_dy = dy * max_extent // max(abs(dx), abs(dy), 1)
        offsets = self._bresenham_line(0, 0, end_dx, end_dy)

        start_x = np.array([p[0] for p in starting_points], dtype=np.int64)
        start_y = np.array([p[1] for p in starting_points], dtype=np.int64)

        # Per-line propagated shadow height (height propagation, same as ShadowMethod2)
        shadow_height = np.full(start_x.shape, -np.inf, dtype=np.float64)

        n_steps = len(offsets)
        for step_idx, (offset_x, offset_y) in enumerate(offsets):
            if progress_callback and (step_idx % max(1, n_steps // 20) == 0):
                progress_callback(step_idx / n_steps)

            x = start_x + offset_x
            y = start_y + offset_y

            # Lines currently outside the image keep their shadow height unchanged
            inside = (x >= 0) & (x < width) & (y >= 0) & (y < height)
            if not np.any(inside):
                continue

            xv = x[inside]
            yv = y[inside]
            current_elev = elevation_data[yv, xv].astype(np.float64)

            # Update shadow height - this pixel can cast shadows
            line_height = np.maximum(shadow_height[inside], current_elev - drop_distance)

            # Pixels shadowed by previously propagated heights
            in_shadow = line_height > current_elev
            shadow_diff = line_height - current_elev
            shadow_intensity = np.minimum(1.0, shadow_diff * shadow_gray_step / drop_distance)
            shadow_intensity = np.where(in_shadow, shadow_intensity, 0.0).astype(np.float32)

            # Apply shadow (take maximum to preserve stronger shadows);
            # maximum.at handles lines that overlap on the same pixel
            np.maximum.at(shadow_map, (yv, xv), shadow_intensity)

            # Shadow weakens with distance where shadowed, otherwise reset to this pixel
            line_height = np.where(
                in_shadow,
                np.maximum(line_height - drop_distance, current_elev - drop_distance),
                current_elev - drop_distance
            )
            shadow_height[inside] = line_height

        return shadow_map
    
    def get_method_info(self) -> dict:
        """
        Return information about this shadow method.
        
        Returns:
            Dictionary with method information
        """
        return {
            'name': 'ShadowMethod3',
            'algorithm': 'Bresenham line + height propagation (360° support)',
            'complexity': 'O(n²) - maintains ShadowMethod2 performance with 360° support',
            'soft_edge_method': 'Integrated geometric calculation (same as ShadowMethod2)',
            'advantages': ['Full 360° support', 'Pixel-perfect shadows for any angle', 'Integer-only math', 'No direction snapping', 'O(n²) performance'],
            'disadvantages': ['Slightly more complex than ShadowMethod2', 'Uses more memory for line generation'],
            'recommended_use': 'When precise light directions are required (e.g., sun position calculations, architectural visualization)',
            'directions_supported': 'All angles 0-360° (continuous, no snapping)',
            'status': 'Implemented - Ready for testing and performance comparison'
        }