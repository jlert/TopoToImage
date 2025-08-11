#!/usr/bin/env python3
"""
Preview Window for DEM Visualizer
Displays terrain preview images in a non-modal, scrollable window
"""

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QScrollArea, QPushButton, QProgressBar, QStatusBar,
                            QApplication)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QFont
from PIL import Image
import numpy as np
import time
from nan_aware_interpolation import resize_with_nan_exclusion
from meridian_utils import (
    calculate_longitude_span, 
    map_longitude_to_array_x,
    split_meridian_crossing_bounds
)

# Add current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import the new DEM assembly system
try:
    from dem_assembly_system import DEMAssembler, AssemblyConfig
    from dem_reader import DEMReader
    ASSEMBLY_SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Assembly system not available: {e}")
    ASSEMBLY_SYSTEM_AVAILABLE = False

def get_dev_workspace_log_path(filename: str) -> str:
    """Get path for log file in development workspace"""
    if hasattr(sys, '_MEIPASS'):
        # Running as bundled app - use home directory
        log_dir = Path.home() / "TopoToImage_Debug"
        log_dir.mkdir(exist_ok=True)
        return str(log_dir / filename)
    else:
        # Development mode - use dev-workspace
        project_root = Path(__file__).parent.parent.parent  # Go up from src/ to claude-code/
        dev_workspace = project_root / "topoToimage-dev-workspace" / "debug-logs"
        dev_workspace.mkdir(parents=True, exist_ok=True)
        return str(dev_workspace / filename)

# Preview system configuration flags
class PreviewConfig:
    """Configuration for preview system behavior"""
    USE_LEGACY_PREVIEW = False      # Set to True to use old system instantly
    COMPARE_WITH_LEGACY = False     # Set to True for side-by-side comparison during development
    DEBUG_MODE = True               # Show detailed debug info to user
    LOG_ASSEMBLY_DETAILS = True     # Log assembly process details

class TerrainProgressDialog(QDialog):
    """Small progress dialog shown during terrain generation"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)  # Block interaction with parent
        self.setWindowTitle("Generating Terrain Preview")
        self.setFixedSize(400, 120)  # Small, fixed size
        
        # Remove window controls (can't close during generation)
        try:
            # Try different PyQt6 versions
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        except AttributeError:
            try:
                # Try older PyQt6 syntax
                self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
            except (AttributeError, NameError):
                # If all else fails, just keep the window as-is
                pass
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the compact progress UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Current phase label
        self.phase_label = QLabel("Preparing...")
        self.phase_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.phase_label.font()
        font.setBold(True)
        self.phase_label.setFont(font)
        layout.addWidget(self.phase_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status label (percentage and time info)
        self.status_label = QLabel("0%")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
    def update_progress(self, percentage, phase="Processing"):
        """Update progress display"""
        self.progress_bar.setValue(percentage)
        self.phase_label.setText(phase)
        self.status_label.setText(f"{percentage}%")
        
    def update_status(self, status_text):
        """Update status text (for time estimates, etc.)"""
        self.status_label.setText(status_text)

class PreviewGenerationThread(QThread):
    """Thread for generating preview images without blocking UI"""
    
    progress_updated = pyqtSignal(int, str)  # Progress percentage (0-100), phase name
    status_updated = pyqtSignal(str)     # Status text (time estimates, etc.)
    preview_ready = pyqtSignal(object)   # PIL Image object
    error_occurred = pyqtSignal(str)     # Error message
    elevation_range_detected = pyqtSignal(float, float, str)  # min_elevation, max_elevation, units
    
    def __init__(self, elevation_data, gradient_name, bounds, gradient_manager, terrain_renderer, dem_bounds=None, export_scale=100.0, database_path=None, dem_reader=None, elevation_range_override=None):
        super().__init__()
        self.elevation_data = elevation_data
        self.gradient_name = gradient_name
        self.bounds = bounds  # (west, north, east, south) - user selection
        self.dem_bounds = dem_bounds  # (west, north, east, south) - full DEM bounds
        self.gradient_manager = gradient_manager
        self.terrain_renderer = terrain_renderer
        self.export_scale = export_scale
        self.database_path = database_path  # Path to multi-file database folder
        self.dem_reader = dem_reader  # DEM reader for chunked processing
        self.elevation_range_override = elevation_range_override  # Optional (min_elev, max_elev) from spinboxes
        
        # Initialize assembly system if available
        self.assembler = None
        self.temp_dem_path = None
        
        # TESTING: Set artificial memory limit for chunking tests
        self.TESTING_MEMORY_LIMIT_MB = None  # Set to None for normal operation
        
        if ASSEMBLY_SYSTEM_AVAILABLE and not PreviewConfig.USE_LEGACY_PREVIEW:
            try:
                TESTING_MEMORY_LIMIT_MB = self.TESTING_MEMORY_LIMIT_MB
                
                if TESTING_MEMORY_LIMIT_MB:
                    assembly_config = AssemblyConfig(
                        artificial_memory_limit_mb=TESTING_MEMORY_LIMIT_MB,
                        chunk_size_mb=max(5, TESTING_MEMORY_LIMIT_MB // 3),
                        force_universal_chunking=True,
                        debug_mode=True,
                        log_file=get_dev_workspace_log_path(f"preview_assembly_{TESTING_MEMORY_LIMIT_MB}mb_test.log")
                    )
                    print(f"🧪 Assembly system initialized with {TESTING_MEMORY_LIMIT_MB}MB limit")
                else:
                    assembly_config = AssemblyConfig(
                        force_universal_chunking=True,  # Use Option 2 by default
                        debug_mode=PreviewConfig.DEBUG_MODE,
                        log_file=get_dev_workspace_log_path("preview_assembly_debug.log")
                    )
                    print("✅ Assembly system initialized with Option 2 (Universal Chunking)")
                
                self.assembler = DEMAssembler(assembly_config)
                
            except Exception as e:
                print(f"⚠️ Failed to initialize assembly system: {e}")
                self.assembler = None
        
    def run(self):
        """Generate preview image in background thread"""
        try:
            start_time = time.time()
            self.progress_updated.emit(10, "Initializing")
            
            # Choose preview generation method and track which one was used
            used_assembly_system = False
            
            # Check if we should use assembly system
            should_use_assembly = False
            
            if self.assembler and self.database_path:
                # Multi-file databases always use assembly system
                should_use_assembly = True
            elif self.assembler and self.elevation_data is not None:
                # Single file: check if it's too large for legacy system
                pixels = self.elevation_data.size
                if pixels > 50_000_000:  # 50M pixel limit
                    should_use_assembly = True
                    if PreviewConfig.DEBUG_MODE:
                        print(f"🔄 Large single file detected ({pixels:,} pixels) - using assembly system")
            
            if should_use_assembly:
                # Use new assembly system
                if PreviewConfig.DEBUG_MODE:
                    print("🔧 Using new assembly system for preview generation")
                cropped_elevation_data = self._generate_preview_with_assembly()
                used_assembly_system = True
            else:
                # Use legacy system (small single files)
                if PreviewConfig.DEBUG_MODE:
                    print("🔧 Using legacy system for preview generation")
                cropped_elevation_data = self._generate_preview_legacy()
                used_assembly_system = False
                
            if cropped_elevation_data is None:
                return  # Error already emitted
            
            # Log full dataset info but don't reject based on it yet
            total_pixels = cropped_elevation_data.size
            memory_mb = (total_pixels * 4) / (1024 * 1024)  # Rough estimate
            print(f"📊 Elevation data for preview: {cropped_elevation_data.shape}, {total_pixels:,} pixels, ~{memory_mb:.1f}MB")
                
            self.progress_updated.emit(25, "Loading Data")
            
            # NOTE: Cropping is now handled inside _generate_preview_legacy() and _generate_preview_with_assembly()
            # No additional cropping needed here to avoid duplicate processing
            print(f"📏 Using processed data: {cropped_elevation_data.shape} (cropping handled by generation method)")
            
            # Apply export scale with NaN-aware interpolation (only if scale is different from 100%)
            # Skip this for assembly system since it handles scaling internally
            if not used_assembly_system and self.export_scale < 100.0:
                scale_factor = self.export_scale / 100.0
                original_shape = cropped_elevation_data.shape
                target_height = int(original_shape[0] * scale_factor)
                target_width = int(original_shape[1] * scale_factor)
                
                print(f"📏 Applying {self.export_scale}% scale with NaN-aware interpolation: {original_shape} → ({target_height}, {target_width})")
                
                # Check for NaN values before interpolation
                valid_data_before = np.sum(~np.isnan(cropped_elevation_data))
                print(f"   Valid pixels before scaling: {valid_data_before:,}")
                
                # Use NaN-aware interpolation to properly handle no-data areas
                try:
                    cropped_elevation_data = resize_with_nan_exclusion(
                        cropped_elevation_data, 
                        (target_height, target_width),
                        method='lanczos'
                    )
                    
                    # Validate results
                    valid_data_after = np.sum(~np.isnan(cropped_elevation_data))
                    print(f"✅ NaN-aware interpolation complete: {cropped_elevation_data.shape}")
                    print(f"   Valid pixels after scaling: {valid_data_after:,}")
                    
                    if valid_data_after == 0:
                        raise ValueError("Interpolation resulted in no valid data")
                    
                except Exception as e:
                    # Fallback: simple subsampling (preserves data integrity)
                    print(f"⚠️ NaN-aware interpolation failed ({e}), using simple subsampling")
                    subsample_factor = max(1, int(1.0 / scale_factor))
                    if subsample_factor > 1:
                        cropped_elevation_data = cropped_elevation_data[::subsample_factor, ::subsample_factor]
                        print(f"✅ Simple subsampling complete: {cropped_elevation_data.shape}")
                    else:
                        print(f"⚠️ Scale factor too large for subsampling, using original data")
                    
            elif self.export_scale > 100.0:
                print(f"⚠️ Export scale >100% not supported for preview (would be too large)")
            else:
                print(f"📏 Export scale: {self.export_scale}% (no scaling needed)")
            
            # Now check if the cropped/processed data is still too large
            final_pixels = cropped_elevation_data.size
            final_memory_mb = (final_pixels * 4) / (1024 * 1024)
            print(f"📋 Final data for rendering: {cropped_elevation_data.shape}, {final_pixels:,} pixels, ~{final_memory_mb:.1f}MB")
            
            # Size limit check - reasonable limit for preview generation
            # Assembly system can handle larger areas, so only check for legacy system
            if not used_assembly_system:
                max_pixels = 50_000_000  # 50M pixels max (about 7000x7000)
                if final_pixels > max_pixels:
                    self.error_occurred.emit(f"Selected area too large: {final_pixels:,} pixels. Please select a smaller area (max ~7000x7000 pixels).")
                    return
            else:
                # Assembly system handles its own size limits
                if PreviewConfig.DEBUG_MODE:
                    print(f"✅ Assembly system handled size management: {final_pixels:,} pixels")
            
            self.progress_updated.emit(30, "Preparing Data")
            
            # Get the gradient
            gradient = self.gradient_manager.get_gradient(self.gradient_name)
            if gradient is None:
                self.error_occurred.emit(f"Gradient '{self.gradient_name}' not found")
                return
                
            self.progress_updated.emit(40, "Loading Gradient")
            
            # Show different progress steps based on gradient type
            gradient_type = getattr(gradient, 'gradient_type', 'gradient')
            print(f"🎨 Rendering {gradient_type} gradient: {self.gradient_name}")
            
            # Get gradient information for detailed progress reporting
            gradient = self.gradient_manager.get_gradient(self.gradient_name)
            gradient_type = getattr(gradient, 'gradient_type', 'gradient')
            has_shadows = (hasattr(gradient, 'cast_shadows') and gradient.cast_shadows and 
                          gradient_type in ['shading_and_gradient', 'shading_and_posterized'])
            
            # Define detailed progress callback for real-time updates
            self.current_phase = "Starting"
            self.phase_start_time = time.time()
            
            def terrain_progress_callback(progress, phase=None):
                current_time = time.time()
                
                if phase:
                    # New phase started
                    if hasattr(self, 'current_phase') and self.current_phase != "Starting":
                        phase_time = current_time - self.phase_start_time
                        print(f"✓ {self.current_phase} completed in {phase_time:.1f}s")
                    
                    self.current_phase = phase
                    self.phase_start_time = current_time
                    print(f"🔄 Starting: {phase}")
                
                # Each phase shows 0-100% progress for that specific phase
                ui_progress = int(progress * 100)  # Always 0-100% for current phase
                current_phase_name = self.current_phase if hasattr(self, 'current_phase') else "Processing"
                
                # Emit progress with phase information
                self.progress_updated.emit(ui_progress, current_phase_name)
                
                # Special handling for shadow progress with time estimates
                if phase == "Shadow Calculation" and progress > 0:
                    elapsed = current_time - self.phase_start_time
                    estimated_total = elapsed / progress if progress > 0.05 else elapsed * 20
                    remaining = max(0, estimated_total - elapsed)
                    
                    # Update status with time estimate
                    time_status = f"{ui_progress}% (elapsed: {elapsed:.0f}s, remaining: ~{remaining:.0f}s)"
                    self.status_updated.emit(time_status)
                    
                    print(f"   Shadow progress: {progress*100:.1f}% (elapsed: {elapsed:.0f}s, remaining: ~{remaining:.0f}s)")
                else:
                    # For other phases, just show percentage
                    self.status_updated.emit(f"{ui_progress}%")
            
            print(f"🎨 Starting terrain rendering:")
            print(f"   Gradient type: {gradient_type}")
            print(f"   Has shadows: {has_shadows}")
            print(f"   Data size: {cropped_elevation_data.shape}")
            
            # Determine elevation range to use for rendering
            min_elev_override = None
            max_elev_override = None
            
            if self.elevation_range_override:
                # Use spinbox values when "Scale gradient to maximum and minimum elevation" is selected
                min_elev_override, max_elev_override = self.elevation_range_override
                print(f"📏 Passing elevation range override to terrain renderer: {min_elev_override:.1f}-{max_elev_override:.1f}m")
            else:
                # Detect elevation range from crop area when "Scale gradient to elevation found in crop area" is selected
                detected_range = self._detect_elevation_range_for_rendering(gradient, cropped_elevation_data)
                if detected_range:
                    min_elev_override, max_elev_override = detected_range
                    print(f"📏 Using detected elevation range for terrain rendering: {min_elev_override:.1f}-{max_elev_override:.1f}m")
            
            # Render the terrain image using the full rendering pipeline with detailed progress
            rendered_image = self.terrain_renderer.render_terrain(
                elevation_data=cropped_elevation_data,
                gradient_name=self.gradient_name,
                min_elevation=min_elev_override,
                max_elevation=max_elev_override,
                progress_callback=terrain_progress_callback
            )
            
            self.progress_updated.emit(90, "Finalizing")
            
            # Convert numpy array to PIL Image if needed
            if isinstance(rendered_image, np.ndarray):
                if rendered_image.dtype != np.uint8:
                    rendered_image = (rendered_image * 255).astype(np.uint8)
                
                # Handle different array shapes
                if len(rendered_image.shape) == 2:
                    # Grayscale
                    pil_image = Image.fromarray(rendered_image, mode='L')
                elif len(rendered_image.shape) == 3:
                    if rendered_image.shape[2] == 3:
                        # RGB
                        pil_image = Image.fromarray(rendered_image, mode='RGB')
                    elif rendered_image.shape[2] == 4:
                        # RGBA
                        pil_image = Image.fromarray(rendered_image, mode='RGBA')
                    else:
                        self.error_occurred.emit(f"Unexpected image shape: {rendered_image.shape}")
                        return
                else:
                    self.error_occurred.emit(f"Unexpected image dimensions: {len(rendered_image.shape)}")
                    return
            else:
                pil_image = rendered_image
                
            # Update spinbox values if elevation range was detected during rendering
            self._update_spinboxes_if_needed(gradient, cropped_elevation_data, min_elev_override, max_elev_override)
            
            self.progress_updated.emit(100, "Complete")
            self.preview_ready.emit(pil_image)
            
            # Clean up temporary DEM file if it was created
            self._cleanup_temp_files()
            
        except Exception as e:
            # Clean up on error too
            self._cleanup_temp_files()
            self.error_occurred.emit(f"Error generating preview: {str(e)}")
    
    def _detect_elevation_ranges_if_needed(self, gradient, elevation_data):
        """
        Detect and emit elevation ranges when crop area radio button is selected.
        
        This scans the selected area for min/max elevations and updates the spinboxes for:
        - Any gradient when "Scale gradient to elevation found in crop area" is selected
        - Percent gradients (legacy behavior for backwards compatibility)
        
        If elevation_range_override is provided (from spinboxes), use those values instead.
        """
        try:
            # Check if we have an elevation range override from the main window spinboxes
            if self.elevation_range_override:
                override_min, override_max = self.elevation_range_override
                print(f"📏 Using elevation range override from spinboxes: {override_min:.1f}-{override_max:.1f}m")
                print(f"   (Ignoring crop area elevation range auto-detection)")
                
                # Emit the override values to update the main window controls
                self.elevation_range_detected.emit(override_min, override_max, "meters")
                print(f"✅ Elevation range override applied - signaled to main window")
                return
            
            # If no elevation range override, this means "Scale gradient to elevation found in crop area" is selected
            # We should scan the terrain data and update the spinboxes for ANY gradient type
            gradient_units = getattr(gradient, 'units', 'meters')
            print(f"🔧 No elevation override - scanning crop area for elevation range")
            print(f"   Gradient units: {gradient_units}, will scan terrain data")
            
            # Scan terrain data for elevation range (works for any gradient type)
            gradient_type = getattr(gradient, 'gradient_type', 'gradient')
            print(f"🎯 Auto-detecting elevation range for gradient: {self.gradient_name}")
            print(f"   Gradient type: {gradient_type}")
            print(f"   Gradient units: {gradient_units}")
            
            # Find valid elevation data (exclude NaN values)
            valid_elevations = elevation_data[~np.isnan(elevation_data)]
            
            if len(valid_elevations) == 0:
                print("⚠️ No valid elevation data found in selection area")
                return
            
            # Calculate min/max elevations from the actual data
            detected_min = float(np.min(valid_elevations))
            detected_max = float(np.max(valid_elevations))
            
            print(f"📊 Auto-detected elevation range in selection area:")
            print(f"   Min elevation: {detected_min:.1f}m")
            print(f"   Max elevation: {detected_max:.1f}m")
            print(f"   Valid pixels: {len(valid_elevations):,}")
            
            # Determine the database units (assume meters for now, but this could be enhanced)
            # TODO: This could be enhanced to detect actual database units from DEM metadata
            database_units = "meters"
            
            # Emit the detected elevation range to update the main window controls
            self.elevation_range_detected.emit(detected_min, detected_max, database_units)
            
            print(f"✅ Auto-detection complete - signaled to main window")
            
        except Exception as e:
            print(f"⚠️ Error detecting elevation ranges: {e}")
            # Don't fail the preview generation for this - it's a nice-to-have feature
    
    def _detect_elevation_range_for_rendering(self, gradient, elevation_data):
        """
        Detect elevation range from terrain data for immediate use in rendering.
        Returns (min_elev, max_elev) tuple or None if detection fails.
        """
        try:
            print(f"🔧 Detecting elevation range from crop area for rendering")
            
            # Find valid elevation data (exclude NaN values)
            valid_elevations = elevation_data[~np.isnan(elevation_data)]
            
            if len(valid_elevations) == 0:
                print("⚠️ No valid elevation data found for rendering - using gradient defaults")
                return None
            
            # Calculate min/max elevations from the actual data
            detected_min = float(np.min(valid_elevations))
            detected_max = float(np.max(valid_elevations))
            
            print(f"📊 Detected elevation range for rendering:")
            print(f"   Min elevation: {detected_min:.1f}m")
            print(f"   Max elevation: {detected_max:.1f}m")
            print(f"   Valid pixels: {len(valid_elevations):,}")
            
            return (detected_min, detected_max)
            
        except Exception as e:
            print(f"⚠️ Error detecting elevation range for rendering: {e}")
            return None
    
    def _update_spinboxes_if_needed(self, gradient, elevation_data, min_elev_used, max_elev_used):
        """
        Update spinbox values if elevation range was detected during rendering.
        This ensures the UI reflects the actual values used for rendering.
        """
        try:
            # Only update spinboxes if we detected elevation range (not using spinbox override)
            if not self.elevation_range_override and min_elev_used is not None and max_elev_used is not None:
                print(f"📊 Updating spinboxes with values used for rendering: {min_elev_used:.1f}-{max_elev_used:.1f}m")
                
                # Emit the values to update the main window controls
                self.elevation_range_detected.emit(min_elev_used, max_elev_used, "meters")
                print(f"✅ Spinbox update complete - signaled to main window")
                
        except Exception as e:
            print(f"⚠️ Error updating spinboxes: {e}")
    
    def _crop_elevation_data(self):
        """Crop elevation data to selected bounds, handling prime meridian crossing"""
        # Get the bounds
        dem_west, dem_north, dem_east, dem_south = self.dem_bounds
        sel_west, sel_north, sel_east, sel_south = self.bounds
        
        print(f"🗺️ DEM bounds: W={dem_west}, N={dem_north}, E={dem_east}, S={dem_south}")
        print(f"🔲 Selection bounds: W={sel_west}, N={sel_north}, E={sel_east}, S={sel_south}")
        
        # Check if selection crosses prime meridian
        sel_span = calculate_longitude_span(sel_west, sel_east)
        dem_span = calculate_longitude_span(dem_west, dem_east)
        
        height, width = self.elevation_data.shape
        print(f"📐 Full data dimensions: {height} x {width}")
        
        if sel_span.crosses_meridian and dem_span.crosses_meridian:
            # Both selection and DEM cross meridian - handle complex case
            return self._crop_meridian_crossing_both(sel_west, sel_north, sel_east, sel_south)
        elif sel_span.crosses_meridian and not dem_span.crosses_meridian:
            # Selection crosses meridian but DEM doesn't - handle split selection
            return self._crop_meridian_crossing_selection_only(sel_west, sel_north, sel_east, sel_south)
        elif not sel_span.crosses_meridian and dem_span.crosses_meridian:
            # DEM crosses meridian but selection doesn't - use meridian-aware coordinate mapping
            return self._crop_meridian_crossing_dem_only(sel_west, sel_north, sel_east, sel_south)
        else:
            # Neither crosses meridian - use original logic
            return self._crop_simple(sel_west, sel_north, sel_east, sel_south)
    
    def _crop_simple(self, sel_west: float, sel_north: float, sel_east: float, sel_south: float):
        """Simple crop without meridian crossing"""
        dem_west, dem_north, dem_east, dem_south = self.dem_bounds
        height, width = self.elevation_data.shape
        
        # Convert geographic bounds to pixel coordinates
        x_min = int((sel_west - dem_west) / (dem_east - dem_west) * width)
        x_max = int((sel_east - dem_west) / (dem_east - dem_west) * width)
        y_min = int((dem_north - sel_north) / (dem_north - dem_south) * height)
        y_max = int((dem_north - sel_south) / (dem_north - dem_south) * height)
        
        print(f"🧮 Simple crop coords: x={x_min}-{x_max}, y={y_min}-{y_max}")
        
        # Clamp to valid ranges
        x_min = max(0, min(x_min, width - 1))
        x_max = max(x_min + 1, min(x_max, width))
        y_min = max(0, min(y_min, height - 1))
        y_max = max(y_min + 1, min(y_max, height))
        
        print(f"✂️ Clamped coords: x={x_min}-{x_max}, y={y_min}-{y_max}")
        
        if x_max <= x_min or y_max <= y_min:
            raise ValueError("Invalid selection bounds - results in zero or negative crop size")
        
        return self.elevation_data[y_min:y_max, x_min:x_max]
    
    def _crop_simple_meridian_aware(self, sel_west: float, sel_north: float, sel_east: float, sel_south: float):
        """Simple crop using meridian-aware coordinate mapping for 360° DEM databases"""
        dem_west, dem_north, dem_east, dem_south = self.dem_bounds
        height, width = self.elevation_data.shape
        
        # Use meridian-aware coordinate mapping for longitude
        x_min = map_longitude_to_array_x(sel_west, dem_west, dem_east, width, crosses_meridian=True)
        x_max = map_longitude_to_array_x(sel_east, dem_west, dem_east, width, crosses_meridian=True)
        
        # Use simple linear mapping for latitude (no meridian issues)
        y_min = int((dem_north - sel_north) / (dem_north - dem_south) * height)
        y_max = int((dem_north - sel_south) / (dem_north - dem_south) * height)
        
        print(f"🧮 Meridian-aware simple crop: x={x_min}-{x_max}, y={y_min}-{y_max}")
        
        # Clamp to valid ranges
        x_min = max(0, min(x_min, width - 1))
        x_max = max(x_min + 1, min(x_max, width))
        y_min = max(0, min(y_min, height - 1))
        y_max = max(y_min + 1, min(y_max, height))
        
        if x_max <= x_min or y_max <= y_min:
            raise ValueError("Invalid selection bounds - results in zero or negative crop size")
        
        return self.elevation_data[y_min:y_max, x_min:x_max]
    
    def _crop_meridian_crossing_dem_only(self, sel_west: float, sel_north: float, sel_east: float, sel_south: float):
        """Crop from DEM that crosses meridian using meridian-aware coordinate mapping"""
        dem_west, dem_north, dem_east, dem_south = self.dem_bounds
        height, width = self.elevation_data.shape
        
        print(f"🌍 DEM crosses meridian, selection doesn't - using meridian-aware mapping")
        
        # Use meridian-aware coordinate mapping
        x_min = map_longitude_to_array_x(sel_west, dem_west, dem_east, width, crosses_meridian=True)
        x_max = map_longitude_to_array_x(sel_east, dem_west, dem_east, width, crosses_meridian=True)
        y_min = int((dem_north - sel_north) / (dem_north - dem_south) * height)
        y_max = int((dem_north - sel_south) / (dem_north - dem_south) * height)
        
        print(f"🧮 Meridian-aware coords: x={x_min}-{x_max}, y={y_min}-{y_max}")
        
        # Clamp to valid ranges
        x_min = max(0, min(x_min, width - 1))
        x_max = max(x_min + 1, min(x_max, width))
        y_min = max(0, min(y_min, height - 1))
        y_max = max(y_min + 1, min(y_max, height))
        
        if x_max <= x_min or y_max <= y_min:
            raise ValueError("Invalid selection bounds - results in zero or negative crop size")
        
        return self.elevation_data[y_min:y_max, x_min:x_max]
    
    def _crop_meridian_crossing_selection_only(self, sel_west: float, sel_north: float, sel_east: float, sel_south: float):
        """Handle selection that crosses meridian by splitting into two regions and stitching"""
        print(f"🌍 Selection crosses meridian - splitting into regions")
        
        # Split selection into non-crossing regions
        regions = split_meridian_crossing_bounds(sel_west, sel_north, sel_east, sel_south)
        
        if len(regions) != 2:
            # Fallback to simple crop if splitting failed
            return self._crop_simple(sel_west, sel_north, sel_east, sel_south)
        
        # Get crops from both regions
        region1_bounds = regions[0]  # Western region
        region2_bounds = regions[1]  # Eastern region
        
        try:
            # Check if DEM spans 360° - if so, use meridian-aware cropping for individual regions
            dem_west, dem_north, dem_east, dem_south = self.dem_bounds
            dem_spans_360 = abs(dem_east - dem_west) >= 359.9
            
            if dem_spans_360:
                print(f"   Using meridian-aware cropping for 360° DEM")
                crop1 = self._crop_simple_meridian_aware(*region1_bounds)
                crop2 = self._crop_simple_meridian_aware(*region2_bounds)
            else:
                print(f"   Using simple cropping for non-360° DEM")
                crop1 = self._crop_simple(*region1_bounds)
                crop2 = self._crop_simple(*region2_bounds)
            
            print(f"   Region 1: {crop1.shape} from {region1_bounds}")
            print(f"   Region 2: {crop2.shape} from {region2_bounds}")
            
            # Stitch the two regions horizontally
            # Region 1 (western) goes on the left, Region 2 (eastern) goes on the right
            stitched = np.concatenate([crop1, crop2], axis=1)
            
            print(f"✅ Stitched meridian-crossing selection: {stitched.shape}")
            return stitched
            
        except Exception as e:
            print(f"⚠️ Failed to crop meridian-crossing selection: {e}")
            # Fallback to meridian-aware crop for 360° DEM
            dem_west, dem_north, dem_east, dem_south = self.dem_bounds
            if abs(dem_east - dem_west) >= 359.9:
                return self._crop_simple_meridian_aware(sel_west, sel_north, sel_east, sel_south)
            else:
                return self._crop_simple(sel_west, sel_north, sel_east, sel_south)
    
    def _crop_meridian_crossing_both(self, sel_west: float, sel_north: float, sel_east: float, sel_south: float):
        """Handle case where both DEM and selection cross meridian (complex case)"""
        print(f"🌍 Both DEM and selection cross meridian - using complex meridian handling")
        
        # Check if DEM spans 360° (most common case for "both cross meridian")
        dem_west, dem_north, dem_east, dem_south = self.dem_bounds
        if abs(dem_east - dem_west) >= 359.9:
            # DEM spans 360°, so treat this as "DEM crosses, selection crosses"
            # Use the selection crossing logic with meridian-aware coordinate mapping
            return self._crop_meridian_crossing_selection_only(sel_west, sel_north, sel_east, sel_south)
        else:
            # True complex case - both have limited spans that cross meridian
            # Fall back to meridian-aware DEM mapping as best effort
            return self._crop_meridian_crossing_dem_only(sel_west, sel_north, sel_east, sel_south)

    def _cleanup_temp_files(self):
        """Clean up temporary DEM files created during assembly"""
        if self.temp_dem_path and self.assembler:
            try:
                self.assembler.cleanup_temp_dem(self.temp_dem_path)
                if PreviewConfig.DEBUG_MODE:
                    print(f"🧹 Cleaned up temporary DEM: {self.temp_dem_path}")
                self.temp_dem_path = None
            except Exception as e:
                if PreviewConfig.DEBUG_MODE:
                    print(f"⚠️ Failed to cleanup temp files: {e}")

    def _generate_preview_with_assembly(self) -> Optional[np.ndarray]:
        """Generate preview using new assembly system with automatic memory management"""
        try:
            if PreviewConfig.DEBUG_MODE:
                print("🔧 Starting new assembly system preview generation")
            
            # Handle both multi-file databases and large single files
            if self.database_path:
                # Multi-file database path
                return self._generate_preview_multifile_assembly()
            elif self.elevation_data is not None:
                # Large single file - use assembly system for memory management
                return self._generate_preview_singlefile_assembly()
            else:
                self.error_occurred.emit("No data source provided for assembly system")
                return None
                
        except Exception as e:
            self.error_occurred.emit(f"Error in assembly preview generation: {str(e)}")
            return None
    
    def _generate_preview_multifile_assembly(self) -> Optional[np.ndarray]:
        """Generate preview from multi-file database using assembly system"""
        try:
            from multi_file_database import MultiFileDatabase
            from pathlib import Path
            
            self.progress_updated.emit(15, "🔍 Discovering tiles...")
            
            db_path = Path(self.database_path)
            if not db_path.exists():
                self.error_occurred.emit(f"Database path does not exist: {db_path}")
                return None
                
            database = MultiFileDatabase(db_path)
            if not database.tiles:
                self.error_occurred.emit(f"No tiles found in database: {db_path}")
                return None
                
            if PreviewConfig.LOG_ASSEMBLY_DETAILS:
                print(f"🗂️ Database: {len(database.tiles)} tiles, type: {database.database_type}")
            
            # Get intersecting tiles
            west, north, east, south = self.bounds
            tiles = database.get_tiles_for_bounds(west, north, east, south)
            
            if not tiles:
                self.error_occurred.emit(f"No tiles found for selected area")
                return None
                
            if PreviewConfig.LOG_ASSEMBLY_DETAILS:
                print(f"📍 Found {len(tiles)} intersecting tiles for bounds: W={west:.2f}°, N={north:.2f}°, E={east:.2f}°, S={south:.2f}°")
            
            # Use assembly system to create single DEM
            def assembly_progress_callback(message):
                """Progress callback for assembly system"""
                self.progress_updated.emit(50, message)
                if PreviewConfig.LOG_ASSEMBLY_DETAILS:
                    print(f"   {message}")
            
            export_scale_fraction = self.export_scale / 100.0
            self.temp_dem_path = self.assembler.assemble_tiles_to_dem(
                tiles=tiles,
                west=west, north=north, east=east, south=south,
                export_scale=export_scale_fraction,
                progress_callback=assembly_progress_callback
            )
            
            if not self.temp_dem_path:
                # Assembly failed - fall back to legacy system
                if PreviewConfig.DEBUG_MODE:
                    print("⚠️ Assembly failed, falling back to legacy system")
                return self._generate_preview_legacy()
                
            self.progress_updated.emit(75, "📖 Loading assembled DEM...")
            
            # Load the assembled DEM
            temp_reader = DEMReader()
            if not temp_reader.load_dem_file(self.temp_dem_path):
                self.error_occurred.emit("Failed to load assembled DEM file")
                return None
                
            elevation_data = temp_reader.load_elevation_data()
            if elevation_data is None:
                self.error_occurred.emit("Failed to load elevation data from assembled DEM")
                return None
                
            if PreviewConfig.LOG_ASSEMBLY_DETAILS:
                print(f"✅ Loaded assembled DEM: {elevation_data.shape} ({self.temp_dem_path})")
                print(f"📐 Final assembly size: {elevation_data.shape[1]}×{elevation_data.shape[0]} pixels")
                export_scale_percent = self.export_scale
                print(f"📐 Export scale applied in assembly: {export_scale_percent}%")
                
            return elevation_data
            
        except Exception as e:
            if PreviewConfig.DEBUG_MODE:
                print(f"❌ Assembly system failed: {e}, falling back to legacy")
                import traceback
                traceback.print_exc()
            # Fall back to legacy system on any error
            return self._generate_preview_legacy()
    
    def _generate_preview_singlefile_assembly(self) -> Optional[np.ndarray]:
        """Generate preview from large single file using assembly system for memory management"""
        try:
            if PreviewConfig.DEBUG_MODE:
                print(f"🔧 Using assembly system for large single file ({self.elevation_data.size:,} pixels)")
            
            self.progress_updated.emit(15, "🔍 Preparing large file processing...")
            
            # Get bounds - use full file if no bounds specified
            if self.bounds:
                west, north, east, south = self.bounds
            else:
                # Use full file bounds (this would need to be passed from the main window)
                # For now, use placeholder values - this should be improved
                west, north, east, south = -180, 90, 180, -90
                if PreviewConfig.DEBUG_MODE:
                    print("⚠️ No bounds specified - using full file (placeholder bounds)")
            
            # Check if we can process this in memory or need chunking
            export_scale_fraction = self.export_scale / 100.0
            estimated_memory_gb = self.assembler.estimate_assembly_memory_gb(west, north, east, south, export_scale_fraction)
            approach = self.assembler.select_assembly_approach(estimated_memory_gb)
            
            if approach == "in_memory":
                # Can process in memory
                if PreviewConfig.DEBUG_MODE:
                    print(f"📦 Processing in memory ({estimated_memory_gb:.1f}GB estimated)")
                
                return self._process_single_file_in_memory(west, north, east, south, export_scale_fraction)
            else:
                # Use chunking approach  
                if PreviewConfig.DEBUG_MODE:
                    print(f"🗂️ Using chunked processing ({estimated_memory_gb:.1f}GB estimated)")
                
                return self._process_single_file_with_chunking(west, north, east, south, export_scale_fraction)
                
        except Exception as e:
            if PreviewConfig.DEBUG_MODE:
                print(f"❌ Single file assembly failed: {e}")
            self.error_occurred.emit(f"Error in single file assembly: {str(e)}")
            return None
    
    def _process_single_file_in_memory(self, west: float, north: float, east: float, south: float,
                                     export_scale: float) -> Optional[np.ndarray]:
        """Process single file in memory with cropping and scaling"""
        try:
            # Crop to selection if bounds are specified
            if self.bounds and self.dem_bounds:
                cropped_data = self._crop_elevation_data()
                if cropped_data is None:
                    return None
            else:
                cropped_data = self.elevation_data
            
            # Apply export scale if needed
            if export_scale != 1.0:
                self.progress_updated.emit(40, f"🔄 Scaling to {export_scale:.1%}...")
                
                try:
                    from scipy import ndimage
                    cropped_data = ndimage.zoom(cropped_data, export_scale, order=1)
                except ImportError:
                    # Fallback: simple subsampling
                    subsample_factor = max(1, int(1.0 / export_scale))
                    if subsample_factor > 1:
                        cropped_data = cropped_data[::subsample_factor, ::subsample_factor]
            
            return cropped_data
            
        except Exception as e:
            if PreviewConfig.DEBUG_MODE:
                print(f"❌ In-memory processing failed: {e}")
            return None
    
    def _process_single_file_with_chunking(self, west: float, north: float, east: float, south: float,
                                         export_scale: float) -> Optional[np.ndarray]:
        """Process single large file using TRUE chunking for memory management"""
        try:
            self.progress_updated.emit(30, "🗂️ Initializing TRUE chunked processing...")
            
            if PreviewConfig.DEBUG_MODE:
                print(f"🗂️ Starting TRUE chunked processing for single file")
                print(f"   Selection: W={west:.3f}, N={north:.3f}, E={east:.3f}, S={south:.3f}")
                print(f"   Export scale: {export_scale:.1%}")
            
            # Calculate memory requirements and chunking strategy
            memory_limit_mb = getattr(self, 'TESTING_MEMORY_LIMIT_MB', None) or 512  # Default 512MB limit
            chunk_size_mb = 50  # 50MB per chunk
            
            # Calculate output dimensions
            deg_width = east - west
            deg_height = north - south
            pixels_per_degree = 120  # Approximate for GTOPO30
            
            total_width = int(deg_width * pixels_per_degree * export_scale)
            total_height = int(deg_height * pixels_per_degree * export_scale)
            
            # Calculate memory requirements (4 bytes per pixel)
            total_memory_mb = (total_width * total_height * 4) / (1024 * 1024)
            
            if PreviewConfig.DEBUG_MODE:
                print(f"📊 Chunking analysis:")
                print(f"   Output dimensions: {total_width}×{total_height}")
                print(f"   Total memory required: {total_memory_mb:.1f}MB")
                print(f"   Memory limit: {memory_limit_mb}MB")
                print(f"   Chunk size: {chunk_size_mb}MB")
            
            # Check if chunking is needed
            if total_memory_mb <= memory_limit_mb:
                if PreviewConfig.DEBUG_MODE:
                    print(f"✅ Data fits in memory - using direct processing")
                return self._process_single_file_in_memory(west, north, east, south, export_scale)
            
            # Calculate chunk grid
            pixels_per_chunk = int((chunk_size_mb * 1024 * 1024) / 4)  # 4 bytes per pixel
            chunk_dimension = int(np.sqrt(pixels_per_chunk))
            
            chunks_x = int(np.ceil(total_width / chunk_dimension))
            chunks_y = int(np.ceil(total_height / chunk_dimension))
            total_chunks = chunks_x * chunks_y
            
            if PreviewConfig.DEBUG_MODE:
                print(f"📦 Chunk configuration:")
                print(f"   Chunk dimension: {chunk_dimension}×{chunk_dimension}")
                print(f"   Chunk grid: {chunks_y}×{chunks_x} = {total_chunks} chunks")
            
            self.progress_updated.emit(40, f"🗂️ Processing {total_chunks} chunks...")
            
            # Create output array
            output_array = np.full((total_height, total_width), np.nan, dtype=np.float32)
            
            # Process each chunk
            for chunk_y in range(chunks_y):
                for chunk_x in range(chunks_x):
                    chunk_num = chunk_y * chunks_x + chunk_x + 1
                    progress = int((chunk_num / total_chunks) * 50) + 40  # 40-90% progress
                    
                    self.progress_updated.emit(progress, f"🗂️ Chunk {chunk_num}/{total_chunks}")
                    
                    # Calculate chunk bounds in pixels
                    start_x = chunk_x * chunk_dimension
                    start_y = chunk_y * chunk_dimension
                    end_x = min(start_x + chunk_dimension, total_width)
                    end_y = min(start_y + chunk_dimension, total_height)
                    
                    # Convert pixel bounds to geographic bounds
                    chunk_west = west + (start_x / total_width) * deg_width
                    chunk_east = west + (end_x / total_width) * deg_width
                    chunk_north = north - (start_y / total_height) * deg_height
                    chunk_south = north - (end_y / total_height) * deg_height
                    
                    if PreviewConfig.DEBUG_MODE and chunk_num <= 3:  # Log first few chunks
                        print(f"   Chunk {chunk_num}: [{start_y}:{end_y}, {start_x}:{end_x}] "
                              f"geo({chunk_west:.3f},{chunk_south:.3f},{chunk_east:.3f},{chunk_north:.3f})")
                    
                    # Load and process this chunk
                    try:
                        # Calculate expected dimensions first
                        expected_height = end_y - start_y
                        expected_width = end_x - start_x
                        
                        chunk_data = self._load_chunk_from_dem(
                            chunk_west, chunk_north, chunk_east, chunk_south,
                            expected_height, expected_width
                        )
                        
                        if chunk_data is not None and chunk_data.size > 0:
                            
                            if chunk_data.shape != (expected_height, expected_width):
                                # Resize using NaN-aware interpolation
                                chunk_data = resize_with_nan_exclusion(
                                    chunk_data, (expected_height, expected_width)
                                )
                            
                            # Place chunk in output array
                            output_array[start_y:end_y, start_x:end_x] = chunk_data
                            
                    except Exception as e:
                        if PreviewConfig.DEBUG_MODE:
                            print(f"   ⚠️ Chunk {chunk_num} failed: {e}")
                        # Leave this chunk as NaN
                        continue
            
            self.progress_updated.emit(90, "🗂️ Finalizing chunked result...")
            
            if PreviewConfig.DEBUG_MODE:
                valid_pixels = np.count_nonzero(~np.isnan(output_array))
                total_pixels = output_array.size
                coverage = (valid_pixels / total_pixels) * 100
                print(f"✅ Chunking complete: {output_array.shape}, {coverage:.1f}% coverage")
            
            return output_array
                
        except Exception as e:
            if PreviewConfig.DEBUG_MODE:
                print(f"❌ Chunked processing failed: {e}")
                import traceback
                traceback.print_exc()
            
            # Fallback to in-memory processing
            return self._process_single_file_in_memory(west, north, east, south, export_scale)
    
    def _load_chunk_from_dem(self, chunk_west: float, chunk_north: float, chunk_east: float, chunk_south: float,
                            expected_height: int, expected_width: int) -> Optional[np.ndarray]:
        """Load a specific chunk from the DEM file using geographic coordinates"""
        try:
            # Get the DEM bounds
            dem_bounds = self.dem_reader.get_geographic_bounds()
            if not dem_bounds:
                return None
            
            dem_west, dem_north, dem_east, dem_south = dem_bounds
            
            # Load the full elevation data if not already loaded
            if not hasattr(self, '_full_elevation_data') or self._full_elevation_data is None:
                self._full_elevation_data = self.dem_reader.load_elevation_data()
                if self._full_elevation_data is None:
                    return None
            
            height, width = self._full_elevation_data.shape
            
            # Convert geographic chunk bounds to pixel coordinates
            x_min = max(0, int((chunk_west - dem_west) / (dem_east - dem_west) * width))
            x_max = min(width, int((chunk_east - dem_west) / (dem_east - dem_west) * width))
            y_min = max(0, int((dem_north - chunk_north) / (dem_north - dem_south) * height))
            y_max = min(height, int((dem_north - chunk_south) / (dem_north - dem_south) * height))
            
            # Ensure we have valid bounds
            if x_min >= x_max or y_min >= y_max:
                return None
            
            # Extract the chunk
            chunk_data = self._full_elevation_data[y_min:y_max, x_min:x_max].copy()
            
            # Resize to expected dimensions if needed
            if chunk_data.shape != (expected_height, expected_width):
                chunk_data = resize_with_nan_exclusion(chunk_data, (expected_height, expected_width))
            
            return chunk_data
            
        except Exception as e:
            if PreviewConfig.DEBUG_MODE:
                print(f"   ⚠️ Failed to load chunk: {e}")
            return None
    
    def _generate_preview_legacy(self) -> Optional[np.ndarray]:
        """Generate preview using legacy system (original method)"""
        try:
            if PreviewConfig.DEBUG_MODE:
                print("🔧 Using legacy preview generation system")
                
            # Handle multi-file database vs single-file elevation data
            if self.elevation_data is None and self.database_path is not None:
                # Multi-file database - use original assembly method
                cropped_elevation_data = self._load_multi_file_database_legacy()
                if cropped_elevation_data is None:
                    return None  # Error already emitted
            elif self.elevation_data is not None:
                # Single-file database - use provided elevation data
                cropped_elevation_data = self.elevation_data
            else:
                self.error_occurred.emit("No elevation data or database path provided")
                return None
                
            # Apply original scaling and cropping logic
            if self.elevation_data is not None and self.dem_bounds and self.bounds:
                try:
                    original_data = cropped_elevation_data
                    cropped_elevation_data = self._crop_elevation_data()
                    if PreviewConfig.DEBUG_MODE:
                        print(f"🔪 Cropped elevation data from {original_data.shape} to {cropped_elevation_data.shape}")
                except Exception as e:
                    if PreviewConfig.DEBUG_MODE:
                        print(f"⚠️ Could not crop elevation data: {e}")
            
            # NOTE: Export scaling is now handled in the run() method to avoid duplicate scaling
            # No scaling applied here - just return the cropped data
            if PreviewConfig.DEBUG_MODE:
                print(f"📏 Skipping scaling in legacy method (handled by main run() method)")
            
            # Check size limits (original logic)
            final_pixels = cropped_elevation_data.size
            max_pixels = 50_000_000  # 50M pixels max
            if final_pixels > max_pixels:
                self.error_occurred.emit(f"Selected area too large: {final_pixels:,} pixels. Please select a smaller area (max ~7000x7000 pixels).")
                return None
                
            return cropped_elevation_data
            
        except Exception as e:
            self.error_occurred.emit(f"Error in legacy preview generation: {str(e)}")
            return None
    
    def _load_multi_file_database_legacy(self) -> Optional[np.ndarray]:
        """Load and assemble tiles from multi-file database for the selected bounds (legacy method)"""
        try:
            from multi_file_database import MultiFileDatabase
            from pathlib import Path
            
            self.progress_updated.emit(15, "Discovering Tiles")
            
            # Create multi-file database instance
            db_path = Path(self.database_path)
            if not db_path.exists():
                self.error_occurred.emit(f"Database path does not exist: {db_path}")
                return None
            
            print(f"🗂️ Loading multi-file database: {db_path}")
            database = MultiFileDatabase(db_path)
            
            if not database.tiles:
                self.error_occurred.emit(f"No tiles found in database: {db_path}")
                return None
                
            print(f"📋 Database info: {len(database.tiles)} tiles, type: {database.database_type}")
            
            self.progress_updated.emit(25, "Finding Intersecting Tiles")
            
            # Get bounds for tile selection
            if not self.bounds:
                self.error_occurred.emit("No selection bounds provided for multi-file database")
                return None
                
            west, north, east, south = self.bounds
            print(f"🎯 Selection bounds: W={west:.2f}°, N={north:.2f}°, E={east:.2f}°, S={south:.2f}°")
            
            # Check for reasonable area size before proceeding
            area_width = abs(east - west) if west <= east else (180 - west) + (east + 180)
            area_height = abs(north - south)
            estimated_pixels = int(area_width * area_height * 120 * 120)  # Rough estimate at 2-arc-minute resolution
            
            if estimated_pixels > 50_000_000:  # 50M pixels
                self.error_occurred.emit(f"Selected area too large: ~{estimated_pixels:,} pixels. Please select a smaller area (< 7000x7000 pixels).")
                return None
            
            self.progress_updated.emit(40, "Assembling Tiles")
            
            # Assemble tiles for the bounds
            assembled_data = database.assemble_tiles_for_bounds(west, north, east, south)
            
            if assembled_data is None:
                self.error_occurred.emit("Failed to assemble tiles for selected area")
                return None
            
            # Check data quality
            valid_pixels = np.sum(~np.isnan(assembled_data))
            total_pixels = assembled_data.size
            coverage_percent = (valid_pixels / total_pixels) * 100 if total_pixels > 0 else 0
            
            print(f"✅ Multi-file assembly complete:")
            print(f"   Data shape: {assembled_data.shape}")
            print(f"   Coverage: {valid_pixels:,}/{total_pixels:,} pixels ({coverage_percent:.1f}%)")
            
            if valid_pixels == 0:
                self.error_occurred.emit("No valid data in selected area - area may be entirely ocean or no-data")
                return None
            
            if coverage_percent < 5:
                print(f"⚠️ Warning: Low data coverage ({coverage_percent:.1f}%) in selected area")
            
            self.progress_updated.emit(50, "Data Assembly Complete")
            return assembled_data
            
        except Exception as e:
            error_msg = f"Error loading multi-file database: {str(e)}"
            print(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)
            return None


class TerrainPreviewWindow(QDialog):
    """Non-modal preview window with scrollable terrain image display"""
    
    # Signal to emit elevation range data back to main window
    elevation_range_detected = pyqtSignal(float, float, str)  # min_elevation, max_elevation, units
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(False)  # Non-modal allows main window interaction
        self.setWindowTitle("Terrain Preview")
        self.resize(400, 300)  # Minimal default size - will be resized intelligently when image loads
        self.hide()  # Start hidden, will be shown when preview is ready
        
        # Keep references for refresh capability
        self.current_dem_file = None
        self.current_gradient_name = None
        self.current_bounds = None
        self.gradient_manager = None
        self.terrain_renderer = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the preview window UI"""
        layout = QVBoxLayout(self)
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Scroll area for the image
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)  # Don't resize widget automatically
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Image label inside scroll area
        self.image_label = QLabel("Generating preview...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid gray; background-color: white;")
        self.image_label.setMinimumSize(400, 300)
        self.image_label.setScaledContents(False)  # Don't scale the image content
        
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)
        
        # Status bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        self.status_bar.showMessage("Ready")
        
    def generate_preview(self, elevation_data, gradient_name, bounds, gradient_manager, terrain_renderer, dem_bounds=None, export_scale=100.0, database_path=None, dem_reader=None, elevation_range_override=None):
        """Generate and display a terrain preview using elevation data or multi-file database
        
        Args:
            elevation_range_override: Optional tuple (min_elev, max_elev) to override auto-detection
                                    Used when "scale to max/min elevation" radio button is active
        """
        try:
            # Create and show progress dialog instead of large preview window
            self.progress_dialog = TerrainProgressDialog(self.parent())
            self.progress_dialog.show()
            
            # Create and start generation thread with elevation data or database path
            self.generation_thread = PreviewGenerationThread(
                elevation_data, gradient_name, bounds, gradient_manager, terrain_renderer, dem_bounds, export_scale, database_path, dem_reader, elevation_range_override
            )
            
            # Set up timeout timer (30 minutes max for shadow calculations)
            self.timeout_timer = QTimer()
            self.timeout_timer.timeout.connect(self.handle_timeout)
            self.timeout_timer.setSingleShot(True)
            self.timeout_timer.start(1800000)  # 30 minutes (1800 seconds)
            
            # Connect thread signals to progress dialog
            self.generation_thread.progress_updated.connect(self.update_progress_dialog)
            self.generation_thread.status_updated.connect(self.update_status_dialog)
            self.generation_thread.preview_ready.connect(self.display_preview)
            self.generation_thread.error_occurred.connect(self.handle_error)
            self.generation_thread.finished.connect(self.cleanup_timeout)
            self.generation_thread.elevation_range_detected.connect(self.handle_elevation_range_detected)
            
            # Start generation
            self.generation_thread.start()
            
        except Exception as e:
            self.handle_error(f"Error starting preview generation: {str(e)}")
    
    def update_progress_dialog(self, percentage, phase):
        """Update progress dialog with phase and percentage"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.update_progress(percentage, phase)
    
    def update_status_dialog(self, status_text):
        """Update progress dialog status text"""
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.update_status(status_text)
    
    def update_progress(self, percentage):
        """Update progress bar (legacy method for compatibility)"""
        self.progress_bar.setValue(percentage)
        
    def handle_elevation_range_detected(self, min_elevation, max_elevation, units):
        """Relay elevation range data to main window"""
        print(f"🔗 Preview window relaying elevation range: {min_elevation:.1f} to {max_elevation:.1f} {units}")
        self.elevation_range_detected.emit(min_elevation, max_elevation, units)
    
    def _resize_window_for_image(self, pixmap):
        """Intelligently resize window to show as much of the image as possible using available screen space"""
        try:
            from PyQt6.QtGui import QGuiApplication
            
            # Get available screen geometry (excluding taskbars, dock, etc.)
            screen = QGuiApplication.primaryScreen()
            if screen is None:
                # Fallback if no screen detected
                print("⚠️ Could not detect screen - using default window size")
                return
            
            available_geometry = screen.availableGeometry()
            screen_width = available_geometry.width()
            screen_height = available_geometry.height()
            
            print(f"📺 Available screen space: {screen_width}×{screen_height}")
            print(f"🖼️ Image size: {pixmap.width()}×{pixmap.height()}")
            
            # Calculate padding for window decorations and controls
            padding_width = 50    # Space for scroll bars and window border
            padding_height = 150  # Space for title bar, status bar, and window border
            
            # Calculate maximum window size that fits on screen
            max_window_width = screen_width - 100   # Leave some margin from screen edge
            max_window_height = screen_height - 100 # Leave some margin from screen edge
            
            # Calculate ideal window size to show the full image
            ideal_window_width = pixmap.width() + padding_width
            ideal_window_height = pixmap.height() + padding_height
            
            # Determine actual window size - use full image size if it fits, otherwise use available space
            if ideal_window_width <= max_window_width and ideal_window_height <= max_window_height:
                # Image fits entirely on screen - size window to show full image
                new_width = ideal_window_width
                new_height = ideal_window_height
                resize_reason = "full image fits on screen"
            else:
                # Image doesn't fit entirely - maximize window size to show as much as possible
                new_width = min(ideal_window_width, max_window_width)
                new_height = min(ideal_window_height, max_window_height)
                resize_reason = "maximizing for large image"
            
            # Apply minimum sizes to ensure usability
            min_width = 400
            min_height = 300
            new_width = max(new_width, min_width)
            new_height = max(new_height, min_height)
            
            print(f"🔧 Resizing window: {new_width}×{new_height} ({resize_reason})")
            
            # Resize the window
            self.resize(new_width, new_height)
            
            # If image is larger than window, inform user about scrolling
            content_width = new_width - padding_width
            content_height = new_height - padding_height
            
            if pixmap.width() > content_width or pixmap.height() > content_height:
                print(f"📜 Image larger than window - scrollbars will be available")
                print(f"   Visible area: {content_width}×{content_height}")
                print(f"   Total image: {pixmap.width()}×{pixmap.height()}")
            else:
                print(f"✅ Full image visible in window")
            
        except Exception as e:
            print(f"⚠️ Error resizing window: {e}")
            # Fallback to original logic
            if pixmap.width() < 800 and pixmap.height() < 600:
                new_width = min(pixmap.width() + 50, 1200)
                new_height = min(pixmap.height() + 150, 900)
                self.resize(new_width, new_height)
    
    def handle_error(self, error_message):
        """Handle preview generation errors"""
        self.cleanup_timeout()
        
        # Close progress dialog if it exists
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
            delattr(self, 'progress_dialog')
        
        # Show the preview window with error message
        self.show()
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Error")
        self.image_label.setText(f"Preview Error:\n{error_message}")
        print(f"❌ Preview error: {error_message}")
    
    def handle_timeout(self):
        """Handle preview generation timeout"""
        print("⏰ Preview generation timed out after 30 minutes")
        if hasattr(self, 'generation_thread') and self.generation_thread.isRunning():
            self.generation_thread.terminate()
            self.generation_thread.wait(5000)  # Wait up to 5 seconds for cleanup
        
        # Close progress dialog if it exists
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.close()
            delattr(self, 'progress_dialog')
        
        # Show the preview window with timeout message
        self.show()
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Timeout")
        self.image_label.setText("Preview Timeout:\nGeneration took over 30 minutes.\nShadow calculations are very slow for large areas.\nTry a smaller area or disable shadows.")
    
    def cleanup_timeout(self):
        """Clean up the timeout timer"""
        if hasattr(self, 'timeout_timer'):
            self.timeout_timer.stop()
    
    def display_preview(self, pil_image):
        """Display the generated preview image"""
        try:
            self.cleanup_timeout()  # Stop timeout timer
            
            # Close progress dialog
            if hasattr(self, 'progress_dialog'):
                self.progress_dialog.close()
                delattr(self, 'progress_dialog')
            
            # Convert PIL Image to QPixmap
            # First convert to RGB if necessary
            if pil_image.mode not in ('RGB', 'RGBA'):
                pil_image = pil_image.convert('RGB')
            
            # Convert to bytes
            image_data = pil_image.tobytes('raw', pil_image.mode)
            
            # Create QPixmap
            if pil_image.mode == 'RGB':
                # Alternative approach for RGB
                from PyQt6.QtGui import QImage
                qimage = QImage(image_data, pil_image.width, pil_image.height, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimage)
            else:
                # RGBA
                from PyQt6.QtGui import QImage
                qimage = QImage(image_data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
                pixmap = QPixmap.fromImage(qimage)
            
            # Display the image
            self.image_label.setPixmap(pixmap)
            self.image_label.resize(pixmap.size())
            
            # Intelligently size window to use available screen space for the image
            self._resize_window_for_image(pixmap)
            
            # Show the preview window now that we have content
            self.show()
            
            # Hide progress bar and update status
            self.progress_bar.setVisible(False)
            self.status_bar.showMessage(f"Preview: {pil_image.width}×{pil_image.height} pixels")
            
            print(f"✅ Preview displayed: {pil_image.width}×{pil_image.height} pixels")
            
        except Exception as e:
            self.handle_error(f"Error displaying preview: {str(e)}")


def test_preview_window():
    """Test the preview window with dummy data"""
    app = QApplication(sys.argv)
    
    window = TerrainPreviewWindow()
    window.show()
    
    # Create a dummy preview image for testing
    test_image = Image.new('RGB', (400, 300), color='lightblue')
    window.display_preview(test_image)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    test_preview_window()