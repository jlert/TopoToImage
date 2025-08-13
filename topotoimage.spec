# -*- mode: python ; coding: utf-8 -*-
"""
TopoToImage PyInstaller Specification File

Created based on Phase 0 bundle preparation work.
This spec file bundles all necessary resources while ensuring
proper separation of bundled (read-only) and user-writable data.
"""

import sys
from pathlib import Path

# Get the project root directory
project_root = Path.cwd()

# Define data files to include in the bundle
# These are read-only resources that get bundled with the application
datas = [
    # UI files
    ('ui/main_window_complete.ui', 'ui'),
    
    # Application icons
    ('assets/icons/TopoToImage.icns', 'icons'),
    
    # Maps and backgrounds
    ('assets/maps/default_background_map.svg', 'maps'),
    
    # Default gradients (templates for user customization)
    ('assets/gradients/gradients.json', 'gradients'),
    
    # Sample data for first-run experience
    ('assets/sample_data/Gtopo30_reduced_2160x1080.tif', 'sample_data'),
    
    # Preview icon databases for cycling functionality
    ('assets/preview_icon_databases/pr01_fixed.tif', 'preview_icon_databases'),
    ('assets/preview_icon_databases/pr05_fixed.tif', 'preview_icon_databases'),
    ('assets/preview_icon_databases/pr06_shadow_test.tif', 'preview_icon_databases'),
    ('assets/preview_icon_databases/preview_icon_10.tif', 'preview_icon_databases'),
    
    # Application modules that need to be included as data
    ('src/version.py', 'src'),
]

# Hidden imports - modules that PyInstaller might miss
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
    
    # GDAL
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
    
    # Image processing
    'PIL',
    'PIL.Image',
    'PIL.ImageQt',
    
    # Standard library modules that might be missed
    'json',
    'pathlib',
    'shutil',
    'datetime',
    'typing',
    
    # Our application modules
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