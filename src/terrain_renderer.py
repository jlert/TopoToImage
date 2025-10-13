#!/usr/bin/env python3
"""
DEM Visualizer - Terrain Rendering Engine
Converts elevation data to colorized terrain images using gradient mapping.

This module provides the core terrain visualization functionality that made
TopoToImage valuable - taking raw elevation data and producing beautiful
colorized terrain maps.
"""

import numpy as np
from PIL import Image
from pathlib import Path
from typing import Optional, Tuple, Union, List
import time
import math

from gradient_system import GradientManager, Gradient
from dem_reader import DEMReader
from shadow_methods import ShadowMethod1, ShadowMethod2, ShadowMethod3


class TerrainRenderer:
    """
    Core terrain rendering engine that applies color gradients to elevation data.
    
    This is the heart of the terrain visualization system - it takes DEM elevation
    data and gradient definitions to produce colorized terrain images.
    """
    
    def __init__(self, gradient_manager: Optional[GradientManager] = None):
        """
        Initialize terrain renderer.
        
        Args:
            gradient_manager: Optional gradient manager instance. If None, creates new one.
        """
        self.gradient_manager = gradient_manager or GradientManager()
        self.stats = {
            'last_render_time': 0,
            'last_pixels_processed': 0,
            'total_renders': 0
        }
        
        # Shadow method selection (for development/testing)
        # Change this to switch between shadow algorithms:
        # "method1" = Current ray-casting method (slow but 360° support)
        # "method2" = TopoToImage height-propagation method (fast, 8-direction)
        # "method3" = Directional vector propagation (360° support, moderate speed)
        self.SHADOW_METHOD = "method3"
        
        # Initialize shadow method instances
        self._shadow_method_1 = ShadowMethod1()
        self._shadow_method_2 = ShadowMethod2()
        self._shadow_method_3 = ShadowMethod3()
    
    def render_gradient_layer(
        self,
        elevation_data: np.ndarray,
        gradient: Gradient,
        min_elevation: Optional[float] = None,
        max_elevation: Optional[float] = None,
        no_data_color: Optional[Tuple[int, int, int, int]] = None,
        progress_callback: Optional[callable] = None
    ) -> np.ndarray:
        """
        Create pure gradient layer (no shading or shadows).
        
        Returns:
            RGBA array (height, width, 4) with gradient colors applied to elevation data
        """
        # Use gradient's no_data_color if not explicitly provided
        if no_data_color is None:
            if hasattr(gradient, 'no_data_color') and gradient.no_data_color:
                no_data_color = (
                    gradient.no_data_color.get('red', 0),
                    gradient.no_data_color.get('green', 0), 
                    gradient.no_data_color.get('blue', 0),
                    gradient.no_data_color.get('alpha', 255)
                )
            else:
                no_data_color = (0, 0, 0, 0)  # Transparent
        
        # Override gradient elevation range if specified
        if min_elevation is not None or max_elevation is not None:
            effective_min = min_elevation if min_elevation is not None else gradient.min_elevation
            effective_max = max_elevation if max_elevation is not None else gradient.max_elevation
        else:
            effective_min = gradient.min_elevation
            effective_max = gradient.max_elevation
        
        # Create output array (height, width, 4) for RGBA
        height, width = elevation_data.shape
        rgba_array = np.zeros((height, width, 4), dtype=np.uint8)
        
        # Handle NaN values (no-data areas)
        valid_mask = ~np.isnan(elevation_data)
        valid_count = np.sum(valid_mask)
        
        # Apply gradient to valid pixels
        if valid_count > 0:
            valid_elevations = elevation_data[valid_mask]
            
            # Normalize elevations to 0-1 range
            elev_range = effective_max - effective_min
            if elev_range > 0:
                normalized = (valid_elevations - effective_min) / elev_range
                normalized = np.clip(normalized, 0.0, 1.0)
            else:
                normalized = np.zeros_like(valid_elevations)
            
            # Apply gradient to normalized values
            valid_colors = np.zeros((valid_count, 4), dtype=np.uint8)
            
            for i, norm_elev in enumerate(normalized):
                # Report progress during gradient color application
                if progress_callback and i % max(1, valid_count // 10) == 0:  # Update 10 times during processing
                    progress = min(0.9, i / valid_count)  # Cap at 90% to reserve final 10% for array assignment
                    progress_callback(progress, "Generating Base Color")
                
                # SPECIAL HANDLING FOR POSTERIZED GRADIENTS: Use actual elevation values
                # to ensure "above posterized" colors work correctly
                actual_elevation = valid_elevations[i]
                
                is_posterized = hasattr(gradient, 'gradient_type') and gradient.gradient_type in ["posterized", "shading_and_posterized"]
                has_above_color = hasattr(gradient, 'below_gradient_color') and gradient.below_gradient_color
                
                if is_posterized and has_above_color:
                    # For posterized gradients with above-gradient colors, use actual elevation
                    # This allows elevations above the gradient range to get the correct "above posterized" color
                    color = gradient.get_color_at_elevation(actual_elevation)
                else:
                    # For regular gradients, use normalized mapping to gradient range
                    gradient_elev = gradient.min_elevation + norm_elev * (gradient.max_elevation - gradient.min_elevation)
                    color = gradient.get_color_at_elevation(gradient_elev)
                
                valid_colors[i] = color
            
            # Final progress update before array assignment
            if progress_callback:
                progress_callback(0.95, "Generating Base Color")
            
            # Place colors back into full array
            rgba_array[valid_mask] = valid_colors
        
        # Set no-data areas to specified color
        rgba_array[~valid_mask] = no_data_color
        
        return rgba_array
    
    def render_shading_layer(
        self,
        elevation_data: np.ndarray,
        light_direction: int = 315,
        shading_intensity: int = 50,
        min_elevation: Optional[float] = None,
        max_elevation: Optional[float] = None,
        progress_callback: Optional[callable] = None
    ) -> np.ndarray:
        """
        Create pure hillshade layer (grayscale, 0-255).
        
        Returns:
            Grayscale array (height, width) with hillshade values 0-255
        """
        if progress_callback:
            progress_callback(0.0, "Hillshading")
            
        hillshade = self.calculate_hillshade(
            elevation_data,
            light_direction=light_direction,
            shading_intensity=shading_intensity,
            min_elevation=min_elevation,
            max_elevation=max_elevation,
            progress_callback=progress_callback
        )
        
        if progress_callback:
            progress_callback(1.0, "Hillshading")
        
        # Convert to 0-255 range
        return (hillshade * 255).astype(np.uint8)
    
    def render_shadow_layer(
        self,
        elevation_data: np.ndarray,
        light_direction: int = 315,
        shadow_drop_distance: float = 1.0,
        shadow_soft_edge: int = 3,
        progress_callback: Optional[callable] = None
    ) -> np.ndarray:
        """
        Create pure shadow layer (grayscale mask, 0-255).
        
        Returns:
            Shadow mask array (height, width) with shadow intensity 0-255
        """
        shadow_map = self.calculate_cast_shadows(
            elevation_data,
            light_direction=light_direction,
            shadow_drop_distance=shadow_drop_distance,
            shadow_soft_edge=shadow_soft_edge,
            progress_callback=progress_callback
        )
        
        # Convert to 0-255 range
        return (shadow_map * 255).astype(np.uint8)
    
    def composite_layers(
        self,
        gradient_layer: np.ndarray,
        shading_layer: Optional[np.ndarray] = None,
        shadow_layer: Optional[np.ndarray] = None,
        blending_mode: str = "Multiply",
        blending_strength: int = 100,
        gradient = None,  # Pass gradient object to access shadow_color
        progress_callback: Optional[callable] = None
    ) -> np.ndarray:
        """
        Composite gradient, shading, and shadow layers.
        
        Args:
            gradient_layer: RGBA array (height, width, 4) 
            shading_layer: Grayscale array (height, width) with values 0-255
            shadow_layer: Grayscale array (height, width) with values 0-255
            blending_mode: How to blend layers (Multiply, Overlay, etc.) - always "Hard Light" now
            blending_strength: Blending intensity 0-200% (100 = normal)
            
        Returns:
            Final RGBA array (height, width, 4)
        """
        result = gradient_layer.copy()
        height, width = result.shape[:2]
        
        # Apply shading layer if provided
        if shading_layer is not None:
            print(f"🎨 Applying Hard Light blending with {blending_strength}% strength")
            
            if progress_callback:
                progress_callback(0.1, "Compositing")
            
            # PRESERVE "ABOVE POSTERIZED" COLORS: For posterized gradients with above-gradient colors,
            # preserve those colors from shading effects to maintain visibility
            preserve_above_colors = False
            above_color_mask = None
            
            if gradient and hasattr(gradient, 'gradient_type') and hasattr(gradient, 'below_gradient_color'):
                is_posterized = gradient.gradient_type in ["posterized", "shading_and_posterized"] 
                has_above_color = gradient.below_gradient_color is not None
                
                if is_posterized and has_above_color:
                    preserve_above_colors = True
                    # Create mask for pixels that have the "above posterized" color
                    above_rgb = (
                        gradient.below_gradient_color.get('red', 0),
                        gradient.below_gradient_color.get('green', 0), 
                        gradient.below_gradient_color.get('blue', 0)
                    )
                    
                    # Find pixels that match the above posterized color (before blending)
                    above_color_mask = (
                        (result[:, :, 0] == above_rgb[0]) &
                        (result[:, :, 1] == above_rgb[1]) &
                        (result[:, :, 2] == above_rgb[2])
                    )
                    
                    above_pixel_count = np.sum(above_color_mask)
                    print(f"🎨 Preserving {above_pixel_count} 'above posterized' pixels from shading: RGB{above_rgb}")
            
            # Convert layers to 0.0-1.0 range for blending
            base = result[:, :, :3].astype(np.float32) / 255.0  # RGB only
            overlay = shading_layer.astype(np.float32) / 255.0
            
            # Debug: show shading range
            shading_min = np.min(overlay)
            shading_max = np.max(overlay)
            print(f"🔍 Shading layer range: {shading_min:.3f} to {shading_max:.3f}")
            
            # Always use Hard Light blending (most dramatic and useful)
            overlay_3d = overlay[:, :, np.newaxis]
            condition = overlay_3d < 0.5
            hard_light_result = np.where(condition,
                             2 * base * overlay_3d,
                             1 - 2 * (1 - base) * (1 - overlay_3d))
            
            # Apply blending strength: 0% = no effect, 100% = full effect, 200% = double effect
            strength_factor = blending_strength / 100.0
            
            if strength_factor == 0.0:
                # No blending, just return base
                blended = base
            elif strength_factor == 1.0:
                # Normal blending strength
                blended = hard_light_result
            else:
                # Interpolate between base and blended result based on strength
                # For values > 100%, extrapolate beyond the blended result
                blended = base + strength_factor * (hard_light_result - base)
            
            # Clamp to valid range and convert back to uint8
            blended = np.clip(blended, 0.0, 1.0)
            result[:, :, :3] = (blended * 255).astype(np.uint8)
            
            # RESTORE "ABOVE POSTERIZED" COLORS: After blending, restore the original above-gradient color
            # for those pixels to ensure they remain visible as intended
            if preserve_above_colors and above_color_mask is not None and np.any(above_color_mask):
                above_rgb = (
                    gradient.below_gradient_color.get('red', 0),
                    gradient.below_gradient_color.get('green', 0), 
                    gradient.below_gradient_color.get('blue', 0)
                )
                result[above_color_mask, 0] = above_rgb[0]  # Red
                result[above_color_mask, 1] = above_rgb[1]  # Green  
                result[above_color_mask, 2] = above_rgb[2]  # Blue
                
                restored_count = np.sum(above_color_mask)
                print(f"🎨 Restored {restored_count} 'above posterized' pixels to RGB{above_rgb}")
            
            # Debug: show result statistics
            result_min = np.min(result[:, :, :3])
            result_max = np.max(result[:, :, :3])
            print(f"🔍 Blended result range: {result_min} to {result_max}")
            
            if progress_callback:
                progress_callback(0.5, "Compositing")
        
        # Apply shadow layer if provided
        if shadow_layer is not None:
            print(f"🌑 Applying shadows with proper shadow color...")
            
            # Get shadow color from gradient (same as shaded relief method)
            if gradient and hasattr(gradient, 'shadow_color') and gradient.shadow_color:
                shadow_r = gradient.shadow_color.get('red', 0)
                shadow_g = gradient.shadow_color.get('green', 0)  
                shadow_b = gradient.shadow_color.get('blue', 0)
                print(f"🎨 Using shadow color: RGB({shadow_r}, {shadow_g}, {shadow_b})")
            else:
                shadow_r = shadow_g = shadow_b = 0  # Black shadows if no color specified
                print(f"🎨 Using default black shadows")
            
            # Convert shadow to 0.0-1.0 range for blending
            shadow_map = shadow_layer.astype(np.float32) / 255.0
            
            # Apply shadows using TopoToImage formula (same as shaded relief)
            height, width = result.shape[:2]
            total_pixels = height * width
            processed_pixels = 0
            
            for y in range(height):
                # Report progress during shadow compositing
                if progress_callback and y % max(1, height // 10) == 0:  # Update 10 times during processing
                    progress = 0.5 + (processed_pixels / total_pixels) * 0.4  # Start at 50%, end at 90%
                    progress_callback(progress, "Compositing")
                
                for x in range(width):
                    processed_pixels += 1
                    shadow_intensity = shadow_map[y, x]
                    if shadow_intensity > 0:  # Only apply where there are shadows
                        # Calculate shadow scaling factors (TopoToImage formula)
                        r_scale = ((1 - shadow_intensity) * (1 - shadow_r / 255.0)) + (shadow_r / 255.0)
                        g_scale = ((1 - shadow_intensity) * (1 - shadow_g / 255.0)) + (shadow_g / 255.0)
                        b_scale = ((1 - shadow_intensity) * (1 - shadow_b / 255.0)) + (shadow_b / 255.0)
                        
                        # Apply shadow to RGB channels
                        result[y, x, 0] = int(result[y, x, 0] * r_scale)
                        result[y, x, 1] = int(result[y, x, 1] * g_scale)
                        result[y, x, 2] = int(result[y, x, 2] * b_scale)
        
        # Final progress update
        if progress_callback:
            progress_callback(0.95, "Compositing")
        
        return result
    
    def render_terrain(
        self, 
        elevation_data: np.ndarray, 
        gradient_name: str,
        min_elevation: Optional[float] = None,
        max_elevation: Optional[float] = None,
        no_data_color: Optional[Tuple[int, int, int, int]] = None,
        progress_callback: Optional[callable] = None
    ) -> Optional[Image.Image]:
        """
        Convert elevation data to colorized terrain image using layered approach.
        
        Args:
            elevation_data: 2D numpy array of elevation values (may contain NaN for no-data)
            gradient_name: Name of gradient to apply
            min_elevation: Override minimum elevation for gradient scaling (optional)
            max_elevation: Override maximum elevation for gradient scaling (optional)
            no_data_color: RGBA color for no-data areas (default: transparent)
            progress_callback: Function to call with progress percentage (0.0-1.0) (optional)
            
        Returns:
            PIL Image with colorized terrain, or None if gradient not found
        """
        start_time = time.time()
        
        # Get gradient
        gradient = self.gradient_manager.get_gradient(gradient_name)
        if not gradient:
            print(f"Error: Gradient '{gradient_name}' not found")
            return None
        
        # Handle shaded relief gradient type
        if gradient.gradient_type == "shaded_relief":
            print(f"🏔️ Rendering shaded relief with light direction {gradient.light_direction}° and intensity {gradient.shading_intensity}%")
            return self.render_shaded_relief(
                elevation_data,
                gradient,
                min_elevation=min_elevation,
                max_elevation=max_elevation,
                no_data_color=no_data_color,
                progress_callback=progress_callback
            )
        
        height, width = elevation_data.shape
        valid_mask = ~np.isnan(elevation_data)
        valid_count = np.sum(valid_mask)
        
        print(f"🏔️ Rendering {width}×{height} terrain using layered approach")
        print(f"   Valid pixels: {valid_count:,}")
        print(f"   Gradient: {gradient.name} ({len(gradient.color_stops)} color stops)")
        print(f"   Type: {getattr(gradient, 'gradient_type', 'gradient')}")
        
        # Layer 1: Create base color layer (gradient or posterized)
        if gradient.gradient_type == 'shading_and_posterized':
            print(f"🎨 Layer 1: Creating posterized layer...")
        else:
            print(f"🎨 Layer 1: Creating gradient layer...")
        
        if progress_callback:
            progress_callback(0.0, "Generating Base Color")
        
        gradient_layer = self.render_gradient_layer(
            elevation_data,
            gradient,
            min_elevation=min_elevation,
            max_elevation=max_elevation,
            no_data_color=no_data_color,
            progress_callback=progress_callback
        )
        
        if progress_callback:
            progress_callback(1.0, "Generating Base Color")  # Base layer complete
        
        # Layer 2: Create shading layer if needed
        shading_layer = None
        if (hasattr(gradient, 'gradient_type') and 
            gradient.gradient_type in ['shading_and_gradient', 'shading_and_posterized']):
            print(f"🌄 Layer 2: Creating hillshade layer (light: {gradient.light_direction}°, intensity: {gradient.shading_intensity}%)...")
            
            if progress_callback:
                progress_callback(0.0, "Hillshading")
                
            shading_layer = self.render_shading_layer(
                elevation_data,
                light_direction=gradient.light_direction,
                shading_intensity=gradient.shading_intensity,
                min_elevation=min_elevation,
                max_elevation=max_elevation,
                progress_callback=progress_callback
            )
            
            if progress_callback:
                progress_callback(1.0, "Hillshading")
        else:
            print(f"🌄 Layer 2: No hillshading needed for {gradient.gradient_type}")
            if progress_callback:
                progress_callback(1.0, "Hillshading")
        
        # Layer 3: Create shadow layer if enabled
        shadow_layer = None
        if (hasattr(gradient, 'cast_shadows') and gradient.cast_shadows and 
            hasattr(gradient, 'gradient_type') and 
            gradient.gradient_type in ['shading_and_gradient', 'shading_and_posterized']):
            print(f"🌑 Layer 3: Creating shadow layer (drop distance: {gradient.shadow_drop_distance})...")
            print(f"   ⚠️  Shadow calculation can be very slow for large areas!")
            
            if progress_callback:
                progress_callback(0.0, "Shadow Calculation")
                
            shadow_layer = self.render_shadow_layer(
                elevation_data,
                light_direction=gradient.light_direction,
                shadow_drop_distance=gradient.shadow_drop_distance,
                shadow_soft_edge=getattr(gradient, 'shadow_soft_edge', 3),
                progress_callback=progress_callback
            )
            
            if progress_callback:
                progress_callback(1.0, "Shadow Calculation")
        else:
            print(f"🌑 Layer 3: No shadows needed")
            if progress_callback:
                progress_callback(1.0, "Shadow Calculation")
        
        # Layer 4: Composite all layers
        print(f"🎭 Layer 4: Compositing layers...")
        
        if progress_callback:
            progress_callback(0.0, "Compositing")
            
        final_rgba = self.composite_layers(
            gradient_layer,
            shading_layer=shading_layer,
            shadow_layer=shadow_layer,
            blending_mode='Hard Light',  # Always use Hard Light
            blending_strength=getattr(gradient, 'blending_strength', 100),
            gradient=gradient,  # Pass gradient for shadow color access
            progress_callback=progress_callback
        )
        
        if progress_callback:
            progress_callback(0.5, "Compositing")
        
        # Convert to PIL Image
        image = Image.fromarray(final_rgba, 'RGBA')
        
        if progress_callback:
            progress_callback(1.0, "Compositing")  # 100% - complete
        
        # Update statistics
        render_time = time.time() - start_time
        self.stats['last_render_time'] = render_time
        self.stats['last_pixels_processed'] = height * width
        self.stats['total_renders'] += 1
        
        pixels_per_second = (height * width) / render_time if render_time > 0 else 0
        print(f"✓ Terrain rendered in {render_time:.3f}s ({pixels_per_second:,.0f} pixels/sec)")
        
        return image
    
    def render_terrain_layers(
        self,
        elevation_data: np.ndarray,
        gradient_name: str,
        min_elevation: Optional[float] = None,
        max_elevation: Optional[float] = None,
        no_data_color: Optional[Tuple[int, int, int, int]] = None
    ) -> dict:
        """
        Render terrain and return all individual layers for advanced export (e.g., Photoshop).
        
        Args:
            elevation_data: 2D numpy array of elevation values
            gradient_name: Name of gradient to apply
            min_elevation: Override minimum elevation for gradient scaling
            max_elevation: Override maximum elevation for gradient scaling
            no_data_color: RGBA color for no-data areas
            
        Returns:
            Dictionary containing:
            - 'elevation': RGBA array (height, width, 4) - normalized grayscale elevation (black=min, white=max)
            - 'gradient': RGBA array (height, width, 4) - pure gradient colors
            - 'shading': Grayscale array (height, width) - hillshade 0-255 (if applicable)
            - 'shadows': Grayscale array (height, width) - shadow mask 0-255 (if applicable) 
            - 'composite': RGBA array (height, width, 4) - final composited result
            - 'gradient_obj': The Gradient object used for rendering
        """
        # Get gradient
        gradient = self.gradient_manager.get_gradient(gradient_name)
        if not gradient:
            raise ValueError(f"Gradient '{gradient_name}' not found")
        
        layers = {'gradient_obj': gradient}
        
        # Layer 0: Normalized elevation layer (grayscale base)
        layers['elevation'] = self.render_normalized_elevation_layer(
            elevation_data,
            min_elevation=min_elevation,
            max_elevation=max_elevation,
            no_data_color=no_data_color
        )
        
        # Layer 1: Gradient layer (always created)
        layers['gradient'] = self.render_gradient_layer(
            elevation_data,
            gradient,
            min_elevation=min_elevation,
            max_elevation=max_elevation,
            no_data_color=no_data_color
        )
        
        # Layer 2: Shading layer (if gradient type supports it)
        layers['shading'] = None
        if (hasattr(gradient, 'gradient_type') and 
            gradient.gradient_type in ['shaded_relief', 'shading_and_gradient', 'shading_and_posterized']):
            layers['shading'] = self.render_shading_layer(
                elevation_data,
                light_direction=gradient.light_direction,
                shading_intensity=gradient.shading_intensity
            )
        
        # Layer 3: Shadow layer (if enabled)
        layers['shadows'] = None
        if (hasattr(gradient, 'cast_shadows') and gradient.cast_shadows):
            layers['shadows'] = self.render_shadow_layer(
                elevation_data,
                light_direction=gradient.light_direction,
                shadow_drop_distance=gradient.shadow_drop_distance,
                shadow_soft_edge=getattr(gradient, 'shadow_soft_edge', 3)
            )
        
        # Layer 4: Composite result
        layers['composite'] = self.composite_layers(
            layers['gradient'],
            shading_layer=layers['shading'],
            shadow_layer=layers['shadows'],
            blending_mode='Hard Light',  # Always use Hard Light
            blending_strength=getattr(gradient, 'blending_strength', 100),
            gradient=gradient  # Pass gradient for shadow color access
        )
        
        return layers
    
    def render_dem_file(
        self,
        dem_path: Union[str, Path],
        gradient_name: str,
        output_path: Optional[Union[str, Path]] = None,
        subsample: Optional[int] = None,
        min_elevation: Optional[float] = None,
        max_elevation: Optional[float] = None
    ) -> Optional[Path]:
        """
        Render terrain directly from DEM file.
        
        Args:
            dem_path: Path to DEM file or directory
            gradient_name: Name of gradient to apply
            output_path: Where to save result (optional, auto-generated if None)
            subsample: Subsample factor for faster processing (optional)
            min_elevation: Override minimum elevation (optional)
            max_elevation: Override maximum elevation (optional)
            
        Returns:
            Path to saved image file, or None if failed
        """
        try:
            # Load DEM data
            dem_reader = DEMReader(dem_path)
            elevation_data = dem_reader.load_elevation_data(subsample=subsample)
            
            # Auto-detect elevation range if not specified
            if min_elevation is None or max_elevation is None:
                valid_data = elevation_data[~np.isnan(elevation_data)]
                if len(valid_data) > 0:
                    auto_min = float(np.min(valid_data))
                    auto_max = float(np.max(valid_data))
                    
                    if min_elevation is None:
                        min_elevation = auto_min
                    if max_elevation is None:
                        max_elevation = auto_max
                    
                    print(f"Auto-detected elevation range: {auto_min:.0f}m to {auto_max:.0f}m")
            
            # Render terrain
            terrain_image = self.render_terrain(
                elevation_data, 
                gradient_name,
                min_elevation=min_elevation,
                max_elevation=max_elevation
            )
            
            if not terrain_image:
                return None
            
            # Generate output path if not provided
            if output_path is None:
                dem_path = Path(dem_path)
                if dem_path.is_dir():
                    base_name = dem_path.name
                else:
                    base_name = dem_path.stem
                
                suffix = f"_subsample{subsample}" if subsample else ""
                output_path = Path(f"{base_name}_{gradient_name.replace(' ', '_')}{suffix}_terrain.png")
            else:
                output_path = Path(output_path)
            
            # Save image
            terrain_image.save(output_path)
            print(f"✓ Terrain image saved: {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"Error rendering DEM file {dem_path}: {e}")
            return None
    
    def render_selection(
        self,
        dem_reader: DEMReader,
        bounds: List[float],
        gradient_name: str,
        max_pixels: int = 1000000,
        min_elevation: Optional[float] = None,
        max_elevation: Optional[float] = None
    ) -> Optional[Image.Image]:
        """
        Render terrain for a selected geographic area.
        
        Args:
            dem_reader: DEM reader instance with loaded data
            bounds: Geographic bounds [west, north, east, south] in degrees
            gradient_name: Name of gradient to apply
            max_pixels: Maximum pixels to render (for performance)
            min_elevation: Override minimum elevation (optional)
            max_elevation: Override maximum elevation (optional)
            
        Returns:
            PIL Image with rendered terrain, or None if failed
        """
        try:
            # TODO: Implement geographic cropping and multi-tile stitching
            # For now, render the entire loaded DEM
            
            if dem_reader.elevation_data is None:
                # Load data with appropriate subsampling
                total_pixels = dem_reader.width * dem_reader.height
                subsample = max(1, int(np.sqrt(total_pixels / max_pixels)))
                
                print(f"Loading elevation data (subsample factor: {subsample})")
                elevation_data = dem_reader.load_elevation_data(subsample=subsample)
            else:
                elevation_data = dem_reader.elevation_data
            
            # Render terrain
            return self.render_terrain(
                elevation_data,
                gradient_name,
                min_elevation=min_elevation,
                max_elevation=max_elevation
            )
            
        except Exception as e:
            print(f"Error rendering selection: {e}")
            return None
    
    def calculate_hillshade(
        self,
        elevation_data: np.ndarray,
        light_direction: int = 315,
        shading_intensity: int = 50,
        min_elevation: Optional[float] = None,
        max_elevation: Optional[float] = None,
        cell_size: float = 1.0,
        progress_callback: Optional[callable] = None
    ) -> np.ndarray:
        """
        Calculate hillshade relief using TopoToImage's elevation difference algorithm with full 360° light direction.
        Enhanced from original TopoToImage to support any light angle with bilinear interpolation.
        
        Args:
            elevation_data: 2D numpy array of elevation values
            light_direction: Light direction in degrees (0-360: 0=North, 90=East, 180=South, 270=West)
            shading_intensity: Shading intensity percentage (0-100)
            cell_size: Size of each cell (unused in TopoToImage algorithm)
            
        Returns:
            2D numpy array with hillshade values (0.0 to 1.0)
        """
        height, width = elevation_data.shape
        hillshade = np.full((height, width), 0.5, dtype=np.float32)  # Start with neutral gray (0.5)
        
        # Pre-calculate terrain relief for consistent scaling
        # Use specified elevation range if provided, otherwise auto-detect from data
        if min_elevation is not None and max_elevation is not None:
            terrain_relief = max(50.0, max_elevation - min_elevation)
            print(f"🏔️ Hillshade: using specified elevation range {min_elevation:.1f}-{max_elevation:.1f}m")
        else:
            valid_elevations = elevation_data[~np.isnan(elevation_data)]
            if len(valid_elevations) > 0:
                terrain_relief = max(50.0, np.max(valid_elevations) - np.min(valid_elevations))
                print(f"🏔️ Hillshade: auto-detected terrain range from data")
            else:
                terrain_relief = 100.0  # Default fallback
                print(f"🏔️ Hillshade: using default terrain relief (no valid data)")
        
        print(f"🏔️ Hillshade: terrain relief = {terrain_relief:.1f}, intensity = {shading_intensity}%")
        
        # Calculate continuous light direction offsets for full 360° support
        # Convert light direction to radians and calculate unit vector
        light_rad = math.radians(light_direction)
        
        # Calculate direction vector for sampling (OPPOSITE of light direction)
        # We want to sample the slope that the light hits, not the direction light goes
        dx = -math.sin(light_rad)  # Opposite East-West component
        dy = math.cos(light_rad)   # Opposite North-South component
        
        # Normalize to create reasonable offset distances
        # Use a sampling distance that captures local terrain variation
        sample_distance = 1.0  # Start with 1-pixel sampling
        
        x_offset = dx * sample_distance
        y_offset = dy * sample_distance
        
        # Apply TopoToImage's simple elevation difference algorithm with bilinear interpolation
        total_pixels = height * width
        processed_pixels = 0
        
        for y in range(height):
            # Report progress during hillshade calculation
            if progress_callback and y % max(1, height // 10) == 0:  # Update 10 times during processing
                progress = min(0.9, processed_pixels / total_pixels)  # Cap at 90%
                progress_callback(progress, "Hillshading")
            
            for x in range(width):
                processed_pixels += 1
                # Get current pixel elevation
                current_elev = elevation_data[y, x]
                
                # Skip if current pixel has no data
                if np.isnan(current_elev):
                    continue
                
                # Calculate neighbor position with floating-point precision
                neighbor_x = x + x_offset
                neighbor_y = y + y_offset
                
                # Check if neighbor position is within bounds
                if (neighbor_x < 0 or neighbor_x >= width - 1 or 
                    neighbor_y < 0 or neighbor_y >= height - 1):
                    continue
                
                # Bilinear interpolation to get neighbor elevation at fractional coordinates
                x0, x1 = int(neighbor_x), int(neighbor_x) + 1
                y0, y1 = int(neighbor_y), int(neighbor_y) + 1
                
                # Get the four surrounding pixels
                q00 = elevation_data[y0, x0]  # Top-left
                q01 = elevation_data[y1, x0]  # Bottom-left  
                q10 = elevation_data[y0, x1]  # Top-right
                q11 = elevation_data[y1, x1]  # Bottom-right
                
                # Skip if any surrounding pixel has no data
                if np.isnan(q00) or np.isnan(q01) or np.isnan(q10) or np.isnan(q11):
                    continue
                
                # Calculate interpolation weights
                wx = neighbor_x - x0
                wy = neighbor_y - y0
                
                # Bilinear interpolation
                neighbor_elev = (q00 * (1 - wx) * (1 - wy) + 
                               q10 * wx * (1 - wy) + 
                               q01 * (1 - wx) * wy + 
                               q11 * wx * wy)
                
                # Calculate simple elevation difference (TopoToImage: j-k)
                # Fixed to match shadow direction: current - neighbor
                # When current is higher than neighbor (slope facing away from light) → positive → darker
                # When current is lower than neighbor (slope facing towards light) → negative → lighter
                elev_diff = current_elev - neighbor_elev
                
                # Apply intensity scaling (TopoToImage: col*pcent%>>8)
                # Convert intensity from 0-100 to equivalent of TopoToImage's scaling
                intensity_factor = shading_intensity / 100.0
                
                # Scale elevation difference to produce visible shading range
                # Target range: ±0.4 around 0.5 baseline for strong contrast (wider than before)
                shaded_value_normalized = (elev_diff / terrain_relief) * intensity_factor * 1.2  # 1.2 = enhanced contrast range
                
                # Apply to hillshade (add to neutral 0.5)
                hillshade[y, x] = 0.5 + shaded_value_normalized
        
        # Clamp values to valid 0-1 range (TopoToImage: clipCol2)
        hillshade = np.clip(hillshade, 0.0, 1.0)
        
        # Final progress update
        if progress_callback:
            progress_callback(0.95, "Hillshading")
        
        return hillshade

    def calculate_cast_shadows(
        self,
        elevation_data: np.ndarray,
        light_direction: int = 315,
        shadow_drop_distance: float = 1.0,
        shadow_soft_edge: int = 3,
        cell_size: float = 1.0,
        progress_callback: Optional[callable] = None
    ) -> np.ndarray:
        """
        Calculate cast shadows using the selected shadow method.
        
        Args:
            elevation_data: 2D numpy array of elevation values
            light_direction: Light direction in degrees (0-360)
            shadow_drop_distance: Shadow threshold - LOWER values = LONGER shadows (0.1-10.0)
            shadow_soft_edge: Size of soft edge effect
            cell_size: Size of each cell in elevation units
            progress_callback: Optional callback for progress reporting
            
        Returns:
            2D numpy array with shadow values (0.0 = no shadow, 1.0 = full shadow)
        """
        # Use the selected shadow method
        if self.SHADOW_METHOD == "method1":
            return self._shadow_method_1.calculate_shadows(
                elevation_data=elevation_data,
                light_direction=light_direction,
                shadow_drop_distance=shadow_drop_distance,
                shadow_soft_edge=shadow_soft_edge,
                cell_size=cell_size,
                progress_callback=progress_callback
            )
        elif self.SHADOW_METHOD == "method2":
            return self._shadow_method_2.calculate_shadows(
                elevation_data=elevation_data,
                light_direction=light_direction,
                shadow_drop_distance=shadow_drop_distance,
                shadow_soft_edge=shadow_soft_edge,
                cell_size=cell_size,
                progress_callback=progress_callback
            )
        elif self.SHADOW_METHOD == "method3":
            return self._shadow_method_3.calculate_shadows(
                elevation_data=elevation_data,
                light_direction=light_direction,
                shadow_drop_distance=shadow_drop_distance,
                shadow_soft_edge=shadow_soft_edge,
                cell_size=cell_size,
                progress_callback=progress_callback
            )
        else:
            # Fallback to method1 if invalid method specified
            print(f"⚠️ Invalid shadow method '{self.SHADOW_METHOD}', falling back to method1")
            return self._shadow_method_1.calculate_shadows(
                elevation_data=elevation_data,
                light_direction=light_direction,
                shadow_drop_distance=shadow_drop_distance,
                shadow_soft_edge=shadow_soft_edge,
                cell_size=cell_size,
                progress_callback=progress_callback
            )
    
    def get_shadow_method_info(self) -> dict:
        """
        Get information about the currently active shadow method.
        
        Returns:
            Dictionary with information about the active shadow method
        """
        if self.SHADOW_METHOD == "method1":
            return self._shadow_method_1.get_method_info()
        elif self.SHADOW_METHOD == "method2":
            return self._shadow_method_2.get_method_info()
        elif self.SHADOW_METHOD == "method3":
            return self._shadow_method_3.get_method_info()
        else:
            return {"error": f"Unknown shadow method: {self.SHADOW_METHOD}"}

    def render_shaded_relief(
        self,
        elevation_data: np.ndarray,
        gradient: Gradient,
        min_elevation: Optional[float] = None,
        max_elevation: Optional[float] = None,
        no_data_color: Optional[Tuple[int, int, int, int]] = None,
        progress_callback: Optional[callable] = None
    ) -> Optional[Image.Image]:
        """
        Render terrain with hillshade relief using gradient settings.
        
        Args:
            elevation_data: 2D numpy array of elevation values
            gradient: Gradient object with shading parameters
            min_elevation: Override minimum elevation for gradient scaling
            max_elevation: Override maximum elevation for gradient scaling
            no_data_color: RGBA color for no-data areas
            progress_callback: Function to call with progress percentage (0.0-1.0) (optional)
            
        Returns:
            PIL Image with hillshaded terrain
        """
        # Calculate hillshade
        hillshade = self.calculate_hillshade(
            elevation_data,
            light_direction=gradient.light_direction,
            shading_intensity=gradient.shading_intensity
        )
        if progress_callback:
            progress_callback(0.4)  # 40% - hillshade complete
        
        # Calculate cast shadows if enabled
        shadow_map = None
        if hasattr(gradient, 'cast_shadows') and gradient.cast_shadows:
            print(f"🌑 Calculating cast shadows with drop distance {gradient.shadow_drop_distance}")
            shadow_map = self.calculate_cast_shadows(
                elevation_data,
                light_direction=gradient.light_direction,
                shadow_drop_distance=gradient.shadow_drop_distance,
                shadow_soft_edge=getattr(gradient, 'shadow_soft_edge', 3)
            )
        if progress_callback:
            progress_callback(0.7)  # 70% - shadows complete
        
        # Note: Cast shadows will be applied to final RGBA array later, 
        # after no-data areas are properly set
        
        # Convert hillshade to grayscale image (0-255)
        hillshade_gray = (hillshade * 255).astype(np.uint8)
        
        # Create RGBA array for the hillshade
        height, width = elevation_data.shape
        rgba_array = np.zeros((height, width, 4), dtype=np.uint8)
        
        # Set grayscale values to RGB channels
        rgba_array[:, :, 0] = hillshade_gray  # Red
        rgba_array[:, :, 1] = hillshade_gray  # Green
        rgba_array[:, :, 2] = hillshade_gray  # Blue
        rgba_array[:, :, 3] = 255             # Alpha (fully opaque)
        
        # Handle no-data areas
        valid_mask = ~np.isnan(elevation_data)
        
        # For shaded relief, use middle gray for no-data areas
        no_data_gray = (128, 128, 128, 255)  # Middle gray, fully opaque
        
        # Set no-data areas to middle gray
        rgba_array[~valid_mask] = no_data_gray
        
        # Apply shadows to RGBA array AFTER setting no-data areas
        # This ensures shadows are visible on both land AND ocean areas
        if shadow_map is not None:
            # Get shadow color (default to black for shaded relief)
            if hasattr(gradient, 'shadow_color') and gradient.shadow_color:
                shadow_r = gradient.shadow_color.get('red', 0)
                shadow_g = gradient.shadow_color.get('green', 0)  
                shadow_b = gradient.shadow_color.get('blue', 0)
            else:
                shadow_r = shadow_g = shadow_b = 0  # Black shadows
            
            # Apply shadows to ALL pixels (including no-data) where shadows are cast
            for y in range(height):
                for x in range(width):
                    if shadow_map[y, x] > 0:  # Apply shadows to ALL pixels, including no-data
                        shadow_intensity = shadow_map[y, x]
                        
                        # Calculate shadow scaling factors (TopoToImage formula)
                        r_scale = ((1 - shadow_intensity) * (1 - shadow_r / 255.0)) + (shadow_r / 255.0)
                        g_scale = ((1 - shadow_intensity) * (1 - shadow_g / 255.0)) + (shadow_g / 255.0)
                        b_scale = ((1 - shadow_intensity) * (1 - shadow_b / 255.0)) + (shadow_b / 255.0)
                        
                        # Apply shadow to RGB channels
                        rgba_array[y, x, 0] = int(rgba_array[y, x, 0] * r_scale)
                        rgba_array[y, x, 1] = int(rgba_array[y, x, 1] * g_scale)
                        rgba_array[y, x, 2] = int(rgba_array[y, x, 2] * b_scale)
        
        # Convert to PIL Image
        image = Image.fromarray(rgba_array, 'RGBA')
        
        if progress_callback:
            progress_callback(1.0)  # 100% - complete
        
        return image

    def get_available_gradients(self) -> List[str]:
        """Get list of available gradient names."""
        return self.gradient_manager.get_gradient_names()
    
    def get_rendering_stats(self) -> dict:
        """Get rendering performance statistics."""
        return self.stats.copy()
    
    def _crop_elevation_data_to_bounds(
        self,
        elevation_data: np.ndarray,
        dem_bounds: Tuple[float, float, float, float],
        sel_west: float,
        sel_north: float,
        sel_east: float,
        sel_south: float
    ) -> np.ndarray:
        """
        Crop elevation data to selection bounds
        
        Args:
            elevation_data: Full elevation data array
            dem_bounds: DEM geographic bounds (west, north, east, south)
            sel_west, sel_north, sel_east, sel_south: Selection bounds
            
        Returns:
            Cropped elevation data
        """
        dem_west, dem_north, dem_east, dem_south = dem_bounds
        height, width = elevation_data.shape
        
        print(f"🗺️ DEM bounds: W={dem_west}, N={dem_north}, E={dem_east}, S={dem_south}")
        print(f"🔲 Selection bounds: W={sel_west}, N={sel_north}, E={sel_east}, S={sel_south}")
        print(f"📐 Full data dimensions: {height} x {width}")
        
        # Convert geographic bounds to pixel coordinates
        x_min = int((sel_west - dem_west) / (dem_east - dem_west) * width)
        x_max = int((sel_east - dem_west) / (dem_east - dem_west) * width)
        y_min = int((dem_north - sel_north) / (dem_north - dem_south) * height)
        y_max = int((dem_north - sel_south) / (dem_north - dem_south) * height)
        
        print(f"🧮 Raw crop coords: x={x_min}-{x_max}, y={y_min}-{y_max}")
        
        # Clamp to valid ranges
        x_min = max(0, min(x_min, width - 1))
        x_max = max(x_min + 1, min(x_max, width))
        y_min = max(0, min(y_min, height - 1))
        y_max = max(y_min + 1, min(y_max, height))
        
        print(f"✂️ Clamped coords: x={x_min}-{x_max}, y={y_min}-{y_max}")
        
        if x_max <= x_min or y_max <= y_min:
            raise ValueError(f"Invalid selection bounds - results in zero or negative crop size: x={x_min}-{x_max}, y={y_min}-{y_max}")
        
        cropped_data = elevation_data[y_min:y_max, x_min:x_max]
        print(f"🔪 Cropped elevation data from {elevation_data.shape} to {cropped_data.shape}")
        
        return cropped_data
    
    def export_terrain(
        self,
        west: float,
        north: float, 
        east: float,
        south: float,
        file_path: str,
        gradient_name: str,
        database_info: dict = None,
        dem_reader = None,
        export_scale: float = 1.0,
        min_elevation: Optional[float] = None,
        max_elevation: Optional[float] = None,
        dpi: Optional[float] = None,
        progress_callback: Optional[callable] = None
    ) -> bool:
        """
        Export terrain to image file (JPEG, PNG, etc.)
        
        Args:
            west, north, east, south: Geographic bounds for export
            file_path: Output file path (determines format by extension)
            gradient_name: Name of gradient to apply
            database_info: Database information (for multi-file databases)
            dem_reader: DEM reader instance (for single-file databases) 
            export_scale: Scale factor (1.0 = 100%, 0.5 = 50%, etc.)
            min_elevation: Override minimum elevation for gradient scaling
            max_elevation: Override maximum elevation for gradient scaling
            dpi: Dots per inch for exported image (default: 72)
            progress_callback: Optional progress callback function
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            print(f"🌍 Exporting terrain to: {file_path}")
            print(f"   Bounds: ({west:.2f}°, {north:.2f}°) to ({east:.2f}°, {south:.2f}°)")
            print(f"   Gradient: {gradient_name}")
            print(f"   Scale: {export_scale * 100:.1f}%")
            if dpi:
                print(f"   DPI: {dpi:.1f}")
            
            # Determine if we're working with multi-file database
            is_multi_file = (database_info and database_info.get('type') == 'multi_file')
            
            # Get elevation data
            elevation_data = None
            
            if is_multi_file:
                print(f"📂 Loading from multi-file database...")
                # Use multi-file database assembly
                from multi_file_database import MultiFileDatabase
                from pathlib import Path
                
                database_path = Path(database_info.get('path', ''))
                if not database_path.exists():
                    print(f"❌ Database path not found: {database_path}")
                    return False
                
                database = MultiFileDatabase(database_path)
                elevation_data = database.assemble_tiles_for_bounds(west, north, east, south)
                
                if elevation_data is None:
                    print(f"❌ Failed to assemble elevation data from multi-file database")
                    return False
                    
            else:
                print(f"📄 Loading from single-file database...")
                # Use single-file database loading
                if not dem_reader:
                    print(f"❌ No DEM reader provided for single-file export")
                    return False
                
                # Load elevation data from single file (same as preview system)
                elevation_data = dem_reader.load_elevation_data()
                if elevation_data is None:
                    print(f"❌ Failed to load elevation data from single file")
                    return False
                
                # Crop to selection bounds if needed
                try:
                    geographic_bounds = dem_reader.get_geographic_bounds()
                    if geographic_bounds:
                        elevation_data = self._crop_elevation_data_to_bounds(
                            elevation_data, geographic_bounds, west, north, east, south)
                        print(f"✅ Cropped elevation data to selection bounds")
                except Exception as e:
                    print(f"⚠️ Could not crop elevation data: {e}")
                    # Continue with full elevation data
            
            if elevation_data is None or elevation_data.size == 0:
                print(f"❌ No elevation data available for export")
                return False
            
            print(f"✅ Loaded elevation data: {elevation_data.shape}")
            
            # Apply export scale if not 100%
            if export_scale != 1.0 and export_scale > 0:
                original_shape = elevation_data.shape
                new_height = int(original_shape[0] * export_scale)
                new_width = int(original_shape[1] * export_scale)
                
                if new_height > 0 and new_width > 0:
                    print(f"🔄 Scaling from {original_shape} to ({new_height}, {new_width})")
                    
                    # Use NaN-aware interpolation for scaling
                    try:
                        from nan_aware_interpolation import resize_with_nan_exclusion
                        elevation_data = resize_with_nan_exclusion(
                            elevation_data, (new_height, new_width), method='lanczos')
                    except ImportError:
                        # Fallback to simple PIL scaling
                        from PIL import Image
                        temp_image = Image.fromarray(elevation_data.astype(np.float32), mode='F')
                        scaled_image = temp_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        elevation_data = np.array(scaled_image, dtype=np.float32)
            
            if progress_callback:
                progress_callback(0.3, "Rendering terrain")

            # MEMORY SAFETY CHECK (FIX BUG #2 - CORRECTED)
            # Check if rendering can complete given available memory
            print(f"🔍 Checking memory safety for rendering {elevation_data.shape[1]}×{elevation_data.shape[0]} image...")
            memory_check = self._check_rendering_memory_safety(elevation_data, gradient_name)

            if not memory_check['safe']:
                print(f"❌ Export aborted: {memory_check['error']}")
                if memory_check.get('suggestion'):
                    print(f"💡 Suggestion: {memory_check['suggestion']}")
                return False

            # Render terrain using existing pipeline
            def export_progress_callback(progress, message="Rendering"):
                if progress_callback:
                    # Scale progress from 30% to 90% of total export progress
                    scaled_progress = 0.3 + progress * 0.6
                    progress_callback(scaled_progress, message)
            
            image = self.render_terrain(
                elevation_data=elevation_data,
                gradient_name=gradient_name,
                min_elevation=min_elevation,
                max_elevation=max_elevation,
                progress_callback=export_progress_callback if progress_callback else None
            )
            
            if image is None:
                print(f"❌ Failed to render terrain")
                return False
            
            if progress_callback:
                progress_callback(0.9, "Saving file")
            
            # Determine output format from file extension
            file_path_lower = file_path.lower()
            save_kwargs = {}
            
            if file_path_lower.endswith('.jpg') or file_path_lower.endswith('.jpeg'):
                # JPEG export - convert RGBA to RGB (JPEG doesn't support transparency)
                if image.mode == 'RGBA':
                    # Create white background for transparency
                    from PIL import Image as PILImage
                    background = PILImage.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
                    image = background
                save_kwargs = {'quality': 95, 'optimize': True}
                if dpi:
                    save_kwargs['dpi'] = (dpi, dpi)
                
            elif file_path_lower.endswith('.png'):
                # PNG export - convert RGBA to RGB with solid background (no transparency)
                if image.mode == 'RGBA':
                    from PIL import Image as PILImage
                    # Create white background to replace transparency
                    background = PILImage.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1])  # Use alpha channel as mask
                    image = background
                save_kwargs = {'optimize': True}
                if dpi:
                    save_kwargs['dpi'] = (dpi, dpi)
                
            else:
                # Default to PNG for other extensions - also remove transparency
                if image.mode == 'RGBA':
                    from PIL import Image as PILImage
                    background = PILImage.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1])
                    image = background
                save_kwargs = {'optimize': True}
                if dpi:
                    save_kwargs['dpi'] = (dpi, dpi)
            
            # Save the image
            image.save(file_path, **save_kwargs)
            
            if progress_callback:
                progress_callback(1.0, "Export complete")
            
            print(f"✅ Export successful: {file_path}")
            print(f"   Image size: {image.size}")
            print(f"   Image mode: {image.mode}")
            
            return True
            
        except Exception as e:
            print(f"❌ Export failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _check_rendering_memory_safety(
        self,
        elevation_data: np.ndarray,
        gradient_name: str
    ) -> dict:
        """
        Check if rendering can proceed given memory constraints (FIX BUG #2 - CORRECTED)

        This checks the RENDERING stage, not assembly. Assembly uses chunking which can
        handle huge outputs. Rendering currently loads everything into memory.

        Args:
            elevation_data: The assembled elevation data to render
            gradient_name: Name of gradient (to check if it needs hillshade/shadows)

        Returns:
            Dict with keys: 'safe' (bool), 'error' (str), 'suggestion' (str)
        """
        import psutil

        height, width = elevation_data.shape
        total_pixels = height * width

        # Get gradient to check what layers will be created
        gradient = self.gradient_manager.get_gradient(gradient_name)
        has_shading = False
        has_shadows = False

        if gradient:
            has_shading = hasattr(gradient, 'gradient_type') and gradient.gradient_type in [
                'shaded_relief', 'shading_and_gradient', 'shading_and_posterized'
            ]
            has_shadows = has_shading and hasattr(gradient, 'cast_shadows') and gradient.cast_shadows

        # Calculate memory requirements for rendering
        # Each layer that will be created:
        elevation_memory_mb = (total_pixels * 4) / (1024**2)  # float32
        gradient_memory_mb = (total_pixels * 4) / (1024**2)   # RGBA uint8
        hillshade_memory_mb = (total_pixels * 1) / (1024**2) if has_shading else 0  # grayscale uint8
        shadow_memory_mb = (total_pixels * 1) / (1024**2) if has_shadows else 0     # grayscale uint8
        compositing_memory_mb = (total_pixels * 8) / (1024**2)  # temporary arrays during blending

        # Total memory needed
        total_memory_mb = (elevation_memory_mb + gradient_memory_mb + hillshade_memory_mb +
                          shadow_memory_mb + compositing_memory_mb)
        total_memory_gb = total_memory_mb / 1024

        # Get system memory
        memory = psutil.virtual_memory()
        available_gb = memory.available / (1024**3)
        total_system_gb = memory.total / (1024**3)

        # Hard limits
        MAX_PIXELS = 500_000_000  # 500 million pixels
        MAX_MEMORY_PERCENT = 0.85  # Use max 85% of total system memory

        # Check 1: Pixel count limit
        if total_pixels > MAX_PIXELS:
            safe_scale = np.sqrt(MAX_PIXELS / total_pixels)
            safe_percent = int(safe_scale * 100)

            return {
                'safe': False,
                'error': f"Output too large: {width:,}×{height:,} = {total_pixels:,} pixels (max: {MAX_PIXELS:,})",
                'suggestion': f"Reduce export scale to ~{safe_percent}% or select a smaller area"
            }

        # Check 2: Memory availability for rendering
        max_safe_memory_gb = total_system_gb * MAX_MEMORY_PERCENT

        if total_memory_gb > max_safe_memory_gb:
            # Calculate safe scale
            safe_scale = np.sqrt(max_safe_memory_gb / total_memory_gb)
            safe_percent = int(safe_scale * 100)

            return {
                'safe': False,
                'error': (f"Insufficient memory for rendering: needs {total_memory_gb:.1f}GB, "
                         f"only {available_gb:.1f}GB available (system has {total_system_gb:.1f}GB total)"),
                'suggestion': f"Reduce export scale to ~{safe_percent}% or close other applications"
            }

        # Check 3: Warning for high memory usage
        if total_memory_gb > available_gb * 0.7:
            print(f"⚠️  High memory usage: rendering will use {total_memory_gb:.1f}GB of {available_gb:.1f}GB available")
            print(f"   Consider closing other applications if export fails")

        # All checks passed
        print(f"✅ Memory check passed: {total_memory_gb:.1f}GB needed, {available_gb:.1f}GB available")
        return {
            'safe': True,
            'error': None,
            'suggestion': None
        }

    def render_normalized_elevation_layer(
        self,
        elevation_data: np.ndarray,
        min_elevation: Optional[float] = None,
        max_elevation: Optional[float] = None,
        no_data_color: Optional[Tuple[int, int, int, int]] = None
    ) -> np.ndarray:
        """
        Render normalized grayscale elevation layer where min=black, max=white.
        
        Args:
            elevation_data: 2D numpy array of elevation values
            min_elevation: Override minimum elevation (optional)
            max_elevation: Override maximum elevation (optional)  
            no_data_color: RGBA color for no-data areas (default: transparent)
            
        Returns:
            RGBA numpy array (height, width, 4) - grayscale elevation with alpha
        """
        height, width = elevation_data.shape
        
        # Handle NaN values
        valid_mask = ~np.isnan(elevation_data)
        
        if not np.any(valid_mask):
            print("⚠️ No valid elevation data found")
            # Return transparent image
            return np.zeros((height, width, 4), dtype=np.uint8)
        
        # Determine elevation range
        if min_elevation is None or max_elevation is None:
            valid_elevations = elevation_data[valid_mask]
            calc_min = np.min(valid_elevations)
            calc_max = np.max(valid_elevations)
            
            min_elev = min_elevation if min_elevation is not None else calc_min
            max_elev = max_elevation if max_elevation is not None else calc_max
        else:
            min_elev = min_elevation
            max_elev = max_elevation
        
        print(f"📏 Normalized elevation range: {min_elev:.1f}m to {max_elev:.1f}m")
        
        # Avoid division by zero
        if max_elev == min_elev:
            print("⚠️ Min and max elevation are equal, using mid-gray")
            normalized = np.full((height, width), 128, dtype=np.uint8)
        else:
            # Normalize elevation to 0-255 range (min=0/black, max=255/white)
            normalized = np.zeros((height, width), dtype=np.uint8)
            normalized[valid_mask] = np.clip(
                255 * (elevation_data[valid_mask] - min_elev) / (max_elev - min_elev),
                0, 255
            ).astype(np.uint8)
        
        # Create RGBA image (grayscale with alpha)
        rgba_image = np.zeros((height, width, 4), dtype=np.uint8)
        
        # Set RGB channels to normalized grayscale values
        rgba_image[..., 0] = normalized  # Red
        rgba_image[..., 1] = normalized  # Green  
        rgba_image[..., 2] = normalized  # Blue
        
        # Set alpha channel
        if no_data_color is None:
            # Transparent for no-data areas, opaque for valid data
            rgba_image[valid_mask, 3] = 255  # Opaque
            rgba_image[~valid_mask, 3] = 0   # Transparent
        else:
            # Use specified no-data color
            rgba_image[valid_mask, 3] = 255  # Opaque for valid data
            rgba_image[~valid_mask, :3] = no_data_color[:3]  # No-data color RGB
            rgba_image[~valid_mask, 3] = no_data_color[3] if len(no_data_color) > 3 else 255
        
        valid_pixels = np.sum(valid_mask)
        print(f"✅ Normalized elevation layer: {valid_pixels:,} valid pixels")
        
        return rgba_image


def main():
    """Test the terrain renderer with sample data."""
    
    # Test with small synthetic DEM if available
    synthetic_dem = Path("small_synthetic_dem")
    if synthetic_dem.exists():
        print("Testing terrain renderer with small synthetic DEM...")
        
        renderer = TerrainRenderer()
        
        # List available gradients
        gradients = renderer.get_available_gradients()
        print(f"Available gradients: {gradients}")
        
        # Test rendering with different gradients
        for gradient_name in gradients[:2]:  # Test first 2 gradients
            print(f"\nTesting gradient: {gradient_name}")
            output_path = renderer.render_dem_file(
                synthetic_dem,
                gradient_name,
                subsample=1  # Full resolution for small test file
            )
            
            if output_path:
                print(f"✓ Created: {output_path}")
        
        # Show statistics
        stats = renderer.get_rendering_stats()
        print(f"\nRendering statistics:")
        print(f"  Total renders: {stats['total_renders']}")
        print(f"  Last render time: {stats['last_render_time']:.3f}s")
        print(f"  Last pixels processed: {stats['last_pixels_processed']:,}")
        
    else:
        print("Small synthetic DEM not found. Run create_small_synthetic_dem.py first.")
        
        # Test with any available DEM
        dem_path = Path("../dem-databases/gt30e020n40_dem")
        if dem_path.exists():
            print(f"Testing with {dem_path}...")
            renderer = TerrainRenderer()
            output_path = renderer.render_dem_file(
                dem_path,
                "Classic Elevation",
                subsample=8  # Heavy subsample for speed
            )
            if output_path:
                print(f"✓ Created: {output_path}")


if __name__ == "__main__":
    main()