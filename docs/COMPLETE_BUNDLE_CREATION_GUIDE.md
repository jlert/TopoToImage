# TopoToImage Complete Bundle Creation Guide

## Overview

This comprehensive guide provides step-by-step instructions for creating a fully functional PyInstaller bundle of the TopoToImage application. This guide incorporates all lessons learned through multiple development phases and addresses all known issues to ensure a successful bundle creation process.

## Table of Contents

1. [Prerequisites and System Requirements](#prerequisites-and-system-requirements)
2. [Critical Pre-Bundle Preparations](#critical-pre-bundle-preparations)
3. [PyInstaller Specification File](#pyinstaller-specification-file)
4. [Build Process](#build-process)
5. [Testing and Verification](#testing-and-verification)
6. [Known Issues and Solutions](#known-issues-and-solutions)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Maintenance and Updates](#maintenance-and-updates)

## Prerequisites and System Requirements

### System Requirements
- **Platform**: macOS (this guide is macOS-specific)
- **Python**: 3.12.2 or compatible
- **PyInstaller**: 6.5.0 or later
- **Architecture**: ARM64 (Apple Silicon) or x64 (Intel)

### Required Python Packages
Install all dependencies in your Python environment:
```bash
pip install PyQt6 rasterio GDAL numpy matplotlib scipy Pillow reportlab pyinstaller
```

### Development Environment Setup
- Ensure the TopoToImage application runs correctly in development mode
- All features should work before attempting to create a bundle
- Test all functionality including preview creation, exports, and dialog windows

## Critical Pre-Bundle Preparations

### 1. Resource Path Resolution Functions

Ensure these critical functions are properly implemented in `src/main_window_qt_designer.py`:

```python
def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and PyInstaller bundled app"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        if hasattr(sys, '_MEIPASS'):
            # Running as PyInstaller bundle
            # Resources are in Contents/Resources/, not in _MEIPASS directly
            bundle_resources = Path(sys._MEIPASS).parent / "Resources"
            
            # Handle different resource types in bundle
            if relative_path.startswith('gradients/') or relative_path == 'gradients.json':
                if relative_path == 'gradients.json':
                    return bundle_resources / "gradients" / "gradients.json"
                else:
                    return bundle_resources / "gradients" / relative_path.replace('gradients/', '')
            elif relative_path.startswith('maps/') or relative_path == 'maps':
                if relative_path == 'maps':
                    return bundle_resources / "maps"
                else:
                    return bundle_resources / "maps" / relative_path.replace('maps/', '')
            elif relative_path.startswith('preview_icon_databases/') or relative_path == 'preview_icon_databases':
                if relative_path == 'preview_icon_databases':
                    return bundle_resources / "preview_icon_databases"
                else:
                    return bundle_resources / "preview_icon_databases" / relative_path.replace('preview_icon_databases/', '')
            elif relative_path.startswith('ui/'):
                return bundle_resources / relative_path
            elif relative_path.startswith('icons/'):
                return bundle_resources / relative_path
            elif relative_path.startswith('sample_data/'):
                return bundle_resources / relative_path
            else:
                return bundle_resources / relative_path
        else:
            # Development mode - use relative paths from project root
            project_root = Path(__file__).parent.parent
            
            # Handle different resource types in development
            if relative_path.endswith('.ui'):
                return project_root / "ui" / relative_path
            elif relative_path.startswith('maps/') or relative_path == 'maps':
                return project_root / "assets" / relative_path
            elif relative_path.startswith('gradients/') or relative_path == 'gradients.json':
                return project_root / "assets" / "gradients" / relative_path.replace('gradients/', '')
            elif relative_path.startswith('preview_icon_databases/') or relative_path == 'preview_icon_databases':
                return project_root / "assets" / relative_path
            else:
                return project_root / "assets" / relative_path
                
    except AttributeError:
        # Fallback for development mode
        project_root = Path(__file__).parent.parent
        return project_root / "assets" / relative_path

def get_writable_data_path(relative_path: str) -> Path:
    """Get absolute path to writable data location, works for dev and PyInstaller bundled app"""
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle - use writable home directory location
        data_dir = Path.home() / "TopoToImage_Data"
        data_dir.mkdir(exist_ok=True)
        return data_dir / relative_path
    else:
        # Running in development - use project assets directory (writable)
        project_root = Path(__file__).parent.parent
        return project_root / "assets" / relative_path
```

### 2. First-Run Experience Implementation

Ensure the first-run experience is properly implemented:

```python
def is_first_run(self):
    """Check if this is the first run using a dedicated flag file in home directory"""
    try:
        user_data_dir = Path.home() / "TopoToImage_Data"
        first_run_flag = user_data_dir / ".first_run_complete"
        return not first_run_flag.exists()
    except Exception as e:
        print(f"⚠️ Error checking first run status: {e}")
        return False

def setup_first_run_experience(self):
    """Set up first-run experience with sample data and user directory"""
    # Implementation should create ~/TopoToImage_Data/ structure
    # Copy preview databases, gradients, and sample data
    # Load sample database automatically
    # Show welcome dialog
    # Mark first run as complete
```

### 3. Proper Initialization Order

Ensure correct initialization order in the main window `__init__` method:

```python
def __init__(self):
    # ... other initialization code ...
    
    # Connect signals
    self.connect_signals()
    
    # Initialize export controls with default values (before loading gradients)
    self.initialize_export_controls()
    
    # CRITICAL: Scan preview databases BEFORE loading gradients
    self.scan_preview_databases()
    
    # Load gradients into browser (this triggers preview generation)
    self.load_gradients_into_browser()
    
    # Handle startup database loading (must be after UI setup)
    QTimer.singleShot(100, self.handle_startup_database_loading)
```

## PyInstaller Specification File

Create `topotoimage.spec` with the following complete configuration:

```python
# -*- mode: python ; coding: utf-8 -*-
"""
TopoToImage PyInstaller Specification File

This spec file bundles all necessary resources while ensuring
proper separation of bundled (read-only) and user-writable data.
Incorporates all lessons learned through multiple development phases.
"""

import sys
from pathlib import Path

# Get the project root directory
project_root = Path.cwd()

# Define data files to include in the bundle
# These are read-only resources that get bundled with the application
datas = [
    # UI files - CRITICAL: All dialog UI files must be included
    ('ui/main_window_complete.ui', 'ui'),
    ('ui/gradient_editor_02.ui', 'ui'),
    ('ui/hls_adjustment_dialog.ui', 'ui'),
    
    # Application icons
    ('assets/icons/TopoToImage.icns', 'icons'),
    
    # Maps and backgrounds
    ('assets/maps/default_background_map.svg', 'maps'),
    
    # Default gradients (templates for user customization)
    ('assets/gradients.json', 'gradients'),
    
    # Sample data for first-run experience
    ('assets/sample_data/Gtopo30_reduced_2160x1080.tif', 'sample_data'),
    
    # Preview icon databases for cycling functionality
    ('assets/preview_icon_databases/pr01_fixed.tif', 'preview_icon_databases'),
    ('assets/preview_icon_databases/pr03_fixed.tif', 'preview_icon_databases'),
    ('assets/preview_icon_databases/pr04_fixed.tif', 'preview_icon_databases'),
    ('assets/preview_icon_databases/preview_icon_01.tif', 'preview_icon_databases'),
    ('assets/preview_icon_databases/preview_icon_02.tif', 'preview_icon_databases'),
    ('assets/preview_icon_databases/preview_icon_12.tif', 'preview_icon_databases'),
    ('assets/preview_icon_databases/preview_icon_14.tif', 'preview_icon_databases'),
    
    # PROJ data for coordinate reference systems (fixes bundle preview icon creation)
    ('/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/rasterio/proj_data', 'rasterio/proj_data'),
    
    # Application modules that need to be included as data
    ('src/__init__.py', 'src'),
    ('src/coordinate_converter.py', 'src'),
    ('src/coordinate_validator.py', 'src'),
    ('src/dem_assembly_system.py', 'src'),
    ('src/dem_reader.py', 'src'),
    ('src/dialog_helpers.py', 'src'),
    ('src/distance_formatter.py', 'src'),
    ('src/elevation_scaler.py', 'src'),
    ('src/export_controls_logic.py', 'src'),
    ('src/gradient_editor_window.py', 'src'),
    ('src/gradient_system.py', 'src'),
    ('src/gradient_widgets.py', 'src'),
    ('src/hls_adjustment_dialog.py', 'src'),
    ('src/interactive_color_ramp.py', 'src'),
    ('src/key_file_generator.py', 'src'),
    ('src/main_window_qt_designer.py', 'src'),
    ('src/map_backgrounds.py', 'src'),
    ('src/map_widgets.py', 'src'),
    ('src/meridian_utils.py', 'src'),
    ('src/multi_file_database.py', 'src'),
    ('src/multi_tile_loader.py', 'src'),
    ('src/nan_aware_interpolation.py', 'src'),
    ('src/preview_window.py', 'src'),
    ('src/recent_databases.py', 'src'),
    ('src/shadow_method_1.py', 'src'),
    ('src/shadow_method_2.py', 'src'),
    ('src/shadow_method_3.py', 'src'),
    ('src/shadow_methods/__init__.py', 'src/shadow_methods'),
    ('src/shadow_methods/shadow_method_1.py', 'src/shadow_methods'),
    ('src/shadow_methods/shadow_method_2.py', 'src/shadow_methods'),
    ('src/shadow_methods/shadow_method_3.py', 'src/shadow_methods'),
    ('src/terrain_renderer.py', 'src'),
    ('src/update_checker.py', 'src'),
    ('src/version.py', 'src'),
]

# Hidden imports - modules that PyInstaller might miss
# CRITICAL: All these must be included for the application to work
hiddenimports = [
    # PyQt6 modules
    'PyQt6.QtCore',
    'PyQt6.QtGui', 
    'PyQt6.QtWidgets',
    'PyQt6.QtSvg',
    'PyQt6.uic',
    
    # Rasterio and GDAL dependencies
    'rasterio',
    'rasterio.env',
    'rasterio._env',
    'rasterio.crs',
    'rasterio.transform',
    'rasterio.mask',
    'rasterio.features',
    'rasterio.warp',
    'rasterio.sample',
    'rasterio._io',
    'rasterio.dtypes',
    'rasterio.errors',
    'rasterio.windows',
    'rasterio.coords',
    'rasterio.profiles',
    'rasterio.merge',
    'rasterio.enums',
    'rasterio.vrt',
    
    # GDAL - Note: May show "not found" errors but usually still works
    'osgeo',
    'osgeo.gdal',
    'osgeo.osr',
    'osgeo.ogr',
    
    # Numpy and data processing
    'numpy',
    'numpy.core',
    'numpy.core._methods',
    'numpy.lib.format',
    
    # Matplotlib for color processing
    'matplotlib',
    'matplotlib.pyplot',
    'matplotlib.colors',
    'matplotlib.cm',
    
    # Scipy for scientific computing
    'scipy',
    'scipy.special',
    'scipy.special._cdflib',
    'scipy.stats',
    'scipy.linalg',
    
    # Image processing
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageQt',
    
    # PDF generation for key files - CRITICAL for legend file generation
    'reportlab',
    'reportlab.pdfgen',
    'reportlab.pdfgen.canvas',
    'reportlab.lib.pagesizes',
    'reportlab.lib.units',
    'reportlab.lib.colors',
    'reportlab.lib.utils',
    'reportlab.platypus',
    'reportlab.lib.styles',
    'reportlab.lib.enums',
    
    # Standard library modules that might be missed
    'json',
    'pathlib',
    'shutil',
    'datetime',
    'typing',
    
    # Application modules
    'version',
    'src.version',
]

# Binary exclusions (files we don't want to include)
excludes = [
    # Development tools
    'pytest',
    'setuptools',
    'pip',
    
    # Unnecessary matplotlib backends
    'matplotlib.backends.backend_tk',
    'matplotlib.backends.backend_tkagg',
    
    # Test modules
    'test',
    'tests',
    'unittest',
]

# Analysis step - analyzes the Python script and its dependencies
a = Analysis(
    ['topotoimage.py'],                    # Main script
    pathex=[str(project_root)],            # Path to search for modules
    binaries=[],                           # Additional binary files
    datas=datas,                          # Data files to include
    hiddenimports=hiddenimports,          # Hidden imports
    hookspath=[],                         # Custom hooks
    hooksconfig={},                       # Hook configuration
    runtime_hooks=[],                     # Runtime hooks
    excludes=excludes,                    # Modules to exclude
    win_no_prefer_redirects=False,        # Windows-specific
    win_private_assemblies=False,         # Windows-specific
    cipher=None,                          # Encryption (None = no encryption)
    noarchive=False,                      # Create archive
)

# PYZ step - creates the Python archive
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# EXE step - creates the executable
exe = EXE(
    pyz,
    a.scripts,
    [],                                   # No additional scripts
    exclude_binaries=True,                # Create a directory bundle (not one-file)
    name='TopoToImage',                   # Executable name
    debug=False,                          # Debug mode (False for release)
    bootloader_ignore_signals=False,      # Signal handling
    strip=False,                          # Strip debug symbols (False for better error reporting)
    upx=False,                            # UPX compression (disabled for compatibility)
    console=False,                        # Hide console window on Windows
    disable_windowed_traceback=False,     # Show tracebacks in windowed mode
    argv_emulation=False,                 # macOS-specific
    target_arch=None,                     # Target architecture (None = current)
    codesign_identity=None,               # Code signing identity (None = no signing)
    entitlements_file=None,               # macOS entitlements
    icon='assets/icons/TopoToImage.icns', # Application icon
)

# COLLECT step - creates the final bundle directory
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,                          # Strip debug symbols
    upx=False,                            # UPX compression
    upx_exclude=[],                       # Files to exclude from UPX
    name='TopoToImage',                   # Bundle directory name
)

# macOS App Bundle creation
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='TopoToImage.app',           # App bundle name
        icon='assets/icons/TopoToImage.icns',  # App icon
        bundle_identifier='com.topotoimage.app',  # Bundle identifier
        info_plist={
            'CFBundleName': 'TopoToImage',
            'CFBundleDisplayName': 'TopoToImage',
            'CFBundleIdentifier': 'com.topotoimage.app',
            'CFBundleVersion': '4.0.0',
            'CFBundleShortVersionString': '4.0.0',
            'CFBundleInfoDictionaryVersion': '6.0',
            'CFBundleExecutable': 'TopoToImage',
            'CFBundlePackageType': 'APPL',
            'CFBundleSignature': 'TOPO',
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,
            'CFBundleDocumentTypes': [
                {
                    'CFBundleTypeName': 'GeoTIFF File',
                    'CFBundleTypeExtensions': ['tif', 'tiff'],
                    'CFBundleTypeRole': 'Editor',
                    'CFBundleTypeDescription': 'GeoTIFF elevation data file',
                },
                {
                    'CFBundleTypeName': 'DEM File',
                    'CFBundleTypeExtensions': ['dem'],
                    'CFBundleTypeRole': 'Editor',
                    'CFBundleTypeDescription': 'Digital Elevation Model file',
                },
            ],
        },
    )
```

## Build Process

### 1. Clean Previous Builds
```bash
# Remove any existing build artifacts
rm -rf build dist
```

### 2. Run PyInstaller
```bash
# Build the bundle using the spec file
pyinstaller topotoimage.spec
```

### 3. Expected Build Output
The build process should show:
- Analysis phase completing successfully
- Hidden imports being analyzed (including reportlab and rasterio)
- Data files being collected
- PROJ data being included
- macOS app bundle being created

Watch for these confirmation messages:
```
INFO: Analyzing hidden import 'reportlab'
INFO: Building BUNDLE BUNDLE-00.toc completed successfully
```

### 4. Build Results
After successful build:
```
dist/
├── TopoToImage/                    # Directory bundle
└── TopoToImage.app/                # macOS app bundle (final product)
    ├── Contents/
    │   ├── MacOS/
    │   │   └── TopoToImage
    │   ├── Resources/
    │   │   ├── rasterio/
    │   │   │   └── proj_data/       # CRITICAL: PROJ database for CRS operations
    │   │   │       └── proj.db
    │   │   ├── ui/
    │   │   ├── gradients/
    │   │   ├── preview_icon_databases/
    │   │   └── sample_data/
    │   └── Frameworks/
```

## Testing and Verification

### 1. Launch Test
```bash
# Test direct execution
./dist/TopoToImage.app/Contents/MacOS/TopoToImage

# Test macOS app bundle
open dist/TopoToImage.app
```

### 2. Comprehensive Feature Verification Checklist

**✅ Basic Functionality:**
- [ ] Application launches without errors
- [ ] Main window displays correctly
- [ ] No missing UI file errors
- [ ] No PROJ database errors

**✅ Gradient System:**
- [ ] All gradients load correctly (21+ gradients)
- [ ] Gradient list displays correctly
- [ ] Gradient selection works
- [ ] Preview icon generates automatically on startup

**✅ Dialog Windows:**
- [ ] Edit gradient window opens (`gradient_editor_02.ui`)
- [ ] HLS adjustment dialog opens (`hls_adjustment_dialog.ui`)
- [ ] All UI controls functional

**✅ Preview System:**
- [ ] Preview icon displays on startup
- [ ] Preview cycling works (if multiple preview databases)
- [ ] Preview updates when gradient selected
- [ ] **CRITICAL**: Preview icon creation works (tests CRS functionality)

**✅ Export Functionality:**
- [ ] Image export works at different scales
- [ ] Scale settings are respected (not always 100%)
- [ ] Elevation database export works
- [ ] Key file (legend) generation works when checkbox activated
- [ ] No "Key file generation failed" messages

**✅ Database Operations:**
- [ ] GeoTIFF databases load correctly
- [ ] Terrain rendering works
- [ ] Database information displays
- [ ] Temporary files created in system temp directory (not root)

**✅ First-Run Experience:**
- [ ] Sample database loads automatically
- [ ] Preview databases are copied to user directory
- [ ] Welcome dialog appears with proper branding
- [ ] User data directory (`~/TopoToImage_Data/`) is created

### 3. Console Output Monitoring

Watch for these success indicators:
```
✅ rasterio available - GeoTIFF support enabled
🗺️ Starting TopoToImage v4.0.0-beta.1...
✅ All essential map files found
🎨 Initializing gradient system with: /Users/.../gradients.json
📁 Loading array format gradients
✅ Loaded 21+ gradients
```

Watch for these warning signs:
```
⚠️ reportlab not available - Key file generation disabled     # BAD - reportlab missing
❌ UI file not found: ...                                     # BAD - missing UI files  
❌ No gradient list or no current item selected              # BAD - initialization order issue
ERROR 1: PROJ: internal_proj_create_from_database: Cannot find proj.db  # BAD - missing PROJ data
Failed to create Preview icon from selection                  # BAD - CRS/PROJ issue
```

## Known Issues and Solutions

### Issue Categories and Solutions

#### 1. **Resource Path Resolution Issues**
**Symptoms**: Missing UI files, gradients not loading, preview databases not found
**Root Cause**: Incorrect `get_resource_path()` implementation
**Solution**: Use the complete path resolution function provided above

#### 2. **Preview Icon Creation Failures** 
**Symptoms**: "Failed to create Preview icon from selection", CRS errors
**Root Cause**: Missing PROJ database in bundle
**Solution**: Include PROJ data in spec file as shown above

#### 3. **Working Directory Problems**
**Symptoms**: "Read-only file system" errors, export failures, temp file creation issues
**Root Cause**: Bundle runs with working directory set to root (/)
**Solution**: Ensure `dem_assembly_system.py` uses `temp_dem_location: str = "system"`

#### 4. **Missing Dependencies**
**Symptoms**: Import errors, "module not found", functionality failures
**Root Cause**: Missing packages in hiddenimports
**Solution**: Add all required modules to hiddenimports list in spec file

#### 5. **Initialization Order Problems**
**Symptoms**: Blank preview area, features not working at startup
**Root Cause**: Dependencies initialized in wrong order
**Solution**: Follow the correct initialization order shown above

#### 6. **First-Run Setup Failures**
**Symptoms**: No sample data, empty user directory, startup errors
**Root Cause**: Resource path resolution or first-run logic issues
**Solution**: Verify `get_resource_path()` handles exact directory matches correctly

## Troubleshooting Guide

### Debug Process

1. **Check Console Output**:
   ```bash
   ./dist/TopoToImage.app/Contents/MacOS/TopoToImage
   ```
   Look for specific error messages to identify the issue category.

2. **Verify Bundle Structure**:
   ```bash
   ls -la dist/TopoToImage.app/Contents/Resources/
   find dist/TopoToImage.app -name "proj.db"
   find dist/TopoToImage.app -name "*.ui"
   ```

3. **Test Resource Access**:
   ```bash
   # Check if PROJ data is accessible
   ls -la dist/TopoToImage.app/Contents/Resources/rasterio/proj_data/
   
   # Check if all preview databases are included
   ls -la dist/TopoToImage.app/Contents/Resources/preview_icon_databases/
   ```

### Common Error Messages and Solutions

| Error Message | Root Cause | Solution |
|---------------|------------|----------|
| `UI file not found` | Missing UI files in spec | Add UI files to `datas` section |
| `Cannot find proj.db` | Missing PROJ data | Add rasterio/proj_data to spec |
| `Read-only file system` | Working directory issue | Fix `temp_dem_location` setting |
| `Key file generation failed` | Missing reportlab | Add reportlab to hiddenimports |
| `Failed to create Preview icon` | CRS/PROJ database issue | Ensure PROJ data is included |
| Import errors for local modules | Missing application modules | Add all src files to datas section |
| Export elevation database returns empty string | QFileDialog cancel handling issue | Check for empty string, not just None |

## Debugging Bundled Applications

### Overview
Debugging bundled applications differs significantly from debugging development code. The bundle runs in a restricted environment with different file paths and permissions. This section covers strategies learned through real-world debugging sessions.

### 1. Debug Logging Configuration

**CRITICAL**: Set appropriate logging level for production bundles.

```python
# In topotoimage.py - Main entry point
import logging

# For PRODUCTION bundles - use INFO level
logging.basicConfig(
    level=logging.INFO,  # NOT logging.DEBUG
    format='%(levelname)s: %(message)s'
)

# For DEBUG bundles only - use DEBUG level
# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(levelname)s: %(message)s'
# )
```

**Why this matters:**
- DEBUG level can generate 16,000+ lines per operation
- Creates huge log files that slow down the application
- Makes it impossible to find actual errors in the noise
- INFO level logs only essential information

### 2. File Dialog Issues in Bundled Apps

**Symptom**: File dialogs return empty string `""` instead of `None` when user cancels

**Root Cause**: QFileDialog behavior differs between development and bundled environments

**Correct Implementation**:
```python
# BAD - Only checks for None
output_path = QFileDialog.getSaveFileName(...)
if output_path:  # Empty string is truthy!
    # This runs even when user cancelled

# GOOD - Checks for both None and empty string
output_path = QFileDialog.getSaveFileName(...)
if output_path and output_path.strip():  # Handles both None and ""
    # Only runs when user actually selected a file
```

**Files to check:**
- `src/dem_assembly_system.py:712` (single-file export)
- `src/main_window_qt_designer.py:3463` (multi-file export)
- Any other file dialog handling code

### 3. File Dialog Default Paths

**Issue**: File dialogs opening in wrong locations (root directory, system folders)

**Solution**: Always use home directory as default:
```python
import os

# BAD - Uses current working directory (could be /)
output_path = QFileDialog.getSaveFileName(self, "Save File", "", "...")

# GOOD - Uses home directory
default_path = os.path.expanduser('~')
output_path = QFileDialog.getSaveFileName(self, "Save File", default_path, "...")
```

### 4. Systematic Debugging Approach

When a feature doesn't work in the bundle but works in development:

**Step 1: Enable console output**
```bash
# Don't just double-click the app - run from terminal
./dist/TopoToImage.app/Contents/MacOS/TopoToImage
```

**Step 2: Reproduce the issue**
- Perform the exact action that fails
- Watch console output carefully
- Look for Python exceptions, not just warnings

**Step 3: Identify the failure point**
- Note the last successful operation before failure
- Look for file path issues (wrong paths, missing files)
- Check for permission errors (read-only locations)

**Step 4: Compare development vs bundle behavior**
```python
# Add temporary debug prints to identify environment
import sys
print(f"Running in bundle: {hasattr(sys, '_MEIPASS')}")
print(f"Current working directory: {os.getcwd()}")
print(f"Home directory: {Path.home()}")
```

**Step 5: Fix and verify**
- Make the fix in source code
- Rebuild bundle: `pyinstaller topotoimage.spec`
- Test the specific feature again
- Verify console shows expected behavior

### 5. Common Bundle-Specific Bugs

#### Export Elevation Database Not Working

**Symptoms:**
- Feature works in development
- Fails silently in bundle
- Console shows no error messages
- Function returns immediately without doing anything

**Debugging Process:**
```python
# Add strategic debug prints
def export_elevation_database(self):
    print("DEBUG: Export function called")

    output_path = QFileDialog.getSaveFileName(...)
    print(f"DEBUG: Dialog returned: '{output_path}'")

    if output_path:
        print(f"DEBUG: Path check passed")
        # Export code...
    else:
        print(f"DEBUG: Path check failed")
```

**Common Findings:**
- `output_path` is `""` (empty string) when user cancels, not `None`
- Empty string passes the `if output_path:` check
- Function proceeds with empty path, causing silent failure

**Fix:**
```python
# Change from:
if output_path:

# To:
if output_path and output_path.strip():
```

### 6. Excessive Debug Output

**Symptom**: Bundle is slow, generates huge log files

**Root Cause**: logging.DEBUG level in production

**Investigation**:
```bash
# Check log file size
ls -lh ~/TopoToImage_Debug/dem_assembly_debug.log

# Count log lines
wc -l ~/TopoToImage_Debug/dem_assembly_debug.log

# If you see 16,000+ lines for one export, DEBUG level is enabled
```

**Fix**:
```python
# In topotoimage.py
logging.basicConfig(
    level=logging.INFO,  # Change from DEBUG to INFO
    format='%(levelname)s: %(message)s'
)
```

### 7. Testing Strategy for Bundled Apps

**Create a testing checklist for every bundle:**

1. **Basic Launch**
   - [ ] App starts without errors
   - [ ] Main window displays
   - [ ] No missing file warnings

2. **File Dialogs**
   - [ ] Open file dialog works
   - [ ] Save file dialog works
   - [ ] Cancel doesn't cause errors
   - [ ] Default paths are sensible (not root)

3. **Export Functions**
   - [ ] Image export works
   - [ ] Elevation database export works
   - [ ] Key file generation works
   - [ ] Scale settings are respected

4. **Performance**
   - [ ] Operations complete in reasonable time
   - [ ] No excessive logging
   - [ ] Disk space usage is reasonable

### 8. Release Package Testing

Before creating final DMG for release:

**Full Test Protocol:**
```bash
# 1. Clean build
rm -rf dist/ build/
pyinstaller topotoimage.spec

# 2. Test from terminal (see all output)
./dist/TopoToImage.app/Contents/MacOS/TopoToImage

# 3. Test every major feature
#    - Load database
#    - Generate preview
#    - Export image
#    - Export elevation database
#    - Generate key file
#    - Open dialogs (gradient editor, HLS adjustment)

# 4. Test as user would (double-click)
open dist/TopoToImage.app
#    - Verify first-run experience
#    - Test all features again
#    - Check for any unexpected behavior

# 5. Check log files
ls -lh ~/TopoToImage_Debug/
# Should be minimal or empty for INFO logging
```

### 9. Lessons Learned - File Dialog Best Practices

**Summary of today's debugging session:**

**Problem**: Export elevation database feature worked in development but failed silently in bundle.

**Investigation Process:**
1. Noticed feature did nothing when clicked
2. Added debug prints to trace execution
3. Found QFileDialog.getSaveFileName() returned empty string when cancelled
4. Discovered `if output_path:` check passed for empty string
5. Function proceeded with empty path, failing silently

**Root Cause**: Inconsistent QFileDialog behavior between environments
- Development: Returns `None` on cancel
- Bundle: Returns `""` (empty string) on cancel

**Solution Applied**:
```python
# Updated both locations:
# src/dem_assembly_system.py:712
# src/main_window_qt_designer.py:3463

# From:
if output_path:

# To:
if output_path and output_path.strip():
```

**Prevention**: Always check file dialog returns for both `None` and empty string:
```python
path = QFileDialog.getSaveFileName(...)
if path and path.strip():  # Handles both None and ""
    # Safe to proceed
```

## Maintenance and Updates

### For Future Development

**When making changes to the terminal version:**

1. **Test thoroughly in development mode first**
2. **Update the spec file if you add new dependencies or resource files**
3. **Follow the established build process**:
   ```bash
   rm -rf dist/ build/
   pyinstaller topotoimage.spec
   ```
4. **Test the bundle with the same verification checklist**

**Adding New Dependencies:**
- Add new Python packages to `hiddenimports` in the spec file
- Include any new data files in the `datas` section
- Test both development and bundle modes

**Adding New Resource Files:**
- Add new assets to the appropriate section in `datas`
- Update `get_resource_path()` if new resource types are introduced
- Verify path resolution works in both modes

### Success Metrics

A successful bundle should have:
- **Size**: ~180-200MB (depending on included resources)
- **All features functional**: Preview creation, exports, dialog windows, legend generation
- **No console errors** during normal operation
- **Identical behavior** to terminal version
- **Platform**: macOS (universal or architecture-specific)

## Final Bundle Specifications

### Expected Results
- **Bundle Size**: ~180-200MB
- **Startup Time**: 3-5 seconds on modern hardware
- **Memory Usage**: 100-200MB during normal operation
- **Dependencies**: All Python packages self-contained
- **Platform Support**: macOS 10.14+ (depending on Python version)

### Distribution Readiness
The bundle created by this process is ready for:
- ✅ Local distribution and testing
- ✅ Sharing with other Mac users
- ✅ Basic macOS compatibility
- ⚠️ For App Store or wide distribution, additional code signing may be required

## Historical Context

This guide represents the culmination of multiple development phases:

- **Phase 0**: Critical pre-bundle preparations and resource path resolution
- **Phase 1**: Initial PyInstaller bundle creation and dependency management
- **Phase 2**: UI file inclusion and gradient system fixes
- **Phase 3**: Preview icon system corrections and initialization order fixes
- **Phase 4**: PROJ database inclusion and CRS functionality restoration
- **Phase 5**: Production debugging and file dialog handling fixes
  - Fixed export elevation database feature (QFileDialog empty string vs None)
  - Optimized debug logging for production (INFO vs DEBUG level)
  - Improved file dialog default paths (home directory instead of root)
  - Documented systematic debugging approach for bundled applications

All known issues have been identified and resolved. Following this guide should produce a fully functional TopoToImage bundle without the trial-and-error process of the original development.

---

**Note**: This guide supersedes all previous bundle creation documentation and incorporates lessons learned through extensive testing and debugging. For any issues not covered here, refer to the console output and use the systematic debugging approach outlined above.