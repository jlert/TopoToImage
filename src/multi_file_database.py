#!/usr/bin/env python3
"""
Multi-File Database System for DEM Visualizer
Handles discovery, assembly, and preview generation for multi-tile databases like Gtopo30.
"""

import re
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from dem_reader import DEMReader
from meridian_utils import (
    calculate_longitude_span, 
    map_longitude_to_array_x, 
    calculate_meridian_crossing_output_dimensions,
    split_meridian_crossing_bounds
)


class TileBounds(NamedTuple):
    """Geographic bounds for a tile"""
    west: float
    north: float
    east: float
    south: float


@dataclass
class TileInfo:
    """Information about a single tile in a multi-file database"""
    name: str
    file_path: Path
    bounds: TileBounds
    width_pixels: int = 0
    height_pixels: int = 0
    pixels_per_degree: float = 0.0
    elevation_range: Tuple[float, float] = (0.0, 0.0)
    

class MultiFileDatabase:
    """Manages multi-file databases like Gtopo30 with automatic tile discovery and assembly"""
    
    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        self.tiles: Dict[str, TileInfo] = {}
        self.global_bounds: Optional[TileBounds] = None
        self.database_type: str = "unknown"
        
        # Initialize DEM reader for tile loading
        self.dem_reader = DEMReader()
        
        # Discover tiles in the database
        self.discover_tiles()
        
    def discover_tiles(self):
        """Discover all tiles in the database directory"""
        if not self.database_path.exists():
            print(f"❌ Database path does not exist: {self.database_path}")
            return
            
        print(f"🔍 Discovering tiles in: {self.database_path}")
        
        # Detect database type from path name
        db_name = self.database_path.name.lower()
        if 'gtopo30' in db_name:
            self.database_type = "gtopo30"
            self._discover_gtopo30_tiles()
        else:
            self.database_type = "generic"
            self._discover_generic_tiles()
            
        if self.tiles:
            self._calculate_global_bounds()
            print(f"✅ Discovered {len(self.tiles)} tiles in {self.database_type} database")
            print(f"📏 Global bounds: {self.global_bounds}")
        else:
            print(f"⚠️ No tiles found in database")
    
    def _discover_gtopo30_tiles(self):
        """Discover GTOPO30 tiles using naming pattern and actual file dimensions"""
        pattern = re.compile(r'gt30([we])(\d{3})([ns])(\d{2})\.dem$')
        
        for dem_file in self.database_path.rglob('*.dem'):
            match = pattern.match(dem_file.name)
            if match:
                try:
                    # Load the DEM file to get actual dimensions and bounds
                    if self.dem_reader.load_dem_file(str(dem_file)):
                        # Get actual bounds from the loaded file
                        bounds_info = self.dem_reader.get_geographic_bounds()
                        if bounds_info:
                            west, north, east, south = bounds_info
                            # Clean up floating-point precision issues
                            west, north, east, south = self._normalize_bounds(west, north, east, south)
                            bounds = TileBounds(west, north, east, south)
                            
                            # Get actual pixel dimensions
                            width_pixels = self.dem_reader.width
                            height_pixels = self.dem_reader.height
                            
                            # Calculate actual resolution
                            tile_width_deg = east - west
                            tile_height_deg = north - south
                            pixels_per_deg = (width_pixels / tile_width_deg + height_pixels / tile_height_deg) / 2
                            
                            tile_info = TileInfo(
                                name=dem_file.stem,
                                file_path=dem_file,
                                bounds=bounds,
                                width_pixels=width_pixels,
                                height_pixels=height_pixels,
                                pixels_per_degree=pixels_per_deg
                            )
                            
                            self.tiles[tile_info.name] = tile_info
                            print(f"   Found tile: {tile_info.name} → {bounds} ({width_pixels}×{height_pixels}, {pixels_per_deg:.1f} px/deg)")
                        else:
                            print(f"   ⚠️ Could not get bounds for: {dem_file.name}")
                    else:
                        print(f"   ⚠️ Could not load: {dem_file.name}")
                except Exception as e:
                    print(f"   ⚠️ Error processing {dem_file.name}: {e}")
                    continue
    
    def _discover_generic_tiles(self):
        """Discover tiles in generic multi-file databases"""
        # Look for common DEM file extensions
        extensions = ['.dem', '.bil', '.tif', '.tiff']
        
        for ext in extensions:
            for dem_file in self.database_path.rglob(f'*{ext}'):
                try:
                    # Try to load the file to get bounds information
                    if self.dem_reader.load_dem_file(str(dem_file)):
                        bounds_info = self.dem_reader.get_geographic_bounds()
                        if bounds_info:
                            west, north, east, south = bounds_info
                            # Clean up floating-point precision issues
                            west, north, east, south = self._normalize_bounds(west, north, east, south)
                            bounds = TileBounds(west, north, east, south)
                            
                            # Calculate actual resolution
                            tile_width_deg = east - west
                            tile_height_deg = north - south
                            pixels_per_deg = (self.dem_reader.width / tile_width_deg + self.dem_reader.height / tile_height_deg) / 2
                            
                            tile_info = TileInfo(
                                name=dem_file.stem,
                                file_path=dem_file,
                                bounds=bounds,
                                width_pixels=self.dem_reader.width,
                                height_pixels=self.dem_reader.height,
                                pixels_per_degree=pixels_per_deg
                            )
                            
                            self.tiles[tile_info.name] = tile_info
                            print(f"   Found tile: {tile_info.name} → {bounds} ({self.dem_reader.width}×{self.dem_reader.height}, {pixels_per_deg:.1f} px/deg)")
                            
                except Exception as e:
                    print(f"   ⚠️ Could not process {dem_file.name}: {e}")
                    continue
    
    def _normalize_bounds(self, west: float, north: float, east: float, south: float) -> Tuple[float, float, float, float]:
        """Clean up floating-point precision issues in bounds"""
        # Round very small values near zero to exactly zero
        tolerance = 1e-10
        
        if abs(west) < tolerance:
            west = 0.0
        if abs(north - 90.0) < tolerance:
            north = 90.0
        if abs(east - 90.0) < tolerance:
            east = 90.0
        elif abs(east - 180.0) < tolerance:
            east = 180.0
        elif abs(east) < tolerance:
            east = 0.0
        if abs(south) < tolerance:
            south = 0.0
        elif abs(south + 90.0) < tolerance:
            south = -90.0
            
        # Round to reasonable precision (6 decimal places should be sufficient for geographic coordinates)
        west = round(west, 6)
        north = round(north, 6)
        east = round(east, 6)
        south = round(south, 6)
        
        return west, north, east, south
    
    @staticmethod
    def _static_normalize_bounds(west: float, north: float, east: float, south: float) -> Tuple[float, float, float, float]:
        """Static version of bounds normalization for use in class methods"""
        # Round very small values near zero to exactly zero
        tolerance = 1e-10
        
        if abs(west) < tolerance:
            west = 0.0
        if abs(north - 90.0) < tolerance:
            north = 90.0
        if abs(east - 90.0) < tolerance:
            east = 90.0
        elif abs(east - 180.0) < tolerance:
            east = 180.0
        elif abs(east) < tolerance:
            east = 0.0
        if abs(south) < tolerance:
            south = 0.0
        elif abs(south + 90.0) < tolerance:
            south = -90.0
            
        # Round to reasonable precision (6 decimal places should be sufficient for geographic coordinates)
        west = round(west, 6)
        north = round(north, 6)
        east = round(east, 6)
        south = round(south, 6)
        
        return west, north, east, south
    
    def _calculate_global_bounds(self):
        """Calculate the overall bounds of all tiles"""
        if not self.tiles:
            return
            
        west_values = [tile.bounds.west for tile in self.tiles.values()]
        east_values = [tile.bounds.east for tile in self.tiles.values()]
        north_values = [tile.bounds.north for tile in self.tiles.values()]
        south_values = [tile.bounds.south for tile in self.tiles.values()]
        
        self.global_bounds = TileBounds(
            west=min(west_values),
            north=max(north_values),
            east=max(east_values),
            south=min(south_values)
        )
    
    def get_tiles_for_bounds(self, west: float, north: float, east: float, south: float) -> List[TileInfo]:
        """Get all tiles that intersect with the given bounds"""
        print(f"🔍 DEBUG: get_tiles_for_bounds called with bounds: W={west}°, N={north}°, E={east}°, S={south}°")
        print(f"🔍 DEBUG: Database type: {self.database_type}, Total tiles available: {len(self.tiles)}")
        
        intersecting_tiles = []
        
        # Always check tiles in their normal positions first
        print(f"🔍 DEBUG: Checking normal tile positions...")
        normal_tiles = self._get_tiles_for_simple_bounds(west, north, east, south)
        print(f"🔍 DEBUG: Found {len(normal_tiles)} normal tiles: {[t.name for t in normal_tiles]}")
        intersecting_tiles.extend(normal_tiles)
        
        # Check for meridian crossing cases and add shifted tiles
        crossing_east = east > 180.0
        crossing_west = west < -180.0
        
        print(f"🔍 DEBUG: Meridian crossing check - crossing_east: {crossing_east}, crossing_west: {crossing_west}")
        
        if crossing_east:
            # Selection crosses eastward past 180° - check each tile shifted +360°
            print(f"🌍 DEBUG: Crossing east detected (east={east}°) - checking tiles shifted +360°")
            shifted_tiles = self._get_tiles_with_longitude_shift(west, north, east, south, 360.0)
            print(f"🔍 DEBUG: Found {len(shifted_tiles)} east-shifted tiles: {[t.name for t in shifted_tiles]}")
            intersecting_tiles.extend(shifted_tiles)
            
        if crossing_west:
            # Selection crosses westward past -180° - check each tile shifted -360°
            print(f"🌍 DEBUG: Crossing west detected (west={west}°) - checking tiles shifted -360°")
            shifted_tiles = self._get_tiles_with_longitude_shift(west, north, east, south, -360.0)
            print(f"🔍 DEBUG: Found {len(shifted_tiles)} west-shifted tiles: {[t.name for t in shifted_tiles]}")
            intersecting_tiles.extend(shifted_tiles)
        
        # Remove duplicates (same tile found multiple ways)
        unique_tiles = []
        seen_names = set()
        for tile in intersecting_tiles:
            if tile.name not in seen_names:
                unique_tiles.append(tile)
                seen_names.add(tile.name)
        
        print(f"🔍 DEBUG: Final unique tiles: {len(unique_tiles)} total")
        for tile in unique_tiles:
            print(f"   📋 {tile.name}: {tile.bounds}")
        
        if crossing_east or crossing_west:
            print(f"🌍 Meridian crossing: found {len(unique_tiles)} unique tiles (including shifted)")
        
        return unique_tiles
    
    def _get_tiles_for_simple_bounds(self, west: float, north: float, east: float, south: float) -> List[TileInfo]:
        """Get tiles for bounds that don't cross prime meridian"""
        intersecting_tiles = []
        
        for tile in self.tiles.values():
            # Check if tile bounds intersect with selection bounds
            if (tile.bounds.west < east and tile.bounds.east > west and
                tile.bounds.south < north and tile.bounds.north > south):
                intersecting_tiles.append(tile)
        
        return intersecting_tiles
    
    def _get_tiles_with_longitude_shift(self, west: float, north: float, east: float, south: float, longitude_shift: float) -> List[TileInfo]:
        """Check each tile with shifted longitude coordinates to find meridian crossing matches"""
        print(f"🔍 DEBUG: _get_tiles_with_longitude_shift called with shift={longitude_shift}°")
        intersecting_tiles = []
        
        for tile in self.tiles.values():
            # Shift the tile's longitude bounds
            shifted_west = tile.bounds.west + longitude_shift
            shifted_east = tile.bounds.east + longitude_shift
            
            print(f"   🔄 DEBUG: Checking tile {tile.name}: original ({tile.bounds.west:.1f}°, {tile.bounds.east:.1f}°) → shifted ({shifted_west:.1f}°, {shifted_east:.1f}°)")
            
            # Check if the shifted tile intersects with selection bounds
            intersects = (shifted_west < east and shifted_east > west and
                         tile.bounds.south < north and tile.bounds.north > south)
            
            print(f"      🔍 DEBUG: Intersection check: ({shifted_west:.1f} < {east}) and ({shifted_east:.1f} > {west}) and ({tile.bounds.south:.1f} < {north}) and ({tile.bounds.north:.1f} > {south}) = {intersects}")
            
            if intersects:
                intersecting_tiles.append(tile)
                print(f"   ✅ Found shifted tile: {tile.name} shifted to ({shifted_west:.1f}°, {shifted_east:.1f}°)")
            else:
                print(f"   ❌ No intersection for shifted tile: {tile.name}")
        
        return intersecting_tiles
    
    def assemble_tiles_for_bounds(self, west: float, north: float, east: float, south: float) -> Optional[np.ndarray]:
        """Assemble elevation data from multiple tiles for the given bounds"""
        
        # Get intersecting tiles
        tiles = self.get_tiles_for_bounds(west, north, east, south)
        
        if not tiles:
            print(f"⚠️ No tiles found for bounds: {west}, {north}, {east}, {south}")
            return None
        
        print(f"🔨 Assembling {len(tiles)} tiles for preview:")
        for tile in tiles:
            print(f"   • {tile.name}: {tile.bounds}")
        
        # For now, implement a simple assembly strategy
        # TODO: Implement proper stitching with overlap handling
        return self._simple_tile_assembly(tiles, west, north, east, south)
    
    def _simple_tile_assembly(self, tiles: List[TileInfo], west: float, north: float, east: float, south: float) -> Optional[np.ndarray]:
        """Simple tile assembly - loads and crops each tile individually then stitches"""
        
        # Determine target resolution based on first tile
        if not tiles:
            return None
            
        # Determine target resolution from tiles (use the highest resolution available)
        target_pixels_per_deg = 120  # Default fallback
        
        for tile in tiles:
            if hasattr(tile, 'pixels_per_degree') and tile.pixels_per_degree > 0:
                target_pixels_per_deg = max(target_pixels_per_deg, tile.pixels_per_degree)
        
        # Calculate output dimensions handling meridian crossing
        output_width, crosses_meridian = calculate_meridian_crossing_output_dimensions(
            west, east, target_pixels_per_deg
        )
        output_height = int((north - south) * target_pixels_per_deg)
        
        # Fix for full world export: if width is 0 but we have full world bounds, force correct width
        if output_width == 0 and abs(west - (-180.0)) < 0.1 and abs(east - 180.0) < 0.1:
            print(f"🌍 Detected full world export with zero width - fixing...")
            output_width = int(360.0 * target_pixels_per_deg)  # 360° * pixels_per_degree
            crosses_meridian = False  # Treat as normal span for full world
            print(f"   Fixed width: {output_width} pixels (360° × {target_pixels_per_deg} px/deg)")
        
        print(f"📐 Assembly target: {output_width}×{output_height} pixels")
        print(f"   Resolution: {target_pixels_per_deg:.1f} pixels/degree")
        if crosses_meridian:
            span = calculate_longitude_span(west, east)
            print(f"   🌍 Prime meridian crossing detected: {span.width_degrees:.1f}° total span")
            print(f"     Region 1: {span.region1_west:.1f}° to {span.region1_east:.1f}°")
            # Handle case where region2 values might be None (e.g., full world bounds)
            if span.region2_west is not None and span.region2_east is not None:
                print(f"     Region 2: {span.region2_west:.1f}° to {span.region2_east:.1f}°")
            else:
                print(f"     Region 2: None (full world bounds)")
        
        # Create output array filled with NaN (no data)
        assembled_data = np.full((output_height, output_width), np.nan, dtype=np.float32)
        
        # Process each tile
        for tile in tiles:
            try:
                if not self.dem_reader.load_dem_file(str(tile.file_path)):
                    print(f"   ⚠️ Could not load tile: {tile.name}")
                    continue
                
                elevation_data = self.dem_reader.load_elevation_data()
                if elevation_data is None:
                    print(f"   ⚠️ No elevation data for tile: {tile.name}")
                    continue
                
                # Calculate intersection between tile bounds and selection bounds
                # Handle meridian crossing by determining if this tile was found via shifting
                tile_needs_shifting = False
                
                print(f"🔍 DEBUG: Processing tile {tile.name} with bounds {tile.bounds}")
                print(f"🔍 DEBUG: Selection bounds: W={west}°, N={north}°, E={east}°, S={south}°")
                print(f"🔍 DEBUG: crosses_meridian={crosses_meridian}")
                
                # Check if this tile needs longitude shifting for intersection calculation
                if crosses_meridian:
                    # Check if tile intersects normally
                    normal_intersects = (tile.bounds.west < east and tile.bounds.east > west and
                                        tile.bounds.south < north and tile.bounds.north > south)
                    
                    print(f"🔍 DEBUG: Normal intersection check: ({tile.bounds.west} < {east}) and ({tile.bounds.east} > {west}) and ({tile.bounds.south} < {north}) and ({tile.bounds.north} > {south}) = {normal_intersects}")
                    
                    if not normal_intersects:
                        # This tile was found via shifting - need to calculate intersection with shifted coordinates
                        if east > 180.0:  # East crossing case
                            # Shift tile east by 360° for intersection calculation
                            shifted_west = tile.bounds.west + 360.0
                            shifted_east = tile.bounds.east + 360.0
                            intersect_west = max(west, shifted_west)
                            intersect_east = min(east, shifted_east)
                            tile_needs_shifting = True
                            print(f"🔍 DEBUG: East crossing - tile shifted to ({shifted_west}°, {shifted_east}°)")
                            print(f"🔍 DEBUG: Shifted intersection: W={intersect_west}°, E={intersect_east}°")
                        elif west < -180.0:  # West crossing case
                            # Shift tile west by 360° for intersection calculation
                            # gt30e140n90 (140° to 180°) becomes (-220° to -180°)
                            shifted_west = tile.bounds.west - 360.0
                            shifted_east = tile.bounds.east - 360.0
                            intersect_west = max(west, shifted_west)
                            intersect_east = min(east, shifted_east)
                            tile_needs_shifting = True
                            print(f"🔍 DEBUG: West crossing - tile shifted to ({shifted_west}°, {shifted_east}°)")
                            print(f"🔍 DEBUG: Shifted intersection: W={intersect_west}°, E={intersect_east}°")
                
                if not tile_needs_shifting:
                    # Normal intersection calculation
                    intersect_west = max(west, tile.bounds.west)
                    intersect_east = min(east, tile.bounds.east)
                    print(f"🔍 DEBUG: Normal intersection: W={intersect_west}°, E={intersect_east}°")
                
                intersect_north = min(north, tile.bounds.north)
                intersect_south = max(south, tile.bounds.south)
                
                print(f"   📍 FINAL Intersection: W={intersect_west:.1f}°, N={intersect_north:.1f}°, E={intersect_east:.1f}°, S={intersect_south:.1f}°")
                print(f"🔍 DEBUG: tile_needs_shifting = {tile_needs_shifting}")
                
                # Calculate where this intersection should go in the output array (handling meridian crossing)
                output_west_px = map_longitude_to_array_x(intersect_west, west, east, output_width, crosses_meridian)
                output_east_px = map_longitude_to_array_x(intersect_east, west, east, output_width, crosses_meridian)
                output_north_px = int((north - intersect_north) * target_pixels_per_deg)
                output_south_px = int((north - intersect_south) * target_pixels_per_deg)
                
                # Ensure east > west for array indexing
                if output_east_px < output_west_px:
                    output_east_px, output_west_px = output_west_px, output_east_px
                
                # Calculate which part of the tile to extract
                tile_width_deg = tile.bounds.east - tile.bounds.west
                tile_height_deg = tile.bounds.north - tile.bounds.south
                tile_height_px, tile_width_px = elevation_data.shape
                
                # For tile pixel calculation, use original tile bounds even when intersection used shifted coordinates
                if tile_needs_shifting:
                    # Need to map shifted intersection back to original tile coordinates
                    if east > 180.0:  # East crossing case
                        # For positive meridian crossing, the shifted intersection coordinates need to be
                        # wrapped back to the tile's coordinate space properly.
                        # The issue is that we shifted the tile by +360° for intersection calculation,
                        # but now we need to map the intersection back to the tile's actual coordinate range.
                        
                        # Simple approach: just subtract 360° from both coordinates to get them 
                        # back into the tile's coordinate space
                        tile_intersect_west = intersect_west - 360.0
                        tile_intersect_east = intersect_east - 360.0
                        
                        # Ensure they're within the tile's actual bounds
                        tile_intersect_west = max(tile_intersect_west, tile.bounds.west)
                        tile_intersect_east = min(tile_intersect_east, tile.bounds.east)
                        
                    elif west < -180.0:  # West crossing case
                        # Map shifted intersection coordinates back to original tile space
                        # For west crossing, coordinates like -200° should map to 160°, -180° should map to 180°
                        tile_intersect_west = intersect_west + 360.0 if intersect_west < -180.0 else intersect_west
                        tile_intersect_east = intersect_east + 360.0 if intersect_east < -179.99 else intersect_east
                else:
                    # Normal case - use intersection coordinates as-is
                    tile_intersect_west = intersect_west
                    tile_intersect_east = intersect_east
                
                print(f"🔍 DEBUG: Tile pixel calculation inputs:")
                print(f"   tile_intersect_west = {tile_intersect_west:.6f}°")
                print(f"   tile_intersect_east = {tile_intersect_east:.6f}°")
                print(f"   tile.bounds.west = {tile.bounds.west:.6f}°")
                print(f"   tile_width_deg = {tile_width_deg:.6f}°")
                print(f"   tile_width_px = {tile_width_px}")
                
                tile_west_px = int((tile_intersect_west - tile.bounds.west) / tile_width_deg * tile_width_px)
                tile_east_px = int((tile_intersect_east - tile.bounds.west) / tile_width_deg * tile_width_px)
                tile_north_px = int((tile.bounds.north - intersect_north) / tile_height_deg * tile_height_px)
                tile_south_px = int((tile.bounds.north - intersect_south) / tile_height_deg * tile_height_px)
                
                print(f"🔍 DEBUG: Calculated tile pixels:")
                print(f"   tile_west_px = {tile_west_px}")
                print(f"   tile_east_px = {tile_east_px}")
                print(f"   pixel width = {tile_east_px - tile_west_px}")
                
                # Debug output for meridian crossing cases
                if tile_needs_shifting:
                    print(f"   🔧 Tile coordinate mapping: intersect({intersect_west:.1f}°, {intersect_east:.1f}°) → tile_intersect({tile_intersect_west:.1f}°, {tile_intersect_east:.1f}°)")
                    print(f"   🔧 Pixel calculation: ({tile_intersect_west:.1f} - {tile.bounds.west:.1f}) / {tile_width_deg:.1f} * {tile_width_px} = {tile_west_px} to {tile_east_px}")
                
                # Clamp tile coordinates to valid ranges
                tile_west_px = max(0, min(tile_west_px, tile_width_px - 1))
                tile_east_px = max(tile_west_px + 1, min(tile_east_px, tile_width_px))
                tile_north_px = max(0, min(tile_north_px, tile_height_px - 1))
                tile_south_px = max(tile_north_px + 1, min(tile_south_px, tile_height_px))
                
                # Extract the intersection portion from the tile
                cropped_tile_data = elevation_data[tile_north_px:tile_south_px, tile_west_px:tile_east_px]
                
                print(f"   🔪 Tile crop: [{tile_north_px}:{tile_south_px}, {tile_west_px}:{tile_east_px}] → {cropped_tile_data.shape}")
                
                # Calculate target dimensions in output array
                target_height = output_south_px - output_north_px
                target_width = output_east_px - output_west_px
                
                if target_height > 0 and target_width > 0:
                    # Use NaN-aware interpolation to match single-file system behavior
                    try:
                        from nan_aware_interpolation import resize_with_nan_exclusion
                        
                        print(f"   🔄 NaN-aware tile resize: {cropped_tile_data.shape} → ({target_height}, {target_width})")
                        
                        # Use NaN-aware interpolation for proper coastline handling
                        resized_data = resize_with_nan_exclusion(
                            cropped_tile_data, 
                            (target_height, target_width),
                            method='lanczos'
                        )
                        
                        print(f"   ✅ NaN-aware tile resize complete")
                        
                    except Exception as e:
                        # Fallback to simple subsampling if NaN-aware fails
                        print(f"   ⚠️ NaN-aware tile resize failed ({e}), using simple scaling")
                        
                        # Calculate scale factors
                        scale_y = target_height / cropped_tile_data.shape[0]
                        scale_x = target_width / cropped_tile_data.shape[1]
                        
                        if scale_y < 1.0 and scale_x < 1.0:
                            # Downsampling - use simple subsampling to preserve data integrity
                            subsample_y = max(1, int(1.0 / scale_y))
                            subsample_x = max(1, int(1.0 / scale_x))
                            resized_data = cropped_tile_data[::subsample_y, ::subsample_x]
                            print(f"   ✅ Simple subsampling: {resized_data.shape}")
                        else:
                            # Upsampling or complex scaling - use PIL with sentinel values
                            from PIL import Image
                            
                            # Convert cropped tile data to PIL image for resizing
                            if cropped_tile_data.dtype != np.float32:
                                cropped_tile_data = cropped_tile_data.astype(np.float32)
                            
                            # Handle NaN values for PIL
                            has_nan = np.isnan(cropped_tile_data)
                            if np.any(has_nan):
                                sentinel_value = np.nanmin(cropped_tile_data) - 1000 if np.any(~has_nan) else -9999
                                resizing_data = cropped_tile_data.copy()
                                resizing_data[has_nan] = sentinel_value
                            else:
                                resizing_data = cropped_tile_data
                                sentinel_value = None
                            
                            # Resize using PIL
                            pil_image = Image.fromarray(resizing_data.astype(np.float32), mode='F')
                            resized_image = pil_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
                            resized_data = np.array(resized_image, dtype=np.float32)
                            
                            # Restore NaN values
                            if sentinel_value is not None:
                                resized_data[resized_data <= sentinel_value + 500] = np.nan
                            
                            print(f"   ✅ PIL resize fallback: {resized_data.shape}")
                    
                    # Place into assembled array at correct output position
                    assembled_data[output_north_px:output_south_px, output_west_px:output_east_px] = resized_data
                    
                    print(f"   ✅ Assembled tile {tile.name}: {resized_data.shape} → [{output_north_px}:{output_south_px}, {output_west_px}:{output_east_px}]")
                
            except Exception as e:
                print(f"   ❌ Error processing tile {tile.name}: {e}")
                continue
        
        # Check if we got any data
        valid_pixels = np.sum(~np.isnan(assembled_data))
        total_pixels = assembled_data.size
        
        print(f"🎯 Assembly complete: {valid_pixels:,}/{total_pixels:,} pixels ({valid_pixels/total_pixels*100:.1f}% coverage)")
        
        if valid_pixels == 0:
            print(f"❌ No valid data in assembled result")
            return None
        
        return assembled_data
    
    @staticmethod
    def create_metadata_file(folder_path: Path, database_name: str = None) -> bool:
        """
        Create a metadata JSON file for a folder containing DEM files
        
        Args:
            folder_path: Path to folder containing DEM files
            database_name: Optional name for the database (defaults to folder name)
            
        Returns:
            True if metadata file created successfully, False otherwise
        """
        import json
        from datetime import datetime
        
        folder_path = Path(folder_path)
        
        if not folder_path.exists() or not folder_path.is_dir():
            print(f"❌ {folder_path} is not a valid directory")
            return False
        
        print(f"🔍 Scanning folder for DEM files: {folder_path}")
        
        # Look for DEM files (common extensions)
        dem_files = []
        for pattern in ['*.dem', '*.bil', '*.tif', '*.tiff']:
            found_files = list(folder_path.rglob(pattern))
            dem_files.extend(found_files)
            
        if not dem_files:
            print(f"❌ No DEM files found in {folder_path}")
            return False
            
        print(f"📁 Found {len(dem_files)} potential DEM files")
        
        # Create DEM reader for scanning
        dem_reader = DEMReader()
        tiles_metadata = {}
        
        # Calculate overall bounds and resolution
        all_west = []
        all_north = []  
        all_east = []
        all_south = []
        resolutions = []
        valid_files = 0
        
        for dem_file in dem_files:
            try:
                print(f"   📊 Processing: {dem_file.name}")
                
                if dem_reader.load_dem_file(str(dem_file)):
                    bounds = dem_reader.get_geographic_bounds()
                    if bounds:
                        west, north, east, south = bounds
                        # Clean up floating-point precision issues
                        west, north, east, south = MultiFileDatabase._static_normalize_bounds(west, north, east, south)
                        width = dem_reader.width
                        height = dem_reader.height
                        
                        # Calculate resolution (pixels per degree)
                        tile_width_deg = east - west
                        tile_height_deg = north - south
                        if tile_width_deg > 0 and tile_height_deg > 0:
                            res_x = width / tile_width_deg
                            res_y = height / tile_height_deg
                            avg_resolution = (res_x + res_y) / 2.0
                            resolutions.append(avg_resolution)
                        
                        # Get relative path from folder
                        relative_path = dem_file.relative_to(folder_path)
                        
                        # Create tile metadata
                        tile_name = dem_file.stem
                        tiles_metadata[tile_name] = {
                            "file_path": str(relative_path),
                            "dimensions": [width, height],
                            "bounds": [west, north, east, south],
                            "bounds_desc": f"{west:.1f}°{'E' if west >= 0 else 'W'}, {north:.1f}°{'N' if north >= 0 else 'S'}, {east:.1f}°{'E' if east >= 0 else 'W'}, {south:.1f}°{'N' if south >= 0 else 'S'}",
                            "resolution_degrees": [tile_width_deg / width, tile_height_deg / height],
                            "nodata_value": getattr(dem_reader, 'no_data_value', -9999),
                            "byte_order": "little_endian",  # Most modern files
                            "data_format": dem_file.suffix.upper()[1:],  # Remove dot, uppercase
                            "bits_per_sample": 16  # Most common
                        }
                        
                        # Collect bounds for overall calculation
                        all_west.append(west)
                        all_north.append(north)
                        all_east.append(east)
                        all_south.append(south)
                        valid_files += 1
                        
                        print(f"      ✅ {width}×{height}, {west:.1f}°-{east:.1f}°, {south:.1f}°-{north:.1f}°")
                    else:
                        print(f"      ⚠️ Could not get geographic bounds")
                else:
                    print(f"      ⚠️ Could not load as DEM file")
                    
            except Exception as e:
                print(f"      ❌ Error processing {dem_file.name}: {e}")
                continue
        
        if valid_files == 0:
            print(f"❌ No valid DEM files found")
            return False
            
        if valid_files == 1:
            print(f"⚠️ Only 1 valid DEM file found. Consider using 'Open Single File' instead.")
            # Continue anyway - user might want to add more files later
        
        # Calculate overall database bounds
        global_west = min(all_west)
        global_north = max(all_north)
        global_east = max(all_east)
        global_south = min(all_south)
        
        # Calculate average resolution
        avg_resolution = sum(resolutions) / len(resolutions) if resolutions else 30.0  # Default to 30 arc-seconds
        resolution_degrees = 1.0 / avg_resolution if avg_resolution > 0 else 0.00833333333333
        
        # Calculate total dimensions if this were a single raster
        total_width = int((global_east - global_west) / resolution_degrees)
        total_height = int((global_north - global_south) / resolution_degrees)
        
        # Create database metadata
        db_name = database_name or f"Custom Database ({folder_path.name})"
        
        metadata = {
            "dataset_info": {
                "name": db_name,
                "description": f"Multi-file database created from {folder_path}",
                "resolution_arcsec": 3600.0 / avg_resolution if avg_resolution > 0 else 30,
                "resolution_degrees": resolution_degrees,
                "total_dimensions": [total_width, total_height],
                "total_bounds": [global_west, global_north, global_east, global_south],
                "bounds_desc": f"{global_west:.1f}°{'E' if global_west >= 0 else 'W'}, {global_north:.1f}°{'N' if global_north >= 0 else 'S'}, {global_east:.1f}°{'E' if global_east >= 0 else 'W'}, {global_south:.1f}°{'N' if global_south >= 0 else 'S'}",
                "total_tiles": valid_files,
                "coverage": f"{valid_files} tiles covering {global_east - global_west:.1f}° × {global_north - global_south:.1f}°",
                "source": "User-created multi-file database",
                "coordinate_system": "Geographic (WGS84)",
                "datum": "WGS84",
                "nodata_value": -9999,
                "data_type": "int16",
                "byte_order": "little_endian",
                "created_date": datetime.now().isoformat(),
                "created_by": "TopoToImage v4.0.0"
            },
            "tiles": tiles_metadata
        }
        
        # Write metadata file
        metadata_file = folder_path / f"{folder_path.name}_metadata.json"
        
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Created metadata file: {metadata_file.name}")
            print(f"📊 Database summary:")
            print(f"   Name: {db_name}")
            print(f"   Tiles: {valid_files}")
            print(f"   Coverage: {global_west:.1f}°W-{global_east:.1f}°E, {global_south:.1f}°S-{global_north:.1f}°N")
            print(f"   Resolution: ~{3600.0 / avg_resolution:.0f} arc-seconds")
            
            return True
            
        except Exception as e:
            print(f"❌ Error writing metadata file: {e}")
            return False


def test_multi_file_database():
    """Test the multi-file database system with Gtopo30"""
    
    print("🧪 Testing Multi-File Database System")
    print("=" * 50)
    
    # Test with Gtopo30 database
    gtopo30_path = Path("/Users/josephlertola/Documents/claude-code/dem-databases/Gtopo30")
    
    if not gtopo30_path.exists():
        print(f"❌ Gtopo30 database not found at: {gtopo30_path}")
        return False
    
    # Create multi-file database instance
    db = MultiFileDatabase(gtopo30_path)
    
    print(f"\nDatabase info:")
    print(f"   Type: {db.database_type}")
    print(f"   Tiles: {len(db.tiles)}")
    print(f"   Global bounds: {db.global_bounds}")
    
    # Test tile discovery for a specific area (e.g., part of Europe)
    west, north, east, south = 10.0, 50.0, 30.0, 40.0  # Central Europe
    intersecting_tiles = db.get_tiles_for_bounds(west, north, east, south)
    
    print(f"\nTiles for Europe test area ({west}°, {north}°, {east}°, {south}°):")
    for tile in intersecting_tiles:
        print(f"   • {tile.name}: {tile.bounds}")
    
    # Test prime meridian crossing (Pacific area)
    west, north, east, south = 170.0, 60.0, -170.0, 50.0  # Crosses prime meridian
    crossing_tiles = db.get_tiles_for_bounds(west, north, east, south)
    
    print(f"\nTiles for Pacific crossing area ({west}°, {north}°, {east}°, {south}°):")
    for tile in crossing_tiles:
        print(f"   • {tile.name}: {tile.bounds}")
    
    return True


if __name__ == "__main__":
    test_multi_file_database()