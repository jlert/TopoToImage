# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Add data files and resources
added_files = [
    ('assets/gradients', 'assets/gradients'),
    ('assets/maps', 'assets/maps'), 
    ('assets/icons', 'assets/icons'),
    ('assets/sample_data', 'assets/sample_data'),
    ('ui', 'ui'),
]

a = Analysis(
    ['topotoimage.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'PyQt6.QtSvg',
        'rasterio',
        'rasterio.crs',
        'rasterio._shim',
        'rasterio.control',
        'rasterio.coords',
        'rasterio.warp',
        'fiona',
        'fiona.crs',
        'shapely',
        'shapely.geometry',
        'packaging',
        'packaging.version',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TopoToImage',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipped_data,
    Tree('src', prefix='src'),
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TopoToImage',
)

app = BUNDLE(
    coll,
    name='TopoToImage.app',
    icon='assets/icons/TopoToImage.icns',
    bundle_identifier='com.topotoimage.app',
    version='4.0.0-beta.1',
    info_plist={
        'CFBundleName': 'TopoToImage',
        'CFBundleDisplayName': 'TopoToImage',
        'CFBundleGetInfoString': 'TopoToImage 4.0.0-beta.1 - Professional terrain visualization',
        'CFBundleIdentifier': 'com.topotoimage.app',
        'CFBundleVersion': '4.0.0-beta.1',
        'CFBundleShortVersionString': '4.0.0-beta.1',
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '10.14',
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'DEM Files',
                'CFBundleTypeIconFile': 'TopoToImage.icns',
                'LSItemContentTypes': ['public.tiff', 'public.data'],
                'CFBundleTypeRole': 'Editor'
            }
        ]
    },
)