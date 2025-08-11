#!/usr/bin/env python3
"""
Gradient Editor Window for DEM Visualizer
Loads the gradient_editor_02.ui file and provides functionality for editing gradients
"""

import sys
import numpy as np
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QMessageBox, QColorDialog, QButtonGroup, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap, QPainter
from PyQt6 import uic
from interactive_color_ramp import InteractiveColorRamp
from terrain_renderer import TerrainRenderer
from gradient_system import GradientManager, Gradient, ColorStop
from dem_reader import DEMReader

class GradientEditorWindow(QDialog):
    """
    Gradient Editor Window that loads the gradient_editor_02.ui file
    Uses the control names from the UI file as variable names for easy reference
    """
    
    # Signal emitted when gradient is saved
    gradient_saved = pyqtSignal(dict)  # Emits the gradient data
    
    def __init__(self, parent=None, gradient_data=None, is_new_gradient=False, preview_database_path=None):
        super().__init__(parent)
        self.gradient_data = gradient_data or {}
        self.is_new_gradient = is_new_gradient
        self.preview_database_path = preview_database_path  # Use specific preview database if provided
        
        # Flag to prevent redundant preview updates during initialization
        self.updating_ui = False
        
        # Track if user is currently typing in the number of colors spinbox
        self.number_of_colors_text_being_edited = False
        
        # Timer for debouncing light direction changes
        from PyQt6.QtCore import QTimer
        self.light_direction_timer = QTimer()
        self.light_direction_timer.timeout.connect(self.update_terrain_preview)
        self.light_direction_timer.setSingleShot(True)
        
        # Internal storage for absolute elevation ranges (preserved when switching units)
        self.absolute_min_elevation_meters = 0
        self.absolute_max_elevation_meters = 1000
        
        # Terrain preview setup
        self.gradient_manager = GradientManager()
        self.terrain_renderer = TerrainRenderer(self.gradient_manager)
        self.preview_elevation_data = None
        self.load_preview_database()
        
        # Load the UI file from ui directory
        ui_file = Path(__file__).parent.parent / "ui" / "gradient_editor_02.ui"
        if not ui_file.exists():
            QMessageBox.critical(self, "Error", f"UI file not found: {ui_file}")
            return
            
        try:
            uic.loadUi(str(ui_file), self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load UI file: {e}")
            return
        
        self.setup_window()
        self.setup_interactive_color_ramp()
        self.setup_button_groups()
        self.replace_point_elevation_spinbox()
        self.connect_signals()
        self.populate_from_gradient_data()
        
        # Note: update_terrain_preview() is called at the end of populate_from_gradient_data()
        
    def setup_window(self):
        """Setup window properties"""
        if self.is_new_gradient:
            self.setWindowTitle("New Gradient")
        else:
            self.setWindowTitle("Edit Gradient")
        
        # Make it a modal dialog
        self.setModal(True)
        
        # Set reasonable default size
        self.resize(772, 728)
        
    def setup_interactive_color_ramp(self):
        """Replace the static color ramp with interactive widget"""
        try:
            # Get the parent widget and position of the existing label
            old_label = self.verticle_color_ramp
            parent_widget = old_label.parent()
            original_position = old_label.geometry()
            
            # Create the interactive color ramp widget
            self.color_ramp = InteractiveColorRamp(parent_widget)
            
            # Position it with new x position (24) and updated width (62)
            self.color_ramp.setGeometry(24, original_position.y(), 62, original_position.height())
            
            # Remove the old label from layout
            old_label.hide()
            old_label.deleteLater()
            
            # Connect color ramp signals
            self.color_ramp.point_selected.connect(self.on_color_ramp_point_selected)
            self.color_ramp.point_changed.connect(self.on_color_ramp_point_changed)
            self.color_ramp.point_added.connect(self.on_color_ramp_point_added)
            self.color_ramp.point_deleted.connect(self.on_color_ramp_point_deleted)
            self.color_ramp.point_double_clicked.connect(self.on_color_ramp_point_double_clicked)
            self.color_ramp.gradient_updated.connect(self.on_color_ramp_gradient_updated)
            
            # Set initial gradient type if gradient data is available
            if hasattr(self, 'gradient_data') and self.gradient_data:
                initial_gradient_type = self.gradient_data.get('gradient_type', 'gradient')
                self.color_ramp.set_gradient_type(initial_gradient_type)
            
            # Show the new widget
            self.color_ramp.show()
            
        except Exception as e:
            print(f"Error setting up interactive color ramp: {e}")
            # Keep the original label if setup fails
        
    def setup_button_groups(self):
        """Setup button groups for radio buttons"""
        # Gradient type button group
        self.gradient_type_group = QButtonGroup(self)
        self.gradient_type_group.addButton(self.shaded_relief_radio)
        self.gradient_type_group.addButton(self.gradient_radio)
        self.gradient_type_group.addButton(self.posterized_radio)
        self.gradient_type_group.addButton(self.shad_grad_radio)
        self.gradient_type_group.addButton(self.shad_post_radio)
        
        # Units button group
        self.units_group = QButtonGroup(self)
        self.units_group.addButton(self.percent_radio_button)
        self.units_group.addButton(self.meters_radio_button)
    
    def replace_point_elevation_spinbox(self):
        """Replace the integer point elevation spinbox with a double spinbox for decimal precision"""
        try:
            # Get the current integer spinbox
            old_spinbox = self.point_elevation_spin_box
            parent_widget = old_spinbox.parent()
            
            # Get current geometry and properties
            geometry = old_spinbox.geometry()
            current_value = old_spinbox.value()
            minimum = old_spinbox.minimum()
            maximum = old_spinbox.maximum()
            
            # Create new double spinbox
            new_spinbox = QDoubleSpinBox(parent_widget)
            new_spinbox.setObjectName("point_elevation_spin_box")  # Keep same object name
            new_spinbox.setGeometry(geometry)
            
            # Set properties for decimal precision
            new_spinbox.setRange(-10000.0, 10000.0)  # Wide range for elevation values
            new_spinbox.setDecimals(2)  # Allow 2 decimal places (e.g., 1234.56)
            new_spinbox.setSingleStep(0.1)  # Step by 0.1 for fine control
            new_spinbox.setValue(float(current_value))  # Set current value
            
            # Copy styling from old spinbox
            new_spinbox.setStyleSheet(old_spinbox.styleSheet())
            
            # Replace the reference
            self.point_elevation_spin_box = new_spinbox
            
            # Hide and remove old spinbox
            old_spinbox.hide()
            old_spinbox.deleteLater()
            
            # Show new spinbox
            new_spinbox.show()
            
            print("✅ Point elevation spinbox upgraded to support decimal values")
            
        except Exception as e:
            print(f"⚠️ Error replacing point elevation spinbox: {e}")
            print("   Continuing with original integer spinbox")
        
    def connect_signals(self):
        """Connect all the UI signals to their handlers"""
        # Action buttons
        self.OK_button.clicked.connect(self.save_gradient)
        self.cancel_button.clicked.connect(self.cancel_editing)
        
        # Color boxes (clickable for color picker)
        self.shadow_color_box.mousePressEvent = self.select_shadow_color
        self.current_point_color.mousePressEvent = self.select_point_color
        self.no_data_color.mousePressEvent = self.select_no_data_color
        self.below_gradient_color.mousePressEvent = self.select_below_gradient_color
        
        # Light direction dial and spinbox sync - dial uses debounced timer for smooth dragging
        self.light_direction_dial.valueChanged.connect(self.on_light_direction_changed_debounced)
        # Spinbox updates only when editing is finished (Enter, Tab, or focus loss)
        self.light_direction_spin_box.editingFinished.connect(self.on_light_direction_spinbox_changed)
        
        # Shading intensity changes - trigger preview updates only when editing is finished
        self.shading_intensity_spin_box.editingFinished.connect(self.on_shading_intensity_changed)
        
        # Point selection changes - immediate for navigation
        self.point_number_spin_box.valueChanged.connect(self.on_point_selection_changed)
        
        # Elevation range changes - only when editing is finished
        self.min_elevation_spin_box.editingFinished.connect(self.on_elevation_range_changed)
        self.max_elevation_spin_box.editingFinished.connect(self.on_elevation_range_changed)
        
        # Point elevation changes - only when editing is finished
        self.point_elevation_spin_box.editingFinished.connect(self.on_point_elevation_changed)
        
        # Shadow parameter changes - ADD MISSING CONNECTIONS
        self.shadow_drop_spin_box.editingFinished.connect(self.on_shadow_parameters_changed)
        self.shadow_soft_edge_spin_box.editingFinished.connect(self.on_shadow_parameters_changed)
        
        # Gradient name field - update only when editing is finished
        self.gradient_name_edit_field.editingFinished.connect(self.on_gradient_name_changed)
        
        # Effect buttons
        self.spread_button.clicked.connect(self.apply_spread_effect)
        self.square_button.clicked.connect(self.apply_square_effect)
        self.flip_button.clicked.connect(self.apply_flip_effect)
        self.random_button.clicked.connect(self.apply_random_effect)
        self.rainbow_button.clicked.connect(self.apply_rainbow_effect)
        self.roll_button.clicked.connect(self.apply_roll_effect)
        self.hls_button.clicked.connect(self.apply_hls_effect)
        
        # Gradient type changes
        self.gradient_type_group.buttonClicked.connect(self.on_gradient_type_changed)
        
        # Cast shadow checkbox
        self.draw_cast_shadows_check_box.toggled.connect(self.on_cast_shadows_toggled)
        
        # New combo box controls (if present in UI)
        if hasattr(self, 'color_mode_combo'):
            self.color_mode_combo.currentTextChanged.connect(self.on_color_mode_changed)
        
        # Blending strength control (if present in UI)
        if hasattr(self, 'blending_strength_spin_box'):
            self.blending_strength_spin_box.editingFinished.connect(self.on_blending_strength_changed)
        
        # Number of colors changes - connect both signals to handle typing vs button clicks differently
        self.number_of_colors_spin_box.valueChanged.connect(self.on_number_of_colors_value_changed)
        self.number_of_colors_spin_box.editingFinished.connect(self.on_number_of_colors_editing_finished)
        
        # Track if we're currently editing the spinbox text (to distinguish typing from button clicks)
        self.number_of_colors_spin_box.lineEdit().textEdited.connect(self.on_number_of_colors_text_edited)
        
        # Units radio button changes
        self.units_group.buttonClicked.connect(self.on_units_changed)
        
        # Install event filters to prevent Enter key from closing dialog when editing fields
        self.install_enter_key_filters()
        
    def populate_from_gradient_data(self):
        """Populate UI fields from gradient data"""
        if not self.gradient_data:
            # Set defaults for new gradient
            self.set_default_values()
            return
            
        # Set flag to prevent redundant preview updates during UI population
        self.updating_ui = True
        
        # Populate fields from existing gradient data
        try:
            # Gradient name
            if 'name' in self.gradient_data:
                self.gradient_name_edit_field.setText(self.gradient_data['name'])
            
            # Gradient type (check both 'gradient_type' and 'type' for compatibility)
            gradient_type = self.gradient_data.get('gradient_type', self.gradient_data.get('type', 'gradient'))
            if gradient_type == 'shaded_relief':
                self.shaded_relief_radio.setChecked(True)
            elif gradient_type == 'posterized':
                self.posterized_radio.setChecked(True)
            elif gradient_type == 'shading_and_gradient':
                self.shad_grad_radio.setChecked(True)
            elif gradient_type == 'shading_and_posterized':
                self.shad_post_radio.setChecked(True)
            else:
                self.gradient_radio.setChecked(True)
            
            # CRITICAL: Set gradient type BEFORE loading gradient data
            if hasattr(self, 'color_ramp'):
                self.color_ramp.set_gradient_type(gradient_type)
                
                # FOR POSTERIZED GRADIENTS: Simulate button click to ensure proper rendering
                # This fixes the issue where gradient bar shows smooth gradients on first open
                if gradient_type in ['posterized', 'shading_and_posterized']:
                    # Use QTimer to simulate the button click after UI is fully loaded
                    from PyQt6.QtCore import QTimer
                    def simulate_posterized_click():
                        if hasattr(self, 'posterized_radio') and self.posterized_radio.isChecked():
                            # Programmatically trigger the button click workflow
                            self.on_gradient_type_changed(self.posterized_radio)
                        elif hasattr(self, 'shad_post_radio') and self.shad_post_radio.isChecked():
                            # Programmatically trigger the button click workflow for shading+posterized
                            self.on_gradient_type_changed(self.shad_post_radio)
                    
                    # Schedule the simulated click for after initialization
                    QTimer.singleShot(100, simulate_posterized_click)
            
            # Number of colors
            self.number_of_colors_spin_box.setValue(self.gradient_data.get('num_colors', 8))
            
            # Elevation range - first set proper ranges to handle large values
            self.min_elevation_spin_box.setRange(-10000, 10000)  # Allow wide range
            self.max_elevation_spin_box.setRange(-10000, 10000)  # Allow wide range
            self.point_elevation_spin_box.setRange(-10000.0, 10000.0)  # Allow wide range for point elevations (decimal)
            
            # Store the absolute elevation values from gradient data
            min_elev = self.gradient_data.get('min_elevation', 0)
            max_elev = self.gradient_data.get('max_elevation', 1000)
            
            # Preserve absolute values based on the units
            loaded_units = self.gradient_data.get('units', 'meters')
            if loaded_units == 'meters':
                self.absolute_min_elevation_meters = min_elev
                self.absolute_max_elevation_meters = max_elev
            # For percentage mode, keep current internal values as defaults
            
            
            self.min_elevation_spin_box.setValue(int(min_elev))
            self.max_elevation_spin_box.setValue(int(max_elev))
            
            # Units (with support for legacy gradients without scale_type)
            units = self.gradient_data.get('units', 'meters')
            scale_type = self.gradient_data.get('scale_type', 'absolute')  # Default to absolute for legacy
            
            # If scale_type is 'relative' but units is not 'percent', force percent mode
            if scale_type == 'relative':
                units = 'percent'
                
            if units == 'percent':
                self.percent_radio_button.setChecked(True)
            else:
                self.meters_radio_button.setChecked(True)
            
            # Shading options
            self.light_direction_spin_box.setRange(0, 360)
            self.light_direction_spin_box.setValue(int(self.gradient_data.get('light_direction', 315)))
            self.light_direction_dial.setRange(0, 360)
            self.light_direction_dial.setValue(int(self.gradient_data.get('light_direction', 315)))
            self.shading_intensity_spin_box.setRange(-1000, 1000)  # Full experimental range
            self.shading_intensity_spin_box.setValue(int(self.gradient_data.get('shading_intensity', 50)))
            
            # Cast shadows
            self.draw_cast_shadows_check_box.setChecked(self.gradient_data.get('cast_shadows', False))
            self.shadow_drop_spin_box.setRange(0.0, 10000.0)  # Allow wide range for shadow drop distance
            self.shadow_drop_spin_box.setValue(self.gradient_data.get('shadow_drop_distance', 1.0))
            self.shadow_soft_edge_spin_box.setRange(0, 100)  # Allow 0-100 pixel soft edge
            self.shadow_soft_edge_spin_box.setValue(int(self.gradient_data.get('shadow_soft_edge', 3)))
            
            # Blending strength (if control exists)
            if hasattr(self, 'blending_strength_spin_box'):
                self.blending_strength_spin_box.setRange(-1000, 1000)  # Full experimental range
                self.blending_strength_spin_box.setSingleStep(10)  # 10% increments
                blending_strength = self.gradient_data.get('blending_strength', 100)
                self.blending_strength_spin_box.setValue(int(blending_strength))
            
            # Color mode (if control exists)
            if hasattr(self, 'color_mode_combo'):
                color_mode = self.gradient_data.get('color_mode', '8-bit')
                index = self.color_mode_combo.findText(color_mode)
                if index >= 0:
                    self.color_mode_combo.setCurrentIndex(index)
            
            # Load special colors (with defaults for None values)
            if 'shadow_color' in self.gradient_data and self.gradient_data['shadow_color']:
                shadow_color = self.gradient_data['shadow_color']
                if isinstance(shadow_color, dict):
                    # Convert from stored JSON format
                    shadow_color = QColor(shadow_color.get('red', 0), shadow_color.get('green', 0), 
                                        shadow_color.get('blue', 0), shadow_color.get('alpha', 128))
                self.set_color_box(self.shadow_color_box, shadow_color)
            
            if 'no_data_color' in self.gradient_data and self.gradient_data['no_data_color']:
                no_data_color = self.gradient_data['no_data_color']
                if isinstance(no_data_color, dict):
                    # Convert from stored JSON format  
                    no_data_color = QColor(no_data_color.get('red', 255), no_data_color.get('green', 255),
                                         no_data_color.get('blue', 255), no_data_color.get('alpha', 0))
                self.set_color_box(self.no_data_color, no_data_color)
            
            if 'below_gradient_color' in self.gradient_data and self.gradient_data['below_gradient_color']:
                below_gradient_color = self.gradient_data['below_gradient_color']
                if isinstance(below_gradient_color, dict):
                    # Convert from stored JSON format
                    below_gradient_color = QColor(below_gradient_color.get('red', 0), below_gradient_color.get('green', 0),
                                                below_gradient_color.get('blue', 255), below_gradient_color.get('alpha', 255))
                self.set_color_box(self.below_gradient_color, below_gradient_color)
            
            # Set initial point selection
            self.point_number_spin_box.setValue(1)
            self.point_number_spin_box.setMaximum(self.number_of_colors_spin_box.value())
            
            # Update color ramp with elevation range and color stops
            if hasattr(self, 'color_ramp'):
                self.color_ramp.set_elevation_range(
                    self.min_elevation_spin_box.value(),
                    self.max_elevation_spin_box.value()
                )
                
                # Load color stops AFTER gradient type is set
                if 'color_stops' in self.gradient_data and self.gradient_data['color_stops']:
                    self.color_ramp.load_gradient_data(self.gradient_data)
                    # Ensure spinbox matches actual number of color stops loaded
                    actual_color_stops = len(self.gradient_data['color_stops'])
                    if actual_color_stops != self.number_of_colors_spin_box.value():
                        self.number_of_colors_spin_box.setValue(actual_color_stops)
                else:
                    # No color stops provided, use default number from spinbox
                    self.color_ramp.set_num_colors(self.number_of_colors_spin_box.value())
                
                self.update_ui_from_selected_point()
            
            # Update control states based on loaded gradient data
            self.update_control_states()
            
            # Update units display to reflect loaded units
            self.update_units_display()
            
        except Exception as e:
            print(f"Error populating gradient data: {e}")
            self.set_default_values()
        finally:
            # Clear the updating flag and do a single preview update
            self.updating_ui = False
            self.update_terrain_preview()
    
    def set_default_values(self):
        """Set default values for new gradient"""
        # Default gradient name
        self.gradient_name_edit_field.setText("New Gradient")
        
        # Default gradient type
        self.gradient_radio.setChecked(True)
        
        # Default colors and elevation
        self.number_of_colors_spin_box.setValue(8)
        self.min_elevation_spin_box.setRange(-10000, 10000)  # Allow wide range
        self.max_elevation_spin_box.setRange(-10000, 10000)  # Allow wide range
        self.point_elevation_spin_box.setRange(-10000.0, 10000.0)  # Allow wide range for point elevations (decimal)
        self.min_elevation_spin_box.setValue(0)
        self.max_elevation_spin_box.setValue(1000)
        
        # Default units
        self.meters_radio_button.setChecked(True)
        
        # Default shading
        self.light_direction_spin_box.setRange(0, 360)
        self.light_direction_spin_box.setValue(315)  # Northwest
        self.light_direction_dial.setRange(0, 360)
        self.light_direction_dial.setValue(315)
        self.shading_intensity_spin_box.setRange(-1000, 1000)  # Full experimental range
        self.shading_intensity_spin_box.setValue(50)
        
        # Default cast shadows
        self.draw_cast_shadows_check_box.setChecked(False)
        self.shadow_drop_spin_box.setRange(0.0, 10000.0)  # Allow wide range for shadow drop distance
        self.shadow_drop_spin_box.setValue(1.0)
        self.shadow_soft_edge_spin_box.setRange(0, 100)  # Allow 0-100 pixel soft edge
        self.shadow_soft_edge_spin_box.setValue(3)
        
        # Default combo box values (if present in UI)
        if hasattr(self, 'color_mode_combo'):
            self.color_mode_combo.setCurrentText("8-bit")
        
        # Default blending strength (if control exists)
        if hasattr(self, 'blending_strength_spin_box'):
            self.blending_strength_spin_box.setRange(-1000, 1000)  # Full experimental range
            self.blending_strength_spin_box.setSingleStep(10)  # 10% increments
            self.blending_strength_spin_box.setValue(100)  # 100% = normal Hard Light intensity
        
        # Point selection
        self.point_number_spin_box.setValue(1)
        self.point_number_spin_box.setMaximum(8)
        
        # Set default colors
        self.set_color_box(self.shadow_color_box, QColor(0, 0, 0, 128))  # Semi-transparent black
        self.set_color_box(self.current_point_color, QColor(255, 0, 0))  # Red
        self.set_color_box(self.no_data_color, QColor(255, 255, 255, 0))  # Transparent
        self.set_color_box(self.below_gradient_color, QColor(0, 0, 255))  # Blue
        
        # Initialize color ramp with default elevation range and colors
        if hasattr(self, 'color_ramp'):
            self.color_ramp.set_elevation_range(0, 1000)
            # Ensure color ramp has the correct number of colors (8)
            self.color_ramp.set_num_colors(8)
            self.update_ui_from_selected_point()
        
        # Set initial control states based on default selections
        self.update_control_states()
        
        # Set initial units display
        self.update_units_display()
    
    def set_color_box(self, color_box, color):
        """Set the background color of a color box"""
        color_box.setStyleSheet(f"""
            QLabel {{
                border: 1px solid #CCCCCC;
                background-color: rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()});
                width: 101px;
                height: 22px;
            }}
        """)
        # Store the color as a property
        color_box.setProperty("color", color)
    
    def select_shadow_color(self, event):
        """Open color dialog for shadow color"""
        color = QColorDialog.getColor(self.shadow_color_box.property("color") or QColor(0, 0, 0))
        if color.isValid():
            self.set_color_box(self.shadow_color_box, color)
            # Update terrain preview when shadow color changes
            self.update_terrain_preview()
    
    def select_point_color(self, event):
        """Open color dialog for current point color"""
        color = QColorDialog.getColor(self.current_point_color.property("color") or QColor(255, 0, 0))
        if color.isValid():
            self.set_color_box(self.current_point_color, color)
            # Update the color ramp if a point is selected
            if hasattr(self, 'color_ramp') and 0 <= self.color_ramp.selected_point_index < len(self.color_ramp.gradient_points):
                self.color_ramp.update_point_color(self.color_ramp.selected_point_index, color)
    
    def select_no_data_color(self, event):
        """Open color dialog for no data color"""
        color = QColorDialog.getColor(self.no_data_color.property("color") or QColor(255, 255, 255))
        if color.isValid():
            self.set_color_box(self.no_data_color, color)
            # Update the color ramp's no_data_color for gradient bar display
            if hasattr(self, 'color_ramp'):
                rgba_dict = {
                    'red': color.red(),
                    'green': color.green(), 
                    'blue': color.blue(),
                    'alpha': color.alpha()
                }
                self.color_ramp.no_data_color = rgba_dict
                self.color_ramp.update()  # Force gradient bar redraw
            # Update terrain preview when no-data color changes
            self.update_terrain_preview()
    
    def select_below_gradient_color(self, event):
        """Open color dialog for below gradient color"""
        color = QColorDialog.getColor(self.below_gradient_color.property("color") or QColor(0, 0, 255))
        if color.isValid():
            self.set_color_box(self.below_gradient_color, color)
            # Update the color ramp's below_gradient_color for gradient bar display
            if hasattr(self, 'color_ramp'):
                rgba_dict = {
                    'red': color.red(),
                    'green': color.green(), 
                    'blue': color.blue(),
                    'alpha': color.alpha()
                }
                self.color_ramp.below_gradient_color = rgba_dict
                self.color_ramp.update()  # Force gradient bar redraw
            # Update terrain preview when below gradient color changes
            self.update_terrain_preview()
    
    def on_light_direction_changed_debounced(self, value):
        """Handle light direction dial changes - sync immediately, debounce preview update"""
        self.light_direction_spin_box.setValue(value)
        # Start/restart timer for debounced preview update (300ms delay)
        self.light_direction_timer.start(300)
    
    def on_light_direction_spinbox_changed(self):
        """Handle light direction spinbox changes (when editing is complete)"""
        # Get the current value from the spinbox
        value = self.light_direction_spin_box.value()
        # Sync dial with spinbox (without triggering debounced updates)
        self.light_direction_dial.blockSignals(True)
        self.light_direction_dial.setValue(value)
        self.light_direction_dial.blockSignals(False)
        # Update preview immediately since editing is complete
        self.update_terrain_preview()
    
    def on_shading_intensity_changed(self):
        """Handle shading intensity spinbox changes (when editing is complete)"""
        # Update preview for shaded relief gradients
        self.update_terrain_preview()
    
    def on_point_selection_changed(self, point_number):
        """Handle point selection changes from spinbox"""
        # Convert to 0-based index
        point_index = point_number - 1
        if hasattr(self, 'color_ramp') and 0 <= point_index < len(self.color_ramp.gradient_points):
            self.color_ramp.select_point(point_index)
            self.update_ui_from_selected_point()
    
    def on_elevation_range_changed(self):
        """Handle elevation range changes"""
        if hasattr(self, 'color_ramp'):
            min_elev = self.min_elevation_spin_box.value()
            max_elev = self.max_elevation_spin_box.value()
            
            # Update internal storage when user manually changes elevation ranges (meters only)
            if self.meters_radio_button.isChecked():
                self.absolute_min_elevation_meters = min_elev
                self.absolute_max_elevation_meters = max_elev
            
            # Use preserve positions method to keep points in same visual location
            self.color_ramp.set_elevation_range_preserve_positions(min_elev, max_elev)
            # Update the UI to reflect the new elevation of the selected point
            self.update_ui_from_selected_point()
            
            # Update terrain preview when elevation range changes
            self.update_terrain_preview()
    
    def on_point_elevation_changed(self):
        """Handle point elevation spinbox changes (when editing is complete)"""
        # Get the current value from the spinbox
        elevation = self.point_elevation_spin_box.value()
        if hasattr(self, 'color_ramp') and 0 <= self.color_ramp.selected_point_index < len(self.color_ramp.gradient_points):
            self.color_ramp.update_point_elevation(self.color_ramp.selected_point_index, elevation)
    
    def on_number_of_colors_text_edited(self, text):
        """Handle when user is typing in the number of colors spinbox"""
        self.number_of_colors_text_being_edited = True
        print(f"🖊️ User typing in number of colors field: '{text}'")
    
    def on_number_of_colors_value_changed(self, value):
        """Handle number of colors spinbox value changes (immediate for button clicks)"""
        # Only update immediately if this is NOT from typing (i.e., from button clicks)
        if not self.number_of_colors_text_being_edited:
            print(f"🔢 Number of colors button clicked: {value} (updating immediately)")
            self.update_number_of_colors(value)
        else:
            print(f"🖊️ Number of colors changed via typing: {value} (waiting for editing to finish)")
    
    def on_number_of_colors_editing_finished(self):
        """Handle when editing of number of colors spinbox is finished"""
        if self.number_of_colors_text_being_edited:
            print(f"✅ Number of colors editing finished: {self.number_of_colors_spin_box.value()}")
            self.update_number_of_colors(self.number_of_colors_spin_box.value())
        
        # Reset the editing flag
        self.number_of_colors_text_being_edited = False
    
    def update_number_of_colors(self, num_colors):
        """Update the number of colors in the gradient (shared logic)"""
        if not hasattr(self, 'color_ramp') or not self.color_ramp.gradient_points:
            return
            
        # Validate minimum 2 points
        if num_colors < 2:
            print(f"⚠️ Minimum 2 colors required, resetting to 2")
            self.number_of_colors_spin_box.setValue(2)
            return
            
        current_count = len(self.color_ramp.gradient_points)
        
        if num_colors == current_count:
            print(f"📊 Number of colors unchanged: {num_colors}")
            return  # No change needed
            
        print(f"🎨 Updating gradient: {current_count} → {num_colors} colors")
        
        # Update the color ramp to match the new number of colors
        if hasattr(self, 'color_ramp'):
            self.color_ramp.set_num_colors(num_colors)
            
        # Update point selection maximum
        self.point_number_spin_box.setMaximum(num_colors)
        
        # Ensure current point selection is still valid
        if self.point_number_spin_box.value() > num_colors:
            self.point_number_spin_box.setValue(num_colors)
            # Select the last point
            if hasattr(self, 'color_ramp'):
                self.color_ramp.select_point(num_colors - 1)
                self.update_ui_from_selected_point()
        
        print(f"✅ Gradient updated successfully to {num_colors} colors")
    
    def on_color_ramp_point_selected(self, index):
        """Handle point selection from color ramp"""
        # Update point number spinbox (1-based)
        self.point_number_spin_box.setValue(index + 1)
        self.update_ui_from_selected_point()
    
    def on_color_ramp_point_changed(self, index, elevation, color):
        """Handle point changes from color ramp"""
        # Update UI to reflect the changes
        if index == self.color_ramp.selected_point_index:
            self.point_elevation_spin_box.setValue(float(elevation))  # Support decimal values
            self.set_color_box(self.current_point_color, color)
        # Update terrain preview when color point changes
        self.update_terrain_preview()
    
    def on_color_ramp_point_added(self, index):
        """Handle point addition from color ramp"""
        # Update the number of colors and point selection
        self.number_of_colors_spin_box.setValue(len(self.color_ramp.gradient_points))
        self.point_number_spin_box.setMaximum(len(self.color_ramp.gradient_points))
        self.point_number_spin_box.setValue(index + 1)
        self.update_ui_from_selected_point()
    
    def on_color_ramp_point_deleted(self, index):
        """Handle point deletion from color ramp"""
        # Update the number of colors and point selection
        self.number_of_colors_spin_box.setValue(len(self.color_ramp.gradient_points))
        self.point_number_spin_box.setMaximum(len(self.color_ramp.gradient_points))
        # Ensure selected point is valid
        if self.point_number_spin_box.value() > len(self.color_ramp.gradient_points):
            self.point_number_spin_box.setValue(len(self.color_ramp.gradient_points))
        self.update_ui_from_selected_point()
    
    def on_color_ramp_point_double_clicked(self, index):
        """Handle double-click on gradient point - open color selector dialog"""
        print(f"🎨 Opening color selector for double-clicked point {index}")
        
        # First, ensure the double-clicked point is selected
        if hasattr(self, 'color_ramp') and 0 <= index < len(self.color_ramp.gradient_points):
            self.color_ramp.select_point(index)
            self.update_ui_from_selected_point()
            
            # Get the current color of the selected point
            current_color = self.color_ramp.gradient_points[index].color
            
            # Open color dialog
            color = QColorDialog.getColor(current_color, self, "Select Point Color")
            if color.isValid():
                # Update the color box display
                self.set_color_box(self.current_point_color, color)
                # Update the color ramp point
                self.color_ramp.update_point_color(index, color)
                print(f"🎨 Point {index} color updated to {color.name()}")
    
    def on_color_ramp_gradient_updated(self):
        """Handle gradient updates from color ramp"""
        # Update terrain preview when gradient changes
        self.update_terrain_preview()
    
    def update_ui_from_selected_point(self):
        """Update UI controls based on currently selected point"""
        if hasattr(self, 'color_ramp'):
            selected_point = self.color_ramp.get_selected_point()
            if selected_point:
                self.point_elevation_spin_box.setValue(float(selected_point.elevation))  # Support decimal values
                self.set_color_box(self.current_point_color, selected_point.color)
    
    def update_control_states(self):
        """Update the enabled/disabled state of controls based on current selections"""
        # Get current gradient type
        gradient_type = "gradient"  # default
        if self.shaded_relief_radio.isChecked():
            gradient_type = "Shaded relief"
        elif self.posterized_radio.isChecked():
            gradient_type = "Posterized"
        elif self.shad_grad_radio.isChecked():
            gradient_type = "Shading and Gradient"
        elif self.shad_post_radio.isChecked():
            gradient_type = "Shading and Posterized"
        
        # Update shading controls
        has_shading = gradient_type in ["Shaded relief", "Shading and Gradient", "Shading and Posterized"]
        self.cast_shadow_group_box.setEnabled(has_shading)
        
        # Update blending strength control (only for combined shading+color modes)
        has_blending = gradient_type in ["Shading and Gradient", "Shading and Posterized"]
        if hasattr(self, 'blending_strength_spin_box'):
            self.blending_strength_spin_box.setEnabled(has_blending)
        if hasattr(self, 'blending_mode_label'):  # Label was renamed but object name stayed the same
            self.blending_mode_label.setEnabled(has_blending)
        
        # Update gradient options
        has_gradient = gradient_type != "Shaded relief"
        self.gradient_options_group_box.setEnabled(has_gradient)
        
        # Update cast shadow controls
        cast_shadows_enabled = self.draw_cast_shadows_check_box.isChecked()
        self.shadow_drop_spin_box.setEnabled(cast_shadows_enabled)
        self.shadow_soft_edge_spin_box.setEnabled(cast_shadows_enabled)
        self.shadow_color_box.setEnabled(cast_shadows_enabled)
        self.shadow_drop_distance_label.setEnabled(cast_shadows_enabled)
        self.shadow_drop_distance_label_2.setEnabled(cast_shadows_enabled)
        self.shadow_soft_edge_label.setEnabled(cast_shadows_enabled)
        self.shadow_color_label.setEnabled(cast_shadows_enabled)
    
    def on_gradient_type_changed(self, button):
        """Handle gradient type changes"""
        # Get current gradient type
        gradient_type = "gradient"  # default
        if self.shaded_relief_radio.isChecked():
            gradient_type = "shaded_relief"
        elif self.posterized_radio.isChecked():
            gradient_type = "posterized"
        elif self.shad_grad_radio.isChecked():
            gradient_type = "shading_and_gradient"
        elif self.shad_post_radio.isChecked():
            gradient_type = "shading_and_posterized"
        
        # Update the color ramp display to match gradient type
        if hasattr(self, 'color_ramp'):
            self.color_ramp.set_gradient_type(gradient_type)
        
        # Update all control states when gradient type changes
        self.update_control_states()
        # Update terrain preview when gradient type changes
        self.update_terrain_preview()
        
    def on_cast_shadows_toggled(self, checked):
        """Handle cast shadows checkbox"""
        print(f"🌑 Cast shadows toggled: {'ON' if checked else 'OFF'}")
        # Update all control states when cast shadows setting changes
        self.update_control_states()
        # Update terrain preview immediately when cast shadows setting changes
        self.update_terrain_preview()
    
    def on_blending_strength_changed(self):
        """Handle blending strength changes"""
        if hasattr(self, 'blending_strength_spin_box'):
            strength = self.blending_strength_spin_box.value()
            print(f"🎨 Blending strength changed to: {strength}%")
            self.update_terrain_preview()
    
    def on_color_mode_changed(self, mode):
        """Handle color mode combo box changes"""
        # Store the color mode for gradient data
        print(f"Color mode changed to: {mode}")
        # This will affect how colors are stored and displayed
        # TODO: Convert existing color values when switching modes
    
    def on_units_changed(self, button):
        """Handle units radio button changes"""
        # Skip updates during UI population to prevent overwriting loaded values
        if getattr(self, 'updating_ui', False):
            return
        
        # Determine which units mode was selected
        selected_units = "unknown"
        if self.percent_radio_button.isChecked():
            selected_units = "percent"
        elif self.meters_radio_button.isChecked():
            selected_units = "meters"
        
        # Get current spinbox values BEFORE units display update
        old_min = self.min_elevation_spin_box.value()
        old_max = self.max_elevation_spin_box.value()
        
        print(f"🔄 Console radio buttons changed: {selected_units}")
        print(f"   Before update: min={old_min}, max={old_max}")
            
        self.update_units_display()
        
        # Get spinbox values AFTER units display update
        new_min = self.min_elevation_spin_box.value()
        new_max = self.max_elevation_spin_box.value()
        
        print(f"   After update: min={new_min}, max={new_max}, units={selected_units}")
        
        # Show color ramp state
        if hasattr(self, 'color_ramp') and hasattr(self.color_ramp, 'gradient_points'):
            print(f"   Color ramp points: {len(self.color_ramp.gradient_points)}")
            if len(self.color_ramp.gradient_points) > 0:
                for i, point in enumerate(self.color_ramp.gradient_points):
                    print(f"     Point {i}: position={point.y_position:.3f}, elevation={point.elevation:.1f}")
        
        self.update_control_states()
        # Update terrain preview when units change
        self.update_terrain_preview()
    
    def on_shadow_parameters_changed(self):
        """Handle shadow drop distance and soft edge parameter changes"""
        print(f"Shadow parameters changed: drop={self.shadow_drop_spin_box.value()}, soft_edge={self.shadow_soft_edge_spin_box.value()}")
        # Update terrain preview when shadow parameters change
        self.update_terrain_preview()
    
    def on_gradient_name_changed(self):
        """Handle gradient name field changes"""
        name = self.gradient_name_edit_field.text()
        print(f"Gradient name changed to: '{name}'")
        # No need to update preview for name changes
    
    def install_enter_key_filters(self):
        """Install event filters to prevent Enter key from closing dialog when editing fields"""
        # Create event filter to handle Enter key in edit fields
        from PyQt6.QtCore import QObject, QEvent
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtCore import Qt
        
        class EnterKeyFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.KeyPress:
                    if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                        # For spin boxes and line edits, trigger editingFinished and consume the event
                        # This prevents the Enter key from reaching the dialog and closing it
                        try:
                            if hasattr(obj, 'editingFinished'):
                                obj.editingFinished.emit()
                            return True  # Event handled, don't propagate
                        except Exception:
                            # If there's any issue with the signal, just consume the event
                            return True
                return False  # Let other events (including Tab) pass through normally
        
        # Create one instance of the filter
        self.enter_filter = EnterKeyFilter(self)
        
        # Install the filter on all edit fields and spin boxes
        edit_widgets = [
            self.gradient_name_edit_field,
            self.light_direction_spin_box,
            self.shading_intensity_spin_box,
            self.min_elevation_spin_box,
            self.max_elevation_spin_box,
            self.point_elevation_spin_box,
            self.shadow_drop_spin_box,
            self.shadow_soft_edge_spin_box,
            self.number_of_colors_spin_box,
            self.point_number_spin_box
        ]
        
        for widget in edit_widgets:
            if widget:  # Make sure widget exists
                widget.installEventFilter(self.enter_filter)
    
    def update_units_display(self):
        """Update elevation display based on selected units mode - preserves point positions"""
        
        # Store current absolute values before switching (if we're currently in absolute mode)
        # We need to check if current spinbox ranges indicate we're NOT in percentage mode
        current_min = self.min_elevation_spin_box.value()
        current_max = self.max_elevation_spin_box.value()
        
        # If current values are not 0-100 range OR if min/max boxes are enabled, we're in absolute mode
        is_currently_absolute_mode = (self.min_elevation_spin_box.isEnabled() and 
                                    self.max_elevation_spin_box.isEnabled())
        
        if is_currently_absolute_mode:
            # We're switching FROM absolute mode (meters), so preserve the current values
            self.absolute_min_elevation_meters = current_min
            self.absolute_max_elevation_meters = current_max
        
        if self.percent_radio_button.isChecked():
            # Percentage mode: 0% to 100%
            self.min_elevation_spin_box.setValue(0)
            self.max_elevation_spin_box.setValue(100)
            
            # Set labels to show percentage
            self.min_elevation_label.setText("Min elevation (%)")
            self.max_elevation_label.setText("Max elevation (%)")
            self.point_elevation_label.setText("Point elevation (%)")
            
            # Disable min/max fields (grayed out like in original TopoToImage)
            self.min_elevation_spin_box.setEnabled(False)
            self.max_elevation_spin_box.setEnabled(False)
            
            # Set spinbox ranges for percentage
            self.min_elevation_spin_box.setRange(0, 100)
            self.max_elevation_spin_box.setRange(0, 100)
            self.point_elevation_spin_box.setRange(0.0, 100.0)  # Support decimal percentages
            
            # Update color ramp to percentage mode - PRESERVE POINT POSITIONS
            if hasattr(self, 'color_ramp'):
                self.color_ramp.set_elevation_range_preserve_positions(0, 100)
                self.color_ramp.set_units_mode('percent')
                
        else:  # meters_radio_button.isChecked()
            # Meters mode: restore saved absolute elevation values
            self.min_elevation_label.setText("Min elevation (m)")
            self.max_elevation_label.setText("Max elevation (m)")
            self.point_elevation_label.setText("Point elevation (m)")
            
            # Enable min/max fields
            self.min_elevation_spin_box.setEnabled(True)
            self.max_elevation_spin_box.setEnabled(True)
            
            # Set spinbox ranges for meters - BEFORE setting values
            self.min_elevation_spin_box.setRange(-10000, 10000)
            self.max_elevation_spin_box.setRange(-10000, 10000)
            self.point_elevation_spin_box.setRange(-10000.0, 10000.0)  # Support decimal meters
            
            # Restore saved meter values
            self.min_elevation_spin_box.setValue(int(self.absolute_min_elevation_meters))
            self.max_elevation_spin_box.setValue(int(self.absolute_max_elevation_meters))
                
            # Update color ramp to meters mode - PRESERVE POINT POSITIONS
            if hasattr(self, 'color_ramp'):
                self.color_ramp.set_elevation_range_preserve_positions(
                    self.absolute_min_elevation_meters, 
                    self.absolute_max_elevation_meters
                )
                self.color_ramp.set_units_mode('meters')
        
        # Update UI from selected point to reflect new units
        self.update_ui_from_selected_point()
    
    # Effect button handlers (to be implemented)
    def apply_spread_effect(self):
        """Apply spread effect to elevation points - evenly distribute elevations from bottom to top"""
        if not hasattr(self, 'color_ramp') or not self.color_ramp.gradient_points:
            return
        
        num_points = len(self.color_ramp.gradient_points)
        if num_points < 2:
            return
        
        print("Applying spread effect - evenly distributing elevation points")
        
        # Sort points by current y_position to maintain color order
        sorted_points = sorted(self.color_ramp.gradient_points, key=lambda p: p.y_position)
        
        # Evenly distribute y_positions from 0.0 (top) to 1.0 (bottom)
        for i, point in enumerate(sorted_points):
            if num_points == 1:
                new_y_position = 0.5
            else:
                new_y_position = i / (num_points - 1)  # 0.0, 0.33, 0.67, 1.0 for 4 points
            
            point.y_position = new_y_position
            point.elevation = self.color_ramp.y_position_to_elevation(new_y_position)
        
        # Update UI and preview
        self.color_ramp.update()
        self.update_terrain_preview()
        self.color_ramp.gradient_updated.emit()
        print(f"Spread complete - {num_points} points evenly distributed")
    
    def apply_square_effect(self):
        """Apply square effect to elevation points - square the percentage elevation (moves points down)"""
        if not hasattr(self, 'color_ramp') or not self.color_ramp.gradient_points:
            return
        
        print("Applying square effect - squaring percentage elevations")
        
        for point in self.color_ramp.gradient_points:
            # Convert y_position (0.0=top, 1.0=bottom) to percentage (0.0=bottom, 1.0=top)
            percentage_elevation = 1.0 - point.y_position
            
            # Square the percentage elevation
            squared_percentage = percentage_elevation ** 2
            
            # Convert back to y_position
            point.y_position = 1.0 - squared_percentage
            point.elevation = self.color_ramp.y_position_to_elevation(point.y_position)
            
            print(f"Point: {percentage_elevation:.3f} -> {squared_percentage:.3f} (y_pos: {point.y_position:.3f})")
        
        # Update UI and preview
        self.color_ramp.update()
        self.update_terrain_preview()
        self.color_ramp.gradient_updated.emit()
        print("Square effect complete - points moved toward bottom")
    
    def apply_flip_effect(self):
        """Apply flip effect - flip all color points, elevations, and colors (top becomes bottom)"""
        if not hasattr(self, 'color_ramp') or not self.color_ramp.gradient_points:
            return
        
        print("Applying flip effect - flipping gradient top to bottom")
        
        for point in self.color_ramp.gradient_points:
            # Flip the y_position: new_y_position = 1.0 - old_y_position
            # This makes top points (y=0.0) become bottom points (y=1.0) and vice versa
            old_y_position = point.y_position
            point.y_position = 1.0 - old_y_position
            point.elevation = self.color_ramp.y_position_to_elevation(point.y_position)
            
            print(f"Point flipped: y_pos {old_y_position:.3f} -> {point.y_position:.3f}")
        
        # Update UI and preview
        self.color_ramp.update()
        self.update_terrain_preview()
        self.color_ramp.gradient_updated.emit()
        print("Flip effect complete - gradient flipped top to bottom")
    
    def apply_random_effect(self):
        """Apply random effect - replace each color with random RGB values"""
        if not hasattr(self, 'color_ramp') or not self.color_ramp.gradient_points:
            return
        
        import random
        
        print("Applying random effect - replacing all colors with random RGB values")
        
        for i, point in enumerate(self.color_ramp.gradient_points):
            # Generate random RGB values (0-255)
            random_red = random.randint(0, 255)
            random_green = random.randint(0, 255)
            random_blue = random.randint(0, 255)
            
            # Keep alpha at 255 (fully opaque)
            point.color = QColor(random_red, random_green, random_blue, 255)
            
            print(f"Point {i+1}: New random color RGB({random_red}, {random_green}, {random_blue})")
        
        # Update UI and preview
        self.color_ramp.update()
        self.update_terrain_preview()
        self.color_ramp.gradient_updated.emit()
        
        # Update the current point color display if a point is selected
        if (hasattr(self, 'color_ramp') and 
            0 <= self.color_ramp.selected_point_index < len(self.color_ramp.gradient_points)):
            selected_color = self.color_ramp.gradient_points[self.color_ramp.selected_point_index].color
            self.set_color_box(self.current_point_color, selected_color)
        
        print("Random effect complete - all colors randomized")
    
    def apply_rainbow_effect(self):
        """Apply rainbow effect - replace colors with fully saturated rainbow colors evenly spaced around color wheel"""
        if not hasattr(self, 'color_ramp') or not self.color_ramp.gradient_points:
            return
        
        import colorsys
        
        num_points = len(self.color_ramp.gradient_points)
        print(f"Applying rainbow effect - creating {num_points} evenly spaced rainbow colors")
        
        # Sort points by y_position to assign colors from top to bottom
        sorted_points = sorted(self.color_ramp.gradient_points, key=lambda p: p.y_position)
        
        for i, point in enumerate(sorted_points):
            # Calculate hue evenly distributed around color wheel (0 to 360 degrees)
            hue = i / num_points  # 0.0 to 1.0 (maps to 0° to 360°)
            saturation = 1.0      # 100% saturation (fully saturated)
            value = 1.0          # 100% brightness/value
            
            # Convert HSV to RGB
            rgb = colorsys.hsv_to_rgb(hue, saturation, value)
            
            # Convert to 0-255 range
            red = int(rgb[0] * 255)
            green = int(rgb[1] * 255)
            blue = int(rgb[2] * 255)
            
            # Set the color
            point.color = QColor(red, green, blue, 255)
            
            print(f"Point {i+1}: Hue {hue*360:.1f}° -> RGB({red}, {green}, {blue})")
        
        # Update UI and preview
        self.color_ramp.update()
        self.update_terrain_preview()
        self.color_ramp.gradient_updated.emit()
        
        # Update the current point color display if a point is selected
        if (hasattr(self, 'color_ramp') and 
            0 <= self.color_ramp.selected_point_index < len(self.color_ramp.gradient_points)):
            selected_color = self.color_ramp.gradient_points[self.color_ramp.selected_point_index].color
            self.set_color_box(self.current_point_color, selected_color)
        
        print("Rainbow effect complete - colors set to evenly spaced rainbow hues")
    
    def apply_roll_effect(self):
        """Apply roll effect - roll colors up by one position (bottom becomes top, others move up)"""
        if not hasattr(self, 'color_ramp') or not self.color_ramp.gradient_points:
            return
        
        num_points = len(self.color_ramp.gradient_points)
        if num_points < 2:
            return
        
        print("Applying roll effect - rolling colors up by one position")
        
        # Sort points by y_position to get them in order from top to bottom
        sorted_points = sorted(self.color_ramp.gradient_points, key=lambda p: p.y_position)
        
        # Store all colors
        colors = [point.color for point in sorted_points]
        
        # Roll colors: each color gets replaced by the one below it
        # The bottom color goes to the top
        for i in range(num_points):
            if i == 0:
                # Top point gets the bottom color
                new_color = colors[-1]  # Last color (bottom)
                print(f"Point 1 (top): Gets color from point {num_points} (bottom)")
            else:
                # Each other point gets the color from the point above it
                new_color = colors[i - 1]
                print(f"Point {i+1}: Gets color from point {i}")
            
            sorted_points[i].color = new_color
        
        # Update UI and preview
        self.color_ramp.update()
        self.update_terrain_preview()
        self.color_ramp.gradient_updated.emit()
        
        # Update the current point color display if a point is selected
        if (hasattr(self, 'color_ramp') and 
            0 <= self.color_ramp.selected_point_index < len(self.color_ramp.gradient_points)):
            selected_color = self.color_ramp.gradient_points[self.color_ramp.selected_point_index].color
            self.set_color_box(self.current_point_color, selected_color)
        
        print("Roll effect complete - colors rolled up by one position")
    
    def apply_hls_effect(self):
        """Apply HLS effect to colors - open HLS adjustment dialog"""
        if not hasattr(self, 'color_ramp') or not self.color_ramp.gradient_points:
            return
        
        from hls_adjustment_dialog import HLSAdjustmentDialog, apply_hls_adjustment
        
        print("Opening HLS adjustment dialog")
        
        # Store original colors for live preview and cancel functionality
        self.original_colors = []
        for point in self.color_ramp.gradient_points:
            self.original_colors.append(QColor(point.color))
        
        # Create and configure the HLS dialog
        hls_dialog = HLSAdjustmentDialog(self)
        
        # Connect the live preview signal
        hls_dialog.adjustments_changed.connect(self.apply_hls_live_preview)
        
        # Show the dialog
        result = hls_dialog.exec()
        
        if result == hls_dialog.DialogCode.Accepted:
            # User clicked OK - keep the changes
            print("HLS adjustments accepted")
            self.update_terrain_preview()
            self.color_ramp.gradient_updated.emit()
            
            # Update the current point color display if a point is selected
            if (hasattr(self, 'color_ramp') and 
                0 <= self.color_ramp.selected_point_index < len(self.color_ramp.gradient_points)):
                selected_color = self.color_ramp.gradient_points[self.color_ramp.selected_point_index].color
                self.set_color_box(self.current_point_color, selected_color)
        else:
            # User clicked Cancel - restore original colors
            print("HLS adjustments cancelled - restoring original colors")
            for i, original_color in enumerate(self.original_colors):
                if i < len(self.color_ramp.gradient_points):
                    self.color_ramp.gradient_points[i].color = original_color
            
            self.color_ramp.update()
            self.update_terrain_preview()
            
            # Update the current point color display
            if (hasattr(self, 'color_ramp') and 
                0 <= self.color_ramp.selected_point_index < len(self.color_ramp.gradient_points)):
                selected_color = self.color_ramp.gradient_points[self.color_ramp.selected_point_index].color
                self.set_color_box(self.current_point_color, selected_color)
        
        # Clean up stored colors
        self.original_colors = []
    
    def apply_hls_live_preview(self, hue_shift, lightness_shift, saturation_shift, all_colors):
        """Apply HLS adjustments for live preview"""
        from hls_adjustment_dialog import apply_hls_adjustment
        
        if not hasattr(self, 'original_colors') or not self.original_colors:
            return
        
        if all_colors:
            # Apply to all gradient points
            for i, original_color in enumerate(self.original_colors):
                if i < len(self.color_ramp.gradient_points):
                    adjusted_color = apply_hls_adjustment(original_color, hue_shift, lightness_shift, saturation_shift)
                    self.color_ramp.gradient_points[i].color = adjusted_color
        else:
            # Apply only to selected point
            if (0 <= self.color_ramp.selected_point_index < len(self.color_ramp.gradient_points) and
                self.color_ramp.selected_point_index < len(self.original_colors)):
                original_color = self.original_colors[self.color_ramp.selected_point_index]
                adjusted_color = apply_hls_adjustment(original_color, hue_shift, lightness_shift, saturation_shift)
                self.color_ramp.gradient_points[self.color_ramp.selected_point_index].color = adjusted_color
        
        # Update visual elements
        self.color_ramp.update()
        self.update_terrain_preview()
        
        # Update current point color display if needed
        if (hasattr(self, 'color_ramp') and 
            0 <= self.color_ramp.selected_point_index < len(self.color_ramp.gradient_points)):
            selected_color = self.color_ramp.gradient_points[self.color_ramp.selected_point_index].color
            self.set_color_box(self.current_point_color, selected_color)
    
    def save_gradient(self):
        """Save the gradient and close the window"""
        try:
            # Collect all the gradient data from the UI
            gradient_data = self.collect_gradient_data()
            
            # Emit the gradient data
            self.gradient_saved.emit(gradient_data)
            
            # Close the window
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save gradient: {e}")
    
    def collect_gradient_data(self):
        """Collect all gradient data from the UI controls"""
        # Get gradient type
        gradient_type = "gradient"  # default
        if self.shaded_relief_radio.isChecked():
            gradient_type = "shaded_relief"
        elif self.posterized_radio.isChecked():
            gradient_type = "posterized"
        elif self.shad_grad_radio.isChecked():
            gradient_type = "shading_and_gradient"
        elif self.shad_post_radio.isChecked():
            gradient_type = "shading_and_posterized"
        
        # Get units
        units = "meters"  # default
        if self.percent_radio_button.isChecked():
            units = "percent"
        
        # Extract color stops from the interactive color ramp
        color_stops = []
        if hasattr(self, 'color_ramp') and self.color_ramp.gradient_points:
            # Sort gradient points by elevation (position)
            sorted_points = sorted(self.color_ramp.gradient_points, key=lambda p: p.y_position)
            
            for point in sorted_points:
                color_stop = {
                    'position': point.y_position,  # 0.0 to 1.0
                    'red': point.color.red(),
                    'green': point.color.green(),
                    'blue': point.color.blue(),
                    'alpha': point.color.alpha()
                }
                color_stops.append(color_stop)
            
        else:
            print("⚠️  No interactive color ramp found, creating default color stops")
            # Default color stops if no ramp is available
            color_stops = [
                {'position': 0.0, 'red': 0, 'green': 128, 'blue': 0, 'alpha': 255},
                {'position': 1.0, 'red': 255, 'green': 255, 'blue': 255, 'alpha': 255}
            ]

        # Determine scale type based on units (like original TopoToImage)
        scale_type = 'relative' if units == 'percent' else 'absolute'
        
        # Get elevation range based on units mode (same logic as build_current_gradient)
        if units == 'percent':
            # In percent mode, use actual database elevation range
            if self.preview_elevation_data is not None:
                valid_data = self.preview_elevation_data[~np.isnan(self.preview_elevation_data)]
                if len(valid_data) > 0:
                    min_elevation = float(np.min(valid_data))
                    max_elevation = float(np.max(valid_data))
                    print(f"💾 Saving gradient in percent mode: using actual range {min_elevation:.1f} to {max_elevation:.1f}m")
                else:
                    min_elevation = 0
                    max_elevation = 100
            else:
                min_elevation = 0
                max_elevation = 100
        else:
            # In absolute modes (feet/meters), use spinbox values directly
            min_elevation = self.min_elevation_spin_box.value()
            max_elevation = self.max_elevation_spin_box.value()
        
        # Collect all data
        gradient_data = {
            'name': self.gradient_name_edit_field.text(),
            'type': gradient_type,
            'gradient_type': gradient_type,  # Also include gradient_type for consistency
            'num_colors': self.number_of_colors_spin_box.value(),
            'min_elevation': min_elevation,
            'max_elevation': max_elevation,
            'units': units,
            'scale_type': scale_type,  # 'relative' (percentage) or 'absolute' (feet/meters)
            'light_direction': self.light_direction_spin_box.value(),
            'shading_intensity': self.shading_intensity_spin_box.value(),
            'cast_shadows': self.draw_cast_shadows_check_box.isChecked(),
            'shadow_drop_distance': self.shadow_drop_spin_box.value(),
            'shadow_soft_edge': self.shadow_soft_edge_spin_box.value(),
            'shadow_color': self.convert_qcolor_to_dict(self.shadow_color_box.property("color")),
            'no_data_color': self.convert_qcolor_to_dict(self.no_data_color.property("color")),
            'below_gradient_color': self.convert_qcolor_to_dict(self.below_gradient_color.property("color")),
            'blending_mode': 'Hard Light',  # Always use Hard Light
            'blending_strength': self.blending_strength_spin_box.value() if hasattr(self, 'blending_strength_spin_box') else 100,
            'color_mode': self.color_mode_combo.currentText() if hasattr(self, 'color_mode_combo') else '8-bit',
            'color_stops': color_stops,  # Add the extracted color stops
            # Add more fields as needed
        }
        
        return gradient_data
    
    def convert_qcolor_to_dict(self, color):
        """Convert QColor object to dictionary format for JSON storage"""
        if color is None:
            return None
        return {
            'red': color.red(),
            'green': color.green(),
            'blue': color.blue(),
            'alpha': color.alpha()
        }
    
    def load_preview_database(self):
        """Load a preview database for terrain rendering - use same system as main window"""
        try:
            # If a specific preview database path was provided, use it
            if self.preview_database_path and Path(self.preview_database_path).exists():
                preview_path = Path(self.preview_database_path)
                print(f"🔍 Loading specified preview database: {preview_path.name}")
                dem_reader = DEMReader(preview_path)
                self.preview_elevation_data = dem_reader.load_elevation_data()
                if self.preview_elevation_data is not None:
                    print(f"✅ Loaded preview elevation data: {self.preview_elevation_data.shape}")
                    valid_data = self.preview_elevation_data[~np.isnan(self.preview_elevation_data)]
                    if len(valid_data) > 0:
                        elev_min, elev_max = float(np.min(valid_data)), float(np.max(valid_data))
                        print(f"📊 Elevation range: {elev_min:.0f}m to {elev_max:.0f}m")
                    return
            
            # Fallback: Use the same preview_icon_databases folder as main window
            preview_dir = Path(__file__).parent / "preview_icon_databases"
            if not preview_dir.exists():
                print(f"⚠️ Preview databases directory not found: {preview_dir}")
                print("🔄 Creating synthetic preview elevation data")
                self.preview_elevation_data = self.create_synthetic_terrain()
                return
            
            # Supported DEM file extensions (same as main window)
            dem_extensions = {'.tif', '.tiff', '.dem', '.bil'}
            
            # Find the first available DEM file in the preview directory
            preview_files = []
            for file_path in preview_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in dem_extensions:
                    preview_files.append(file_path)
            
            # Sort by name for consistent ordering (same as main window)
            preview_files.sort(key=lambda p: p.name)
            
            if preview_files:
                # Use the first preview database (pr01_fixed.tif or similar)
                preview_path = preview_files[0]
                print(f"🔍 Loading default preview database: {preview_path.name}")
                dem_reader = DEMReader(preview_path)
                self.preview_elevation_data = dem_reader.load_elevation_data()
                if self.preview_elevation_data is not None:
                    print(f"✅ Loaded preview elevation data: {self.preview_elevation_data.shape}")
                    valid_data = self.preview_elevation_data[~np.isnan(self.preview_elevation_data)]
                    if len(valid_data) > 0:
                        elev_min, elev_max = float(np.min(valid_data)), float(np.max(valid_data))
                        print(f"📊 Elevation range: {elev_min:.0f}m to {elev_max:.0f}m")
                    return
                        
            # Fallback: create synthetic elevation data
            print("🔄 No valid preview databases found, creating synthetic preview elevation data")
            self.preview_elevation_data = self.create_synthetic_terrain()
            
        except Exception as e:
            print(f"⚠️ Error loading preview database: {e}")
            # Create synthetic data as fallback
            self.preview_elevation_data = self.create_synthetic_terrain()
    
    def create_synthetic_terrain(self):
        """Create synthetic terrain data for preview"""
        size = 120
        x = np.linspace(-2, 2, size)
        y = np.linspace(-2, 2, size)
        X, Y = np.meshgrid(x, y)
        
        # Create interesting terrain with hills and valleys
        Z = 100 * (np.sin(X * 2) * np.cos(Y * 2) + 
                   0.5 * np.sin(X * 4) * np.cos(Y * 4) +
                   0.3 * np.sin(X * 8) * np.cos(Y * 8))
        
        # Shift to positive values (0-1000m range)
        Z = Z + 500
        
        return Z.astype(np.float32)
    
    def update_terrain_preview(self):
        """Update the terrain preview icon with current gradient settings"""
        try:
            # Skip preview update if we're in the middle of updating UI
            if self.updating_ui:
                return
                
            if self.preview_elevation_data is None:
                return
                
            # Build current gradient from UI
            gradient = self.build_current_gradient()
            if not gradient:
                return
                
            # Add gradient to manager temporarily for rendering
            temp_name = "__temp_preview_gradient__"
            self.gradient_manager.gradients[temp_name] = gradient
            
            # Determine elevation range based on units mode
            min_elev, max_elev = self.calculate_elevation_range_for_preview(gradient)
            
            # Render terrain preview
            preview_image = self.terrain_renderer.render_terrain(
                elevation_data=self.preview_elevation_data,
                gradient_name=temp_name,
                min_elevation=min_elev,
                max_elevation=max_elev
            )
            
            # Remove temporary gradient
            if temp_name in self.gradient_manager.gradients:
                del self.gradient_manager.gradients[temp_name]
            
            if preview_image:
                # Scale to preview size (124x124 to perfectly fit UI container)
                preview_image = preview_image.resize((124, 124))
                
                # Convert PIL image to QPixmap and display
                qimage = preview_image.toqimage()
                pixmap = QPixmap.fromImage(qimage)
                self.preview_icon.setPixmap(pixmap)
                print("🎨 Updated terrain preview in gradient editor")
            
        except Exception as e:
            print(f"⚠️ Error updating terrain preview: {e}")
            import traceback
            traceback.print_exc()
    
    def build_current_gradient(self):
        """Build a Gradient object from current UI settings"""
        try:
            # Get basic info
            name = self.gradient_name_edit_field.text() or "Preview Gradient"
            
            # Determine units first to get correct elevation range
            units = 'meters'  # default
            if self.percent_radio_button.isChecked():
                units = 'percent'
            
            # Get elevation range based on units mode
            if units == 'percent':
                # In percent mode, use actual database elevation range
                if self.preview_elevation_data is not None:
                    valid_data = self.preview_elevation_data[~np.isnan(self.preview_elevation_data)]
                    if len(valid_data) > 0:
                        min_elev = float(np.min(valid_data))
                        max_elev = float(np.max(valid_data))
                        print(f"🎯 Building gradient in percent mode: using actual range {min_elev:.1f} to {max_elev:.1f}m")
                    else:
                        min_elev = 0
                        max_elev = 100
                else:
                    min_elev = 0
                    max_elev = 100
            else:
                # In absolute mode (meters), use spinbox values
                min_elev = self.min_elevation_spin_box.value()
                max_elev = self.max_elevation_spin_box.value()
            
            # Get color stops from color ramp
            color_stops = []
            if hasattr(self, 'color_ramp') and hasattr(self.color_ramp, 'gradient_points'):
                # Sort points by y_position (visual position in the ramp)
                sorted_points = sorted(self.color_ramp.gradient_points, key=lambda p: p.y_position)
                for point in sorted_points:
                    # Use y_position directly as it's already normalized (0.0 = top, 1.0 = bottom)
                    position = point.y_position
                    stop = ColorStop(
                        position=position,
                        red=point.color.red(),
                        green=point.color.green(),
                        blue=point.color.blue(),
                        alpha=point.color.alpha()
                    )
                    color_stops.append(stop)
            
            # Get special colors from UI
            no_data_color = self.convert_qcolor_to_dict(self.no_data_color.property("color"))
            shadow_color = self.convert_qcolor_to_dict(self.shadow_color_box.property("color"))
            below_gradient_color = self.convert_qcolor_to_dict(self.below_gradient_color.property("color"))
            
            # Get gradient type
            gradient_type = "gradient"  # default
            if self.shaded_relief_radio.isChecked():
                gradient_type = "shaded_relief"
            elif self.posterized_radio.isChecked():
                gradient_type = "posterized"
            elif self.shad_grad_radio.isChecked():
                gradient_type = "shading_and_gradient"
            elif self.shad_post_radio.isChecked():
                gradient_type = "shading_and_posterized"
            
            # Create gradient object with all special colors
            gradient = Gradient(
                name=name,
                description="Live preview gradient",
                min_elevation=min_elev,
                max_elevation=max_elev,
                color_stops=color_stops,
                discrete=False,  # Use gradient_type parameter instead of discrete
                units=units,
                no_data_color=no_data_color,
                shadow_color=shadow_color,
                below_gradient_color=below_gradient_color,
                gradient_type=gradient_type,
                light_direction=self.light_direction_spin_box.value(),
                shading_intensity=self.shading_intensity_spin_box.value(),
                cast_shadows=self.draw_cast_shadows_check_box.isChecked(),
                shadow_drop_distance=self.shadow_drop_spin_box.value(),
                shadow_soft_edge=self.shadow_soft_edge_spin_box.value(),
                blending_mode='Hard Light',  # Always use Hard Light
                blending_strength=self.blending_strength_spin_box.value() if hasattr(self, 'blending_strength_spin_box') else 100,
                color_mode=self.color_mode_combo.currentText() if hasattr(self, 'color_mode_combo') else '8-bit'
            )
            
            return gradient
            
        except Exception as e:
            print(f"⚠️ Error building current gradient: {e}")
            return None
    
    def calculate_elevation_range_for_preview(self, gradient):
        """Calculate elevation range for preview based on gradient units (same logic as main window)"""
        gradient_units = getattr(gradient, 'units', 'meters')
        
        if gradient_units == 'percent':
            # Percentage mode: Use ACTUAL database elevation range
            # The gradient positions (0.0-1.0) represent percentages of the actual database range
            valid_data = self.preview_elevation_data[~np.isnan(self.preview_elevation_data)]
            if len(valid_data) > 0:
                actual_min = float(np.min(valid_data))
                actual_max = float(np.max(valid_data))
                print(f"🎯 Percent mode: Using actual database range {actual_min:.1f} to {actual_max:.1f}m")
                return actual_min, actual_max
            else:
                # Fallback if no valid data
                return gradient.min_elevation, gradient.max_elevation
                
        else:  # meters
            # Meters mode: Use directly
            return gradient.min_elevation, gradient.max_elevation
    
    def cancel_editing(self):
        """Cancel editing and close the window"""
        self.reject()

if __name__ == "__main__":
    # Test the gradient editor window
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Test with some sample gradient data
    sample_gradient = {
        'name': 'Test Gradient',
        'type': 'gradient',
        'num_colors': 8,
        'min_elevation': 0,
        'max_elevation': 1000,
        'units': 'meters'
    }
    
    window = GradientEditorWindow(gradient_data=sample_gradient)
    window.show()
    
    sys.exit(app.exec())