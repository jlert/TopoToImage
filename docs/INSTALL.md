# TopoToImage Installation Guide

## System Requirements

### Operating Systems
- **macOS**: 10.14+ (Mojave or later)
- **Windows**: Windows 10/11
- **Linux**: Ubuntu 18.04+, Fedora 32+, or equivalent

### Python Requirements
- **Python**: 3.8 or later
- **pip**: Latest version recommended

### Hardware Requirements
- **RAM**: 4GB minimum, 8GB+ recommended for large datasets
- **Storage**: 100MB for application, additional space for elevation data
- **Display**: 1024x768 minimum resolution

## Installation Methods

### Method 1: macOS Application Bundle (Recommended for Mac)

1. Download the latest DMG from [Releases](https://github.com/yourusername/TopoToImage/releases)
2. Open `TopoToImage-v4.0.0-beta.1-macOS.dmg`
3. Drag `TopoToImage.app` to your Applications folder
4. Launch from Applications or Launchpad

**Note**: You may need to allow the app in System Preferences > Security & Privacy on first launch.

### Method 2: From Source (All Platforms)

#### Step 1: Clone Repository
```bash
git clone https://github.com/yourusername/TopoToImage.git
cd TopoToImage
```

#### Step 2: Install Dependencies
```bash
# Using pip (recommended)
pip install -r requirements.txt

# Or using conda (if you prefer)
conda env create -f environment.yml
conda activate topotoimage
```

#### Step 3: Launch Application
```bash
python topotoimage.py
```

## Dependencies

TopoToImage requires the following Python packages:

```
PyQt6 >= 6.5.0          # GUI framework
numpy >= 1.21.0          # Numerical computing  
Pillow >= 9.0.0          # Image processing
rasterio >= 1.3.0        # Geospatial data I/O
scipy >= 1.7.0           # Scientific computing
packaging >= 21.0        # Version management (for update checker)
```

## Sample Data

The application includes sample elevation data in `assets/sample_data/`:
- `Gtopo30_reduced_2160x1080_map.tif` - Global elevation data for testing

## Troubleshooting

### Common Issues

#### "ModuleNotFoundError: No module named 'PyQt6'"
```bash
pip install PyQt6
```

#### "Could not find or load shared libraries" (Linux)
```bash
# Ubuntu/Debian
sudo apt install python3-pyqt6 libqt6gui6

# Fedora/RHEL
sudo dnf install python3-PyQt6 qt6-qtbase-gui
```

#### Application won't start on macOS
- Right-click the app and select "Open" instead of double-clicking
- Check System Preferences > Security & Privacy for blocked applications

#### "Permission denied" when launching
```bash
chmod +x topotoimage.py
```

### Performance Issues

#### Large dataset processing is slow
- Increase available RAM
- Use smaller geographic selections for testing
- Enable preview mode for faster feedback

#### UI feels sluggish
- Update graphics drivers
- Close other memory-intensive applications
- Try reducing preview resolution in preferences

### Data Issues

#### "Could not read elevation file"
- Verify file format is supported (BIL, GeoTIFF, GTOPO30, SRTM)
- Check file isn't corrupted by opening in another GIS application
- Ensure file permissions allow reading

#### "No elevation data in selected area"
- Verify geographic coordinates are correct
- Check that elevation file covers your selected region
- Try the included sample data to test functionality

## Getting Elevation Data

See [DATA_SOURCES.md](DATA_SOURCES.md) for comprehensive information on:
- Free global elevation datasets (GTOPO30, SRTM)
- Regional high-resolution data sources
- Recommended data preparation workflows

## Development Environment

For developers wanting to contribute:

```bash
# Clone with development extras
git clone https://github.com/yourusername/TopoToImage.git
cd TopoToImage

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Run with development logging
python topotoimage.py --debug
```

## Support

- **Bug Reports**: [GitHub Issues](https://github.com/yourusername/TopoToImage/issues)
- **Questions**: [GitHub Discussions](https://github.com/yourusername/TopoToImage/discussions)
- **Documentation**: [docs/](docs/) directory

---

*Having installation issues? Please check our [Troubleshooting Guide](docs/TROUBLESHOOTING.md) or file an issue.*