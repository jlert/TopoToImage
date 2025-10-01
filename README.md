# TopoToImage 4.0.0-beta.1

> **Modern recreation of the 1990s Macintosh terrain visualization software**

**⚠️ BETA SOFTWARE**: This is pre-release software under active development. Please report bugs and provide feedback!

## 📥 Download

**macOS Users:** [Download TopoToImage v4.0.0-beta.1 (DMG)](https://github.com/jlert/TopoToImage/releases/latest) - 386 MB

See [Installation Guide](docs/INSTALLATION.md) for setup instructions including how to bypass macOS Gatekeeper.

**Windows/Linux Users:** The application is built with cross-platform libraries (PyQt6, NumPy, GDAL) but has not been tested on these systems. You can try running from source (see Quick Start below). **Testers wanted!** If you successfully run TopoToImage on Windows or Linux, please open an issue to let us know.

## 🐛 Report Issues

Found a bug? [Report it here](https://github.com/jlert/TopoToImage/issues/new) or browse [existing issues](https://github.com/jlert/TopoToImage/issues).

---

TopoToImage recreates the classic cartographic software from the 1990s and used by professional cartographers and Time Magazine. 

## ✨ Key Features

- **Advanced Color Gradients** - Support for 2-64 color gradients
- **Realistic Hillshading** - Configurable light direction  
- **Cast Shadows** - Soft-edge shadows
- **Interactive Gradient Editor** - Drag-and-drop color ramp editing with real-time preview
- **Global Coordinate System** - Support for worldwide elevation data including prime meridian crossing
- **Multi-Format Export** - Professional output to GeoTIFF images, Geocart Image databases, PNG, JPG, and layered PNG images.
- **PDF Key Files** - Automated legend generation with Adobe Illustrator compatibility provides the metadata for the images the program creates
- **Elevation data export** - Export cropped and scaled versions of elevation databases

## 🗺️ Professional Cartographic Output

TopoToImage produces publication-quality terrain visualizations suitable for:
- **Scientific Publications** - High-resolution academic mapping
- **Commercial Cartography** - Professional map production
- **GIS Workflows** - QGIS-compatible GeoTIFF files
- **Design Projects** - Export a series of PNG files to be loaded as layers in photo editing software

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/josephlertola/TopoToImage.git
cd TopoToImage

# Install dependencies
pip install -r requirements.txt

# Launch the application
python topotoimage.py
```

### Basic Usage

1. **Load Elevation Data** - Support for BIL, GeoTIFF, GTOPO30, and SRTM formats
2. **Select Geographic Area** - Interactive map selection with coordinate input including selection across the prime meridian
3. **Choose Color Gradient** - Professional gradients or create custom schemes
4. **Configure Rendering** - Adjust hillshading, shadows, and lighting
5. **Export Results** - Multiple professional formats with georeferencing

**Try the included sample:** The project includes `Gtopo30_reduced_2160x1080.tif` - a global elevation dataset perfect for testing all features.

## 📊 Supported Data Formats

### Input Formats
- **GeoTIFF** - Standard georeferenced TIFF format
- **BIL** - Band Interleaved by Line format
- **DEM** - Same as BIL
- **Single and multi file databases supported**


### Output Formats

Image formats:
- **GeoTIFF Image file** - Georeferenced images for GIS applications
- **Geocart Image database** - Specialized cartographic format
- **PNG image** - Image file
- **JPG image** - Image file
- **Multiple PNG files** - Export Gradient, Hill shading, Shadows, and Elevation as separate PNG files to load as layers in photo editing software
- **PDF Key Files** - Save the metadata for the exported image

Elevation database export:
- **GeoTIFF Elevation database** - Georeferenced images for GIS applications
- **DEM** - Band Interleaved by Line format

## 🎨 Gradient System

The gradient system supports five visualization modes:
- **Shaded Relief** - Pure hillshading without color
- **Gradient** - Color-coded elevation without shading
- **Posterized** - Stepped color bands for contour-like appearance
- **Shading + Gradient** - Combined elevation colors with hillshading
- **Shading + Posterized** - Stepped colors with realistic shading

## 🌍 Global Coverage

TopoToImage handles worldwide elevation data including:
- **Prime Meridian Crossing** - Seamless Pacific Ocean selections
- **Coordinate Systems** - Decimal degrees and DMS formats
- **Large Area Assembly** - Multi-tile stitching across boundaries

## 🛠️ Development

TopoToImage is built with:
- **Python 3.8+** - Modern Python with type hints
- **PyQt6** - Cross-platform GUI framework
- **NumPy/SciPy** - High-performance numerical computing
- **Rasterio** - Geospatial data I/O
- **Pillow** - Image processing and export

## 🎯 Historical Context

TopoToImage 4.0 recreates the terrain visualization capabilities of the original 1990s Macintosh software. The original TopoToImage was:
- **Commercially successful** in the professional cartography market
- **Used by Time Magazine** for geographic illustrations
- **Provided a source for Geocart Image databases** created striking color maps that could be used by Geocart the sophisticated map projection software. No problem.

This modern recreation preserves the original's algorithms.

## 📄 License

Released under the MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

---
