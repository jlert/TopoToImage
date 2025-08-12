#!/usr/bin/env python3
"""
TopoToImage Version Information
Centralized version management for the application
"""

# Version components
VERSION_MAJOR = 4
VERSION_MINOR = 0
VERSION_PATCH = 0
VERSION_PRERELEASE = "beta.1"

# Application metadata
APP_NAME = "TopoToImage"
APP_DESCRIPTION = "Professional Digital Elevation Model visualization and cartographic rendering software"

# Build version string
def get_version_string(include_v_prefix=True):
    """
    Get the full version string
    
    Args:
        include_v_prefix: If True, includes 'v' prefix (e.g., 'v4.0.0-beta.1')
                         If False, just version number (e.g., '4.0.0-beta.1')
    
    Returns:
        Version string
    """
    base_version = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"
    
    if VERSION_PRERELEASE:
        full_version = f"{base_version}-{VERSION_PRERELEASE}"
    else:
        full_version = base_version
    
    if include_v_prefix:
        return f"v{full_version}"
    else:
        return full_version

def get_app_name_with_version():
    """Get application name with version (e.g., 'TopoToImage v4.0.0-beta.1')"""
    return f"{APP_NAME} {get_version_string()}"

def get_metadata_created_by():
    """Get the 'created_by' string for metadata files"""
    return f"{APP_NAME} {get_version_string()}"

# Version info dictionary for programmatic access
VERSION_INFO = {
    'major': VERSION_MAJOR,
    'minor': VERSION_MINOR,
    'patch': VERSION_PATCH,
    'prerelease': VERSION_PRERELEASE,
    'string': get_version_string(include_v_prefix=False),
    'string_with_v': get_version_string(include_v_prefix=True),
    'app_name': APP_NAME,
    'description': APP_DESCRIPTION,
    'full_name': get_app_name_with_version()
}

# For compatibility with standard Python versioning
__version__ = get_version_string(include_v_prefix=False)

if __name__ == "__main__":
    # Test the version system
    print(f"Application: {APP_NAME}")
    print(f"Version: {get_version_string()}")
    print(f"Full name: {get_app_name_with_version()}")
    print(f"Metadata: {get_metadata_created_by()}")
    print(f"Python __version__: {__version__}")
    print(f"\nVersion components:")
    print(f"  Major: {VERSION_MAJOR}")
    print(f"  Minor: {VERSION_MINOR}")
    print(f"  Patch: {VERSION_PATCH}")
    print(f"  Prerelease: {VERSION_PRERELEASE}")