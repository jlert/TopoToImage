# TopoToImage User Guide

**Version 4.0.0-beta.1**

---

## Table of Contents

1. [Overview](#overview)
2. [Elevation Databases](#elevation-databases)
3. [Opening Databases](#opening-databases)
4. [Main Window Interface](#main-window-interface)
5. [Gradient Style Panel](#gradient-style-panel)
6. [Creating Visualizations](#creating-visualizations)
7. [Gradient Editor Window](#gradient-editor-window)

---

## Overview

### What TopoToImage Does

TopoToImage creates colored terrain visualization images from elevation databases. The application imports Digital Elevation Model (DEM) data, applies color gradients based on elevation, and renders professional cartographic output with hillshading and cast shadows.

### Import and Export Workflow

**Import:** Open elevation databases in GeoTIFF or BIL/DEM format (single-file or multi-file)

**Visualize:** Select geographic area, apply color gradients, configure shading and shadows

**Export:**
- **Images:** GeoTIFF, PNG, JPG, PDF with full georeferencing
- **Elevation Databases:** Cropped and/or scaled versions of the source data

The elevation export feature allows you to create smaller, cropped, or reduced-resolution versions of large databases for faster testing or distribution.

---

## Elevation Databases

### What Are Elevation Databases?

Elevation databases are files containing height values for geographic locations. Each pixel in the database represents the elevation (in meters) at a specific latitude/longitude coordinate.

### Supported Formats

**GeoTIFF (.tif, .tiff)**
- Single file containing both elevation data and georeferencing
- 16-bit elevation values
- Industry standard format

**BIL/DEM (.bil, .dem)**
- Requires three files:
  - `.bil` or `.dem` - Elevation data
  - `.hdr` - Header file (dimensions, resolution)
  - `.prj` - Projection file (coordinate system)
- All three files must be present in the same directory

### Where to Get Data

**USGS Earth Explorer** - https://earthexplorer.usgs.gov/
- GTOPO30 (global, 1km resolution)
- SRTM (near-global, 30m-90m resolution)
- NED (US only, 10m-30m resolution)

**OpenTopography** - https://opentopography.org/
- High-resolution lidar data
- Regional datasets

### Single-File vs Multi-File Databases

**Single-File Database**
- One GeoTIFF file or one BIL/DEM file set
- Covers a single geographic area
- Simple to open and use

**Multi-File Database**
- Multiple elevation files in a folder
- Each file (tile) covers adjacent geographic areas
- TopoToImage automatically stitches tiles together for seamless visualization
- Enables continent or world-scale mapping

---

## Opening Databases

### Opening Single-File Databases

**File → Open Database** (or Cmd+O)

1. Navigate to your elevation file
2. Select a GeoTIFF file, or the `.tif`, `.bil`, or `.dem` file from a BIL/DEM set
3. Click Open

The world map displays the database coverage area with a red rectangle. Blue lines show individual tile boundaries for multi-file databases.

### Opening Multi-File Databases

**File → Open Database** (or Cmd+O)

1. Navigate to the folder containing multiple elevation files
2. Select any one of the elevation files in the folder
3. If a `.json` metadata file exists, TopoToImage loads the multi-file database automatically
4. If no `.json` file exists, use "Create Multi-File Database" first (see below)

### Creating Multi-File Databases

**File → Create Multi-File Database**

Use this command when you have multiple elevation tiles in a folder that should work together as one database.

**Requirements:**
- All files must be in the same folder
- Each file must be a valid GeoTIFF or BIL/DEM format
- Files can be in subfolders (each BIL/DEM set in its own subfolder is fine)
- No specific naming convention required - use original filenames from data source

**How It Works:**
1. Select the folder containing your elevation files
2. TopoToImage scans the folder and analyzes each file's:
   - Geographic boundaries (lat/lon coverage)
   - Resolution (pixels per degree)
   - Elevation range
3. A `.json` metadata file is created in the folder with the compiled database information
4. The database is now ready to open as a multi-file database

**Example folder structure:**
```
MyGlobalDatabase/
├── tile_n00e000/
│   ├── data.dem
│   ├── data.hdr
│   └── data.prj
├── tile_n00e010.tif
├── tile_n10e000.tif
└── MyGlobalDatabase.json  ← Created by TopoToImage
```

---

## Main Window Interface

### Map Area

**World Map Display**
- Political boundaries shown for geographic reference
- Default background map (professional SVG)

**Database Coverage**
- Red rectangle shows loaded database boundaries
- Blue lines show individual tile boundaries (multi-file databases only)

**Selection Rectangle**
- Yellow rectangle shows currently selected area for export
- Drag on map to select area
- Adjust with coordinate inputs for precision

### Selection & Coordinates Panel

**Coordinate Input**
- North/South/East/West latitude/longitude fields
- Enter precise coordinates for selection
- Supports decimal degrees

**Selection Tools**
- Select All Database - Sets selection to full database coverage
- Interactive map clicking and dragging

**Geographic Information**
- Real-time coordinate conversion
- Distance calculations
- Area measurements

### Database Info Panel

Shows information about the currently loaded elevation database:

- **Width/Height** - Database dimensions in pixels
- **Pixels per Degree** - Resolution of the data
- **Latitude/Longitude Boundaries** - Geographic coverage (N/S/E/W)
- **File Size** - Storage size of the database
- **Pixel Height** - Geographic distance (in meters or km) of one pixel's height

### Export File Info Panel

Shows information about the image/database that will be exported based on current selection:

- **Width/Height** - Output dimensions in pixels
- **Pixels per Degree** - Output resolution
- **File Size Estimate** - Approximate output file size
- **Pixel Height** - Geographic distance of one pixel in output

This allows you to verify output size before exporting and adjust selection or scaling as needed.

---

## Gradient Style Panel

### Preview Icon Databases

**Purpose:** Small terrain preview thumbnails showing what the currently selected gradient looks like when applied to real elevation data.

**Cycling Through Previews:**
- Double-click any preview icon to cycle through available preview databases
- Shows same gradient on different terrain types
- Helps evaluate gradient effectiveness before applying to full database

**Preview Icon Menu Commands:**

**Create Preview Icon Database**
- Renders current map selection as a new preview database
- Useful for testing gradients on specific terrain in your project

**Delete Preview Icon Database**
- Removes preview databases you no longer need
- First (default) preview cannot be deleted

**Set as Database 1/2/3/4**
- Assigns specific preview databases to cycle positions
- Organizes your most-used terrain types

### Gradient Management Buttons

Eight buttons control gradient creation, editing, and organization:

**New Gradient**
- Opens gradient editor window
- Creates copy of currently selected gradient
- Gradient name shows "_copy" suffix to indicate new gradient will be saved separately

**Edit Gradient**
- Opens gradient editor for currently selected gradient
- Click OK to update gradient with new settings
- Changes affect the existing gradient

**Delete Gradient**
- Removes currently selected gradient from list
- Cannot be undone

**Move Up / Move Down**
- Rearranges gradient position in list
- Affects display order in gradient list

**Sort List**
- Sorts all gradients alphabetically by name
- Useful for organizing large gradient collections

**Save List**
- Exports current gradient list to file
- Saves all gradients and their settings
- Standard file format for sharing gradient collections

**Load List**
- Imports gradients from saved file
- Options:
  - **Append** - Adds loaded gradients to end of current list
  - **Replace** - Replaces entire gradient list with loaded gradients

**Note:** Gradient menu also provides access to these commands.

### Gradient List

**Selection**
- Click gradient name to select
- Selected gradient is used for preview and export
- Preview icons update to show selected gradient

**Organization**
- Use Move Up/Down to manually arrange
- Use Sort List for alphabetical order
- Gradient order is saved with list

### Percent vs Meters Mode

Critical setting that controls how gradients are applied to elevation data.

**Percent Mode (Auto-Scaling)**
- Scans selected area for minimum and maximum elevation
- Scales gradient to fit between these values
- Lowest elevation = bottom gradient color
- Highest elevation = top gradient color
- **Best for:** Areas with unknown elevation range, ensuring full gradient is always visible

**Meters Mode (Fixed Thresholds)**
- Gradient elevation values are explicitly set in meters
- Colors are applied at exact elevation thresholds
- Elevations below gradient minimum use bottom color
- Elevations above gradient maximum use top color
- **Best for:** Precise control, comparing multiple areas at same scale, bathymetric/topographic boundaries

**Example:**
- Gradient set to 0m (bottom) → 100m (top)
- Selected area contains mountains up to 2000m elevation
- **Percent mode:** 0m gets bottom color, 2000m gets top color, gradient scales across full range
- **Meters mode:** 0-100m shows gradient, everything above 100m shows top color

---

## Creating Visualizations

### Preview Button

**Quick Preview Window**
- Renders current selection with current gradient settings
- Opens in separate window
- Fast way to test gradient and shading before full export
- Does not save file - for evaluation only

### Save Image File Button

**Also available:** File → Save Image File (Cmd+S)

**Export Options:**
- **GeoTIFF** - Georeferenced image for GIS applications (QGIS, ArcGIS, etc.)
- **Geocart Image** - Specialized cartographic database format
- **PNG** - Standard image format, high quality
- **JPG** - Compressed image format, smaller file size
- **Multiple PNG Files** - Exports separate layers:
  - Gradient (base colors)
  - Hillshading
  - Shadows
  - Elevation data
  - Ideal for compositing in Photoshop, Illustrator, or other image editors

**PDF Key Files:**
- Automatically generates legend with gradient information
- Adobe Illustrator compatible
- Contains metadata for the exported image

### Export Elevation Database Button

**Purpose:** Create cropped and/or scaled versions of source elevation data

**Cropping:**
- Uses current map selection as crop area
- Extract specific regions from large global databases
- Reduces file size for distribution or faster processing

**Resolution Scaling:**
- Adjust pixels per degree (resolution)
- Create lower-resolution versions for testing
- Reduce file size while maintaining geographic coverage

**Format Options (in Save dialog):**
- **GeoTIFF** - Standard georeferenced format
- **DEM** - BIL format with header and projection files

**Common Uses:**
- Extract country/region from global dataset
- Create test databases at lower resolution
- Prepare data for sharing or distribution
- Focus on specific study areas

---

## Gradient Editor Window

**Access:** Click "New Gradient" or "Edit Gradient" button

The gradient editor provides complete control over terrain visualization appearance.

### Gradient Types

Five visualization modes for different cartographic needs:

**1. Shaded Relief**
- Pure hillshading without color
- Grayscale representation of terrain
- Light and shadow based on surface angles

**2. Colored Shaded Relief**
- Color gradient based on elevation
- Hillshading applied for 3D effect
- Most common cartographic style
- Combines elevation information with terrain texture

**3. Posterized**
- Discrete elevation bands (stepped colors)
- No hillshading
- Hypsometric tint style
- Clear elevation zone visualization

**4. Posterized with Shading**
- Discrete elevation bands with hillshading
- Combines zone clarity with terrain texture
- Professional topographic map style

**5. Posterized with Shading and Shadows**
- Full-featured visualization
- Discrete elevation bands
- Hillshading for surface detail
- Cast shadows for dramatic relief
- Maximum visual information

### Color Ramp Controls

**Interactive Gradient Bar**
- Drag color control points to adjust elevation thresholds
- Click to add new color points
- Right-click to remove points
- 2-64 colors supported

**Color Selection**
- Double-click color point to change color
- Standard color picker interface
- Supports RGB color values

**Elevation Assignment**
- Each color point has elevation value (meters or percent)
- Displayed in gradient editor
- Defines where colors transition

### Shading Options

**Hillshading (Gradient Types 2, 4, 5)**
- **Light Direction** - 360° control (0° = North, 90° = East, etc.)
- **Light Angle** - Altitude of light source above horizon
- **Intensity** - Strength of hillshading effect
- **Exaggeration** - Vertical exaggeration multiplier for dramatic effect

**Azimuth Control:**
- Circular dial for intuitive light direction selection
- Numeric input for precise angles
- Real-time preview updates

### Shadow Options

**Cast Shadows (Gradient Type 5)**
- **Enable Shadows** - Toggle shadow rendering
- **Shadow Direction** - Follows light direction setting
- **Soft Edges** - Anti-aliased shadow boundaries
- **Shadow Length** - Distance shadows extend from terrain
- **Shadow Opacity** - Transparency of shadow overlay

**Shadow Methods:**
- Multiple algorithms available
- Different performance/quality tradeoffs
- Method 2 recommended for production use

### Gradient-Specific Options

**Color Blending**
- Linear interpolation (smooth gradients)
- Step interpolation (hard edges between colors)

**Elevation Mode**
- Matches Percent/Meters mode in main window
- Can be set independently for each gradient

**Naming**
- Descriptive gradient names for organization
- Displayed in gradient list

**QGIS Compatibility**
- Import gradients from QGIS color ramp files
- Export TopoToImage gradients to QGIS format
- Cross-application workflow support

---

## Tips and Workflow

**Starting a New Project:**
1. Open elevation database (single or multi-file)
2. Select geographic area on map
3. Choose gradient from list (or create new)
4. Set Percent/Meters mode
5. Preview to test appearance
6. Adjust gradient, shading, shadows as needed
7. Export image or elevation database

**Testing Gradients:**
- Use preview icons to see gradient on different terrain
- Create preview from your project area for accurate evaluation
- Cycle through previews while adjusting colors

**Managing Large Databases:**
- Create multi-file database from downloaded tiles
- Export smaller regional databases for faster testing
- Use lower resolution for draft visualizations
- Export full resolution for final output

**Organizing Gradients:**
- Save gradient lists by project or theme
- Use descriptive names (e.g., "Alps_Hypsometric", "Ocean_Bathymetry")
- Sort alphabetically for large collections
- Delete unused gradients to reduce clutter

---

**For installation instructions, see [INSTALLATION.md](INSTALLATION.md)**

**For technical details on bundle creation, see [COMPLETE_BUNDLE_CREATION_GUIDE.md](COMPLETE_BUNDLE_CREATION_GUIDE.md)**

**Report issues at:** https://github.com/jlert/TopoToImage/issues
