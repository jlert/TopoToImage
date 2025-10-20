# TopoToImage - Claude Code Project Context

## Project Overview

TopoToImage is a professional terrain visualization application for macOS that creates beautiful shaded relief maps from digital elevation models (DEMs). The application is built with Python and PyQt6, and distributed as a standalone macOS application bundle.

**Current Version**: v4.0.0-beta.3
**License**: MIT
**Author**: Joseph Lertola
**Repository**: https://github.com/jlert/TopoToImage

## Project Structure

```
TopoToImage/
├── src/                          # Source code
│   ├── main_window_qt_designer.py    # Main application window
│   ├── dem_assembly_system.py        # DEM assembly and processing
│   ├── preview_window.py             # Preview window with progress
│   ├── shaded_relief_renderer.py     # Terrain rendering engine
│   ├── version.py                    # Version management
│   └── ...
├── ui/                           # Qt Designer UI files
├── assets/                       # Application resources
│   └── icon.icns                     # macOS application icon
├── docs/                         # Documentation
│   ├── USER_GUIDE.md                 # Comprehensive user guide
│   ├── INSTALLATION.md               # Installation instructions
│   ├── COMPLETE_BUNDLE_CREATION_GUIDE.md  # PyInstaller bundling guide
│   └── ELEVATION_DATA_SOURCES.md     # Data sources guide
├── sample_data/                  # Sample elevation data for testing
├── dist/                         # Build output (gitignored)
│   └── TopoToImage.app              # Bundled macOS application
├── build/                        # Build artifacts (gitignored)
├── topotoimage.py                # Main entry point
├── topotoimage.spec              # PyInstaller specification
├── requirements.txt              # Python dependencies
├── generate_user_guide_pdf_improved.py  # PDF generation script
└── generate_combined_readme_pdf.py      # README PDF generation script
```

## Key Technical Details

### Technology Stack
- **Language**: Python 3.11+
- **GUI Framework**: PyQt6
- **Bundling**: PyInstaller (for macOS .app creation)
- **Geospatial**: GDAL/OGR, rasterio
- **Image Processing**: NumPy, Pillow
- **PDF Generation**: ReportLab

### Application Architecture
- **Main Window**: `main_window_qt_designer.py` - handles UI and user interactions
- **DEM Assembly**: `dem_assembly_system.py` - manages elevation data loading and processing
- **Rendering Engine**: `shaded_relief_renderer.py` - creates shaded relief visualizations
- **Preview System**: `preview_window.py` - real-time preview with progress tracking

## Development Phases

### Phase 1: Core Functionality (Early Development)
- Basic DEM loading and visualization
- Single-file GeoTIFF support
- Simple hillshade rendering

### Phase 2: Advanced Features
- Multi-file database support
- Multiple shading methods (slope, aspect, curvature)
- Custom color gradients
- Export capabilities

### Phase 3: Bundle Creation and Distribution
- PyInstaller configuration
- macOS code signing considerations
- DMG creation for releases
- Sample data integration

### Phase 4: User Experience Improvements
- Interactive preview window
- Real-time parameter adjustments
- Progress indicators
- Error handling and user feedback

### Phase 5: Production Debugging and File Dialog Fixes (Current)
- Fixed export elevation database feature (QFileDialog empty string vs None handling)
- Optimized debug logging for production (INFO vs DEBUG level)
- Improved file dialog default paths (home directory instead of root)
- Documented systematic debugging approach for bundled applications
- PDF generation improvements (spacing, formatting, image aspect ratios)

## Critical Bundled Application Issues

### QFileDialog Behavior Differences
**Problem**: File dialogs behave differently in bundled apps vs development
- **Development**: Returns `None` when user cancels
- **Bundle**: Returns `""` (empty string) when user cancels

**Solution**: Always check for both conditions:
```python
if output_path and output_path.strip():
    # Process file
```

**Affected files**:
- `src/dem_assembly_system.py:712` (export elevation database)
- `src/main_window_qt_designer.py:3463` (multi-file database export)

### Debug Logging in Production
**Problem**: DEBUG level logging generates 16,000+ lines per operation
- Creates huge log files
- Slows down application performance
- Difficult to find actual issues

**Solution**: Use INFO level for production builds
```python
# topotoimage.py:63
logging.basicConfig(
    level=logging.INFO,  # Not DEBUG
    format='%(levelname)s: %(message)s'
)
```

### File Dialog Default Paths
**Best Practice**: Always provide sensible default paths
```python
default_path = os.path.expanduser('~')
output_path = QFileDialog.getSaveFileName(
    self, "Save File", default_path, "GeoTIFF Files (*.tif)"
)
```

## Building and Release Process

### Building the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Build with PyInstaller
pyinstaller topotoimage.spec

# Result: dist/TopoToImage.app
```

### Creating Release Package
1. Create staging folder with version number
2. Copy TopoToImage.app from dist/
3. Copy sample_data/ folder
4. Generate PDFs:
   - User Guide: `python generate_user_guide_pdf_improved.py`
   - README: `python generate_combined_readme_pdf.py`
5. Copy Elevation_Data_Sources.pdf
6. Create DMG: `hdiutil create -volname "TopoToImage v4.0.0-beta.3" -srcfolder staging_folder -ov -format UDZO output.dmg`

### Release Contents
- **TopoToImage.app** - Main application bundle
- **sample_data/** - Sample global elevation data for testing
- **TopoToImage_User_Guide.pdf** - Complete user guide (~13 MB, includes images)
- **TopoToImage_README.pdf** - Installation and quick start guide
- **Elevation_Data_Sources.pdf** - Guide to finding elevation data worldwide

## PDF Generation

### User Guide PDF
Script: `generate_user_guide_pdf_improved.py`

**Key features**:
- Converts `docs/USER_GUIDE.md` to PDF
- Preserves image aspect ratios using PIL
- Creates clickable table of contents with internal links
- Dark, readable heading colors
- Proper code block formatting
- Optimized spacing (reduced from initial version)

**Critical settings**:
```python
# Heading colors (dark for readability)
heading1_style.textColor = colors.HexColor('#2C3E50')  # Dark blue-gray
heading2_style.textColor = colors.HexColor('#34495E')

# Spacing (tight to minimize pages)
body_style.leading = 12  # Line height
body_style.spaceAfter = 2  # Space after paragraphs

# Image aspect ratio preservation
aspect_ratio = img_width / img_height
img_display_width = min(max_width, 6*inch)
img_display_height = img_display_width / aspect_ratio
```

### README PDF
Script: `generate_combined_readme_pdf.py`

**Content**:
- Installation instructions (including Gatekeeper bypass)
- Package contents
- Quick start guide
- What's new in current version
- Troubleshooting
- Feature overview

## Common Issues and Solutions

### "TopoToImage is damaged and can't be opened"
macOS Gatekeeper blocking unsigned app.

**Solution**:
```bash
xattr -cr /Applications/TopoToImage.app
```
Then right-click → Open (first time only)

### Export Functions Not Working in Bundle
Check QFileDialog return value handling (see "Critical Bundled Application Issues" above)

### Excessive Log Files
Check logging level in `topotoimage.py` - should be INFO for production

### PDF Images Distorted
Use PIL to get actual dimensions and maintain aspect ratio:
```python
with PILImage.open(img_path) as pil_img:
    img_width, img_height = pil_img.size
    aspect_ratio = img_width / img_height
```

### PDF Too Many Pages
Reduce spacing values in ParagraphStyle definitions:
- `spaceBefore` and `spaceAfter` in heading styles
- `leading` and `spaceAfter` in body styles
- Spacer elements throughout
- Replace `PageBreak()` with `Spacer(1, 0.2*inch)` between sections

## Testing Checklist

### Before Release
- [ ] Test in development mode
- [ ] Build bundle with PyInstaller
- [ ] Test all features in bundled app:
  - [ ] Load single-file database
  - [ ] Load multi-file database
  - [ ] Generate preview
  - [ ] Export image (PNG, JPEG, TIFF)
  - [ ] Export GeoTIFF
  - [ ] Export elevation database (single file)
  - [ ] Export elevation database (multi-file)
- [ ] Check log output (should be minimal with INFO level)
- [ ] Verify file dialogs work correctly (cancel returns empty string)
- [ ] Test on clean macOS system (Gatekeeper bypass)

### PDF Generation
- [ ] Generate User Guide PDF
- [ ] Verify all images display with correct proportions
- [ ] Test table of contents links
- [ ] Check heading colors (should be dark/readable)
- [ ] Verify code blocks display properly
- [ ] Generate README PDF
- [ ] Review both PDFs for spacing and layout

## Documentation

### For Users
- **docs/USER_GUIDE.md** - Comprehensive guide with screenshots
- **docs/INSTALLATION.md** - Installation instructions
- **docs/ELEVATION_DATA_SOURCES.md** - Where to find elevation data

### For Developers
- **docs/COMPLETE_BUNDLE_CREATION_GUIDE.md** - Complete PyInstaller bundling guide
  - Environment setup
  - PyInstaller configuration
  - Debugging bundled applications
  - Common issues and solutions
  - File dialog best practices

## Version Management

Version information is centralized in `src/version.py`:

```python
VERSION = "4.0.0-beta.3"
APP_NAME = "TopoToImage"

def get_version_string(include_v_prefix=True):
    """Returns version string, e.g., 'v4.0.0-beta.3' or '4.0.0-beta.3'"""

def get_app_name_with_version():
    """Returns app name with version, e.g., 'TopoToImage 4.0.0-beta.3'"""
```

**Update process**:
1. Update VERSION in `src/version.py`
2. Update PDF generation scripts (output paths and version strings)
3. Update GitHub release tag
4. Update release notes

## Lessons Learned

### Debugging Bundled Applications
1. **Always test in both environments** - Development and bundled app behavior can differ significantly
2. **File dialogs are different** - QFileDialog returns None in dev, empty string in bundle
3. **Logging strategy matters** - DEBUG in development, INFO in production
4. **Default paths improve UX** - Always provide sensible defaults (home directory, not root)

### PDF Generation
1. **Image aspect ratios** - Always use PIL to get actual dimensions, calculate display size to maintain proportions
2. **Spacing accumulates** - Small reductions in spacing values across the document make a big difference
3. **PageBreak vs Spacer** - PageBreak can create unwanted blank pages; Spacer is more controlled
4. **Color readability** - Light gray headings (#95A5A6) are hard to read; use dark colors (#2C3E50)
5. **Code blocks** - Use Preformatted, not Paragraph, for proper monospace formatting

### Release Process
1. **Staging folder is essential** - Assemble everything first, review before creating DMG
2. **Automate what you can** - PDF generation scripts save time and ensure consistency
3. **Test on clean system** - Your development machine has different permissions than user machines
4. **Document everything** - Bundle creation guide has saved countless hours

## Contact and Support

- **GitHub Issues**: https://github.com/jlert/TopoToImage/issues
- **Releases**: https://github.com/jlert/TopoToImage/releases

## Notes for Future Claude Sessions

### Quick Context
This is a mature macOS application in beta testing. The core functionality is stable. Most recent work has focused on:
- Fixing production bugs (file dialogs, logging)
- Improving release process (PDF generation, DMG creation)
- Documentation (bundle creation guide, debugging guide)

### Common Requests
- **PDF regeneration**: Use existing scripts, adjust spacing if needed
- **Bundle creation**: Follow docs/COMPLETE_BUNDLE_CREATION_GUIDE.md
- **Bug fixes**: Check if it's a bundled app issue (file dialogs, logging)
- **Release creation**: Staging folder → generate PDFs → create DMG → update GitHub

### Things to Watch Out For
- QFileDialog empty string vs None
- Logging level (DEBUG vs INFO)
- File dialog default paths
- Image aspect ratios in PDFs
- Spacing in PDF generation (tight but readable)

### Project Status
- **Current**: v4.0.0-beta.3 released
- **Next**: Gather user feedback, fix bugs, prepare for v4.0.0 final release
- **Future**: Potential features include batch processing, additional shading methods, Windows/Linux support
