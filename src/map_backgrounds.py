#!/usr/bin/env python3
"""
DEM Visualizer - Map Background System
Handles world map backgrounds with support for SVG, PNG, and database-specific maps.
"""

import json
import sys
from pathlib import Path
from typing import Optional, Dict, Tuple
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QSizeF
from PyQt6.QtGui import QPainter, QPixmap, QPen, QBrush, QColor
from PyQt6.QtSvg import QSvgRenderer

def get_writable_data_path(relative_path):
    """Get absolute path to writable data location, works for dev and PyInstaller bundled app"""
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle - use writable home directory location
        data_dir = Path.home() / "TopoToImage_Data"
        data_dir.mkdir(exist_ok=True)
        return data_dir / relative_path
    else:
        # Running in development - use project assets directory (writable)
        project_root = Path(__file__).parent.parent  # Go up from src/ to project root
        return project_root / "assets" / relative_path

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller bundled app"""
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle
        return Path(sys._MEIPASS) / relative_path
    else:
        # Running in development - determine correct path based on resource type
        project_root = Path(__file__).parent.parent  # Go up from src/ to project root
        
        # Handle different resource types
        if relative_path.endswith('.ui'):
            return project_root / "ui" / relative_path
        elif relative_path.startswith('maps/') or relative_path == 'maps':
            return project_root / "assets" / relative_path
        elif relative_path.startswith('gradients/') or relative_path == 'gradients.json':
            return project_root / "assets" / "gradients" / relative_path.replace('gradients/', '')
        elif relative_path.startswith('preview_icon_databases/') or relative_path == 'preview_icon_databases':
            return project_root / "assets" / relative_path
        else:
            # Default: assume it's in assets
            return project_root / "assets" / relative_path

class MapBackgroundManager:
    """Manages map background images and database-specific overlays."""
    
    def __init__(self, config_file: Optional[Path] = None):
        # Use bundle-aware path for map backgrounds config
        self.config_file = config_file or get_writable_data_path("map_backgrounds.json")
        self.backgrounds = {}
        self.current_background = None
        self.default_background = None  # Permanent default
        self.active_database_background = None  # Temporary database-specific background
        self.load_config()
        
        # Default paths - use resource path for bundled app
        self.maps_dir = get_resource_path("maps")
        if not hasattr(sys, '_MEIPASS'):
            # Only create directory in development mode
            self.maps_dir.mkdir(exist_ok=True)
    
    def load_config(self):
        """Load map background configuration."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.backgrounds = data.get('backgrounds', {})
                    self.default_background = data.get('default_background')
                    self.current_background = self.default_background
                    
                # Always check for default_background_map.svg file
                self._check_for_default_map()
            else:
                self._create_default_config()
        except Exception as e:
            print(f"Error loading map background config: {e}")
            self._create_default_config()
    
    def save_config(self):
        """Save map background configuration."""
        try:
            data = {
                'version': '1.0',
                'default_background': self.default_background,
                'backgrounds': self.backgrounds
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving map background config: {e}")
    
    def _create_default_config(self):
        """Create default map background configuration."""
        self.backgrounds = {
            'simple_world': {
                'name': 'Simple World',
                'description': 'Basic world outline map',
                'file_path': 'maps/simple_world.svg',
                'type': 'svg',
                'projection': 'equirectangular',
                'bounds': [-180, 90, 180, -90]  # [west, north, east, south]
            },
            'natural_earth': {
                'name': 'Natural Earth',
                'description': 'Natural Earth world map',
                'file_path': 'maps/natural_earth_world.svg',
                'type': 'svg',
                'projection': 'equirectangular',
                'bounds': [-180, 90, 180, -90]
            },
        }
        
        # Check for user's preferred default map file
        default_map_path = get_resource_path('maps/default_background_map.svg')
        if default_map_path.exists():
            self.backgrounds['default_map'] = {
                'name': 'Default Background Map',
                'description': 'User-specified default world map',
                'file_path': 'maps/default_background_map.svg',
                'type': 'svg',
                'projection': 'equirectangular',
                'bounds': [-180, 90, 180, -90]
            }
            self.default_background = 'default_map'
            self.current_background = 'default_map'
        else:
            self.default_background = 'simple_world'
            self.current_background = 'simple_world'
            
        self.save_config()
    
    def _check_for_default_map(self):
        """Check for user's default background map file and add/update it."""
        default_map_path = get_resource_path('maps/default_background_map.svg')
        if default_map_path.exists():
            # Add or update the default map entry
            self.backgrounds['default_map'] = {
                'name': 'Default Background Map',
                'description': 'User-specified default world map',
                'file_path': 'maps/default_background_map.svg',
                'type': 'svg',
                'projection': 'equirectangular',
                'bounds': [-180, 90, 180, -90]
            }
            
            # Set as default background if not already set to something else
            if not self.default_background or self.default_background not in self.backgrounds:
                self.default_background = 'default_map'
                self.current_background = 'default_map'
                self.save_config()
    
    def get_background_list(self) -> Dict[str, Dict]:
        """Get list of available backgrounds."""
        return self.backgrounds.copy()
    
    def get_current_background(self) -> Optional[str]:
        """Get current background name."""
        return self.current_background
    
    def set_current_background(self, background_name: str):
        """Set current background by name."""
        if background_name in self.backgrounds:
            self.current_background = background_name
            self.save_config()
            return True
        return False
    
    def add_background(self, name: str, file_path: Path, description: str = "", 
                      background_type: str = "svg", database_type: Optional[str] = None):
        """Add a new background map."""
        self.backgrounds[name] = {
            'name': name,
            'description': description,
            'file_path': str(file_path),
            'type': background_type,
            'projection': 'equirectangular',
            'bounds': [-180, 90, 180, -90],
        }
        
        if database_type:
            self.backgrounds[name]['database_type'] = database_type
        
        self.save_config()
    
    def set_database_background(self, database_type: str, database_path: Optional[Path] = None):
        """Set background for a specific database, returns the background name used."""
        # First, check for database-specific background file in the database folder
        if database_path:
            db_specific_background = database_path / "default_database_background_map.svg"
            if db_specific_background.exists():
                # Add this background to our collection if not already present
                bg_name = f"{database_path.name}_database_background"
                self.backgrounds[bg_name] = {
                    'name': f'{database_path.name} Database Background',
                    'description': f'Database-specific background for {database_path.name}',
                    'file_path': str(db_specific_background),
                    'type': 'svg',
                    'projection': 'equirectangular',
                    'bounds': [-180, 90, 180, -90],
                    'database_type': database_type,
                    'database_specific': True
                }
                self.save_config()
                # Set as active database background (temporary)
                self.active_database_background = bg_name
                self.current_background = bg_name
                return bg_name
        
        # Second, look for database-specific backgrounds in configuration
        for name, config in self.backgrounds.items():
            if config.get('database_type') == database_type:
                self.active_database_background = name
                self.current_background = name
                return name
        
        # No database-specific background found, keep current
        return self.current_background
    
    def clear_database_background(self):
        """Clear database-specific background and return to default."""
        self.active_database_background = None
        self.current_background = self.default_background
    
    def get_background_for_database(self, database_type: str, database_path: Optional[Path] = None) -> Optional[str]:
        """Get best background for a specific database type and path (without setting it)."""
        # First, check for database-specific background file in the database folder
        if database_path:
            db_specific_background = database_path / "default_database_background_map.svg"
            if db_specific_background.exists():
                bg_name = f"{database_path.name}_database_background"
                return bg_name
        
        # Second, look for database-specific backgrounds in configuration
        for name, config in self.backgrounds.items():
            if config.get('database_type') == database_type:
                return name
        
        # Fall back to default background
        return self.default_background
    
    def get_background_path(self, background_name: Optional[str] = None) -> Optional[Path]:
        """Get file path for background."""
        name = background_name or self.current_background
        if name and name in self.backgrounds:
            file_path = self.backgrounds[name].get('file_path')
            if file_path:
                # Try both resource path (for bundled app) and regular path (for development)
                resource_path = get_resource_path(file_path)
                if resource_path.exists():
                    return resource_path
                # Fall back to regular path
                path = Path(file_path)
                if path.exists():
                    return path
        return None
    
    def use_default_map_as_primary(self):
        """Force the use of default_background_map.svg as the primary background."""
        default_map_path = get_resource_path('maps/default_background_map.svg')
        if default_map_path.exists():
            self._check_for_default_map()  # Ensure it's in the backgrounds dict
            if 'default_map' in self.backgrounds:
                self.default_background = 'default_map'
                self.current_background = 'default_map'
                self.save_config()
                return True
        return False


class WorldMapRenderer:
    """Renders world map backgrounds with geographic overlays."""
    
    def __init__(self, widget: QWidget):
        self.widget = widget
        self.background_manager = MapBackgroundManager()
        self.cached_background = None
        self.cached_size = None
        self.svg_renderer = None
    
    def set_background(self, background_name: str):
        """Set the background map."""
        if self.background_manager.set_current_background(background_name):
            self.clear_cache()
    
    def clear_cache(self):
        """Clear cached background image."""
        self.cached_background = None
        self.cached_size = None
        self.svg_renderer = None
    
    def render_background(self, painter: QPainter, widget_rect: QRectF):
        """Render background map to painter."""
        # Check if we need to regenerate cache
        current_size = (widget_rect.width(), widget_rect.height())
        if (self.cached_background is None or 
            self.cached_size != current_size):
            self._generate_background_cache(current_size)
        
        # Draw cached background
        if self.cached_background:
            if hasattr(widget_rect, 'toRect'):
                rect = widget_rect.toRect()
            else:
                rect = widget_rect  # Already a QRect
            painter.drawPixmap(rect, self.cached_background)
    
    def _generate_background_cache(self, size: Tuple[float, float]):
        """Generate cached background image."""
        width, height = int(size[0]), int(size[1])
        if width <= 0 or height <= 0:
            return
        
        # Create pixmap for caching
        self.cached_background = QPixmap(width, height)
        self.cached_background.fill(Qt.GlobalColor.white)
        self.cached_size = size
        
        painter = QPainter(self.cached_background)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get background file
        background_path = self.background_manager.get_background_path()
        
        if background_path and background_path.exists():
            self._render_background_file(painter, background_path, width, height)
        else:
            self._render_default_background(painter, width, height)
        
        painter.end()
    
    def _render_background_file(self, painter: QPainter, file_path: Path, width: int, height: int):
        """Render background from file (SVG or raster)."""
        try:
            if file_path.suffix.lower() == '.svg':
                # Render SVG
                if not self.svg_renderer or self.svg_renderer != file_path:
                    self.svg_renderer = QSvgRenderer(str(file_path))
                
                if self.svg_renderer.isValid():
                    # Scale SVG to fit widget with 2:1 aspect ratio
                    svg_rect = QRectF(0, 0, width, height)
                    self.svg_renderer.render(painter, svg_rect)
                else:
                    self._render_default_background(painter, width, height)
            
            else:
                # Load and scale raster image
                pixmap = QPixmap(str(file_path))
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        width, height, 
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    painter.drawPixmap(0, 0, scaled_pixmap)
                else:
                    self._render_default_background(painter, width, height)
                    
        except Exception as e:
            print(f"Error rendering background: {e}")
            self._render_default_background(painter, width, height)
    
    def _render_default_background(self, painter: QPainter, width: int, height: int):
        """Render default world outline when no background file is available."""
        # Light blue background (ocean)
        painter.fillRect(0, 0, width, height, QColor(200, 230, 255))
        
        # Simple continent outlines
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.setBrush(QBrush(QColor(220, 220, 180)))  # Light tan for land
        
        # Very simplified continent shapes (just for reference)
        # These are rough approximations for when no proper map is available
        
        # North America
        na_width = width * 0.25
        na_height = height * 0.4
        na_x = width * 0.15
        na_y = height * 0.15
        painter.drawEllipse(int(na_x), int(na_y), int(na_width), int(na_height))
        
        # South America  
        sa_width = width * 0.12
        sa_height = height * 0.35
        sa_x = width * 0.25
        sa_y = height * 0.45
        painter.drawEllipse(int(sa_x), int(sa_y), int(sa_width), int(sa_height))
        
        # Europe/Africa
        ea_width = width * 0.15
        ea_height = height * 0.6
        ea_x = width * 0.45
        ea_y = height * 0.15
        painter.drawEllipse(int(ea_x), int(ea_y), int(ea_width), int(ea_height))
        
        # Asia
        as_width = width * 0.25
        as_height = height * 0.4
        as_x = width * 0.55
        as_y = height * 0.15
        painter.drawEllipse(int(as_x), int(as_y), int(as_width), int(as_height))
        
        # Australia
        au_width = width * 0.08
        au_height = height * 0.15
        au_x = width * 0.72
        au_y = height * 0.65
        painter.drawEllipse(int(au_x), int(au_y), int(au_width), int(au_height))
    
    def get_available_backgrounds(self) -> Dict[str, Dict]:
        """Get list of available background maps."""
        return self.background_manager.get_background_list()
    
    def get_current_background_name(self) -> Optional[str]:
        """Get current background name."""
        return self.background_manager.get_current_background()
    
    def set_database_background(self, database_type: str, database_path: Optional[Path] = None):
        """Set background appropriate for database type and path."""
        background_name = self.background_manager.set_database_background(database_type, database_path)
        if background_name:
            self.clear_cache()
    
    def clear_database_background(self):
        """Clear database-specific background and return to default."""
        self.background_manager.clear_database_background()
        self.clear_cache()
    
    def add_background_map(self, name: str, file_path: Path, description: str = "",
                          database_type: Optional[str] = None):
        """Add a new background map."""
        self.background_manager.add_background(name, file_path, description, 
                                             file_path.suffix[1:], database_type)
        self.clear_cache()


def create_simple_world_svg():
    """Create a simple world map SVG file for testing."""
    svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="360" height="180" viewBox="-180 -90 360 180" xmlns="http://www.w3.org/2000/svg">
  <!-- Ocean background -->
  <rect x="-180" y="-90" width="360" height="180" fill="#b3d9ff" />
  
  <!-- Equator line -->
  <line x1="-180" y1="0" x2="180" y2="0" stroke="#666" stroke-width="0.5" opacity="0.5"/>
  
  <!-- Prime meridian -->
  <line x1="0" y1="-90" x2="0" y2="90" stroke="#666" stroke-width="0.5" opacity="0.5"/>
  
  <!-- Simplified continent shapes -->
  <g fill="#e6ddd4" stroke="#999" stroke-width="0.3">
    <!-- North America -->
    <path d="M -140 60 L -60 70 L -60 30 L -100 25 L -140 40 Z" />
    
    <!-- South America -->
    <path d="M -80 10 L -50 15 L -40 -50 L -70 -55 L -80 -10 Z" />
    
    <!-- Europe -->
    <path d="M -10 60 L 30 65 L 35 45 L 5 40 L -10 50 Z" />
    
    <!-- Africa -->
    <path d="M -5 35 L 40 40 L 50 -35 L 10 -40 L -5 10 Z" />
    
    <!-- Asia -->
    <path d="M 30 70 L 140 75 L 150 25 L 40 20 L 30 50 Z" />
    
    <!-- Australia -->
    <path d="M 110 -15 L 155 -10 L 150 -45 L 115 -40 Z" />
  </g>
  
  <!-- Grid lines -->
  <g stroke="#ccc" stroke-width="0.2" opacity="0.7">
    <!-- Latitude lines -->
    <line x1="-180" y1="-60" x2="180" y2="-60"/>
    <line x1="-180" y1="-30" x2="180" y2="-30"/>
    <line x1="-180" y1="30" x2="180" y2="30"/>
    <line x1="-180" y1="60" x2="180" y2="60"/>
    
    <!-- Longitude lines -->
    <line x1="-120" y1="-90" x2="-120" y2="90"/>
    <line x1="-60" y1="-90" x2="-60" y2="90"/>
    <line x1="60" y1="-90" x2="60" y2="90"/>
    <line x1="120" y1="-90" x2="120" y2="90"/>
  </g>
</svg>'''
    
    maps_dir = Path("maps")
    maps_dir.mkdir(exist_ok=True)
    
    svg_file = maps_dir / "simple_world.svg"
    with open(svg_file, 'w') as f:
        f.write(svg_content)
    
    return svg_file

if __name__ == "__main__":
    # Test the map background system
    print("=== Map Background System Test ===")
    
    # Create simple world map
    svg_file = create_simple_world_svg()
    print(f"Created simple world map: {svg_file}")
    
    # Test background manager
    manager = MapBackgroundManager()
    backgrounds = manager.get_background_list()
    
    print(f"\nAvailable backgrounds:")
    for name, config in backgrounds.items():
        print(f"  • {name}: {config['description']}")
        print(f"    File: {config['file_path']}")
        if 'database_type' in config:
            print(f"    Database: {config['database_type']}")
    
    print(f"\nCurrent background: {manager.get_current_background()}")
    print(f"GTOPO30 background: {manager.get_background_for_database('gtopo30')}")
    
    print(f"\nBackground system ready for integration!")