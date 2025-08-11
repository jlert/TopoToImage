#!/usr/bin/env python3
"""
Multi-tile DEM loader for handling datasets with multiple DEM files
Supports both metadata-based (JSON) and dynamic scanning approaches
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
from dem_reader import DEMReader

class MultiTileLoader:
    """
    Loads and manages multi-tile DEM datasets
    """
    
    def __init__(self):
        self.dataset_info = None
        self.tiles = {}
        self.coverage_bounds = None  # [west, north, east, south] for entire dataset
        self.loaded_folder = None
        
    def load_dataset(self, folder_path: Union[str, Path]) -> bool:
        """
        Load a multi-tile dataset from a folder
        
        Args:
            folder_path: Path to folder containing DEM files
            
        Returns:
            True if dataset loaded successfully, False otherwise
        """
        folder_path = Path(folder_path)
        
        if not folder_path.exists() or not folder_path.is_dir():
            print(f"Error: {folder_path} is not a valid directory")
            return False
            
        self.loaded_folder = folder_path
        
        # Try metadata-based loading first
        if self._load_from_metadata(folder_path):
            print(f"Loaded dataset using metadata: {self.dataset_info['name']}")
            return True
            
        # Fallback to dynamic scanning
        if self._load_from_scanning(folder_path):
            print(f"Loaded dataset using dynamic scanning")
            return True
            
        print(f"Error: No DEM files found in {folder_path}")
        return False
    
    def _load_from_metadata(self, folder_path: Path) -> bool:
        """Load dataset using JSON metadata file"""
        
        # Look for JSON metadata files
        metadata_files = list(folder_path.glob("*.json"))
        
        if not metadata_files:
            return False
            
        metadata_file = metadata_files[0]  # Use first JSON file found
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                
            self.dataset_info = metadata.get('dataset_info', {})
            tile_specs = metadata.get('tiles', {})
            
            # Load tile information
            self.tiles = {}
            for tile_name, tile_data in tile_specs.items():
                file_path = folder_path / tile_data['file_path']
                
                if file_path.exists():
                    self.tiles[tile_name] = {
                        'file_path': file_path,
                        'bounds': tile_data['bounds'],  # [west, north, east, south]
                        'dimensions': tile_data['dimensions'],  # [width, height]
                        'bounds_desc': tile_data.get('bounds_desc', ''),
                        'loaded': False,
                        'dem_reader': None,
                        'data': None
                    }
                else:
                    print(f"Warning: Missing file {file_path}")
            
            if self.tiles:
                self._calculate_coverage_bounds()
                return True
                
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading metadata: {e}")
            
        return False
    
    def _load_from_scanning(self, folder_path: Path) -> bool:
        """Load dataset by scanning for DEM files"""
        
        # Look for DEM files (common extensions)
        dem_files = []
        for pattern in ['*.dem', '*.bil', '*.tif', '*.tiff']:
            dem_files.extend(folder_path.rglob(pattern))
        
        if not dem_files:
            return False
            
        self.dataset_info = {
            'name': f"Custom Dataset ({folder_path.name})",
            'description': f"Scanned DEM files from {folder_path}",
            'total_tiles': len(dem_files),
            'source': 'Dynamic scanning'
        }
        
        self.tiles = {}
        
        for dem_file in dem_files:
            tile_name = dem_file.stem
            
            try:
                # Create temporary DEM reader to get bounds
                reader = DEMReader()
                if reader.load_dem_file(str(dem_file)):
                    bounds = reader.get_geographic_bounds()  # Should return [west, north, east, south]
                    dimensions = [reader.width, reader.height]
                    
                    self.tiles[tile_name] = {
                        'file_path': dem_file,
                        'bounds': bounds,
                        'dimensions': dimensions,
                        'bounds_desc': f"Scanned from {dem_file.name}",
                        'loaded': False,
                        'dem_reader': None,
                        'data': None
                    }
                    
            except Exception as e:
                print(f"Warning: Could not read {dem_file}: {e}")
        
        if self.tiles:
            self._calculate_coverage_bounds()
            
            # For single-file folders, set total dimensions
            if len(self.tiles) == 1:
                tile_data = list(self.tiles.values())[0]
                self.dataset_info['total_dimensions'] = tile_data['dimensions']
            
            return True
            
        return False
    
    def _calculate_coverage_bounds(self):
        """Calculate overall coverage bounds from all tiles"""
        if not self.tiles:
            return
            
        west_min = float('inf')
        north_max = float('-inf')
        east_max = float('-inf')
        south_min = float('inf')
        
        for tile_data in self.tiles.values():
            west, north, east, south = tile_data['bounds']
            west_min = min(west_min, west)
            north_max = max(north_max, north)
            east_max = max(east_max, east)
            south_min = min(south_min, south)
        
        self.coverage_bounds = [west_min, north_max, east_max, south_min]
    
    def get_coverage_bounds(self) -> Optional[List[float]]:
        """Get overall dataset coverage bounds [west, north, east, south]"""
        return self.coverage_bounds
    
    def get_tiles_for_region(self, region_bounds: List[float]) -> List[str]:
        """
        Get list of tile names that intersect with a geographic region
        
        Args:
            region_bounds: [west, north, east, south] of region of interest
            
        Returns:
            List of tile names that intersect the region
        """
        region_west, region_north, region_east, region_south = region_bounds
        intersecting_tiles = []
        
        for tile_name, tile_data in self.tiles.items():
            tile_west, tile_north, tile_east, tile_south = tile_data['bounds']
            
            # Check for intersection
            if (tile_west < region_east and tile_east > region_west and
                tile_south < region_north and tile_north > region_south):
                intersecting_tiles.append(tile_name)
        
        return intersecting_tiles
    
    def load_tile_data(self, tile_name: str) -> bool:
        """Load elevation data for a specific tile"""
        if tile_name not in self.tiles:
            return False
            
        tile_data = self.tiles[tile_name]
        
        if tile_data['loaded']:
            return True  # Already loaded
            
        try:
            reader = DEMReader()
            if reader.load_dem_file(str(tile_data['file_path'])):
                # Load the actual elevation data
                elevation_data = reader.load_elevation_data()
                tile_data['dem_reader'] = reader
                tile_data['data'] = elevation_data
                tile_data['loaded'] = True
                return True
        except Exception as e:
            print(f"Error loading tile {tile_name}: {e}")
            
        return False
    
    def get_tile_data(self, tile_name: str) -> Optional[np.ndarray]:
        """Get elevation data for a tile (loads if necessary)"""
        if self.load_tile_data(tile_name):
            return self.tiles[tile_name]['data']
        return None
    
    def get_dataset_info(self) -> Dict:
        """Get dataset information"""
        info = self.dataset_info.copy() if self.dataset_info else {}
        info['tiles_loaded'] = len([t for t in self.tiles.values() if t['loaded']])
        info['tiles_total'] = len(self.tiles)
        
        # Add coverage bounds if available
        if self.coverage_bounds:
            west, north, east, south = self.coverage_bounds
            info['bounds'] = {
                'west': west,
                'north': north, 
                'east': east,
                'south': south
            }
        
        # Add total database dimensions (for display in database info window)
        # These should be the total pixel dimensions for the entire database
        if 'total_dimensions' in info:
            # Use dimensions from metadata if available (like GTOPO30: [43200, 21600])
            total_width, total_height = info['total_dimensions']
            info['total_width_pixels'] = total_width
            info['total_height_pixels'] = total_height
        else:
            # Calculate from resolution and geographic bounds
            if self.coverage_bounds and 'resolution_degrees' in info:
                west, north, east, south = self.coverage_bounds
                resolution_deg = info['resolution_degrees']
                
                # Calculate total dimensions from geographic extent and resolution
                total_width_degrees = abs(east - west)
                total_height_degrees = abs(north - south)
                info['total_width_pixels'] = int(total_width_degrees / resolution_deg)
                info['total_height_pixels'] = int(total_height_degrees / resolution_deg)
            else:
                # Fallback: Set to 0 if we can't calculate (better than crashing)
                info['total_width_pixels'] = 0
                info['total_height_pixels'] = 0
        
        # Calculate pixels per degree for export calculations
        if 'resolution_degrees' in info:
            info['pix_per_degree'] = 1.0 / info['resolution_degrees']
        elif self.coverage_bounds and info.get('total_width_pixels', 0) > 0:
            # Calculate from total dimensions and geographic bounds
            west, north, east, south = self.coverage_bounds
            total_width_degrees = abs(east - west)
            if total_width_degrees > 0:
                info['pix_per_degree'] = info['total_width_pixels'] / total_width_degrees
            else:
                info['pix_per_degree'] = 0
        else:
            info['pix_per_degree'] = 0
        
        return info
    
    def get_tile_list(self) -> List[str]:
        """Get list of all tile names"""
        return list(self.tiles.keys())
    
    def get_tile_bounds(self, tile_name: str) -> Optional[List[float]]:
        """Get bounds for a specific tile [west, north, east, south]"""
        if tile_name in self.tiles:
            return self.tiles[tile_name]['bounds']
        return None
    
    def get_tile_resolution(self, tile_name: str) -> Optional[Tuple[float, float]]:
        """Get resolution (XDIM, YDIM) for a specific tile in degrees per pixel"""
        if tile_name not in self.tiles:
            return None
            
        tile_data = self.tiles[tile_name]
        
        # Try to get from loaded dem_reader first
        if tile_data.get('dem_reader'):
            metadata = tile_data['dem_reader'].metadata
            xdim = metadata.get('XDIM')
            ydim = metadata.get('YDIM')
            if xdim is not None and ydim is not None:
                return (xdim, ydim)
        
        # Fallback: load the tile to get metadata
        if self.load_tile_data(tile_name):
            dem_reader = self.tiles[tile_name]['dem_reader']
            if dem_reader and dem_reader.metadata:
                xdim = dem_reader.metadata.get('XDIM')
                ydim = dem_reader.metadata.get('YDIM')
                if xdim is not None and ydim is not None:
                    return (xdim, ydim)
        
        return None
    
    def get_database_resolution(self) -> Optional[Tuple[float, float]]:
        """Get resolution for the database by checking the first available tile"""
        if not self.tiles:
            return None
            
        # Get resolution from the first tile (all tiles in a database should have same resolution)
        tile_name = list(self.tiles.keys())[0]
        return self.get_tile_resolution(tile_name)
    
    def unload_tile_data(self, tile_name: str):
        """Unload elevation data for a tile to free memory"""
        if tile_name in self.tiles:
            self.tiles[tile_name]['loaded'] = False
            self.tiles[tile_name]['dem_reader'] = None
            self.tiles[tile_name]['data'] = None
    
    def unload_all_tiles(self):
        """Unload all tile data to free memory"""
        for tile_name in self.tiles:
            self.unload_tile_data(tile_name)

if __name__ == "__main__":
    # Test the multi-tile loader
    loader = MultiTileLoader()
    
    # Test with GTOPO30 dataset
    if loader.load_dataset("Gtopo30"):
        print(f"Dataset info: {loader.get_dataset_info()}")
        print(f"Coverage bounds: {loader.get_coverage_bounds()}")
        print(f"Total tiles: {len(loader.get_tile_list())}")
        
        # Test region query
        europe_bounds = [0, 60, 40, 40]  # [west, north, east, south]
        europe_tiles = loader.get_tiles_for_region(europe_bounds)
        print(f"Tiles for Europe region: {europe_tiles}")
        
        # Test loading a single tile
        if europe_tiles:
            tile_name = europe_tiles[0]
            print(f"Loading tile: {tile_name}")
            if loader.load_tile_data(tile_name):
                data = loader.get_tile_data(tile_name)
                print(f"Loaded data shape: {data.shape}")
            else:
                print("Failed to load tile data")
    else:
        print("Failed to load dataset")