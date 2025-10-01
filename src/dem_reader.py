#!/usr/bin/env python3
"""
DEM Visualizer - Basic DEM File Reader
Recreating functionality from 1990s TopoToImage software

Supports GTOPO30 BIL format and modern GeoTIFF formats
"""

import numpy as np
import struct
import os
from pathlib import Path
from typing import Tuple, Dict, Optional, Union, List
from PIL import Image
import matplotlib.pyplot as plt

# Global rasterio availability check
try:
    import rasterio
    import rasterio.sample
    RASTERIO_AVAILABLE = True
    print("✅ rasterio available - GeoTIFF support enabled")
except ImportError as e:
    RASTERIO_AVAILABLE = False
    print(f"⚠️ rasterio not available - GeoTIFF support disabled: {e}")


class DEMReader:
    """
    Basic DEM file reader supporting GTOPO30 BIL format and GeoTIFF
    """
    
    def __init__(self, file_path: Union[str, Path] = None):
        """
        Initialize DEM reader with optional file path
        
        Args:
            file_path: Path to DEM file or directory containing BIL files (optional)
        """
        self.file_path = Path(file_path) if file_path else None
        self.metadata = {}
        self.elevation_data = None
        self.bounds = None
        self.width = None
        self.height = None
        
        # Try to detect and load file format if path provided
        if self.file_path:
            self._detect_and_load()
    
    def _detect_and_load(self):
        """Detect file format and load metadata"""
        if self.file_path.is_dir():
            # Look for BIL format files in directory
            self._load_bil_format()
        elif self.file_path.suffix.lower() in ['.tif', '.tiff']:
            # GeoTIFF format
            self._load_geotiff_format()
        elif self.file_path.suffix.lower() in ['.dem', '.bil']:
            # Direct BIL format file (.dem or .bil) - look for header in same directory
            self._load_bil_format()
        else:
            raise ValueError(f"Unsupported file format: {self.file_path}")
    
    def _load_bil_format(self):
        """Load BIL format data (.dem or .bil files) including GTOPO30 and SRTM"""
        if self.file_path.is_dir():
            # Find .dem or .bil files in directory
            dem_files = list(self.file_path.glob("*.dem"))
            bil_files = list(self.file_path.glob("*.bil"))
            
            if dem_files:
                dem_file = dem_files[0]
            elif bil_files:
                dem_file = bil_files[0]
            else:
                raise FileNotFoundError(f"No .dem or .bil files found in {self.file_path}")
            
            base_name = dem_file.stem
        else:
            # Direct .dem or .bil file
            dem_file = self.file_path
            base_name = dem_file.stem
        
        # Look for header file
        hdr_file = dem_file.parent / f"{base_name}.hdr"
        if not hdr_file.exists():
            raise FileNotFoundError(f"Header file not found: {hdr_file}")
        
        # Parse header file
        self._parse_bil_header(hdr_file)
        
        # Set file paths
        self.dem_file = dem_file
        self.hdr_file = hdr_file
        
        # Look for additional files
        self.prj_file = dem_file.parent / f"{base_name}.prj"
        self.stx_file = dem_file.parent / f"{base_name}.stx"
        
        # Load projection info if available
        if self.prj_file.exists():
            self._parse_projection_file(self.prj_file)
        
        # Load statistics if available
        if self.stx_file.exists():
            self._parse_statistics_file(self.stx_file)
        
        # Calculate geographic bounds
        self._calculate_bounds()
        
        print(f"✓ Successfully loaded BIL format DEM: {dem_file.name}")
    
    def _parse_bil_header(self, hdr_file: Path):
        """Parse BIL header file"""
        with open(hdr_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].upper()
                    value = ' '.join(parts[1:])
                    
                    # Convert numeric values
                    try:
                        if '.' in value:
                            value = float(value)
                        elif value.lstrip('-').isdigit():
                            value = int(value)
                    except ValueError:
                        pass
                    
                    self.metadata[key] = value
        
        # Validate required fields
        required_fields = ['NROWS', 'NCOLS', 'NBITS', 'NODATA', 'ULXMAP', 'ULYMAP', 'XDIM', 'YDIM']
        for field in required_fields:
            if field not in self.metadata:
                raise ValueError(f"Required header field missing: {field}")
    
    def _parse_projection_file(self, prj_file: Path):
        """Parse projection file"""
        with open(prj_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0]
                    value = ' '.join(parts[1:])
                    self.metadata[f"PROJ_{key}"] = value
        
        # Validate coordinate system compatibility
        is_valid, message = self.validate_coordinate_system(prj_file)
        if is_valid is False:
            raise ValueError(f"Incompatible coordinate system: {message}")
        elif is_valid is None:
            print(f"Warning: {message}")
    
    def validate_coordinate_system(self, prj_file: Path):
        """
        Validate that the coordinate system is geographic (lat/lon) not projected
        
        Args:
            prj_file: Path to .prj projection file
            
        Returns:
            Tuple of (is_valid: bool|None, message: str)
            - True: Compatible geographic coordinate system
            - False: Incompatible projected coordinate system  
            - None: Unknown format (warning but proceed)
        """
        try:
            with open(prj_file, 'r') as f:
                prj_content = f.read().upper()
            
            # Check for geographic coordinate system indicators
            if 'PROJECTION' in prj_content and 'GEOGRAPHIC' in prj_content:
                # Handle both "PROJECTION GEOGRAPHIC" and "PROJECTION    GEOGRAPHIC" (with multiple spaces)
                datum = "Unknown"
                for line in prj_content.split('\n'):
                    if 'DATUM' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            datum = parts[1]
                            break
                return True, f"Geographic coordinate system (Datum: {datum})"
                
            elif 'GEOGCS[' in prj_content and 'PROJCS[' not in prj_content:
                # Well-Known Text (WKT) format geographic system
                return True, "Geographic coordinate system (WKT format)"
                
            elif 'PROJCS[' in prj_content:
                # Projected coordinate system - extract projection name
                proj_name = "Unknown"
                if 'PROJECTION[' in prj_content:
                    start = prj_content.find('PROJECTION[') + 11
                    end = prj_content.find(']', start)
                    if end > start:
                        proj_name = prj_content[start:end].strip('"')
                return False, f"Projected coordinate system ({proj_name}) - requires lat/lon geographic data"
                
            else:
                return None, f"Unknown coordinate system format in {prj_file.name}"
                
        except Exception as e:
            return None, f"Could not read projection file {prj_file.name}: {e}"
    
    def _parse_statistics_file(self, stx_file: Path):
        """Parse statistics file"""
        with open(stx_file, 'r') as f:
            line = f.readline().strip()
            if line:
                parts = line.split()
                if len(parts) >= 5:
                    self.metadata['STATS_BAND'] = int(parts[0])
                    self.metadata['STATS_MIN'] = float(parts[1])
                    self.metadata['STATS_MAX'] = float(parts[2])
                    self.metadata['STATS_MEAN'] = float(parts[3])
                    self.metadata['STATS_STDDEV'] = float(parts[4])
    
    def _calculate_bounds(self):
        """Calculate geographic bounds"""
        if all(key in self.metadata for key in ['ULXMAP', 'ULYMAP', 'XDIM', 'YDIM', 'NCOLS', 'NROWS']):
            west = self.metadata['ULXMAP']
            north = self.metadata['ULYMAP']
            east = west + (self.metadata['NCOLS'] * self.metadata['XDIM'])
            south = north - (self.metadata['NROWS'] * self.metadata['YDIM'])
            
            self.bounds = {
                'west': west,
                'north': north,
                'east': east,
                'south': south
            }
            
            # Set width and height for easy access
            self.width = self.metadata['NCOLS']
            self.height = self.metadata['NROWS']
    
    def load_dem_file(self, file_path: Union[str, Path]) -> bool:
        """
        Load a DEM file into this reader instance
        
        Args:
            file_path: Path to DEM file or directory containing BIL files
            
        Returns:
            True if file loaded successfully, False otherwise
        """
        try:
            self.file_path = Path(file_path)
            self.metadata = {}
            self.elevation_data = None
            self.bounds = None
            self.width = None
            self.height = None
            
            self._detect_and_load()
            return True
        except Exception as e:
            print(f"Error loading DEM file {file_path}: {e}")
            return False
    
    def get_geographic_bounds(self) -> Optional[List[float]]:
        """
        Get geographic bounds in [west, north, east, south] format
        
        Returns:
            List of [west, north, east, south] coordinates, or None if not loaded
        """
        if self.bounds:
            return [
                self.bounds['west'],
                self.bounds['north'], 
                self.bounds['east'],
                self.bounds['south']
            ]
        return None
    
    def _load_geotiff_format(self):
        """Load GeoTIFF format using rasterio with validation for elevation data"""
        if not RASTERIO_AVAILABLE:
            raise ImportError(
                "GeoTIFF support requires the 'rasterio' library.\n\n"
                "To install rasterio, run this command in your terminal:\n"
                "pip install rasterio\n\n"
                "Alternative: You can use .dem or .bil format files instead, "
                "which don't require additional libraries."
            )
        try:
            with rasterio.open(self.file_path) as dataset:
                # First, validate that this is an elevation database, not an image
                validation_result = self._validate_geotiff_elevation_data(dataset)
                
                if not validation_result['is_elevation']:
                    raise ValueError(
                        f"This GeoTIFF file appears to contain {validation_result['detected_type']} data, not elevation data.\n\n"
                        f"Reasons: {', '.join(validation_result['reasons'])}\n\n"
                        f"For elevation databases, please use:\n"
                        f"• Single-band GeoTIFF files with floating-point elevation data\n"
                        f"• .dem or .bil format elevation files\n\n"
                        f"This file appears to be a regular image (RGB/RGBA) rather than an elevation database."
                    )
                
                self.metadata['NROWS'] = dataset.height
                self.metadata['NCOLS'] = dataset.width
                self.metadata['NBANDS'] = dataset.count
                self.bounds = {
                    'west': dataset.bounds.left,
                    'south': dataset.bounds.bottom,
                    'east': dataset.bounds.right,
                    'north': dataset.bounds.top
                }
                self.metadata['CRS'] = str(dataset.crs)
                
                # Set width and height for easy access
                self.width = dataset.width
                self.height = dataset.height
                
            print(f"✓ Successfully loaded GeoTIFF elevation database: {self.file_path.name}")
            print(f"   Validation: {validation_result['confidence']:.0%} confidence elevation data")
        except ImportError:
            raise ImportError(
                "GeoTIFF support requires the 'rasterio' library.\n\n"
                "To install rasterio, run this command in your terminal:\n"
                "pip install rasterio\n\n"
                "Alternative: You can use .dem or .bil format files instead, "
                "which don't require additional libraries."
            )
    
    def load_elevation_data(self, subsample: Optional[int] = None) -> np.ndarray:
        """
        Load elevation data from DEM file
        
        Args:
            subsample: If provided, subsample the data by this factor for faster loading
            
        Returns:
            2D numpy array of elevation values
        """
        if self.file_path.suffix.lower() in ['.tif', '.tiff']:
            return self._load_geotiff_data(subsample)
        else:
            return self._load_bil_data(subsample)
    
    def _load_bil_data(self, subsample: Optional[int] = None) -> np.ndarray:
        """Load BIL format elevation data"""
        nrows = self.metadata['NROWS']
        ncols = self.metadata['NCOLS']
        nbits = self.metadata['NBITS']
        byteorder = self.metadata.get('BYTEORDER', 'M')
        nodata = self.metadata['NODATA']
        
        # Determine data type and byte order
        if nbits == 16:
            if byteorder == 'M':  # Motorola (big-endian)
                dtype = '>i2'
            else:  # Intel (little-endian)
                dtype = '<i2'
        elif nbits == 32:
            if byteorder == 'M':
                dtype = '>i4'
            else:
                dtype = '<i4'
        else:
            raise ValueError(f"Unsupported bit depth: {nbits}")
        
        # Load data
        with open(self.dem_file, 'rb') as f:
            data = np.frombuffer(f.read(), dtype=dtype)
        
        # Reshape to 2D array
        data = data.reshape(nrows, ncols)
        
        # Handle no-data values
        data = data.astype(np.float32)
        data[data == nodata] = np.nan
        
        # Subsample if requested
        if subsample and subsample > 1:
            data = data[::subsample, ::subsample]
        
        self.elevation_data = data
        return data
    
    def _load_geotiff_data(self, subsample: Optional[int] = None) -> np.ndarray:
        """Load GeoTIFF elevation data"""
        if not RASTERIO_AVAILABLE:
            raise ImportError("rasterio library required for GeoTIFF support")
        try:
            with rasterio.open(self.file_path) as dataset:
                if subsample and subsample > 1:
                    # Read with downsampling
                    out_shape = (dataset.height // subsample, dataset.width // subsample)
                    data = dataset.read(1, out_shape=out_shape)
                else:
                    data = dataset.read(1)
                
                # Handle no-data values
                if dataset.nodata is not None:
                    data = data.astype(np.float32)
                    data[data == dataset.nodata] = np.nan
                
                self.elevation_data = data
                return data
        except ImportError:
            raise ImportError("rasterio library required for GeoTIFF support")
    
    def _validate_geotiff_elevation_data(self, dataset):
        """
        Validate that a GeoTIFF contains elevation data rather than image data
        
        Args:
            dataset: rasterio dataset object
            
        Returns:
            dict with 'is_elevation', 'confidence', 'detected_type', and 'reasons'
        """
        import numpy as np
        
        reasons = []
        elevation_score = 0
        image_score = 0
        
        # Factor 1: Number of bands
        if dataset.count == 1:
            elevation_score += 3
            reasons.append("single band")
        elif dataset.count >= 3:
            image_score += 3
            reasons.append(f"{dataset.count} bands (RGB/RGBA imagery)")
        
        # Factor 2: Data type
        dtype = str(dataset.dtypes[0])
        if 'float' in dtype:
            elevation_score += 2
            reasons.append("floating point data")
        elif 'uint8' in dtype:
            image_score += 2
            reasons.append("8-bit integer data (typical for images)")
        elif 'uint16' in dtype:
            image_score += 1
            reasons.append("16-bit integer data")
        
        # Factor 3: Sample data analysis (only for single band to avoid image confusion)
        if dataset.count == 1:
            try:
                # Read a small sample to avoid loading huge files
                sample_size = min(100, dataset.height)
                sample_data = dataset.read(1, window=((0, sample_size), (0, min(100, dataset.width))))
                
                # Remove NoData values
                if dataset.nodata is not None:
                    valid_data = sample_data[sample_data != dataset.nodata]
                else:
                    valid_data = sample_data.flatten()
                
                # Remove NaN values
                valid_data = valid_data[~np.isnan(valid_data)]
                
                if len(valid_data) > 0:
                    min_val = np.min(valid_data)
                    max_val = np.max(valid_data)
                    
                    # Check value ranges typical for elevation data
                    if min_val >= -500 and max_val <= 10000:
                        elevation_score += 2
                        reasons.append("elevation-like range (-500 to 10,000m)")
                    elif min_val >= 0 and max_val <= 255:
                        image_score += 2
                        reasons.append("8-bit image value range (0-255)")
                    elif min_val >= 0 and max_val <= 65535:
                        image_score += 1
                        reasons.append("16-bit image value range")
                    
                    # Check for negative values (common in elevation data for below sea level)
                    if np.any(valid_data < 0):
                        elevation_score += 1
                        reasons.append("has negative values (below sea level)")
                    
                    # Check if values look like typical image pixel values
                    if dtype == 'uint8' and np.all(valid_data >= 0) and np.all(valid_data <= 255):
                        image_score += 2
                        reasons.append("values match 8-bit image pixel range")
                        
            except Exception as e:
                # If data reading fails, don't penalize, just note it
                reasons.append(f"data sampling failed: {str(e)[:50]}")
        
        # Factor 4: Metadata analysis
        tags = dataset.tags()
        elevation_keywords = ['elevation', 'dem', 'height', 'altitude', 'terrain', 'meters']
        image_keywords = ['image', 'rgb', 'photo', 'picture', 'imagery']
        
        for key, value in tags.items():
            key_lower = key.lower()
            value_lower = str(value).lower()
            
            if any(keyword in key_lower or keyword in value_lower for keyword in elevation_keywords):
                elevation_score += 1
                reasons.append("elevation-related metadata")
                break
            elif any(keyword in key_lower or keyword in value_lower for keyword in image_keywords):
                image_score += 1
                reasons.append("image-related metadata")
                break
        
        # Factor 5: Special check for obvious image indicators
        if dataset.count == 3 and dtype == 'uint8':
            image_score += 3
            reasons.append("RGB 8-bit format (typical image)")
        elif dataset.count == 4 and dtype == 'uint8':
            image_score += 3
            reasons.append("RGBA 8-bit format (typical image)")
        
        # Determine classification
        total_score = elevation_score + image_score
        
        if total_score == 0:
            # If no strong indicators either way, default to rejecting to be safe
            return {
                'is_elevation': False,
                'confidence': 0.0,
                'detected_type': 'unknown',
                'reasons': ['insufficient data to classify']
            }
        
        if elevation_score > image_score:
            confidence = elevation_score / total_score
            # Require at least 60% confidence for elevation data
            is_elevation = confidence >= 0.6
            return {
                'is_elevation': is_elevation,
                'confidence': confidence,
                'detected_type': 'elevation' if is_elevation else 'uncertain',
                'reasons': reasons
            }
        else:
            confidence = image_score / total_score
            return {
                'is_elevation': False,
                'confidence': confidence,
                'detected_type': 'image',
                'reasons': reasons
            }
    
    def get_summary(self) -> str:
        """Get a formatted summary of the DEM file"""
        lines = []
        lines.append(f"DEM File: {self.file_path.name}")
        lines.append(f"Format: {self.metadata.get('LAYOUT', 'Unknown')}")
        lines.append(f"Dimensions: {self.metadata.get('NCOLS', '?')} × {self.metadata.get('NROWS', '?')} pixels")
        
        if self.bounds:
            lines.append(f"Bounds: {self.bounds['west']:.3f}°W to {self.bounds['east']:.3f}°E, "
                        f"{self.bounds['south']:.3f}°S to {self.bounds['north']:.3f}°N")
        
        if 'XDIM' in self.metadata and 'YDIM' in self.metadata:
            lines.append(f"Resolution: {self.metadata['XDIM']:.6f}° × {self.metadata['YDIM']:.6f}°")
        
        if 'STATS_MIN' in self.metadata and 'STATS_MAX' in self.metadata:
            lines.append(f"Elevation range: {self.metadata['STATS_MIN']:.0f}m to {self.metadata['STATS_MAX']:.0f}m")
        
        if 'NODATA' in self.metadata:
            lines.append(f"No data value: {self.metadata['NODATA']}")
        
        if 'PROJ_Datum' in self.metadata:
            lines.append(f"Datum: {self.metadata['PROJ_Datum']}")
        
        return '\n'.join(lines)
    
    def create_preview_image(self, output_path: Optional[Path] = None, size: int = 512) -> Path:
        """
        Create a grayscale preview image of the elevation data
        
        Args:
            output_path: Where to save the preview image
            size: Maximum dimension of the preview image
            
        Returns:
            Path to the created preview image
        """
        if self.elevation_data is None:
            # Load data with subsampling for faster preview
            subsample = max(1, max(self.metadata['NROWS'], self.metadata['NCOLS']) // size)
            self.load_elevation_data(subsample=subsample)
        
        # Create output path if not provided
        if output_path is None:
            output_path = self.file_path.parent / f"{self.file_path.stem}_preview.png"
        
        # Normalize elevation data for display
        data = self.elevation_data.copy()
        
        # Remove NaN values for display
        valid_mask = ~np.isnan(data)
        if np.any(valid_mask):
            min_val = np.nanmin(data)
            max_val = np.nanmax(data)
            
            # Normalize to 0-255 range
            data_norm = np.zeros_like(data)
            data_norm[valid_mask] = 255 * (data[valid_mask] - min_val) / (max_val - min_val)
            data_norm[~valid_mask] = 0  # Set no-data areas to black
        else:
            data_norm = np.zeros_like(data)
        
        # Convert to uint8 and create image
        data_uint8 = data_norm.astype(np.uint8)
        image = Image.fromarray(data_uint8, mode='L')
        
        # Resize if necessary
        if max(image.size) > size:
            image.thumbnail((size, size), Image.Resampling.LANCZOS)
        
        # Save image
        image.save(output_path)
        
        return output_path


def main():
    """Test the DEM reader with the GTOPO30 sample data"""
    # Path to the GTOPO30 data
    dem_path = Path("gt30e020n40_dem")
    
    if not dem_path.exists():
        print(f"DEM data not found at: {dem_path}")
        print("Please ensure the GTOPO30 data is in the current directory")
        return
    
    try:
        # Create DEM reader
        print("Loading DEM file...")
        dem_reader = DEMReader(dem_path)
        
        # Print summary
        print("\n" + dem_reader.get_summary())
        
        # Load elevation data
        print("\nLoading elevation data...")
        elevation_data = dem_reader.load_elevation_data(subsample=4)  # Subsample for speed
        
        print(f"Loaded elevation array: {elevation_data.shape}")
        print(f"Data type: {elevation_data.dtype}")
        print(f"Valid pixels: {np.sum(~np.isnan(elevation_data)):,}")
        print(f"No-data pixels: {np.sum(np.isnan(elevation_data)):,}")
        
        if np.any(~np.isnan(elevation_data)):
            print(f"Elevation range: {np.nanmin(elevation_data):.0f}m to {np.nanmax(elevation_data):.0f}m")
        
        # Create preview image
        print("\nCreating preview image...")
        preview_path = dem_reader.create_preview_image()
        print(f"Preview image saved: {preview_path}")
        
        print("\n✓ DEM reader test completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        return


if __name__ == "__main__":
    main()