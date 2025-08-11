# TopoToImage Developer Guide

*Beta release placeholder - comprehensive development documentation coming in v4.0.0*

## Project Structure

```
TopoToImage/
├── src/                          # Core application code
│   ├── main_window_qt_designer.py    # Main application window
│   ├── terrain_renderer.py           # Core rendering engine
│   ├── gradient_system.py            # Gradient management
│   ├── interactive_color_ramp.py     # Gradient editor widget
│   ├── shadow_methods/               # Shadow calculation algorithms
│   └── ...                          # Additional modules
├── ui/                           # Qt Designer UI files
├── assets/                       # Static resources
├── docs/                         # Documentation
└── topotoimage.py               # Main entry point
```

## Key Modules

### Core Rendering (`terrain_renderer.py`)
- Elevation data processing
- Hillshading calculations  
- Shadow rendering
- Export functionality

### Gradient System (`gradient_system.py`)
- Color mapping algorithms
- QGIS gradient compatibility
- Gradient file I/O

### Shadow Methods (`shadow_methods/`)
- Multiple shadow algorithms
- Performance-optimized implementations
- 360-degree lighting support

## Development Setup

```bash
git clone https://github.com/yourusername/TopoToImage.git
cd TopoToImage
pip install -r requirements.txt

# Run from source
python topotoimage.py

# Run tests (when available)
python -m pytest tests/
```

## Architecture Notes

- **PyQt6** for cross-platform GUI
- **NumPy/SciPy** for numerical processing
- **Rasterio** for geospatial data I/O
- **Modular design** for easy testing and extension

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## API Documentation

*Complete API documentation will be available in the stable release.*

---

*Full developer documentation including API references, architecture details, and contribution guidelines will be provided in the stable 4.0.0 release.*