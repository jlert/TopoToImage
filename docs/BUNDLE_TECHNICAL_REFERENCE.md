# TopoToImage Bundle Technical Reference

## Resource Path Functions Implementation

### Core Functions (in `main_window_qt_designer.py`)

```python
def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller bundled app"""
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle
        return Path(sys._MEIPASS) / relative_path
    else:
        # Running in development - determine correct path based on resource type
        project_root = Path(__file__).parent.parent  # Go up from src/ to project root
        
        # Handle different resource types
        if relative_path.endswith('.ui'):
            return project_root / "ui" / relative_path
        elif relative_path.startswith('maps/') or relative_path == 'maps':
            return project_root / "assets" / relative_path
        elif relative_path.startswith('gradients/') or relative_path == 'gradients.json':
            return project_root / "assets" / "gradients" / relative_path.replace('gradients/', '')
        elif relative_path.startswith('preview_icon_databases/') or relative_path == 'preview_icon_databases':
            return project_root / "assets" / relative_path
        else:
            # Default: assume it's in assets
            return project_root / "assets" / relative_path

def get_writable_data_path(relative_path):
    """Get absolute path to writable data location, works for dev and PyInstaller bundled app"""
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle - use writable home directory location
        data_dir = Path.home() / "TopoToImage_Data"
        data_dir.mkdir(exist_ok=True)
        return data_dir / relative_path
    else:
        # Running in development - use project assets directory (writable)
        project_root = Path(__file__).parent.parent  # Go up from src/ to project root
        return project_root / "assets" / relative_path
```

### Module-Specific Implementations

#### `map_backgrounds.py`
Added duplicate `get_writable_data_path()` function to resolve import dependency:

```python
def get_writable_data_path(relative_path):
    """Get absolute path to writable data location, works for dev and PyInstaller bundled app"""
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle - use writable home directory location
        data_dir = Path.home() / "TopoToImage_Data"
        data_dir.mkdir(exist_ok=True)
        return data_dir / relative_path
    else:
        # Running in development - use project assets directory (writable)
        project_root = Path(__file__).parent.parent  # Go up from src/ to project root
        return project_root / "assets" / relative_path
```

## File Migration Strategy

### Files That Must Be Bundled (Read-Only)
- `ui/main_window_complete.ui` - Main UI definition
- `assets/icons/TopoToImage.icns` - Application icon
- `assets/maps/default_background_map.svg` - Default world map
- `assets/gradients/gradients.json` - Default gradient templates
- `assets/sample_data/Gtopo30_reduced_2160x1080.tif` - Sample terrain database
- `assets/preview_icon_databases/*.tif` - Preview icon databases

### Files That Must Be User-Writable (Home Directory)
- `~/TopoToImage_Data/gradients.json` - User's custom gradients
- `~/TopoToImage_Data/recent_databases.json` - User's recent database list
- `~/TopoToImage_Data/map_backgrounds.json` - User's map background settings
- `~/TopoToImage_Data/.first_run_complete` - First-run completion flag

## First-Run Experience Code

### Detection Logic
```python
def is_first_run(self):
    """Check if this is the first run using a dedicated flag file in home directory"""
    try:
        # Check for flag file in the user's home TopoToImage_Data directory
        user_data_dir = Path.home() / "TopoToImage_Data"
        first_run_flag = user_data_dir / ".first_run_complete"
        
        # If flag file doesn't exist, it's first run
        return not first_run_flag.exists()
            
    except Exception as e:
        print(f"⚠️  Error checking first run status: {e}")
        return False  # Assume not first run to avoid errors
```

### Setup Implementation
```python
def setup_first_run_experience(self):
    """Set up first-run experience with sample data and user directory"""
    try:
        print("🚀 Setting up first-run experience...")
        
        # Always use home directory for first-run, even in development mode
        user_data_dir = Path.home() / "TopoToImage_Data"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created user data directory: {user_data_dir}")
        
        # Create subdirectories
        user_preview_dir = user_data_dir / "preview_icon_databases"
        user_preview_dir.mkdir(exist_ok=True)
        (user_data_dir / "sample_data").mkdir(exist_ok=True)
        
        # Copy preview icon databases
        bundle_preview_dir = get_resource_path("preview_icon_databases")
        if bundle_preview_dir.exists():
            print(f"📋 Copying preview icon databases...")
            copied_count = 0
            for preview_file in bundle_preview_dir.glob("*.tif"):
                user_preview_file = user_preview_dir / preview_file.name
                shutil.copy2(preview_file, user_preview_file)
                copied_count += 1
            print(f"✅ Copied {copied_count} preview databases to user directory")
        
        # Copy gradient files to user directory
        user_gradients_file = user_data_dir / "gradients.json"
        bundle_gradients = get_resource_path("gradients.json")
        if bundle_gradients.exists() and not user_gradients_file.exists():
            print(f"📋 Copying gradient configuration...")
            shutil.copy2(bundle_gradients, user_gradients_file)
            print(f"✅ Gradient configuration copied to user directory")
        
        # Use the correct sample TIF database
        bundle_sample = get_resource_path("sample_data") / "Gtopo30_reduced_2160x1080.tif"
        user_sample = user_data_dir / "sample_data" / "Gtopo30_reduced_2160x1080.tif"
        
        if bundle_sample.exists():
            print(f"📋 Copying sample database: {bundle_sample.name}")
            shutil.copy2(bundle_sample, user_sample)
            
            print(f"✅ Sample database copied to: {user_sample}")
            
            # Load the sample database automatically
            print(f"🔄 Auto-loading sample database...")
            success = self.load_dem_file(str(user_sample))
            
            if success:
                print(f"✅ Successfully loaded sample database")
                welcome_msg = "Welcome to TopoToImage! Sample terrain loaded - you're ready to create beautiful maps!"
                print(f"📢 {welcome_msg}")
                self.status_bar.showMessage(welcome_msg, 8000)
                
                # Add sample database to recent databases so it loads on next run
                from recent_databases import recent_db_manager
                recent_db_manager.add_recent_database(str(user_sample), 'single_file', 'Gtopo30_reduced_2160x1080.tif')
                print(f"📝 Added sample database to recent databases")
                
                # Also ensure recent database file exists in development assets location
                # (since get_writable_data_path points there in development mode)
                dev_recent_db_file = get_writable_data_path("recent_databases.json")
                if not dev_recent_db_file.exists():
                    print(f"📝 Creating recent database file in development assets")
                    recent_db_manager.save_recent_databases()
                
                # Show proper welcome dialog box
                self.show_welcome_dialog()
                
                # Update window title
                self.update_window_title("Gtopo30_reduced_2160x1080.tif - TopoToImage")
                
                # Mark first run as complete (in home directory)
                first_run_flag = user_data_dir / ".first_run_complete"
                first_run_flag.touch()
                print(f"✅ First run setup completed")
                
                return True
                
        return False
        
    except Exception as e:
        print(f"❌ Error setting up first-run experience: {e}")
        import traceback
        traceback.print_exc()
        return False
```

## Bundle Dependencies

### Required Python Packages
- PyQt6 (with all submodules)
- rasterio (for GeoTIFF handling)
- numpy (for data processing)
- Pillow (for image processing)
- matplotlib (for color mapping)

### System Dependencies
- GDAL (included with rasterio)
- PROJ (for coordinate transformations)

## Error Handling Patterns

### Resource Loading
```python
try:
    resource_path = get_resource_path("some_resource.file")
    if resource_path.exists():
        # Use resource
    else:
        # Fallback or error handling
except Exception as e:
    print(f"Error loading resource: {e}")
    # Graceful degradation
```

### User Data Creation
```python
try:
    user_file = get_writable_data_path("config.json")
    user_file.parent.mkdir(parents=True, exist_ok=True)
    # Write to user file
except Exception as e:
    print(f"Error creating user data: {e}")
    # Continue with defaults
```

## Testing Considerations

### Development Testing
1. Test with clean `~/TopoToImage_Data/` (delete directory)
2. Verify first-run experience creates all necessary files
3. Test second run loads recent database correctly
4. Verify resource paths resolve correctly

### Bundle Testing
1. Test on system without Python/development environment
2. Verify all resources are accessible within bundle
3. Test user data directory creation and permissions
4. Verify first-run experience works identically to development

## Known Limitations

1. **macOS Code Signing**: Bundle will need to be signed for distribution
2. **File Permissions**: Bundle must have permission to create `~/TopoToImage_Data/`
3. **GDAL Data**: Rasterio includes GDAL data, but may need explicit inclusion
4. **Large File Size**: Preview databases and sample data increase bundle size

---

*This technical reference documents the current implementation as of Phase 0 completion.*