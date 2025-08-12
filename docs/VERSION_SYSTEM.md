# TopoToImage Version System

## Overview

TopoToImage uses a centralized version management system to ensure consistent version numbers across the entire application.

## Current Version

**TopoToImage v4.0.0-beta.1**

The version follows semantic versioning:
- **Major**: 4 (significant new features or breaking changes)
- **Minor**: 0 (new features, backward compatible)  
- **Patch**: 0 (bug fixes, backward compatible)
- **Prerelease**: beta.1 (beta release)

## How the Version System Works

### Centralized Management
The version is defined in `src/version.py` and automatically used throughout the application:

- **Application startup**: `🗺️ Starting TopoToImage v4.0.0-beta.1...`
- **Database metadata**: `"created_by": "TopoToImage v4.0.0-beta.1"`
- **Application properties**: PyQt application metadata
- **Future exports**: Headers and documentation

### Automatic Consistency
When you create a new multi-file database metadata file, it will automatically include the correct version information. This helps track which version of TopoToImage was used to create different databases.

### Benefits
- **Consistency**: Same version number everywhere
- **Traceability**: Know which version created each database
- **Compatibility**: Future versions can handle databases created by older versions

## Version Information in Metadata

When you create a multi-file database, the metadata will include:

```json
{
  "dataset_info": {
    "created_by": "TopoToImage v4.0.0-beta.1",
    "created_date": "2025-08-11T17:08:55.731463"
  }
}
```

This helps identify:
- Which version created the database
- When it was created
- Compatibility requirements for loading

## Release Notes

Version updates and new features are managed by the project maintainer. Check the project releases for information about new versions and their features.