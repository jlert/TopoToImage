#!/usr/bin/env python3
"""
DEM Visualizer - Gradient Browser Widget
Gradient selection and elevation control interface
"""

from pathlib import Path
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
        QListWidget, QGroupBox, QSpinBox, QComboBox, QCheckBox
    )
    from PyQt6.QtCore import Qt, pyqtSignal
except ImportError:
    print("PyQt6 not available")
    import sys
    sys.exit(1)


class GradientBrowserWidget(QWidget):
    """Right panel: Gradient browser and elevation controls"""
    
    gradient_selected = pyqtSignal(str)  # Emit selected gradient name
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Gradient list group
        gradient_group = QGroupBox("Gradient List")
        gradient_layout = QVBoxLayout(gradient_group)
        
        self.gradient_list = QListWidget()
        self.gradient_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)  # Allow multiple selection
        self.gradient_list.itemClicked.connect(self.gradient_item_clicked)
        gradient_layout.addWidget(self.gradient_list)
        
        # Gradient control buttons
        gradient_btn_layout = QHBoxLayout()
        
        self.new_gradient_btn = QPushButton("New Gradient")
        self.delete_gradient_btn = QPushButton("Delete Gradient")
        self.edit_gradient_btn = QPushButton("Edit Gradient")
        
        gradient_btn_layout.addWidget(self.new_gradient_btn)
        gradient_btn_layout.addWidget(self.delete_gradient_btn)
        gradient_btn_layout.addWidget(self.edit_gradient_btn)
        
        gradient_layout.addLayout(gradient_btn_layout)
        
        # List management buttons
        list_btn_layout = QHBoxLayout()
        
        self.move_up_btn = QPushButton("Move Up")
        self.move_down_btn = QPushButton("Down")
        self.sort_list_btn = QPushButton("Sort List")
        self.save_list_btn = QPushButton("Save List")
        
        list_btn_layout.addWidget(self.move_up_btn)
        list_btn_layout.addWidget(self.move_down_btn)
        list_btn_layout.addWidget(self.sort_list_btn)
        list_btn_layout.addWidget(self.save_list_btn)
        
        gradient_layout.addLayout(list_btn_layout)
        
        layout.addWidget(gradient_group)
        
        # Preview and controls group
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        # Preview image
        self.preview_label = QLabel("No preview")
        self.preview_label.setMinimumSize(150, 150)
        self.preview_label.setStyleSheet("border: 1px solid gray; background-color: white;")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.preview_label)
        
        # Scale controls
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("Scale:"))
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["1:24999", "1:50000", "1:100000", "1:250000"])
        scale_layout.addWidget(self.scale_combo)
        preview_layout.addLayout(scale_layout)
        
        # Min/Max elevation controls
        minmax_layout = QHBoxLayout()
        
        min_layout = QVBoxLayout()
        min_layout.addWidget(QLabel("Min"))
        self.min_elevation = QSpinBox()
        self.min_elevation.setRange(-500, 8000)
        self.min_elevation.setValue(0)
        min_layout.addWidget(self.min_elevation)
        
        max_layout = QVBoxLayout()
        max_layout.addWidget(QLabel("Max"))
        self.max_elevation = QSpinBox()
        self.max_elevation.setRange(-500, 8000)
        self.max_elevation.setValue(1000)
        max_layout.addWidget(self.max_elevation)
        
        minmax_layout.addLayout(min_layout)
        minmax_layout.addLayout(max_layout)
        preview_layout.addLayout(minmax_layout)
        
        # Gradient scaling options
        scaling_layout = QVBoxLayout()
        self.scale_to_crop = QCheckBox("Scale gradient to elevations found in crop area")
        self.scale_to_absolute = QCheckBox("Scale gradient absolute Max and Min")
        scaling_layout.addWidget(self.scale_to_crop)
        scaling_layout.addWidget(self.scale_to_absolute)
        preview_layout.addLayout(scaling_layout)
        
        layout.addWidget(preview_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("Preview")
        self.save_database_btn = QPushButton("Save Data Base")
        
        action_layout.addWidget(self.preview_btn)
        action_layout.addWidget(self.save_database_btn)
        
        layout.addLayout(action_layout)
        
        # Initialize with default gradients
        self.load_default_gradients()
    
    def load_default_gradients(self):
        """Load default gradient presets"""
        default_gradients = [
            "Blue green hills",
            "Congo no shadow",
            "Congo",
            "Desert bloom",
            "Drapes",
            "Green Hills + Shad",
            "Green Hills S + 5",
            "Green Hills Square",
            "Green high",
            "Green high--lands",
            "Green high--lands",
            "Green low",
            "Green low--lands",
            "Hammond Brown",
            "Hammond Dk + Sh.."
        ]
        
        for gradient in default_gradients:
            self.gradient_list.addItem(gradient)
    
    def gradient_item_clicked(self, item):
        """Handle gradient selection"""
        gradient_name = item.text()
        self.gradient_selected.emit(gradient_name)
    
    def get_selected_gradient(self):
        """Get the currently selected gradient name"""
        current_item = self.gradient_list.currentItem()
        if current_item:
            return current_item.text()
        return None