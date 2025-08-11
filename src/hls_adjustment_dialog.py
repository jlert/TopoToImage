#!/usr/bin/env python3
"""
HLS Adjustment Dialog for DEM Visualizer
Provides Hue, Lightness, and Saturation adjustment controls similar to Photoshop
"""

import sys
import colorsys
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QApplication, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6 import uic

class HLSAdjustmentDialog(QDialog):
    """
    HLS (Hue, Lightness, Saturation) adjustment dialog
    
    Provides Photoshop-style color adjustment controls with:
    - Hue slider (-180° to +180°)
    - Lightness slider (-100% to +100%)
    - Saturation slider (-100% to +100%)
    - Radio buttons for "Current point only" vs "All colors"
    - Live preview updates
    """
    
    # Signal emitted when adjustments should be applied (for live preview)
    adjustments_changed = pyqtSignal(float, float, float, bool)  # hue, lightness, saturation, all_colors
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Load the UI file
        ui_file = Path(__file__).parent.parent / "ui" / "hls_adjustment_dialog.ui"
        if not ui_file.exists():
            QMessageBox.critical(self, "Error", f"UI file not found: {ui_file}")
            return
            
        try:
            uic.loadUi(str(ui_file), self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load UI file: {e}")
            return
        
        # Store original values for reset
        self.original_hue = 0
        self.original_lightness = 0
        self.original_saturation = 0
        
        # Connect signals
        self.setup_connections()
        
        # Set initial values
        self.reset_values()
        
    def setup_connections(self):
        """Connect all the UI signals to their handlers"""
        
        # Slider and spinbox synchronization
        self.hue_slider.valueChanged.connect(self.hue_spinbox.setValue)
        self.hue_spinbox.valueChanged.connect(self.hue_slider.setValue)
        
        self.lightness_slider.valueChanged.connect(self.lightness_spinbox.setValue)
        self.lightness_spinbox.valueChanged.connect(self.lightness_slider.setValue)
        
        self.saturation_slider.valueChanged.connect(self.saturation_spinbox.setValue)
        self.saturation_spinbox.valueChanged.connect(self.saturation_slider.setValue)
        
        # Live preview updates
        self.hue_slider.valueChanged.connect(self.on_adjustment_changed)
        self.lightness_slider.valueChanged.connect(self.on_adjustment_changed)
        self.saturation_slider.valueChanged.connect(self.on_adjustment_changed)
        self.current_point_radio.toggled.connect(self.on_adjustment_changed)
        self.all_colors_radio.toggled.connect(self.on_adjustment_changed)
        
        # Buttons
        self.reset_button.clicked.connect(self.reset_values)
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button.clicked.connect(self.accept)
        
    def reset_values(self):
        """Reset all sliders to their default values"""
        self.hue_slider.setValue(0)
        self.lightness_slider.setValue(0)
        self.saturation_slider.setValue(0)
        
        # Trigger update
        self.on_adjustment_changed()
        
    def on_adjustment_changed(self):
        """Called when any adjustment value changes - emits signal for live preview"""
        hue_adjustment = self.hue_slider.value()  # -180 to +180
        lightness_adjustment = self.lightness_slider.value()  # -100 to +100
        saturation_adjustment = self.saturation_slider.value()  # -100 to +100
        all_colors = self.all_colors_radio.isChecked()
        
        # Emit signal for live preview
        self.adjustments_changed.emit(hue_adjustment, lightness_adjustment, saturation_adjustment, all_colors)
        
    def get_adjustments(self):
        """Get the current adjustment values"""
        return {
            'hue': self.hue_slider.value(),
            'lightness': self.lightness_slider.value(),
            'saturation': self.saturation_slider.value(),
            'all_colors': self.all_colors_radio.isChecked()
        }
    
    def set_adjustments(self, hue=0, lightness=0, saturation=0, all_colors=True):
        """Set the adjustment values"""
        self.hue_slider.setValue(hue)
        self.lightness_slider.setValue(lightness)
        self.saturation_slider.setValue(saturation)
        
        if all_colors:
            self.all_colors_radio.setChecked(True)
        else:
            self.current_point_radio.setChecked(True)

def apply_hls_adjustment(color: QColor, hue_shift: float, lightness_shift: float, saturation_shift: float) -> QColor:
    """
    Apply HLS adjustments to a color
    
    Args:
        color: Input QColor
        hue_shift: Hue shift in degrees (-180 to +180)
        lightness_shift: Lightness adjustment percentage (-100 to +100)
        saturation_shift: Saturation adjustment percentage (-100 to +100)
        
    Returns:
        New QColor with adjustments applied
    """
    # Convert QColor to RGB (0-1 range)
    r = color.red() / 255.0
    g = color.green() / 255.0
    b = color.blue() / 255.0
    
    # Convert RGB to HLS
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    
    # Apply hue shift (convert degrees to 0-1 range)
    h = (h + hue_shift / 360.0) % 1.0
    
    # Apply lightness shift
    l = max(0.0, min(1.0, l + lightness_shift / 100.0))
    
    # Apply saturation shift
    s = max(0.0, min(1.0, s + saturation_shift / 100.0))
    
    # Convert back to RGB
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    
    # Convert to 0-255 range and create new QColor
    return QColor(
        int(r * 255),
        int(g * 255),
        int(b * 255),
        color.alpha()  # Preserve alpha
    )

# Test application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    def test_adjustment(hue, lightness, saturation, all_colors):
        """Test function for the adjustment signal"""
        print(f"HLS Adjustment: Hue={hue}°, Lightness={lightness}%, Saturation={saturation}%, All Colors={all_colors}")
        
        # Test color adjustment
        test_color = QColor(255, 128, 64)  # Orange color
        adjusted_color = apply_hls_adjustment(test_color, hue, lightness, saturation)
        print(f"  Test color RGB({test_color.red()},{test_color.green()},{test_color.blue()}) -> RGB({adjusted_color.red()},{adjusted_color.green()},{adjusted_color.blue()})")
    
    # Create and show dialog
    dialog = HLSAdjustmentDialog()
    dialog.adjustments_changed.connect(test_adjustment)
    
    result = dialog.exec()
    if result == QDialog.DialogCode.Accepted:
        adjustments = dialog.get_adjustments()
        print(f"Final adjustments: {adjustments}")
    else:
        print("Dialog cancelled")
    
    sys.exit(0)