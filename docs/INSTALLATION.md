# TopoToImage Installation Guide

## 📦 Installing on macOS

### Important Security Notice

**Why am I seeing a security warning?**

TopoToImage is not code-signed with an Apple Developer certificate ($99/year). This means macOS Gatekeeper will block the application on first launch. This is a normal security feature - the application is safe to use.

### Installation Steps

1. **Download** `TopoToImage-v4.0.0-beta.1-macOS.dmg` from the [Releases page](https://github.com/jlert/TopoToImage/releases)

2. **Open the DMG** by double-clicking it

3. **Drag TopoToImage.app** to your Applications folder (or anywhere you prefer)

4. **First Launch - Bypass Gatekeeper:**

   **Method 1: Right-Click (Recommended)**
   - Right-click (or Control-click) on TopoToImage.app
   - Select "Open" from the menu
   - Click "Open" in the security dialog
   - You only need to do this once - future launches work normally

   **Method 2: System Settings**
   - Try to open TopoToImage.app by double-clicking
   - When the security warning appears, click "Open System Settings"
   - Navigate to **Privacy & Security**
   - Scroll down to the **Security** section
   - Click **"Open Anyway"** next to the TopoToImage message
   - Enter your administrator password if prompted
   - Try launching TopoToImage again

5. **Subsequent Launches:** After the first successful launch, you can open TopoToImage normally by double-clicking

### Troubleshooting

**"TopoToImage is damaged and can't be opened"**

If you see this message, macOS has quarantined the app. Open Terminal and run:
```bash
xattr -cr /Applications/TopoToImage.app
```
Then try Method 1 above.

---

## 🐍 Running from Source

If you prefer to run TopoToImage from source code (or are on Windows/Linux):

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jlert/TopoToImage.git
   cd TopoToImage
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python3 topotoimage.py
   ```

### System Requirements
- **macOS:** 10.13 (High Sierra) or later
- **Windows:** Windows 10 or later
- **Linux:** Most modern distributions with Python 3.8+

---

## 📊 Sample Data

TopoToImage works with Digital Elevation Model (DEM) files. The DMG includes sample data to get you started.

**Supported Formats:**
- GeoTIFF (.tif)
- BIL (Band Interleaved by Line)
- GTOPO30
- SRTM

**Where to Get DEM Data:**
- [USGS Earth Explorer](https://earthexplorer.usgs.gov/) - GTOPO30, SRTM, and more
- [OpenTopography](https://opentopography.org/) - High-resolution lidar data
- Sample data included in the DMG distribution

---

## 🆘 Getting Help

- **Issues:** Report bugs on the [GitHub Issues page](https://github.com/jlert/TopoToImage/issues)
- **Discussions:** Ask questions in [GitHub Discussions](https://github.com/jlert/TopoToImage/discussions)
- **Documentation:** See the main [README](../README.md) for feature documentation

---

## 📝 License

TopoToImage is released under the MIT License. See [LICENSE](../LICENSE) for details.
