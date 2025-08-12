#!/usr/bin/env python3
"""
TopoToImage 4.0.0-beta.1 - Main Entry Point
Professional terrain visualization software
"""

import sys
import os
from pathlib import Path

def main():
    """Launch TopoToImage application"""
    try:
        # Add src directory to path for imports
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        
        # Import version info (now in src directory)
        from version import get_app_name_with_version, get_version_string, APP_NAME
        
        # Import the main application class
        from main_window_qt_designer import DEMVisualizerQtDesignerWindow
        from PyQt6.QtWidgets import QApplication
        
        print(f"🗺️ Starting {get_app_name_with_version()}...")
        print("📍 Recreating 1990s cartographic excellence")
        
        # Create PyQt application
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(get_version_string(include_v_prefix=False))
        app.setOrganizationName("TopoToImage")
        
        # Create and show main window
        window = DEMVisualizerQtDesignerWindow()
        window.show()
        
        # Start the application event loop
        sys.exit(app.exec())
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("🔧 Make sure all dependencies are installed:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()