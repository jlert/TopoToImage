#!/usr/bin/env python3
"""
Shadow Method 2: TopoToImage Height-Propagation Algorithm

This implements the original TopoToImage shadow calculation method using 
height propagation for optimal performance and visual quality.

Algorithm: Propagate maximum heights line-by-line based on light direction.
Soft edges are calculated during shadow generation, not as post-process.

Performance: O(n²) complexity - significantly faster than ray-casting
Visual Quality: Geometrically accurate soft edges confined within shadow boundaries
"""

import numpy as np
import math
from typing import Optional


class ShadowMethod2:
    """
    TopoToImage height-propagation shadow calculation method.
    
    This method uses the original TopoToImage algorithm that propagates
    shadow heights line-by-line for optimal performance and quality.
    """
    
    def __init__(self):
        """Initialize ShadowMethod2"""
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
        Calculate cast shadows using TopoToImage height-propagation algorithm.
        
        Based on the original TopoToImage BASIC algorithm that uses height propagation
        for optimal O(n²) performance and geometrically accurate soft edges.
        
        Args:
            elevation_data: 2D numpy array of elevation values
            light_direction: Light direction in degrees (snapped to nearest 45° increment)
            shadow_drop_distance: Shadow threshold - controls shadow length and softness
            shadow_soft_edge: Soft edge distance in pixels (integrated into calculation)
            cell_size: Size of each cell in elevation units (for future use)
            progress_callback: Optional callback for progress reporting
            
        Returns:
            2D numpy array with shadow values (0.0 = no shadow, 1.0 = full shadow)
        """
        height, width = elevation_data.shape
        shadow_map = np.zeros((height, width), dtype=np.float32)
        
        # Snap light direction to nearest 45° increment (8 cardinal directions)
        snapped_direction = self._snap_to_8_directions(light_direction)
        
        # Flip direction by 180° to cast shadows away from light (same as ShadowMethod1)
        shadow_direction = (snapped_direction + 180) % 360
        
        print(f"🌑 ShadowMethod2: drop_distance={shadow_drop_distance}, light_dir={light_direction}° → {snapped_direction}° → shadow_dir={shadow_direction}°")
        print(f"   Height-propagation for {height:,} rows × {width:,} columns = {height*width:,} pixels")
        
        # Get direction offsets for the shadow direction (not light direction)
        dx, dy = self._get_direction_offsets(shadow_direction)
        
        # Handle NaN values by treating them as elevation 0 (sea level)
        clean_elevation = np.copy(elevation_data)
        clean_elevation[np.isnan(clean_elevation)] = 0.0
        
        # Calculate soft edge parameters (similar to original TopoToImage)
        # Convert soft_edge parameter to intensity gradient
        if shadow_soft_edge > 0:
            shadow_gray_step = 1.0 / shadow_soft_edge  # Gradient step for soft edges
        else:
            shadow_gray_step = 1.0  # No soft edges - binary shadows
        
        # Use appropriate algorithm based on shadow direction (after 180° flip)
        if shadow_direction in [0, 180]:  # North/South (vertical)
            shadow_map = self._calculate_vertical_shadows(
                clean_elevation, shadow_direction, shadow_drop_distance, 
                shadow_gray_step, progress_callback
            )
        elif shadow_direction in [90, 270]:  # East/West (horizontal)
            shadow_map = self._calculate_horizontal_shadows(
                clean_elevation, shadow_direction, shadow_drop_distance, 
                shadow_gray_step, progress_callback
            )
        else:  # Diagonal directions (45, 135, 225, 315) - add another 180° flip
            # For diagonal directions, add an additional 180° rotation to fix direction
            diagonal_shadow_direction = (shadow_direction + 180) % 360
            print(f"   Diagonal fix: {shadow_direction}° → {diagonal_shadow_direction}° (added 180°)")
            shadow_map = self._calculate_diagonal_shadows(
                clean_elevation, diagonal_shadow_direction, shadow_drop_distance, 
                shadow_gray_step, progress_callback
            )
        
        print(f"🌑 ShadowMethod2 complete: {np.sum(shadow_map > 0)} pixels in shadow")
        return shadow_map
    
    def _snap_to_8_directions(self, angle: int) -> int:
        """
        Snap any angle to the nearest 45° increment (8 cardinal directions).
        
        Args:
            angle: Angle in degrees (0-360)
            
        Returns:
            Snapped angle: 0, 45, 90, 135, 180, 225, 270, or 315
        """
        # Normalize angle to 0-360 range
        normalized = angle % 360
        
        # Snap to nearest 45° increment
        snapped = round(normalized / 45) * 45
        
        # Handle 360° wraparound
        if snapped >= 360:
            snapped = 0
            
        return int(snapped)
    
    def _get_direction_offsets(self, direction: int) -> tuple:
        """
        Get x,y offsets for the 8 cardinal directions.
        
        Args:
            direction: Direction in degrees (0, 45, 90, 135, 180, 225, 270, 315)
            
        Returns:
            Tuple of (dx, dy) offsets
        """
        direction_map = {
            0:   (0, -1),   # North
            45:  (1, -1),   # Northeast  
            90:  (1, 0),    # East
            135: (1, 1),    # Southeast
            180: (0, 1),    # South
            225: (-1, 1),   # Southwest
            270: (-1, 0),   # West
            315: (-1, -1)   # Northwest
        }
        
        return direction_map.get(direction, (0, -1))  # Default to North
    
    def _calculate_horizontal_shadows(
        self, 
        elevation_data: np.ndarray, 
        direction: int, 
        drop_distance: float, 
        shadow_gray_step: float,
        progress_callback: Optional[callable] = None
    ) -> np.ndarray:
        """
        Calculate shadows for East/West light directions using fast row-by-row scanning.
        
        This is the optimal algorithm for horizontal light - O(n²) complexity.
        """
        height, width = elevation_data.shape
        shadow_map = np.zeros((height, width), dtype=np.float32)
        
        # Determine scanning direction (West=270° scans left-to-right, East=90° scans right-to-left)
        scan_left_to_right = (direction == 270)  # West light = shadows cast eastward
        
        for y in range(height):
            # Report progress
            if progress_callback and (y % max(1, height // 100) == 0 or y == height - 1):
                progress = y / height if height > 0 else 1.0
                progress_callback(progress)
            
            if scan_left_to_right:
                # Scan left to right (West light)
                shadow_height = elevation_data[y, 0] - drop_distance
                
                for x in range(1, width):
                    current_elev = elevation_data[y, x]
                    
                    if shadow_height > current_elev:
                        # Calculate soft edge intensity
                        shadow_diff = shadow_height - current_elev
                        shadow_intensity = min(1.0, shadow_diff * shadow_gray_step / drop_distance)
                        shadow_map[y, x] = shadow_intensity
                        # Shadow weakens with distance
                        shadow_height = max(shadow_height - drop_distance, current_elev - drop_distance)
                    else:
                        # No shadow at this pixel
                        shadow_height = current_elev - drop_distance
                        shadow_map[y, x] = 0.0
            else:
                # Scan right to left (East light)
                shadow_height = elevation_data[y, width-1] - drop_distance
                
                for x in range(width-2, -1, -1):
                    current_elev = elevation_data[y, x]
                    
                    if shadow_height > current_elev:
                        # Calculate soft edge intensity
                        shadow_diff = shadow_height - current_elev
                        shadow_intensity = min(1.0, shadow_diff * shadow_gray_step / drop_distance)
                        shadow_map[y, x] = shadow_intensity
                        # Shadow weakens with distance
                        shadow_height = max(shadow_height - drop_distance, current_elev - drop_distance)
                    else:
                        # No shadow at this pixel
                        shadow_height = current_elev - drop_distance
                        shadow_map[y, x] = 0.0
        
        return shadow_map
    
    def _calculate_vertical_shadows(
        self, 
        elevation_data: np.ndarray, 
        direction: int, 
        drop_distance: float, 
        shadow_gray_step: float,
        progress_callback: Optional[callable] = None
    ) -> np.ndarray:
        """
        Calculate shadows for North/South light directions using column-by-column scanning.
        """
        height, width = elevation_data.shape
        shadow_map = np.zeros((height, width), dtype=np.float32)
        
        # Determine scanning direction (North=0° scans top-to-bottom, South=180° scans bottom-to-top)
        scan_top_to_bottom = (direction == 0)  # North light = shadows cast southward
        
        for x in range(width):
            # Report progress
            if progress_callback and (x % max(1, width // 100) == 0 or x == width - 1):
                progress = x / width if width > 0 else 1.0
                progress_callback(progress)
            
            if scan_top_to_bottom:
                # Scan top to bottom (North light)
                shadow_height = elevation_data[0, x] - drop_distance
                
                for y in range(1, height):
                    current_elev = elevation_data[y, x]
                    
                    if shadow_height > current_elev:
                        # Calculate soft edge intensity
                        shadow_diff = shadow_height - current_elev
                        shadow_intensity = min(1.0, shadow_diff * shadow_gray_step / drop_distance)
                        shadow_map[y, x] = shadow_intensity
                        # Shadow weakens with distance
                        shadow_height = max(shadow_height - drop_distance, current_elev - drop_distance)
                    else:
                        # No shadow at this pixel
                        shadow_height = current_elev - drop_distance
                        shadow_map[y, x] = 0.0
            else:
                # Scan bottom to top (South light)
                shadow_height = elevation_data[height-1, x] - drop_distance
                
                for y in range(height-2, -1, -1):
                    current_elev = elevation_data[y, x]
                    
                    if shadow_height > current_elev:
                        # Calculate soft edge intensity
                        shadow_diff = shadow_height - current_elev
                        shadow_intensity = min(1.0, shadow_diff * shadow_gray_step / drop_distance)
                        shadow_map[y, x] = shadow_intensity
                        # Shadow weakens with distance
                        shadow_height = max(shadow_height - drop_distance, current_elev - drop_distance)
                    else:
                        # No shadow at this pixel
                        shadow_height = current_elev - drop_distance
                        shadow_map[y, x] = 0.0
        
        return shadow_map
    
    def _calculate_diagonal_shadows(
        self, 
        elevation_data: np.ndarray, 
        direction: int, 
        drop_distance: float, 
        shadow_gray_step: float,
        progress_callback: Optional[callable] = None
    ) -> np.ndarray:
        """
        Calculate shadows for diagonal light directions (45°, 135°, 225°, 315°).
        
        Uses diagonal scanning similar to horizontal/vertical methods.
        The key insight: scan diagonal lines and propagate shadows along them.
        """
        height, width = elevation_data.shape
        shadow_map = np.zeros((height, width), dtype=np.float32)
        
        print(f"   Diagonal shadow: direction={direction}°")
        
        # For diagonal directions, we need to scan along diagonal lines
        # The approach: scan each diagonal line from the light source edge towards the shadow edge
        
        if direction == 45:  # Shadow direction 45° = Northeast shadows (light was from 225° Southwest) 
            # Light comes from Southwest (225°), shadows cast Northeast (45°)
            # Scan ALL diagonal lines from southwest to northeast to cover entire image
            
            # We need to scan all diagonals that go from bottom-left to top-right
            # Start from each position on the left edge and bottom edge
            diagonals_to_scan = []
            
            # Add diagonals starting from left edge (bottom to top)
            for y in range(height):
                diagonals_to_scan.append((y, 0))
            
            # Add diagonals starting from bottom edge (left to right, skip corner)
            for x in range(1, width):
                diagonals_to_scan.append((height - 1, x))
            
            for start_idx, (start_y, start_x) in enumerate(diagonals_to_scan):
                if progress_callback and (start_idx % max(1, len(diagonals_to_scan) // 20) == 0):
                    progress = start_idx / len(diagonals_to_scan) if len(diagonals_to_scan) > 0 else 1.0
                    progress_callback(progress)
                
                # Scan along this diagonal line (toward northeast)
                shadow_height = elevation_data[start_y, start_x] - drop_distance
                y, x = start_y, start_x
                
                while y >= 0 and x < width:
                    current_elev = elevation_data[y, x]
                    
                    if shadow_height > current_elev:
                        shadow_diff = shadow_height - current_elev
                        shadow_intensity = min(1.0, shadow_diff * shadow_gray_step / drop_distance)
                        shadow_map[y, x] = shadow_intensity
                        shadow_height = max(shadow_height - drop_distance, current_elev - drop_distance)
                    else:
                        shadow_height = current_elev - drop_distance
                        shadow_map[y, x] = 0.0
                    
                    # Move to next pixel diagonally (toward northeast)
                    y -= 1
                    x += 1
                    
        elif direction == 135:  # Shadow direction 135° = Southeast shadows (light was from 315° Northwest)
            # Light comes from Northwest (315°), shadows cast Southeast (135°)
            # Scan ALL diagonal lines from northwest to southeast to cover entire image
            
            # We need to scan all diagonals that go from top-left to bottom-right
            # Start from each position on the left edge and top edge
            diagonals_to_scan = []
            
            # Add diagonals starting from left edge (top to bottom)
            for y in range(height):
                diagonals_to_scan.append((y, 0))
            
            # Add diagonals starting from top edge (left to right, skip corner)
            for x in range(1, width):
                diagonals_to_scan.append((0, x))
            
            for start_idx, (start_y, start_x) in enumerate(diagonals_to_scan):
                if progress_callback and (start_idx % max(1, len(diagonals_to_scan) // 20) == 0):
                    progress = start_idx / len(diagonals_to_scan) if len(diagonals_to_scan) > 0 else 1.0
                    progress_callback(progress)
                
                # Scan along this diagonal line (toward southeast)
                shadow_height = elevation_data[start_y, start_x] - drop_distance
                y, x = start_y, start_x
                
                while y < height and x < width:
                    current_elev = elevation_data[y, x]
                    
                    if shadow_height > current_elev:
                        shadow_diff = shadow_height - current_elev
                        shadow_intensity = min(1.0, shadow_diff * shadow_gray_step / drop_distance)
                        shadow_map[y, x] = shadow_intensity
                        shadow_height = max(shadow_height - drop_distance, current_elev - drop_distance)
                    else:
                        shadow_height = current_elev - drop_distance
                        shadow_map[y, x] = 0.0
                    
                    # Move to next pixel diagonally (toward southeast)
                    y += 1
                    x += 1
                    
        elif direction == 225:  # Shadow direction 225° = Southwest shadows (light was from 45° Northeast)
            # Light comes from Northeast (45°), shadows cast Southwest (225°)  
            # Scan ALL diagonal lines from northeast to southwest to cover entire image
            
            # We need to scan all diagonals that go from top-right to bottom-left
            # Start from each position on the right edge and top edge
            diagonals_to_scan = []
            
            # Add diagonals starting from right edge (top to bottom)
            for y in range(height):
                diagonals_to_scan.append((y, width - 1))
            
            # Add diagonals starting from top edge (right to left, skip corner)
            for x in range(width - 2, -1, -1):
                diagonals_to_scan.append((0, x))
            
            for start_idx, (start_y, start_x) in enumerate(diagonals_to_scan):
                if progress_callback and (start_idx % max(1, len(diagonals_to_scan) // 20) == 0):
                    progress = start_idx / len(diagonals_to_scan) if len(diagonals_to_scan) > 0 else 1.0
                    progress_callback(progress)
                
                # Scan along this diagonal line (toward southwest)
                shadow_height = elevation_data[start_y, start_x] - drop_distance
                y, x = start_y, start_x
                
                while y < height and x >= 0:
                    current_elev = elevation_data[y, x]
                    
                    if shadow_height > current_elev:
                        shadow_diff = shadow_height - current_elev
                        shadow_intensity = min(1.0, shadow_diff * shadow_gray_step / drop_distance)
                        shadow_map[y, x] = shadow_intensity
                        shadow_height = max(shadow_height - drop_distance, current_elev - drop_distance)
                    else:
                        shadow_height = current_elev - drop_distance
                        shadow_map[y, x] = 0.0
                    
                    # Move to next pixel diagonally (toward southwest)
                    y += 1
                    x -= 1
                    
        elif direction == 315:  # Shadow direction 315° = Northwest shadows (light was from 135° Southeast)
            # Light comes from Southeast (135°), shadows cast Northwest (315°)
            # Scan ALL diagonal lines from southeast to northwest to cover entire image
            
            # We need to scan all diagonals that go from bottom-right to top-left
            # Start from each position on the right edge and bottom edge
            diagonals_to_scan = []
            
            # Add diagonals starting from right edge (bottom to top)
            for y in range(height - 1, -1, -1):
                diagonals_to_scan.append((y, width - 1))
            
            # Add diagonals starting from bottom edge (right to left, skip corner)
            for x in range(width - 2, -1, -1):
                diagonals_to_scan.append((height - 1, x))
            
            for start_idx, (start_y, start_x) in enumerate(diagonals_to_scan):
                if progress_callback and (start_idx % max(1, len(diagonals_to_scan) // 20) == 0):
                    progress = start_idx / len(diagonals_to_scan) if len(diagonals_to_scan) > 0 else 1.0
                    progress_callback(progress)
                
                # Scan along this diagonal line (toward northwest)
                shadow_height = elevation_data[start_y, start_x] - drop_distance
                y, x = start_y, start_x
                
                while y >= 0 and x >= 0:
                    current_elev = elevation_data[y, x]
                    
                    if shadow_height > current_elev:
                        shadow_diff = shadow_height - current_elev
                        shadow_intensity = min(1.0, shadow_diff * shadow_gray_step / drop_distance)
                        shadow_map[y, x] = shadow_intensity
                        shadow_height = max(shadow_height - drop_distance, current_elev - drop_distance)
                    else:
                        shadow_height = current_elev - drop_distance
                        shadow_map[y, x] = 0.0
                    
                    # Move to next pixel diagonally (toward northwest)
                    y -= 1
                    x -= 1
        
        return shadow_map
    
    def get_method_info(self) -> dict:
        """
        Return information about this shadow method.
        
        Returns:
            Dictionary with method information
        """
        return {
            'name': 'ShadowMethod2',
            'algorithm': 'Height propagation (TopoToImage)',
            'complexity': 'O(n²)',
            'soft_edge_method': 'Integrated geometric calculation',
            'advantages': ['Very fast', 'Geometrically accurate soft edges', 'No blur creep', 'Cache-friendly memory access'],
            'disadvantages': ['Limited to 8 cardinal directions (45° increments)'],
            'recommended_use': 'Production use - superior performance and quality for most applications',
            'directions_supported': [0, 45, 90, 135, 180, 225, 270, 315],
            'status': 'Implemented - Ready for testing'
        }