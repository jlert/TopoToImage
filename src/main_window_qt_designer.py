#!/usr/bin/env python3
"""
Main Window Qt Designer Integration - Complete Version
Loads the main_window_complete.ui file and provides the same interface as the original main window
"""

import sys
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QApplication, QMessageBox
from PyQt6.QtCore import QTimer

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller bundled app"""
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle
        # Resources are in Contents/Resources/, not in _MEIPASS directly
        bundle_resources = Path(sys._MEIPASS).parent / "Resources"
        
        # Handle different resource types in bundle
        if relative_path.endswith('.ui'):
            # UI files are in Contents/Resources/ui/
            return bundle_resources / "ui" / relative_path
        elif relative_path.startswith('gradients/') or relative_path == 'gradients.json':
            # Gradients are in Contents/Resources/gradients/
            if relative_path == 'gradients.json':
                return bundle_resources / "gradients" / "gradients.json"
            else:
                return bundle_resources / "gradients" / relative_path.replace('gradients/', '')
        elif relative_path.startswith('maps/') or relative_path == 'maps':
            # Maps are in Contents/Resources/maps/
            if relative_path == 'maps':
                return bundle_resources / "maps"
            else:
                return bundle_resources / "maps" / relative_path.replace('maps/', '')
        elif relative_path.startswith('preview_icon_databases/') or relative_path == 'preview_icon_databases':
            # Preview icons are in Contents/Resources/preview_icon_databases/
            if relative_path == 'preview_icon_databases':
                return bundle_resources / "preview_icon_databases"
            else:
                return bundle_resources / "preview_icon_databases" / relative_path.replace('preview_icon_databases/', '')
        else:
            # Other resources are directly in Resources
            return bundle_resources / relative_path
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

def check_essential_maps():
    """Check if essential map files exist and show error dialog if missing"""
    essential_maps = [
        "maps/default_background_map.svg"
    ]
    
    missing_maps = []
    for map_path in essential_maps:
        if not get_resource_path(map_path).exists():
            missing_maps.append(map_path)
    
    if missing_maps:
        error_message = f"""Critical Error: Essential map files are missing from the application bundle:

{chr(10).join('• ' + m for m in missing_maps)}

This indicates a corrupted installation or missing resources. 

Please:
1. Verify the application was built correctly
2. Check that all assets are included in the bundle
3. Download a fresh copy if this is a distributed version
4. Contact support if the problem persists

The application cannot function without these essential map files."""
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("TopoToImage - Critical Error")
        msg.setText("Essential map files are missing")
        msg.setDetailedText(error_message)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        
        print("❌ Critical Error: Essential map files missing")
        for missing_map in missing_maps:
            print(f"   Missing: {missing_map}")
        sys.exit(1)
        
    print("✅ All essential map files found")

def setup_debug_logging():
    """Setup debug logging for bundled app troubleshooting"""
    # Create logs directory in user's home directory for bundled app
    if hasattr(sys, '_MEIPASS'):
        log_dir = Path.home() / "TopoToImage_Debug"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "preview_debug.log"
    else:
        # In development, log to dev-workspace
        project_root = Path(__file__).parent.parent.parent  # Go up from src/ to claude-code/
        dev_workspace = project_root / "topoToimage-dev-workspace" / "debug-logs"
        dev_workspace.mkdir(parents=True, exist_ok=True)
        log_file = dev_workspace / "preview_debug.log"
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w'),  # Overwrite each run
            logging.StreamHandler(sys.stdout)  # Also print to console
        ]
    )
    
    logger = logging.getLogger('TopoToImage')
    logger.info(f"🚀 TopoToImage Debug Logging Started")
    logger.info(f"📁 Log file: {log_file}")
    logger.info(f"🗂️ Is bundled app: {hasattr(sys, '_MEIPASS')}")
    if hasattr(sys, '_MEIPASS'):
        logger.info(f"📦 Bundle path: {sys._MEIPASS}")
    
    return logger

# Initialize debug logging
debug_logger = setup_debug_logging()

# Import existing modules
from dem_reader import DEMReader
from multi_tile_loader import MultiTileLoader
from gradient_system import GradientManager
from terrain_renderer import TerrainRenderer
from recent_databases import recent_db_manager, StartupDatabaseDialog
from coordinate_converter import CoordinateConverter
from export_controls_logic import ExportControlsLogic, LockType, Units
from map_widgets import MapDisplayWidget, WorldMapWidget
from gradient_widgets import GradientBrowserWidget
from gradient_editor_window import GradientEditorWindow
from dialog_helpers import show_rasterio_install_dialog, copy_to_clipboard
from preview_window import TerrainPreviewWindow
from distance_formatter import format_distance_km_miles
from key_file_generator import KeyFileGenerator, create_key_filename
from meridian_utils import normalize_longitude, calculate_longitude_span


class DEMVisualizerQtDesignerWindow(QMainWindow):
    """Main application window using Qt Designer layout"""
    
    def __init__(self):
        super().__init__()
        
        # Check for essential map files before initializing anything else
        check_essential_maps()
        
        self.current_dem_file = None
        self.current_database_info = None  # Information about currently loaded database
        self.multi_tile_loader = MultiTileLoader()
        # Initialize gradient manager with user-writable path (bundle-safe)
        self.initialize_gradient_system()
        self.terrain_renderer = TerrainRenderer(self.gradient_manager)
        self.key_file_generator = KeyFileGenerator(self.gradient_manager, self.terrain_renderer)
        self.updating_fields = False  # Flag to prevent signal recursion during field updates
        self.export_logic = ExportControlsLogic()  # Export controls calculation logic
        
        # Preview database cycling state
        self.preview_databases = []  # List of available preview database files
        self.current_preview_index = 0  # Index of currently active preview database
        
        # Preview window
        self.preview_window = None  # Will be created when first needed
        
        # Load the UI file
        self.load_ui()
        self.setup_menu()
        self.setup_status_bar()
        
        # Replace the placeholder map widget with the actual WorldMapWidget
        self.setup_world_map()
        
        # Connect signals
        self.connect_signals()
        
        # Initialize export controls with default values (before loading gradients)
        self.initialize_export_controls()
        
        # Scan and setup preview databases for cycling (BEFORE loading gradients)
        self.scan_preview_databases()
        
        # Load gradients into browser
        self.load_gradients_into_browser()
        
        # Handle startup database loading (must be after UI setup)
        QTimer.singleShot(100, self.handle_startup_database_loading)
    
    def load_ui(self):
        """Load the Qt Designer .ui file"""
        ui_file = get_resource_path("main_window_complete.ui")
        uic.loadUi(ui_file, self)
        
        print("✅ Successfully loaded main_window_complete.ui")
        print(f"Window size: {self.width()}x{self.height()}")
        
        # Fix widget references that may not be automatically accessible
        self.fix_widget_references()
        
        # Log all the widgets we have access to (after fixing references)
        self.log_available_widgets()
    
    def fix_widget_references(self):
        """Fix widget references that aren't automatically accessible"""
        try:
            # Find widgets by searching the entire widget tree
            from PyQt6.QtWidgets import QComboBox, QListWidget, QDoubleSpinBox, QSpinBox, QRadioButton, QLabel, QCheckBox
            
            # Find combo boxes
            all_combos = self.findChildren(QComboBox)
            print(f"Found {len(all_combos)} combo boxes:")
            for combo in all_combos:
                name = combo.objectName()
                print(f"  - {name}")
                if name == "export_type_combo":
                    self.export_type_combo = combo
                    print(f"    ✅ Assigned export_type_combo")
                elif name == "export_scale_combo":
                    self.export_scale_combo = combo
                    print(f"    ✅ Assigned export_scale_combo")
            
            # Find list widgets
            all_lists = self.findChildren(QListWidget)
            print(f"Found {len(all_lists)} list widgets:")
            for list_widget in all_lists:
                name = list_widget.objectName()
                print(f"  - {name}")
                if name == "gradient_list":
                    self.gradient_list = list_widget
                    print(f"    ✅ Assigned gradient_list")
            
            # Find spinboxes
            all_double_spins = self.findChildren(QDoubleSpinBox)
            all_spins = self.findChildren(QSpinBox)
            print(f"Found {len(all_double_spins)} double spinboxes and {len(all_spins)} spinboxes:")
            for spin in all_double_spins + all_spins:
                name = spin.objectName()
                print(f"  - {name}")
                if name == "export_scale_spinbox":
                    self.export_scale_spinbox = spin
                    print(f"    ✅ Assigned export_scale_spinbox")
                elif name == "max_elevation":
                    self.max_elevation = spin
                    print(f"    ✅ Assigned max_elevation")
                elif name == "min_elevation":
                    self.min_elevation = spin
                    print(f"    ✅ Assigned min_elevation")
            
            # Find labels (including preview label and unit labels)
            all_labels = self.findChildren(QLabel)
            print(f"Found {len(all_labels)} labels:")
            for label in all_labels:
                name = label.objectName()
                print(f"  - {name}")
                if 'preview' in name.lower():
                    self.preview_label = label
                    print(f"    ✅ Assigned preview_label: {name}")
                elif name == 'width_unit_label':
                    self.width_unit_label = label
                    print(f"    ✅ Assigned width_unit_label")
                elif name == 'height_unit_label':
                    self.height_unit_label = label
                    print(f"    ✅ Assigned height_unit_label")
                elif name == 'resolution_unit_label':
                    self.resolution_unit_label = label
                    print(f"    ✅ Assigned resolution_unit_label")
            
            # Find radio buttons that might not be accessible
            all_radios = self.findChildren(QRadioButton)
            radio_mapping = {
                'lock_width_radio': 'lock_width_radio',
                'lock_height_radio': 'lock_height_radio', 
                'lock_resolution_radio': 'lock_resolution_radio',
                'inches_radio': 'inches_radio',
                'picas_radio': 'picas_radio',
                'points_radio': 'points_radio',
                'cm_radio': 'cm_radio',
                        'meters_radio': 'meters_radio',
                'scale_to_crop_radio': 'scale_to_crop_radio',
                'scale_to_max_min_radio': 'scale_to_max_min_radio',
                'decimal_radio': 'decimal_radio',
                'dms_radio': 'dms_radio'
            }
            
            print(f"Checking {len(all_radios)} radio buttons for missing references:")
            for radio in all_radios:
                name = radio.objectName()
                if name in radio_mapping:
                    if not hasattr(self, name):
                        setattr(self, name, radio)
                        print(f"    ✅ Assigned {name}")
                    else:
                        print(f"    ℹ️ {name} already available")
            
            # Find checkboxes
            all_checkboxes = self.findChildren(QCheckBox)
            print(f"Found {len(all_checkboxes)} checkboxes:")
            for checkbox in all_checkboxes:
                name = checkbox.objectName()
                print(f"  - {name}")
                if name == "key_file_export_check_box":
                    self.key_file_export_check_box = checkbox
                    print(f"    ✅ Assigned key_file_export_check_box")
                    
            print("✅ Fixed widget references")
            
            # Quick check of the assigned widgets
            print(f"Post-assignment check:")
            critical_widgets = ['export_type_combo', 'export_scale_combo', 'gradient_list', 'export_scale_spinbox']
            for widget_name in critical_widgets:
                print(f"  {widget_name}: {'✅ Available' if hasattr(self, widget_name) else '❌ Missing'}")
            
        except Exception as e:
            print(f"❌ Error fixing widget references: {e}")
            import traceback
            traceback.print_exc()
    
    def log_available_widgets(self):
        """Log all the widgets loaded from the UI file for debugging"""
        important_widgets = [
            # Map
            'world_map',
            # Coordinates
            'coordinates_widget', 'north_edit', 'south_edit', 'west_edit', 'east_edit',
            'decimal_radio', 'dms_radio',
            # Database info
            'database_info_groupbox', 'export_file_info_groupbox',
            # Export controls
            'export_controls_widget', 'export_type_combo', 'export_scale_combo', 'export_scale_spinbox',
            'width_edit', 'height_edit', 'resolution_edit',
            'lock_width_radio', 'lock_height_radio', 'lock_resolution_radio',
            'inches_radio', 'picas_radio', 'points_radio', 'cm_radio',
            # Gradient controls
            'gradient_controls_widget', 'gradient_list', 'new_gradient_btn', 'edit_gradient_btn', 'delete_gradient_btn',
            'max_elevation', 'min_elevation', 'meters_radio',
            'scale_to_crop_radio', 'scale_to_max_min_radio', 'preview_label',
            # Bottom buttons
            'preview_btn', 'export_btn'
        ]
        
        print("\n=== Widget Availability Check ===")
        for widget_name in important_widgets:
            # Check if widget is available as an attribute
            widget = getattr(self, widget_name, None)
            status = "✅" if widget else "❌"
            print(f"{status} {widget_name}: {type(widget).__name__ if widget else 'Not found'}")
        
        # Check database info labels specifically
        print("\n=== Database Info Labels ===")
        db_labels = [
            'width_db_label', 'height_db_label', 'pix_deg_db_label',
            'west_db_label', 'north_db_label', 'east_db_label', 'south_db_label',
            'size_db_label', 'pxheight_db_label'
        ]
        for label_name in db_labels:
            label = getattr(self, label_name, None)
            status = "✅" if label else "❌"
            print(f"{status} {label_name}: {type(label).__name__ if label else 'Not found'}")
        
        # Check export file info labels
        print("\n=== Export File Info Labels ===")
        export_labels = [
            'width_export_label_2', 'height_export_label_2', 'pix_deg_export_label_2',
            'west_export_label_2', 'north_export_label_2', 'east_export_label_2', 'south_export_label_2',
            'size_export_label_2', 'pxheight_export_label_2'
        ]
        for label_name in export_labels:
            label = getattr(self, label_name, None)
            status = "✅" if label else "❌"
            print(f"{status} {label_name}: {type(label).__name__ if label else 'Not found'}")
    
    def setup_world_map(self):
        """Replace the placeholder map widget with the actual WorldMapWidget"""
        try:
            # Get the placeholder widget and its parent layout
            placeholder = self.world_map
            parent_widget = placeholder.parent()
            placeholder_geometry = placeholder.geometry()
            placeholder_style = placeholder.styleSheet()
            
            print(f"Placeholder geometry: {placeholder_geometry}")
            print(f"Placeholder parent: {parent_widget}")
            
            # Remove the placeholder first
            placeholder.hide()
            placeholder.deleteLater()
            
            # Create the actual WorldMapWidget
            self.world_map = WorldMapWidget()
            self.world_map.setParent(parent_widget)
            self.world_map.setGeometry(placeholder_geometry)
            self.world_map.setStyleSheet(placeholder_style)
            
            # Force the widget to be visible and properly displayed
            self.world_map.show()
            self.world_map.setVisible(True)
            self.world_map.raise_()
            
            # Initialize the background map
            if hasattr(self.world_map, 'initialize_background'):
                self.world_map.initialize_background()
            
            # Force redraw
            self.world_map.repaint()
            self.world_map.update()
            
            print(f"New map geometry: {self.world_map.geometry()}")
            print(f"New map visible: {self.world_map.isVisible()}")
            print(f"New map parent: {self.world_map.parent()}")
            print("✅ Successfully replaced placeholder with WorldMapWidget")
            
        except Exception as e:
            print(f"❌ Error setting up world map: {e}")
            import traceback
            traceback.print_exc()
    
    def setup_menu(self):
        """Setup the application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = file_menu.addAction("Open Elevation Database...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_dem_file)
        
        open_folder_action = file_menu.addAction("Open Elevation Database Folder...")
        open_folder_action.setShortcut("Ctrl+Shift+O")
        open_folder_action.triggered.connect(self.open_database_folder)
        
        create_multifile_action = file_menu.addAction("Create Multi-File Database...")
        create_multifile_action.setShortcut("Ctrl+Shift+N")
        create_multifile_action.triggered.connect(self.create_multi_file_database)
        
        file_menu.addSeparator()
        
        reveal_action = file_menu.addAction("Reveal Database in Finder")
        reveal_action.setShortcut("Ctrl+R")
        reveal_action.triggered.connect(self.reveal_database_in_finder)
        
        # Recent Databases submenu
        self.recent_databases_menu = file_menu.addMenu("Recent Databases")
        self.setup_recent_databases_menu()
        
        file_menu.addSeparator()
        
        # Export menu items
        save_image_action = file_menu.addAction("Save Image File...")
        save_image_action.setShortcut("Ctrl+S")
        save_image_action.triggered.connect(self.save_image_file)
        
        export_db_action = file_menu.addAction("Export Elevation Database...")
        export_db_action.setShortcut("Ctrl+Shift+E")
        export_db_action.triggered.connect(self.show_export_elevation_database_dialog)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        # Select All action - select full database bounds
        from PyQt6.QtGui import QAction, QKeySequence
        select_all_action = QAction("Select All", self)
        # Use Meta+D (Command+D on Mac) and Ctrl+D (for other platforms)
        select_all_action.setShortcuts([QKeySequence("Meta+D"), QKeySequence("Ctrl+D")])
        select_all_action.triggered.connect(self.select_all_database)
        edit_menu.addAction(select_all_action)
        
        # Disable macOS system services for Edit menu (Writing Tools, AutoFill, etc.)
        # These are automatically added by macOS but not relevant to TopoToImage
        try:
            # Method 1: Set the menu to not accept system services
            edit_menu.setProperty("NSMenu.UserInterfaceItemIdentifier", "TopoToImageEditMenu")
            
            # Method 2: Try to disable automatic services
            from PyQt6.QtCore import QCoreApplication
            app = QCoreApplication.instance()
            if app and hasattr(app, 'setAutomaticMenuPrepareHandlingEnabled'):
                # Disable automatic menu item additions for this session
                app.setAutomaticMenuPrepareHandlingEnabled(False)
                
        except (ImportError, AttributeError):
            # If methods not available, the system items will still appear
            # but at least we tried to disable them
            pass
        
        
        # Gradients menu (Gradient Management)
        gradients_menu = menubar.addMenu("Gradients")
        
        # New Gradient
        new_gradient_action = gradients_menu.addAction("New Gradient")
        new_gradient_action.setShortcut("Ctrl+G")
        new_gradient_action.triggered.connect(self.open_new_gradient_editor)
        
        # Edit Gradient  
        edit_gradient_action = gradients_menu.addAction("Edit Gradient")
        edit_gradient_action.setShortcut("Ctrl+E")
        edit_gradient_action.triggered.connect(self.open_edit_gradient_editor)
        
        # Delete Gradient
        delete_gradient_action = gradients_menu.addAction("Delete Gradient")
        delete_gradient_action.setShortcut("Delete")
        delete_gradient_action.triggered.connect(self.delete_selected_gradient)
        
        gradients_menu.addSeparator()
        
        # Move Up
        move_up_action = gradients_menu.addAction("Move Up")
        move_up_action.setShortcut("Ctrl+Up")
        move_up_action.triggered.connect(self.move_gradient_up)
        
        # Move Down
        move_down_action = gradients_menu.addAction("Move Down") 
        move_down_action.setShortcut("Ctrl+Down")
        move_down_action.triggered.connect(self.move_gradient_down)
        
        gradients_menu.addSeparator()
        
        # Sort List
        sort_list_action = gradients_menu.addAction("Sort List")
        sort_list_action.setShortcut("Ctrl+L")
        sort_list_action.triggered.connect(self.sort_gradients_alphabetically)
        
        gradients_menu.addSeparator()
        
        # Save List
        save_list_action = gradients_menu.addAction("Save List")
        save_list_action.setShortcut("Ctrl+Shift+S")
        save_list_action.triggered.connect(self.save_gradient_list_to_file)
        
        # Load List
        load_list_action = gradients_menu.addAction("Load List")
        load_list_action.setShortcut("Ctrl+Shift+L")
        load_list_action.triggered.connect(self.load_gradient_list_from_file)
        
        # Preview Icon menu
        preview_menu = menubar.addMenu("Preview Icon")
        
        # Create preview icon from selection
        self.create_preview_action = preview_menu.addAction("Create Preview Icon from Selection")
        self.create_preview_action.setShortcut("Ctrl+Shift+P")
        self.create_preview_action.triggered.connect(self.menu_create_preview_icon_from_selection)
        
        # Next preview icon
        self.next_preview_action = preview_menu.addAction("Next Preview Icon")
        self.next_preview_action.setShortcut("Ctrl+Shift+Right")
        self.next_preview_action.triggered.connect(self.menu_next_preview_icon)
        
        preview_menu.addSeparator()
        
        # Delete current preview icon
        self.delete_preview_action = preview_menu.addAction("Delete Current Preview Icon")
        self.delete_preview_action.setShortcut("Ctrl+Shift+Delete")
        self.delete_preview_action.triggered.connect(self.menu_delete_current_preview_icon)
        
        # Store menu actions for later state updates
        self.preview_menu_actions = {
            'create': self.create_preview_action,
            'next': self.next_preview_action, 
            'delete': self.delete_preview_action
        }
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        user_guide_action = help_menu.addAction("Open User Guide...")
        user_guide_action.triggered.connect(self.open_user_guide)
        
        help_menu.addSeparator()
        
        help_menu.addAction("About DEM Visualizer")
        
        print("✅ Menu setup complete")
    
    def setup_status_bar(self):
        """Setup the status bar"""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        print("✅ Status bar setup complete")
    
    def connect_signals(self):
        """Connect all widget signals"""
        try:
            # Connect map selection to coordinate field updates
            self.world_map.selection_changed.connect(self.on_selection_changed)
            
            # Connect map context menu for creating preview icons
            self.world_map.create_preview_requested.connect(self.create_preview_icon_from_selection)
            
            # Connect coordinate field changes to map selection updates
            self.north_edit.editingFinished.connect(self.on_coordinate_field_changed)
            self.north_edit.returnPressed.connect(self.on_coordinate_field_changed)
            self.south_edit.editingFinished.connect(self.on_coordinate_field_changed)
            self.south_edit.returnPressed.connect(self.on_coordinate_field_changed)
            self.west_edit.editingFinished.connect(self.on_coordinate_field_changed)
            self.west_edit.returnPressed.connect(self.on_coordinate_field_changed)
            self.east_edit.editingFinished.connect(self.on_coordinate_field_changed)
            self.east_edit.returnPressed.connect(self.on_coordinate_field_changed)
            
            # Connect gradient selection
            if hasattr(self, 'gradient_list'):
                self.gradient_list.itemClicked.connect(self.on_gradient_selected)
                self.gradient_list.currentItemChanged.connect(lambda current, previous: self.on_gradient_selected(current) if current else None)
            
            # Connect gradient editor buttons
            if hasattr(self, 'new_gradient_btn'):
                self.new_gradient_btn.clicked.connect(self.open_new_gradient_editor)
            if hasattr(self, 'edit_gradient_btn'):
                self.edit_gradient_btn.clicked.connect(self.open_edit_gradient_editor)
            if hasattr(self, 'delete_gradient_btn'):
                self.delete_gradient_btn.clicked.connect(self.delete_selected_gradient)
            
            # Connect gradient list management buttons
            if hasattr(self, 'move_up_btn'):
                self.move_up_btn.clicked.connect(self.move_gradient_up)
            if hasattr(self, 'move_down_btn'):
                self.move_down_btn.clicked.connect(self.move_gradient_down)
            if hasattr(self, 'sort_list_btn'):
                self.sort_list_btn.clicked.connect(self.sort_gradients_alphabetically)
            if hasattr(self, 'save_list_btn'):
                self.save_list_btn.clicked.connect(self.save_gradient_list_to_file)
            if hasattr(self, 'load_list_btn'):
                self.load_list_btn.clicked.connect(self.load_gradient_list_from_file)
            
            # Connect coordinate format toggle (using the button group)
            from PyQt6.QtWidgets import QButtonGroup
            self.coord_format_group = QButtonGroup(self)
            self.coord_format_group.addButton(self.decimal_radio)
            self.coord_format_group.addButton(self.dms_radio)
            self.coord_format_group.buttonClicked.connect(self.on_coordinate_format_changed)
            
            # Export type combo no longer exists - removed for separated export functions
            
            # Export scale controls
            if hasattr(self, 'export_scale_combo'):
                self.export_scale_combo.currentTextChanged.connect(self.on_export_scale_combo_changed)
            if hasattr(self, 'export_scale_spinbox'):
                self.export_scale_spinbox.valueChanged.connect(self.on_export_scale_spinbox_changed)
            
            # Export dimension fields (connect to editingFinished to avoid constant updates)
            if hasattr(self, 'width_edit'):
                self.width_edit.editingFinished.connect(self.on_width_changed)
            if hasattr(self, 'height_edit'):
                self.height_edit.editingFinished.connect(self.on_height_changed)
            if hasattr(self, 'resolution_edit'):
                self.resolution_edit.editingFinished.connect(self.on_resolution_changed)
            
            # Lock radio buttons group
            self.lock_group = QButtonGroup(self)
            if hasattr(self, 'lock_width_radio'):
                self.lock_group.addButton(self.lock_width_radio)
            if hasattr(self, 'lock_height_radio'):
                self.lock_group.addButton(self.lock_height_radio)
            if hasattr(self, 'lock_resolution_radio'):
                self.lock_group.addButton(self.lock_resolution_radio)
            self.lock_group.buttonClicked.connect(self.on_lock_option_changed)
            
            # Units radio buttons group
            self.units_group = QButtonGroup(self)
            if hasattr(self, 'inches_radio'):
                self.units_group.addButton(self.inches_radio)
            if hasattr(self, 'picas_radio'):
                self.units_group.addButton(self.picas_radio)
            if hasattr(self, 'points_radio'):
                self.units_group.addButton(self.points_radio)
            if hasattr(self, 'cm_radio'):
                self.units_group.addButton(self.cm_radio)
            self.units_group.buttonClicked.connect(self.on_units_changed)
            
            # Elevation controls
            if hasattr(self, 'max_elevation'):
                self.max_elevation.valueChanged.connect(self.on_elevation_range_changed)
            if hasattr(self, 'min_elevation'):
                self.min_elevation.valueChanged.connect(self.on_elevation_range_changed)
            
            # Elevation units radio buttons group (meters only)
            self.elevation_units_group = QButtonGroup(self)
            if hasattr(self, 'meters_radio'):
                self.elevation_units_group.addButton(self.meters_radio)
            self.elevation_units_group.buttonClicked.connect(self.on_elevation_units_changed)
            
            # Scale mode radio buttons group
            self.scale_mode_group = QButtonGroup(self)
            if hasattr(self, 'scale_to_crop_radio'):
                self.scale_mode_group.addButton(self.scale_to_crop_radio)
            if hasattr(self, 'scale_to_max_min_radio'):
                self.scale_mode_group.addButton(self.scale_to_max_min_radio)
            self.scale_mode_group.buttonClicked.connect(self.on_scale_mode_changed)
            
            # Preview and Export buttons
            self.preview_btn.clicked.connect(self.generate_terrain_preview)
            
            # Connect new export buttons
            if hasattr(self, 'save_image_btn'):
                self.save_image_btn.clicked.connect(self.save_image_file)
            if hasattr(self, 'export_elevation_btn'):
                self.export_elevation_btn.clicked.connect(self.show_export_elevation_database_dialog)
            
            print("✅ Signal connections complete")
            
        except Exception as e:
            print(f"❌ Error connecting signals: {e}")
            import traceback
            traceback.print_exc()
    
    def load_gradients_into_browser(self, select_gradient_name=None):
        """Load gradients into the gradient list
        
        Args:
            select_gradient_name: Optional name of gradient to select after loading
        """
        try:
            if hasattr(self, 'gradient_list'):
                # Clear existing items
                self.gradient_list.clear()
                
                # Load gradients from the gradient manager
                gradients = self.gradient_manager.get_gradient_names()
                
                for gradient_name in gradients:
                    self.gradient_list.addItem(gradient_name)
                
                # Select specified gradient or first gradient if available
                if self.gradient_list.count() > 0:
                    selected_row = 0  # Default to first
                    
                    # Try to find and select the specified gradient
                    if select_gradient_name:
                        for i in range(self.gradient_list.count()):
                            if self.gradient_list.item(i).text() == select_gradient_name:
                                selected_row = i
                                break
                    
                    self.gradient_list.setCurrentRow(selected_row)
                    
                    # Ensure the selection is processed
                    from PyQt6.QtCore import QCoreApplication
                    QCoreApplication.processEvents()
                    
                    # Update controls based on the selected gradient
                    selected_gradient_name = self.gradient_list.item(selected_row).text()
                    self.update_controls_from_gradient(selected_gradient_name)
                    
                    # Trigger preview for the selected gradient
                    self.update_gradient_preview()
                
                print(f"✅ Loaded {len(gradients)} gradients into browser")
                if select_gradient_name:
                    print(f"✅ Selected gradient: {select_gradient_name}")
            else:
                print("❌ gradient_list not found")
                
        except Exception as e:
            print(f"❌ Error loading gradients: {e}")
            import traceback
            traceback.print_exc()
    
    def initialize_gradient_system(self):
        """Initialize gradient system with proper user data path handling"""
        try:
            # User gradient file (writable location)
            user_gradients = get_writable_data_path("gradients.json")
            
            # If user gradients don't exist, copy from bundle defaults
            if not user_gradients.exists():
                print("🎯 First run detected: Setting up user gradient system...")
                
                # Ensure user data directory exists
                user_gradients.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy default gradients from bundle
                bundle_gradients = get_resource_path("gradients.json")
                if bundle_gradients.exists():
                    shutil.copy2(bundle_gradients, user_gradients)
                    print(f"✅ Copied default gradients: {bundle_gradients} → {user_gradients}")
                else:
                    print("⚠️  Bundle gradients not found - gradient manager will create defaults")
            
            # Initialize gradient manager with user-writable file
            print(f"🎨 Initializing gradient system with: {user_gradients}")
            self.gradient_manager = GradientManager(user_gradients)
            
        except Exception as e:
            print(f"❌ Error initializing gradient system: {e}")
            # Fallback to bundle gradients if user setup fails
            bundle_gradients = get_resource_path("gradients.json")
            print(f"🔄 Falling back to bundle gradients: {bundle_gradients}")
            self.gradient_manager = GradientManager(bundle_gradients)
    
    def is_first_run(self):
        """Check if this is the first run using a dedicated flag file in home directory"""
        try:
            # Check for flag file in the user's home TopoToImage_Data directory
            user_data_dir = Path.home() / "TopoToImage_Data"
            first_run_flag = user_data_dir / ".first_run_complete"
            
            # If flag file doesn't exist, it's first run
            return not first_run_flag.exists()
                
        except Exception as e:
            print(f"⚠️  Error checking first run status: {e}")
            return False  # Assume not first run to avoid errors
    
    def setup_first_run_experience(self):
        """Set up first-run experience with sample data and user directory"""
        try:
            print("🚀 Setting up first-run experience...")
            
            # Always use home directory for first-run, even in development mode
            user_data_dir = Path.home() / "TopoToImage_Data"
            user_data_dir.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created user data directory: {user_data_dir}")
            
            # Create subdirectories
            user_preview_dir = user_data_dir / "preview_icon_databases"
            user_preview_dir.mkdir(exist_ok=True)
            (user_data_dir / "sample_data").mkdir(exist_ok=True)
            
            # Copy preview icon databases
            bundle_preview_dir = get_resource_path("preview_icon_databases")
            if bundle_preview_dir.exists():
                print(f"📋 Copying preview icon databases...")
                copied_count = 0
                for preview_file in bundle_preview_dir.glob("*.tif"):
                    user_preview_file = user_preview_dir / preview_file.name
                    shutil.copy2(preview_file, user_preview_file)
                    copied_count += 1
                print(f"✅ Copied {copied_count} preview databases to user directory")
            else:
                print(f"⚠️  Bundle preview directory not found: {bundle_preview_dir}")
            
            # Copy gradient files to user directory
            user_gradients_file = user_data_dir / "gradients.json"
            bundle_gradients = get_resource_path("gradients.json")
            if bundle_gradients.exists() and not user_gradients_file.exists():
                print(f"📋 Copying gradient configuration...")
                shutil.copy2(bundle_gradients, user_gradients_file)
                print(f"✅ Gradient configuration copied to user directory")
            
            # Use the correct sample TIF database
            bundle_sample = get_resource_path("sample_data") / "Gtopo30_reduced_2160x1080.tif"
            user_sample = user_data_dir / "sample_data" / "Gtopo30_reduced_2160x1080.tif"
            
            if bundle_sample.exists():
                print(f"📋 Copying sample database: {bundle_sample.name}")
                shutil.copy2(bundle_sample, user_sample)
                
                # TIF files don't need separate header files
                
                print(f"✅ Sample database copied to: {user_sample}")
                
                # Load the sample database automatically
                print(f"🔄 Auto-loading sample database...")
                success = self.load_dem_file(str(user_sample))
                
                if success:
                    print(f"✅ Successfully loaded sample database")
                    welcome_msg = "🎉 Welcome to TopoToImage! Sample terrain loaded - you're ready to create beautiful maps!"
                    print(f"📢 {welcome_msg}")
                    self.status_bar.showMessage(welcome_msg, 8000)
                    
                    # Add sample database to recent databases so it loads on next run
                    from recent_databases import recent_db_manager
                    recent_db_manager.add_recent_database(str(user_sample), 'single_file', 'Gtopo30_reduced_2160x1080.tif')
                    print(f"📝 Added sample database to recent databases")
                    
                    # Also ensure recent database file exists in development assets location
                    # (since get_writable_data_path points there in development mode)
                    dev_recent_db_file = get_writable_data_path("recent_databases.json")
                    if not dev_recent_db_file.exists():
                        print(f"📝 Creating recent database file in development assets")
                        recent_db_manager.save_recent_databases()
                    
                    # Show proper welcome dialog box
                    self.show_welcome_dialog()
                    
                    # Update window title
                    self.update_window_title("Gtopo30_reduced_2160x1080.tif - TopoToImage")
                    
                    # Mark first run as complete (in home directory)
                    first_run_flag = user_data_dir / ".first_run_complete"
                    first_run_flag.touch()
                    print(f"✅ First run setup completed")
                    
                    return True
                else:
                    print(f"⚠️  Failed to load sample database")
                    
            else:
                print(f"⚠️  Sample database not found: {bundle_sample}")
                
                # Fallback: try the assembled DEM in the root directory
                fallback_sample = Path("assembled_dem_20250811_194830.dem")
                if fallback_sample.exists():
                    print(f"📋 Using fallback sample: {fallback_sample.name}")
                    success = self.load_dem_file(str(fallback_sample))
                    if success:
                        print(f"✅ Successfully loaded fallback sample")
                        self.status_bar.showMessage("Welcome to TopoToImage! Sample data loaded.", 5000)
                        self.update_window_title("assembled_dem_20250811_194830.dem")
                        
                        # Mark first run as complete (in home directory)
                        first_run_flag = user_data_dir / ".first_run_complete"
                        first_run_flag.touch()
                        print(f"✅ First run setup completed")
                        
                        return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error setting up first-run experience: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def show_welcome_dialog(self):
        """Show welcome dialog for first-run users"""
        try:
            from PyQt6.QtWidgets import QMessageBox
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QIcon, QPixmap
            
            # Create welcome message box
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("TopoToImage - Initial Setup Complete")
            
            # Use application icon instead of standard info icon
            icon_path = get_resource_path("icons/TopoToImage.icns")
            if icon_path.exists():
                app_icon = QIcon(str(icon_path))
                msg_box.setWindowIcon(app_icon)
                # Try to set a custom icon for the dialog
                try:
                    pixmap = QPixmap(str(icon_path)).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    msg_box.setIconPixmap(pixmap)
                except:
                    msg_box.setIcon(QMessageBox.Icon.Information)
            else:
                msg_box.setIcon(QMessageBox.Icon.Information)
            
            # Professional welcome message
            welcome_text = """<h3>Setup Complete</h3>

<p>Your TopoToImage workspace has been configured at:</p>
<p><code>~/TopoToImage_Data/</code></p>

<p>This workspace includes:</p>
<ul>
<li>Sample terrain database (Gtopo30_reduced_2160x1080.tif)</li>
<li>Preview icon databases for visualization</li>
<li>Gradient configurations for map styling</li>
</ul>

<p>The sample terrain database has been loaded automatically.</p>

<p>You can now:</p>
<ul>
<li>Experiment with gradient schemes</li>
<li>Adjust coordinate selections</li>
<li>Export high-quality topographic maps</li>
</ul>"""

            msg_box.setText(welcome_text)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # Professional dialog size
            msg_box.setMinimumSize(450, 320)
            
            # Show the dialog
            msg_box.exec()
            
        except Exception as e:
            print(f"⚠️  Error showing welcome dialog: {e}")
    
    def scan_preview_databases(self):
        """Scan preview_icon_databases folders for available DEM files (both bundled and user-created)"""
        try:
            debug_logger.info("📂 === SCANNING PREVIEW DATABASES ===")
            
            self.preview_databases = []
            dem_extensions = {'.tif', '.tiff', '.dem', '.bil'}
            debug_logger.info(f"📂 Supported extensions: {dem_extensions}")
            
            # Get both directory paths
            bundled_preview_dir = get_resource_path("preview_icon_databases")
            user_preview_dir = get_writable_data_path("preview_icon_databases")
            
            debug_logger.info(f"📂 Bundled preview directory: {bundled_preview_dir}")
            debug_logger.info(f"📂 User preview directory: {user_preview_dir}")
            debug_logger.info(f"📂 Same directory?: {bundled_preview_dir == user_preview_dir}")
            
            # If both paths are the same (development mode), scan only once
            if bundled_preview_dir == user_preview_dir:
                debug_logger.info("📂 Development mode: scanning single directory")
                if bundled_preview_dir.exists():
                    debug_logger.info("📂 Scanning preview databases:")
                    for file_path in bundled_preview_dir.iterdir():
                        if file_path.is_file() and file_path.suffix.lower() in dem_extensions:
                            debug_logger.info(f"  📄 Found: {file_path.name}")
                            self.preview_databases.append(file_path)
                else:
                    debug_logger.warning(f"📂 Preview directory does not exist: {bundled_preview_dir}")
            else:
                # Different paths (bundle mode) - scan both with duplicate detection
                debug_logger.info("📂 Bundle mode: scanning both directories with duplicate detection")
                seen_filenames = set()
                
                # Scan bundled first
                if bundled_preview_dir.exists():
                    debug_logger.info("📂 Scanning bundled preview databases:")
                    for file_path in bundled_preview_dir.iterdir():
                        if file_path.is_file() and file_path.suffix.lower() in dem_extensions:
                            filename = file_path.name
                            debug_logger.info(f"  📄 Found bundled: {filename}")
                            self.preview_databases.append(file_path)
                            seen_filenames.add(filename)
                
                # Scan user directory, skipping duplicates
                if user_preview_dir.exists():
                    debug_logger.info("📂 Scanning user-created preview databases:")
                    for file_path in user_preview_dir.iterdir():
                        if file_path.is_file() and file_path.suffix.lower() in dem_extensions:
                            filename = file_path.name
                            if filename not in seen_filenames:
                                debug_logger.info(f"  📄 Found user-created: {filename}")
                                self.preview_databases.append(file_path)
                                seen_filenames.add(filename)
                            else:
                                debug_logger.info(f"  ⚠️  Skipping duplicate: {filename}")
            
            # Sort by name for consistent ordering
            self.preview_databases.sort(key=lambda p: p.name)
            
            # Reset to first database
            self.current_preview_index = 0
            
            debug_logger.info(f"✅ Found {len(self.preview_databases)} preview databases:")
            for i, db_path in enumerate(self.preview_databases):
                indicator = "🔸" if i == 0 else "  "
                debug_logger.info(f"  {indicator} {db_path.name}")
            
            # Set up double-click handler for preview label
            debug_logger.info("🔧 Setting up preview double-click handler...")
            self.setup_preview_double_click_handler()
            
            # Update menu state after scanning preview databases
            self.update_preview_icon_menu_state()
            
        except Exception as e:
            debug_logger.error(f"❌ Error scanning preview databases: {e}")
            import traceback
            debug_logger.error(f"❌ Traceback: {traceback.format_exc()}")
            traceback.print_exc()
    
    def setup_preview_double_click_handler(self):
        """Set up double-click handler and tooltip for the preview label"""
        try:
            if hasattr(self, 'preview_label') and self.preview_label:
                # Create a custom preview label class that handles double-clicks
                from PyQt6.QtWidgets import QLabel
                from PyQt6.QtCore import QEvent
                
                # Store original mousePressEvent if it exists
                original_mouse_press = getattr(self.preview_label, 'mousePressEvent', None)
                
                def handle_mouse_press(event):
                    from PyQt6.QtCore import Qt
                    import time  # Move import to top of function
                    
                    print(f"🖱️  === PREVIEW MOUSE PRESS EVENT ===")
                    print(f"🖱️  Button: {event.button()}")
                    print(f"🖱️  Position: {event.position()}")
                    print(f"🖱️  Global Position: {event.globalPosition()}")
                    
                    if event.button() == Qt.MouseButton.LeftButton:
                        print(f"🖱️  Left button pressed")
                        current_time = time.time()
                        print(f"🖱️  Current time: {current_time}")
                        
                        # Check for double-click
                        if hasattr(handle_mouse_press, 'last_click_time'):
                            time_diff = current_time - handle_mouse_press.last_click_time
                            print(f"🖱️  Last click time: {handle_mouse_press.last_click_time}")
                            print(f"🖱️  Time difference: {time_diff:.3f}s")
                            print(f"🖱️  Double-click threshold: 0.5s")
                            
                            if time_diff < 0.5:  # 500ms double-click threshold
                                print(f"🖱️  ✅ DOUBLE-CLICK DETECTED! Cycling preview database...")
                                self.cycle_to_next_preview_database()
                                print(f"🖱️  ✅ Double-click handler completed, returning early")
                                return
                            else:
                                print(f"🖱️  ❌ Not a double-click (time diff: {time_diff:.3f}s > 0.5s)")
                        else:
                            print(f"🖱️  ❌ No previous click recorded")
                        
                        print(f"🖱️  Recording click time: {current_time}")
                        handle_mouse_press.last_click_time = current_time
                        
                    elif event.button() == Qt.MouseButton.RightButton:
                        print(f"🖱️  Right button pressed - showing context menu")
                        # Handle right-click for context menu
                        self.show_preview_context_menu(event.globalPosition().toPoint())
                    
                    # Call original handler if it exists
                    if original_mouse_press:
                        print(f"🖱️  Calling original mouse press handler")
                        original_mouse_press(event)
                    else:
                        print(f"🖱️  No original mouse press handler to call")
                    
                    print(f"🖱️  === END MOUSE PRESS EVENT ===")
                
                # Replace the mouse press event handler
                self.preview_label.mousePressEvent = handle_mouse_press
                
                # Set up initial tooltip
                self.update_preview_tooltip()
                
                print("✅ Preview double-click handler and tooltip setup complete")
            else:
                print("⚠️  Preview label not found for double-click setup")
                
        except Exception as e:
            print(f"❌ Error setting up preview double-click handler: {e}")
            import traceback
            traceback.print_exc()
    
    def update_preview_tooltip(self):
        """Update the preview label tooltip with current database info"""
        try:
            if not hasattr(self, 'preview_label') or not self.preview_label:
                return
            
            if not self.preview_databases:
                self.preview_label.setToolTip("No preview databases available")
                return
            
            total_count = len(self.preview_databases)
            current_num = self.current_preview_index + 1
            
            # Check if current database is the protected default (pr01_fixed.tif)
            if (self.preview_databases and 
                0 <= self.current_preview_index < len(self.preview_databases)):
                current_db = self.preview_databases[self.current_preview_index]
                is_default = current_db.name == "pr01_fixed.tif"
            else:
                is_default = False
            
            if is_default:
                tooltip_text = f"Default icon • Double-click to cycle"
            else:
                tooltip_text = f"Preview Icon {current_num} of {total_count} • Double-click to cycle • Right-click to delete"
            
            self.preview_label.setToolTip(tooltip_text)
            print(f"✅ Preview tooltip updated: {tooltip_text}")
            
        except Exception as e:
            print(f"❌ Error updating preview tooltip: {e}")
            import traceback
            traceback.print_exc()
    
    def show_preview_context_menu(self, global_pos):
        """Show context menu for preview icon with delete option"""
        try:
            from PyQt6.QtWidgets import QMenu
            
            # Don't show context menu if no databases available
            if not self.preview_databases:
                return
            
            # Check if current database is the protected default (pr01_fixed.tif)
            current_db = self.preview_databases[self.current_preview_index]
            is_default = current_db.name == "pr01_fixed.tif"
            
            # Don't show delete option if it's the last remaining database
            can_delete = len(self.preview_databases) > 1 and not is_default
            
            # Create context menu
            context_menu = QMenu(self)
            
            if can_delete:
                delete_action = context_menu.addAction("Delete this preview icon")
                delete_action.triggered.connect(self.delete_current_preview_database)
            else:
                if is_default:
                    no_delete_action = context_menu.addAction("Cannot delete default icon")
                else:
                    no_delete_action = context_menu.addAction("Cannot delete last preview icon")
                no_delete_action.setEnabled(False)
            
            # Show the context menu
            context_menu.exec(global_pos)
            
        except Exception as e:
            print(f"❌ Error showing preview context menu: {e}")
            import traceback
            traceback.print_exc()
    
    def delete_current_preview_database(self):
        """Delete the currently active preview database"""
        try:
            if not self.preview_databases or self.current_preview_index < 0:
                print("⚠️  No preview database to delete")
                return
            
            current_db = self.preview_databases[self.current_preview_index]
            
            # Safety check: don't delete the protected default
            if current_db.name == "pr01_fixed.tif":
                print("⚠️  Cannot delete protected default preview database")
                return
            
            # Safety check: don't delete if it's the last database
            if len(self.preview_databases) <= 1:
                print("⚠️  Cannot delete the last preview database")
                return
            
            print(f"🗑️  Deleting preview database: {current_db.name}")
            
            # Delete the physical file
            import os
            if current_db.exists():
                os.remove(current_db)
                print(f"✅ Deleted file: {current_db}")
            
            # Remove from the database list
            self.preview_databases.pop(self.current_preview_index)
            
            # Adjust current index (move to next, or wrap to 0 if we were at the end)
            if self.current_preview_index >= len(self.preview_databases):
                self.current_preview_index = 0
            
            # Update the preview with the new current database
            self.update_gradient_preview()
            
            # Update the tooltip
            self.update_preview_tooltip()
            
            # Show status message
            new_db = self.preview_databases[self.current_preview_index]
            total_count = len(self.preview_databases)
            current_num = self.current_preview_index + 1
            status_msg = f"Preview icon deleted (now showing icon {current_num} of {total_count})"
            self.status_bar.showMessage(status_msg, 3000)
            
            print(f"✅ Preview database deleted successfully. Now showing: {new_db.name}")
            
            # Update menu state after deletion
            self.update_preview_icon_menu_state()
            
        except Exception as e:
            print(f"❌ Error deleting preview database: {e}")
            import traceback
            traceback.print_exc()
    
    def create_preview_icon_from_selection(self, selection_bounds):
        """Create a new preview icon database from the selected geographic area"""
        try:
            print(f"🎯 Creating preview icon from selection: {selection_bounds}")
            
            # Check if we have a loaded database or DEM file
            has_database = hasattr(self, 'current_database_info') and self.current_database_info
            has_dem_file = hasattr(self, 'current_dem_file') and self.current_dem_file
            
            if not has_database and not has_dem_file:
                print("⚠️  No database or DEM file loaded - cannot create preview icon")
                self.status_bar.showMessage("Cannot create preview icon: No database loaded", 3000)
                return
            
            # Show brief processing message
            self.status_bar.showMessage("Creating preview icon from selection...", 5000)
            
            # Get elevation data for the selected area
            elevation_data = self.extract_elevation_data_for_bounds(selection_bounds)
            if elevation_data is None:
                print("❌ Failed to extract elevation data for selection")
                self.status_bar.showMessage("Failed to create preview icon: Could not extract elevation data", 3000)
                return
            
            # Crop to square aspect ratio (center crop)
            square_data = self.crop_to_square_aspect_ratio(elevation_data)
            
            # Scale to 120x120 pixels using high-quality resampling
            preview_data = self.scale_elevation_data_to_120x120(square_data)
            
            # Generate a unique filename
            preview_filename = self.generate_unique_preview_filename()
            
            # Save as GeoTIFF in the preview databases folder (use writable location)
            preview_path = get_writable_data_path("preview_icon_databases") / preview_filename
            self.save_elevation_data_as_geotiff(preview_data, selection_bounds, preview_path)
            
            # Refresh the preview database list
            self.scan_preview_databases()
            
            # Switch to the new preview database (it will be the last one after sorting)
            if self.preview_databases:
                # Find the new database in the list
                for i, db_path in enumerate(self.preview_databases):
                    if db_path.name == preview_filename:
                        self.current_preview_index = i
                        break
                
                # Update the preview and tooltip
                self.update_gradient_preview()
                self.update_preview_tooltip()
                
                # Show success message
                total_count = len(self.preview_databases)
                current_num = self.current_preview_index + 1
                status_msg = f"Preview icon created from selection (now showing icon {current_num} of {total_count})"
                self.status_bar.showMessage(status_msg, 4000)
                
                print(f"✅ Preview icon created successfully: {preview_filename}")
            
        except Exception as e:
            print(f"❌ Error creating preview icon from selection: {e}")
            import traceback
            traceback.print_exc()
            self.status_bar.showMessage("Failed to create preview icon from selection", 3000)
    
    def extract_elevation_data_for_bounds(self, bounds):
        """Extract elevation data for the specified geographic bounds"""
        try:
            # Use the same logic as the export system to get elevation data
            west = bounds['west']
            north = bounds['north'] 
            east = bounds['east']
            south = bounds['south']
            
            print(f"📊 Extracting elevation data for bounds: W={west}, N={north}, E={east}, S={south}")
            
            # Try single DEM file first (most common case)
            if hasattr(self, 'current_dem_file') and self.current_dem_file:
                print(f"📁 Using single DEM file: {self.current_dem_file}")
                # Use single DEM file
                from dem_reader import DEMReader
                dem_reader = DEMReader(self.current_dem_file)
                
                # Load elevation data
                full_elevation_data = dem_reader.load_elevation_data()
                if full_elevation_data is None:
                    print("❌ Failed to load elevation data from DEM file")
                    return None
                
                # For single files covering large areas, we need to crop to the selection bounds
                # Get the geographic bounds of the DEM file
                try:
                    bounds_list = dem_reader.get_geographic_bounds()
                    if bounds_list and len(bounds_list) >= 4:
                        # Convert from list format [west, north, east, south] to dict
                        dem_bounds = {
                            'west': bounds_list[0],
                            'north': bounds_list[1], 
                            'east': bounds_list[2],
                            'south': bounds_list[3]
                        }
                        print(f"📍 DEM file bounds: W={dem_bounds['west']}, N={dem_bounds['north']}, E={dem_bounds['east']}, S={dem_bounds['south']}")
                        
                        # Calculate which portion of the data corresponds to the selection
                        cropped_data = self.crop_elevation_data_to_geographic_bounds(
                            full_elevation_data, dem_bounds, bounds
                        )
                        
                        if cropped_data is not None:
                            print(f"✅ Cropped elevation data from single DEM file: {cropped_data.shape}")
                            return cropped_data
                        else:
                            print("⚠️  Selection outside DEM bounds, using full data")
                            return full_elevation_data
                    else:
                        print("⚠️  Could not get DEM bounds, using full elevation data")
                        return full_elevation_data
                        
                except Exception as e:
                    print(f"⚠️  Error getting DEM bounds: {e}, using full elevation data")
                    return full_elevation_data
                    
            # Check if we have a multi-file database
            elif hasattr(self, 'current_database_info') and self.current_database_info and self.current_database_info.get('type') == 'multi_file':
                print(f"📁 Using multi-file database: {self.current_database_info['path']}")
                # Use multi-file database assembly
                from multi_file_database import MultiFileDatabase
                multi_db = MultiFileDatabase(self.current_database_info['path'])
                
                # Assemble tiles for the specified bounds
                assembly_result = multi_db.assemble_tiles_for_bounds(west, north, east, south)
                
                if assembly_result is not None:
                    # Handle different return formats from assemble_tiles_for_bounds
                    if isinstance(assembly_result, tuple):
                        # If it returns a tuple, take the first element as elevation data
                        elevation_data = assembly_result[0]
                        print(f"✅ Extracted elevation data from multi-file database (tuple): {elevation_data.shape}")
                    else:
                        # If it returns just the elevation data directly
                        elevation_data = assembly_result
                        print(f"✅ Extracted elevation data from multi-file database (direct): {elevation_data.shape}")
                    
                    if elevation_data is not None:
                        return elevation_data
                    else:
                        print("❌ Assembly returned None elevation data")
                        return None
                else:
                    print("❌ No tiles found for the selected area in multi-file database")
                    return None
                
            # Check if we have a single-file database
            elif hasattr(self, 'current_database_info') and self.current_database_info and self.current_database_info.get('type') == 'single_file':
                print(f"📄 Using single-file database via current_database_info: {self.current_database_info['path']}")
                # Use single-file database via dem_reader
                if hasattr(self, 'dem_reader') and self.dem_reader:
                    # Load elevation data
                    full_elevation_data = self.dem_reader.load_elevation_data()
                    if full_elevation_data is None:
                        print("❌ Failed to load elevation data from single-file database")
                        return None
                    
                    # Crop to bounds
                    try:
                        dem_bounds = self.dem_reader.bounds
                        print(f"📍 Single-file database bounds: W={dem_bounds['west']}, N={dem_bounds['north']}, E={dem_bounds['east']}, S={dem_bounds['south']}")
                        
                        # Calculate which portion of the data corresponds to the selection
                        cropped_data = self.crop_elevation_data_to_geographic_bounds(
                            full_elevation_data, dem_bounds, bounds
                        )
                        
                        if cropped_data is not None:
                            print(f"✅ Cropped elevation data from single-file database: {cropped_data.shape}")
                            return cropped_data
                        else:
                            print("⚠️  Selection outside database bounds, using full data")
                            return full_elevation_data
                    except Exception as e:
                        print(f"⚠️  Error cropping single-file database data: {e}, using full data")
                        return full_elevation_data
                else:
                    print("❌ No DEM reader available for single-file database")
                    return None
                
            else:
                print("❌ No valid data source available")
                return None
                
        except Exception as e:
            print(f"❌ Error extracting elevation data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def crop_elevation_data_to_geographic_bounds(self, elevation_data, dem_bounds, selection_bounds):
        """Crop elevation data to match the selected geographic bounds"""
        try:
            import numpy as np
            
            height, width = elevation_data.shape
            
            # Calculate the pixel coordinates that correspond to the selection bounds
            dem_west = dem_bounds['west']
            dem_east = dem_bounds['east'] 
            dem_north = dem_bounds['north']
            dem_south = dem_bounds['south']
            
            sel_west = selection_bounds['west']
            sel_east = selection_bounds['east']
            sel_north = selection_bounds['north'] 
            sel_south = selection_bounds['south']
            
            # Calculate pixel coordinates (0,0 is top-left)
            # X corresponds to longitude (west to east)
            # Y corresponds to latitude (north to south, inverted)
            
            # Calculate X bounds (longitude)
            if dem_east > dem_west:  # Normal case (no meridian crossing)
                x_start = max(0, int((sel_west - dem_west) / (dem_east - dem_west) * width))
                x_end = min(width, int((sel_east - dem_west) / (dem_east - dem_west) * width))
            else:
                # Handle meridian crossing case if needed
                x_start = 0
                x_end = width
            
            # Calculate Y bounds (latitude, inverted because image coordinates)
            if dem_north > dem_south:  # Normal case
                y_start = max(0, int((dem_north - sel_north) / (dem_north - dem_south) * height))
                y_end = min(height, int((dem_north - sel_south) / (dem_north - dem_south) * height))
            else:
                y_start = 0
                y_end = height
            
            # Ensure we have valid bounds
            if x_start >= x_end or y_start >= y_end:
                print(f"⚠️  Invalid crop bounds: x={x_start}:{x_end}, y={y_start}:{y_end}")
                return None
            
            # Crop the elevation data
            cropped_data = elevation_data[y_start:y_end, x_start:x_end]
            
            print(f"📐 Cropped elevation data: {height}x{width} → {cropped_data.shape}")
            print(f"   Selection bounds: W={sel_west}, N={sel_north}, E={sel_east}, S={sel_south}")
            print(f"   Pixel bounds: x={x_start}:{x_end}, y={y_start}:{y_end}")
            
            # Add diagnostic information about the cropped data
            if cropped_data.size > 0:
                min_val = np.nanmin(cropped_data)
                max_val = np.nanmax(cropped_data)
                valid_pixels = np.sum(~np.isnan(cropped_data))
                print(f"   Cropped data range: {min_val} to {max_val} meters")
                print(f"   Valid pixels: {valid_pixels}/{cropped_data.size}")
            
            return cropped_data
            
        except Exception as e:
            print(f"❌ Error cropping elevation data to geographic bounds: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def crop_to_square_aspect_ratio(self, elevation_data):
        """Crop elevation data to square aspect ratio (center crop)"""
        try:
            if elevation_data is None:
                return None
                
            height, width = elevation_data.shape
            print(f"📐 Cropping elevation data from {width}x{height} to square")
            
            # Determine the size of the square (minimum of width/height)
            square_size = min(width, height)
            
            # Calculate center crop coordinates
            center_x = width // 2
            center_y = height // 2
            half_size = square_size // 2
            
            # Crop to square
            start_x = center_x - half_size
            end_x = start_x + square_size
            start_y = center_y - half_size  
            end_y = start_y + square_size
            
            # Ensure we don't go out of bounds
            start_x = max(0, start_x)
            end_x = min(width, end_x)
            start_y = max(0, start_y)
            end_y = min(height, end_y)
            
            square_data = elevation_data[start_y:end_y, start_x:end_x]
            print(f"✅ Cropped to square: {square_data.shape}")
            
            return square_data
            
        except Exception as e:
            print(f"❌ Error cropping to square: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def scale_elevation_data_to_120x120(self, elevation_data):
        """Scale elevation data to 120x120 pixels using NaN-aware resampling"""
        try:
            if elevation_data is None:
                return None
                
            import numpy as np
            
            print(f"🔄 Scaling elevation data from {elevation_data.shape} to 120x120")
            
            # Check for NaN values before scaling
            nan_mask = np.isnan(elevation_data)
            valid_pixels_before = np.sum(~nan_mask)
            total_pixels_before = elevation_data.size
            
            if valid_pixels_before == 0:
                print("❌ All input data is NaN - cannot scale")
                return np.full((120, 120), np.nan, dtype=np.float32)
            
            print(f"📊 Input data: {valid_pixels_before}/{total_pixels_before} valid pixels ({100*valid_pixels_before/total_pixels_before:.1f}%)")
            
            # Use NaN-aware scaling approach
            try:
                from scipy.ndimage import zoom
                
                current_height, current_width = elevation_data.shape
                scale_y = 120.0 / current_height
                scale_x = 120.0 / current_width
                
                # Method 1: Handle NaN values properly for no-data color rendering
                if np.any(nan_mask):
                    print("🌊 Preserving NaN values for proper no-data color rendering...")
                    
                    # Create a copy for processing
                    filled_data = elevation_data.copy()
                    
                    # Temporarily fill NaN with a placeholder value for scaling
                    # We'll restore NaN values afterwards
                    valid_mean = np.nanmean(elevation_data)
                    if np.isnan(valid_mean):
                        # All data is NaN, use 0 as placeholder
                        placeholder_value = 0.0
                    else:
                        placeholder_value = valid_mean
                    
                    filled_data[nan_mask] = placeholder_value
                    
                    # Scale the temporarily filled data
                    scaled_data = zoom(filled_data, (scale_y, scale_x), order=1)  # Use linear interpolation
                    
                    # Now we need to determine which pixels in the scaled data should be NaN
                    # Scale the NaN mask to match the new resolution
                    nan_mask_float = nan_mask.astype(np.float32)
                    scaled_nan_mask = zoom(nan_mask_float, (scale_y, scale_x), order=0)  # Use nearest neighbor for mask
                    
                    # Restore NaN values where the scaled mask indicates no-data areas
                    # Use a threshold to determine which pixels should be NaN (>0.5 means mostly no-data)
                    scaled_data[scaled_nan_mask > 0.5] = np.nan
                    
                    print(f"✅ Scaled data preserving NaN areas using scipy.ndimage.zoom: {scaled_data.shape}")
                else:
                    # No NaN values, use normal scaling
                    scaled_data = zoom(elevation_data, (scale_y, scale_x), order=3)
                    print(f"✅ Scaled clean data using scipy.ndimage.zoom: {scaled_data.shape}")
                
                # Ensure exact 120x120 size
                scaled_data = scaled_data[:120, :120]
                
                # Check results
                valid_pixels_after = np.sum(~np.isnan(scaled_data))
                print(f"📊 Output data: {valid_pixels_after}/{scaled_data.size} valid pixels ({100*valid_pixels_after/scaled_data.size:.1f}%)")
                
                return scaled_data
                
            except ImportError:
                # Fallback to PIL-based resizing
                print("🔄 Using PIL fallback for scaling...")
                from PIL import Image
                
                # Handle NaN values for PIL processing while preserving no-data areas
                if np.any(nan_mask):
                    print("🌊 Preserving NaN values for proper no-data color rendering (PIL)...")
                    filled_data = elevation_data.copy()
                    
                    # Temporarily fill NaN with mean for PIL processing
                    valid_mean = np.nanmean(elevation_data)
                    if np.isnan(valid_mean):
                        placeholder_value = 0.0
                    else:
                        placeholder_value = valid_mean
                    filled_data[nan_mask] = placeholder_value
                else:
                    filled_data = elevation_data
                
                # Normalize to 0-255 range for PIL processing
                data_min = np.nanmin(filled_data)
                data_max = np.nanmax(filled_data)
                
                if data_max > data_min:
                    normalized = ((filled_data - data_min) / (data_max - data_min) * 255).astype(np.uint8)
                else:
                    normalized = np.full_like(filled_data, 128, dtype=np.uint8)
                
                pil_image = Image.fromarray(normalized)
                resized_pil = pil_image.resize((120, 120), Image.Resampling.BICUBIC)
                
                # Convert back to elevation values
                resized_normalized = np.array(resized_pil).astype(np.float32)
                if data_max > data_min:
                    scaled_data = (resized_normalized / 255.0 * (data_max - data_min) + data_min)
                else:
                    scaled_data = np.full((120, 120), data_min, dtype=np.float32)
                
                # Restore NaN values for no-data areas if there were any originally
                if np.any(nan_mask):
                    # Scale the original NaN mask to the new size
                    from PIL import Image as PILImage
                    nan_mask_uint8 = (nan_mask * 255).astype(np.uint8)
                    nan_pil = PILImage.fromarray(nan_mask_uint8)
                    scaled_nan_pil = nan_pil.resize((120, 120), PILImage.Resampling.NEAREST)
                    scaled_nan_mask = np.array(scaled_nan_pil) > 127  # Threshold to boolean
                    
                    # Restore NaN values
                    scaled_data[scaled_nan_mask] = np.nan
                
                print(f"✅ Scaled using PIL fallback: {scaled_data.shape}")
                return scaled_data
                
        except Exception as e:
            print(f"❌ Error scaling elevation data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_unique_preview_filename(self):
        """Generate a unique filename for a new preview database"""
        try:
            preview_dir = get_resource_path("preview_icon_databases")
            base_name = "preview_icon_"
            extension = ".tif"
            
            # Find the next available number
            existing_numbers = []
            for file_path in preview_dir.iterdir():
                if file_path.is_file() and file_path.name.startswith(base_name):
                    try:
                        # Extract number from filename like "preview_icon_07.tif"
                        name_part = file_path.stem.replace(base_name, "")
                        if name_part.isdigit():
                            existing_numbers.append(int(name_part))
                    except:
                        continue
            
            # Find the next number
            next_number = 1
            while next_number in existing_numbers:
                next_number += 1
            
            # Format with zero padding
            filename = f"{base_name}{next_number:02d}{extension}"
            print(f"📝 Generated unique preview filename: {filename}")
            
            return filename
            
        except Exception as e:
            print(f"❌ Error generating unique filename: {e}")
            return "preview_icon_new.tif"
    
    def save_elevation_data_as_geotiff(self, elevation_data, bounds, output_path):
        """Save elevation data as a GeoTIFF file with proper georeferencing"""
        try:
            import numpy as np
            from pathlib import Path
            
            print(f"💾 Saving elevation data as GeoTIFF: {output_path}")
            
            # Diagnostic information about the elevation data
            if elevation_data is not None:
                min_val = np.nanmin(elevation_data)
                max_val = np.nanmax(elevation_data)
                mean_val = np.nanmean(elevation_data)
                valid_pixels = np.sum(~np.isnan(elevation_data))
                total_pixels = elevation_data.size
                
                print(f"📊 Elevation data stats:")
                print(f"   Shape: {elevation_data.shape}")
                print(f"   Range: {min_val} to {max_val} meters")
                print(f"   Mean: {mean_val:.2f} meters")
                print(f"   Valid pixels: {valid_pixels}/{total_pixels} ({100*valid_pixels/total_pixels:.1f}%)")
                
                # Check if data is all NaN or has no variation
                if valid_pixels == 0:
                    print("❌ WARNING: All elevation data is NaN - preview will be blank!")
                elif min_val == max_val:
                    print("❌ WARNING: No elevation variation - preview will be flat!")
                elif valid_pixels < total_pixels * 0.5:
                    print("⚠️  WARNING: Less than 50% valid elevation data - preview may be sparse!")
            
            # Ensure the preview_icon_databases directory exists
            output_path.parent.mkdir(exist_ok=True)
            
            # Use rasterio for proper GeoTIFF creation if available
            try:
                import rasterio
                from rasterio.transform import from_bounds
                from rasterio.crs import CRS
                
                height, width = elevation_data.shape
                
                # Create transform from geographic bounds
                transform = from_bounds(
                    bounds['west'], bounds['south'], 
                    bounds['east'], bounds['north'], 
                    width, height
                )
                
                # Save as GeoTIFF
                with rasterio.open(
                    output_path,
                    'w',
                    driver='GTiff',
                    height=height,
                    width=width,
                    count=1,
                    dtype=elevation_data.dtype,
                    crs=CRS.from_epsg(4326),  # WGS84
                    transform=transform,
                    compress='lzw'
                ) as dst:
                    dst.write(elevation_data, 1)
                
                print(f"✅ Saved GeoTIFF with rasterio: {output_path}")
                
            except ImportError:
                # Fallback to simple TIFF using PIL
                from PIL import Image
                
                # Convert to 16-bit integer for better precision
                elevation_min = elevation_data.min()
                elevation_max = elevation_data.max()
                
                if elevation_max > elevation_min:
                    normalized = ((elevation_data - elevation_min) / 
                                (elevation_max - elevation_min) * 65535).astype(np.uint16)
                else:
                    normalized = np.zeros_like(elevation_data, dtype=np.uint16)
                
                pil_image = Image.fromarray(normalized)
                pil_image.save(output_path, format='TIFF')
                
                print(f"✅ Saved TIFF with PIL fallback: {output_path}")
                
        except Exception as e:
            print(f"❌ Error saving elevation data as GeoTIFF: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def cycle_to_next_preview_database(self):
        """Cycle to the next preview database and update the preview"""
        try:
            print(f"🔄 === CYCLE PREVIEW DATABASE CALLED ===")
            print(f"🔄 Preview databases available: {len(self.preview_databases) if self.preview_databases else 0}")
            print(f"🔄 Current preview index: {self.current_preview_index}")
            
            if not self.preview_databases:
                print("⚠️  No preview databases available for cycling")
                return
            
            # Store old index for comparison
            old_index = self.current_preview_index
            old_db = self.preview_databases[old_index] if self.preview_databases else None
            
            # Move to next database (cycle back to 0 if at end)
            self.current_preview_index = (self.current_preview_index + 1) % len(self.preview_databases)
            
            current_db = self.preview_databases[self.current_preview_index]
            print(f"🔄 Index changed: {old_index} → {self.current_preview_index}")
            print(f"🔄 Database changed: {old_db.name if old_db else 'None'} → {current_db.name}")
            print(f"🔄 Cycling to preview database: {current_db.name} ({self.current_preview_index + 1} of {len(self.preview_databases)})")
            
            # Update the gradient preview with the new database
            print(f"🔄 Calling update_gradient_preview()...")
            self.update_gradient_preview()
            print(f"🔄 update_gradient_preview() completed")
            
            # Update the tooltip to reflect the new database
            print(f"🔄 Updating preview tooltip...")
            self.update_preview_tooltip()
            print(f"🔄 Preview tooltip updated")
            
            # Show brief status message
            db_name = current_db.stem  # Filename without extension
            status_msg = f"Preview: {db_name} ({self.current_preview_index + 1} of {len(self.preview_databases)})"
            print(f"🔄 Setting status message: {status_msg}")
            self.status_bar.showMessage(status_msg, 3000)  # Show for 3 seconds
            
            print(f"🔄 === CYCLE PREVIEW DATABASE COMPLETED ===")
            
            # Update menu state after cycling 
            self.update_preview_icon_menu_state()
            
        except Exception as e:
            print(f"❌ Error cycling preview database: {e}")
            import traceback
            traceback.print_exc()
    
    def get_current_preview_database(self):
        """Get the path to the currently active preview database"""
        print(f"📂 === GET_CURRENT_PREVIEW_DATABASE CALLED ===")
        print(f"📂 Preview databases available: {len(self.preview_databases) if self.preview_databases else 0}")
        print(f"📂 Current preview index: {self.current_preview_index}")
        
        if self.preview_databases and 0 <= self.current_preview_index < len(self.preview_databases):
            selected_db = self.preview_databases[self.current_preview_index]
            print(f"📂 Returning selected database: {selected_db.name}")
            print(f"📂 Database path: {selected_db}")
            return selected_db
        
        # Fallback to the original hardcoded database using resource path
        fallback_db = get_resource_path("preview_icon_databases") / "pr01_fixed.tif"
        print(f"📂 Using fallback database: {fallback_db}")
        return fallback_db
    
    def initialize_export_controls(self):
        """Initialize export controls with default values"""
        try:
            # Export type combo no longer exists - removed for separated export functions
            
            # Initialize export scale combo
            if hasattr(self, 'export_scale_combo'):
                self.export_scale_combo.addItems([
                    "100%",
                    "50%", 
                    "33.3%",
                    "25%",
                    "10%",
                    "Custom"
                ])
                self.export_scale_combo.setCurrentText("100%")
            
            # Initialize export scale spinbox to match combo default
            if hasattr(self, 'export_scale_spinbox'):
                self.export_scale_spinbox.setValue(100)  # Default to 100%
            
            # Initialize elevation spinboxes with default values
            if hasattr(self, 'min_elevation') and hasattr(self, 'max_elevation'):
                self.min_elevation.setValue(0)  # Default minimum elevation
                self.max_elevation.setValue(9000)  # Default maximum elevation
                print(f"✅ Initialized elevation spinboxes: 0m to 9000m")
            
            # Initialize export controls with default values
            # Set initial values in UI
            self.width_edit.setText("20.000")
            self.height_edit.setText("10.000") 
            self.resolution_edit.setText("300.000")
            
            # Initialize export logic with default values
            self.export_logic.set_width(20.0)  # This will set width as locked and calculate others
            self.export_logic.set_units(Units.INCHES)  # Default to inches
            
            # Set default radio button states (already set in .ui file)
            # lock_width_radio is checked by default
            # inches_radio is checked by default
            
            # Initialize unit labels to default (inches)
            self.update_unit_labels("In.")
            
            print("✅ Export controls initialized")
            
        except Exception as e:
            print(f"❌ Error initializing export controls: {e}")
            import traceback
            traceback.print_exc()
    
    def handle_startup_database_loading(self):
        """Handle automatic database loading on startup with first-run detection"""
        try:
            # Check for first-run scenario
            if self.is_first_run():
                print("🎉 First run detected - setting up user data directory...")
                if self.setup_first_run_experience():
                    print("✅ First run setup completed successfully")
                    return
                else:
                    print("⚠️  First run setup failed, falling back to normal startup")
            
            # Try to open the last database
            last_database = recent_db_manager.get_last_database()
            
            if last_database and self._database_exists(last_database):
                # Auto-open the last database with enhanced error handling
                try:
                    print(f"🔄 Attempting to auto-load: {last_database['display_name']} ({last_database['type']})")
                    
                    success = False
                    if last_database['type'] == 'single_file':
                        success = self.load_dem_file(last_database['path'])
                        if success:
                            # Update window title for auto-opened single files
                            file_path = Path(last_database['path'])
                            self.update_window_title(file_path.name)
                    elif last_database['type'] == 'multi_file':
                        # Add extra protection for multi-file databases
                        try:
                            success = self.load_database_folder(last_database['path'])
                        except Exception as multi_file_error:
                            print(f"⚠️  Multi-file database failed to load: {multi_file_error}")
                            success = False
                    else:
                        print(f"⚠️  Unknown database type: {last_database['type']}")
                        success = False
                    
                    if success:
                        self.status_bar.showMessage(f"Auto-opened: {last_database['display_name']}")
                        print(f"✅ Successfully auto-loaded: {last_database['display_name']}")
                        return
                    else:
                        print(f"⚠️  Failed to load database: {last_database['display_name']}")
                        # Remove invalid database from recent list
                        recent_db_manager.remove_database(last_database['path'])
                        self.update_recent_databases_menu()
                        
                except Exception as e:
                    print(f"❌ Failed to auto-open last database: {e}")
                    # Remove problematic database from recent list to prevent future crashes
                    recent_db_manager.remove_database(last_database['path'])
                    self.update_recent_databases_menu()
                    
                    # Clear any partially loaded state
                    self.current_dem_file = None
                    if hasattr(self, 'world_map_widget'):
                        self.world_map_widget.clear_selection()
                    
                    # Show error message to user
                    self.status_bar.showMessage(f"Error loading {last_database['display_name']} - removed from recent databases")
            
            # No valid last database - show startup dialog
            self.show_startup_database_dialog()
            
        except Exception as e:
            print(f"❌ Critical error in startup database loading: {e}")
            import traceback
            traceback.print_exc()
            
            # Clear recent databases to prevent repeated crashes
            try:
                recent_db_manager.clear_recent_databases()
                print("🧹 Cleared recent databases cache to prevent future startup crashes")
            except:
                pass
            
            # Show startup dialog as fallback
            try:
                self.show_startup_database_dialog()
            except:
                print("❌ Could not show startup dialog - continuing without auto-loading")
    
    def update_database_info_display(self, database_info=None, export_info=None):
        """Update the database info display with new Qt Designer layout"""
        try:
            if database_info:
                # Update database info labels with safe key access
                try:
                    self.width_db_label.setText(str(database_info.get('width_pixels', 0)))
                    self.height_db_label.setText(str(database_info.get('height_pixels', 0)))
                    self.pix_deg_db_label.setText(f"{database_info.get('pix_per_degree', 0):.2f}")
                    # Use clean coordinate formatting for database labels
                    from coordinate_validator import coordinate_validator
                    west_db_clean = coordinate_validator.format_coordinate_clean(database_info.get('west', 0), is_longitude=True, use_dms=False)
                    north_db_clean = coordinate_validator.format_coordinate_clean(database_info.get('north', 0), is_longitude=False, use_dms=False)
                    east_db_clean = coordinate_validator.format_coordinate_clean(database_info.get('east', 0), is_longitude=True, use_dms=False)
                    south_db_clean = coordinate_validator.format_coordinate_clean(database_info.get('south', 0), is_longitude=False, use_dms=False)
                    
                    self.west_db_label.setText(west_db_clean)
                    self.north_db_label.setText(north_db_clean)
                    self.east_db_label.setText(east_db_clean)
                    self.south_db_label.setText(south_db_clean)
                except Exception as e:
                    print(f"Error updating database labels: {e}")
                    # Set default values if there's an error
                    self.width_db_label.setText("0")
                    self.height_db_label.setText("0")
                    self.pix_deg_db_label.setText("0.00")
                    self.west_db_label.setText("0")
                    self.north_db_label.setText("0")
                    self.east_db_label.setText("0")
                    self.south_db_label.setText("0")
                
                # Calculate file size (rough estimate) with error handling
                try:
                    total_pixels = database_info.get('width_pixels', 0) * database_info.get('height_pixels', 0)
                    file_size_kb = (total_pixels * 2) / 1024  # 2 bytes per pixel estimate
                    if file_size_kb < 1024:
                        self.size_db_label.setText(f"{file_size_kb:.1f} KB")
                    else:
                        self.size_db_label.setText(f"{file_size_kb/1024:.1f} MB")
                except Exception as e:
                    print(f"Error calculating file size: {e}")
                    self.size_db_label.setText("Unknown")
                
                # Calculate pixel height in miles with error handling
                try:
                    height_pixels = database_info.get('height_pixels', 0)
                    if height_pixels > 0:
                        north = float(database_info.get('north', 0))
                        south = float(database_info.get('south', 0))
                        degrees_per_pixel = abs(north - south) / height_pixels
                        miles_per_pixel = degrees_per_pixel * 69  # Roughly 69 miles per degree latitude
                        self.pxheight_db_label.setText(format_distance_km_miles(miles_per_pixel))
                    else:
                        self.pxheight_db_label.setText("0.00 km (0.00 mi.)")
                except Exception as e:
                    print(f"Error calculating pixel height: {e}")
                    self.pxheight_db_label.setText("0.00 km (0.00 mi.)")
            
            if export_info:
                # Update export file info labels (with _2 suffix)
                self.width_export_label_2.setText(str(export_info.get('width_pixels', 0)))
                self.height_export_label_2.setText(str(export_info.get('height_pixels', 0)))
                self.pix_deg_export_label_2.setText(f"{export_info.get('pix_per_degree', 0):.2f}")
                # Use clean coordinate formatting for export labels  
                from coordinate_validator import coordinate_validator
                west_clean = coordinate_validator.format_coordinate_clean(export_info.get('west', 0), is_longitude=True, use_dms=False)
                north_clean = coordinate_validator.format_coordinate_clean(export_info.get('north', 0), is_longitude=False, use_dms=False)
                east_clean = coordinate_validator.format_coordinate_clean(export_info.get('east', 0), is_longitude=True, use_dms=False)
                south_clean = coordinate_validator.format_coordinate_clean(export_info.get('south', 0), is_longitude=False, use_dms=False)
                
                self.west_export_label_2.setText(west_clean)
                self.north_export_label_2.setText(north_clean)
                self.east_export_label_2.setText(east_clean)
                self.south_export_label_2.setText(south_clean)
                
                # Calculate export file size
                total_pixels = export_info.get('width_pixels', 0) * export_info.get('height_pixels', 0)
                file_size_kb = (total_pixels * 4) / 1024  # 4 bytes per pixel for RGBA
                if file_size_kb < 1024:
                    self.size_export_label_2.setText(f"{file_size_kb:.1f} KB")
                else:
                    self.size_export_label_2.setText(f"{file_size_kb/1024:.1f} MB")
                
                # Calculate export pixel height in miles and format as km (mi.)
                if export_info.get('height_pixels', 0) > 0:
                    degrees_per_pixel = abs(export_info.get('north', 0) - export_info.get('south', 0)) / export_info.get('height_pixels', 1)
                    miles_per_pixel = degrees_per_pixel * 69
                    self.pxheight_export_label_2.setText(format_distance_km_miles(miles_per_pixel))
                else:
                    self.pxheight_export_label_2.setText("0.00 km (0.00 mi.)")
            
            print("✅ Database info display updated successfully")
            
        except Exception as e:
            print(f"❌ Error updating database info display: {e}")
            import traceback
            traceback.print_exc()

    # Menu action methods
    def setup_recent_databases_menu(self):
        """Setup the Recent Databases submenu"""
        self.update_recent_databases_menu()
    
    def update_recent_databases_menu(self):
        """Update the Recent Databases submenu with current recent databases"""
        self.recent_databases_menu.clear()
        
        recent_items = recent_db_manager.get_menu_items()
        
        if not recent_items:
            # No recent databases
            no_recent_action = self.recent_databases_menu.addAction("(No recent databases)")
            no_recent_action.setEnabled(False)
        else:
            # Add recent database items
            for display_text, path, db_type in recent_items:
                action = self.recent_databases_menu.addAction(display_text)
                action.triggered.connect(lambda checked, p=path, t=db_type: self.open_recent_database(p, t))
            
            # Add separator and clear option
            self.recent_databases_menu.addSeparator()
            clear_action = self.recent_databases_menu.addAction("Clear Recent Databases")
            clear_action.triggered.connect(self.clear_recent_databases)
    
    # File menu actions
    def open_dem_file(self):
        """Open a single DEM file"""
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Elevation Database",
            "",
            "DEM Files (*.dem *.bil *.tif *.tiff);;All Files (*)"
        )
        
        if file_path:
            success = self.load_dem_file(file_path)
            if success:
                file_name = Path(file_path).name
                self.update_window_title(file_name)
                recent_db_manager.add_recent_database(file_path, 'single_file')
                self.update_recent_databases_menu()

    def open_database_folder(self):
        """Open a database folder"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from pathlib import Path
        
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Open Elevation Database Folder"
        )
        
        if folder_path:
            folder_path_obj = Path(folder_path)
            
            # Check if metadata file exists
            existing_json_files = list(folder_path_obj.glob("*.json"))
            
            if not existing_json_files:
                # No metadata file found - ask user if they want to create one
                reply = QMessageBox.question(
                    self,
                    "No Multi-File Database Definition",
                    f"This folder does not contain a multi-file database definition file.\n\n"
                    f"Would you like to scan this folder for elevation data and create a definition file?\n\n"
                    f"This will make loading faster and enable full multi-file database features.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Create metadata file using the create_multi_file_database workflow
                    from multi_file_database import MultiFileDatabase
                    
                    try:
                        print(f"🔨 Creating metadata file for folder: {folder_path}")
                        success = MultiFileDatabase.create_metadata_file(folder_path_obj, None)
                        
                        if not success:
                            QMessageBox.warning(
                                self,
                                "Metadata Creation Failed",
                                f"Could not create metadata file for this folder.\n\n"
                                f"Common issues:\n"
                                f"• No valid DEM files found\n"
                                f"• Files cannot be read as elevation data\n\n"
                                f"You can try loading individual files instead."
                            )
                            return
                    except Exception as e:
                        print(f"❌ Error creating metadata: {e}")
                        QMessageBox.critical(
                            self,
                            "Error Creating Metadata",
                            f"An error occurred while creating the metadata file:\n\n{str(e)}"
                        )
                        return
            
            # Try to load the database (now with metadata file if we just created one)
            success = self.load_database_folder(folder_path)
            if success:
                recent_db_manager.add_recent_database(folder_path, 'multi_file')
                self.update_recent_databases_menu()
    
    def create_multi_file_database(self):
        """Create a multi-file database from a folder of DEM files"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog, QInputDialog
        from PyQt6.QtCore import Qt
        from pathlib import Path
        
        # Get folder from user
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder to Create Multi-File Database",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not folder_path:
            return
            
        folder_path = Path(folder_path)
        
        # Check if metadata file already exists
        existing_json_files = list(folder_path.glob("*_metadata.json"))
        if existing_json_files:
            reply = QMessageBox.question(
                self,
                "Metadata File Exists",
                f"This folder already contains a metadata file:\n{existing_json_files[0].name}\n\n"
                f"Do you want to recreate it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Get optional database name from user
        database_name, ok = QInputDialog.getText(
            self,
            "Database Name",
            "Enter name for database:",
            text=folder_path.name
        )
        
        if not ok:
            return
            
        if not database_name.strip():
            database_name = None
        
        # Show progress dialog
        progress = QProgressDialog("Scanning folder for DEM files...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.show()
        
        try:
            # Import and create metadata file
            from multi_file_database import MultiFileDatabase
            
            print(f"🔨 Creating multi-file database: {folder_path}")
            success = MultiFileDatabase.create_metadata_file(folder_path, database_name)
            
            progress.close()
            
            if success:
                # Show success dialog
                QMessageBox.information(
                    self,
                    "Multi-File Database Created",
                    f"Successfully created multi-file database metadata.\n\n"
                    f"Folder: {folder_path.name}\n"
                    f"Metadata file: {folder_path.name}_metadata.json\n\n"
                    f"Loading database now..."
                )
                
                # Load the newly created database
                if self.load_database_folder(folder_path):
                    # Add to recent databases
                    from recent_databases import RecentDatabasesManager
                    recent_db_manager = RecentDatabasesManager()
                    recent_db_manager.add_recent_database(str(folder_path), 'multi_file')
                    self.update_recent_databases_menu()
                    
                    print(f"✅ Successfully created and loaded multi-file database: {folder_path.name}")
                else:
                    QMessageBox.warning(
                        self,
                        "Database Load Failed",
                        f"Created metadata file but failed to load the database.\n\n"
                        f"You can try opening the folder manually using 'Open Elevation Database Folder...'"
                    )
            else:
                QMessageBox.critical(
                    self,
                    "Creation Failed",
                    f"Failed to create multi-file database.\n\n"
                    f"Common issues:\n"
                    f"• No valid DEM files found in folder\n"
                    f"• Files cannot be read as elevation data\n"
                    f"• Permission issues\n\n"
                    f"Check the console output for details."
                )
                
        except Exception as e:
            progress.close()
            print(f"❌ Error creating multi-file database: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while creating the multi-file database:\n\n{str(e)}"
            )

    def reveal_database_in_finder(self):
        """Reveal the currently loaded database in Finder"""
        if not hasattr(self, 'current_database_info') or not self.current_database_info:
            QMessageBox.information(
                self,
                "No Database Loaded",
                "No database is currently loaded.\n\n"
                "Please open a database first, then use this command to reveal it in Finder."
            )
            return
        
        database_path = self.current_database_info.get('path')
        database_type = self.current_database_info.get('type')
        
        if not database_path:
            QMessageBox.warning(
                self,
                "Database Path Unknown",
                "Could not determine the path to the currently loaded database."
            )
            return
            
        import subprocess
        from pathlib import Path
        
        try:
            path_obj = Path(database_path)
            
            if database_type == 'single_file':
                # For single files, reveal and select the file in Finder
                if path_obj.exists():
                    subprocess.run(['open', '-R', str(path_obj)], check=True)
                    print(f"✅ Revealed single-file database in Finder: {path_obj.name}")
                else:
                    QMessageBox.warning(
                        self,
                        "File Not Found", 
                        f"The database file no longer exists:\n{path_obj}\n\n"
                        f"It may have been moved or deleted."
                    )
            
            elif database_type == 'multi_file':
                # For multi-file databases, open the containing folder
                if path_obj.is_dir() and path_obj.exists():
                    subprocess.run(['open', str(path_obj)], check=True)
                    print(f"✅ Opened multi-file database folder in Finder: {path_obj.name}")
                else:
                    QMessageBox.warning(
                        self,
                        "Folder Not Found",
                        f"The database folder no longer exists:\n{path_obj}\n\n"
                        f"It may have been moved or deleted."
                    )
            
            else:
                QMessageBox.warning(
                    self,
                    "Unknown Database Type",
                    f"Unknown database type: {database_type}"
                )
                
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(
                self,
                "Finder Error",
                f"Failed to open Finder:\n\n{str(e)}\n\n"
                f"Make sure Finder is available on your system."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An unexpected error occurred:\n\n{str(e)}"
            )

    def show_save_complete_dialog(self, title: str, message: str, file_path: str):
        """Show save complete dialog with 'Reveal in Finder' button"""
        import subprocess
        from pathlib import Path
        from PyQt6.QtWidgets import QMessageBox, QPushButton

        # Create custom message box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Information)

        # Add standard OK button
        ok_button = msg_box.addButton(QMessageBox.StandardButton.Ok)

        # Add custom Reveal in Finder button
        reveal_button = msg_box.addButton("Reveal in Finder", QMessageBox.ButtonRole.ActionRole)

        # Set OK as default button
        msg_box.setDefaultButton(ok_button)

        # Show dialog and get user response
        msg_box.exec()

        # If user clicked Reveal in Finder, open Finder
        if msg_box.clickedButton() == reveal_button:
            try:
                path_obj = Path(file_path)
                if path_obj.exists():
                    subprocess.run(['open', '-R', str(path_obj)], check=True)
                    print(f"✅ Revealed file in Finder: {path_obj.name}")
                else:
                    QMessageBox.warning(
                        self,
                        "File Not Found",
                        f"The file no longer exists:\n{path_obj}\n\n"
                        f"It may have been moved or deleted."
                    )
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(
                    self,
                    "Finder Error",
                    f"Failed to open Finder:\n\n{str(e)}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"An unexpected error occurred:\n\n{str(e)}"
                )

    def open_recent_database(self, path: str, db_type: str):
        """Open a recent database"""
        try:
            if db_type == 'single_file':
                success = self.load_dem_file(path)
                if success:
                    file_path = Path(path)
                    self.update_window_title(file_path.name)
                    recent_db_manager.add_recent_database(path, 'single_file')
                    self.update_recent_databases_menu()
            elif db_type == 'multi_file':
                success = self.load_database_folder(path)
                if success:
                    recent_db_manager.add_recent_database(path, 'multi_file')
                    self.update_recent_databases_menu()
        except Exception as e:
            # Check if this is a GeoTIFF validation error
            error_message = str(e)
            if "appears to contain" in error_message and "data, not elevation data" in error_message:
                QMessageBox.warning(
                    self, 
                    "Invalid Elevation Database", 
                    f"The file '{Path(path).name}' is not a valid elevation database.\n\n"
                    f"This appears to be an image file rather than elevation data. "
                    f"Please select a proper elevation database file."
                )
            else:
                QMessageBox.warning(self, "Error", f"Could not open database:\n{str(e)}")
            recent_db_manager.remove_database(path)
            self.update_recent_databases_menu()

    def clear_recent_databases(self):
        """Clear all recent databases"""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, 
            "Clear Recent Databases",
            "Are you sure you want to clear all recent databases?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            recent_db_manager.clear_recent_databases()
            self.update_recent_databases_menu()

    # Edit menu actions
    def select_all_database(self):
        """Select the full database bounds"""
        if hasattr(self, 'current_database_info') and self.current_database_info:
            # Prevent signal recursion during field updates
            if not self.updating_fields:
                self.updating_fields = True
                try:
                    # Get database bounds
                    west = self.current_database_info.get('west', 0)
                    north = self.current_database_info.get('north', 0)
                    east = self.current_database_info.get('east', 0)
                    south = self.current_database_info.get('south', 0)
                    
                    # Format coordinates properly to avoid floating point artifacts
                    from coordinate_converter import CoordinateConverter
                    is_dms = self.dms_radio.isChecked() if hasattr(self, 'dms_radio') else False
                    
                    # Format each coordinate with proper decimal places or DMS
                    west_text = CoordinateConverter.format_coordinate(west, is_longitude=True, use_dms=is_dms)
                    north_text = CoordinateConverter.format_coordinate(north, is_longitude=False, use_dms=is_dms)
                    east_text = CoordinateConverter.format_coordinate(east, is_longitude=True, use_dms=is_dms)
                    south_text = CoordinateConverter.format_coordinate(south, is_longitude=False, use_dms=is_dms)
                    
                    # Update coordinate input fields with clean formatting
                    self.west_edit.setText(west_text)
                    self.north_edit.setText(north_text)
                    self.east_edit.setText(east_text)
                    self.south_edit.setText(south_text)
                    
                    # Update the red selection rectangle to show the database bounds
                    if hasattr(self.world_map, 'update_selection_rectangles'):
                        self.world_map.update_selection_rectangles(west, east, south, north)
                    
                    # Update map display (this triggers the visual update)
                    if hasattr(self.world_map, 'update'):
                        self.world_map.update()
                    
                    # Update export calculations
                    self.update_export_calculations()
                    
                    # Update status
                    if hasattr(self, 'statusBar'):
                        self.statusBar().showMessage("Selection set to full database bounds")
                    
                    print(f"✅ Selected entire database: W={west_text}, N={north_text}, E={east_text}, S={south_text}")
                    
                except Exception as e:
                    print(f"❌ Error selecting all database: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    self.updating_fields = False
        else:
            # No database loaded - show user message
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "No Database",
                "Please load a DEM file or database first before selecting all."
            )

    # Gradient menu actions
    def import_qgis_gradients(self):
        """Import QGIS color ramps"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import QGIS Color Ramps",
            "",
            "QGIS Files (*.xml *.qml);;All Files (*)"
        )
        
        if file_path:
            try:
                count = self.gradient_manager.import_qgis_gradients(file_path)
                QMessageBox.information(self, "Import Complete", f"Imported {count} gradients successfully.")
                self.load_gradients_into_browser()
            except Exception as e:
                QMessageBox.warning(self, "Import Error", f"Failed to import gradients:\n{str(e)}")

    def export_qgis_gradients(self):
        """Export gradients to QGIS XML format"""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export to QGIS XML",
            "",
            "XML Files (*.xml);;All Files (*)"
        )
        
        if file_path:
            try:
                count = self.gradient_manager.export_qgis_gradients(file_path)
                QMessageBox.information(self, "Export Complete", f"Exported {count} gradients successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Export Error", f"Failed to export gradients:\n{str(e)}")

    def save_gradients(self):
        """Save current gradients"""
        try:
            self.gradient_manager.save_gradients()
            self.status_bar.showMessage("Gradients saved successfully")
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Save Error", f"Failed to save gradients:\n{str(e)}")

    # Help menu actions
    def open_user_guide(self):
        """Open the user guide PDF file"""
        import os
        import platform
        from pathlib import Path
        from PyQt6.QtWidgets import QMessageBox
        
        # Look for user guide PDF in the application directory
        user_guide_path = Path(__file__).parent / "TopoToImage_User_Guide.pdf"
        
        if user_guide_path.exists():
            try:
                # Open PDF with system default viewer
                if platform.system() == "Darwin":  # macOS
                    os.system(f'open "{user_guide_path}"')
                elif platform.system() == "Windows":  # Windows
                    os.startfile(str(user_guide_path))
                else:  # Linux and others
                    os.system(f'xdg-open "{user_guide_path}"')
            except Exception as e:
                QMessageBox.warning(
                    self, 
                    "Error Opening User Guide", 
                    f"Could not open user guide:\n{str(e)}\n\nFile location: {user_guide_path}"
                )
        else:
            QMessageBox.information(
                self, 
                "User Guide Not Available", 
                f"The user guide is not yet available.\n\nWhen complete, it will be located at:\n{user_guide_path}"
            )

    # Signal handlers
    def on_selection_changed(self, bounds):
        """Handle map selection changes - expects a dict with bounds"""
        if not self.updating_fields:
            self.updating_fields = True
            try:
                # Get coordinate values
                west = bounds.get('west', 0)
                north = bounds.get('north', 0)
                east = bounds.get('east', 0)
                south = bounds.get('south', 0)
                
                # Format coordinates with clean display (no trailing zeros)
                from coordinate_validator import coordinate_validator
                is_dms = self.dms_radio.isChecked() if hasattr(self, 'dms_radio') else False
                
                # Format each coordinate with clean formatting (removes trailing zeros)
                west_text = coordinate_validator.format_coordinate_clean(west, is_longitude=True, use_dms=is_dms)
                north_text = coordinate_validator.format_coordinate_clean(north, is_longitude=False, use_dms=is_dms)
                east_text = coordinate_validator.format_coordinate_clean(east, is_longitude=True, use_dms=is_dms)
                south_text = coordinate_validator.format_coordinate_clean(south, is_longitude=False, use_dms=is_dms)
                
                # Update coordinate fields with clean formatting
                self.west_edit.setText(west_text)
                self.north_edit.setText(north_text)
                self.east_edit.setText(east_text)
                self.south_edit.setText(south_text)
                
                # Update export calculations (includes export info and physical dimensions)
                self.update_export_calculations()
                
                print(f"✅ Selection changed: W={west_text}, N={north_text}, E={east_text}, S={south_text}")
                
            finally:
                self.updating_fields = False

    def on_coordinate_field_changed(self):
        """Handle coordinate field changes with validation and snapping"""
        if not self.updating_fields:
            print(f"🔄 on_coordinate_field_changed: User triggered validation")
            self.updating_fields = True
            try:
                # Import validator
                from coordinate_validator import coordinate_validator
                
                # Get current database bounds for validation
                if not hasattr(self, 'current_database_info') or not self.current_database_info:
                    return
                
                database_bounds = self.current_database_info
                is_dms = self.dms_radio.isChecked() if hasattr(self, 'dms_radio') else False
                
                # Parse current longitude values to determine meridian-crossing limits
                try:
                    current_west = coordinate_validator.parse_coordinate_input(self.west_edit.text()) or 0.0
                    current_east = coordinate_validator.parse_coordinate_input(self.east_edit.text()) or 0.0
                except:
                    current_west = 0.0
                    current_east = 0.0
                
                # Validate and format each coordinate with meridian-crossing awareness
                west_val, west_formatted = coordinate_validator.validate_and_format_coordinate(
                    self.west_edit.text(), database_bounds, True, is_dms, current_east)
                north_val, north_formatted = coordinate_validator.validate_and_format_coordinate(
                    self.north_edit.text(), database_bounds, False, is_dms)
                east_val, east_formatted = coordinate_validator.validate_and_format_coordinate(
                    self.east_edit.text(), database_bounds, True, is_dms, current_west)
                south_val, south_formatted = coordinate_validator.validate_and_format_coordinate(
                    self.south_edit.text(), database_bounds, False, is_dms)
                
                # Update fields with validated/formatted values
                self.west_edit.setText(west_formatted)
                self.north_edit.setText(north_formatted)
                self.east_edit.setText(east_formatted)
                self.south_edit.setText(south_formatted)
                
                # Update selection rectangle (NOT database coverage)
                # This should only affect the red selection rectangle, not the green database boundaries
                if hasattr(self.world_map, 'update_selection_rectangles'):
                    self.world_map.update_selection_rectangles(west_val, east_val, south_val, north_val)
                
                # Trigger map redraw to show updated selection
                if hasattr(self.world_map, 'update'):
                    self.world_map.update()
                
                # Update export info
                self.update_export_info_from_selection()
                
            except Exception as e:
                print(f"Error in coordinate field validation: {e}")
                # Fall back to original behavior for invalid input
                try:
                    west = float(self.west_edit.text() or 0)
                    north = float(self.north_edit.text() or 0)
                    east = float(self.east_edit.text() or 0)
                    south = float(self.south_edit.text() or 0)
                    
                    if hasattr(self.world_map, 'update_selection_rectangles'):
                        self.world_map.update_selection_rectangles(west, east, south, north)
                    
                    if hasattr(self.world_map, 'update'):
                        self.world_map.update()
                        
                    self.update_export_info_from_selection()
                except ValueError:
                    pass
            finally:
                self.updating_fields = False

    def on_coordinate_format_changed(self, button):
        """Handle coordinate format changes"""
        if not hasattr(self, 'decimal_radio') or not hasattr(self, 'dms_radio'):
            return
            
        # Determine if DMS format is selected
        is_dms = self.dms_radio.isChecked()
        
        # Prevent recursion during field updates
        if not self.updating_fields:
            self.updating_fields = True
            try:
                from coordinate_converter import CoordinateConverter
                
                # Parse current coordinate values from the fields
                current_west = CoordinateConverter.parse_coordinate(self.west_edit.text())
                current_north = CoordinateConverter.parse_coordinate(self.north_edit.text())
                current_east = CoordinateConverter.parse_coordinate(self.east_edit.text())
                current_south = CoordinateConverter.parse_coordinate(self.south_edit.text())
                
                # Format coordinates in the new format
                west_text = CoordinateConverter.format_coordinate(current_west, is_longitude=True, use_dms=is_dms)
                north_text = CoordinateConverter.format_coordinate(current_north, is_longitude=False, use_dms=is_dms)
                east_text = CoordinateConverter.format_coordinate(current_east, is_longitude=True, use_dms=is_dms)
                south_text = CoordinateConverter.format_coordinate(current_south, is_longitude=False, use_dms=is_dms)
                
                # Update the coordinate input fields
                self.west_edit.setText(west_text)
                self.north_edit.setText(north_text)
                self.east_edit.setText(east_text)
                self.south_edit.setText(south_text)
                
                print(f"✅ Converted coordinates to {'DMS' if is_dms else 'Decimal'} format")
                
            except Exception as e:
                print(f"❌ Error converting coordinate format: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.updating_fields = False

    def on_gradient_selected(self, item):
        """Handle gradient selection"""
        gradient_name = item.text()
        # Update the current gradient selection
        # This will be used when generating previews
        
        # Update elevation controls and radio buttons based on gradient data
        self.update_controls_from_gradient(gradient_name)
        
        # Update preview if available
        self.update_gradient_preview()

    def update_controls_from_gradient(self, gradient_name):
        """Update elevation controls and radio buttons based on selected gradient"""
        elevation_signals_connected = False
        try:
            # Get the gradient data
            gradient = self.gradient_manager.get_gradient(gradient_name)
            if not gradient:
                print(f"⚠️  Gradient '{gradient_name}' not found for control updates")
                return
            
            # Prevent signal recursion during updates
            self.updating_fields = True
            
            # Temporarily disconnect elevation spinbox signals to prevent interference
            if hasattr(self, 'min_elevation') and hasattr(self, 'max_elevation'):
                try:
                    self.min_elevation.valueChanged.disconnect(self.on_elevation_range_changed)
                    self.max_elevation.valueChanged.disconnect(self.on_elevation_range_changed)
                    elevation_signals_connected = True
                except:
                    pass
            
            # Get gradient units for control updates
            gradient_units = getattr(gradient, 'units', 'meters').lower()
            
            # Update elevation spin boxes based on gradient units
            if hasattr(self, 'min_elevation') and hasattr(self, 'max_elevation'):
                if gradient_units == 'percent':
                    # For percent gradients, don't update elevation spin boxes - keep previous values
                    # Spinboxes will only be updated during main terrain rendering (Preview/Save buttons)
                    print(f"📊 Percent gradient selected: Keeping current elevation values (no spinbox update)")
                else:
                    # For meters gradients, update with the gradient's stored values
                    self.min_elevation.setValue(int(gradient.min_elevation))
                    self.max_elevation.setValue(int(gradient.max_elevation))
                    print(f"✅ Updated elevation range: {gradient.min_elevation} to {gradient.max_elevation} {gradient_units}")
            
            # Update radio buttons based on gradient units
            
            # Set elevation units radio buttons (always meters)
            if hasattr(self, 'meters_radio'):
                self.meters_radio.setChecked(True)
                print(f"✅ Set meters radio button (gradient units: {gradient_units})")
            
            # Set scale mode radio buttons based on gradient units
            # ALWAYS set radio buttons when a gradient is selected from the list
            # The dynamic override happens when user manually changes radio buttons
            if gradient_units == 'percent':
                # For percent gradients, use "Scale gradient to elevations found in crop area"
                if hasattr(self, 'scale_to_crop_radio'):
                    self.scale_to_crop_radio.setChecked(True)
                    print(f"✅ Set 'scale to crop' radio button for percent gradient")
                if hasattr(self, 'scale_to_max_min_radio'):
                    self.scale_to_max_min_radio.setChecked(False)
            else:
                # For meters gradients, use "Scale gradient to maximum minimum elevation"
                if hasattr(self, 'scale_to_max_min_radio'):
                    self.scale_to_max_min_radio.setChecked(True)
                    print(f"✅ Set 'scale to max/min' radio button for {gradient_units} gradient")
                if hasattr(self, 'scale_to_crop_radio'):
                    self.scale_to_crop_radio.setChecked(False)
            
            # Update spinbox enabled state based on radio button selection
            self.update_spinbox_state()
            
        except Exception as e:
            print(f"❌ Error updating controls from gradient: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Reconnect elevation spinbox signals
            if elevation_signals_connected and hasattr(self, 'min_elevation') and hasattr(self, 'max_elevation'):
                try:
                    self.min_elevation.valueChanged.connect(self.on_elevation_range_changed)
                    self.max_elevation.valueChanged.connect(self.on_elevation_range_changed)
                except:
                    pass
            
            self.updating_fields = False

    def update_spinbox_state(self):
        """Update the enabled/disabled state of elevation spinboxes based on radio buttons"""
        try:
            # Check which radio button is selected
            scale_to_crop = hasattr(self, 'scale_to_crop_radio') and self.scale_to_crop_radio.isChecked()
            scale_to_max_min = hasattr(self, 'scale_to_max_min_radio') and self.scale_to_max_min_radio.isChecked()
            
            # Update spinbox enabled state
            if hasattr(self, 'min_elevation') and hasattr(self, 'max_elevation'):
                if scale_to_crop:
                    # "Scale gradient to elevation found in crop area" = spinboxes GRAYED OUT
                    self.min_elevation.setEnabled(False)
                    self.max_elevation.setEnabled(False)
                    print(f"🔒 Elevation spinboxes disabled (crop area mode)")
                elif scale_to_max_min:
                    # "Scale gradient to Maximum and Minimum elevation" = spinboxes ACTIVE
                    self.min_elevation.setEnabled(True)
                    self.max_elevation.setEnabled(True)
                    print(f"🔓 Elevation spinboxes enabled (max/min mode)")
                else:
                    # Default case - enable them
                    self.min_elevation.setEnabled(True)
                    self.max_elevation.setEnabled(True)
                    
        except Exception as e:
            print(f"❌ Error updating spinbox state: {e}")

    # on_export_type_changed removed - no longer needed with separated export functions

    def on_width_changed(self):
        """Handle width field changes"""
        if self.updating_fields:
            return
        try:
            width = float(self.width_edit.text())
            self.export_logic.set_width(width)
            # Auto-switch to width lock when user types in width field
            if hasattr(self, 'lock_width_radio'):
                self.lock_width_radio.setChecked(True)
            self.update_export_calculations()
        except ValueError:
            pass

    def on_height_changed(self):
        """Handle height field changes"""
        if self.updating_fields:
            return
        try:
            height = float(self.height_edit.text())
            self.export_logic.set_height(height)
            # Auto-switch to height lock when user types in height field
            if hasattr(self, 'lock_height_radio'):
                self.lock_height_radio.setChecked(True)
            self.update_export_calculations()
        except ValueError:
            pass

    def on_resolution_changed(self):
        """Handle resolution field changes"""
        if self.updating_fields:
            return
        try:
            resolution = float(self.resolution_edit.text())
            self.export_logic.set_resolution(resolution)
            # Auto-switch to resolution lock when user types in resolution field
            if hasattr(self, 'lock_resolution_radio'):
                self.lock_resolution_radio.setChecked(True)
            self.update_export_calculations()
        except ValueError:
            pass

    def on_export_scale_combo_changed(self):
        """Handle export scale combo box changes"""
        try:
            scale_text = self.export_scale_combo.currentText()
            if scale_text and scale_text != "Custom":
                # Parse percentage from text like "100%" -> 100
                if "%" in scale_text:
                    percentage_value = float(scale_text.replace("%", ""))
                    # Temporarily disconnect spinner signal to prevent recursion
                    if hasattr(self, 'export_scale_spinbox'):
                        self.export_scale_spinbox.valueChanged.disconnect()
                        self.export_scale_spinbox.setValue(percentage_value)
                        self.export_scale_spinbox.valueChanged.connect(self.on_export_scale_spinbox_changed)
                self.update_export_calculations()
        except (ValueError, AttributeError):
            pass

    def reset_export_scale_to_100_percent(self):
        """Reset export scale to 100% when loading a new database"""
        try:
            if hasattr(self, 'export_scale_spinbox'):
                # Temporarily disconnect signals to prevent unnecessary updates
                self.export_scale_spinbox.valueChanged.disconnect()
                self.export_scale_spinbox.setValue(100.0)
                self.export_scale_spinbox.valueChanged.connect(self.on_export_scale_spinbox_changed)
                print("🔄 Export scale reset to 100%")
                
            if hasattr(self, 'export_scale_combo'):
                self.export_scale_combo.currentTextChanged.disconnect()
                self.export_scale_combo.setCurrentText("100%")
                self.export_scale_combo.currentTextChanged.connect(self.on_export_scale_combo_changed)
                
        except Exception as e:
            print(f"⚠️ Could not reset export scale: {e}")

    def on_export_scale_spinbox_changed(self):
        """Handle export scale spinbox value changes"""
        try:
            scale_value = self.export_scale_spinbox.value()
            
            # Check if the spinner value matches one of the predefined percentages
            predefined_percentages = [100, 50, 33.3, 25, 10]
            combo_text = f"{scale_value}%"
            
            # Handle special case for 33.3%
            if abs(scale_value - 33.3) < 0.1:
                combo_text = "33.3%"
            
            # Temporarily disconnect combo signal to prevent recursion
            if hasattr(self, 'export_scale_combo'):
                self.export_scale_combo.currentTextChanged.disconnect()
                
                # Check if the value matches a predefined percentage
                if any(abs(scale_value - pct) < 0.1 for pct in predefined_percentages):
                    # Set to the matching predefined percentage
                    self.export_scale_combo.setCurrentText(combo_text)
                else:
                    # Set to "Custom" for any other value
                    self.export_scale_combo.setCurrentText("Custom")
                
                # Reconnect signal
                self.export_scale_combo.currentTextChanged.connect(self.on_export_scale_combo_changed)
            
            # Update calculations based on scale
            self.update_export_calculations()
        except AttributeError:
            pass

    def on_lock_option_changed(self, button):
        """Handle lock radio button changes"""
        try:
            if not button.isChecked():
                return
                
            # Determine which lock option was selected
            if hasattr(self, 'lock_width_radio') and button == self.lock_width_radio:
                self.export_logic.set_lock(LockType.WIDTH)
            elif hasattr(self, 'lock_height_radio') and button == self.lock_height_radio:
                self.export_logic.set_lock(LockType.HEIGHT)
            elif hasattr(self, 'lock_resolution_radio') and button == self.lock_resolution_radio:
                self.export_logic.set_lock(LockType.RESOLUTION)
            
            # Update calculations based on new lock setting
            self.update_export_calculations()
        except AttributeError:
            pass

    def on_units_changed(self, button):
        """Handle units radio button changes"""
        try:
            if not button.isChecked():
                return
                
            # Determine which units option was selected and update unit labels
            if hasattr(self, 'inches_radio') and button == self.inches_radio:
                self.export_logic.set_units(Units.INCHES)
                self.update_unit_labels("In.")
            elif hasattr(self, 'picas_radio') and button == self.picas_radio:
                self.export_logic.set_units(Units.PICAS)
                self.update_unit_labels("Pi.")
            elif hasattr(self, 'points_radio') and button == self.points_radio:
                self.export_logic.set_units(Units.POINTS)
                self.update_unit_labels("Pt.")
            elif hasattr(self, 'cm_radio') and button == self.cm_radio:
                self.export_logic.set_units(Units.CENTIMETERS)
                self.update_unit_labels("CM")
            
            # Update calculations based on new units
            self.update_export_calculations()
        except AttributeError:
            pass

    def update_unit_labels(self, unit_text):
        """Update the unit labels for width and height based on selected units"""
        try:
            # Update width unit label
            if hasattr(self, 'width_unit_label'):
                self.width_unit_label.setText(unit_text)
                print(f"✅ Updated width unit label to: {unit_text}")
            
            # Update height unit label
            if hasattr(self, 'height_unit_label'):
                self.height_unit_label.setText(unit_text)
                print(f"✅ Updated height unit label to: {unit_text}")
            
            # Resolution unit label always stays "Pix/In." regardless of units
            if hasattr(self, 'resolution_unit_label'):
                self.resolution_unit_label.setText("Pix/In.")
                print(f"✅ Resolution unit label remains: Pix/In.")
                
        except Exception as e:
            print(f"❌ Error updating unit labels: {e}")

    def on_elevation_range_changed(self):
        """Handle elevation min/max range changes"""
        try:
            min_elev = self.min_elevation.value()
            max_elev = self.max_elevation.value()
            
            # Ensure min <= max
            if min_elev > max_elev:
                if self.sender() == self.min_elevation:
                    self.max_elevation.setValue(min_elev)
                else:
                    self.min_elevation.setValue(max_elev)
            
            # Refresh preview if available and in max/min elevation mode
            # Only update preview when "Scale to max/min elevation" is selected
            # because in crop mode, spinbox values don't affect the preview
            scale_to_max_min = hasattr(self, 'scale_to_max_min_radio') and self.scale_to_max_min_radio.isChecked()
            
            if scale_to_max_min:
                print(f"📏 Elevation range changed to {min_elev}-{max_elev}m → updating preview")
                self.update_gradient_preview()
            
        except AttributeError:
            pass

    def on_elevation_units_changed(self, button):
        """Handle elevation units radio button changes (meters only)"""
        try:
            if not button.isChecked():
                return
                
            # Only meters is supported
            if hasattr(self, 'meters_radio') and button == self.meters_radio:
                # Update terrain renderer with meters units
                self.terrain_renderer.set_elevation_units('meters')
                
                # Refresh preview if available
                if hasattr(self, 'current_preview_image'):
                    self.update_terrain_preview()
        except AttributeError:
            pass

    def on_scale_mode_changed(self, button):
        """Handle scale mode radio button changes (scale to crop vs max/min)"""
        try:
            if not button.isChecked():
                return
                
            # Determine scale mode
            scale_to_crop = hasattr(self, 'scale_to_crop_radio') and button == self.scale_to_crop_radio
            scale_to_max_min = hasattr(self, 'scale_to_max_min_radio') and button == self.scale_to_max_min_radio
            
            print(f"📻 Scale mode changed: crop={scale_to_crop}, max_min={scale_to_max_min}")
            
            # IMPORTANT: Radio buttons now dynamically override gradient type!
            # - "Scale to crop area" = Treat gradient as Percent type
            # - "Scale to max/min" = Treat gradient as Meters type
            
            # When radio buttons are manually changed, we need to:
            # 1. Update the preview icon (using preview database)
            # 2. If in crop mode, scan the actual loaded database for elevation range
            
            # First, update spinbox enabled state
            self.update_spinbox_state()
            
            # Second, update the preview icon
            self.update_gradient_preview()
            
            # Third, if switching to crop mode, scan the actual database if available
            if scale_to_crop:
                print(f"📊 Switching to crop mode - scanning actual database for elevation range")
                self._scan_actual_database_for_elevation_range()
            else:
                print(f"📏 Switching to max/min mode - using spinbox values")
            
            print(f"✅ Scale mode change complete")
            
        except AttributeError as e:
            print(f"⚠️ Error in scale mode change: {e}")
        except Exception as e:
            print(f"❌ Unexpected error in scale mode change: {e}")
            import traceback
            traceback.print_exc()

    def _scan_actual_database_for_elevation_range(self):
        """Scan the actual loaded database/DEM file for elevation range in selected coordinates"""
        try:
            print(f"🔍 Scanning actual database for elevation range...")
            
            # Check if we have a loaded database or DEM file
            has_database = hasattr(self, 'current_database_info') and self.current_database_info
            has_dem_file = hasattr(self, 'current_dem_file') and self.current_dem_file
            
            if not has_database and not has_dem_file:
                print(f"⚠️ No database or DEM file loaded - cannot scan for elevation range")
                return
            
            # Get current selection coordinates
            try:
                west = float(self.west_edit.text() or 0)
                north = float(self.north_edit.text() or 0)
                east = float(self.east_edit.text() or 0)
                south = float(self.south_edit.text() or 0)
                print(f"📍 Selection coordinates: W={west}, N={north}, E={east}, S={south}")
            except (ValueError, AttributeError):
                print(f"⚠️ Invalid coordinates - cannot scan elevation range")
                return
            
            elevation_data = None
            
            # Try to load elevation data based on database type
            if has_database and self.current_database_info.get('type') == 'multi_file':
                print(f"🗂️ Loading elevation data from multi-file database...")
                try:
                    # For multi-file databases, we need to assemble the selection area
                    from multi_file_database import MultiFileDatabase
                    
                    database_path = self.current_database_info.get('path')
                    if database_path:
                        multi_db = MultiFileDatabase(database_path)
                        # Load elevation data for the selected area
                        elevation_data = multi_db.load_elevation_data_for_bounds(west, east, south, north)
                        print(f"✅ Loaded elevation data from multi-file database: shape {elevation_data.shape if elevation_data is not None else 'None'}")
                except Exception as e:
                    print(f"❌ Error loading from multi-file database: {e}")
            
            elif has_database and self.current_database_info.get('type') == 'single_file':
                print(f"📄 Loading elevation data from single-file database...")
                try:
                    # For single-file databases, use the dem_reader
                    if hasattr(self, 'dem_reader') and self.dem_reader:
                        elevation_data = self.dem_reader.load_elevation_data()
                        print(f"✅ Loaded elevation data from single-file database: shape {elevation_data.shape if elevation_data is not None else 'None'}")
                    else:
                        print(f"⚠️ No DEM reader available for single-file database")
                except Exception as e:
                    print(f"❌ Error loading from single-file database: {e}")
            
            elif has_dem_file:
                print(f"📄 Loading elevation data from single DEM file...")
                try:
                    # For single DEM files, use the existing dem_reader
                    if hasattr(self, 'dem_reader') and self.dem_reader:
                        elevation_data = self.dem_reader.load_elevation_data()
                        print(f"✅ Loaded elevation data from DEM reader: shape {elevation_data.shape if elevation_data is not None else 'None'}")
                    else:
                        # Create a new DEM reader
                        from dem_reader import DEMReader
                        dem_reader = DEMReader(self.current_dem_file)
                        elevation_data = dem_reader.load_elevation_data()
                        print(f"✅ Loaded elevation data from new DEM reader: shape {elevation_data.shape if elevation_data is not None else 'None'}")
                except Exception as e:
                    print(f"❌ Error loading from DEM file: {e}")
            
            # Scan elevation data for min/max
            if elevation_data is not None:
                import numpy as np
                valid_data = elevation_data[~np.isnan(elevation_data)]
                if len(valid_data) > 0:
                    database_min = float(np.min(valid_data))
                    database_max = float(np.max(valid_data))
                    print(f"📊 Found elevation range: {database_min:.1f}m to {database_max:.1f}m")
                    
                    # Update spinboxes with discovered values
                    if hasattr(self, 'min_elevation') and hasattr(self, 'max_elevation'):
                        print(f"📦 Updating spinboxes with discovered elevation range")
                        
                        # Temporarily disconnect signals to prevent recursion
                        elevation_signals_connected = False
                        try:
                            self.min_elevation.valueChanged.disconnect(self.on_elevation_range_changed)
                            self.max_elevation.valueChanged.disconnect(self.on_elevation_range_changed)
                            elevation_signals_connected = True
                        except:
                            pass
                        
                        # Update values
                        self.min_elevation.setValue(int(database_min))
                        self.max_elevation.setValue(int(database_max))
                        
                        # Reconnect signals
                        if elevation_signals_connected:
                            try:
                                self.min_elevation.valueChanged.connect(self.on_elevation_range_changed)
                                self.max_elevation.valueChanged.connect(self.on_elevation_range_changed)
                            except:
                                pass
                        
                        print(f"✅ Spinboxes updated: {int(database_min)} - {int(database_max)}")
                    else:
                        print(f"⚠️ Spinbox controls not found")
                else:
                    print(f"⚠️ No valid elevation data found in scanned area")
            else:
                print(f"⚠️ No elevation data available for scanning")
                
        except Exception as e:
            print(f"❌ Error scanning actual database: {e}")
            import traceback
            traceback.print_exc()

    # Core functionality methods
    def load_dem_file(self, file_path):
        """Load a single DEM file"""
        try:
            file_path = Path(file_path)  # Ensure it's a Path object
            self.current_dem_file = file_path
            
            # Load the DEM file using DEMReader
            self.dem_reader = DEMReader(file_path)
            
            # Clear any database-specific background when loading individual files
            if hasattr(self.world_map, 'clear_database_background'):
                self.world_map.clear_database_background()
            
            # Set DEM coverage on world map
            if self.dem_reader.bounds:
                # Extract bounds for our database info structure
                bounds = self.dem_reader.bounds
                
                # Ensure bounds are numeric - bounds is a dictionary
                west = float(bounds['west'])
                south = float(bounds['south']) 
                east = float(bounds['east'])
                north = float(bounds['north'])
                
                # Convert bounds dict to the expected format for set_dem_coverage
                coverage_bounds = {
                    'west': west, 'east': east, 'north': north, 'south': south
                }
                # For single-file databases, clear any tile boundaries first
                if hasattr(self.world_map, 'set_tile_boundaries'):
                    self.world_map.set_tile_boundaries([])
                self.world_map.set_dem_coverage(coverage_bounds)
                if hasattr(self.world_map, 'set_dem_reader'):
                    self.world_map.set_dem_reader(self.dem_reader)  # Set DEM reader for pixel snapping
                print(f"✓ Set DEM coverage: {self.dem_reader.bounds}")
                
                # Create database info structure  
                database_info = {
                    'type': 'single_file',
                    'path': str(file_path),
                    'west': west,
                    'north': north,
                    'east': east,
                    'south': south,
                    'width_pixels': self.dem_reader.width,
                    'height_pixels': self.dem_reader.height,
                    'pix_per_degree': abs(self.dem_reader.width / (east - west)) if east != west else 0
                }
                
                # Check if this is a database switch (preserve selection) or first load (select full database)
                is_database_switch = hasattr(self, 'current_database_info') and self.current_database_info is not None
                
                self.current_database_info = database_info
                
                # Reset export scale to 100% for new database
                self.reset_export_scale_to_100_percent()
                
                self.update_database_info_display(database_info)
                # Preserve selection when switching databases, select full database for first load
                self.update_coordinate_fields_from_database(database_info, preserve_selection=is_database_switch)
                
                # Update world map display
                self.world_map.update()
                
                self.status_bar.showMessage(f"Loaded: {file_path.name}")
                return True
            else:
                self.status_bar.showMessage("Failed to get DEM bounds")
                return False
                
        except Exception as e:
            # Check if this is a GeoTIFF validation error (not a valid elevation database)
            error_message = str(e)
            if "appears to contain" in error_message and "data, not elevation data" in error_message:
                # This is a validation error - show user-friendly dialog
                QMessageBox.warning(
                    self, 
                    "Invalid Elevation Database", 
                    f"The file '{file_path.name}' is not a valid elevation database.\n\n"
                    f"This appears to be an image file rather than elevation data. "
                    f"Please select a proper elevation database file:\n\n"
                    f"• .dem or .bil format files with header files\n"
                    f"• GeoTIFF files containing elevation data (not images)\n\n"
                    f"For more information about supported formats, see the Help menu."
                )
                self.status_bar.showMessage(f"Invalid elevation database: {file_path.name}")
            else:
                # Generic error - show in status bar and console
                self.status_bar.showMessage(f"Error loading file: {str(e)}")
                print(f"DEM file loading error: {e}")
                import traceback
                traceback.print_exc()
            return False

    def load_database_folder(self, folder_path):
        """Load a database folder"""
        try:
            folder_path = str(folder_path)  # Ensure it's a string
            
            # Load multi-tile database
            if self.multi_tile_loader.load_dataset(folder_path):
                # Successfully loaded multi-tile dataset
                dataset_info = self.multi_tile_loader.get_dataset_info()
                coverage_bounds = self.multi_tile_loader.get_coverage_bounds()
                
                if coverage_bounds:
                    west, north, east, south = coverage_bounds
                    
                    # Create database info structure
                    database_info = {
                        'type': 'multi_file',
                        'path': folder_path,
                        'west': west,
                        'north': north,
                        'east': east,
                        'south': south,
                        'width_pixels': dataset_info.get('total_width_pixels', 0),
                        'height_pixels': dataset_info.get('total_height_pixels', 0),
                        'pix_per_degree': dataset_info.get('pix_per_degree', 0),  # Fixed: was 'pixels_per_degree'
                        'tile_count': dataset_info.get('tiles_total', 0)  # Fixed: use tiles_total from get_dataset_info
                    }
                    
                    self.current_database_info = database_info
                    
                    # Clear single-file database reference since we're now using multi-file
                    self.current_dem_file = None
                    
                    # Reset export scale to 100% for new database
                    self.reset_export_scale_to_100_percent()
                    
                    # Set up map for multi-file database selection
                    # This enables selection rectangle drawing for multi-file databases
                    
                    # Get tile boundaries from the multi-tile loader
                    tile_boundaries = []
                    if hasattr(self.multi_tile_loader, 'tiles'):
                        for tile_name, tile_info in self.multi_tile_loader.tiles.items():
                            if 'bounds' in tile_info:
                                bounds = tile_info['bounds']
                                # Convert [west, north, east, south] to boundary dict
                                if len(bounds) >= 4:
                                    tile_boundaries.append({
                                        'west': bounds[0],
                                        'north': bounds[1], 
                                        'east': bounds[2],
                                        'south': bounds[3],
                                        'name': tile_name
                                    })
                    
                    # Set tile boundaries on the map - this enables selection rectangle drawing
                    if hasattr(self.world_map, 'set_tile_boundaries'):
                        self.world_map.set_tile_boundaries(tile_boundaries)
                        print(f"✅ Set {len(tile_boundaries)} tile boundaries for selection")
                    
                    # Debug: Print what database_info contains
                    print(f"🔍 Database info being passed to display:")
                    print(f"    West: {database_info.get('west', 'MISSING')}")
                    print(f"    North: {database_info.get('north', 'MISSING')}")
                    print(f"    East: {database_info.get('east', 'MISSING')}")
                    print(f"    South: {database_info.get('south', 'MISSING')}")
                    print(f"    Pixels/degree: {database_info.get('pix_per_degree', 'MISSING')}")
                    
                    # Update database info display and coordinate fields
                    self.update_database_info_display(database_info)
                    # For multi-file database loads, preserve existing selection if possible
                    self.update_coordinate_fields_from_database(database_info, preserve_selection=True)
                    
                    # Set coverage bounds on the map for visual feedback
                    # Set overall coverage bounds for green boundary line around entire database
                    # This works alongside tile boundaries - both can be displayed simultaneously
                    coverage_bounds_dict = {'west': west, 'north': north, 'east': east, 'south': south}
                    if hasattr(self.world_map, 'set_dem_coverage'):
                        self.world_map.set_dem_coverage(coverage_bounds_dict)
                    
                    # Set database-specific background (e.g., Gtopo30 background)
                    database_path = Path(folder_path)
                    database_name = database_path.name.lower()
                    
                    # Detect database type for background switching
                    if 'gtopo30' in database_name:
                        self.world_map.set_database_background('gtopo30', database_path)
                        print(f"🗺️ Set Gtopo30 background for database: {database_path.name}")
                    else:
                        # For non-gtopo30 databases, clear any database-specific background and use default
                        self.world_map.clear_database_background()
                        print(f"🗺️ Using default background for database: {database_path.name}")
                    
                    # Update window title and status
                    self.update_window_title(Path(folder_path).name)
                    self.status_bar.showMessage(f"Loaded database: {Path(folder_path).name}")
                    
                    print(f"✅ Multi-file database loaded: {dataset_info.get('name', Path(folder_path).name)}")
                    print(f"   Dimensions: {database_info['width_pixels']}x{database_info['height_pixels']} pixels")
                    print(f"   Geographic bounds: {west:.2f}°W to {east:.2f}°E, {south:.2f}°S to {north:.2f}°N")
                    print(f"   Tiles: {database_info['tile_count']}")
                    
                    # Update menu state after successful database load
                    self.update_preview_icon_menu_state()
                    
                    return True
                else:
                    self.status_bar.showMessage("Failed to get coverage bounds")
                    return False
            else:
                self.status_bar.showMessage("Failed to load database folder")
                return False
                
        except Exception as e:
            self.status_bar.showMessage(f"Error loading database: {str(e)}")
            print(f"Database loading error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_window_title(self, filename):
        """Update the window title with the loaded file/database name"""
        self.setWindowTitle(f"TopoToImage - {filename}")

    def update_coordinate_fields_from_database(self, database_info, preserve_selection=True):
        """Update coordinate fields with database bounds or preserve existing selection"""
        if not self.updating_fields:
            print(f"🔄 update_coordinate_fields_from_database: preserve_selection={preserve_selection}")
            self.updating_fields = True
            
            # Temporarily disconnect coordinate field signals to prevent interference
            self.west_edit.editingFinished.disconnect()
            self.west_edit.returnPressed.disconnect()
            self.north_edit.editingFinished.disconnect()
            self.north_edit.returnPressed.disconnect()
            self.east_edit.editingFinished.disconnect()
            self.east_edit.returnPressed.disconnect()
            self.south_edit.editingFinished.disconnect()
            self.south_edit.returnPressed.disconnect()
            
            try:
                # Get database bounds
                db_west = database_info.get('west', 0)
                db_north = database_info.get('north', 0) 
                db_east = database_info.get('east', 0)
                db_south = database_info.get('south', 0)
                
                if preserve_selection:
                    # Try to preserve existing selection if it overlaps with new database
                    try:
                        # Use coordinate validator to parse DMS coordinates properly
                        from coordinate_validator import coordinate_validator
                        
                        current_west_parsed = coordinate_validator.parse_coordinate_input(self.west_edit.text() or "0")
                        current_north_parsed = coordinate_validator.parse_coordinate_input(self.north_edit.text() or "0")
                        current_east_parsed = coordinate_validator.parse_coordinate_input(self.east_edit.text() or "0")
                        current_south_parsed = coordinate_validator.parse_coordinate_input(self.south_edit.text() or "0")
                        
                        current_west = current_west_parsed if current_west_parsed is not None else 0
                        current_north = current_north_parsed if current_north_parsed is not None else 0
                        current_east = current_east_parsed if current_east_parsed is not None else 0
                        current_south = current_south_parsed if current_south_parsed is not None else 0
                        
                        # Check if current selection is just zeros (no real selection to preserve)
                        is_empty_selection = (current_west == 0 and current_north == 0 and 
                                            current_east == 0 and current_south == 0)
                        
                        if is_empty_selection:
                            # No real selection to preserve - use database bounds
                            west, north, east, south = db_west, db_north, db_east, db_south
                            print(f"✓ Empty selection detected, using database bounds: {west}, {north}, {east}, {south}")
                        else:
                            # Check if current selection overlaps with new database bounds
                            overlaps = (current_west < db_east and current_east > db_west and
                                      current_south < db_north and current_north > db_south)
                            
                            if overlaps:
                                # Clamp current selection to database bounds and pixel grid
                                west = max(current_west, db_west)
                                east = min(current_east, db_east)
                                north = min(current_north, db_north)
                                south = max(current_south, db_south)
                                
                                # Clamp to pixel grid if possible
                                west, north, east, south = self.clamp_to_pixel_grid(
                                    west, north, east, south, database_info
                                )
                                
                                print(f"✓ Preserved and clamped selection: {west}, {north}, {east}, {south}")
                            else:
                                # Use database bounds if no overlap
                                west, north, east, south = db_west, db_north, db_east, db_south
                                print(f"✓ No overlap, using database bounds: {west}, {north}, {east}, {south}")
                    except (ValueError, TypeError):
                        # If parsing fails, use database bounds
                        west, north, east, south = db_west, db_north, db_east, db_south
                        print(f"✓ Parse error, using database bounds: {west}, {north}, {east}, {south}")
                else:
                    # Use database bounds directly
                    west, north, east, south = db_west, db_north, db_east, db_south
                
                # Format coordinates with clean decimal display
                from coordinate_validator import coordinate_validator
                is_dms = self.dms_radio.isChecked() if hasattr(self, 'dms_radio') else False
                
                # Format each coordinate with clean formatting (remove trailing zeros)
                west_text = coordinate_validator.format_coordinate_clean(west, is_longitude=True, use_dms=is_dms)
                north_text = coordinate_validator.format_coordinate_clean(north, is_longitude=False, use_dms=is_dms)
                east_text = coordinate_validator.format_coordinate_clean(east, is_longitude=True, use_dms=is_dms)
                south_text = coordinate_validator.format_coordinate_clean(south, is_longitude=False, use_dms=is_dms)
                
                # Update coordinate input fields
                print(f"   Setting coordinate fields: [{west_text}, {north_text}, {east_text}, {south_text}]")
                self.west_edit.setText(west_text)
                self.north_edit.setText(north_text)
                self.east_edit.setText(east_text)
                self.south_edit.setText(south_text)
                
                # Note: Database coverage should be set elsewhere, not here
                # This method only handles coordinate field updates and selection preservation
                
                # Update the selection rectangle to match the database bounds
                # This ensures the red rectangle updates properly when opening a new database
                if hasattr(self.world_map, 'update_selection_rectangles'):
                    self.world_map.update_selection_rectangles(west, east, south, north)
                elif hasattr(self.world_map, 'handle_database_loaded'):
                    # Use the smart selection management that handles overlap logic
                    database_bounds = {'west': west, 'north': north, 'east': east, 'south': south}
                    self.world_map.handle_database_loaded(database_bounds)
                
                # Trigger a map update to redraw
                if hasattr(self.world_map, 'update'):
                    self.world_map.update()
                    
            finally:
                # Reconnect coordinate field signals
                self.west_edit.editingFinished.connect(self.on_coordinate_field_changed)
                self.west_edit.returnPressed.connect(self.on_coordinate_field_changed)
                self.north_edit.editingFinished.connect(self.on_coordinate_field_changed)
                self.north_edit.returnPressed.connect(self.on_coordinate_field_changed)
                self.east_edit.editingFinished.connect(self.on_coordinate_field_changed)
                self.east_edit.returnPressed.connect(self.on_coordinate_field_changed)
                self.south_edit.editingFinished.connect(self.on_coordinate_field_changed)
                self.south_edit.returnPressed.connect(self.on_coordinate_field_changed)
                
                self.updating_fields = False
                
        # Update export calculations after coordinate fields are updated
        # This ensures export info and physical dimensions reflect the new database
        self.update_export_calculations()
    
    def clamp_to_pixel_grid(self, west, north, east, south, database_info):
        """Clamp coordinates to the pixel grid of the database"""
        try:
            # Get database bounds and resolution
            db_west = database_info.get('west', 0)
            db_north = database_info.get('north', 0)
            db_east = database_info.get('east', 0)
            db_south = database_info.get('south', 0)
            
            # Calculate resolution
            width_pixels = database_info.get('width_pixels', 0)
            height_pixels = database_info.get('height_pixels', 0)
            
            if width_pixels > 0 and height_pixels > 0:
                # Calculate degrees per pixel
                degrees_per_pixel_x = abs(db_east - db_west) / width_pixels
                degrees_per_pixel_y = abs(db_north - db_south) / height_pixels
                
                # Snap coordinates to pixel boundaries
                # For west/east: round to nearest pixel boundary from db_west
                west_offset = west - db_west
                west_pixel = round(west_offset / degrees_per_pixel_x)
                west = db_west + (west_pixel * degrees_per_pixel_x)
                
                east_offset = east - db_west
                east_pixel = round(east_offset / degrees_per_pixel_x)
                east = db_west + (east_pixel * degrees_per_pixel_x)
                
                # For north/south: round to nearest pixel boundary from db_north
                north_offset = db_north - north  # Note: north decreases as we go down
                north_pixel = round(north_offset / degrees_per_pixel_y)
                north = db_north - (north_pixel * degrees_per_pixel_y)
                
                south_offset = db_north - south
                south_pixel = round(south_offset / degrees_per_pixel_y)
                south = db_north - (south_pixel * degrees_per_pixel_y)
                
                print(f"✓ Clamped to pixel grid: resolution {degrees_per_pixel_x:.6f}°/pixel")
            
            return west, north, east, south
            
        except Exception as e:
            print(f"Warning: Could not clamp to pixel grid: {e}")
            return west, north, east, south

    def update_export_info_from_selection(self):
        """Update export info based on current selection"""
        try:
            # Import coordinate validator for DMS parsing
            from coordinate_validator import coordinate_validator
            
            # Parse coordinates using validator (handles both decimal and DMS)
            west_parsed = coordinate_validator.parse_coordinate_input(self.west_edit.text() or "0")
            north_parsed = coordinate_validator.parse_coordinate_input(self.north_edit.text() or "0")
            east_parsed = coordinate_validator.parse_coordinate_input(self.east_edit.text() or "0")
            south_parsed = coordinate_validator.parse_coordinate_input(self.south_edit.text() or "0")
            
            west = west_parsed if west_parsed is not None else 0
            north = north_parsed if north_parsed is not None else 0
            east = east_parsed if east_parsed is not None else 0
            south = south_parsed if south_parsed is not None else 0
            
            # Calculate basic export info from selection bounds
            width_degrees = abs(east - west)
            height_degrees = abs(north - south)
            
            # Use current database resolution instead of hardcoded 120.0
            current_pix_per_degree = 120.0  # Default fallback
            if hasattr(self, 'current_database_info') and self.current_database_info:
                current_pix_per_degree = self.current_database_info.get('pix_per_degree', 120.0)
            
            # Get export scale percentage from spinner (default to 100% if not available)
            export_scale_percent = 100.0  # Default to 100%
            if hasattr(self, 'export_scale_spinbox'):
                export_scale_percent = self.export_scale_spinbox.value()
            
            # Apply export scale to pixel calculations
            scale_factor = export_scale_percent / 100.0
            base_width_pixels = width_degrees * current_pix_per_degree
            base_height_pixels = height_degrees * current_pix_per_degree
            scaled_width_pixels = int(base_width_pixels * scale_factor)
            scaled_height_pixels = int(base_height_pixels * scale_factor)
            
            # Calculate scaled pixels per degree (higher value for smaller scale)
            scaled_pix_per_degree = current_pix_per_degree * scale_factor
            
            export_info = {
                'west': west,
                'north': north, 
                'east': east,
                'south': south,
                'width_pixels': scaled_width_pixels,
                'height_pixels': scaled_height_pixels,
                'pix_per_degree': scaled_pix_per_degree
            }
            
            # Update export file info display
            self.update_database_info_display(export_info=export_info)
            
        except Exception as e:
            print(f"Error updating export info: {e}")

    def update_export_calculations(self):
        """Update export calculations based on current settings"""
        # First update the export info (this calculates scaled pixel dimensions)
        self.update_export_info_from_selection()
        
        # Get the current pixel dimensions from the last calculated export info
        try:
            # Extract pixel dimensions from coordinate fields and scale
            from coordinate_validator import coordinate_validator
            
            west_parsed = coordinate_validator.parse_coordinate_input(self.west_edit.text() or "0")
            north_parsed = coordinate_validator.parse_coordinate_input(self.north_edit.text() or "0")
            east_parsed = coordinate_validator.parse_coordinate_input(self.east_edit.text() or "0")
            south_parsed = coordinate_validator.parse_coordinate_input(self.south_edit.text() or "0")
            
            west = west_parsed if west_parsed is not None else 0
            north = north_parsed if north_parsed is not None else 0
            east = east_parsed if east_parsed is not None else 0
            south = south_parsed if south_parsed is not None else 0
            
            # Calculate pixel dimensions with export scale
            width_degrees = abs(east - west)
            height_degrees = abs(north - south)
            
            current_pix_per_degree = 120.0  # Default fallback
            if hasattr(self, 'current_database_info') and self.current_database_info:
                current_pix_per_degree = self.current_database_info.get('pix_per_degree', 120.0)
            
            # Get export scale and apply it
            export_scale_percent = 100.0
            if hasattr(self, 'export_scale_spinbox'):
                export_scale_percent = self.export_scale_spinbox.value()
            
            scale_factor = export_scale_percent / 100.0
            pixel_width = int(width_degrees * current_pix_per_degree * scale_factor)
            pixel_height = int(height_degrees * current_pix_per_degree * scale_factor)
            
            # Update export logic with current pixel dimensions
            self.export_logic.set_pixel_dimensions(pixel_width, pixel_height)
            
            # Get calculated values from export logic and update UI fields
            calculated_width = self.export_logic.get_width()
            calculated_height = self.export_logic.get_height()
            calculated_resolution = self.export_logic.get_resolution()
            
            # Update UI fields with calculated values (prevent recursion)
            self.updating_fields = True
            try:
                if hasattr(self, 'width_edit'):
                    self.width_edit.setText(f"{calculated_width:.3f}")
                if hasattr(self, 'height_edit'):
                    self.height_edit.setText(f"{calculated_height:.3f}")
                if hasattr(self, 'resolution_edit'):
                    self.resolution_edit.setText(f"{calculated_resolution:.3f}")
            finally:
                self.updating_fields = False
                
        except Exception as e:
            print(f"Error in export calculations: {e}")

    def update_gradient_preview(self):
        """Update the gradient preview with the selected gradient applied to preview database"""
        try:
            print(f"🎨 === UPDATE_GRADIENT_PREVIEW CALLED ===")
            debug_logger.info("🎨 === STARTING GRADIENT PREVIEW UPDATE ===")
            
            # Show current preview database info for debugging
            print(f"🎨 Current preview index: {self.current_preview_index}")
            if hasattr(self, 'preview_databases') and self.preview_databases:
                current_db = self.preview_databases[self.current_preview_index] if 0 <= self.current_preview_index < len(self.preview_databases) else None
                print(f"🎨 Current preview database: {current_db.name if current_db else 'None'}")
            
            # Get currently selected gradient
            if not hasattr(self, 'gradient_list') or not self.gradient_list.currentItem():
                debug_logger.warning("❌ No gradient list or no current item selected")
                return
                
            gradient_name = self.gradient_list.currentItem().text()
            debug_logger.info(f"🎨 Updating gradient preview for: {gradient_name}")
            
            # Get the current preview database (supports cycling)
            preview_db_path = self.get_current_preview_database()
            debug_logger.info(f"📂 Preview database path: {preview_db_path}")
            debug_logger.info(f"📂 Database exists: {preview_db_path.exists()}")
            print(f"🎨 Preview database path from get_current_preview_database(): {preview_db_path}")
            
            if not preview_db_path.exists():
                debug_logger.error(f"❌ Preview database not found: {preview_db_path}")
                return
            
            # Show which database is being used for the preview
            db_name = preview_db_path.stem
            current_num = self.current_preview_index + 1 if self.preview_databases else 1
            total_num = len(self.preview_databases) if self.preview_databases else 1
            debug_logger.info(f"📊 Using preview database: {db_name} ({current_num} of {total_num})")
            debug_logger.info(f"📊 Total preview databases available: {len(self.preview_databases) if self.preview_databases else 0}")
            
            # Load the preview DEM data
            debug_logger.info("🔧 Loading DEM reader...")
            from dem_reader import DEMReader
            preview_dem = DEMReader(preview_db_path)
            debug_logger.info(f"🔧 DEM reader created: {type(preview_dem)}")
            
            # Load elevation data explicitly
            debug_logger.info("🔧 Loading elevation data...")
            elevation_data = preview_dem.load_elevation_data()
            debug_logger.info(f"🔧 Elevation data loaded: {elevation_data is not None}")
            
            if elevation_data is not None:
                debug_logger.info(f"📐 Elevation data shape: {elevation_data.shape}")
                debug_logger.info(f"📐 Elevation data type: {elevation_data.dtype}")
                debug_logger.info(f"📐 Elevation min: {elevation_data.min()}, max: {elevation_data.max()}")
            else:
                debug_logger.error("❌ Could not load preview DEM data")
                return
            
            # Get the gradient to check its units
            debug_logger.info(f"🔧 Getting gradient: {gradient_name}")
            gradient = self.gradient_manager.get_gradient(gradient_name)
            debug_logger.info(f"🔧 Gradient found: {gradient is not None}")
            
            if not gradient:
                debug_logger.error(f"❌ Gradient '{gradient_name}' not found")
                return
            
            debug_logger.info(f"🎨 Gradient type: {gradient.gradient_type}")
            debug_logger.info(f"🎨 Gradient units: {gradient.units}")
            debug_logger.info(f"🎨 Gradient elevation range: {gradient.min_elevation} - {gradient.max_elevation}")
            
            # Determine elevation range based on gradient units
            debug_logger.info("🔧 Calculating elevation range for preview...")
            min_elevation, max_elevation = self.calculate_elevation_range_for_preview(gradient, elevation_data)
            debug_logger.info(f"📐 Preview elevation range: {min_elevation} - {max_elevation}")
            
            # Generate terrain preview with units-aware elevation range
            debug_logger.info("🎨 Rendering terrain preview...")
            preview_image = self.terrain_renderer.render_terrain(
                elevation_data=elevation_data,
                gradient_name=gradient_name,
                min_elevation=min_elevation,
                max_elevation=max_elevation
            )
            
            debug_logger.info(f"🎨 Terrain rendered: {preview_image is not None}")
            
            if preview_image:
                debug_logger.info(f"🖼️ Preview image type: {type(preview_image)}")
                debug_logger.info(f"🖼️ Preview image size: {preview_image.size}")
                debug_logger.info(f"🖼️ Preview image mode: {preview_image.mode}")
                
                # Convert PIL Image to QImage for display
                from PyQt6.QtGui import QImage, QPixmap
                from PyQt6.QtCore import Qt
                
                debug_logger.info("🔧 Converting PIL to QImage...")
                
                # Convert PIL to QImage
                pil_image = preview_image.convert('RGBA')
                width, height = pil_image.size
                debug_logger.info(f"🖼️ Converted image size: {width}x{height}")
                
                rgba_data = pil_image.tobytes()
                debug_logger.info(f"🖼️ RGBA data length: {len(rgba_data)} bytes")
                
                qimage = QImage(rgba_data, width, height, QImage.Format.Format_RGBA8888)
                debug_logger.info(f"🖼️ QImage created: {qimage.isNull()}")
                debug_logger.info(f"🖼️ QImage size: {qimage.width()}x{qimage.height()}")
                
                # Update preview display
                debug_logger.info("🔧 Updating preview display...")
                self.update_preview_display_qimage(qimage)
                debug_logger.info("✅ Gradient preview updated successfully")
            else:
                debug_logger.error("❌ Failed to generate terrain preview")
                
        except Exception as e:
            debug_logger.error(f"❌ Error updating gradient preview: {e}")
            import traceback
            debug_logger.error(f"❌ Traceback: {traceback.format_exc()}")
            traceback.print_exc()
    
    def calculate_elevation_range_for_preview(self, gradient, elevation_data):
        """
        Calculate elevation range for preview based on radio button selection.
        
        IMPORTANT: Radio buttons now dynamically override gradient type interpretation:
        - "Scale gradient to elevation found in crop area" = Treat gradient as PERCENT type
        - "Scale gradient to Maximum and Minimum elevation" = Treat gradient as METERS type
        
        Args:
            gradient: Original gradient object (type may be overridden by radio buttons)
            elevation_data: 2D numpy array of elevation values in meters
            
        Returns:
            tuple: (min_elevation, max_elevation) in meters for rendering
        """
        import numpy as np
        
        # Check radio button states to determine gradient type override
        scale_to_crop = hasattr(self, 'scale_to_crop_radio') and self.scale_to_crop_radio.isChecked()
        scale_to_max_min = hasattr(self, 'scale_to_max_min_radio') and self.scale_to_max_min_radio.isChecked()
        
        # Determine effective gradient type based on radio button override
        if scale_to_crop:
            effective_gradient_type = "percent"
            print(f"📻 Radio button override: Treating '{gradient.name}' as PERCENT gradient")
        elif scale_to_max_min:
            effective_gradient_type = "meters" 
            print(f"📻 Radio button override: Treating '{gradient.name}' as METERS gradient")
        else:
            # No radio button selected - use original gradient type
            effective_gradient_type = getattr(gradient, 'units', 'meters').lower()
            print(f"📻 No override: Using original gradient type: {effective_gradient_type}")
        
        if effective_gradient_type == "percent":
            # PERCENT MODE: "Scale gradient to elevation found in crop area"
            # Scan database for actual min/max elevation and auto-populate spinboxes
            valid_data = elevation_data[~np.isnan(elevation_data)]
            if len(valid_data) > 0:
                database_min = float(np.min(valid_data))
                database_max = float(np.max(valid_data))
                print(f"📊 Percent mode: Found elevation range {database_min:.0f}m to {database_max:.0f}m")
                
                # SPECIAL CASE: Posterized gradients with "above posterized" colors
                # For these gradients, using data range would eliminate above-range elevations
                # that should display the "above posterized" color. Preserve gradient range.
                is_posterized = gradient.gradient_type in ["posterized", "shading_and_posterized"]
                has_above_color = hasattr(gradient, 'below_gradient_color') and gradient.below_gradient_color
                
                if is_posterized and has_above_color:
                    print(f"🎨 Posterized gradient with above-gradient color detected")
                    print(f"🎨 Using gradient range to preserve above-gradient behavior: {gradient.min_elevation:.0f}m to {gradient.max_elevation:.0f}m")
                    return gradient.min_elevation, gradient.max_elevation
                
                # For preview icon generation, DO NOT update spinboxes
                # Spinboxes should only be updated during main terrain rendering (Preview/Save buttons)
                print(f"📊 Found elevations: {database_min:.0f}-{database_max:.0f}m (preview icon - no spinbox update)")
                
                return database_min, database_max
            else:
                # Fallback if no valid data
                print("⚠️  No valid elevation data found, using gradient defaults")
                return gradient.min_elevation, gradient.max_elevation
                
        else:  # effective_gradient_type == "meters"
            # METERS MODE: "Scale gradient to Maximum and Minimum elevation"  
            # Use values from spinboxes (like original meters gradients)
            if hasattr(self, 'min_elevation') and hasattr(self, 'max_elevation'):
                spinbox_min = float(self.min_elevation.value())
                spinbox_max = float(self.max_elevation.value())
                print(f"📏 Spinbox mode: Using elevation range {spinbox_min:.0f}m to {spinbox_max:.0f}m")
                return spinbox_min, spinbox_max
            else:
                # Fallback if spinboxes not found
                print("⚠️  Spinboxes not found, using gradient defaults")
                return gradient.min_elevation, gradient.max_elevation
    
    def update_preview_display_qimage(self, qimage):
        """Update the preview display with a QImage"""
        try:
            debug_logger.info("🖼️ === UPDATING PREVIEW DISPLAY ===")
            debug_logger.info(f"🖼️ QImage input: {qimage is not None}")
            debug_logger.info(f"🖼️ QImage null: {qimage.isNull() if qimage else 'N/A'}")
            
            # Update the preview label if it exists
            debug_logger.info(f"🔧 Has preview_label attribute: {hasattr(self, 'preview_label')}")
            debug_logger.info(f"🔧 Preview label exists: {hasattr(self, 'preview_label') and self.preview_label is not None}")
            
            if hasattr(self, 'preview_label') and self.preview_label:
                debug_logger.info(f"🔧 Preview label type: {type(self.preview_label)}")
                debug_logger.info(f"🔧 Preview label visible: {self.preview_label.isVisible()}")
                debug_logger.info(f"🔧 Preview label size: {self.preview_label.size()}")
                
                from PyQt6.QtGui import QPixmap
                from PyQt6.QtCore import Qt
                
                debug_logger.info("🔧 Converting QImage to QPixmap...")
                pixmap = QPixmap.fromImage(qimage)
                debug_logger.info(f"🖼️ Pixmap created: {pixmap is not None}")
                debug_logger.info(f"🖼️ Pixmap size: {pixmap.size()}")
                debug_logger.info(f"🖼️ Pixmap null: {pixmap.isNull()}")
                
                # Scale to fit the preview area while maintaining aspect ratio
                if hasattr(self.preview_label, 'size'):
                    label_size = self.preview_label.size()
                    debug_logger.info(f"🖼️ Label size for scaling: {label_size}")
                    
                    scaled_pixmap = pixmap.scaled(
                        label_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    debug_logger.info(f"🖼️ Scaled pixmap size: {scaled_pixmap.size()}")
                    debug_logger.info(f"🖼️ Scaled pixmap null: {scaled_pixmap.isNull()}")
                    
                    debug_logger.info("🔧 Setting pixmap on preview label...")
                    self.preview_label.setPixmap(scaled_pixmap)
                    debug_logger.info("✅ Preview display updated successfully")
                else:
                    # Fallback if size not available
                    debug_logger.info("🔧 Using fallback pixmap setting (no size available)")
                    self.preview_label.setPixmap(pixmap)
                    debug_logger.info("✅ Preview display updated (fallback)")
                    
                # Force repaint/update
                debug_logger.info("🔧 Forcing preview label update...")
                self.preview_label.update()
                self.preview_label.repaint()
                
                # Force immediate processing of UI events to ensure visual update
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()
                
            else:
                debug_logger.error("❌ Preview label not found or not available")
                debug_logger.info("🔧 Attempting to find and setup preview widget...")
                # Try to find preview widget by searching
                self.find_and_setup_preview_widget()
                
        except Exception as e:
            debug_logger.error(f"❌ Error updating preview display: {e}")
            import traceback
            debug_logger.error(f"❌ Traceback: {traceback.format_exc()}")
    
    def find_and_setup_preview_widget(self):
        """Try to find and setup the preview widget if not already found"""
        try:
            from PyQt6.QtWidgets import QLabel
            
            # Search for any QLabel that might be the preview display
            all_labels = self.findChildren(QLabel)
            for label in all_labels:
                label_name = label.objectName()
                # Look for labels with "preview" in the name
                if 'preview' in label_name.lower():
                    print(f"🔍 Found potential preview label: {label_name}")
                    self.preview_label = label
                    return
                    
            print(f"⚠️  No preview label found in UI")
            
        except Exception as e:
            print(f"❌ Error finding preview widget: {e}")

    def _database_exists(self, db_entry):
        """Check if a database entry still exists"""
        path = Path(db_entry['path'])
        return path.exists()

    def show_startup_database_dialog(self):
        """Show the startup database selection dialog"""
        try:
            # Use the static method from StartupDatabaseDialog
            db_type, selected_path = StartupDatabaseDialog.show_database_selection_dialog(self)
            
            if selected_path:
                if db_type == 'single_file':
                    self.load_dem_file(selected_path)
                elif db_type == 'multi_file':
                    self.load_database_folder(selected_path)
                        
        except Exception as e:
            print(f"Error showing startup dialog: {e}")

    # Gradient editor methods
    def open_new_gradient_editor(self):
        """Open the gradient editor for a new gradient with current gradient parameters"""
        try:
            # Get current preview database path for synchronized preview
            current_preview_path = self.get_current_preview_database()
            
            # Store the current gradient position for inserting new gradient below it
            self.new_gradient_insert_position = -1
            if hasattr(self, 'gradient_list') and self.gradient_list.currentItem():
                self.new_gradient_insert_position = self.gradient_list.currentRow()
                current_gradient_name = self.gradient_list.currentItem().text()
                print(f"🔍 Debug - Stored insert position: {self.new_gradient_insert_position} for gradient '{current_gradient_name}'")
            
            # Get current gradient data to populate new gradient fields
            current_gradient_data = None
            if hasattr(self, 'gradient_list') and self.gradient_list.currentItem():
                gradient_name = self.gradient_list.currentItem().text()
                gradient = self.gradient_manager.get_gradient(gradient_name)
                if gradient:
                    # Convert current gradient to dictionary format (same as edit gradient)
                    current_gradient_data = {
                        'name': f'{gradient.name}_copy',  # Add "_copy" suffix for new gradient
                        'description': gradient.description,
                        'min_elevation': int(gradient.min_elevation),  # Convert to int for spin boxes
                        'max_elevation': int(gradient.max_elevation),  # Convert to int for spin boxes
                        'color_stops': [
                            {
                                'position': stop.position,
                                'red': stop.red,
                                'green': stop.green,
                                'blue': stop.blue,
                                'alpha': stop.alpha,
                                'elevation': gradient.max_elevation - stop.position * (gradient.max_elevation - gradient.min_elevation)
                            } for stop in gradient.color_stops
                        ],
                        'discrete': gradient.discrete,
                        'created_by': gradient.created_by,
                        'tags': gradient.tags,
                        'type': gradient.gradient_type,
                        'num_colors': len(gradient.color_stops),
                        'units': gradient.units,
                        'light_direction': int(gradient.light_direction),  # Convert to int for spin boxes
                        'shading_intensity': int(gradient.shading_intensity),  # Convert to int for spin boxes
                        'cast_shadows': gradient.cast_shadows,
                        'shadow_drop_distance': gradient.shadow_drop_distance,
                        'shadow_soft_edge': int(gradient.shadow_soft_edge),  # Convert to int for spin boxes
                        'shadow_color': gradient.shadow_color,
                        'no_data_color': gradient.no_data_color,
                        'below_gradient_color': gradient.below_gradient_color,
                        'blending_mode': gradient.blending_mode,
                        'blending_strength': getattr(gradient, 'blending_strength', 100),  # Add missing blending_strength
                        'color_mode': gradient.color_mode
                    }
            
            # Create a new gradient editor with is_new_gradient=True and current gradient data
            editor = GradientEditorWindow(parent=self, gradient_data=current_gradient_data, is_new_gradient=True, 
                                        preview_database_path=current_preview_path)
            
            # Connect the gradient_saved signal to our save handler
            editor.gradient_saved.connect(self.save_gradient_from_editor)
            
            result = editor.exec()
            
            # If the gradient was saved (OK clicked), refresh the gradient list
            from PyQt6.QtWidgets import QDialog
            if result == QDialog.DialogCode.Accepted:
                # Note: Don't call load_gradients_into_browser() here because save_gradient_from_editor() handles it
                print("✅ New gradient created and gradient list refreshed")
                
            # Clean up the insert position variable (do this after save callback completes)
            if hasattr(self, 'new_gradient_insert_position'):
                delattr(self, 'new_gradient_insert_position')
                
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Could not open gradient editor:\n{str(e)}")

    def open_edit_gradient_editor(self):
        """Open the gradient editor for the selected gradient"""
        try:
            if hasattr(self, 'gradient_list') and self.gradient_list.currentItem():
                gradient_name = self.gradient_list.currentItem().text()
                
                # Get the gradient data from the gradient manager
                gradient = self.gradient_manager.get_gradient(gradient_name)
                if gradient:
                    # Convert gradient object to dictionary format for the editor
                    gradient_data = {
                        'name': gradient.name,
                        'description': gradient.description,
                        'min_elevation': int(gradient.min_elevation),  # Convert to int for spin boxes
                        'max_elevation': int(gradient.max_elevation),  # Convert to int for spin boxes
                        'color_stops': [
                            {
                                'position': stop.position,
                                'red': stop.red,
                                'green': stop.green,
                                'blue': stop.blue,
                                'alpha': stop.alpha,
                                'elevation': gradient.max_elevation - stop.position * (gradient.max_elevation - gradient.min_elevation)
                            } for stop in gradient.color_stops
                        ],
                        'discrete': gradient.discrete,
                        'created_by': gradient.created_by,
                        'tags': gradient.tags,
                        # Add gradient editor specific fields from gradient object
                        'type': gradient.gradient_type,
                        'num_colors': len(gradient.color_stops),
                        'units': gradient.units,
                        'light_direction': int(gradient.light_direction),  # Convert to int for spin boxes
                        'shading_intensity': int(gradient.shading_intensity),  # Convert to int for spin boxes
                        'cast_shadows': gradient.cast_shadows,
                        'shadow_drop_distance': gradient.shadow_drop_distance,
                        'shadow_soft_edge': int(gradient.shadow_soft_edge),  # Convert to int for spin boxes
                        'shadow_color': gradient.shadow_color,
                        'no_data_color': gradient.no_data_color,
                        'below_gradient_color': gradient.below_gradient_color,
                        'blending_mode': gradient.blending_mode,
                        'blending_strength': getattr(gradient, 'blending_strength', 100),  # Add missing blending_strength
                        'color_mode': gradient.color_mode
                    }
                    
                    # Get current preview database path for synchronized preview
                    current_preview_path = self.get_current_preview_database()
                    
                    editor = GradientEditorWindow(parent=self, gradient_data=gradient_data, is_new_gradient=False,
                                                preview_database_path=current_preview_path)
                    
                    # Store the original name and prepare for name change tracking
                    self.last_edited_gradient_name = gradient_name  # This will be updated if name changes
                    
                    # Connect the gradient_saved signal to our save handler with original name
                    editor.gradient_saved.connect(lambda data: self.save_gradient_from_editor(data, original_gradient_name=gradient_name))
                    
                    result = editor.exec()
                    
                    # If the gradient was saved (OK clicked), refresh the gradient list and maintain selection
                    from PyQt6.QtWidgets import QDialog
                    if result == QDialog.DialogCode.Accepted:
                        # Use the potentially updated gradient name
                        final_gradient_name = getattr(self, 'last_edited_gradient_name', gradient_name)
                        self.load_gradients_into_browser(select_gradient_name=final_gradient_name)
                        # Update controls based on the edited gradient
                        self.update_controls_from_gradient(final_gradient_name)
                        print(f"✅ Gradient edited and gradient list refreshed with '{final_gradient_name}' selected")
                else:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Error", f"Could not find gradient '{gradient_name}' in gradient manager")
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "No Selection", "Please select a gradient to edit.")
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Could not open gradient editor:\n{str(e)}")

    def delete_selected_gradient(self):
        """Delete the currently selected gradient"""
        try:
            if hasattr(self, 'gradient_list') and self.gradient_list.currentItem():
                gradient_name = self.gradient_list.currentItem().text()
                
                # Get current selection index for repositioning
                current_row = self.gradient_list.currentRow()
                
                # Remove gradient from manager
                success = self.gradient_manager.remove_gradient(gradient_name)
                
                if success:
                    # Determine which gradient to select after deletion
                    # Get all remaining gradient names
                    remaining_gradients = self.gradient_manager.get_gradient_names()

                    # Determine the gradient to select
                    gradient_to_select = None
                    if remaining_gradients:
                        # If we deleted the last item, select the new last item
                        if current_row >= len(remaining_gradients):
                            gradient_to_select = remaining_gradients[-1]
                        else:
                            # Select the item that took the place of the deleted one
                            gradient_to_select = remaining_gradients[current_row]

                    # Refresh gradient list with proper selection
                    # Note: load_gradients_into_browser already handles setting the selection
                    self.load_gradients_into_browser(select_gradient_name=gradient_to_select)
                    
                    print(f"✅ Gradient '{gradient_name}' deleted successfully")
                else:
                    # Show error message only for actual failures
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(
                        self,
                        "Delete Failed",
                        f"Failed to delete gradient '{gradient_name}'."
                    )
                
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Could not delete gradient:\n{str(e)}")

    def save_gradient_from_editor(self, gradient_data, original_gradient_name=None):
        """Save gradient data from the gradient editor to the gradient manager"""
        try:
            from gradient_system import Gradient, ColorStop
            
            # Convert gradient editor data to gradient system format
            gradient_name = gradient_data.get('name', 'Unnamed Gradient')
            
            # Get the actual color stops from the gradient editor's interactive color ramp
            color_stops = []
            
            # Check if we have color_stops data in the gradient_data (from the interactive color ramp)
            if 'color_stops' in gradient_data and gradient_data['color_stops']:
                for stop_data in gradient_data['color_stops']:
                    color_stop = ColorStop(
                        position=stop_data['position'],
                        red=stop_data['red'],
                        green=stop_data['green'],
                        blue=stop_data['blue'],
                        alpha=stop_data.get('alpha', 255)
                    )
                    color_stops.append(color_stop)
            else:
                # Fallback: create a default gradient if no color stops provided
                print("⚠️  No color stops provided, creating default gradient")
                color_stops = [
                    ColorStop(0.0, 0, 128, 0),      # Dark green at bottom
                    ColorStop(1.0, 255, 255, 255)   # White at top
                ]
            
            # Create the gradient object
            gradient = Gradient(
                name=gradient_name,
                description=f"Created with gradient editor",
                min_elevation=gradient_data.get('min_elevation', 0),
                max_elevation=gradient_data.get('max_elevation', 3000),
                color_stops=color_stops,
                discrete=False,  # TODO: Get from editor
                created_by="Gradient Editor",
                tags=["custom", "user_created"],
                # Special colors and advanced settings
                shadow_color=gradient_data.get('shadow_color'),
                no_data_color=gradient_data.get('no_data_color'),
                below_gradient_color=gradient_data.get('below_gradient_color'),
                gradient_type=gradient_data.get('type', 'gradient'),
                light_direction=gradient_data.get('light_direction', 315),
                shading_intensity=gradient_data.get('shading_intensity', 50),
                cast_shadows=gradient_data.get('cast_shadows', False),
                shadow_drop_distance=gradient_data.get('shadow_drop_distance', 1.0),
                shadow_soft_edge=gradient_data.get('shadow_soft_edge', 3),
                blending_mode=gradient_data.get('blending_mode', 'Multiply'),
                color_mode=gradient_data.get('color_mode', '8-bit'),
                units=gradient_data.get('units', 'meters')
            )
            
            # Handle gradient name changes for edit operations
            if original_gradient_name and original_gradient_name != gradient_name:
                # Name changed: remove old gradient and add new one while preserving position
                print(f"🔄 Gradient name changed from '{original_gradient_name}' to '{gradient_name}'")
                
                # Get the current position of the gradient in the list
                current_gradient_names = self.gradient_manager.get_gradient_names()
                try:
                    original_position = current_gradient_names.index(original_gradient_name)
                    print(f"📍 Original gradient position: {original_position}")
                except ValueError:
                    original_position = -1  # Fallback if not found
                
                # Remove the old gradient
                removed = self.gradient_manager.remove_gradient(original_gradient_name)
                if removed:
                    print(f"✅ Removed old gradient '{original_gradient_name}'")
                
                # Update the last edited gradient name for the main window to use
                self.last_edited_gradient_name = gradient_name
                
                # Add the new gradient
                success = self.gradient_manager.add_gradient(gradient)
                
                # Restore the original position if we successfully added the gradient
                if success and original_position >= 0:
                    # Get the current gradient names after adding the new one
                    updated_gradient_names = self.gradient_manager.get_gradient_names()
                    
                    # Remove the new gradient from its current position (should be at the end)
                    updated_gradient_names.remove(gradient_name)
                    
                    # Insert it back at the original position
                    updated_gradient_names.insert(original_position, gradient_name)
                    
                    # Reorder the gradients to maintain the original position
                    reorder_success = self.gradient_manager.reorder_gradients(updated_gradient_names)
                    if reorder_success:
                        print(f"✅ Restored gradient '{gradient_name}' to original position {original_position}")
                    else:
                        print(f"⚠️ Failed to restore position for gradient '{gradient_name}'")
                
                operation_type = "renamed and updated"
            elif original_gradient_name:
                # Name stayed the same: update existing gradient
                success = self.gradient_manager.add_gradient(gradient)
                operation_type = "updated"
            else:
                # New gradient creation
                success = self.gradient_manager.add_gradient(gradient)
                operation_type = "created"
                
                # Debug: Check insertion variables
                has_position = hasattr(self, 'new_gradient_insert_position')
                position_value = getattr(self, 'new_gradient_insert_position', 'MISSING') if has_position else 'MISSING'
                print(f"🔍 Debug - Insert position: has_attr={has_position}, value={position_value}")
                
                # For new gradients, insert at the position below the previously selected gradient
                if success and hasattr(self, 'new_gradient_insert_position') and self.new_gradient_insert_position >= 0:
                    # Get current gradient names after adding the new one (it's at the end)
                    current_gradient_names = self.gradient_manager.get_gradient_names()
                    
                    # Remove the new gradient from the end
                    current_gradient_names.remove(gradient_name)
                    
                    # Insert it at the desired position (below the previously selected gradient)
                    insert_position = min(self.new_gradient_insert_position + 1, len(current_gradient_names))
                    current_gradient_names.insert(insert_position, gradient_name)
                    
                    # Reorder the gradients
                    reorder_success = self.gradient_manager.reorder_gradients(current_gradient_names)
                    if reorder_success:
                        print(f"✅ Inserted new gradient '{gradient_name}' at position {insert_position} (below previously selected gradient)")
                    else:
                        print(f"⚠️ Failed to reorder gradients, '{gradient_name}' remains at end of list")
            
            if success:
                print(f"✅ Gradient '{gradient_name}' {operation_type} successfully")
                # Update gradient preview with the new gradient - pass gradient name to auto-select it
                self.load_gradients_into_browser(select_gradient_name=gradient_name)
                print(f"✅ New gradient '{gradient_name}' selected and controls updated")
            else:
                print(f"❌ Failed to save gradient '{gradient_name}'")
                
        except Exception as e:
            print(f"❌ Error saving gradient from editor: {e}")
            import traceback
            traceback.print_exc()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to save gradient:\n{str(e)}")

    # Gradient List Management Methods
    def move_gradient_up(self):
        """Move the selected gradient up in the list"""
        try:
            if not hasattr(self, 'gradient_list') or not self.gradient_list:
                return
            
            current_row = self.gradient_list.currentRow()
            if current_row <= 0:  # Already at top or no selection
                return
            
            # Get current gradient name
            current_item = self.gradient_list.currentItem()
            if not current_item:
                return
            
            gradient_name = current_item.text()
            
            # Get all gradient names in current order
            gradient_names = []
            for i in range(self.gradient_list.count()):
                gradient_names.append(self.gradient_list.item(i).text())
            
            # Swap with previous item
            gradient_names[current_row], gradient_names[current_row - 1] = gradient_names[current_row - 1], gradient_names[current_row]
            
            # Update the gradient manager's order
            self.gradient_manager.reorder_gradients(gradient_names)

            # Reload the list and maintain selection
            # Note: load_gradients_into_browser already handles setting the selection
            self.load_gradients_into_browser(select_gradient_name=gradient_name)
            
        except Exception as e:
            print(f"❌ Error moving gradient up: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to move gradient up:\n{str(e)}")

    def move_gradient_down(self):
        """Move the selected gradient down in the list"""
        try:
            if not hasattr(self, 'gradient_list') or not self.gradient_list:
                return
            
            current_row = self.gradient_list.currentRow()
            if current_row < 0 or current_row >= self.gradient_list.count() - 1:  # Already at bottom or no selection
                return
            
            # Get current gradient name
            current_item = self.gradient_list.currentItem()
            if not current_item:
                return
            
            gradient_name = current_item.text()
            
            # Get all gradient names in current order
            gradient_names = []
            for i in range(self.gradient_list.count()):
                gradient_names.append(self.gradient_list.item(i).text())
            
            # Swap with next item
            gradient_names[current_row], gradient_names[current_row + 1] = gradient_names[current_row + 1], gradient_names[current_row]
            
            # Update the gradient manager's order
            self.gradient_manager.reorder_gradients(gradient_names)

            # Reload the list and maintain selection
            # Note: load_gradients_into_browser already handles setting the selection
            self.load_gradients_into_browser(select_gradient_name=gradient_name)
            
        except Exception as e:
            print(f"❌ Error moving gradient down: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to move gradient down:\n{str(e)}")

    def sort_gradients_alphabetically(self):
        """Sort the gradient list alphabetically"""
        try:
            if not hasattr(self, 'gradient_list') or not self.gradient_list:
                return
            
            # Get current selection
            current_item = self.gradient_list.currentItem()
            selected_gradient = current_item.text() if current_item else None
            
            # Get all gradient names
            gradient_names = []
            for i in range(self.gradient_list.count()):
                gradient_names.append(self.gradient_list.item(i).text())
            
            # Sort alphabetically
            gradient_names.sort()
            
            # Update the gradient manager's order
            self.gradient_manager.reorder_gradients(gradient_names)
            
            # Reload the list and maintain selection
            self.load_gradients_into_browser(select_gradient_name=selected_gradient)
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Sort Complete", "Gradient list has been sorted alphabetically.")
            
        except Exception as e:
            print(f"❌ Error sorting gradients: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to sort gradients:\n{str(e)}")

    def save_gradient_list_to_file(self):
        """Save the current gradient list to a file"""
        try:
            from PyQt6.QtWidgets import QFileDialog
            import json
            
            # Get save location
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Gradient List",
                "gradient_list.json",
                "JSON files (*.json);;All files (*)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Get all gradients
            gradients_data = {}
            for gradient_name in self.gradient_manager.get_gradient_names():
                gradient = self.gradient_manager.get_gradient(gradient_name)
                if gradient:
                    gradients_data[gradient_name] = gradient.to_dict()
            
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(gradients_data, f, indent=2)

            self.show_save_complete_dialog("Save Complete", f"Gradient list saved to:\n{file_path}", file_path)
            
        except Exception as e:
            print(f"❌ Error saving gradient list: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to save gradient list:\n{str(e)}")

    def load_gradient_list_from_file(self):
        """Load a gradient list from a file"""
        try:
            from PyQt6.QtWidgets import QFileDialog, QMessageBox
            import json
            
            # Get file to load
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load Gradient List",
                "",
                "JSON files (*.json);;All files (*)"
            )
            
            if not file_path:
                return  # User cancelled
            
            # Load and parse file
            with open(file_path, 'r') as f:
                gradients_data = json.load(f)
            
            # Validate data format
            if not isinstance(gradients_data, dict):
                QMessageBox.warning(self, "Invalid File", "The selected file does not contain valid gradient data.")
                return
            
            # Ask user if they want to replace or append - using custom dialog
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Load Gradient List")
            msg_box.setText("How would you like to load the gradients?")
            msg_box.setInformativeText(
                "• Replace: Replace all current gradients with the loaded ones\n"
                "• Append: Add the loaded gradients to the current list"
            )
            
            # Add custom buttons with proper labels
            replace_button = msg_box.addButton("Replace", QMessageBox.ButtonRole.YesRole)
            append_button = msg_box.addButton("Append", QMessageBox.ButtonRole.NoRole)
            cancel_button = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            
            msg_box.setDefaultButton(replace_button)
            msg_box.exec()
            
            clicked_button = msg_box.clickedButton()
            
            if clicked_button == cancel_button:
                return
            
            replace_mode = clicked_button == replace_button
            
            # Load gradients
            loaded_count = 0
            skipped_count = 0
            
            # Handle different file formats
            # Format 1: Direct gradient data {gradient_name: gradient_data} (from Save List)
            # Format 2: Wrapped format {"gradients": [gradient_list]} (like main gradients.json)
            
            gradients_to_load = {}
            
            if "gradients" in gradients_data and isinstance(gradients_data["gradients"], list):
                # Format 2: Wrapped format like main gradients.json
                print("📁 Loading wrapped format (like main gradients.json)")
                for gradient_data in gradients_data["gradients"]:
                    gradient_name = gradient_data.get("name", "Unknown")
                    gradients_to_load[gradient_name] = gradient_data
            else:
                # Format 1: Direct format from Save List button
                print("📁 Loading direct format (from Save List)")
                gradients_to_load = gradients_data
            
            print(f"📊 Found {len(gradients_to_load)} gradients to load")

            # If replace mode, clear all existing gradients first
            if replace_mode:
                print("🗑️ Replace mode: Clearing all existing gradients")
                self.gradient_manager.gradients.clear()

            for gradient_name, gradient_data in gradients_to_load.items():
                try:
                    # In append mode, check if gradient already exists
                    if not replace_mode and self.gradient_manager.get_gradient(gradient_name):
                        # Skip duplicate in append mode
                        skipped_count += 1
                        continue
                    
                    # Create gradient from data
                    from gradient_system import Gradient, ColorStop
                    
                    color_stops = []
                    for stop_data in gradient_data.get('color_stops', []):
                        color_stop = ColorStop(
                            position=stop_data['position'],
                            red=stop_data['red'],
                            green=stop_data['green'],
                            blue=stop_data['blue'],
                            alpha=stop_data.get('alpha', 255)
                        )
                        color_stops.append(color_stop)
                    
                    gradient = Gradient(
                        name=gradient_name,
                        description=gradient_data.get('description', 'Imported gradient'),
                        min_elevation=gradient_data.get('min_elevation', 0),
                        max_elevation=gradient_data.get('max_elevation', 1000),
                        color_stops=color_stops,
                        discrete=gradient_data.get('discrete', False),
                        created_by=gradient_data.get('created_by', 'Imported'),
                        tags=gradient_data.get('tags', []),
                        # Special colors and advanced settings
                        shadow_color=gradient_data.get('shadow_color', None),
                        no_data_color=gradient_data.get('no_data_color', None),
                        below_gradient_color=gradient_data.get('below_gradient_color', None),
                        gradient_type=gradient_data.get('gradient_type', 'gradient'),
                        light_direction=gradient_data.get('light_direction', 315),
                        shading_intensity=gradient_data.get('shading_intensity', 50),
                        cast_shadows=gradient_data.get('cast_shadows', False),
                        shadow_drop_distance=gradient_data.get('shadow_drop_distance', 1.0),
                        shadow_soft_edge=gradient_data.get('shadow_soft_edge', 3),
                        blending_mode=gradient_data.get('blending_mode', 'Multiply'),
                        color_mode=gradient_data.get('color_mode', '8-bit'),
                        units=gradient_data.get('units', 'meters')
                    )
                    
                    # Add to gradient manager
                    # Both modes can use add_gradient since replace mode already cleared the dict
                    self.gradient_manager.add_gradient(gradient)
                    
                    loaded_count += 1
                    
                except Exception as e:
                    print(f"❌ Error loading gradient '{gradient_name}': {e}")
                    continue
            
            # Save updated gradients
            self.gradient_manager.save_gradients()
            
            # Reload UI
            self.load_gradients_into_browser()
            
            # Show result
            message = f"Successfully loaded {loaded_count} gradients."
            if skipped_count > 0:
                message += f"\nSkipped {skipped_count} duplicate gradients."
            
            QMessageBox.information(self, "Load Complete", message)
            
        except Exception as e:
            print(f"❌ Error loading gradient list: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to load gradient list:\n{str(e)}")

    # Preview and Export methods
    def generate_terrain_preview(self):
        """Generate a terrain preview in the preview window"""
        try:
            # Validate that we have a DEM file or database loaded
            if not self.current_dem_file and not hasattr(self, 'current_database_info'):
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "No Database", 
                                  "Please load a DEM file or database first.")
                return
            
            # Detect if we're working with multi-file database
            is_multi_file_database = (hasattr(self, 'current_database_info') and 
                                     self.current_database_info and 
                                     self.current_database_info.get('type') == 'multi_file')
            
            print(f"🔍 Preview type: {'Multi-file database' if is_multi_file_database else 'Single file'}")
            
            # Get current selection bounds
            try:
                west = float(self.west_edit.text() or 0)
                north = float(self.north_edit.text() or 0)
                east = float(self.east_edit.text() or 0)
                south = float(self.south_edit.text() or 0)
            except ValueError:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Invalid Coordinates", 
                                  "Please enter valid coordinate values.")
                return
            
            # Get current gradient selection
            gradient_name = None
            if hasattr(self, 'gradient_list') and self.gradient_list.currentItem():
                gradient_name = self.gradient_list.currentItem().text()
            
            if not gradient_name:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "No Gradient Selected", 
                                  "Please select a gradient from the gradient list.")
                return
            
            # Close existing preview window if it exists
            if self.preview_window is not None:
                self.preview_window.close()
                self.preview_window = None
            
            # Create new preview window (but don't show it yet)
            self.preview_window = TerrainPreviewWindow(self)
            
            # Connect preview window signals
            self.preview_window.elevation_range_detected.connect(self.handle_elevation_range_detected)
            
            # Don't show the preview window yet - it will be shown when the image is ready
            
            # Handle elevation data loading for single-file vs multi-file databases
            elevation_data = None
            database_path = None
            
            if is_multi_file_database:
                # For multi-file databases, pass the database path for assembly
                database_path = self.current_database_info.get('path')
                print(f"🗂️ Multi-file database path: {database_path}")
                # elevation_data will be None, letting the preview system handle assembly
            else:
                # For single-file databases, load elevation data as before
                
                # First try to use existing dem_reader
                if hasattr(self, 'dem_reader') and self.dem_reader:
                    try:
                        # Check if elevation data is already loaded
                        if self.dem_reader.elevation_data is not None:
                            elevation_data = self.dem_reader.elevation_data
                            print(f"✅ Using existing elevation data: {elevation_data.shape}")
                        else:
                            # Load elevation data
                            print("📖 Loading elevation data from existing dem_reader...")
                            elevation_data = self.dem_reader.load_elevation_data()
                            print(f"✅ Loaded elevation data: {elevation_data.shape}")
                    except Exception as e:
                        print(f"❌ Error loading elevation data from existing dem_reader: {e}")
                
                # If that didn't work, try loading fresh
                if elevation_data is None and self.current_dem_file:
                    try:
                        from dem_reader import DEMReader
                        print(f"📖 Creating fresh DEMReader for {self.current_dem_file}...")
                        temp_reader = DEMReader()
                        if temp_reader.load_dem_file(self.current_dem_file):
                            elevation_data = temp_reader.load_elevation_data()
                            print(f"✅ Fresh elevation data loaded: {elevation_data.shape}")
                        else:
                            print(f"❌ Failed to load DEM file: {self.current_dem_file}")
                    except Exception as e:
                        print(f"❌ Error with fresh DEMReader: {e}")
                        import traceback
                        traceback.print_exc()
                
                # For single-file databases, we must have elevation data
                if elevation_data is None:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "No Elevation Data", 
                                      "Could not load elevation data from the current database.")
                    return
            
            # Get DEM bounds for area cropping
            dem_bounds = None
            if hasattr(self, 'dem_reader') and self.dem_reader and self.dem_reader.bounds:
                bounds_dict = self.dem_reader.bounds
                dem_bounds = (bounds_dict['west'], bounds_dict['north'], bounds_dict['east'], bounds_dict['south'])
                print(f"📍 DEM bounds: {dem_bounds}")
            
            # Get export scale setting
            export_scale = 100.0  # Default
            if hasattr(self, 'export_scale_spinbox'):
                export_scale = self.export_scale_spinbox.value()
            
            print(f"📏 Export scale: {export_scale}%")
            
            # Check radio button state and get elevation range override if needed
            elevation_range_override = None
            scale_to_max_min = hasattr(self, 'scale_to_max_min_radio') and self.scale_to_max_min_radio.isChecked()
            
            if scale_to_max_min and hasattr(self, 'min_elevation') and hasattr(self, 'max_elevation'):
                min_elev = float(self.min_elevation.value())
                max_elev = float(self.max_elevation.value())
                elevation_range_override = (min_elev, max_elev)
                print(f"📏 Using elevation range override from spinboxes: {min_elev}-{max_elev}m")
            else:
                print(f"📊 Will auto-detect elevation range from crop area data")
            
            # Start preview generation
            selection_bounds = (west, north, east, south)
            print(f"🔲 Selection bounds: {selection_bounds}")
            
            self.preview_window.generate_preview(
                elevation_data=elevation_data,
                gradient_name=gradient_name,
                bounds=selection_bounds,
                gradient_manager=self.gradient_manager,
                terrain_renderer=self.terrain_renderer,
                dem_bounds=dem_bounds,
                export_scale=export_scale,
                database_path=database_path,
                dem_reader=getattr(self, 'dem_reader', None),  # Pass dem_reader for chunked processing (None for multi-tile databases)
                elevation_range_override=elevation_range_override  # Pass spinbox values when max/min radio button is active
            )
            
            # Update status
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage("Generating terrain preview...")
            
            print(f"✅ Preview generation started:")
            print(f"   DEM File: {self.current_dem_file}")
            print(f"   Gradient: {gradient_name}")
            print(f"   Bounds: W={west}, N={north}, E={east}, S={south}")
                
        except Exception as e:
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage(f"Preview error: {str(e)}")
            print(f"❌ Preview generation error: {str(e)}")
            import traceback
            traceback.print_exc()

    def export_terrain_file(self):
        """Export the terrain to a file with improved UI integration"""
        try:
            from PyQt6.QtWidgets import QFileDialog, QMessageBox
            from pathlib import Path
            
            # Get selected export type from dropdown
            selected_export_type = "PNG Image"  # Default fallback
            if hasattr(self, 'export_type_combo') and self.export_type_combo:
                selected_export_type = self.export_type_combo.currentText()
                print(f"📋 Selected export type: {selected_export_type}")
            
            # Get the base database name for filename generation
            base_db_name = "terrain_export"
            if hasattr(self, 'current_database_info') and self.current_database_info:
                # Use database info for consistent naming (works for both single-file and multi-file)
                db_path = self.current_database_info.get('path', '')
                
                if db_path:
                    db_name = Path(db_path).name
                    
                    # For single-file databases, the path includes the .dem extension, so use stem
                    if db_name.endswith('.dem') or db_name.endswith('.tif') or db_name.endswith('.tiff'):
                        db_name = Path(db_path).stem
                    
                    # Remove any existing suffixes to get clean base name
                    if db_name.endswith('_crop') or db_name.endswith('_map') or db_name.endswith('_db'):
                        base_db_name = db_name.rsplit('_', 1)[0]
                    else:
                        base_db_name = db_name
            elif hasattr(self, 'current_dem_file') and self.current_dem_file:
                # Fallback to current_dem_file if database info is not available
                db_name = Path(self.current_dem_file).stem
                # Remove any existing suffixes to get clean base name
                if db_name.endswith('_crop') or db_name.endswith('_map') or db_name.endswith('_db'):
                    base_db_name = db_name.rsplit('_', 1)[0]
                else:
                    base_db_name = db_name
            
            # Function to generate filename based on export type
            def get_filename_for_type(export_type_name, extension):
                if export_type_name in ["DEM elevation database", "Geotiff elevation database"]:
                    return f"{base_db_name}_db.{extension}"
                else:
                    return f"{base_db_name}_map.{extension}"
            
            # Define all 7 export types with their file filters in correct order
            # Order matches main window dropdown exactly
            export_types_ordered = [
                ("Geotiff image", "GeoTIFF Image (*.tif)", "tif"),
                ("Geocart image database", "Geocart Image Database (*.gdb)", "gdb"),
                ("JPG image", "JPEG Image (*.jpg *.jpeg)", "jpg"),
                ("PNG image", "PNG Image (*.png)", "png"), 
                ("Photoshop image", "Photoshop Image (*.psd)", "psd"),
                ("DEM elevation database", "DEM Elevation Database (*.dem)", "dem"),
                ("Geotiff elevation database", "GeoTIFF Elevation Database (*.tif)", "tif")
            ]
            
            # Convert to dict for lookup
            export_types = {}
            for dropdown_name, filter_name, ext in export_types_ordered:
                export_types[dropdown_name] = (filter_name, ext)
            
            # Create file filter string with selected type first, then maintain order
            file_filters = []
            selected_filter = None
            selected_extension = None
            
            # Add selected type first
            if selected_export_type in export_types:
                filter_str, ext = export_types[selected_export_type]
                file_filters.append(filter_str)
                selected_filter = filter_str
                selected_extension = ext
            
            # Add remaining types in the correct order
            for dropdown_name, filter_name, ext in export_types_ordered:
                if dropdown_name != selected_export_type:
                    file_filters.append(filter_name)
            
            # Add "All Files" option
            file_filters.append("All Files (*)")
            
            # Join filters with ;; separator
            filter_string = ";;".join(file_filters)
            
            # Set initial default filename with appropriate extension
            initial_filename = get_filename_for_type(selected_export_type, selected_extension or "png")
            
            print(f"📁 Base database name: {base_db_name}")
            print(f"🎯 Initial file path: {initial_filename}")
            print(f"📋 File filters: {filter_string}")
            
            # Use standard QFileDialog - it's the safest approach
            # We'll provide the correct initial filename and let the user handle any changes
            
            from PyQt6.QtWidgets import QFileDialog
            from PyQt6.QtCore import QFileInfo
            
            # Show standard save dialog with correct initial filename
            file_path, chosen_filter = QFileDialog.getSaveFileName(
                self,
                "Export Terrain File",
                initial_filename,
                filter_string,
                selected_filter or file_filters[0]
            )
            
            
            if file_path:
                # Check if selected format is implemented
                print(f"💾 Export file path: {file_path}")
                print(f"🎯 Chosen filter: {chosen_filter}")
                
                # Check for unimplemented formats
                if chosen_filter and "Photoshop" in chosen_filter:
                    QMessageBox.information(
                        self, 
                        "Export Format Not Yet Implemented", 
                        f"Photoshop layered files are planned for future implementation.\n\n"
                        f"Currently supported: PNG, JPEG, GeoTIFF Image, Geocart Image Database, DEM Elevation Database, GeoTIFF Elevation Database\n\n"
                        f"Please select an implemented format for now."
                    )
                    return
                    
                # Check if this is a GeoTIFF export (needs special handling)
                is_geotiff_export = chosen_filter and "GeoTIFF Image" in chosen_filter
                print(f"🌍 GeoTIFF export: {is_geotiff_export}")
                
                # Check if this is a Geocart export (needs special handling)
                is_geocart_export = chosen_filter and "Geocart Image Database" in chosen_filter
                print(f"🗺️ Geocart export: {is_geocart_export}")
                
                # Check if this is an elevation database export (needs special handling)
                is_dem_elevation_export = chosen_filter and "DEM Elevation Database" in chosen_filter
                is_geotiff_elevation_export = chosen_filter and "GeoTIFF Elevation Database" in chosen_filter
                print(f"🏔️ DEM elevation export: {is_dem_elevation_export}")
                print(f"🗻 GeoTIFF elevation export: {is_geotiff_elevation_export}")
                
                # Get current selection bounds (handle both decimal degrees and DMS format)
                try:
                    from coordinate_converter import CoordinateConverter
                    converter = CoordinateConverter()
                    
                    west_text = self.west_edit.text() or "0"
                    north_text = self.north_edit.text() or "0"
                    east_text = self.east_edit.text() or "0"
                    south_text = self.south_edit.text() or "0"
                    
                    print(f"🗺️ Converting coordinates from UI:")
                    print(f"   West: '{west_text}'")
                    print(f"   North: '{north_text}'")
                    print(f"   East: '{east_text}'")
                    print(f"   South: '{south_text}'")
                    
                    # Convert coordinates to decimal degrees
                    west = converter.parse_coordinate(west_text)
                    north = converter.parse_coordinate(north_text)
                    east = converter.parse_coordinate(east_text)
                    south = converter.parse_coordinate(south_text)
                    
                    print(f"✅ Converted to decimal degrees:")
                    print(f"   West: {west:.6f}°")
                    print(f"   North: {north:.6f}°")
                    print(f"   East: {east:.6f}°")
                    print(f"   South: {south:.6f}°")
                    
                except Exception as coord_error:
                    QMessageBox.warning(self, "Coordinate Conversion Error", 
                                      f"Failed to parse coordinates:\n{str(coord_error)}\n\n"
                                      f"Please check coordinate format in the edit fields.")
                    return
                
                # Get current gradient selection
                gradient_name = None
                if hasattr(self, 'gradient_list') and self.gradient_list.currentItem():
                    gradient_name = self.gradient_list.currentItem().text()
                
                if not gradient_name:
                    QMessageBox.warning(self, "No Gradient Selected", 
                                      "Please select a gradient from the gradient list.")
                    return
                
                # Get export scale from UI
                export_scale = 1.0  # Default 100%
                if hasattr(self, 'export_scale_spinbox'):
                    export_scale_percent = self.export_scale_spinbox.value()
                    export_scale = export_scale_percent / 100.0
                    print(f"📏 Export scale read from UI: {export_scale_percent}% (factor: {export_scale})")
                
                # Get elevation range from UI  
                min_elevation = None
                max_elevation = None
                if hasattr(self, 'min_elevation') and hasattr(self, 'max_elevation'):
                    try:
                        min_elevation = float(self.min_elevation.value())
                        max_elevation = float(self.max_elevation.value())
                    except (ValueError, AttributeError):
                        # Use default elevation range from data
                        pass
                
                # Get DPI from UI
                dpi = None
                if hasattr(self, 'resolution_edit'):
                    try:
                        dpi = float(self.resolution_edit.text() or 72)
                    except (ValueError, AttributeError):
                        dpi = 72  # Default DPI
                
                # Determine database type and prepare parameters
                database_info = None
                dem_reader = None
                
                # Check if we have multi-file database
                if (hasattr(self, 'current_database_info') and 
                    self.current_database_info and 
                    self.current_database_info.get('type') == 'multi_file'):
                    database_info = self.current_database_info
                else:
                    # Single-file database - ensure we have elevation data loaded
                    if hasattr(self, 'dem_reader') and self.dem_reader:
                        dem_reader = self.dem_reader
                        # Ensure elevation data is loaded (same logic as preview system)
                        if dem_reader.elevation_data is None:
                            print("📖 Loading elevation data for export...")
                            try:
                                dem_reader.elevation_data = dem_reader.load_elevation_data()
                                print(f"✅ Loaded elevation data: {dem_reader.elevation_data.shape}")
                            except Exception as e:
                                QMessageBox.warning(self, "Data Loading Error", 
                                                  f"Failed to load elevation data:\n{str(e)}")
                                return
                    else:
                        QMessageBox.warning(self, "No Database Loaded", 
                                          "Please load a DEM file or database first.")
                        return
                
                # Handle elevation database exports (raw elevation data, not images)
                if is_dem_elevation_export or is_geotiff_elevation_export:
                    print(f"🏔️ Starting elevation database export...")
                    success = self.export_elevation_database(
                        file_path=file_path,
                        west=west,
                        north=north,
                        east=east,
                        south=south,
                        database_info=database_info,
                        dem_reader=dem_reader,
                        export_scale=export_scale,
                        is_geotiff_elevation=is_geotiff_elevation_export
                    )

                    if success:
                        self.show_save_complete_dialog("Export Complete", f"Elevation database exported to:\n{file_path}", file_path)
                        self.status_bar.showMessage("Elevation database export completed successfully")
                    else:
                        QMessageBox.warning(self, "Export Failed", "Failed to export elevation database.")
                        self.status_bar.showMessage("Elevation database export failed")
                    return
                
                print(f"🌍 Starting image export with:")
                print(f"   Gradient: {gradient_name}")
                print(f"   Scale: {export_scale * 100:.1f}%")
                print(f"   DPI: {dpi:.1f}")
                print(f"   Database type: {'Multi-file' if database_info else 'Single-file'}")
                
                # Use the same pipeline as preview generation for consistency
                success = self.export_using_preview_pipeline(
                    file_path=file_path,
                    west=west,
                    north=north,
                    east=east,
                    south=south,
                    gradient_name=gradient_name,
                    database_info=database_info,
                    dem_reader=dem_reader,
                    export_scale=export_scale,
                    dpi=dpi,
                    is_geotiff=is_geotiff_export,
                    is_geocart=is_geocart_export
                )
                
                if success:
                    QMessageBox.information(self, "Export Complete", f"Terrain exported to:\n{file_path}")
                    self.status_bar.showMessage("Export completed successfully")
                else:
                    QMessageBox.warning(self, "Export Failed", "Failed to export terrain file.")
                    self.status_bar.showMessage("Export failed")
                    
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Export Error", f"Export failed:\n{str(e)}")
            self.status_bar.showMessage(f"Export error: {str(e)}")

    def save_image_file(self):
        """Save terrain as image file with 5 image export options"""
        try:
            from PyQt6.QtWidgets import QFileDialog, QMessageBox
            from pathlib import Path
            
            # Get the base database name for filename generation
            base_db_name = self._get_base_database_name()
            
            # Define image export types
            image_types = [
                ("Geotiff Image", "GeoTIFF Image (*.tif)", "tif"),
                ("Geocart Image Database", "Geocart Image Database (*.gdb)", "gdb"),
                ("JPG Image", "JPEG Image (*.jpg *.jpeg)", "jpg"),
                ("PNG Image", "PNG Image (*.png)", "png"),
                ("Multi-file PNG Layers", "Multi-file PNG Layers (*.png)", "png_layers")
            ]
            
            # Create file filter string
            file_filters = [filter_name for _, filter_name, _ in image_types]
            filter_string = ";;".join(file_filters)
            
            # Set initial default filename with _map suffix
            initial_filename = f"{base_db_name}_map.tif"
            
            print(f"📁 Base database name: {base_db_name}")
            print(f"🎯 Initial file path: {initial_filename}")
            
            # Show save dialog
            file_path, chosen_filter = QFileDialog.getSaveFileName(
                self,
                "Save Image File",
                initial_filename,
                filter_string,
                file_filters[0]  # Default to GeoTIFF
            )
            
            if file_path:
                # Determine export type flags
                is_geotiff_export = chosen_filter and "GeoTIFF Image" in chosen_filter
                is_geocart_export = chosen_filter and "Geocart Image Database" in chosen_filter
                is_multifile_png_export = chosen_filter and "Multi-file PNG Layers" in chosen_filter
                
                print(f"💾 Export file path: {file_path}")
                print(f"🌍 GeoTIFF export: {is_geotiff_export}")
                print(f"🗺️ Geocart export: {is_geocart_export}")
                print(f"🎭 Multi-file PNG export: {is_multifile_png_export}")
                
                # Handle multi-file PNG export separately
                if is_multifile_png_export:
                    success = self._execute_multifile_png_export(file_path)
                else:
                    # Execute the standard single-file export pipeline
                    success = self._execute_terrain_export(
                        file_path=file_path,
                        is_geotiff=is_geotiff_export,
                        is_geocart=is_geocart_export,
                        is_elevation_database=False
                    )
                
                if success:
                    # Check if Key file generation is requested
                    generate_key_file = False
                    if hasattr(self, 'key_file_export_check_box'):
                        generate_key_file = self.key_file_export_check_box.isChecked()
                        print(f"📋 Key file checkbox checked: {generate_key_file}")
                    else:
                        print("⚠️ Key file checkbox not found in UI")
                    
                    key_file_status = ""
                    if generate_key_file:
                        print("🔑 Starting Key file generation...")
                        
                        # Generate Key file
                        key_file_path = create_key_filename(file_path)
                        print(f"🎯 Key file path: {key_file_path}")
                        
                        print("📊 Collecting export data...")
                        export_data = self._collect_export_data_for_key_file(file_path)
                        
                        # Try to get actual image dimensions from the saved file
                        try:
                            from PIL import Image
                            with Image.open(file_path) as img:
                                export_data['pixel_width'] = img.width
                                export_data['pixel_height'] = img.height
                                print(f"📐 Actual image dimensions: {img.width} x {img.height}")
                        except Exception as e:
                            print(f"⚠️ Could not read image dimensions: {e}")
                        print(f"📊 Export data collected: {list(export_data.keys())}")
                        
                        print("🔑 Generating Key file PDF...")
                        if self.key_file_generator.generate_key_file(export_data, key_file_path):
                            key_file_status = f"\nKey file saved to:\n{key_file_path}"
                            print(f"✅ Key file generated successfully: {key_file_path}")
                        else:
                            key_file_status = "\nKey file generation failed."
                            print("❌ Key file generation failed")
                    else:
                        print("ℹ️ Key file generation skipped (checkbox not checked)")

                    self.show_save_complete_dialog("Export Complete", f"Image saved to:\n{file_path}{key_file_status}", file_path)
                    self.status_bar.showMessage("Image export completed successfully")
                else:
                    QMessageBox.warning(self, "Export Failed", "Failed to save image file.")
                    self.status_bar.showMessage("Image export failed")
                    
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Export Error", f"Export failed:\n{str(e)}")
            self.status_bar.showMessage(f"Export error: {str(e)}")

    def _collect_export_data_for_key_file(self, image_path: str) -> dict:
        """Collect all export metadata needed for Key file generation"""
        from pathlib import Path
        
        export_data = {}
        
        # Basic file information
        export_data['filename'] = Path(image_path).name
        
        # Database information
        database_name = 'Unknown Database'
        if hasattr(self, 'current_database_info') and self.current_database_info:
            # Try to get database name from current_database_info
            if 'name' in self.current_database_info:
                database_name = self.current_database_info['name']
            elif 'path' in self.current_database_info:
                # Extract database name from path
                from pathlib import Path
                database_name = Path(self.current_database_info['path']).name
        
        # Also check if we have a current DEM file loaded
        if hasattr(self, 'current_dem_file') and self.current_dem_file:
            from pathlib import Path
            # Extract database name from the DEM file path
            dem_path = Path(self.current_dem_file)
            if 'Gtopo30' in str(dem_path):
                database_name = 'Gtopo30'
            elif 'SRTM' in str(dem_path):
                database_name = 'SRTM'
            else:
                database_name = dem_path.parent.name
        
        export_data['database_name'] = database_name
        print(f"📂 Database name: {database_name}")
        
        # Current gradient information
        current_gradient = None
        if hasattr(self, 'gradient_list') and self.gradient_list.currentItem():
            gradient_name = self.gradient_list.currentItem().text()
            current_gradient = self.gradient_manager.get_gradient(gradient_name)
            print(f"📈 Current gradient: {gradient_name}")
        
        if current_gradient:
            export_data['gradient_name'] = current_gradient.name
            export_data['gradient_type'] = current_gradient.gradient_type
            print(f"📈 Gradient type: {current_gradient.gradient_type}")
        else:
            export_data['gradient_name'] = 'Unknown Gradient'
            export_data['gradient_type'] = 'gradient'
            print("⚠️ No current gradient found")
        
        # Export scale from UI
        if hasattr(self, 'export_scale_spinbox'):
            export_data['export_scale'] = int(self.export_scale_spinbox.value())
            print(f"📊 Export scale: {export_data['export_scale']}%")
        else:
            export_data['export_scale'] = 100
            print("⚠️ Export scale spinbox not found, using default 100%")
        
        # Geographic bounds from coordinate fields
        try:
            if hasattr(self, 'west_edit'):
                export_data['west'] = float(self.west_edit.text() or 0)
            if hasattr(self, 'north_edit'):
                export_data['north'] = float(self.north_edit.text() or 0)
            if hasattr(self, 'east_edit'):
                export_data['east'] = float(self.east_edit.text() or 0)
            if hasattr(self, 'south_edit'):
                export_data['south'] = float(self.south_edit.text() or 0)
            print(f"🌍 Geographic bounds: W={export_data['west']}, N={export_data['north']}, E={export_data['east']}, S={export_data['south']}")
        except (ValueError, AttributeError) as e:
            # Fallback to default bounds if coordinate parsing fails
            export_data.update({
                'west': -180.0, 'north': 90.0, 'east': 180.0, 'south': -90.0
            })
            print(f"⚠️ Geographic bounds parsing failed: {e}, using defaults")
        
        # Elevation range from UI
        try:
            if hasattr(self, 'min_elevation'):
                export_data['min_elevation'] = float(self.min_elevation.value())
            if hasattr(self, 'max_elevation'):
                export_data['max_elevation'] = float(self.max_elevation.value())
            print(f"🏔️ Elevation range: {export_data['min_elevation']} - {export_data['max_elevation']} meters")
        except (ValueError, AttributeError) as e:
            # Use gradient defaults if available
            if current_gradient:
                export_data['min_elevation'] = current_gradient.min_elevation
                export_data['max_elevation'] = current_gradient.max_elevation
                print(f"🏔️ Using gradient elevation range: {export_data['min_elevation']} - {export_data['max_elevation']} meters")
            else:
                export_data['min_elevation'] = 0
                export_data['max_elevation'] = 1000
                print("⚠️ Using default elevation range: 0 - 1000 meters")
        
        # Pixel dimensions - we'll need to calculate these from the export
        # For now, use placeholder values
        export_data['pixel_width'] = 1200
        export_data['pixel_height'] = 800
        print(f"📐 Pixel dimensions: {export_data['pixel_width']} x {export_data['pixel_height']} (placeholder)")
        
        print(f"📋 Export data collection complete with {len(export_data)} fields")
        return export_data

    def show_export_elevation_database_dialog(self):
        """Show export elevation database dialog with 2 database export options"""
        try:
            from PyQt6.QtWidgets import QFileDialog, QMessageBox
            from pathlib import Path
            
            # Get the base database name for filename generation
            base_db_name = self._get_base_database_name()
            
            # Define database export types
            database_types = [
                ("DEM Elevation Database", "DEM Elevation Database (*.dem)", "dem"),
                ("Geotiff Elevation Database", "GeoTIFF Elevation Database (*.tif)", "tif")
            ]
            
            # Create file filter string
            file_filters = [filter_name for _, filter_name, _ in database_types]
            filter_string = ";;".join(file_filters)
            
            # Set initial default filename with _db suffix
            initial_filename = f"{base_db_name}_db.dem"
            
            print(f"📁 Base database name: {base_db_name}")
            print(f"🎯 Initial file path: {initial_filename}")
            
            # Show save dialog
            file_path, chosen_filter = QFileDialog.getSaveFileName(
                self,
                "Export Elevation Database",
                initial_filename,
                filter_string,
                file_filters[1]  # Default to GeoTIFF Elevation
            )
            
            if file_path:
                # Determine export type flags
                is_dem_elevation_export = chosen_filter and "DEM Elevation Database" in chosen_filter
                is_geotiff_elevation_export = chosen_filter and "GeoTIFF Elevation Database" in chosen_filter
                
                print(f"💾 Export file path: {file_path}")
                print(f"🏔️ DEM elevation export: {is_dem_elevation_export}")
                print(f"🗻 GeoTIFF elevation export: {is_geotiff_elevation_export}")
                
                # Execute the export using existing elevation database export pipeline
                success = self._execute_terrain_export(
                    file_path=file_path,
                    is_geotiff=is_geotiff_elevation_export,
                    is_geocart=False,
                    is_elevation_database=True
                )

                if success:
                    self.show_save_complete_dialog("Export Complete", f"Elevation database exported to:\n{file_path}", file_path)
                    self.status_bar.showMessage("Elevation database export completed successfully")
                else:
                    QMessageBox.warning(self, "Export Failed", "Failed to export elevation database.")
                    self.status_bar.showMessage("Elevation database export failed")
                    
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Export Error", f"Export failed:\n{str(e)}")
            self.status_bar.showMessage(f"Export error: {str(e)}")

    def _get_base_database_name(self):
        """Get the base database name for filename generation"""
        base_db_name = "terrain_export"
        if hasattr(self, 'current_database_info') and self.current_database_info:
            # Use database info for consistent naming (works for both single-file and multi-file)
            db_path = self.current_database_info.get('path', '')
            
            if db_path:
                db_name = Path(db_path).name
                
                # For single-file databases, the path includes the .dem extension, so use stem
                if db_name.endswith('.dem') or db_name.endswith('.tif') or db_name.endswith('.tiff'):
                    db_name = Path(db_path).stem
                
                # Remove any existing suffixes to get clean base name
                if db_name.endswith('_crop') or db_name.endswith('_map') or db_name.endswith('_db'):
                    base_db_name = db_name.rsplit('_', 1)[0]
                else:
                    base_db_name = db_name
        elif hasattr(self, 'current_dem_file') and self.current_dem_file:
            # Fallback to current_dem_file if database info is not available
            db_name = Path(self.current_dem_file).stem
            # Remove any existing suffixes to get clean base name
            if db_name.endswith('_crop') or db_name.endswith('_map') or db_name.endswith('_db'):
                base_db_name = db_name.rsplit('_', 1)[0]
            else:
                base_db_name = db_name
        
        return base_db_name

    def _execute_terrain_export(self, file_path, is_geotiff=False, is_geocart=False, is_elevation_database=False):
        """Execute terrain export with the specified parameters"""
        try:
            # Get current selection bounds using coordinate validator
            from coordinate_validator import coordinate_validator
            
            west_text = self.west_edit.text() or "0"
            north_text = self.north_edit.text() or "0"
            east_text = self.east_edit.text() or "0"
            south_text = self.south_edit.text() or "0"
            
            print(f"🗺️ Converting coordinates from UI:")
            print(f"   West: '{west_text}', North: '{north_text}', East: '{east_text}', South: '{south_text}'")
            
            # Convert coordinates to decimal degrees using the correct validator
            west_parsed = coordinate_validator.parse_coordinate_input(west_text)
            north_parsed = coordinate_validator.parse_coordinate_input(north_text)
            east_parsed = coordinate_validator.parse_coordinate_input(east_text)
            south_parsed = coordinate_validator.parse_coordinate_input(south_text)
            
            west = west_parsed if west_parsed is not None else 0
            north = north_parsed if north_parsed is not None else 0
            east = east_parsed if east_parsed is not None else 0
            south = south_parsed if south_parsed is not None else 0
            
            print(f"🗺️ Converted coordinates: West={west}, North={north}, East={east}, South={south}")
            
            # Get gradient and export settings
            gradient_name = None
            if hasattr(self, 'gradient_list') and self.gradient_list.currentItem():
                gradient_name = self.gradient_list.currentItem().text()
            
            if not gradient_name:
                print("⚠️ No gradient selected, using default")
                # Could show an error dialog here instead
                return False
            
            # Get export scale from UI
            export_scale = 1.0  # Default 100%
            if hasattr(self, 'export_scale_spinbox'):
                export_scale_percent = self.export_scale_spinbox.value()
                export_scale = export_scale_percent / 100.0
            
            # Get DPI from UI
            dpi = 72  # Default DPI
            if hasattr(self, 'resolution_edit'):
                try:
                    dpi = float(self.resolution_edit.text() or 72)
                except (ValueError, AttributeError):
                    dpi = 72
            
            print(f"🎨 Gradient: {gradient_name}")
            print(f"📏 Export scale: {export_scale * 100:.1f}%")
            print(f"🖨️ DPI: {dpi}")
            
            # Get database info for both export types
            database_info = None
            if hasattr(self, 'current_database_info') and self.current_database_info:
                database_info = self.current_database_info
            
            # Execute appropriate export pipeline
            if is_elevation_database:
                # Use elevation database export pipeline
                
                success = self.export_elevation_database(
                    file_path=file_path,
                    west=west,
                    north=north,
                    east=east,
                    south=south,
                    database_info=database_info,
                    dem_reader=None,  # Will be determined inside the function
                    export_scale=export_scale,
                    is_geotiff_elevation=is_geotiff
                )
                return success
            else:
                # Use image export pipeline
                success = self.export_using_preview_pipeline(
                    file_path=file_path,
                    west=west,
                    north=north,
                    east=east,
                    south=south,
                    gradient_name=gradient_name,
                    database_info=database_info,
                    dem_reader=None,  # Will be determined inside the function
                    export_scale=export_scale,
                    dpi=dpi,
                    is_geotiff=is_geotiff,
                    is_geocart=is_geocart
                )
                return success
                
        except Exception as e:
            print(f"❌ Export execution error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def handle_elevation_range_detected(self, min_elevation, max_elevation, units):
        """
        Handle elevation range detection from preview generation.
        
        Updates the elevation spin boxes ONLY when "Scale gradient to elevation found in crop area" 
        radio button is selected. This respects the user's choice of elevation determination method.
        
        Args:
            min_elevation: Minimum elevation found in selection area
            max_elevation: Maximum elevation found in selection area  
            units: Database units ("meters")
        """
        try:
            print(f"🎯 Main window received elevation range detection:")
            print(f"   Min elevation: {min_elevation:.1f} {units}")
            print(f"   Max elevation: {max_elevation:.1f} {units}")
            
            # Check if user has selected "Scale gradient to elevation found in crop area"
            scale_to_crop = hasattr(self, 'scale_to_crop_radio') and self.scale_to_crop_radio.isChecked()
            scale_to_max_min = hasattr(self, 'scale_to_max_min_radio') and self.scale_to_max_min_radio.isChecked()
            
            print(f"📻 Radio button state: crop_area={scale_to_crop}, max_min={scale_to_max_min}")
            
            # Only update elevation spin boxes if user chose crop area scaling
            if scale_to_crop and hasattr(self, 'min_elevation') and hasattr(self, 'max_elevation'):
                # Round to reasonable precision for spin boxes
                min_rounded = int(round(min_elevation))
                max_rounded = int(round(max_elevation))
                
                print(f"🔄 Updating elevation controls (crop area mode):")
                print(f"   Min elevation: {min_rounded}")
                print(f"   Max elevation: {max_rounded}")
                
                # Update the spin box values
                self.min_elevation.setValue(min_rounded)
                self.max_elevation.setValue(max_rounded)
                
                # Update units radio buttons (always meters)
                if hasattr(self, 'meters_radio'):
                    self.meters_radio.setChecked(True)
                    print(f"✅ Set units to: Meters")
                
                # Update status bar
                if hasattr(self, 'statusBar'):
                    self.statusBar().showMessage(f"Elevation range detected: {min_rounded} to {max_rounded} {units}")
                
                print(f"✅ Elevation range update complete")
                
            elif scale_to_max_min:
                print(f"📊 Max/Min mode selected - keeping current spinbox values")
                print(f"   Current: {self.min_elevation.value() if hasattr(self, 'min_elevation') else 'N/A'} to {self.max_elevation.value() if hasattr(self, 'max_elevation') else 'N/A'}")
            else:
                print(f"⚠️ No radio button selected or elevation spin boxes not found")
                
        except Exception as e:
            print(f"❌ Error updating elevation ranges: {e}")
            import traceback
            traceback.print_exc()

    def export_using_preview_pipeline(
        self,
        file_path: str,
        west: float,
        north: float,
        east: float,
        south: float,
        gradient_name: str,
        database_info: dict = None,
        dem_reader = None,
        export_scale: float = 1.0,
        dpi: Optional[float] = None,
        is_geotiff: bool = False,
        is_geocart: bool = False
    ) -> bool:
        """
        Export terrain using the same pipeline as preview generation.
        This ensures identical processing and results between preview and export.
        """
        try:
            from preview_window import PreviewGenerationThread, TerrainProgressDialog
            from PIL import Image as PILImage
            
            print("🎨 Using unified preview/export pipeline")
            
            # Debug export parameters
            # Use self.dem_reader if available (for single file databases)
            dem_reader = getattr(self, 'dem_reader', None)
            
            print(f"🔍 Export debug info:")
            print(f"   dem_reader: {dem_reader}")
            print(f"   database_info: {database_info}")
            if dem_reader:
                print(f"   dem_reader.elevation_data: {dem_reader.elevation_data.shape if hasattr(dem_reader, 'elevation_data') and hasattr(dem_reader.elevation_data, 'shape') else dem_reader.elevation_data}")
                print(f"   dem_reader.bounds: {getattr(dem_reader, 'bounds', None)}")
                print(f"   dem_reader.bounds type: {type(getattr(dem_reader, 'bounds', None))}")
                
                # Fix bounds format if needed
                if hasattr(dem_reader, 'bounds') and isinstance(dem_reader.bounds, dict):
                    # Convert dict bounds to tuple format for PreviewGenerationThread
                    bounds_tuple = (
                        dem_reader.bounds['west'],
                        dem_reader.bounds['north'], 
                        dem_reader.bounds['east'],
                        dem_reader.bounds['south']
                    )
                    print(f"   dem_reader.bounds as tuple: {bounds_tuple}")
                elif hasattr(dem_reader, 'bounds'):
                    bounds_tuple = dem_reader.bounds
                    print(f"   dem_reader.bounds already tuple: {bounds_tuple}")
                else:
                    bounds_tuple = None
                    print(f"   dem_reader.bounds: None")
                    
            if database_info:
                print(f"   database_path: {database_info.get('path')}")
            
            # Create progress dialog (same as preview system)
            progress_dialog = TerrainProgressDialog(self)
            progress_dialog.setWindowTitle("Exporting Terrain")
            progress_dialog.show()
            
            # Create a generation thread using the same logic as preview
            # PreviewGenerationThread(elevation_data, gradient_name, bounds, gradient_manager, terrain_renderer, dem_bounds=None, export_scale=100.0, database_path=None)
            
            # Ensure dem_bounds is in proper format
            dem_bounds = None
            if dem_reader and hasattr(dem_reader, 'bounds'):
                if isinstance(dem_reader.bounds, dict):
                    dem_bounds = (
                        dem_reader.bounds['west'],
                        dem_reader.bounds['north'], 
                        dem_reader.bounds['east'],
                        dem_reader.bounds['south']
                    )
                else:
                    dem_bounds = dem_reader.bounds
                print(f"   Using dem_bounds: {dem_bounds}")
            else:
                print(f"   No dem_bounds available")
            
            # Determine data source for assembly system
            # For multi-file databases: use database_path
            # For single files: use elevation_data (don't pass database_path)
            elevation_data_param = None
            database_path_param = None
            
            if database_info and database_info.get('type') == 'multi_file':
                # Multi-file database - use database path for assembly
                database_path_param = database_info.get('path')
                print(f"🗂️ Export using multi-file database: {database_path_param}")
            else:
                # Single file - use elevation data (don't pass database_path)
                elevation_data_param = None
                
                if dem_reader and hasattr(dem_reader, 'elevation_data'):
                    if dem_reader.elevation_data is None:
                        # Load elevation data for export
                        print(f"📖 Loading elevation data for export...")
                        try:
                            dem_reader.elevation_data = dem_reader.load_elevation_data()
                            print(f"✅ Loaded elevation data: {dem_reader.elevation_data.shape}")
                        except Exception as e:
                            print(f"❌ Failed to load elevation data: {e}")
                    
                    elevation_data_param = dem_reader.elevation_data
                
                print(f"🔧 Export using single file elevation data: {elevation_data_param.shape if elevation_data_param is not None else None}")
                
                if elevation_data_param is None:
                    print(f"⚠️ Warning: No elevation data available for single file export")
                    if dem_reader is None:
                        print(f"   - dem_reader is None")
                    elif not hasattr(dem_reader, 'elevation_data'):
                        print(f"   - dem_reader has no elevation_data attribute")
                    elif dem_reader.elevation_data is None:
                        print(f"   - dem_reader.elevation_data is None - failed to load")
            
            # Check radio button state and get elevation range override if needed (same as Preview button)
            elevation_range_override = None
            scale_to_max_min = hasattr(self, 'scale_to_max_min_radio') and self.scale_to_max_min_radio.isChecked()
            
            if scale_to_max_min and hasattr(self, 'min_elevation') and hasattr(self, 'max_elevation'):
                min_elev = float(self.min_elevation.value())
                max_elev = float(self.max_elevation.value())
                elevation_range_override = (min_elev, max_elev)
                print(f"📏 Export using elevation range override from spinboxes: {min_elev}-{max_elev}m")
            else:
                print(f"📊 Export will auto-detect elevation range from crop area data")
            
            export_thread = PreviewGenerationThread(
                elevation_data=elevation_data_param,
                gradient_name=gradient_name,
                bounds=(west, north, east, south),
                gradient_manager=self.gradient_manager,
                terrain_renderer=self.terrain_renderer,
                dem_bounds=dem_bounds,
                export_scale=export_scale * 100.0,  # Convert to percentage
                database_path=database_path_param,
                dem_reader=dem_reader,  # Pass dem_reader for chunked processing
                elevation_range_override=elevation_range_override  # Pass spinbox values when max/min radio button is active
            )
            
            # Track export result using proper event-driven approach
            self._export_result = {'success': False, 'error': None, 'image': None, 'completed': False}
            self._export_progress_dialog = progress_dialog
            
            def handle_progress(percentage, phase):
                if hasattr(self, '_export_progress_dialog') and self._export_progress_dialog:
                    self._export_progress_dialog.update_progress(percentage, phase)
                
            def handle_export_ready(pil_image):
                if hasattr(self, '_export_result') and self._export_result:
                    self._export_result['image'] = pil_image
                    self._export_result['success'] = True
                    self._export_result['completed'] = True
                if hasattr(self, '_export_progress_dialog') and self._export_progress_dialog:
                    self._export_progress_dialog.close()
                
            def handle_export_error(error_message):
                if hasattr(self, '_export_result') and self._export_result:
                    self._export_result['error'] = error_message
                    self._export_result['completed'] = True
                if hasattr(self, '_export_progress_dialog') and self._export_progress_dialog:
                    self._export_progress_dialog.close()
                
            def handle_export_finished():
                if hasattr(self, '_export_result') and self._export_result:
                    self._export_result['completed'] = True
                
            # Connect thread signals
            export_thread.progress_updated.connect(handle_progress)
            export_thread.preview_ready.connect(handle_export_ready)
            export_thread.error_occurred.connect(handle_export_error)
            export_thread.finished.connect(handle_export_finished)
            export_thread.elevation_range_detected.connect(self.handle_elevation_range_detected)
            
            # Start the thread
            export_thread.start()
            
            # Process events until thread completes (proper event-driven approach)
            from PyQt6.QtWidgets import QApplication
            while not self._export_result['completed']:
                QApplication.processEvents()
                # Note: TerrainProgressDialog doesn't have cancel button, so no cancellation check needed
                    
            # Wait for thread to finish properly
            if export_thread.isRunning():
                export_thread.wait(5000)  # Wait up to 5 seconds
            
            # Check for errors
            if self._export_result['error']:
                print(f"❌ Export error: {self._export_result['error']}")
                return False
                
            if not self._export_result['success'] or not self._export_result['image']:
                print("❌ Export failed - no image generated")
                return False
                
            generated_image = self._export_result['image']
                
            # Save the generated image to file
            print(f"💾 Saving exported image to: {file_path}")
            
            # Convert RGBA to RGB with white background if needed
            if generated_image.mode == 'RGBA':
                rgb_image = PILImage.new('RGB', generated_image.size, (255, 255, 255))
                rgb_image.paste(generated_image, mask=generated_image.split()[3])
                generated_image = rgb_image
                
            # Handle GeoTIFF export with geographic metadata
            if is_geotiff:
                print("🌍 Saving as GeoTIFF with geographic metadata...")
                success = self._save_geotiff_image(
                    generated_image, file_path, west, north, east, south, 
                    database_info, dem_reader, dpi
                )
                if not success:
                    print("⚠️ GeoTIFF save failed, falling back to regular TIFF")
                    # Fall through to regular image save
                else:
                    print("✅ GeoTIFF saved successfully")
                    return True
                    
            # Handle Geocart image database export with geographic header
            if is_geocart:
                print("🗺️ Saving as Geocart Image Database with geographic header...")
                success = self._save_geocart_image(
                    generated_image, file_path, west, north, east, south
                )
                if not success:
                    print("⚠️ Geocart save failed, falling back to regular image")
                    # Fall through to regular image save
                else:
                    print("✅ Geocart Image Database saved successfully")
                    return True
            
            # Regular image save (PNG, JPEG, or fallback TIFF)
            format_lower = Path(file_path).suffix.lower()
            if format_lower == '.png':
                save_format = 'PNG'
            elif format_lower in ['.jpg', '.jpeg']:
                save_format = 'JPEG'
            elif format_lower in ['.tif', '.tiff']:
                save_format = 'TIFF'
            else:
                save_format = 'PNG'  # Default fallback
                
            # Save with DPI if specified
            save_kwargs = {'format': save_format}
            if dpi:
                save_kwargs['dpi'] = (dpi, dpi)
                print(f"📐 Saving with DPI: {dpi}")
                
            generated_image.save(file_path, **save_kwargs)
            
            # Clean up
            if hasattr(self, '_export_result'):
                delattr(self, '_export_result')
            if hasattr(self, '_export_progress_dialog'):
                delattr(self, '_export_progress_dialog')
            
            print("✅ Export using preview pipeline completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Export using preview pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Clean up on error
            if hasattr(self, '_export_result'):
                delattr(self, '_export_result')
            if hasattr(self, '_export_progress_dialog'):
                delattr(self, '_export_progress_dialog')
            
            return False

    def _save_geotiff_image(self, pil_image, file_path, west, north, east, south, 
                           database_info=None, dem_reader=None, dpi=None):
        """
        Save PIL image as GeoTIFF with proper geographic metadata and resolution
        
        Args:
            pil_image: PIL Image to save
            file_path: Output file path
            west, north, east, south: Geographic bounds of the image
            database_info: Multi-file database info (for projection)
            dem_reader: Single-file DEM reader (for projection) 
            dpi: Dots per inch for image resolution
            
        Returns:
            bool: True if successful, False if failed
        """
        try:
            print("🌍 Starting GeoTIFF creation with optimized PIL+rasterio approach...")
            
            # Try to import required libraries
            try:
                import rasterio
                from rasterio.transform import from_bounds
                from rasterio.crs import CRS
                import numpy as np
            except ImportError as e:
                print(f"❌ Required libraries not available: {e}")
                print(f"🔄 Falling back to regular TIFF export...")
                # Fallback to regular TIFF
                pil_image.save(file_path, format='TIFF', compression='lzw', dpi=(dpi, dpi) if dpi else None)
                print(f"✅ Regular TIFF saved: {file_path}")
                return True
            
            print(f"📐 Image dimensions: {pil_image.size}")
            print(f"🗺️ Original bounds: W={west:.6f}, N={north:.6f}, E={east:.6f}, S={south:.6f}")
            
            # Check for meridian crossing to determine coordinate handling
            longitude_span = calculate_longitude_span(west, east)
            
            if longitude_span.crosses_meridian:
                # For meridian-crossing selections, DO NOT normalize coordinates
                # as this breaks the spatial relationship in GeoTIFF transforms
                print(f"🌍 Meridian crossing detected - preserving original coordinates")
                print(f"📏 Longitude span: {longitude_span.width_degrees:.2f}° (crosses antimeridian)")
                geotiff_west = west
                geotiff_east = east
            else:
                # For normal selections, normalize to [-180°, 180°] range for GeoTIFF compatibility
                geotiff_west = normalize_longitude(west)
                geotiff_east = normalize_longitude(east)
                
                # Log longitude normalization if values changed
                if geotiff_west != west:
                    print(f"📍 Normalized west longitude: {west:.6f}° → {geotiff_west:.6f}°")
                if geotiff_east != east:
                    print(f"📍 Normalized east longitude: {east:.6f}° → {geotiff_east:.6f}°")
            
            print(f"🗺️ GeoTIFF bounds: W={geotiff_west:.6f}, N={north:.6f}, E={geotiff_east:.6f}, S={south:.6f}")
            if dpi:
                print(f"📏 Target resolution: {dpi} DPI")
            
            # Convert PIL image to numpy array for rasterio
            width, height = pil_image.size
            if pil_image.mode == 'RGBA':
                image_array = np.array(pil_image)
                image_array = np.transpose(image_array, (2, 0, 1))  # (H,W,C) to (C,H,W)
                bands = 4
            elif pil_image.mode == 'RGB':
                image_array = np.array(pil_image)
                image_array = np.transpose(image_array, (2, 0, 1))  # (H,W,C) to (C,H,W)
                bands = 3
            else:
                # Convert to RGB if other mode
                pil_image = pil_image.convert('RGB')
                image_array = np.array(pil_image)
                image_array = np.transpose(image_array, (2, 0, 1))
                bands = 3
            
            # Create transform from proper bounds (normalized for normal, original for meridian-crossing)
            transform = from_bounds(geotiff_west, south, geotiff_east, north, width, height)
            
            # Use WGS84 (EPSG:4326) as the default CRS
            crs = CRS.from_epsg(4326)
            
            # Create GeoTIFF with proper georeferencing
            with rasterio.open(
                file_path,
                'w',
                driver='GTiff',
                height=height,
                width=width,
                count=bands,
                dtype=image_array.dtype,
                crs=crs,
                transform=transform,
                compress='lzw'
            ) as dst:
                dst.write(image_array)
                
                # Add DPI information as tags if specified
                if dpi:
                    # Add resolution tags
                    dst.update_tags(
                        TIFFTAG_XRESOLUTION=dpi,
                        TIFFTAG_YRESOLUTION=dpi,
                        TIFFTAG_RESOLUTIONUNIT=2  # 2 = inches
                    )
                    print(f"📐 Added DPI tags: {dpi} DPI")
            
            print(f"🗺️ Coordinate system: WGS84 (EPSG:4326)")
            if longitude_span.crosses_meridian:
                print(f"📐 Geographic extent preserved with original coordinates (meridian crossing)")
            else:
                print(f"📐 Geographic extent preserved with normalized longitude bounds")
            
            print(f"✅ GeoTIFF saved successfully: {file_path}")
            if dpi:
                print(f"📐 Resolution preserved: {dpi} DPI (readable by Photoshop and GIS software)")
            return True
            
        except Exception as e:
            print(f"❌ Error saving GeoTIFF: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _save_geocart_image(self, pil_image, file_path, west, north, east, south):
        """
        Save PIL image as Geocart Image Database with proper geographic header
        
        Args:
            pil_image: PIL Image to save
            file_path: Output file path
            west, north, east, south: Geographic bounds of the image
            
        Returns:
            bool: True if successful, False if failed
        """
        try:
            print("🗺️ Starting Geocart Image Database creation...")
            import struct
            
            # Convert PIL image to RGB (no alpha channel for Geocart)
            if pil_image.mode != 'RGB':
                rgb_image = pil_image.convert('RGB')
            else:
                rgb_image = pil_image
            
            width, height = rgb_image.size
            print(f"📐 Image dimensions: {width} x {height}")
            print(f"🗺️ Geographic bounds: W={west:.6f}, N={north:.6f}, E={east:.6f}, S={south:.6f}")
            
            # Ensure file has .gdb extension
            if not file_path.lower().endswith('.gdb'):
                file_path = file_path + '.gdb'
                print(f"📁 Adding .gdb extension: {file_path}")
            
            # Create Geocart MapRecord header (128 bytes total)
            with open(file_path, 'wb') as f:
                # 1. Type signature (4 bytes): "GeoR"
                f.write(b'GeoR')
                
                # 2. Version (2 bytes): 0 (big-endian)
                f.write(struct.pack('>H', 0))
                
                # 3. Content (2 bytes): 0 (big-endian)
                f.write(struct.pack('>H', 0))
                
                # 4. Geographic boundaries (8 bytes each, big-endian IEEE 754 double)
                # Normalize longitude boundaries to [-180°, 180°] range for Geocart compatibility
                normalized_west = normalize_longitude(west)
                normalized_east = normalize_longitude(east)
                
                # Log longitude normalization if values changed
                if normalized_west != west:
                    print(f"📍 Normalized west longitude: {west:.6f}° → {normalized_west:.6f}°")
                if normalized_east != east:
                    print(f"📍 Normalized east longitude: {east:.6f}° → {normalized_east:.6f}°")
                
                f.write(struct.pack('>d', normalized_west))    # West longitude
                f.write(struct.pack('>d', north))              # North latitude
                f.write(struct.pack('>d', normalized_east))    # East longitude  
                f.write(struct.pack('>d', south))              # South latitude
                
                # 5. Image dimensions (4 bytes each, big-endian)
                f.write(struct.pack('>L', width))   # PixX
                f.write(struct.pack('>L', height))  # PixY
                
                # 6. Padding (80 bytes) - filled with zeros
                f.write(b'\x00' * 80)
                
                # Verify header is exactly 128 bytes
                header_size = f.tell()
                if header_size != 128:
                    print(f"❌ Error: Header size is {header_size}, expected 128 bytes")
                    return False
                
                print(f"✅ Geocart header written (128 bytes)")
                print(f"   Type: GeoR")
                print(f"   Version: 0")
                print(f"   West: {west:.6f}")
                print(f"   North: {north:.6f}")
                print(f"   East: {east:.6f}")
                print(f"   South: {south:.6f}")
                print(f"   Dimensions: {width} x {height}")
                
                # 7. Write raw RGB image data
                # Geocart expects raw RGB bytes (no compression, no additional headers)
                image_bytes = rgb_image.tobytes()
                f.write(image_bytes)
                
                image_data_size = len(image_bytes)
                print(f"✅ Image data written ({image_data_size:,} bytes)")
                
                # Verify expected file size
                expected_size = 128 + (width * height * 3)  # header + RGB pixels
                actual_size = f.tell()
                
                if actual_size == expected_size:
                    print(f"✅ File size correct: {actual_size:,} bytes")
                else:
                    print(f"⚠️ File size mismatch: got {actual_size:,}, expected {expected_size:,}")
            
            print(f"✅ Geocart Image Database saved successfully: {file_path}")
            print(f"🎯 File can be opened in Geocart for map projection")
            print(f"🎯 File contains raw RGB data with 128-byte geographic header")
            return True
            
        except Exception as e:
            print(f"❌ Error saving Geocart Image Database: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _execute_multifile_png_export(self, file_path: str) -> bool:
        """
        Execute multi-file PNG layer export
        
        Args:
            file_path: Base file path (will be modified for each layer)
            
        Returns:
            bool: True if successful, False if failed
        """
        try:
            from pathlib import Path
            from PIL import Image
            import numpy as np
            
            print("🎭 Starting multi-file PNG layer export...")
            
            # Validate terrain renderer is available
            if not hasattr(self, 'terrain_renderer') or not self.terrain_renderer:
                print("❌ Terrain renderer not available")
                return False
            
            # Get export parameters using existing coordinate logic
            from coordinate_validator import coordinate_validator
            
            # Parse coordinates from UI
            west_text = self.west_edit.text() or "0"
            north_text = self.north_edit.text() or "0"
            east_text = self.east_edit.text() or "0"
            south_text = self.south_edit.text() or "0"
            
            west = coordinate_validator.parse_coordinate_input(west_text) or 0
            north = coordinate_validator.parse_coordinate_input(north_text) or 0
            east = coordinate_validator.parse_coordinate_input(east_text) or 0
            south = coordinate_validator.parse_coordinate_input(south_text) or 0
            
            # Get gradient name
            gradient_name = None
            if hasattr(self, 'gradient_list') and self.gradient_list.currentItem():
                gradient_name = self.gradient_list.currentItem().text()
            
            # Get elevation range from UI spinboxes (use correct attribute names)
            min_elevation = None
            max_elevation = None
            if hasattr(self, 'min_elevation'):
                min_elevation = float(self.min_elevation.value())
            if hasattr(self, 'max_elevation'):
                max_elevation = float(self.max_elevation.value())
            
            # Load elevation data using the same system as regular exports
            # Get current database information
            dem_reader = getattr(self, 'dem_reader', None)
            database_info = getattr(self, 'current_database_info', None)
            
            print(f"🔍 Multi-file export debug info:")
            print(f"   dem_reader: {dem_reader}")
            print(f"   database_info: {database_info}")
            
            # Use the multi-file database to get elevation data for the selection
            if database_info and database_info.get('type') == 'multi_file':
                # Multi-file database case
                print(f"📁 Loading elevation data from multi-file database...")
                
                try:
                    # Import and create the MultiFileDatabase
                    from multi_file_database import MultiFileDatabase
                    
                    db_path = database_info.get('path')
                    if not db_path:
                        print("❌ No database path available")
                        return False
                    
                    # Load database and assemble tiles for bounds
                    database = MultiFileDatabase(db_path)
                    if not database.tiles:
                        print(f"❌ No tiles found in database: {db_path}")
                        return False
                    
                    print(f"🗂️ Database: {len(database.tiles)} tiles, type: {database.database_type}")
                    
                    # Get elevation data using the database's assembly method
                    elevation_data = database.assemble_tiles_for_bounds(west, north, east, south)
                    
                    if elevation_data is None:
                        print("❌ Failed to load elevation data from multi-file database")
                        return False
                        
                    print(f"✅ Loaded elevation data: {elevation_data.shape}")
                    
                except Exception as e:
                    print(f"❌ Error loading multi-file database: {e}")
                    return False
                
            elif dem_reader and hasattr(dem_reader, 'get_elevation_subset'):
                # Single-file database case  
                print(f"📁 Loading elevation data from single-file database...")
                
                try:
                    elevation_data = dem_reader.get_elevation_subset(west, north, east, south)
                    if elevation_data is None:
                        print("❌ Failed to get elevation subset from DEM reader")
                        return False
                    print(f"✅ Loaded elevation data: {elevation_data.shape}")
                except Exception as e:
                    print(f"❌ Error getting elevation subset: {e}")
                    return False
                    
            else:
                print("❌ No valid data source available (no dem_reader or database_info)")
                return False
            
            if not gradient_name:
                print("❌ No gradient selected")
                return False
            
            print(f"🎨 Rendering layers for gradient: {gradient_name}")
            print(f"📐 Export bounds: W={west:.6f}, N={north:.6f}, E={east:.6f}, S={south:.6f}")
            
            # Get the correct elevation range based on gradient type (same logic as preview system)
            gradient = self.gradient_manager.get_gradient(gradient_name)
            if gradient:
                # Use the same elevation calculation logic as preview generation
                calculated_min, calculated_max = self.calculate_elevation_range_for_preview(gradient, elevation_data)
                print(f"📏 Calculated elevation range for export: {calculated_min:.1f}m to {calculated_max:.1f}m")
                
                # Use calculated values instead of spinbox values
                export_min_elevation = calculated_min
                export_max_elevation = calculated_max
            else:
                # Fallback to spinbox values if gradient not found
                print(f"⚠️ Gradient not found, using spinbox values: {min_elevation:.1f}m to {max_elevation:.1f}m")
                export_min_elevation = min_elevation
                export_max_elevation = max_elevation
            
            # Generate all layers using terrain renderer
            layers = self.terrain_renderer.render_terrain_layers(
                elevation_data=elevation_data,
                gradient_name=gradient_name,
                min_elevation=export_min_elevation,
                max_elevation=export_max_elevation,
                no_data_color=None  # Use transparent for no-data
            )
            
            # Prepare filenames
            base_path = Path(file_path)
            base_name = base_path.stem
            base_dir = base_path.parent
            
            # Define layer exports (ordered from bottom to top in Photoshop)
            layer_exports = [
                ('elevation', 'elevation_base', "Normalized Elevation (Grayscale)"),
                ('gradient', 'color', "Gradient Colors"),
                ('shading', 'hillshade', "Hillshading"),
                ('shadows', 'shadows', "Cast Shadows"),
                ('composite', 'composite', "Final Composite")
            ]
            
            exported_files = []
            
            # Export each layer as PNG
            for layer_key, suffix, description in layer_exports:
                if layer_key in layers and layers[layer_key] is not None:
                    layer_filename = f"{base_name}_{suffix}.png"
                    layer_path = base_dir / layer_filename
                    
                    print(f"💾 Exporting {description}: {layer_filename}")
                    
                    # Convert numpy array to PIL Image
                    layer_data = layers[layer_key]
                    
                    if layer_data.ndim == 2:
                        # Grayscale layer (shading, shadows) - convert to RGBA
                        if layer_key == 'shadows':
                            # Shadow layer: create white base with shadow transparency
                            height, width = layer_data.shape
                            shadow_rgba = np.full((height, width, 4), 255, dtype=np.uint8)
                            
                            # Get shadow color from gradient
                            gradient = layers['gradient_obj']
                            shadow_rgb = (128, 128, 128)  # Default gray
                            
                            if hasattr(gradient, 'shadow_color') and gradient.shadow_color:
                                shadow_color = gradient.shadow_color
                                print(f"🎨 Processing shadow color: {shadow_color} (type: {type(shadow_color)})")
                                
                                # Handle different shadow color formats
                                if isinstance(shadow_color, (tuple, list)) and len(shadow_color) >= 3:
                                    shadow_rgb = tuple(int(x) for x in shadow_color[:3])
                                    print(f"🎨 Tuple/list format: {shadow_rgb}")
                                elif isinstance(shadow_color, dict):
                                    # Handle dictionary format like {'red': 70, 'green': 157, 'blue': 247, 'alpha': 255}
                                    print(f"🎨 Parsing color dictionary: {shadow_color}")
                                    try:
                                        red = shadow_color.get('red', 128)
                                        green = shadow_color.get('green', 128)
                                        blue = shadow_color.get('blue', 128)
                                        shadow_rgb = (int(red), int(green), int(blue))
                                        print(f"🎨 Dictionary to RGB: {shadow_rgb}")
                                    except Exception as e:
                                        print(f"🎨 Exception parsing dictionary: {e}")
                                        shadow_rgb = (128, 128, 128)
                                elif isinstance(shadow_color, str):
                                    # Handle color name strings like 'red', 'blue', etc.
                                    print(f"🎨 Parsing color string: '{shadow_color}'")
                                    try:
                                        from PyQt6.QtGui import QColor
                                        q_color = QColor(shadow_color)
                                        if q_color.isValid():
                                            shadow_rgb = (q_color.red(), q_color.green(), q_color.blue())
                                            print(f"🎨 Parsed to RGB: {shadow_rgb}")
                                        else:
                                            print(f"🎨 Invalid color name, using default gray")
                                            shadow_rgb = (128, 128, 128)
                                    except Exception as e:
                                        print(f"🎨 Exception parsing color: {e}")
                                        shadow_rgb = (128, 128, 128)
                                else:
                                    # Try to convert any other format to RGB
                                    try:
                                        if hasattr(shadow_color, '__iter__') and not isinstance(shadow_color, str):
                                            shadow_list = list(shadow_color)
                                            if len(shadow_list) >= 3:
                                                shadow_rgb = tuple(int(x) for x in shadow_list[:3])
                                                print(f"🎨 Iterable format: {shadow_rgb}")
                                            else:
                                                print(f"🎨 Iterable too short, using default gray")
                                        else:
                                            print(f"🎨 Unknown format, using default gray")
                                    except Exception as e:
                                        print(f"🎨 Exception converting format: {e}")
                                        shadow_rgb = (128, 128, 128)
                            else:
                                print(f"🎨 No shadow color found, using default gray")
                            
                            # Ensure shadow_rgb is always a tuple of integers
                            try:
                                shadow_rgb = tuple(int(x) for x in shadow_rgb)
                                print(f"🎨 Final shadow RGB: {shadow_rgb}")
                            except:
                                shadow_rgb = (128, 128, 128)
                                print(f"🎨 Final fallback to default gray: {shadow_rgb}")
                            
                            # Shadow layer values: 0 = no shadow, higher values = more shadow
                            # Use shadow values directly as alpha (shadow intensity)
                            shadow_alpha = layer_data  # Use directly: 0 = transparent, 255 = opaque shadow
                            
                            # Set RGB to shadow color everywhere
                            shadow_rgba[..., 0] = shadow_rgb[0]
                            shadow_rgba[..., 1] = shadow_rgb[1]
                            shadow_rgba[..., 2] = shadow_rgb[2]
                            
                            # Set alpha channel to shadow intensity
                            shadow_rgba[..., 3] = shadow_alpha
                            
                            print(f"🎨 Shadow layer: color=RGB{shadow_rgb}, alpha range={shadow_alpha.min()}-{shadow_alpha.max()}")
                            
                            pil_image = Image.fromarray(shadow_rgba, mode='RGBA')
                        else:
                            # Hillshading: convert to grayscale PNG
                            pil_image = Image.fromarray(layer_data, mode='L')
                    else:
                        # RGBA layer (elevation, gradient, composite)
                        pil_image = Image.fromarray(layer_data, mode='RGBA')
                    
                    # Save PNG with maximum quality
                    pil_image.save(str(layer_path), format='PNG', optimize=False)
                    
                    exported_files.append(str(layer_path))
                    print(f"✅ Saved: {layer_filename} ({pil_image.size})")
                else:
                    print(f"⏭️ Skipping {description} (not available for this gradient)")
            
            # Create info file with layer descriptions
            info_filename = f"{base_name}_layer_info.txt"
            info_path = base_dir / info_filename
            
            with open(info_path, 'w') as f:
                f.write("Multi-file PNG Layer Export\n")
                f.write("="*40 + "\n\n")
                f.write(f"Export Date: {self._get_current_timestamp()}\n")
                f.write(f"Gradient: {gradient_name}\n")
                f.write(f"Geographic Bounds: W={west:.6f}, N={north:.6f}, E={east:.6f}, S={south:.6f}\n")
                f.write(f"Elevation Range: {export_min_elevation:.1f}m to {export_max_elevation:.1f}m\n\n")
                f.write("Layer Files (bottom to top for Photoshop):\n")
                f.write("-" * 50 + "\n")
                
                for i, (layer_key, suffix, description) in enumerate(layer_exports, 1):
                    layer_filename = f"{base_name}_{suffix}.png"
                    if layer_filename in [Path(f).name for f in exported_files]:
                        f.write(f"{i}. {layer_filename} - {description}\n")
                
                f.write("\nUsage Instructions:\n")
                f.write("1. Open Photoshop\n")
                f.write("2. Drag layer files into Photoshop in order (bottom to top)\n")
                f.write("3. Set blend modes: Hillshade=Hard Light, Shadows=Multiply\n")
                f.write("4. Adjust layer opacity as needed\n")
            
            exported_files.append(str(info_path))
            
            print(f"\n✅ Multi-file PNG export complete!")
            print(f"📁 Exported {len(exported_files)} files:")
            for file_path in exported_files:
                print(f"   - {Path(file_path).name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Multi-file PNG export failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _get_current_timestamp(self) -> str:
        """Get current timestamp string for export metadata"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def export_elevation_database(
        self,
        file_path: str,
        west: float,
        north: float,
        east: float,
        south: float,
        database_info: dict = None,
        dem_reader = None,
        export_scale: float = 1.0,
        is_geotiff_elevation: bool = False
    ) -> bool:
        """
        Export elevation database (DEM or GeoTIFF format with raw elevation data)
        
        Args:
            file_path: Output file path
            west, north, east, south: Geographic bounds in decimal degrees
            database_info: Multi-file database info
            dem_reader: Single-file DEM reader
            export_scale: Export scale factor (1.0 = 100%)
            is_geotiff_elevation: True for GeoTIFF elevation, False for DEM format
            
        Returns:
            bool: True if successful, False if failed
        """
        try:
            import numpy as np
            from preview_window import TerrainProgressDialog
            
            print(f"🏔️ Starting elevation database export...")
            print(f"   Format: {'GeoTIFF Elevation' if is_geotiff_elevation else 'DEM'}")
            print(f"   Bounds: W={west:.6f}, N={north:.6f}, E={east:.6f}, S={south:.6f}")
            print(f"   Scale: {export_scale * 100:.1f}%")
            
            # Create and show progress dialog
            progress_dialog = TerrainProgressDialog(self)
            format_name = "GeoTIFF Elevation" if is_geotiff_elevation else "DEM Elevation"
            progress_dialog.setWindowTitle(f"Exporting {format_name} Database")
            progress_dialog.show()
            
            try:
                # PRE-FLIGHT MEMORY CHECK (prevents loading data that won't fit in memory)
                # Calculate expected output dimensions before any loading
                pixels_per_degree = None

                if database_info and database_info.get('pixels_per_degree'):
                    pixels_per_degree = database_info['pixels_per_degree']
                elif dem_reader and hasattr(dem_reader, 'pixels_per_degree'):
                    pixels_per_degree = dem_reader.pixels_per_degree
                else:
                    # Try to detect from database
                    if database_info and database_info.get('type') == 'multi_file':
                        from multi_file_database import MultiFileDatabase
                        from pathlib import Path
                        database_path = Path(database_info.get('path', ''))
                        if database_path.exists():
                            database = MultiFileDatabase(database_path)
                            pixels_per_degree = database.pixels_per_degree if hasattr(database, 'pixels_per_degree') else 120
                    else:
                        pixels_per_degree = 120  # Default fallback

                print(f"📏 Database resolution: {pixels_per_degree:.1f} pixels/degree")

                # Calculate expected output dimensions
                deg_width = east - west
                deg_height = north - south
                expected_width = int(deg_width * pixels_per_degree * export_scale)
                expected_height = int(deg_height * pixels_per_degree * export_scale)
                total_pixels = expected_width * expected_height

                # Calculate memory needed for raw elevation data (float32)
                elevation_memory_mb = (total_pixels * 4) / (1024**2)
                elevation_memory_gb = elevation_memory_mb / 1024

                # Get system memory
                import psutil
                memory = psutil.virtual_memory()
                available_gb = memory.available / (1024**3)
                total_system_gb = memory.total / (1024**3)

                # Hard limits (same as image export)
                MAX_PIXELS = 500_000_000
                MAX_MEMORY_PERCENT = 0.85
                max_safe_memory_gb = total_system_gb * MAX_MEMORY_PERCENT

                print(f"📊 Pre-flight check:")
                print(f"   Expected output: {expected_width:,}×{expected_height:,} = {total_pixels:,} pixels")
                print(f"   Memory needed: {elevation_memory_gb:.2f}GB")
                print(f"   Memory available: {available_gb:.2f}GB")

                # Check 1: Pixel count limit
                if total_pixels > MAX_PIXELS:
                    safe_scale = np.sqrt(MAX_PIXELS / total_pixels)
                    safe_percent = int(safe_scale * 100)
                    error_msg = (f"Export cancelled: Output too large\n\n"
                                f"Requested: {expected_width:,}×{expected_height:,} = {total_pixels:,} pixels\n"
                                f"Maximum: {MAX_PIXELS:,} pixels\n\n"
                                f"Suggestion: Reduce export scale to ~{safe_percent}% or select a smaller area")
                    print(f"❌ {error_msg}")
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Export Too Large", error_msg)
                    return False

                # Check 2: Memory availability
                if elevation_memory_gb > max_safe_memory_gb:
                    safe_scale = np.sqrt(max_safe_memory_gb / elevation_memory_gb)
                    safe_percent = int(safe_scale * 100)
                    error_msg = (f"Export cancelled: Insufficient memory\n\n"
                                f"Memory needed: {elevation_memory_gb:.1f}GB\n"
                                f"Memory available: {available_gb:.1f}GB\n"
                                f"System total: {total_system_gb:.1f}GB\n\n"
                                f"Suggestion: Reduce export scale to ~{safe_percent}% or close other applications")
                    print(f"❌ {error_msg}")
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Insufficient Memory", error_msg)
                    return False

                print(f"✅ Pre-flight check passed: Export is safe to proceed")

                # Phase 1: Load elevation data (0-60%)
                progress_dialog.update_progress(5, "Loading elevation data...")
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()

                elevation_data = self._get_cropped_elevation_data(
                    west, north, east, south, database_info, dem_reader, export_scale, progress_dialog
                )
                
                if elevation_data is None:
                    print("❌ Failed to get elevation data for export")
                    return False
                    
                print(f"✅ Got elevation data: {elevation_data.shape}")
                print(f"   Elevation range: {np.nanmin(elevation_data):.1f} to {np.nanmax(elevation_data):.1f} meters")
                
                # Phase 2: Export in the requested format (60-100%)
                progress_dialog.update_progress(60, f"Writing {format_name} file...")
                QApplication.processEvents()
                
                if is_geotiff_elevation:
                    success = self._save_geotiff_elevation(
                        elevation_data, file_path, west, north, east, south, 
                        database_info, dem_reader, progress_dialog
                    )
                else:
                    success = self._save_dem_elevation(
                        elevation_data, file_path, west, north, east, south,
                        database_info, dem_reader, progress_dialog
                    )
                
                if success:
                    progress_dialog.update_progress(100, "Export completed successfully")
                    QApplication.processEvents()
                    
                return success
                
            finally:
                # Always close the progress dialog
                progress_dialog.close()
                
        except Exception as e:
            print(f"❌ Error exporting elevation database: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _get_cropped_elevation_data(
        self,
        west: float,
        north: float, 
        east: float,
        south: float,
        database_info: dict = None,
        dem_reader = None,
        export_scale: float = 1.0,
        progress_dialog = None
    ):
        """Get elevation data cropped to selection bounds"""
        try:
            from PyQt6.QtWidgets import QApplication
            
            # Check database type to determine export path
            if database_info and database_info.get('type') == 'multi_file':
                # Multi-file database - use assembly system like preview
                print("📁 Loading from multi-file database using assembly system...")
                if progress_dialog:
                    progress_dialog.update_progress(10, "Assembling tiles from multi-file database...")
                    QApplication.processEvents()
                    
                elevation_data = self._load_multifile_elevation_data(
                    west, north, east, south, export_scale, progress_dialog
                )
                
                if progress_dialog:
                    progress_dialog.update_progress(40, "Tile assembly completed")
                    QApplication.processEvents()
                    
            elif dem_reader or (database_info and database_info.get('type') == 'single_file'):
                # Single-file database
                print("📄 Loading from single-file database...")
                if progress_dialog:
                    progress_dialog.update_progress(10, "Loading elevation data from file...")
                    QApplication.processEvents()
                    
                # Ensure we have a dem_reader - if not, use the instance one for single-file databases
                if not dem_reader and database_info and database_info.get('type') == 'single_file':
                    dem_reader = getattr(self, 'dem_reader', None)
                    if not dem_reader:
                        print("❌ No DEM reader available for single-file database")
                        return None
                
                if dem_reader.elevation_data is None:
                    elevation_data = dem_reader.load_elevation_data()
                else:
                    elevation_data = dem_reader.elevation_data
                
                if progress_dialog:
                    progress_dialog.update_progress(30, "Cropping to selection bounds...")
                    QApplication.processEvents()
                    
                # Crop to bounds using existing method from terrain renderer
                # Convert bounds dict to tuple format (west, north, east, south)
                dem_bounds_tuple = (
                    dem_reader.bounds['west'],
                    dem_reader.bounds['north'], 
                    dem_reader.bounds['east'],
                    dem_reader.bounds['south']
                )
                elevation_data = self.terrain_renderer._crop_elevation_data_to_bounds(
                    elevation_data, dem_bounds_tuple, west, north, east, south
                )
                
                if progress_dialog:
                    progress_dialog.update_progress(40, "Cropping completed")
                    QApplication.processEvents()
            else:
                print("❌ No elevation data source available")
                return None
                
            if elevation_data is None:
                print("❌ Failed to load elevation data")
                return None

            # Apply export scaling if not 100%
            # NOTE: Skip scaling for multi-file databases - DEMAssemblySystem already applied it
            is_multifile = database_info and database_info.get('type') == 'multi_file'

            if export_scale != 1.0 and not is_multifile:
                print(f"🔧 Applying export scale: {export_scale * 100:.1f}%")
                if progress_dialog:
                    progress_dialog.update_progress(45, f"Scaling to {export_scale * 100:.1f}%...")
                    QApplication.processEvents()

                original_shape = elevation_data.shape
                target_shape = (
                    int(original_shape[0] * export_scale),
                    int(original_shape[1] * export_scale)
                )

                try:
                    # Use NaN-aware bicubic interpolation for highest quality without data corruption
                    from nan_aware_interpolation import resize_with_nan_exclusion
                    elevation_data = resize_with_nan_exclusion(
                        elevation_data,
                        target_shape,
                        method='bicubic'
                    )
                    print(f"   NaN-aware bicubic resize from {original_shape} to {elevation_data.shape}")

                except ImportError:
                    print(f"   ⚠️ NaN-aware interpolation not available, using simple subsampling")
                    # Safe fallback: simple subsampling preserves data integrity
                    subsample_y = max(1, int(1.0 / export_scale))
                    subsample_x = max(1, int(1.0 / export_scale))
                    elevation_data = elevation_data[::subsample_y, ::subsample_x]

                if progress_dialog:
                    progress_dialog.update_progress(55, "Scaling completed")
                    QApplication.processEvents()
            elif is_multifile:
                print(f"✅ Scaling already applied during assembly (multi-file database)")

            if progress_dialog:
                progress_dialog.update_progress(60, "Elevation data ready for export")
                QApplication.processEvents()
                
            return elevation_data
            
        except Exception as e:
            print(f"❌ Error getting cropped elevation data: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _save_dem_elevation(
        self,
        elevation_data,
        file_path: str,
        west: float,
        north: float,
        east: float,
        south: float,
        database_info: dict = None,
        dem_reader = None,
        progress_dialog = None
    ) -> bool:
        """Save elevation data as DEM format with companion files"""
        try:
            print("🏔️ Creating DEM elevation database...")
            import numpy as np
            from pathlib import Path
            from PyQt6.QtWidgets import QApplication
            
            if progress_dialog:
                progress_dialog.update_progress(70, "Creating DEM file structure...")
                QApplication.processEvents()
            
            # Create output directory if needed
            output_path = Path(file_path)
            if not output_path.suffix:
                # If no extension, create a directory with .dem file inside
                output_dir = output_path
                output_dir.mkdir(parents=True, exist_ok=True)
                dem_file_path = output_dir / f"{output_path.name}.dem"
            else:
                # If has extension, use as filename and ensure parent directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)
                dem_file_path = output_path
                
            print(f"📁 Creating DEM database at: {dem_file_path}")
            
            if progress_dialog:
                progress_dialog.update_progress(80, "Writing DEM file and companions...")
                QApplication.processEvents()
            
            # Use existing DEM writing code from dem_assembly_system
            success = self._write_dem_file_with_companions(
                elevation_data, str(dem_file_path), west, north, east, south,
                database_info, dem_reader
            )
            
            if progress_dialog:
                progress_dialog.update_progress(95, "DEM file creation completed")
                QApplication.processEvents()
            
            if success:
                print(f"✅ DEM elevation database created successfully")
                print(f"📄 Files created:")
                for suffix in ['.dem', '.hdr', '.prj', '.stx']:
                    companion_file = dem_file_path.with_suffix(suffix)
                    if companion_file.exists():
                        print(f"   ✅ {companion_file.name}")
                    else:
                        print(f"   ❌ {companion_file.name} (missing)")
                        
            return success
            
        except Exception as e:
            print(f"❌ Error saving DEM elevation database: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _save_geotiff_elevation(
        self,
        elevation_data,
        file_path: str,
        west: float,
        north: float,
        east: float,
        south: float,
        database_info: dict = None,
        dem_reader = None,
        progress_dialog = None
    ) -> bool:
        """Save elevation data as GeoTIFF elevation database"""
        try:
            print("🗻 Creating GeoTIFF elevation database...")
            from PyQt6.QtWidgets import QApplication
            
            if progress_dialog:
                progress_dialog.update_progress(70, "Setting up GeoTIFF elevation export...")
                QApplication.processEvents()
            
            # Try to import rasterio
            try:
                import rasterio
                from rasterio.transform import from_bounds
                from rasterio.crs import CRS
                import numpy as np
            except ImportError:
                print("❌ Rasterio not available. Install with: pip install rasterio")
                return False
            
            height, width = elevation_data.shape
            print(f"📐 Elevation data dimensions: {width} x {height}")
            
            if progress_dialog:
                progress_dialog.update_progress(80, "Writing GeoTIFF elevation file...")
                QApplication.processEvents()
            print(f"🗺️ Geographic bounds: W={west:.6f}, N={north:.6f}, E={east:.6f}, S={south:.6f}")
            
            # Calculate the affine transform
            transform = from_bounds(west, south, east, north, width, height)
            print(f"🔢 Affine transform: {transform}")
            
            # Determine coordinate reference system
            crs = CRS.from_epsg(4326)  # Default to WGS84
            
            # Try to get CRS from source database
            if dem_reader and hasattr(dem_reader, 'crs'):
                try:
                    crs = CRS.from_string(dem_reader.crs)
                    print(f"🌐 Using source CRS: {crs}")
                except:
                    print(f"🌐 Using default CRS: {crs}")
            else:
                print(f"🌐 Using default CRS: {crs}")
            
            # Determine data type and nodata value
            # Always convert to float32 for consistent elevation export to avoid byte order issues
            # Float32 provides enough precision for elevation data and avoids endianness problems
            dtype = 'float32'
            nodata = np.nan
            
            # Ensure elevation data is in native byte order float32
            if elevation_data.dtype != np.float32:
                print(f"🔄 Converting from {elevation_data.dtype} to float32 for consistent export")
                elevation_data = elevation_data.astype(np.float32)
            
            # Ensure data is in native (system) byte order to avoid rasterio byte order issues
            if elevation_data.dtype.byteorder not in ('=', '|'):
                print(f"🔄 Converting from {elevation_data.dtype.byteorder} byte order to native byte order")
                elevation_data = elevation_data.astype(np.float32)  # This forces native byte order
                
            print(f"📊 Data type: {dtype}, NoData: {nodata}")
            
            # Ensure output has .tif extension for GeoTIFF
            if not file_path.lower().endswith('.tif'):
                file_path = file_path + '.tif'
                print(f"📁 Adding .tif extension: {file_path}")
            
            # Create the GeoTIFF
            with rasterio.open(
                file_path,
                'w',
                driver='GTiff',
                height=height,
                width=width,
                count=1,  # Single band for elevation
                dtype=dtype,
                crs=crs,
                transform=transform,
                compress='lzw',  # LZW compression as requested
                tiled=True,      # Tiled for better performance
                blockxsize=512,
                blockysize=512,
                nodata=nodata
            ) as dst:
                # Write elevation data as single band
                dst.write(elevation_data, 1)
                
                # Add metadata
                dst.update_tags(
                    SOFTWARE='DEM Visualizer',
                    DESCRIPTION='Elevation database exported from DEM data',
                    WEST_LONGITUDE=str(west),
                    EAST_LONGITUDE=str(east),
                    NORTH_LATITUDE=str(north),
                    SOUTH_LATITUDE=str(south),
                    ELEVATION_UNITS='meters'
                )
                
                # Add GeoTIFF keys for proper datum information
                # Following the user's advice about datum handling
                dst.update_tags(
                    GEOTIFF_INFORMATION='WGS84 Geographic Coordinate System',
                    GeographicTypeGeoKey='4326',  # WGS84
                    GeogGeodeticDatumGeoKey='6326',  # WGS84 datum
                    GeogEllipsoidGeoKey='7030'  # WGS84 ellipsoid
                )
                
                print(f"✅ GeoTIFF elevation metadata written")
                
            if progress_dialog:
                progress_dialog.update_progress(95, "GeoTIFF elevation file completed")
                QApplication.processEvents()
                
            print(f"✅ GeoTIFF elevation database saved successfully: {file_path}")
            print(f"🎯 File contains raw elevation data with proper georeferencing")
            return True
            
        except Exception as e:
            print(f"❌ Error saving GeoTIFF elevation database: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _write_dem_file_with_companions(
        self,
        elevation_data,
        dem_file_path: str,
        west: float,
        north: float,
        east: float,
        south: float,
        database_info: dict = None,
        dem_reader = None
    ) -> bool:
        """Write DEM file with all companion files (.hdr, .prj, .stx)"""
        try:
            from pathlib import Path
            import numpy as np
            
            height, width = elevation_data.shape
            
            # Calculate pixel size
            pixel_size_x = (east - west) / width
            pixel_size_y = (north - south) / height
            
            dem_path = Path(dem_file_path)
            
            # 1. Write binary elevation data (.dem file)
            print("📄 Writing .dem file...")
            with open(dem_path, 'wb') as f:
                # Handle NaN values by converting to nodata value
                output_array = elevation_data.copy()
                output_array[np.isnan(output_array)] = -9999
                
                # Convert to int16 with big-endian byte order (to match GTOPO30 format)
                int16_data = output_array.astype('>i2')  # Big-endian int16
                int16_data.tofile(f)
            
            # 2. Write header file (.hdr)
            print("📄 Writing .hdr file...")
            hdr_path = dem_path.with_suffix('.hdr')
            with open(hdr_path, 'w') as f:
                f.write(f"BYTEORDER      M\n")
                f.write(f"LAYOUT         BIL\n")
                f.write(f"NROWS          {height}\n")
                f.write(f"NCOLS          {width}\n")
                f.write(f"NBANDS         1\n")
                f.write(f"NBITS          16\n")
                f.write(f"BANDROWBYTES   {width * 2}\n")
                f.write(f"TOTALROWBYTES  {width * 2}\n")
                f.write(f"BANDGAPBYTES   0\n")
                f.write(f"NODATA         -9999\n")
                f.write(f"ULXMAP         {west + pixel_size_x/2}\n")
                f.write(f"ULYMAP         {north - pixel_size_y/2}\n")
                f.write(f"XDIM           {pixel_size_x}\n")
                f.write(f"YDIM           {pixel_size_y}\n")
            
            # 3. Write projection file (.prj)
            print("📄 Writing .prj file...")
            prj_path = dem_path.with_suffix('.prj')
            with open(prj_path, 'w') as f:
                f.write("Projection    GEOGRAPHIC\n")
                f.write("Datum         WGS84\n")
                f.write("Zunits        METERS\n")
                f.write("Units         DD\n")
                f.write("Spheroid      WGS84\n")
                f.write("Xshift        0.0000000000\n")
                f.write("Yshift        0.0000000000\n")
                f.write("Parameters\n")
            
            # 4. Write statistics file (.stx)
            print("📄 Writing .stx file...")
            stx_path = dem_path.with_suffix('.stx')
            
            # Calculate statistics (excluding nodata values)
            valid_data = elevation_data[~np.isnan(elevation_data)]
            if len(valid_data) > 0:
                min_val = np.min(valid_data)
                max_val = np.max(valid_data)
                mean_val = np.mean(valid_data)
                std_val = np.std(valid_data)
            else:
                min_val = max_val = mean_val = std_val = -9999
                
            with open(stx_path, 'w') as f:
                f.write(f"1 {min_val:.6f} {max_val:.6f} {mean_val:.6f} {std_val:.6f}\n")
            
            print(f"✅ DEM file and companions written successfully")
            print(f"   📄 {dem_path.name}")
            print(f"   📄 {hdr_path.name}")
            print(f"   📄 {prj_path.name}")
            print(f"   📄 {stx_path.name}")
            print(f"   📊 Statistics: min={min_val:.1f}, max={max_val:.1f}, mean={mean_val:.1f}m")
            
            return True
            
        except Exception as e:
            print(f"❌ Error writing DEM file with companions: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_multifile_elevation_data(
        self,
        west: float,
        north: float,
        east: float,
        south: float,
        export_scale: float = 1.0,
        progress_dialog = None
    ):
        """
        Load elevation data from multi-file database using DEMAssemblySystem.

        This uses the same memory-safe chunking system as image export, preventing
        out-of-memory crashes when exporting large databases.

        Args:
            west, north, east, south: Geographic bounds in decimal degrees
            export_scale: Scale factor for final output (1.0 = 100%, 0.5 = 50%, etc.)

        Returns:
            numpy.ndarray: Assembled elevation data, or None if failed
        """
        try:
            print(f"🔧 Loading multi-file elevation data using DEMAssemblySystem...")
            print(f"   Bounds: W={west:.6f}, N={north:.6f}, E={east:.6f}, S={south:.6f}")
            print(f"   Scale: {export_scale * 100:.1f}%")

            from pathlib import Path
            from multi_file_database import MultiFileDatabase
            from dem_assembly_system import DEMAssembler, AssemblyConfig
            from dem_reader import DEMReader

            # Load database using the current database info
            db_path = self.current_database_info.get('path')
            if not db_path:
                print("❌ No database path available")
                return None

            db_path = Path(db_path)
            if not db_path.exists():
                print(f"❌ Database path does not exist: {db_path}")
                return None

            database = MultiFileDatabase(db_path)
            if not database.tiles:
                print(f"❌ No tiles found in database: {db_path}")
                return None

            print(f"🗂️ Database: {len(database.tiles)} tiles, type: {database.database_type}")

            # Get tiles for the requested bounds
            tiles = database.get_tiles_for_bounds(west, north, east, south)
            if not tiles:
                print(f"❌ No tiles found for bounds")
                return None

            print(f"📦 Found {len(tiles)} intersecting tiles")

            # Configure assembly system for export (use chunking for large exports)
            assembly_config = AssemblyConfig(
                temp_dem_location="system",
                chunk_size_mb=200,  # Process in 200MB chunks
                max_memory_percent=50.0
            )

            assembler = DEMAssembler(assembly_config)

            # Progress callback wrapper
            def assembly_progress_callback(message):
                if progress_dialog:
                    from PyQt6.QtWidgets import QApplication
                    # Map assembly progress to 15-35% of overall export progress
                    progress_dialog.update_progress(15, message)
                    QApplication.processEvents()
                print(f"   {message}")

            if progress_dialog:
                from PyQt6.QtWidgets import QApplication
                progress_dialog.update_progress(15, f"Assembling {len(tiles)} tiles with memory-safe chunking...")
                QApplication.processEvents()

            # Use assembly system with chunking support (handles large exports safely)
            temp_dem_path = assembler.assemble_tiles_to_dem(
                tiles=tiles,
                west=west, north=north, east=east, south=south,
                export_scale=export_scale,  # Scale is applied DURING assembly, not after
                progress_callback=assembly_progress_callback
            )

            if not temp_dem_path:
                print("❌ Assembly failed")
                return None

            if progress_dialog:
                progress_dialog.update_progress(30, "Loading assembled data...")
                QApplication.processEvents()

            # Load the assembled DEM file
            dem_reader = DEMReader()
            if not dem_reader.load_dem_file(str(temp_dem_path)):
                print("❌ Failed to load assembled DEM")
                return None

            elevation_data = dem_reader.load_elevation_data()

            if progress_dialog:
                progress_dialog.update_progress(35, "Assembly completed")
                QApplication.processEvents()

            if elevation_data is None:
                print("❌ Failed to load elevation data from assembled DEM")
                return None

            print(f"✅ Assembled elevation data: {elevation_data.shape}")
            print(f"   Scale was applied during assembly (no double-scaling)")

            # Clean up temp file
            try:
                Path(temp_dem_path).unlink()
                print(f"🧹 Cleaned up temporary DEM file")
            except Exception as e:
                print(f"⚠️ Could not delete temp file {temp_dem_path}: {e}")

            return elevation_data

        except Exception as e:
            print(f"❌ Error loading multi-file elevation data: {e}")
            import traceback
            traceback.print_exc()
            return None

    def update_preview_display(self, preview_image):
        """Update the preview display with a new image"""
        # Update the preview label if it exists
        if hasattr(self, 'preview_label'):
            from PyQt6.QtGui import QPixmap
            from PyQt6.QtCore import Qt
            pixmap = QPixmap.fromImage(preview_image)
            scaled_pixmap = pixmap.scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled_pixmap)


    # ============================================================================
    # Helper Methods for Preview Icon Operations
    # ============================================================================
    
    def get_current_selection_from_coordinate_fields(self):
        """Get current selection bounds from coordinate input fields"""
        try:
            # Check if coordinate fields exist and have values
            if not all(hasattr(self, field) for field in ['north_edit', 'south_edit', 'west_edit', 'east_edit']):
                print("❌ Coordinate fields not available")
                return None
            
            # Try to parse coordinate values from the input fields
            try:
                north_text = self.north_edit.text().strip()
                south_text = self.south_edit.text().strip()
                west_text = self.west_edit.text().strip()
                east_text = self.east_edit.text().strip()
                
                # Check if all fields have values
                if not all([north_text, south_text, west_text, east_text]):
                    print("❌ One or more coordinate fields are empty")
                    return None
                
                # Parse coordinate values (handle both decimal and DMS formats)
                north = self.parse_coordinate_value(north_text, True)  # True = latitude
                south = self.parse_coordinate_value(south_text, True)
                west = self.parse_coordinate_value(west_text, False)   # False = longitude  
                east = self.parse_coordinate_value(east_text, False)
                
                if None in [north, south, west, east]:
                    print("❌ Failed to parse one or more coordinate values")
                    return None
                
                # Validate coordinate bounds
                if north <= south:
                    print("❌ Invalid coordinates: North must be greater than South")
                    return None
                
                if west >= east:
                    print("❌ Invalid coordinates: East must be greater than West")  
                    return None
                
                selection_bounds = {
                    'north': north,
                    'south': south, 
                    'west': west,
                    'east': east
                }
                
                print(f"✅ Parsed selection bounds: {selection_bounds}")
                return selection_bounds
                
            except ValueError as e:
                print(f"❌ Error parsing coordinate values: {e}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting current selection from coordinate fields: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def parse_coordinate_value(self, text, is_latitude):
        """Parse coordinate value from text (handles both decimal degrees and DMS format)"""
        try:
            text = text.strip()
            if not text:
                return None
            
            # Try parsing as decimal degrees first
            try:
                return float(text)
            except ValueError:
                pass
            
            # Try parsing as DMS (Degrees/Minutes/Seconds) format
            # Examples: "45°30'15"N", "45°30'15.5"N", "45°30'N", "45°N"
            import re
            dms_pattern = r'(\d+)°(?:(\d+)\'?(?:(\d+(?:\.\d+)?)\"?)?)?([NSEW])?'
            match = re.match(dms_pattern, text.upper())
            
            if match:
                degrees = int(match.group(1))
                minutes = int(match.group(2)) if match.group(2) else 0
                seconds = float(match.group(3)) if match.group(3) else 0
                direction = match.group(4)
                
                # Convert to decimal degrees
                decimal = degrees + minutes/60.0 + seconds/3600.0
                
                # Apply direction (negative for South/West)
                if direction in ['S', 'W']:
                    decimal = -decimal
                
                return decimal
            
            # If all parsing fails, return None
            print(f"❌ Could not parse coordinate: '{text}'")
            return None
            
        except Exception as e:
            print(f"❌ Error parsing coordinate '{text}': {e}")
            return None

    # ============================================================================
    # Preview Icon Menu Handlers  
    # ============================================================================
    
    def menu_create_preview_icon_from_selection(self):
        """Menu handler: Create preview icon from current selection"""
        try:
            print("📋 Menu: Create Preview Icon from Selection requested")
            
            # Check if we have a loaded database
            has_database = hasattr(self, 'current_database_info') and self.current_database_info
            has_dem_file = hasattr(self, 'current_dem_file') and self.current_dem_file
            
            if not has_database and not has_dem_file:
                QMessageBox.warning(
                    self,
                    "No Database Loaded",
                    "Cannot create preview icon: No elevation database is loaded.\n\n"
                    "Please load a GeoTIFF file or database folder first."
                )
                return
            
            # Get current selection from coordinate fields
            current_selection = self.get_current_selection_from_coordinate_fields()
            if current_selection:
                print(f"🎯 Using current selection from coordinate fields: {current_selection}")
                self.create_preview_icon_from_selection(current_selection)
            else:
                QMessageBox.information(
                    self,
                    "No Selection",
                    "No area is currently selected on the map.\n\n"
                    "Please drag to select an area on the world map first, or enter coordinates manually in the coordinate fields."
                )
                
        except Exception as e:
            print(f"❌ Error in menu_create_preview_icon_from_selection: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create preview icon from selection:\n{str(e)}"
            )
    
    def menu_next_preview_icon(self):
        """Menu handler: Cycle to next preview icon"""
        try:
            print("🔄 Menu: Next Preview Icon requested")
            
            if not hasattr(self, 'preview_databases') or not self.preview_databases:
                QMessageBox.information(
                    self,
                    "No Preview Icons",
                    "No preview icon databases are available for cycling."
                )
                return
            
            if len(self.preview_databases) <= 1:
                QMessageBox.information(
                    self,
                    "Only One Preview Icon", 
                    "Only one preview icon database is available. Cannot cycle to next."
                )
                return
            
            # Call the existing cycle function
            self.cycle_to_next_preview_database()
            
            # Show brief status message
            current_db = self.preview_databases[self.current_preview_index]
            db_name = current_db.name if hasattr(current_db, 'name') else str(current_db)
            self.status_bar.showMessage(f"Switched to preview icon: {db_name}", 2000)
            
        except Exception as e:
            print(f"❌ Error in menu_next_preview_icon: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to cycle to next preview icon:\n{str(e)}"
            )
    
    def menu_delete_current_preview_icon(self):
        """Menu handler: Delete current preview icon"""
        try:
            print("🗑️ Menu: Delete Current Preview Icon requested")
            
            if not hasattr(self, 'preview_databases') or not self.preview_databases:
                QMessageBox.information(
                    self,
                    "No Preview Icons",
                    "No preview icon databases are available to delete."
                )
                return
            
            if self.current_preview_index < 0 or self.current_preview_index >= len(self.preview_databases):
                QMessageBox.warning(
                    self,
                    "Invalid Selection",
                    "No valid preview icon is currently selected for deletion."
                )
                return
            
            current_db = self.preview_databases[self.current_preview_index]
            db_name = current_db.name if hasattr(current_db, 'name') else str(current_db)
            
            # Safety check: don't delete if it's the protected default
            if db_name == "pr01_fixed.tif":
                QMessageBox.warning(
                    self,
                    "Cannot Delete Default",
                    "Cannot delete the default preview icon database (pr01_fixed.tif).\n\n"
                    "This preview icon is protected to ensure the application always has at least one preview available."
                )
                return
            
            # Safety check: don't delete if it's the last database
            if len(self.preview_databases) <= 1:
                QMessageBox.warning(
                    self,
                    "Cannot Delete Last Icon",
                    "Cannot delete the last remaining preview icon.\n\n"
                    "At least one preview icon must always be available."
                )
                return
            
            # Ask for confirmation
            reply = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to delete the current preview icon?\n\n"
                f"Preview icon: {db_name}\n\n"
                f"This action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Call the existing delete function
                self.delete_current_preview_database()
                
                # Show confirmation message
                self.status_bar.showMessage(f"Deleted preview icon: {db_name}", 3000)
                print(f"✅ Successfully deleted preview icon via menu: {db_name}")
            else:
                print("🚫 Preview icon deletion cancelled by user")
                
        except Exception as e:
            print(f"❌ Error in menu_delete_current_preview_icon: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to delete preview icon:\n{str(e)}"
            )
    
    def update_preview_icon_menu_state(self):
        """Update the state of preview icon menu items based on current conditions"""
        try:
            if not hasattr(self, 'delete_preview_action'):
                return
                
            # Update delete action state
            can_delete = False
            if (hasattr(self, 'preview_databases') and self.preview_databases and 
                len(self.preview_databases) > 1 and 
                0 <= self.current_preview_index < len(self.preview_databases)):
                
                current_db = self.preview_databases[self.current_preview_index]
                db_name = current_db.name if hasattr(current_db, 'name') else str(current_db)
                # Can delete if it's not the protected default
                can_delete = db_name != "pr01_fixed.tif"
            
            self.delete_preview_action.setEnabled(can_delete)
            
            # Update next preview action state  
            can_cycle = (hasattr(self, 'preview_databases') and self.preview_databases and 
                        len(self.preview_databases) > 1)
            
            if hasattr(self, 'next_preview_action'):
                self.next_preview_action.setEnabled(can_cycle)
                
            # Create preview action is always available if we have a database loaded
            has_database = ((hasattr(self, 'current_database_info') and self.current_database_info) or 
                           (hasattr(self, 'current_dem_file') and self.current_dem_file))
            
            if hasattr(self, 'create_preview_action'):
                self.create_preview_action.setEnabled(has_database)
                
        except Exception as e:
            print(f"⚠️ Error updating preview icon menu state: {e}")


def main():
    """Test the Qt Designer integration"""
    app = QApplication(sys.argv)
    
    print("=== Testing Qt Designer Integration ===")
    print(f"Loading UI file from: {get_resource_path('main_window_complete.ui')}")
    
    try:
        window = DEMVisualizerQtDesignerWindow()
        window.show()
        
        print(f"\n✅ Window created successfully!")
        print(f"Window title: {window.windowTitle()}")
        print(f"Window size: {window.width()}x{window.height()}")
        
        # Test database info update
        print("\n=== Testing Database Info Update ===")
        test_db_info = {
            'width_pixels': 4320,
            'height_pixels': 2160,
            'pix_per_degree': 120.0,
            'west': -180.0,
            'north': 90.0,
            'east': 180.0,
            'south': -90.0
        }
        
        test_export_info = {
            'width_pixels': 2880,
            'height_pixels': 2160,
            'pix_per_degree': 72.0,
            'west': 20.0,
            'north': 40.0,
            'east': 60.0,
            'south': -10.0,
            'resolution_ppi': 240.0
        }
        
        window.update_database_info_display(test_db_info, test_export_info)
        
        app.exec()
        
    except Exception as e:
        print(f"❌ Error creating window: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())