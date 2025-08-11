#!/usr/bin/env python3
"""
Interactive Color Ramp Widget
A vertical gradient editor widget that recreates the TopoToImage color ramp functionality
"""

import sys
from typing import List, Optional, Tuple
from dataclasses import dataclass
import math

try:
    from PyQt6.QtWidgets import QWidget, QApplication
    from PyQt6.QtCore import Qt, QRect, pyqtSignal, QPointF
    from PyQt6.QtGui import (QPainter, QColor, QLinearGradient, QPen, QBrush, 
                             QMouseEvent, QPaintEvent, QCursor)
except ImportError:
    print("PyQt6 not found. Installing...")
    import os
    os.system("pip install PyQt6")
    from PyQt6.QtWidgets import QWidget, QApplication
    from PyQt6.QtCore import Qt, QRect, pyqtSignal, QPointF
    from PyQt6.QtGui import (QPainter, QColor, QLinearGradient, QPen, QBrush, 
                             QMouseEvent, QPaintEvent, QCursor)


@dataclass
class GradientPoint:
    """Represents a single gradient point with elevation and color"""
    elevation: float
    color: QColor
    y_position: float  # Relative position (0.0 to 1.0) along the ramp
    point_id: int = 0  # Unique identifier for tracking points through reordering


class InteractiveColorRamp(QWidget):
    """
    Interactive vertical color ramp widget based on TopoToImage functionality.
    
    Features:
    - Vertical gradient display
    - Draggable color points
    - Click to add new points
    - Drag off ramp to delete points
    - Real-time gradient updates
    """
    
    # Signals
    point_selected = pyqtSignal(int)  # Emitted when a point is selected (point index)
    point_changed = pyqtSignal(int, float, QColor)  # Emitted when point elevation/color changes
    point_added = pyqtSignal(int)  # Emitted when a new point is added
    point_deleted = pyqtSignal(int)  # Emitted when a point is deleted
    point_double_clicked = pyqtSignal(int)  # Emitted when a point is double-clicked (point index)
    gradient_updated = pyqtSignal()  # Emitted when the gradient changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Widget properties
        self.setFixedSize(62, 551)  # Wider widget as requested
        self.setMouseTracking(True)
        
        # Gradient configuration
        self.min_elevation = 0.0
        self.max_elevation = 1000.0
        self.units_mode = 'meters'  # 'percent', 'feet', or 'meters'
        self.gradient_type = 'gradient'  # 'gradient', 'posterized', etc.
        self.gradient_points: List[GradientPoint] = []
        
        # Interaction state
        self.selected_point_index = -1
        self.selected_point_id = -1  # ID of the currently selected point
        self.dragging_point = False
        self.drag_start_pos = None
        self.drag_threshold = 5  # Pixels before drag starts
        self.delete_zone_entry_count = 0  # Counter for frames spent in delete zone
        self.delete_confirmation_threshold = 5  # Frames required in delete zone before deletion
        self.next_point_id = 1  # Counter for generating unique point IDs
        
        # Pending deletion state for drag-to-delete behavior
        self.pending_deletion_index = -1  # Index of point pending deletion (-1 = none)
        self.pending_deletion_original_elevation = 0.0  # Original elevation to restore if drag cancelled
        
        # Visual properties
        self.point_radius = 7  # 14px diameter circles (7px radius)
        self.selected_point_radius = 9  # 18px diameter for selected point (9px radius)
        self.point_handle_width = 24  # Space for circles plus margin
        self.border_color = QColor(204, 204, 204)  # #CCCCCC
        self.background_color = None  # Transparent background to blend with parent
        self.selected_point_outline = QColor(0, 0, 0)  # Black outline for selected point
        self.point_outline_color = QColor(0, 0, 0)  # Black outline for all points
        self.connection_line_color = QColor(0, 0, 0)  # Black connection lines
        
        # Initialize with default gradient (blue to red)
        self.initialize_default_gradient()
        
        # Set cursor
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Set transparent background to blend with parent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    
    def initialize_default_gradient(self):
        """Initialize with a simple blue-to-red gradient"""
        self.gradient_points = [
            GradientPoint(self.min_elevation, QColor(0, 0, 255), 0.0, self._get_next_point_id()),  # Blue at bottom
            GradientPoint(self.max_elevation, QColor(255, 0, 0), 1.0, self._get_next_point_id())   # Red at top
        ]
        self._reorder_points_by_elevation()
        self.selected_point_index = 0
        self.selected_point_id = self.gradient_points[0].point_id if self.gradient_points else -1
    
    def set_elevation_range(self, min_elev: float, max_elev: float):
        """Update the elevation range and recalculate point positions"""
        self.min_elevation = min_elev
        self.max_elevation = max_elev
        
        # Recalculate y positions for existing points based on their elevations
        for point in self.gradient_points:
            point.y_position = self.elevation_to_y_position(point.elevation)
        
        self.update()
        self.gradient_updated.emit()
    
    def set_elevation_range_preserve_positions(self, min_elev: float, max_elev: float):
        """Update the elevation range while preserving visual point positions"""
        self.min_elevation = min_elev
        self.max_elevation = max_elev
        
        # PRESERVE visual positions - recalculate elevations from existing y_positions
        for point in self.gradient_points:
            point.elevation = self.y_position_to_elevation(point.y_position)
        
        self.update()
        self.gradient_updated.emit()
    
    def set_units_mode(self, units_mode: str):
        """Set the units mode ('percent', 'feet', or 'meters')"""
        self.units_mode = units_mode
        # Trigger a repaint to reflect any visual changes
        self.update()
    
    def set_gradient_type(self, gradient_type: str):
        """Set the gradient type ('gradient', 'posterized', etc.)"""
        self.gradient_type = gradient_type
        # Trigger a repaint to update the gradient display
        self.update()
    
    def _get_next_point_id(self) -> int:
        """Get the next unique point ID"""
        point_id = self.next_point_id
        self.next_point_id += 1
        return point_id
    
    def _reorder_points_by_elevation(self):
        """Reorder gradient points by elevation (low to high) and update selected index"""
        if not self.gradient_points:
            return
        
        # Store the currently selected point ID
        selected_id = self.selected_point_id
        
        # Sort points by elevation (lowest to highest)
        self.gradient_points.sort(key=lambda p: p.elevation)
        
        # Update selected index to track the moved point
        self.selected_point_index = -1
        for i, point in enumerate(self.gradient_points):
            if point.point_id == selected_id:
                self.selected_point_index = i
                break
        
        # If no point was selected or the selected point was deleted, select the first point
        if self.selected_point_index == -1 and self.gradient_points:
            self.selected_point_index = 0
            self.selected_point_id = self.gradient_points[0].point_id
    
    def load_gradient_data(self, gradient_data):
        """Load gradient data from color stops list or full gradient data"""
        try:
            # Clear existing gradient points
            self.gradient_points = []
            self.selected_point_index = -1
            
            # Handle both old format (just color_stops list) and new format (full gradient dict)
            if isinstance(gradient_data, list):
                # Old format: just color stops
                color_stops = gradient_data
                self.below_gradient_color = None
                self.no_data_color = None
                self.gradient_type = "gradient"
            else:
                # New format: full gradient data
                color_stops = gradient_data.get('color_stops', [])
                self.below_gradient_color = gradient_data.get('below_gradient_color')  # "Above Posterized" color  
                self.no_data_color = gradient_data.get('no_data_color')  # No data color
                # Check both 'gradient_type' and 'type' for compatibility  
                self.gradient_type = gradient_data.get('gradient_type', gradient_data.get('type', 'gradient'))
            
            # Sort color stops by position to ensure correct order
            sorted_stops = sorted(color_stops, key=lambda stop: stop.get('position', 0.0))
            
            # Create gradient points from color stops
            for stop in sorted_stops:
                # Get color components
                red = stop.get('red', 0)
                green = stop.get('green', 0) 
                blue = stop.get('blue', 0)
                alpha = stop.get('alpha', 255)
                
                # Create QColor
                color = QColor(red, green, blue, alpha)
                
                # Use provided elevation if available, otherwise calculate from position
                if 'elevation' in stop and stop['elevation'] is not None:
                    elevation = stop['elevation']
                else:
                    # Calculate elevation from position (0.0-1.0) within current range
                    # Position 0.0 = TOP of ramp = MAX elevation
                    # Position 1.0 = BOTTOM of ramp = MIN elevation
                    position = stop.get('position', 0.0)
                    elevation = self.max_elevation - position * (self.max_elevation - self.min_elevation)
                
                # Create gradient point with unique ID
                y_position = self.elevation_to_y_position(elevation)
                gradient_point = GradientPoint(elevation, color, y_position, self._get_next_point_id())
                self.gradient_points.append(gradient_point)
            
            # Reorder points by elevation (low to high) for consistent numbering
            self._reorder_points_by_elevation()
            
            # Select first point if any points exist (lowest elevation = point 1)
            if self.gradient_points:
                self.selected_point_index = 0
                self.selected_point_id = self.gradient_points[0].point_id
                self.point_selected.emit(0)
            
            # Trigger repaint and update
            self.update()
            self.gradient_updated.emit()
            
        except Exception as e:
            print(f"❌ Error loading gradient data into color ramp: {e}")
            # Fallback to default gradient if loading fails
            self.initialize_default_gradient()
    
    def elevation_to_y_position(self, elevation: float) -> float:
        """Convert elevation to y position (0.0 = top, 1.0 = bottom)"""
        if self.max_elevation == self.min_elevation:
            return 0.5
        
        # Normalize elevation to 0-1 range, then invert for display (higher elevation = top)
        normalized = (elevation - self.min_elevation) / (self.max_elevation - self.min_elevation)
        y_position = 1.0 - normalized  # Invert so high elevation is at top
        
        # Ensure result is within valid range [0.0, 1.0]
        return max(0.0, min(1.0, y_position))
    
    def y_position_to_elevation(self, y_position: float) -> float:
        """Convert y position (0.0 = top, 1.0 = bottom) to elevation"""
        # Invert y position and convert to elevation
        normalized = 1.0 - y_position
        return self.min_elevation + normalized * (self.max_elevation - self.min_elevation)
    
    def pixel_to_y_position(self, pixel_y: int) -> float:
        """Convert pixel Y coordinate to relative position (0.0 to 1.0)"""
        ramp_height = self.height() - 20  # Leave 10px margin top and bottom
        ramp_start_y = 10
        
        if pixel_y < ramp_start_y:
            return 0.0
        elif pixel_y > ramp_start_y + ramp_height:
            return 1.0
        else:
            y_pos = (pixel_y - ramp_start_y) / ramp_height
            # Ensure result is within valid range [0.0, 1.0]
            return max(0.0, min(1.0, y_pos))
    
    def y_position_to_pixel(self, y_position: float) -> int:
        """Convert relative position (0.0 to 1.0) to pixel Y coordinate"""
        ramp_height = self.height() - 20  # Leave 10px margin top and bottom
        ramp_start_y = 10
        # Ensure y_position is within valid range [0.0, 1.0]
        clamped_y = max(0.0, min(1.0, y_position))
        return int(ramp_start_y + clamped_y * ramp_height)
    
    def find_point_at_position(self, pos: QPointF) -> int:
        """Find gradient point at given position, return index or -1"""
        for i, point in enumerate(self.gradient_points):
            point_y = self.y_position_to_pixel(point.y_position)
            
            # Use appropriate radius based on selection state
            radius = self.selected_point_radius if i == self.selected_point_index else self.point_radius
            circle_center_x = int(self.width() - radius - 3)
            circle_center_y = int(point_y)
            
            # Check if mouse is within the circular point (distance from center)
            dx = pos.x() - circle_center_x
            dy = pos.y() - circle_center_y
            distance_squared = dx * dx + dy * dy
            
            if distance_squared <= radius * radius:
                return i
        
        return -1
    
    def add_point_at_position(self, y_position: float) -> int:
        """Add a new gradient point at the specified y position"""
        elevation = self.y_position_to_elevation(y_position)
        
        # Interpolate color at this position
        color = self.interpolate_color_at_position(y_position)
        
        # Create new point with unique ID
        new_point = GradientPoint(elevation, color, y_position, self._get_next_point_id())
        self.gradient_points.append(new_point)
        
        # Reorder points by elevation and update selection
        self._reorder_points_by_elevation()
        
        # Find the new point and select it
        for i, point in enumerate(self.gradient_points):
            if point.point_id == new_point.point_id:
                self.selected_point_index = i
                self.selected_point_id = new_point.point_id
                break
        
        self.update()
        self.point_added.emit(self.selected_point_index)
        self.gradient_updated.emit()
        
        return self.selected_point_index
    
    def remove_point(self, index: int):
        """Remove a gradient point (but keep at least 2 points)"""
        if len(self.gradient_points) <= 2 or index < 0 or index >= len(self.gradient_points):
            return
        
        # Store the ID of the point being removed
        removed_point_id = self.gradient_points[index].point_id
        
        # Remove the point
        self.gradient_points.pop(index)
        
        # If we removed the selected point, select a nearby point
        if self.selected_point_id == removed_point_id:
            # Try to select the point at the same index, or the previous one if we're at the end
            new_index = min(index, len(self.gradient_points) - 1)
            self.selected_point_index = new_index
            self.selected_point_id = self.gradient_points[new_index].point_id if self.gradient_points else -1
        else:
            # Update selected index to track the moved point after removal
            for i, point in enumerate(self.gradient_points):
                if point.point_id == self.selected_point_id:
                    self.selected_point_index = i
                    break
        
        self.update()
        self.point_deleted.emit(index)
        self.gradient_updated.emit()
    
    def set_num_colors(self, num_colors: int):
        """Set the number of gradient colors by adding or removing points"""
        if num_colors < 2:
            return  # Minimum 2 points required
            
        current_count = len(self.gradient_points)
        
        if num_colors == current_count:
            return  # No change needed
            
        if num_colors < current_count:
            # Remove points from the top (highest elevation)
            points_to_remove = current_count - num_colors
            
            # Sort points by elevation (descending) to identify highest points
            sorted_by_elevation = sorted(enumerate(self.gradient_points), 
                                       key=lambda x: x[1].elevation, reverse=True)
            
            # Get indices of points to remove (highest elevation points)
            indices_to_remove = [idx for idx, _ in sorted_by_elevation[:points_to_remove]]
            
            # Remove points in reverse order to maintain indices
            for idx in sorted(indices_to_remove, reverse=True):
                self.gradient_points.pop(idx)
                
            # Adjust selected point if it was removed
            if self.selected_point_index in indices_to_remove:
                # Find the highest remaining point and select it
                if self.gradient_points:
                    highest_remaining = max(enumerate(self.gradient_points), 
                                          key=lambda x: x[1].elevation)
                    self.selected_point_index = highest_remaining[0]
                else:
                    self.selected_point_index = 0
            else:
                # Adjust selected index for removed points
                removed_before_selected = sum(1 for idx in indices_to_remove 
                                            if idx < self.selected_point_index)
                self.selected_point_index = max(0, self.selected_point_index - removed_before_selected)
                
        else:
            # Add points between top two points
            points_to_add = num_colors - current_count
            
            if len(self.gradient_points) < 2:
                return  # Need at least 2 points to interpolate between
                
            # Sort points by elevation to find top two
            sorted_by_elevation = sorted(self.gradient_points, key=lambda p: p.elevation, reverse=True)
            top_point = sorted_by_elevation[0]
            second_top_point = sorted_by_elevation[1]
            
            # Calculate positions between the top two points
            for i in range(points_to_add):
                # Calculate interpolation factor (spread points evenly)
                factor = (i + 1) / (points_to_add + 1)
                
                # Interpolate elevation
                new_elevation = second_top_point.elevation + factor * (top_point.elevation - second_top_point.elevation)
                
                # Calculate y position from elevation
                new_y_position = 1.0 - ((new_elevation - self.min_elevation) / 
                                       (self.max_elevation - self.min_elevation))
                
                # Interpolate color
                new_color = self.interpolate_color_between_points(second_top_point, top_point, factor)
                
                # Create new point with unique ID
                new_point = GradientPoint(
                    elevation=new_elevation,
                    color=new_color,
                    y_position=new_y_position,
                    point_id=self._get_next_point_id()
                )
                
                # Insert in correct position to maintain elevation order
                insert_idx = 0
                for j, existing_point in enumerate(self.gradient_points):
                    if new_elevation > existing_point.elevation:
                        insert_idx = j
                        break
                    insert_idx = j + 1
                
                self.gradient_points.insert(insert_idx, new_point)
                
                # Update selected point ID tracking after insertion
                if self.selected_point_index >= 0:
                    # Find the selected point's new index after insertion
                    for i, point in enumerate(self.gradient_points):
                        if point.point_id == self.selected_point_id:
                            self.selected_point_index = i
                            break
        
        # Emit signals for all changes
        self.update()
        self.gradient_updated.emit()
    
    def interpolate_color_between_points(self, point1: GradientPoint, point2: GradientPoint, factor: float) -> QColor:
        """Interpolate color between two gradient points"""
        r1, g1, b1 = point1.color.red(), point1.color.green(), point1.color.blue()
        r2, g2, b2 = point2.color.red(), point2.color.green(), point2.color.blue()
        
        r = int(r1 + factor * (r2 - r1))
        g = int(g1 + factor * (g2 - g1))
        b = int(b1 + factor * (b2 - b1))
        
        return QColor(r, g, b)
    
    def interpolate_color_at_position(self, y_position: float) -> QColor:
        """Interpolate color at given y position using existing gradient points"""
        if len(self.gradient_points) == 0:
            return QColor(128, 128, 128)  # Gray default
        
        if len(self.gradient_points) == 1:
            return self.gradient_points[0].color
        
        # Sort points by y position for interpolation
        sorted_points = sorted(self.gradient_points, key=lambda p: p.y_position)
        
        # Find the two points that bracket this position
        if y_position <= sorted_points[0].y_position:
            return sorted_points[0].color
        
        if y_position >= sorted_points[-1].y_position:
            return sorted_points[-1].color
        
        # Find bracketing points
        for i in range(len(sorted_points) - 1):
            point1 = sorted_points[i]
            point2 = sorted_points[i + 1]
            
            if point1.y_position <= y_position <= point2.y_position:
                # Interpolate between these two points
                if point1.y_position == point2.y_position:
                    return point1.color
                
                t = (y_position - point1.y_position) / (point2.y_position - point1.y_position)
                
                # Linear interpolation in RGB space
                r = int(point1.color.red() + t * (point2.color.red() - point1.color.red()))
                g = int(point1.color.green() + t * (point2.color.green() - point1.color.green()))
                b = int(point1.color.blue() + t * (point2.color.blue() - point1.color.blue()))
                
                return QColor(r, g, b)
        
        return QColor(128, 128, 128)  # Fallback gray
    
    def update_point_elevation(self, index: int, elevation: float):
        """Update the elevation of a specific point and reorder if necessary"""
        if 0 <= index < len(self.gradient_points):
            # Store the ID of the point being updated
            point_id = self.gradient_points[index].point_id
            
            # Update the point's elevation and position
            self.gradient_points[index].elevation = elevation
            self.gradient_points[index].y_position = self.elevation_to_y_position(elevation)
            
            # Update selected point ID to track the moved point
            self.selected_point_id = point_id
            
            # Reorder points by elevation and update selected index
            self._reorder_points_by_elevation()
            
            self.update()
            self.point_changed.emit(self.selected_point_index, elevation, self.gradient_points[self.selected_point_index].color)
            self.gradient_updated.emit()
    
    def update_point_color(self, index: int, color: QColor):
        """Update the color of a specific point"""
        if 0 <= index < len(self.gradient_points):
            self.gradient_points[index].color = color
            self.update()
            self.point_changed.emit(index, self.gradient_points[index].elevation, color)
            self.gradient_updated.emit()
    
    def get_selected_point(self) -> Optional[GradientPoint]:
        """Get the currently selected gradient point"""
        if 0 <= self.selected_point_index < len(self.gradient_points):
            return self.gradient_points[self.selected_point_index]
        return None
    
    def select_point(self, index: int):
        """Select a specific gradient point"""
        if 0 <= index < len(self.gradient_points):
            self.selected_point_index = index
            self.update()
            self.point_selected.emit(index)
    
    def paintEvent(self, event: QPaintEvent):
        """Paint the color ramp and gradient points"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # No border or background - blend with parent
        
        # Draw gradient
        self.draw_gradient(painter)
        
        # Draw gradient points
        self.draw_gradient_points(painter)
    
    def draw_gradient(self, painter: QPainter):
        """Draw the color gradient (smooth or posterized based on gradient_type)"""
        if len(self.gradient_points) < 2:
            return
        
        # Create gradient area (narrower to leave space between ramp and circles)
        gradient_width = self.width() - self.point_handle_width - 6  # Extra 6px gap
        gradient_rect = QRect(0, 10, gradient_width, self.height() - 20)
        
        if self.gradient_type in ['posterized', 'shading_and_posterized']:
            self.draw_posterized_gradient(painter, gradient_rect)
        else:
            self.draw_smooth_gradient(painter, gradient_rect)
    
    def draw_smooth_gradient(self, painter: QPainter, gradient_rect: QRect):
        """Draw smooth gradient with color blending"""
        # Create linear gradient
        gradient = QLinearGradient(0, gradient_rect.top(), 0, gradient_rect.bottom())
        
        # Sort points by y position for gradient creation
        sorted_points = sorted(self.gradient_points, key=lambda p: p.y_position)
        
        for point in sorted_points:
            # Ensure position is within valid range [0.0, 1.0]
            position = max(0.0, min(1.0, point.y_position))
            gradient.setColorAt(position, point.color)
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(gradient_rect)
    
    def draw_posterized_gradient(self, painter: QPainter, gradient_rect: QRect):
        """Draw posterized gradient with solid color bands - each color extends downward from its point"""
        # Sort points by y position
        sorted_points = sorted(self.gradient_points, key=lambda p: p.y_position)
        
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Draw "Above Posterized" color at the top if it exists and is for posterized gradients
        if (hasattr(self, 'below_gradient_color') and self.below_gradient_color and 
            hasattr(self, 'gradient_type') and self.gradient_type in ['posterized', 'shading_and_posterized']):
            
            # Find the topmost point (smallest y_position = highest elevation)
            if sorted_points:
                topmost_point = sorted_points[0]
                top_band_bottom = int(gradient_rect.top() + topmost_point.y_position * gradient_rect.height())
                
                # Draw "Above Posterized" color from top of gradient to topmost point
                if top_band_bottom > gradient_rect.top():
                    above_posterized_color = QColor(
                        self.below_gradient_color.get('red', 0),
                        self.below_gradient_color.get('green', 0), 
                        self.below_gradient_color.get('blue', 0),
                        self.below_gradient_color.get('alpha', 255)
                    )
                    above_band_rect = QRect(
                        gradient_rect.left(), 
                        gradient_rect.top(),
                        gradient_rect.width(), 
                        top_band_bottom - gradient_rect.top()
                    )
                    painter.setBrush(QBrush(above_posterized_color))
                    painter.drawRect(above_band_rect)
        
        # NEW APPROACH: Each color extends downward from its point to the next point
        # This matches the terrain preview behavior where each color extends "upward" in elevation
        for i in range(len(sorted_points)):
            current_point = sorted_points[i]
            
            # Calculate the band boundaries - each color extends FROM its position TO next position
            band_top = int(gradient_rect.top() + current_point.y_position * gradient_rect.height())
            
            if i == len(sorted_points) - 1:
                # Last point: extends from its position to bottom of gradient
                band_bottom = gradient_rect.bottom()
            else:
                # Other points: extend from this position to next point's position
                next_point = sorted_points[i + 1]
                band_bottom = int(gradient_rect.top() + next_point.y_position * gradient_rect.height())
            
            # Only draw band if it has height (skip if this point is at same position as next)
            if band_bottom > band_top:
                band_rect = QRect(gradient_rect.left(), band_top, gradient_rect.width(), band_bottom - band_top)
                painter.setBrush(QBrush(current_point.color))
                painter.drawRect(band_rect)
    
    def draw_gradient_points(self, painter: QPainter):
        """Draw the interactive gradient points"""
        for i, point in enumerate(self.gradient_points):
            # Skip drawing points that are pending deletion
            if i == self.pending_deletion_index:
                continue
            self.draw_single_point(painter, i, point)
    
    def draw_single_point(self, painter: QPainter, index: int, point: GradientPoint):
        """Draw a single gradient point as a circle with gradient color and connection line"""
        point_y = self.y_position_to_pixel(point.y_position)
        
        # Determine circle size and position based on selection state
        is_selected = index == self.selected_point_index
        radius = self.selected_point_radius if is_selected else self.point_radius
        circle_center_x = int(self.width() - radius - 3)  # Ensure integer coordinates
        circle_center_y = int(point_y)
        
        # Calculate gradient area edge for connection line
        gradient_width = self.width() - self.point_handle_width - 6
        gradient_right_edge = int(gradient_width)
        
        # Draw connection line from gradient edge to left side of circle
        line_start_x = gradient_right_edge
        line_end_x = int(circle_center_x - radius)
        painter.setPen(QPen(self.connection_line_color, 1))
        painter.drawLine(line_start_x, circle_center_y, line_end_x, circle_center_y)
        
        # Use the gradient color at this point's position for the fill
        fill_color = point.color
        
        # Determine outline properties
        outline_color = self.point_outline_color
        outline_width = 2 if is_selected else 1
        
        # Draw the circle with integer coordinates
        painter.setBrush(QBrush(fill_color))
        painter.setPen(QPen(outline_color, outline_width))
        painter.drawEllipse(
            int(circle_center_x - radius),
            int(circle_center_y - radius),
            int(radius * 2),
            int(radius * 2)
        )
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            
            # Check if clicking on an existing point
            point_index = self.find_point_at_position(pos)
            
            if point_index >= 0:
                # Clicking on existing point - select it
                self.selected_point_index = point_index
                self.dragging_point = False  # Will start dragging on mouse move
                self.drag_start_pos = pos
                self.update()
                self.point_selected.emit(point_index)
            else:
                # Check if clicking on the gradient area (not on point circles)
                gradient_width = self.width() - self.point_handle_width - 6
                if pos.x() < gradient_width:
                    # Clicking on gradient - add new point
                    y_position = self.pixel_to_y_position(pos.y())
                    self.add_point_at_position(y_position)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move events"""
        pos = event.position()
        
        if event.buttons() == Qt.MouseButton.LeftButton and self.selected_point_index >= 0:
            # Handle dragging
            if not self.dragging_point and self.drag_start_pos:
                # Check if we've moved enough to start dragging
                drag_distance = (pos - self.drag_start_pos).manhattanLength()
                if drag_distance > self.drag_threshold:
                    self.dragging_point = True
                    self.delete_zone_entry_count = 0  # Reset delete counter when dragging starts
            
            if self.dragging_point:
                # Update point position
                new_y_position = self.pixel_to_y_position(pos.y())
                new_elevation = self.y_position_to_elevation(new_y_position)
                
                # Check if dragged far off the widget (pending delete point)
                delete_threshold = 80  # Must drag 80+ pixels away to enter delete zone
                in_delete_zone = pos.x() < -delete_threshold or pos.x() > self.width() + delete_threshold
                
                if in_delete_zone:
                    self.delete_zone_entry_count += 1
                    # Enter pending deletion state if sustained in delete zone AND we have more than 2 points
                    if (self.delete_zone_entry_count >= self.delete_confirmation_threshold and 
                        len(self.gradient_points) > 2 and 
                        self.pending_deletion_index == -1):  # Only if not already pending
                        # Enter pending deletion state
                        self.pending_deletion_index = self.selected_point_index
                        self.pending_deletion_original_elevation = self.gradient_points[self.selected_point_index].elevation
                        print(f"🗑️ Point {self.selected_point_index} entering pending deletion state")
                        self.update()  # Redraw to hide the point
                else:
                    # Reset delete counter when back in safe zone
                    self.delete_zone_entry_count = 0
                    
                    # If we were pending deletion but moved back to safe zone, restore the point
                    if self.pending_deletion_index == self.selected_point_index:
                        print(f"🔄 Point {self.selected_point_index} restored from pending deletion")
                        self.pending_deletion_index = -1
                        self.pending_deletion_original_elevation = 0.0
                        self.update()  # Redraw to show the point
                
                # Update point position (only if not pending deletion or if restoring)
                if self.pending_deletion_index != self.selected_point_index:
                    self.update_point_elevation(self.selected_point_index, new_elevation)
        else:
            # Update cursor based on hover state
            point_index = self.find_point_at_position(pos)
            if point_index >= 0:
                self.setCursor(QCursor(Qt.CursorShape.SizeVerCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release events"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if we need to finalize a pending deletion
            if self.pending_deletion_index >= 0:
                # Point was dragged to delete zone - actually delete it now
                print(f"🗑️ Finalizing deletion of point {self.pending_deletion_index}")
                self.remove_point(self.pending_deletion_index)
                self.pending_deletion_index = -1
                self.pending_deletion_original_elevation = 0.0
            
            # Reset drag state
            self.dragging_point = False
            self.drag_start_pos = None
            self.delete_zone_entry_count = 0  # Reset delete counter on release
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle mouse double-click events"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            
            # Check if double-clicking on an existing point
            point_index = self.find_point_at_position(pos)
            
            if point_index >= 0:
                # Double-clicking on existing point - emit signal to open color dialog
                print(f"🎨 Double-clicked on gradient point {point_index}")
                self.point_double_clicked.emit(point_index)
            else:
                # Double-clicking on gradient area - let the normal click handler manage point addition
                # (Call the parent's mouseDoubleClickEvent to allow normal processing)
                super().mouseDoubleClickEvent(event)
    
    def reset_pending_deletion(self):
        """Reset the pending deletion state"""
        if self.pending_deletion_index >= 0:
            print(f"🔄 Resetting pending deletion state for point {self.pending_deletion_index}")
            self.pending_deletion_index = -1
            self.pending_deletion_original_elevation = 0.0
            self.update()  # Redraw to show all points


# Test application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Create test window
    ramp = InteractiveColorRamp()
    ramp.show()
    
    # Connect signals for testing
    def on_point_selected(index):
        print(f"Point selected: {index}")
    
    def on_point_changed(index, elevation, color):
        print(f"Point {index} changed: elevation={elevation}, color={color.name()}")
    
    def on_point_added(index):
        print(f"Point added at index: {index}")
    
    def on_point_deleted(index):
        print(f"Point deleted at index: {index}")
    
    ramp.point_selected.connect(on_point_selected)
    ramp.point_changed.connect(on_point_changed)
    ramp.point_added.connect(on_point_added)
    ramp.point_deleted.connect(on_point_deleted)
    
    sys.exit(app.exec())