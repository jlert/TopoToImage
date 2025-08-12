#!/usr/bin/env python3
"""
DEM Visualizer - Map Display Widgets
Sophisticated map widgets for displaying world maps, DEM coverage, and selection tools
"""

import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
        QGroupBox, QLineEdit, QRadioButton, QButtonGroup, QMessageBox
    )
    from PyQt6.QtCore import Qt, QSize, pyqtSignal
    from PyQt6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QDoubleValidator
except ImportError:
    print("PyQt6 not available")
    import sys
    sys.exit(1)

from dem_reader import DEMReader
from multi_tile_loader import MultiTileLoader
from map_backgrounds import WorldMapRenderer
from coordinate_converter import CoordinateConverter


class WorldMapWidget(QWidget):
    """Custom widget that always shows world map with 2:1 aspect ratio"""
    
    selection_changed = pyqtSignal(dict)  # Emit selection bounds
    create_preview_requested = pyqtSignal(dict)  # Emit request to create preview from selection
    
    def __init__(self):
        super().__init__()
        self.dem_coverage = None  # Geographic bounds of loaded DEM (single file)
        self.tile_boundaries = []  # List of tile boundaries for multi-tile datasets
        self.selection_start_geo = None  # Geographic coordinates of selection start
        self.selection_end_geo = None    # Geographic coordinates of selection end
        self.is_selecting = False        # Track if currently selecting
        
        # Support for wrap-around selections in global databases
        self.selection_rectangles = []   # List of selection rectangles (for wrap-around)
        self.has_wrapped_selection = False  # Track if selection wraps around 180°/-180°
        
        self.setMinimumSize(400, 200)  # 2:1 aspect ratio minimum
        
        # Initialize world map renderer (delay to avoid startup issues)
        self.map_renderer = None
        self._background_ready = False
        
    def sizeHint(self):
        """Maintain 2:1 aspect ratio (world map proportions)"""
        return QSize(588, 294)
    
    def heightForWidth(self, width):
        """Maintain 2:1 aspect ratio"""
        return width // 2
    
    def resizeEvent(self, event):
        """Keep 2:1 aspect ratio on resize"""
        super().resizeEvent(event)
        # Force 2:1 aspect ratio
        width = self.width()
        height = width // 2
        if height != self.height():
            self.setFixedHeight(height)
    
    def set_dem_coverage(self, bounds):
        """Set the geographic coverage area of a single loaded DEM"""
        self.dem_coverage = bounds
        self.tile_boundaries = []  # Clear multi-tile boundaries
        self.update()
    
    def set_dem_reader(self, dem_reader):
        """Set the DEM reader for pixel resolution and grid origin information"""
        self.dem_reader = dem_reader
    
    def set_tile_boundaries(self, tile_list):
        """Set multiple tile boundaries for multi-tile datasets"""
        self.tile_boundaries = tile_list
        # Don't clear dem_coverage - allow both tile boundaries AND overall coverage
        self.update()
    
    def set_background_map(self, background_name: str):
        """Set the background map by name"""
        if self.map_renderer:
            self.map_renderer.set_background(background_name)
            self.update()
    
    def set_database_background(self, database_type: str, database_path=None):
        """Set background appropriate for database type"""
        if self.map_renderer:
            self.map_renderer.set_database_background(database_type, database_path)
            self.update()
    
    def clear_database_background(self):
        """Clear database-specific background and return to default"""
        if self.map_renderer:
            self.map_renderer.clear_database_background()
            self.update()
    
    def get_available_backgrounds(self):
        """Get list of available background maps"""
        if self.map_renderer:
            return self.map_renderer.get_available_backgrounds()
        return {}
    
    def add_background_map(self, name: str, file_path, description: str = "", database_type: str = None):
        """Add a new background map"""
        if self.map_renderer:
            self.map_renderer.add_background_map(name, file_path, description, database_type)
            self.update()
    
    def geographic_to_pixel(self, lon, lat):
        """Convert geographic coordinates to widget pixel coordinates"""
        # World bounds: -180° to +180° longitude, -90° to +90° latitude
        width = self.width()
        height = self.height()
        
        # Convert to 0-1 range
        lon_norm = (lon + 180) / 360  # -180 to +180 becomes 0 to 1
        lat_norm = (90 - lat) / 180   # +90 to -90 becomes 0 to 1 (y axis flipped)
        
        # Convert to pixel coordinates
        x = int(lon_norm * width)
        y = int(lat_norm * height)
        
        return x, y
    
    def pixel_to_geographic(self, x, y, allow_wrapping=False):
        """Convert widget pixel coordinates to geographic coordinates"""
        width = self.width()
        height = self.height()
        
        # Convert to 0-1 range
        lon_norm = x / width
        lat_norm = y / height
        
        # Convert to geographic coordinates
        lon = lon_norm * 360 - 180    # 0 to 1 becomes -180 to +180
        lat = 90 - lat_norm * 180     # 0 to 1 becomes +90 to -90 (y axis flipped)
        
        # For global databases during selection, allow longitude beyond ±180°
        if allow_wrapping and self.database_spans_360_degrees() and self.is_selecting:
            # Allow longitude to extend beyond ±180° during drag operation
            # This enables wrap-around selection detection
            bounds = self.get_database_bounds()
            if bounds:
                # Only constrain latitude to database bounds
                lat = max(bounds['south'], min(bounds['north'], lat))
            else:
                # Constrain latitude to Earth bounds
                lat = max(-90, min(90, lat))
            return lon, lat
        
        # Normal case - apply full database constraints
        return self.constrain_coordinates_to_database(lon, lat)
    
    def is_point_in_coverage(self, lon, lat):
        """Check if a geographic point is within DEM coverage"""
        # Check single DEM coverage
        if self.dem_coverage:
            return (self.dem_coverage['west'] <= lon <= self.dem_coverage['east'] and
                    self.dem_coverage['south'] <= lat <= self.dem_coverage['north'])
        
        # Check if point is in any tile boundary
        if self.tile_boundaries:
            for tile_bounds in self.tile_boundaries:
                if (tile_bounds['west'] <= lon <= tile_bounds['east'] and
                    tile_bounds['south'] <= lat <= tile_bounds['north']):
                    return True
        
        return False
    
    def get_database_bounds(self):
        """Get the overall bounds of the loaded database"""
        # Single DEM file
        if self.dem_coverage:
            return self.dem_coverage
        
        # Multi-tile database - calculate overall bounds
        if self.tile_boundaries:
            min_west = min(tile['west'] for tile in self.tile_boundaries)
            max_east = max(tile['east'] for tile in self.tile_boundaries)
            min_south = min(tile['south'] for tile in self.tile_boundaries)
            max_north = max(tile['north'] for tile in self.tile_boundaries)
            
            return {
                'west': min_west,
                'east': max_east,
                'south': min_south,
                'north': max_north
            }
        
        return None
    
    def database_spans_360_degrees(self):
        """Check if database spans the full 360° longitude range"""
        bounds = self.get_database_bounds()
        if not bounds:
            return False
        
        # Check if longitude span is 360° (allowing for small floating point errors)
        longitude_span = bounds['east'] - bounds['west']
        return abs(longitude_span - 360.0) < 0.001
    
    def constrain_coordinates_to_database(self, lon, lat):
        """Constrain coordinates to database boundaries"""
        bounds = self.get_database_bounds()
        if not bounds:
            # No database loaded - only constrain to Earth bounds
            return lon, max(-90, min(90, lat))
        
        # Always constrain latitude to database bounds
        lat = max(bounds['south'], min(bounds['north'], lat))
        
        # Longitude constraints depend on whether database spans 360°
        if self.database_spans_360_degrees():
            # Database spans full world - allow longitude wrapping
            # Don't constrain longitude to enable wrap-around selections
            return self.normalize_longitude_for_global(lon), lat
        else:
            # Database is regional - constrain to database longitude bounds
            lon = max(bounds['west'], min(bounds['east'], lon))
            return lon, lat
    
    def selection_crosses_dateline(self, west, east):
        """Check if selection crosses the 180°/-180° dateline"""
        # Only relevant for global databases that span 360°
        if not self.database_spans_360_degrees():
            return False
        
        # Normalize longitudes to detect wrapping
        # If east > 180°, it wraps to negative longitude
        # If west < -180°, it wraps to positive longitude
        if east > 180 or west < -180:
            return True
            
        # Traditional case: west > east (e.g., 170° to -170°)
        return west > east
    
    def split_wrapped_selection(self, west, east, south, north):
        """Split a wrapped selection into two rectangles"""
        if not self.selection_crosses_dateline(west, east):
            # No wrapping - return single rectangle
            return [{'west': west, 'east': east, 'south': south, 'north': north}]
        
        # Handle different wrapping scenarios
        if east > 180:
            # East extends beyond 180° - convert to negative equivalent
            east_wrapped = east - 360
            rectangles = [
                {'west': west, 'east': 180, 'south': south, 'north': north},
                {'west': -180, 'east': east_wrapped, 'south': south, 'north': north}
            ]
        elif west < -180:
            # West extends beyond -180° - convert to positive equivalent  
            west_wrapped = west + 360
            rectangles = [
                {'west': west_wrapped, 'east': 180, 'south': south, 'north': north},
                {'west': -180, 'east': east, 'south': south, 'north': north}
            ]
        else:
            # Traditional case: west > east (e.g., 170° to -170°)
            rectangles = [
                {'west': west, 'east': 180, 'south': south, 'north': north},
                {'west': -180, 'east': east, 'south': south, 'north': north}
            ]
        
        return rectangles
    
    def snap_bounds_to_pixel_grid(self, bounds):
        """Snap selection bounds to DEM pixel grid boundaries"""
        # Get pixel resolution from current database
        pixel_resolution = self.get_pixel_resolution()
        if not pixel_resolution:
            # No database loaded or no resolution info - return unchanged
            return bounds
        
        lon_res, lat_res = pixel_resolution
        
        # Get the upper-left corner of the database for pixel grid alignment
        grid_origin = self.get_pixel_grid_origin()
        if not grid_origin:
            return bounds
        
        origin_lon, origin_lat = grid_origin
        
        # Snap each boundary to the nearest pixel edge
        west = bounds['west']
        east = bounds['east']
        north = bounds['north']
        south = bounds['south']
        
        # For longitude (west/east)
        west_pixel = round((west - origin_lon) / lon_res)
        east_pixel = round((east - origin_lon) / lon_res)
        
        # For latitude (north/south) - note that latitude decreases going down in DEM files
        north_pixel = round((origin_lat - north) / lat_res)
        south_pixel = round((origin_lat - south) / lat_res)
        
        # Convert back to geographic coordinates (pixel edges)
        snapped_west = origin_lon + west_pixel * lon_res
        snapped_east = origin_lon + east_pixel * lon_res
        snapped_north = origin_lat - north_pixel * lat_res
        snapped_south = origin_lat - south_pixel * lat_res
        
        # Ensure proper bounds order while preserving original relationships
        if bounds['west'] < bounds['east']:
            # Normal case: west < east
            final_west = min(snapped_west, snapped_east)
            final_east = max(snapped_west, snapped_east)
        else:
            # Wrap-around case: preserve which was west vs east
            final_west = snapped_west
            final_east = snapped_east
            
        if bounds['south'] < bounds['north']:
            # Normal case: south < north
            final_south = min(snapped_south, snapped_north)
            final_north = max(snapped_south, snapped_north)
        else:
            # Inverted case: preserve which was south vs north
            final_south = snapped_south
            final_north = snapped_north
        
        return {
            'west': final_west,
            'east': final_east,
            'north': final_north,
            'south': final_south
        }
    
    def get_pixel_resolution(self):
        """Get pixel resolution from current database"""
        # Single DEM file - check directly set dem_reader first, then parent
        dem_reader = None
        if self.dem_coverage:
            if hasattr(self, 'dem_reader') and self.dem_reader:
                dem_reader = self.dem_reader
            elif hasattr(self.parent(), 'dem_reader') and self.parent().dem_reader:
                dem_reader = self.parent().dem_reader
        
        if dem_reader:
            # Check for BIL format metadata first (XDIM/YDIM)
            if 'XDIM' in dem_reader.metadata and 'YDIM' in dem_reader.metadata:
                return (dem_reader.metadata['XDIM'], dem_reader.metadata['YDIM'])
            
            # Calculate from bounds and dimensions for GeoTIFF files
            if dem_reader.bounds and dem_reader.width and dem_reader.height:
                lon_span = dem_reader.bounds['east'] - dem_reader.bounds['west']
                lat_span = dem_reader.bounds['north'] - dem_reader.bounds['south']
                lon_res = lon_span / dem_reader.width
                lat_res = lat_span / dem_reader.height
                return (lon_res, lat_res)
        
        # Multi-tile database - use metadata
        bounds = self.get_database_bounds()
        if bounds and self.tile_boundaries:
            # Calculate resolution from first tile
            first_tile = self.tile_boundaries[0]
            # Assume standard GTOPO30 resolution for now
            # TODO: Get actual resolution from multi-tile metadata
            return (0.00833333333333, 0.00833333333333)  # 30 arc-seconds
        
        return None
    
    def get_pixel_grid_origin(self):
        """Get the upper-left corner coordinates for pixel grid alignment"""
        # Single DEM file - check directly set dem_reader first, then parent
        dem_reader = None
        if self.dem_coverage:
            if hasattr(self, 'dem_reader') and self.dem_reader:
                dem_reader = self.dem_reader
            elif hasattr(self.parent(), 'dem_reader') and self.parent().dem_reader:
                dem_reader = self.parent().dem_reader
        
        if dem_reader:
            if 'ULXMAP' in dem_reader.metadata and 'ULYMAP' in dem_reader.metadata:
                return (dem_reader.metadata['ULXMAP'], dem_reader.metadata['ULYMAP'])
        
        # Multi-tile database - use overall bounds
        bounds = self.get_database_bounds()
        if bounds:
            return (bounds['west'], bounds['north'])
        
        return None
    
    def calculate_longitude_span(self, west, east):
        """Calculate the longitude span of a selection, handling wrap-around"""
        if not self.database_spans_360_degrees():
            # Regional database - simple span calculation
            return abs(east - west)
        
        # Global database - handle wrap-around cases
        if east > 180 or west < -180:
            # Selection extends beyond ±180°
            if east > 180:
                # East wraps around: calculate span as if continuous
                return east - west
            elif west < -180:
                # West wraps around: calculate span as if continuous  
                return east - west
        elif west > east:
            # Traditional wrap-around (e.g., 170° to -170°)
            return (180 - west) + (east - (-180))
        else:
            # Normal case
            return east - west
    
    def constrain_longitude_span_to_360(self, start_lon, current_lon):
        """Constrain longitude span to maximum 360° for global databases"""
        if not self.database_spans_360_degrees():
            return current_lon
        
        # Calculate raw span (allowing for values beyond ±180°)
        span = abs(current_lon - start_lon)
        
        # If span exceeds 360°, constrain it
        if span > 360:
            if current_lon > start_lon:
                # Dragging eastward - constrain to start + 360°
                return start_lon + 360
            else:
                # Dragging westward - constrain to start - 360°
                return start_lon - 360
        
        return current_lon
    
    def normalize_longitude_for_global(self, lon):
        """Normalize longitude for global databases (allow wrapping beyond ±180°)"""
        if not self.database_spans_360_degrees():
            return lon
        
        # For global databases, allow longitude to extend beyond ±180°
        # This enables proper wrap-around selection
        return lon
    
    def update_selection_rectangles(self, west, east, south, north):
        """Update selection rectangles, handling wrap-around if needed"""
        # Split selection if it crosses dateline
        self.selection_rectangles = self.split_wrapped_selection(west, east, south, north)
        self.has_wrapped_selection = len(self.selection_rectangles) > 1
        
        # Also set selection_start_geo and selection_end_geo for drawing compatibility
        # These are needed for the paintEvent guard condition
        self.selection_start_geo = (west, north)  # Top-left corner
        self.selection_end_geo = (east, south)    # Bottom-right corner
    
    def paintEvent(self, event):
        """Draw the world map with DEM coverage and selection"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Initialize map renderer on first paint
        if not self._background_ready:
            try:
                if self.map_renderer is None:
                    self.map_renderer = WorldMapRenderer(self)
                self._background_ready = True
            except Exception as e:
                print(f"Error initializing map renderer: {e}")
                # Fall back to simple background
                painter.fillRect(self.rect(), QColor(200, 230, 255))
                return
        
        # Render world map background
        if self.map_renderer:
            self.map_renderer.render_background(painter, self.rect())
        else:
            # Simple fallback background
            painter.fillRect(self.rect(), QColor(200, 230, 255))
        
        # Draw world map grid (lighter overlay on background)
        # DISABLED: Graticule drawing - uncomment line below to restore grid lines
        # self.draw_world_grid(painter)
        
        # Draw DEM coverage area if loaded
        if self.dem_coverage:
            self.draw_coverage_area(painter)
            
        # Draw individual tile boundaries for multi-file databases
        if self.tile_boundaries:
            self.draw_tile_boundaries(painter)
        
        # Draw selection rectangle if active
        if self.selection_start_geo and self.selection_end_geo:
            self.draw_selection_rectangle(painter)
    
    def draw_world_grid(self, painter):
        """Draw geographic grid lines"""
        width = self.width()
        height = self.height()
        
        # Set grid line style
        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.PenStyle.SolidLine))
        
        # Draw longitude lines (vertical) every 30 degrees
        for lon in range(-180, 181, 30):
            x, _ = self.geographic_to_pixel(lon, 0)
            painter.drawLine(x, 0, x, height)
        
        # Draw latitude lines (horizontal) every 30 degrees
        for lat in range(-90, 91, 30):
            _, y = self.geographic_to_pixel(0, lat)
            painter.drawLine(0, y, width, y)
        
        # Draw equator and prime meridian more prominently
        painter.setPen(QPen(QColor(150, 150, 150), 2, Qt.PenStyle.SolidLine))
        
        # Equator (0° latitude)
        _, y = self.geographic_to_pixel(0, 0)
        painter.drawLine(0, y, width, y)
        
        # Prime meridian (0° longitude)
        x, _ = self.geographic_to_pixel(0, 0)
        painter.drawLine(x, 0, x, height)
    
    def draw_coverage_area(self, painter):
        """Draw the DEM coverage area with green border only (no background fill)"""
        # Get coverage bounds
        west = self.dem_coverage['west']
        east = self.dem_coverage['east']
        north = self.dem_coverage['north']
        south = self.dem_coverage['south']
        
        # Convert to pixel coordinates
        x1, y1 = self.geographic_to_pixel(west, north)  # Top-left
        x2, y2 = self.geographic_to_pixel(east, south)  # Bottom-right
        
        # Draw green border around coverage area (no fill)
        painter.setPen(QPen(QColor(0, 120, 0), 2, Qt.PenStyle.SolidLine))
        painter.setBrush(QBrush())  # No fill
        painter.drawRect(x1, y1, x2 - x1, y2 - y1)
    
    def draw_tile_boundaries(self, painter):
        """Draw individual tile boundaries with thin blue borders only (no text labels, no background fill)"""
        # Draw thin blue border for each tile (no gray overlay, no fill, no text labels)
        painter.setPen(QPen(QColor(0, 100, 200), 0.5, Qt.PenStyle.SolidLine))  # Thin blue color
        painter.setBrush(QBrush())  # No fill
        
        for tile_bounds in self.tile_boundaries:
            west = tile_bounds['west']
            east = tile_bounds['east'] 
            north = tile_bounds['north']
            south = tile_bounds['south']
            # Note: Ignoring tile_bounds['name'] to prevent any text labels from being drawn
            
            # Convert to pixel coordinates
            x1, y1 = self.geographic_to_pixel(west, north)  # Top-left
            x2, y2 = self.geographic_to_pixel(east, south)  # Bottom-right
            
            # Draw blue border around this tile area (no fill, no text)
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)
    
    def draw_selection_rectangle(self, painter):
        """Draw the current selection rectangle(s)"""
        # Use a more visible red pen and brush for better visibility in bundled app
        pen = QPen(QColor(255, 0, 0), 1, Qt.PenStyle.SolidLine)
        brush = QBrush(QColor(255, 0, 0, 80))
        painter.setPen(pen)
        painter.setBrush(brush)
        
        # If we have stored selection rectangles (completed selection), draw those
        if self.selection_rectangles:
            for rect in self.selection_rectangles:
                # Convert geographic bounds to pixel coordinates
                x1, y1 = self.geographic_to_pixel(rect['west'], rect['north'])  # Top-left
                x2, y2 = self.geographic_to_pixel(rect['east'], rect['south'])  # Bottom-right
                
                # Calculate rectangle bounds
                x = min(x1, x2)
                y = min(y1, y2)
                w = abs(x2 - x1)
                h = abs(y2 - y1)
                
                painter.drawRect(x, y, w, h)
                
        # If actively selecting, draw the current drag rectangle(s)
        elif self.is_selecting and self.selection_start_geo and self.selection_end_geo:
            # For global databases, check if current drag would wrap around
            if self.database_spans_360_degrees():
                lon1, lat1 = self.selection_start_geo
                lon2, lat2 = self.selection_end_geo
                
                west = min(lon1, lon2)
                east = max(lon1, lon2)
                south = min(lat1, lat2)
                north = max(lat1, lat2)
                
                # Get current drag rectangles (may be split for wrap-around)
                current_rects = self.split_wrapped_selection(west, east, south, north)
                
                for rect in current_rects:
                    # Convert geographic bounds to pixel coordinates
                    x1, y1 = self.geographic_to_pixel(rect['west'], rect['north'])  # Top-left
                    x2, y2 = self.geographic_to_pixel(rect['east'], rect['south'])  # Bottom-right
                    
                    # Calculate rectangle bounds
                    x = min(x1, x2)
                    y = min(y1, y2)
                    w = abs(x2 - x1)
                    h = abs(y2 - y1)
                    
                    painter.drawRect(x, y, w, h)
            else:
                # Regional database - single rectangle
                x1, y1 = self.geographic_to_pixel(self.selection_start_geo[0], self.selection_start_geo[1])
                x2, y2 = self.geographic_to_pixel(self.selection_end_geo[0], self.selection_end_geo[1])
                
                # Calculate rectangle bounds
                x = min(x1, x2)
                y = min(y1, y2)
                w = abs(x2 - x1)
                h = abs(y2 - y1)
                
                painter.drawRect(x, y, w, h)
    
    def mousePressEvent(self, event):
        """Handle mouse press for selection and context menu"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if click is within coverage area
            lon, lat = self.pixel_to_geographic(event.pos().x(), event.pos().y())
            if self.is_point_in_coverage(lon, lat):
                # Clear previous selection rectangles
                self.selection_rectangles = []
                self.has_wrapped_selection = False
                
                self.selection_start_geo = (lon, lat)
                self.selection_end_geo = (lon, lat)
                self.is_selecting = True
        elif event.button() == Qt.MouseButton.RightButton:
            # Handle right-click for context menu
            self.show_map_context_menu(event.globalPosition().toPoint())
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for selection rectangle"""
        if self.is_selecting:
            # Convert current mouse position to geographic coordinates
            # Allow wrapping for global databases to enable wrap-around selection
            lon, lat = self.pixel_to_geographic(event.pos().x(), event.pos().y(), allow_wrapping=True)
            
            # For global databases, constrain longitude span to maximum 360°
            if self.database_spans_360_degrees() and self.selection_start_geo:
                start_lon = self.selection_start_geo[0]
                lon = self.constrain_longitude_span_to_360(start_lon, lon)
            
            self.selection_end_geo = (lon, lat)
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release to complete selection"""
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            # Convert current mouse position to geographic coordinates for final position
            # Allow wrapping for global databases to enable wrap-around selection
            lon, lat = self.pixel_to_geographic(event.pos().x(), event.pos().y(), allow_wrapping=True)
            
            # For global databases, constrain longitude span to maximum 360°
            if self.database_spans_360_degrees() and self.selection_start_geo:
                start_lon = self.selection_start_geo[0]
                lon = self.constrain_longitude_span_to_360(start_lon, lon)
            
            self.selection_end_geo = (lon, lat)
            self.is_selecting = False
            
            # Use the stored geographic coordinates
            lon1, lat1 = self.selection_start_geo
            lon2, lat2 = self.selection_end_geo
            
            # Calculate selection bounds
            west = min(lon1, lon2)
            east = max(lon1, lon2)
            
            south = min(lat1, lat2)
            north = max(lat1, lat2)
            
            # Apply database constraints to final selection bounds
            west, south = self.constrain_coordinates_to_database(west, south)
            east, north = self.constrain_coordinates_to_database(east, north)
            
            # Snap bounds to pixel grid boundaries
            bounds = {'west': west, 'east': east, 'north': north, 'south': south}
            snapped_bounds = self.snap_bounds_to_pixel_grid(bounds)
            
            # Update selection rectangles for drawing (handles wrap-around splitting)
            self.update_selection_rectangles(snapped_bounds['west'], snapped_bounds['east'], 
                                           snapped_bounds['south'], snapped_bounds['north'])
            
            # Emit snapped selection bounds
            self.selection_changed.emit(snapped_bounds)
    
    def show_map_context_menu(self, global_pos):
        """Show context menu for map with create preview option"""
        try:
            from PyQt6.QtWidgets import QMenu
            
            # Only show create preview option if there's an active selection
            has_selection = (self.selection_start_geo is not None and 
                           self.selection_end_geo is not None and
                           self.selection_start_geo != self.selection_end_geo)
            
            if not has_selection:
                # No selection - no context menu
                return
            
            # Create context menu
            context_menu = QMenu(self)
            
            create_action = context_menu.addAction("Create preview icon from selection")
            create_action.triggered.connect(self.request_create_preview_from_selection)
            
            # Show the context menu
            context_menu.exec(global_pos)
            
        except Exception as e:
            print(f"❌ Error showing map context menu: {e}")
            import traceback
            traceback.print_exc()
    
    def request_create_preview_from_selection(self):
        """Request creation of preview icon from current selection"""
        try:
            if not (self.selection_start_geo and self.selection_end_geo):
                print("⚠️  No selection available for preview creation")
                return
            
            # Get selection bounds
            west = min(self.selection_start_geo[0], self.selection_end_geo[0])
            east = max(self.selection_start_geo[0], self.selection_end_geo[0])
            south = min(self.selection_start_geo[1], self.selection_end_geo[1])
            north = max(self.selection_start_geo[1], self.selection_end_geo[1])
            
            # Emit signal with selection bounds
            selection_bounds = {
                'west': west,
                'north': north,
                'east': east,
                'south': south
            }
            
            print(f"🎯 Requesting preview creation from selection: {selection_bounds}")
            self.create_preview_requested.emit(selection_bounds)
            
        except Exception as e:
            print(f"❌ Error requesting preview creation: {e}")
            import traceback
            traceback.print_exc()


class MapDisplayWidget(QWidget):
    """Left panel: Map display with coordinate controls and database info"""
    
    selection_changed = pyqtSignal(dict)  # Emit selection bounds
    
    def __init__(self):
        super().__init__()
        self.dem_reader = None
        self.multi_tile_loader = MultiTileLoader()
        self.coordinate_converter = CoordinateConverter()
        self.is_first_database_load = True  # Track first database load since program start
        self.updating_fields = False  # Flag to prevent signal recursion during field updates
        print(f"[DEBUG] MapDisplayWidget.__init__: is_first_database_load = {self.is_first_database_load}")
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the map display interface"""
        layout = QVBoxLayout(self)
        
        # World map display
        self.world_map = WorldMapWidget()
        layout.addWidget(self.world_map)
        
        # Coordinate input group
        coord_group = QGroupBox("Selection Coordinates")
        coord_layout = QVBoxLayout(coord_group)
        
        # Coordinate format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Format:"))
        
        self.coord_format_group = QButtonGroup()
        self.decimal_radio = QRadioButton("Decimal")
        self.dms_radio = QRadioButton("DMS")
        self.decimal_radio.setChecked(True)  # Default to decimal
        
        self.coord_format_group.addButton(self.decimal_radio)
        self.coord_format_group.addButton(self.dms_radio)
        
        format_layout.addWidget(self.decimal_radio)
        format_layout.addWidget(self.dms_radio)
        format_layout.addStretch()
        
        coord_layout.addLayout(format_layout)
        
        # Coordinate input fields with spatial layout
        coord_input_layout = QVBoxLayout()
        
        # North field (top row)
        north_layout = QHBoxLayout()
        north_layout.addStretch()
        north_layout.addWidget(QLabel("North:"))
        self.north_edit = QLineEdit()
        self.north_edit.setMaximumWidth(120)
        north_layout.addWidget(self.north_edit)
        north_layout.addStretch()
        coord_input_layout.addLayout(north_layout)
        
        # West and East fields (middle row)
        west_east_layout = QHBoxLayout()
        west_east_layout.addWidget(QLabel("West:"))
        self.west_edit = QLineEdit()
        self.west_edit.setMaximumWidth(120)
        west_east_layout.addWidget(self.west_edit)
        
        west_east_layout.addStretch()
        
        west_east_layout.addWidget(QLabel("East:"))
        self.east_edit = QLineEdit()
        self.east_edit.setMaximumWidth(120)
        west_east_layout.addWidget(self.east_edit)
        coord_input_layout.addLayout(west_east_layout)
        
        # South field (bottom row)
        south_layout = QHBoxLayout()
        south_layout.addStretch()
        south_layout.addWidget(QLabel("South:"))
        self.south_edit = QLineEdit()
        self.south_edit.setMaximumWidth(120)
        south_layout.addWidget(self.south_edit)
        south_layout.addStretch()
        coord_input_layout.addLayout(south_layout)
        
        coord_layout.addLayout(coord_input_layout)
        
        layout.addWidget(coord_group)
        
        # Database info display
        info_group = QGroupBox("Database Info")
        info_layout = QVBoxLayout(info_group)
        
        # Database info text
        self.db_info_text = QLabel("No database loaded")
        self.db_info_text.setWordWrap(True)
        self.db_info_text.setStyleSheet("padding: 10px; background-color: #f0f0f0;")
        info_layout.addWidget(self.db_info_text)
        
        layout.addWidget(info_group)
        
        # Connect signals
        self.decimal_radio.toggled.connect(self.on_coordinate_format_changed)
        self.dms_radio.toggled.connect(self.on_coordinate_format_changed)
        self.north_edit.editingFinished.connect(self.on_coordinate_input_changed)
        self.south_edit.editingFinished.connect(self.on_coordinate_input_changed)
        self.east_edit.editingFinished.connect(self.on_coordinate_input_changed)
        self.west_edit.editingFinished.connect(self.on_coordinate_input_changed)
        self.north_edit.returnPressed.connect(self.on_coordinate_input_changed)
        self.south_edit.returnPressed.connect(self.on_coordinate_input_changed)
        self.east_edit.returnPressed.connect(self.on_coordinate_input_changed)
        self.west_edit.returnPressed.connect(self.on_coordinate_input_changed)
        
        # Connect world map selection changes to update coordinate fields
        self.world_map.selection_changed.connect(self.on_world_map_selection_changed)
        
        # Initialize coordinate field validators and format
        self.update_coordinate_field_validators()
        
    def load_dem_file(self, file_path):
        """Load a single DEM file"""
        print(f"[DEBUG] load_dem_file called with: {file_path}")
        print(f"[DEBUG] is_first_database_load at start of load_dem_file: {self.is_first_database_load}")
        try:
            self.dem_reader = DEMReader(file_path)
            bounds = self.dem_reader.get_geographic_bounds()
            if bounds:
                bounds_dict = {
                    'west': bounds[0],
                    'north': bounds[1], 
                    'east': bounds[2],
                    'south': bounds[3]
                }
                self.world_map.set_dem_coverage(bounds_dict)
                self.update_database_info()
                
                # Set database-specific background
                self.world_map.set_database_background("single_dem", file_path)
                
                # Smart selection management
                self.handle_database_loaded(bounds_dict)
            
            # Update coordinate field validators for new database bounds
            self.update_coordinate_field_validators()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load DEM file: {str(e)}")
    
    def update_database_info(self):
        """Update the database info display"""
        if self.dem_reader:
            info = []
            info.append(f"File: {self.dem_reader.file_path.name}")
            info.append(f"Dimensions: {self.dem_reader.metadata.get('NCOLS', '?')} × {self.dem_reader.metadata.get('NROWS', '?')} pixels")
            
            if self.dem_reader.bounds:
                bounds = self.dem_reader.bounds
                info.append(f"Bounds: {bounds['west']:.3f}° to {bounds['east']:.3f}°E")
                info.append(f"        {bounds['south']:.3f}° to {bounds['north']:.3f}°N")
            
            if 'STATS_MIN' in self.dem_reader.metadata:
                info.append(f"Elevation: {self.dem_reader.metadata['STATS_MIN']:.0f}m to {self.dem_reader.metadata['STATS_MAX']:.0f}m")
            
            self.db_info_text.setText('\n'.join(info))
    
    def update_database_info_multi_tile(self, dataset_info):
        """Update the database info display for multi-tile datasets"""
        info = []
        info.append(f"Database: {dataset_info.get('name', 'Unknown')}")
        info.append(f"Tiles: {dataset_info.get('tiles_total', dataset_info.get('tile_count', 0))}")
        
        if 'bounds' in dataset_info:
            bounds = dataset_info['bounds']
            info.append(f"Coverage: {bounds['west']:.1f}° to {bounds['east']:.1f}°E")
            info.append(f"         {bounds['south']:.1f}° to {bounds['north']:.1f}°N")
        
        if 'total_pixels' in dataset_info:
            info.append(f"Total pixels: {dataset_info['total_pixels']:,}")
        
        self.db_info_text.setText('\n'.join(info))
    
    def load_multi_tile_database(self, folder_path):
        """Load a multi-tile DEM database"""
        print(f"[DEBUG] load_multi_tile_database called with: {folder_path}")
        print(f"[DEBUG] is_first_database_load at start of load_multi_tile_database: {self.is_first_database_load}")
        try:
            # Load the database (fixed method name)
            if self.multi_tile_loader.load_dataset(folder_path):
                dataset_info = self.multi_tile_loader.get_dataset_info()
                
                # Extract tile boundaries for map display
                tile_boundaries = []
                for tile_name, tile_info in self.multi_tile_loader.tiles.items():
                    tile_boundaries.append(tile_info['bounds'])
                
                # Update world map with tile boundaries
                self.world_map.set_tile_boundaries(tile_boundaries)
                self.update_database_info_multi_tile(dataset_info)
                
                # Set database-specific background
                self.world_map.set_database_background("multi_tile", folder_path)
                
                # Smart selection management - get overall database bounds
                coverage_bounds = self.multi_tile_loader.get_coverage_bounds()
                if coverage_bounds:
                    # Convert from [west, north, east, south] to bounds dict
                    bounds_dict = {
                        'west': coverage_bounds[0],
                        'north': coverage_bounds[1],
                        'east': coverage_bounds[2],
                        'south': coverage_bounds[3]
                    }
                    self.handle_database_loaded(bounds_dict)
                
                # Update coordinate field validators for new database bounds
                self.update_coordinate_field_validators()
                
                return True
            else:
                QMessageBox.warning(self, "Error", "Failed to load multi-tile database")
                return False
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load database: {str(e)}")
            return False
    
    def on_coordinate_format_changed(self):
        """Handle coordinate format radio button changes"""
        # Update validators based on selected format
        self.update_coordinate_field_validators()
        
        # Convert existing coordinates to new format
        self.update_coordinate_field_display()
    
    def update_coordinate_field_validators(self):
        """Update coordinate field validators based on current format"""
        # Clear existing validators
        self.north_edit.setValidator(None)
        self.south_edit.setValidator(None)
        self.east_edit.setValidator(None)
        self.west_edit.setValidator(None)
        
        if self.decimal_radio.isChecked():
            # Decimal degree format - use QDoubleValidator
            # Get database bounds for validation range
            bounds = self.world_map.get_database_bounds()
            
            if bounds:
                # Use database bounds
                lat_min, lat_max = bounds['south'], bounds['north']
                lon_min, lon_max = bounds['west'], bounds['east']
            else:
                # Use Earth bounds
                lat_min, lat_max = -90.0, 90.0
                lon_min, lon_max = -180.0, 180.0
            
            # Latitude validators
            north_validator = QDoubleValidator(lat_min, lat_max, 6)
            north_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
            self.north_edit.setValidator(north_validator)
            
            south_validator = QDoubleValidator(lat_min, lat_max, 6)
            south_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
            self.south_edit.setValidator(south_validator)
            
            # Longitude validators
            west_validator = QDoubleValidator(lon_min, lon_max, 6)
            west_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
            self.west_edit.setValidator(west_validator)
            
            east_validator = QDoubleValidator(lon_min, lon_max, 6)
            east_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
            self.east_edit.setValidator(east_validator)
        
        # For DMS format, we don't use validators since they would block DMS text input
        # The coordinate parsing will handle validation
    
    def on_coordinate_input_changed(self):
        """Handle manual coordinate input changes"""
        # Prevent recursion during field updates
        if self.updating_fields:
            return
            
        try:
            # Get coordinate format
            is_decimal = self.decimal_radio.isChecked()
            
            # Parse coordinates based on format
            if is_decimal:
                # Parse as decimal degrees
                try:
                    north = float(self.north_edit.text()) if self.north_edit.text() else 0.0
                    south = float(self.south_edit.text()) if self.south_edit.text() else 0.0
                    east = float(self.east_edit.text()) if self.east_edit.text() else 0.0
                    west = float(self.west_edit.text()) if self.west_edit.text() else 0.0
                except ValueError:
                    # Invalid decimal input - ignore
                    return
            else:
                # Parse as DMS coordinates
                north = self.coordinate_converter.dms_to_float(self.north_edit.text()) if self.north_edit.text() else 0.0
                south = self.coordinate_converter.dms_to_float(self.south_edit.text()) if self.south_edit.text() else 0.0
                east = self.coordinate_converter.dms_to_float(self.east_edit.text()) if self.east_edit.text() else 0.0
                west = self.coordinate_converter.dms_to_float(self.west_edit.text()) if self.west_edit.text() else 0.0
                
                if any(coord is None for coord in [north, south, east, west]):
                    # Invalid DMS input - ignore
                    return
            
            # Create bounds dictionary
            bounds = {
                'north': north,
                'south': south,
                'east': east,
                'west': west
            }
            
            # Apply database constraints
            west, south = self.world_map.constrain_coordinates_to_database(west, south)
            east, north = self.world_map.constrain_coordinates_to_database(east, north)
            
            # Update bounds with constrained values
            bounds = {
                'north': north,
                'south': south,
                'east': east,
                'west': west
            }
            
            # Snap to pixel grid
            snapped_bounds = self.world_map.snap_bounds_to_pixel_grid(bounds)
            
            # Update the world map selection
            self.world_map.update_selection_rectangles(
                snapped_bounds['west'], snapped_bounds['east'],
                snapped_bounds['south'], snapped_bounds['north']
            )
            self.world_map.update()
            
            # Update coordinate fields with snapped values
            self.update_coordinate_fields(snapped_bounds)
            
            # Emit the selection change
            self.selection_changed.emit(snapped_bounds)
            
        except Exception as e:
            print(f"Error processing coordinate input: {e}")
    
    def on_world_map_selection_changed(self, bounds):
        """Handle selection changes from world map (e.g., mouse drag selection)"""
        # Update coordinate fields with the snapped bounds from world map
        self.update_coordinate_fields(bounds)
        
        # Forward the selection change signal
        self.selection_changed.emit(bounds)
    
    def format_coordinate(self, value, coord_type):
        """Format coordinate value based on current format setting"""
        is_decimal = self.decimal_radio.isChecked()
        
        if is_decimal:
            # Decimal degrees format
            # Get precision based on pixel resolution
            pixel_resolution = self.world_map.get_pixel_resolution()
            if pixel_resolution:
                if coord_type in ['lat', 'latitude']:
                    resolution = pixel_resolution[1]  # YDIM
                else:
                    resolution = pixel_resolution[0]  # XDIM
                
                # Calculate decimal places needed for pixel resolution
                decimal_places = max(0, int(-np.log10(resolution)) + 1)
                decimal_places = min(decimal_places, 8)  # Cap at 8 decimal places
            else:
                decimal_places = 6  # Default precision
            
            return f"{value:.{decimal_places}f}"
        else:
            # DMS format
            is_longitude = coord_type in ['lon', 'longitude']
            return self.coordinate_converter.float_to_dms(value, is_longitude)
    
    def update_coordinate_field_display(self):
        """Update coordinate field display format without changing values"""
        # Get current selection bounds from world map
        if hasattr(self.world_map, 'selection_rectangles') and self.world_map.selection_rectangles:
            # Use first rectangle for display (most common case)
            bounds = self.world_map.selection_rectangles[0]
            self.update_coordinate_fields(bounds)
    
    def update_coordinate_fields(self, bounds):
        """Update coordinate input fields with new bounds"""
        # Set flag to prevent signal recursion
        self.updating_fields = True
        try:
            # Use clean coordinate formatting to avoid trailing zeros
            from coordinate_validator import coordinate_validator
            
            # Check if DMS radio button is selected (if available)
            is_dms = False
            if hasattr(self, 'dms_radio') and hasattr(self.dms_radio, 'isChecked'):
                is_dms = self.dms_radio.isChecked()
            
            # Format coordinates with clean display (no trailing zeros)
            north_text = coordinate_validator.format_coordinate_clean(bounds['north'], is_longitude=False, use_dms=is_dms)
            south_text = coordinate_validator.format_coordinate_clean(bounds['south'], is_longitude=False, use_dms=is_dms)
            east_text = coordinate_validator.format_coordinate_clean(bounds['east'], is_longitude=True, use_dms=is_dms)
            west_text = coordinate_validator.format_coordinate_clean(bounds['west'], is_longitude=True, use_dms=is_dms)
            
            self.north_edit.setText(north_text)
            self.south_edit.setText(south_text)
            self.east_edit.setText(east_text)
            self.west_edit.setText(west_text)
        finally:
            # Always clear the flag
            self.updating_fields = False
    
    def handle_database_loaded(self, database_bounds):
        """Smart selection management when a new database is loaded"""
        
        print(f"\n=== SMART SELECTION DEBUG ===")
        print(f"Database bounds: West={database_bounds['west']:.6f}, North={database_bounds['north']:.6f}, East={database_bounds['east']:.6f}, South={database_bounds['south']:.6f}")
        print(f"is_first_database_load: {self.is_first_database_load}")
        
        if self.is_first_database_load:
            # Scenario 1: First database - set selection to full database bounds
            print("DECISION: First database load: setting selection to full database bounds")
            self.set_selection_to_database_bounds(database_bounds)
            self.is_first_database_load = False
            print(f"[DEBUG] Setting is_first_database_load = False after first load")
        else:
            # Get current selection if it exists
            current_selection = self.get_current_selection()
            if current_selection:
                print(f"Current selection: West={current_selection['west']:.6f}, North={current_selection['north']:.6f}, East={current_selection['east']:.6f}, South={current_selection['south']:.6f}")
            else:
                print(f"Current selection: None")
            
            if not current_selection:
                # No current selection - treat like first load
                print("DECISION: No current selection: setting to database bounds")
                self.set_selection_to_database_bounds(database_bounds)
            elif not self.databases_overlap(database_bounds, current_selection):
                # Scenario 2: No overlap between databases - set selection to new database bounds
                print("DECISION: No overlap with previous selection: setting to new database bounds")
                self.set_selection_to_database_bounds(database_bounds)
            elif self.database_encompasses_selection(database_bounds, current_selection):
                # Scenario 3: New database encompasses current selection - keep selection, snap to pixel grid
                print("DECISION: Database encompasses selection: keeping selection, snapping to pixel grid")
                snapped_selection = self.snap_selection_to_pixel_grid(current_selection)
                self.update_selection_display(snapped_selection)
            elif self.selection_larger_than_database(current_selection, database_bounds):
                # Scenario 4: Current selection larger than new database - use database bounds
                print("DECISION: Selection larger than database: setting to database bounds")
                
                # Debug the size calculation
                sel_width = abs(current_selection['east'] - current_selection['west'])
                sel_height = abs(current_selection['north'] - current_selection['south'])
                db_width = abs(database_bounds['east'] - database_bounds['west'])
                db_height = abs(database_bounds['north'] - database_bounds['south'])
                print(f"  Selection size: {sel_width:.3f} x {sel_height:.3f}")
                print(f"  Database size: {db_width:.3f} x {db_height:.3f}")
                print(f"  Width larger: {sel_width > db_width}, Height larger: {sel_height > db_height}")
                
                self.set_selection_to_database_bounds(database_bounds)
            else:
                # Scenario 5: Partial overlap - adjust outside corners to database boundaries
                print("DECISION: Partial overlap: adjusting selection to fit database")
                
                # Debug what the adjustment will be
                adjusted_preview = {
                    'west': max(current_selection['west'], database_bounds['west']),
                    'east': min(current_selection['east'], database_bounds['east']),
                    'south': max(current_selection['south'], database_bounds['south']),
                    'north': min(current_selection['north'], database_bounds['north'])
                }
                print(f"  Adjusted preview: West={adjusted_preview['west']:.6f}, North={adjusted_preview['north']:.6f}, East={adjusted_preview['east']:.6f}, South={adjusted_preview['south']:.6f}")
                
                adjusted_selection = self.adjust_selection_to_fit(current_selection, database_bounds)
                self.update_selection_display(adjusted_selection)
        
        final_selection = self.get_current_selection()
        if final_selection:
            print(f"Final selection: West={final_selection['west']:.6f}, North={final_selection['north']:.6f}, East={final_selection['east']:.6f}, South={final_selection['south']:.6f}")
        else:
            print(f"Final selection: None")
        print(f"==============================\n")
    
    def get_current_selection(self):
        """Get current selection bounds from coordinate fields or world map"""
        # Try to get from world map first
        if hasattr(self.world_map, 'selection_rectangles') and self.world_map.selection_rectangles:
            return self.world_map.selection_rectangles[0]
        
        # Try to parse from coordinate fields
        try:
            north_text = self.north_edit.text().strip()
            south_text = self.south_edit.text().strip()
            east_text = self.east_edit.text().strip()
            west_text = self.west_edit.text().strip()
            
            if not all([north_text, south_text, east_text, west_text]):
                return None  # Empty fields
            
            # Parse coordinates
            north = self.coordinate_converter.dms_to_float(north_text) if self.dms_radio.isChecked() else float(north_text)
            south = self.coordinate_converter.dms_to_float(south_text) if self.dms_radio.isChecked() else float(south_text)
            east = self.coordinate_converter.dms_to_float(east_text) if self.dms_radio.isChecked() else float(east_text)
            west = self.coordinate_converter.dms_to_float(west_text) if self.dms_radio.isChecked() else float(west_text)
            
            return {'north': north, 'south': south, 'east': east, 'west': west}
        except (ValueError, AttributeError):
            return None
    
    def set_selection_to_database_bounds(self, database_bounds):
        """Set selection to full database bounds and snap to pixel grid"""
        # Snap to pixel grid (database boundaries should align with pixel grid)
        snapped_bounds = self.snap_selection_to_pixel_grid(database_bounds)
        self.update_selection_display(snapped_bounds)
    
    def databases_overlap(self, database_bounds, selection_bounds):
        """Check if database and current selection have any overlap"""
        # Two rectangles overlap if they intersect in both x and y dimensions
        # No overlap if one is completely to the left, right, above, or below the other
        no_overlap = (database_bounds['east'] <= selection_bounds['west'] or      # Database is completely west of selection
                     database_bounds['west'] >= selection_bounds['east'] or       # Database is completely east of selection  
                     database_bounds['north'] <= selection_bounds['south'] or     # Database is completely south of selection
                     database_bounds['south'] >= selection_bounds['north'])       # Database is completely north of selection
        
        return not no_overlap
    
    def database_encompasses_selection(self, database_bounds, selection_bounds):
        """Check if database completely encompasses the current selection"""
        return (database_bounds['west'] <= selection_bounds['west'] and
                database_bounds['east'] >= selection_bounds['east'] and
                database_bounds['south'] <= selection_bounds['south'] and
                database_bounds['north'] >= selection_bounds['north'])
    
    def selection_larger_than_database(self, selection_bounds, database_bounds):
        """Check if current selection is larger than the new database"""
        selection_width = abs(selection_bounds['east'] - selection_bounds['west'])
        selection_height = abs(selection_bounds['north'] - selection_bounds['south'])
        database_width = abs(database_bounds['east'] - database_bounds['west'])
        database_height = abs(database_bounds['north'] - database_bounds['south'])
        
        # Selection is only "larger" if BOTH dimensions are larger
        # This ensures we only replace selection when it's completely outside the database
        return (selection_width > database_width and selection_height > database_height)
    
    def adjust_selection_to_fit(self, selection_bounds, database_bounds):
        """Adjust selection corners that fall outside database to database boundaries"""
        adjusted = selection_bounds.copy()
        
        # Adjust each boundary to fit within database bounds
        adjusted['west'] = max(selection_bounds['west'], database_bounds['west'])
        adjusted['east'] = min(selection_bounds['east'], database_bounds['east'])
        adjusted['south'] = max(selection_bounds['south'], database_bounds['south'])
        adjusted['north'] = min(selection_bounds['north'], database_bounds['north'])
        
        # Snap the adjusted selection to pixel grid
        return self.snap_selection_to_pixel_grid(adjusted)
    
    def snap_selection_to_pixel_grid(self, bounds):
        """Snap selection bounds to pixel grid boundaries"""
        return self.world_map.snap_bounds_to_pixel_grid(bounds)
    
    def update_selection_display(self, bounds):
        """Update both world map selection and coordinate fields"""
        # Update world map selection rectangles
        self.world_map.update_selection_rectangles(
            bounds['west'], bounds['east'], bounds['south'], bounds['north']
        )
        
        # Update coordinate fields
        self.update_coordinate_fields(bounds)
        
        # Trigger map redraw
        self.world_map.update()
        
        # Emit selection change signal
        self.selection_changed.emit(bounds)