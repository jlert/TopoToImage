# Elevation Data Sources for TopoToImage 4.0

A comprehensive guide to finding and downloading Digital Elevation Model (DEM) data for use with TopoToImage 4.0.

## Supported Formats

TopoToImage 4.0 supports these elevation data formats:
- **BIL** (.dem, .bil) - Band Interleaved by Line format
- **GeoTIFF** (.tif, .tiff) - Geographic Tagged Image File Format
- **GTOPO30** (.dem) - Global 30 arc-second elevation dataset

## Global Coverage Data Sources

### 1. GMTED2010 (Recommended for Global Coverage - Newer & Higher Resolution)
**Best for: Modern global terrain visualization, continental mapping**

- **Source**: [USGS Earth Explorer](https://earthexplorer.usgs.gov) / [GMTED2010 Homepage](https://www.usgs.gov/coastal-changes-and-impacts/gmted2010)
- **Resolution**: Multiple options:
  - 7.5 arc-seconds (~250m) - **4x better than GTOPO30**
  - 15 arc-seconds (~500m) - **2x better than GTOPO30** 
  - 30 arc-seconds (~1km) - Same as GTOPO30 but newer data
- **Coverage**: Global (84°N to 56°S latitude)
- **Format**: GeoTIFF (.tif), BIL (.bil)
- **Data Quality**: **Significantly improved over GTOPO30** - newer sources, better void-filling
- **Release**: 2010 (vs GTOPO30's 1990s data)

**Seven Statistical Products Available:**
Each tile includes 6-7 different elevation products with specific use cases:

1. **MEA (Mean)** - `gmted_mea075.tif` ⭐ **RECOMMENDED FOR TOPOTOIMAGE**
   - Average elevation within each grid cell
   - Best overall terrain representation for general mapping
   - Most commonly used for visualization applications

2. **MED (Median)** - `gmted_med075.tif`
   - Middle value of elevation measurements
   - Less affected by elevation outliers than mean
   - Good for mixed terrain characteristics

3. **MIN (Minimum)** - `gmted_min075.tif`
   - Lowest elevation value in each grid cell
   - Useful for drainage analysis and valley identification
   - Good for flood modeling applications

4. **MAX (Maximum)** - `gmted_max075.tif`
   - Highest elevation value in each grid cell
   - Excellent for identifying peaks and ridges
   - Useful for watershed analysis and line-of-sight calculations

5. **STD (Standard Deviation)** - `gmted_std075.tif`
   - Measures terrain roughness/elevation variation
   - Higher values = more rugged terrain
   - Lower values = flatter terrain
   - Excellent for terrain complexity analysis

6. **DSC (Systematic Subsample)** - `gmted_dsc075.tif`
   - Systematically selected elevation points
   - Representative terrain sampling
   - Good for general terrain modeling

7. **Breakline Emphasis** - Available for specialized terrain feature preservation

**Download Instructions:**
1. Visit [USGS Earth Explorer](https://earthexplorer.usgs.gov)
2. Register for free account
3. Search for "GMTED2010"
4. Choose resolution: 7.5", 15", or 30" arc-seconds
5. Select tiles for your area of interest
6. Download will include multiple .tif files - **use MEA (mean) for TopoToImage**

### 2. GTOPO30 (Legacy Global Coverage)
**Best for: Historical compatibility, older workflow reproduction**

- **Source**: [USGS Earth Explorer](https://earthexplorer.usgs.gov)
- **Resolution**: 30 arc-seconds (~1km at equator)
- **Coverage**: Complete global coverage
- **Format**: BIL (.dem files)
- **File Size**: ~12GB for complete global dataset
- **Coordinate System**: WGS84 Geographic (decimal degrees)
- **Tile Structure**: 50° × 40° tiles (e.g., gt30e020n40.dem)
- **Note**: **Consider GMTED2010 instead** - same resolution but newer, higher quality data

**Download Instructions:**
1. Visit [USGS Earth Explorer](https://earthexplorer.usgs.gov)
2. Register for free account
3. Search for "GTOPO30"
4. Select your area of interest or download full global dataset
5. Download includes: .dem (data), .hdr (header), .prj (projection), .stx (statistics)

### 2. SRTM (Shuttle Radar Topography Mission)
**Best for: High-resolution regional mapping between 60°N-60°S**

- **Source**: [NASA Earthdata](https://earthdata.nasa.gov)
- **Resolution**: 1 arc-second (~30m) or 3 arc-second (~90m)
- **Coverage**: 60°N to 60°S latitude (no polar regions)
- **Format**: GeoTIFF (.tif) or BIL (.bil)
- **File Size**: Varies by region (~25-50MB per 1° tile)
- **Coordinate System**: WGS84 Geographic
- **Tile Structure**: 1° × 1° tiles

**Download Instructions:**
1. Visit [NASA Earthdata](https://earthdata.nasa.gov)
2. Register for free NASA account
3. Browse to "SRTM Digital Elevation Data"
4. Choose SRTM 1-Arc Second or 3-Arc Second Global
5. Download individual tiles for your area of interest

### 3. ASTER GDEM (Advanced Spaceborne Thermal Emission)
**Best for: Detailed regional studies, mountain areas**

- **Source**: [NASA Earthdata](https://earthdata.nasa.gov) or [USGS Earth Explorer](https://earthexplorer.usgs.gov)
- **Resolution**: 1 arc-second (~30m)
- **Coverage**: 83°N to 83°S latitude
- **Format**: GeoTIFF (.tif)
- **File Size**: ~25MB per 1° tile
- **Coordinate System**: WGS84 Geographic
- **Quality**: Good detail, some artifacts in water areas

## Regional High-Resolution Sources

### 4. USGS National Elevation Dataset (NED) - United States
**Best for: Detailed US terrain mapping**

- **Source**: [USGS National Map](https://apps.nationalmap.gov/downloader/)
- **Resolution**: 1/3 arc-second (~10m), 1 arc-second (~30m)
- **Coverage**: United States only
- **Format**: GeoTIFF (.tif)
- **Coordinate System**: NAD83 Geographic
- **Quality**: Highest quality for US areas

### 5. CDEM (Canadian Digital Elevation Model)
**Best for: Canadian terrain mapping**

- **Source**: [Natural Resources Canada](https://open.canada.ca/data/en/dataset/7f245e4d-76c2-4caa-951a-45d1d2051333)
- **Resolution**: Various (0.75 arc-second to 3 arc-second)
- **Coverage**: Canada only
- **Format**: GeoTIFF (.tif)
- **Quality**: High quality, regularly updated

### 6. EU-DEM (European Digital Elevation Model)
**Best for: European terrain mapping**

- **Source**: [Copernicus Land Monitoring Service](https://land.copernicus.eu/imagery-in-situ/eu-dem)
- **Resolution**: 1 arc-second (~25m)
- **Coverage**: European Union + surrounding areas
- **Format**: GeoTIFF (.tif)
- **Quality**: Very high quality, seamless coverage

### 7. ODP1 (Open Data Portal - European Data)
**Best for: High-resolution Western European terrain**

- **Source**: [sonny.4lima.de](http://sonny.4lima.de) (Compiled European elevation data)
- **Resolution**: 1 arc-second (~30m)
- **Coverage**: Western Europe and Iceland
- **Format**: Various (processed data)
- **Quality**: Compiled from various European sources
- **Note**: Part of GPS Visualizer's elevation services

## Specialized and Commercial Sources

### 8. OpenTopography
**Best for: Research-grade, high-resolution lidar data**

- **Source**: [OpenTopography.org](https://opentopography.org)
- **Resolution**: Sub-meter to 30m depending on dataset
- **Coverage**: Selected areas worldwide
- **Format**: Various including GeoTIFF
- **Cost**: Free for research/education, registration required

### 9. GEBCO (General Bathymetric Chart of the Oceans)
**Best for: Ocean depth data, underwater terrain**

- **Source**: [GEBCO.net](https://www.gebco.net)
- **Resolution**: 15 arc-second (~450m)
- **Coverage**: Global ocean floor + land elevation
- **Format**: GeoTIFF (.tif)
- **Specialty**: Combines bathymetry with terrestrial elevation

### 10. SRTM30+ (Global 1km DEM with Bathymetry)
**Best for: Global mapping equivalent to GTOPO30 but with ocean floor data**

- **Source**: [NOAA Data Catalog](https://catalog.data.gov/dataset/srtm30-global-1-km-digital-elevation-model-dem-version-11-land-surface) / [PacIOOS](https://www.pacioos.hawaii.edu/metadata/srtm30plus_v11_land.html)
- **Resolution**: 30 arc-seconds (~1km) - same as GTOPO30
- **Coverage**: Complete global coverage (land + ocean floor)
- **Format**: NetCDF, GeoTIFF available through ERDDAP servers
- **Data Components**: 
  - Land: SRTM-derived elevation data (GTOPO30 for polar regions)
  - Ocean: Smith & Sandwell bathymetry with high-resolution additions
- **Versions**: Version 11 (current), Version 6.0 (older)
- **Specialty**: Combines SRTM/GTOPO30 land data with comprehensive ocean bathymetry

### 11. ETOPO (Earth Topography and Ocean Bathymetry)
**Best for: High-resolution ocean floor mapping, global relief**

- **Source**: [NOAA National Centers for Environmental Information](https://www.ncei.noaa.gov/products/etopo-global-relief-model)
- **Resolution**: Multiple options - ETOPO 2022 (15 arc-second), ETOPO1 (1 arc-minute)
- **Coverage**: Global land and ocean floor elevation
- **Format**: GeoTIFF (.tif), NetCDF
- **Data Range**: ~-11,000m (ocean trenches) to +8,850m (Mount Everest)
- **Specialty**: NOAA's premier global relief dataset, combines land topography with ocean bathymetry
- **Quality**: High-quality bathymetry data, regularly updated with latest surveys

## Quick Start Recommendations

### For Beginners
1. **Start with sample data** (included with TopoToImage)
   - Location: `assets/sample_data/`
   - Perfect for learning the software

### For Regional Work
1. **SRTM data** from NASA Earthdata
   - High resolution (30m)
   - Easy to download
   - Good quality

### For Global Projects
1. **GMTED2010** from USGS Earth Explorer ⭐ **RECOMMENDED**
   - **Best modern global dataset**
   - Multiple resolutions (250m, 500m, 1km)
   - 2010 data quality vs 1990s GTOPO30
   - Available in GeoTIFF format

2. **SRTM30+** from NOAA (if you want ocean floor data)
   - Same resolution as GTOPO30 (~1km)
   - Includes ocean bathymetry
   - Global land + sea floor coverage

3. **GTOPO30** from USGS Earth Explorer (legacy option)
   - Complete world coverage including full polar regions
   - Consider GMTED2010 instead for most applications

### For Professional/Research Use
1. **National datasets** (NED, CDEM, EU-DEM)
   - Highest available resolution for specific countries
   - Best accuracy and quality
   - Regular updates

## File Organization Tips

### Recommended Directory Structure
```
~/elevation_data/
├── GTOPO30/
│   ├── gt30w180n90.dem
│   ├── gt30w180n90.hdr
│   └── ...
├── SRTM/
│   ├── n40_w075_1arc_v3.tif
│   └── ...
├── regional/
│   ├── US_NED/
│   ├── Canada_CDEM/
│   └── ...
└── sample_data/
    └── test_dem.tif
```

### Loading in TopoToImage 4.0
1. **File → Open DEM File...** - Load individual files
2. **File → Open Database Folder...** - Load entire directories
3. **Recent Databases** - Quick access to previously used datasets

## Data Quality Considerations

### GMTED2010
- ✅ **Best overall global dataset** - newer, higher quality than GTOPO30
- ✅ Multiple resolution options (250m, 500m, 1km)
- ✅ Modern data sources (2010 vs 1990s)
- ✅ Superior void-filling and processing techniques
- ✅ Available in both GeoTIFF and BIL formats
- ⚠️ Slightly smaller coverage area than GTOPO30 (84°N to 56°S vs full polar)

### GTOPO30 (Legacy)
- ✅ Global coverage including full polar regions
- ✅ Consistent quality, time-tested
- ⚠️ **Outdated** - replaced by GMTED2010 for most applications
- ⚠️ Lower resolution (1km only)
- ⚠️ Based on 1990s data

### SRTM
- ✅ High resolution (30m)
- ✅ Good accuracy
- ⚠️ No coverage above 60°N/below 60°S
- ⚠️ Some gaps in original data

### ASTER GDEM
- ✅ High resolution (30m)
- ✅ Near-global coverage
- ⚠️ Some artifacts over water
- ⚠️ Cloud contamination possible

### National Datasets
- ✅ Highest quality and resolution
- ✅ Regular updates
- ⚠️ Limited to specific countries
- ⚠️ Varying coordinate systems

### SRTM30+, GEBCO & ETOPO (Ocean Floor Data)
- ✅ Unique ocean floor visualization capability
- ✅ Seamless land-to-ocean transitions
- ✅ Global coverage including polar regions
- ✅ Dramatic depth visualization (trenches, ridges, continental shelves)
- ✅ **SRTM30+**: Uses familiar GTOPO30/SRTM land data with bathymetry
- ⚠️ Lower resolution than land-only datasets
- ⚠️ Large elevation range requires careful gradient design
- ⚠️ **SRTM30+**: Primarily available in NetCDF format (may require conversion)

## Coordinate System Requirements

**✅ Supported by TopoToImage 4.0:**
- WGS84 Geographic (decimal degrees)
- NAD83 Geographic (decimal degrees)
- NAD27 Geographic (decimal degrees)

**❌ Not Supported:**
- UTM (Universal Transverse Mercator)
- State Plane coordinates
- Web Mercator
- Any projected coordinate system using linear units

**Note**: If your data is in a projected coordinate system, you'll need to reproject it to geographic coordinates using GIS software like QGIS (free) before using it with TopoToImage.

## Legal and Usage Considerations

### Public Domain Data
- GTOPO30, SRTM, ASTER GDEM: Free for any use
- US NED: Public domain within US
- Most government datasets: Free for public use

### Attribution Requirements
- NASA/USGS datasets: Attribution appreciated but not required
- ASTER GDEM: Credit to NASA/METI required
- OpenTopography: Check individual dataset requirements

### Commercial Use
- Most sources listed here are free for commercial use
- Check specific dataset licenses for commercial applications
- Consider professional data sources for critical applications

## Getting Help

### Data Download Issues
- Most sites require free registration
- Large downloads may need download managers
- Contact data providers' support for access issues

### Format Compatibility
- Ensure data is in geographic coordinates (lat/lon)
- Verify file extensions (.dem, .bil, .tif, .tiff)
- Check that header files (.hdr) exist for BIL format data

### TopoToImage 4.0 Support
- Check SUPPORTED_FORMATS.md for technical details
- Test with sample data first
- Use File → Open DEM File to verify compatibility

---

*This guide covers the most commonly used and freely available elevation data sources. For specialized applications or regions, additional sources may be available through national mapping agencies or commercial providers.*