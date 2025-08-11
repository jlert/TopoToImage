#!/usr/bin/env python3
"""
DEM Visualizer - Dialog Helpers
Reusable dialog functions for user interaction
"""

from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
        QTextEdit, QMessageBox, QApplication
    )
    from PyQt6.QtCore import Qt
except ImportError:
    print("PyQt6 not available")
    import sys
    sys.exit(1)


def show_rasterio_install_dialog(parent, error_message):
    """Show user-friendly dialog for rasterio installation"""
    dialog = QDialog(parent)
    dialog.setWindowTitle("GeoTIFF Support Required")
    dialog.setFixedSize(500, 350)
    
    layout = QVBoxLayout(dialog)
    
    # Title
    title = QLabel("GeoTIFF files require additional software")
    title.setStyleSheet("font-weight: bold; font-size: 14px; color: #d32f2f;")
    layout.addWidget(title)
    
    # Explanation
    explanation = QLabel(
        "You're trying to open a GeoTIFF file (.tif/.tiff), but the required "
        "'rasterio' library is not installed.\n\n"
        "You have two options:"
    )
    explanation.setWordWrap(True)
    layout.addWidget(explanation)
    
    # Instructions
    instructions = QTextEdit()
    instructions.setReadOnly(True)
    instructions.setMaximumHeight(120)
    instructions.setPlainText(
        "OPTION 1: Install GeoTIFF support\n"
        "• Open Terminal/Command Prompt\n"
        "• Run: pip install rasterio\n"
        "• Restart the DEM Visualizer\n\n"
        "OPTION 2: Use alternative formats\n"
        "• Use .dem files (GTOPO30 format)\n"
        "• Use .bil files (SRTM format)\n"
        "• These work without additional software"
    )
    layout.addWidget(instructions)
    
    # Buttons
    button_layout = QHBoxLayout()
    
    # Copy command button
    copy_button = QPushButton("Copy Install Command")
    copy_button.clicked.connect(lambda: copy_to_clipboard("pip install rasterio", parent))
    button_layout.addWidget(copy_button)
    
    # Alternative formats button
    help_button = QPushButton("Show Supported Formats")
    help_button.clicked.connect(lambda: show_supported_formats_help(parent))
    button_layout.addWidget(help_button)
    
    # Close button
    close_button = QPushButton("OK")
    close_button.clicked.connect(dialog.accept)
    close_button.setDefault(True)
    button_layout.addWidget(close_button)
    
    layout.addLayout(button_layout)
    
    dialog.exec()


def copy_to_clipboard(text, parent):
    """Copy text to system clipboard"""
    clipboard = QApplication.clipboard()
    clipboard.setText(text)
    if hasattr(parent, 'statusBar'):
        parent.statusBar().showMessage("Command copied to clipboard!", 3000)


def show_supported_formats_help(parent):
    """Show information about supported file formats"""
    help_text = """
SUPPORTED DEM FILE FORMATS:

✅ .dem files (BIL format)
   • GTOPO30 global dataset
   • 30 arc-second resolution (~1km)
   • No additional software required
   • Example: gt30e020n40.dem

✅ .bil files (BIL format) 
   • SRTM dataset
   • 1 arc-second resolution (~30m)
   • No additional software required
   • Example: n00_e010_1arc_v3.bil

✅ .tif/.tiff files (GeoTIFF)
   • Industry standard format
   • Variable resolution
   • Requires: pip install rasterio
   • Example: gt30e020n40.tif

All formats support the same features:
• Terrain visualization
• Color gradient mapping
• Real-time preview generation
• Export capabilities
    """
    
    QMessageBox.information(parent, "Supported File Formats", help_text.strip())