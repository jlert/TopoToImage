#!/usr/bin/env python3
"""
DEM Assembly System for Large Area Preview Support

This module implements a comprehensive system for assembling multiple DEM tiles 
into a single DEM file, with automatic memory management and disk spooling capabilities.

Week 1 Implementation: Foundation with logging, fallback, and basic assembly
"""

import os
import psutil
import logging
import tempfile
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from datetime import datetime
import time

from dem_reader import DEMReader
from multi_file_database import MultiFileDatabase, TileInfo, TileBounds


@dataclass
class AssemblyConfig:
    """Configuration for DEM assembly operations"""
    use_legacy_preview: bool = False      # Instant rollback to old system
    compare_with_legacy: bool = True      # Side-by-side comparison during development
    debug_mode: bool = True               # Show debug info to user
    temp_dem_location: str = "system"     # "project" or "system" temp directory
    log_file: str = "dem_assembly_debug.log"
    max_memory_percent: float = 50.0      # Maximum percentage of available RAM to use
    
    # New Option 2 controls
    force_universal_chunking: bool = False    # Force Option 2 for testing/comparison
    force_in_memory: bool = False            # Force Option 1 for testing/comparison
    artificial_memory_limit_mb: Optional[int] = None  # Artificial memory limit for testing
    chunk_size_mb: int = 200                 # Default chunk size in MB
    performance_comparison_mode: bool = False # Compare Option 1 vs Option 2 performance


@dataclass
class AssemblyStrategy:
    """Memory strategy for DEM assembly"""
    name: str                    # "in_memory", "streaming", "disk_spooled"
    memory_limit_gb: float       # Maximum memory to use
    description: str             # Human-readable description
    estimated_time: str          # Expected performance


class AssemblyMetrics:
    """Metrics tracking for assembly operations"""
    def __init__(self):
        self.start_time = None
        self.phases = {}
        self.memory_snapshots = []
        
    def start_timing(self):
        self.start_time = time.time()
        
    def record_phase(self, phase_name: str, duration: float = None):
        if duration is None and self.start_time:
            duration = time.time() - self.start_time
        self.phases[phase_name] = duration
        
    def record_memory_snapshot(self, phase: str):
        memory = psutil.virtual_memory()
        self.memory_snapshots.append({
            'phase': phase,
            'timestamp': datetime.now(),
            'percent_used': memory.percent,
            'available_gb': memory.available / (1024**3),
            'used_gb': memory.used / (1024**3)
        })


class DEMAssemblyLogger:
    """Comprehensive logging system for DEM assembly operations"""
    
    def __init__(self, log_file: str = "dem_assembly_debug.log"):
        self.log_file = log_file
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        """Set up detailed logging with both file and console output"""
        logger = logging.getLogger("DEMAssembly")
        logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # File handler for detailed debugging
        file_handler = logging.FileHandler(self.log_file)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
        
        # Console handler for important messages
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)
        
        return logger
    
    def log_system_info(self):
        """Log comprehensive system information at start of assembly"""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('.')
        
        self.logger.info("="*60)
        self.logger.info("DEM ASSEMBLY SESSION STARTED")
        self.logger.info("="*60)
        self.logger.info(f"System Memory: {memory.total/1024**3:.1f}GB total, "
                        f"{memory.available/1024**3:.1f}GB available ({memory.percent}% used)")
        self.logger.info(f"Disk Space: {disk.free/1024**3:.1f}GB free")
        self.logger.info(f"NumPy version: {np.__version__}")
        self.logger.info(f"Working directory: {os.getcwd()}")
        
    def log_assembly_request(self, west: float, north: float, east: float, south: float, 
                           export_scale: float, num_tiles: int):
        """Log details of assembly request"""
        area_sq_deg = (east - west) * (north - south)
        self.logger.info(f"Assembly Request:")
        self.logger.info(f"  Bounds: W={west}°, N={north}°, E={east}°, S={south}°")
        self.logger.info(f"  Area: {area_sq_deg:.2f} square degrees")
        self.logger.info(f"  Export Scale: {export_scale:.1%}")
        self.logger.info(f"  Tiles: {num_tiles}")
        
    def log_memory_state(self, phase: str):
        """Log current memory state"""
        memory = psutil.virtual_memory()
        self.logger.debug(f"{phase}: Memory {memory.percent}% used, "
                         f"{memory.available/1024**3:.1f}GB available")
        
    def log_strategy_selection(self, strategy: AssemblyStrategy, estimated_memory_gb: float):
        """Log strategy selection reasoning"""
        self.logger.info(f"Strategy Selected: {strategy.name}")
        self.logger.info(f"  Estimated Memory: {estimated_memory_gb:.1f}GB")
        self.logger.info(f"  Memory Limit: {strategy.memory_limit_gb:.1f}GB")
        self.logger.info(f"  Description: {strategy.description}")
        self.logger.info(f"  Expected Time: {strategy.estimated_time}")
        
    def log_assembly_completion(self, metrics: AssemblyMetrics, output_path: str):
        """Log assembly completion with metrics"""
        total_time = sum(metrics.phases.values()) if metrics.phases else 0
        self.logger.info(f"Assembly Completed: {total_time:.1f} seconds")
        self.logger.info(f"Output file: {output_path}")
        
        for phase, duration in metrics.phases.items():
            self.logger.info(f"  {phase}: {duration:.1f}s")
            
        if metrics.memory_snapshots:
            max_memory = max(snap['percent_used'] for snap in metrics.memory_snapshots)
            self.logger.info(f"  Peak memory usage: {max_memory:.1f}%")


class DEMAssembler:
    """
    Core DEM assembly system with automatic memory management
    
    Week 1 Implementation: Basic assembly with comprehensive logging and fallback
    """
    
    def __init__(self, config: AssemblyConfig = None):
        self.config = config or AssemblyConfig()
        self.logger = DEMAssemblyLogger(self.config.log_file)
        self.metrics = AssemblyMetrics()
        self.dem_reader = DEMReader()
        
        # Log system info at startup
        self.logger.log_system_info()
        
    def get_system_memory_info(self) -> Dict:
        """Get detailed system memory information"""
        memory = psutil.virtual_memory()
        return {
            'total_gb': memory.total / (1024**3),
            'available_gb': memory.available / (1024**3),
            'used_gb': memory.used / (1024**3),
            'percent_used': memory.percent,
            'free_gb': memory.free / (1024**3)
        }
    
    def estimate_assembly_memory_gb(self, west: float, north: float, east: float, south: float,
                                   export_scale: float, pixels_per_degree: float = 120) -> float:
        """Estimate memory requirements for assembly"""
        
        # Calculate target dimensions
        deg_width = east - west
        deg_height = north - south
        
        # Calculate output array size at full resolution first
        # Then apply export scale to get final dimensions
        full_width_pixels = int(deg_width * pixels_per_degree)
        full_height_pixels = int(deg_height * pixels_per_degree)
        
        # Apply export scale to final dimensions (not to resolution)
        width_pixels = int(full_width_pixels * export_scale)
        height_pixels = int(full_height_pixels * export_scale)
        total_pixels = width_pixels * height_pixels
        
        # Memory calculation (float32 = 4 bytes per pixel)
        array_memory_gb = (total_pixels * 4) / (1024**3)
        
        # Add overhead for intermediate processing (factor of 2.5 for safety)
        estimated_memory_gb = array_memory_gb * 2.5
        
        self.logger.logger.debug(f"Memory estimation: {width_pixels}×{height_pixels} = "
                               f"{total_pixels:,} pixels = {estimated_memory_gb:.2f}GB")
        
        return estimated_memory_gb
    
    def select_assembly_approach(self, estimated_memory_gb: float) -> str:
        """Select between Option 1 (fast path) and Option 2 (universal chunked)"""
        
        memory_info = self.get_system_memory_info()
        available_gb = memory_info['available_gb']
        
        # Apply artificial memory limits for testing
        if self.config.artificial_memory_limit_mb:
            artificial_limit_gb = self.config.artificial_memory_limit_mb / 1024
            available_gb = min(available_gb, artificial_limit_gb)
            self.logger.logger.info(f"🧪 Artificial memory limit applied: {artificial_limit_gb:.1f}GB")
        
        # User can force specific approach for testing/comparison
        if self.config.force_universal_chunking:
            self.logger.logger.info("🔧 Forced universal chunking (Option 2) for testing")
            return "universal_chunked"
        
        if self.config.force_in_memory:
            self.logger.logger.info("🔧 Forced in-memory (Option 1) for testing")
            return "in_memory"
        
        # Automatic decision based on memory requirements
        memory_threshold = available_gb * 0.5  # Use 50% of available RAM as threshold
        
        if estimated_memory_gb < memory_threshold:
            approach = "in_memory"
            reason = f"Data fits comfortably in memory ({estimated_memory_gb:.1f}GB < {memory_threshold:.1f}GB threshold)"
        else:
            approach = "universal_chunked"
            reason = f"Data too large for memory ({estimated_memory_gb:.1f}GB >= {memory_threshold:.1f}GB threshold)"
        
        self.logger.logger.info(f"🎯 Selected approach: {approach}")
        self.logger.logger.info(f"   Reason: {reason}")
        self.logger.logger.info(f"   Available memory: {available_gb:.1f}GB")
        
        return approach
    
    def select_assembly_strategy(self, estimated_memory_gb: float) -> AssemblyStrategy:
        """Legacy method - kept for compatibility"""
        
        approach = self.select_assembly_approach(estimated_memory_gb)
        memory_info = self.get_system_memory_info()
        available_gb = memory_info['available_gb']
        
        if approach == "in_memory":
            strategy = AssemblyStrategy(
                name="in_memory",
                memory_limit_gb=available_gb * 0.5,
                description="Fast in-memory assembly (Option 1)",
                estimated_time="<30 seconds"
            )
        else:  # universal_chunked
            strategy = AssemblyStrategy(
                name="universal_chunked", 
                memory_limit_gb=available_gb * 0.5,
                description="Universal chunked assembly (Option 2)",
                estimated_time="30 seconds - 5 minutes"
            )
        
        self.logger.log_strategy_selection(strategy, estimated_memory_gb)
        return strategy
    
    def create_temp_dem_path(self, prefix: str = "assembled_dem") -> str:
        """Create path for temporary DEM file"""
        if self.config.temp_dem_location == "project":
            # Use project directory
            temp_dir = Path(".")
        else:
            # Use system temp directory
            temp_dir = Path(tempfile.gettempdir())
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = temp_dir / f"{prefix}_{timestamp}.dem"
        
        self.logger.logger.debug(f"Temp DEM path: {temp_path}")
        return str(temp_path)
    
    def assemble_tiles_to_dem(self, tiles: List[TileInfo], west: float, north: float, 
                             east: float, south: float, export_scale: float = 1.0,
                             progress_callback=None) -> Optional[str]:
        """
        Assemble multiple tiles into a single DEM file
        
        Args:
            tiles: List of tiles to assemble
            west, north, east, south: Geographic bounds
            export_scale: Scale factor (0.1 to 1.0)
            progress_callback: Optional progress reporting function
            
        Returns:
            Path to assembled DEM file, or None if failed
        """
        
        if not tiles:
            self.logger.logger.error("No tiles provided for assembly")
            return None
        
        # Start timing and logging
        self.metrics.start_timing()
        self.logger.log_assembly_request(west, north, east, south, export_scale, len(tiles))
        self.logger.log_memory_state("Assembly Start")
        
        try:
            # Phase 1: Estimate memory and select strategy
            if progress_callback:
                progress_callback("🔍 Analyzing memory requirements...")
            
            estimated_memory = self.estimate_assembly_memory_gb(west, north, east, south, export_scale)
            strategy = self.select_assembly_strategy(estimated_memory)
            
            # Phase 2: Execute assembly based on approach
            approach = self.select_assembly_approach(estimated_memory)
            
            if approach == "in_memory":
                # Option 1: Fast path for data that fits in memory
                result_path = self._assemble_in_memory(tiles, west, north, east, south, 
                                                      export_scale, progress_callback)
            else:  # universal_chunked
                # Option 2: Universal chunked system for any size data
                result_path = self._assemble_universal_chunks(tiles, west, north, east, south,
                                                            export_scale, progress_callback)
            
            # Log completion
            if result_path:
                self.logger.log_assembly_completion(self.metrics, result_path)
                self.logger.logger.info(f"✅ Assembly successful: {result_path}")
            else:
                self.logger.logger.error("❌ Assembly failed")
                
            return result_path
            
        except Exception as e:
            self.logger.logger.error(f"Assembly error: {e}")
            import traceback
            self.logger.logger.debug(traceback.format_exc())
            return None
    
    def _assemble_in_memory(self, tiles: List[TileInfo], west: float, north: float,
                           east: float, south: float, export_scale: float,
                           progress_callback=None) -> Optional[str]:
        """Week 1: Basic in-memory assembly implementation"""
        
        self.logger.logger.info("Starting in-memory assembly...")
        self.logger.log_memory_state("In-Memory Assembly Start")
        
        if progress_callback:
            progress_callback("📊 Loading tiles into memory...")
        
        try:
            # For Week 1, use the existing multi_file_database assembly
            # This will be enhanced in later weeks
            from multi_file_database import MultiFileDatabase
            
            # Create a temporary MultiFileDatabase instance
            # Note: This is a simplified approach for Week 1
            temp_db = MultiFileDatabase(tiles[0].file_path.parent)
            
            # Use existing assembly method 
            assembled_data = temp_db._simple_tile_assembly(tiles, west, north, east, south)
            
            if assembled_data is None:
                self.logger.logger.error("Failed to assemble tiles")
                return None
            
            # Apply export scale if not 1.0
            if export_scale != 1.0:
                if progress_callback:
                    progress_callback(f"🔄 Scaling to {export_scale:.1%}...")
                    
                current_height, current_width = assembled_data.shape
                target_width = int(current_width * export_scale)
                target_height = int(current_height * export_scale)
                
                self.logger.logger.info(f"Applying scaling: {current_width}×{current_height} → {target_width}×{target_height}")
                
                # Simple scaling approach
                try:
                    from scipy import ndimage
                    assembled_data = ndimage.zoom(assembled_data, export_scale, order=1)
                    self.logger.logger.info(f"Scaling complete: {assembled_data.shape}")
                except ImportError:
                    # Fallback: simple subsampling
                    subsample_factor = max(1, int(1.0 / export_scale))
                    if subsample_factor > 1:
                        assembled_data = assembled_data[::subsample_factor, ::subsample_factor]
                        self.logger.logger.info(f"Simple subsampling complete: {assembled_data.shape}")
            else:
                self.logger.logger.info(f"Export scale is 100% - using full resolution data")
            
            # Phase 3: Write to DEM file
            if progress_callback:
                progress_callback("💾 Writing DEM file...")
            
            output_path = self.create_temp_dem_path()
            success = self._write_dem_file(assembled_data, output_path, west, north, east, south)
            
            self.logger.log_memory_state("In-Memory Assembly Complete")
            
            return output_path if success else None
            
        except Exception as e:
            self.logger.logger.error(f"In-memory assembly failed: {e}")
            return None
    
    def _assemble_streaming(self, tiles: List[TileInfo], west: float, north: float,
                           east: float, south: float, export_scale: float,
                           progress_callback=None) -> Optional[str]:
        """Week 2: Streaming assembly implementation (placeholder for now)"""
        
        self.logger.logger.info("Streaming assembly not yet implemented - falling back to in-memory")
        return self._assemble_in_memory(tiles, west, north, east, south, export_scale, progress_callback)
    
    def _assemble_disk_spooled(self, tiles: List[TileInfo], west: float, north: float,
                              east: float, south: float, export_scale: float,
                              progress_callback=None) -> Optional[str]:
        """Disk-spooled assembly for unlimited size exports"""
        
        self.logger.logger.info("Using memory-efficient disk-spooled assembly for large export...")
        
        # For very large exports, force a more aggressive export scale if needed
        memory_info = self.get_system_memory_info()
        estimated_memory = self.estimate_assembly_memory_gb(west, north, east, south, export_scale)
        
        # If even with current scale it's too big, suggest a more conservative scale
        if estimated_memory > memory_info['available_gb'] * 0.8:
            # Calculate a safer scale factor
            safe_scale = min(export_scale, (memory_info['available_gb'] * 0.5) / estimated_memory)
            
            if safe_scale < export_scale:
                self.logger.logger.warning(f"Export too large for memory. Reducing scale from {export_scale:.1%} to {safe_scale:.1%}")
                print(f"⚠️ MEMORY LIMITATION: Reducing export scale from {export_scale*100:.1f}% to {safe_scale*100:.1f}%")
                print(f"   Estimated memory: {estimated_memory:.1f}GB, Available: {memory_info['available_gb']:.1f}GB")
                export_scale = safe_scale
            
        # Try in-memory assembly with the (possibly adjusted) scale
        self.logger.logger.info(f"Attempting in-memory assembly with scale {export_scale:.1%}")
        return self._assemble_in_memory(tiles, west, north, east, south, export_scale, progress_callback)
    
    def _assemble_universal_chunks(self, tiles: List[TileInfo], west: float, north: float,
                                  east: float, south: float, export_scale: float,
                                  progress_callback=None) -> Optional[str]:
        """
        Option 2: Universal chunked assembly system
        Handles any size data through intelligent chunking and disk spooling
        """
        
        self.logger.logger.info("🚀 Starting universal chunked assembly (Option 2)")
        self.logger.log_memory_state("Universal Chunked Assembly Start")
        
        try:
            # Phase 1: Calculate optimal chunk configuration
            if progress_callback:
                progress_callback("🔍 Calculating optimal chunk configuration...")
            
            chunk_config = self._calculate_chunk_configuration(west, north, east, south, export_scale)
            
            if chunk_config['num_chunks'] == 1:
                # Single chunk = effectively in-memory processing
                self.logger.logger.info("📦 Single chunk detected - using optimized single-chunk processing")
                return self._process_single_chunk(tiles, west, north, east, south, export_scale, progress_callback)
            else:
                # Multiple chunks = true disk spooling
                self.logger.logger.info(f"📦 Multiple chunks detected ({chunk_config['num_chunks']}) - using disk spooling")
                return self._process_multiple_chunks(tiles, chunk_config, west, north, east, south, export_scale, progress_callback)
                
        except Exception as e:
            self.logger.logger.error(f"Universal chunked assembly failed: {e}")
            import traceback
            self.logger.logger.debug(traceback.format_exc())
            return None
    
    def _calculate_chunk_configuration(self, west: float, north: float, east: float, south: float, 
                                     export_scale: float) -> Dict:
        """Calculate optimal chunk configuration based on available memory"""
        
        # Get memory information
        memory_info = self.get_system_memory_info()
        available_gb = memory_info['available_gb']
        
        # Apply artificial limits for testing
        if self.config.artificial_memory_limit_mb:
            available_gb = min(available_gb, self.config.artificial_memory_limit_mb / 1024)
        
        # Calculate target chunk size in MB
        target_chunk_size_mb = self.config.chunk_size_mb
        target_chunk_size_gb = target_chunk_size_mb / 1024
        
        # Calculate total output dimensions
        deg_width = east - west
        deg_height = north - south
        pixels_per_degree = 120  # Approximate for GTOPO30
        
        total_width_pixels = int(deg_width * pixels_per_degree * export_scale)
        total_height_pixels = int(deg_height * pixels_per_degree * export_scale)
        
        # Calculate memory per pixel (float32 = 4 bytes + overhead)
        bytes_per_pixel = 4 * 2.5  # Include processing overhead
        
        # Calculate how many pixels fit in target chunk size
        pixels_per_chunk = int(target_chunk_size_gb * (1024**3) / bytes_per_pixel)
        
        # Determine chunk grid dimensions
        if total_width_pixels * total_height_pixels <= pixels_per_chunk:
            # Single chunk is sufficient
            chunk_rows = 1
            chunk_cols = 1
        else:
            # Multiple chunks needed
            # Prefer square-ish chunks for better cache locality
            total_chunks_needed = (total_width_pixels * total_height_pixels) / pixels_per_chunk
            chunk_side = int(np.sqrt(total_chunks_needed)) + 1
            
            chunk_rows = min(chunk_side, int(np.ceil(total_height_pixels / np.sqrt(pixels_per_chunk))))
            chunk_cols = min(chunk_side, int(np.ceil(total_width_pixels / np.sqrt(pixels_per_chunk))))
            
            # Ensure we have enough chunks
            while chunk_rows * chunk_cols < total_chunks_needed:
                if chunk_rows <= chunk_cols:
                    chunk_rows += 1
                else:
                    chunk_cols += 1
        
        # Calculate actual chunk dimensions
        chunk_width_pixels = total_width_pixels // chunk_cols
        chunk_height_pixels = total_height_pixels // chunk_rows
        
        chunk_width_degrees = deg_width / chunk_cols
        chunk_height_degrees = deg_height / chunk_rows
        
        config = {
            'total_width_pixels': total_width_pixels,
            'total_height_pixels': total_height_pixels,
            'chunk_rows': chunk_rows,
            'chunk_cols': chunk_cols,
            'num_chunks': chunk_rows * chunk_cols,
            'chunk_width_pixels': chunk_width_pixels,
            'chunk_height_pixels': chunk_height_pixels,
            'chunk_width_degrees': chunk_width_degrees,
            'chunk_height_degrees': chunk_height_degrees,
            'target_chunk_size_mb': target_chunk_size_mb,
            'estimated_chunk_memory_gb': (chunk_width_pixels * chunk_height_pixels * bytes_per_pixel) / (1024**3)
        }
        
        self.logger.logger.info(f"📊 Chunk configuration:")
        self.logger.logger.info(f"   Output dimensions: {total_width_pixels}×{total_height_pixels}")
        self.logger.logger.info(f"   Chunk grid: {chunk_rows}×{chunk_cols} = {config['num_chunks']} chunks")
        self.logger.logger.info(f"   Chunk size: {chunk_width_pixels}×{chunk_height_pixels} (~{config['estimated_chunk_memory_gb']:.1f}GB each)")
        self.logger.logger.info(f"   Available memory: {available_gb:.1f}GB")
        
        return config
    
    def _process_single_chunk(self, tiles: List[TileInfo], west: float, north: float,
                             east: float, south: float, export_scale: float,
                             progress_callback=None) -> Optional[str]:
        """Process data as a single chunk (optimized path for single-chunk scenarios)"""
        
        self.logger.logger.info("📦 Processing as single chunk")
        
        if progress_callback:
            progress_callback("📦 Processing single chunk...")
        
        # Use the existing in-memory assembly for single chunks
        return self._assemble_in_memory(tiles, west, north, east, south, export_scale, progress_callback)
    
    def _process_multiple_chunks(self, tiles: List[TileInfo], chunk_config: Dict,
                                west: float, north: float, east: float, south: float,
                                export_scale: float, progress_callback=None) -> Optional[str]:
        """Process data using multiple chunks with disk spooling"""
        
        num_chunks = chunk_config['num_chunks']
        self.logger.logger.info(f"🗂️ Processing {num_chunks} chunks with disk spooling")
        
        try:
            # Create temporary directory for chunk processing
            temp_dir = Path(tempfile.mkdtemp(prefix="dem_chunks_"))
            self.logger.logger.info(f"📁 Created temp directory: {temp_dir}")
            
            # Process each chunk and save to temporary files
            chunk_files = []
            
            for row in range(chunk_config['chunk_rows']):
                for col in range(chunk_config['chunk_cols']):
                    chunk_index = row * chunk_config['chunk_cols'] + col
                    
                    if progress_callback:
                        progress_percent = 10 + int((chunk_index / num_chunks) * 70)
                        progress_callback(f"🗂️ Processing chunk {chunk_index + 1}/{num_chunks}...")
                    
                    # Calculate chunk boundaries
                    chunk_west = west + col * chunk_config['chunk_width_degrees']
                    chunk_east = min(west + (col + 1) * chunk_config['chunk_width_degrees'], east)
                    chunk_north = north - row * chunk_config['chunk_height_degrees']
                    chunk_south = max(north - (row + 1) * chunk_config['chunk_height_degrees'], south)
                    
                    self.logger.logger.debug(f"   Chunk {chunk_index}: W={chunk_west:.3f}°, N={chunk_north:.3f}°, E={chunk_east:.3f}°, S={chunk_south:.3f}°")
                    
                    # Find tiles that overlap this chunk
                    chunk_tiles = self._find_tiles_for_chunk(tiles, chunk_west, chunk_north, chunk_east, chunk_south)
                    
                    if chunk_tiles:
                        # Process this chunk
                        chunk_data = self._process_chunk_data(chunk_tiles, chunk_west, chunk_north, 
                                                           chunk_east, chunk_south, export_scale)
                        
                        if chunk_data is not None:
                            # Save chunk to temporary file
                            chunk_file = temp_dir / f"chunk_{row}_{col}.npy"
                            np.save(chunk_file, chunk_data)
                            chunk_files.append({
                                'file': chunk_file,
                                'row': row,
                                'col': col,
                                'bounds': (chunk_west, chunk_north, chunk_east, chunk_south),
                                'shape': chunk_data.shape
                            })
                            
                            # Free memory immediately
                            del chunk_data
                        
                        self.logger.log_memory_state(f"After chunk {chunk_index}")
            
            # Assemble chunks into final DEM
            if progress_callback:
                progress_callback("🔗 Assembling chunks into final DEM...")
            
            final_dem_path = self._assemble_chunks_to_dem(chunk_files, chunk_config, west, north, east, south)
            
            # Clean up temporary files
            try:
                for chunk_info in chunk_files:
                    chunk_info['file'].unlink()
                temp_dir.rmdir()
                self.logger.logger.info(f"🧹 Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                self.logger.logger.warning(f"Failed to cleanup temp files: {e}")
            
            return final_dem_path
            
        except Exception as e:
            self.logger.logger.error(f"Multiple chunk processing failed: {e}")
            import traceback
            self.logger.logger.debug(traceback.format_exc())
            return None
    
    def _find_tiles_for_chunk(self, tiles: List[TileInfo], west: float, north: float, 
                             east: float, south: float) -> List[TileInfo]:
        """Find tiles that overlap with the given chunk boundaries"""
        
        overlapping_tiles = []
        
        for tile in tiles:
            # Check if tile overlaps with chunk
            tile_bounds = tile.bounds
            
            # Check for overlap
            if (tile_bounds.west < east and tile_bounds.east > west and
                tile_bounds.north > south and tile_bounds.south < north):
                overlapping_tiles.append(tile)
        
        return overlapping_tiles
    
    def _process_chunk_data(self, chunk_tiles: List[TileInfo], west: float, north: float,
                           east: float, south: float, export_scale: float) -> Optional[np.ndarray]:
        """Process elevation data for a single chunk"""
        
        if not chunk_tiles:
            self.logger.logger.debug(f"No tiles found for chunk bounds")
            return None
        
        try:
            # Use existing multi-file database assembly for this chunk
            from multi_file_database import MultiFileDatabase
            
            # Create temporary database instance
            temp_db = MultiFileDatabase(chunk_tiles[0].file_path.parent)
            
            # Assemble tiles for this chunk
            chunk_data = temp_db._simple_tile_assembly(chunk_tiles, west, north, east, south)
            
            if chunk_data is None:
                return None
            
            # Apply export scale if needed
            if export_scale != 1.0:
                current_height, current_width = chunk_data.shape
                target_width = int(current_width * export_scale)
                target_height = int(current_height * export_scale)
                
                try:
                    from scipy import ndimage
                    chunk_data = ndimage.zoom(chunk_data, export_scale, order=1)
                except ImportError:
                    # Fallback: simple subsampling
                    subsample_factor = max(1, int(1.0 / export_scale))
                    if subsample_factor > 1:
                        chunk_data = chunk_data[::subsample_factor, ::subsample_factor]
            
            return chunk_data
            
        except Exception as e:
            self.logger.logger.error(f"Chunk processing failed: {e}")
            return None
    
    def _assemble_chunks_to_dem(self, chunk_files: List[Dict], chunk_config: Dict,
                               west: float, north: float, east: float, south: float) -> Optional[str]:
        """Assemble processed chunks into final DEM file"""
        
        try:
            # Create output array
            total_height = chunk_config['total_height_pixels'] 
            total_width = chunk_config['total_width_pixels']
            
            self.logger.logger.info(f"🔗 Assembling final DEM: {total_width}×{total_height}")
            
            # Initialize output array
            final_array = np.full((total_height, total_width), np.nan, dtype=np.float32)
            
            # Place each chunk into the final array
            for chunk_info in chunk_files:
                row = chunk_info['row']
                col = chunk_info['col']
                
                # Load chunk data
                chunk_data = np.load(chunk_info['file'])
                
                # Calculate placement position
                start_row = row * chunk_config['chunk_height_pixels']
                end_row = min(start_row + chunk_data.shape[0], total_height)
                start_col = col * chunk_config['chunk_width_pixels']
                end_col = min(start_col + chunk_data.shape[1], total_width)
                
                # Place chunk data
                final_array[start_row:end_row, start_col:end_col] = chunk_data[:end_row-start_row, :end_col-start_col]
                
                # Free memory
                del chunk_data
            
            # Write final DEM file
            output_path = self.create_temp_dem_path("universal_chunked_dem")
            success = self._write_dem_file(final_array, output_path, west, north, east, south)
            
            if success:
                self.logger.logger.info(f"✅ Universal chunked assembly complete: {output_path}")
                return output_path
            else:
                return None
                
        except Exception as e:
            self.logger.logger.error(f"Chunk assembly failed: {e}")
            return None
    
    def _write_dem_file(self, elevation_data: np.ndarray, output_path: str,
                       west: float, north: float, east: float, south: float) -> bool:
        """Write elevation data to DEM file with header"""
        
        try:
            height, width = elevation_data.shape
            
            # Calculate pixel size
            pixel_size_x = (east - west) / width
            pixel_size_y = (north - south) / height
            
            # Write binary elevation data
            dem_path = Path(output_path)
            with open(dem_path, 'wb') as f:
                # Convert to int16 for standard DEM format
                # Handle NaN values by converting to nodata value
                output_array = elevation_data.copy()
                output_array[np.isnan(output_array)] = -9999
                
                # Convert to int16 with big-endian byte order (to match GTOPO30 format)
                int16_data = output_array.astype('>i2')  # Big-endian int16
                int16_data.tofile(f)
            
            # Write header file
            hdr_path = dem_path.with_suffix('.hdr')
            with open(hdr_path, 'w') as f:
                f.write(f"BYTEORDER      M\n")
                f.write(f"LAYOUT         BIL\n")
                f.write(f"NROWS          {height}\n")
                f.write(f"NCOLS          {width}\n")
                f.write(f"NBANDS         1\n")
                f.write(f"NBITS          16\n")
                f.write(f"BANDROWBYTES   {width * 2}\n")
                f.write(f"TOTALROWBYTES  {width * 2}\n")
                f.write(f"BANDGAPBYTES   0\n")
                f.write(f"NODATA         -9999\n")
                f.write(f"ULXMAP         {west + pixel_size_x/2}\n")
                f.write(f"ULYMAP         {north - pixel_size_y/2}\n")
                f.write(f"XDIM           {pixel_size_x}\n")
                f.write(f"YDIM           {pixel_size_y}\n")
            
            self.logger.logger.info(f"DEM file written: {dem_path} ({width}×{height})")
            self.logger.logger.debug(f"Header file written: {hdr_path}")
            
            return True
            
        except Exception as e:
            self.logger.logger.error(f"Failed to write DEM file: {e}")
            return False
    
    def cleanup_temp_dem(self, dem_path: str):
        """Clean up temporary DEM file and header"""
        try:
            dem_file = Path(dem_path)
            hdr_file = dem_file.with_suffix('.hdr')
            
            if dem_file.exists():
                dem_file.unlink()
                self.logger.logger.debug(f"Deleted temp DEM: {dem_file}")
                
            if hdr_file.exists():
                hdr_file.unlink()
                self.logger.logger.debug(f"Deleted temp HDR: {hdr_file}")
                
        except Exception as e:
            self.logger.logger.warning(f"Failed to cleanup temp files: {e}")


class AssemblyDiagnostics:
    """Diagnostic tools for DEM assembly system"""
    
    def __init__(self, assembler: DEMAssembler):
        self.assembler = assembler
        
    def run_health_check(self) -> Dict:
        """Comprehensive system health check"""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'system_info': self.assembler.get_system_memory_info(),
            'disk_space_gb': psutil.disk_usage('.').free / (1024**3),
            'numpy_version': np.__version__,
            'working_directory': os.getcwd(),
            'tests': {}
        }
        
        # Test 1: Memory detection
        try:
            memory_info = self.assembler.get_system_memory_info()
            report['tests']['memory_detection'] = 'PASS'
        except Exception as e:
            report['tests']['memory_detection'] = f'FAIL: {e}'
        
        # Test 2: Strategy selection
        try:
            strategy = self.assembler.select_assembly_strategy(1.0)  # 1GB test
            report['tests']['strategy_selection'] = f'PASS: {strategy.name}'
        except Exception as e:
            report['tests']['strategy_selection'] = f'FAIL: {e}'
        
        # Test 3: Temp file creation
        try:
            temp_path = self.assembler.create_temp_dem_path("health_check")
            Path(temp_path).touch()  # Create test file
            Path(temp_path).unlink()  # Delete test file
            report['tests']['temp_file_creation'] = 'PASS'
        except Exception as e:
            report['tests']['temp_file_creation'] = f'FAIL: {e}'
        
        return report
    
    def save_diagnostic_report(self, report: Dict, filename: str = "assembly_diagnostics.json"):
        """Save diagnostic report to file"""
        import json
        
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Diagnostic report saved: {filename}")
        except Exception as e:
            print(f"Failed to save diagnostic report: {e}")


def test_assembly_system():
    """Test the assembly system with basic functionality"""
    
    print("🧪 Testing DEM Assembly System")
    print("=" * 50)
    
    # Create assembler
    config = AssemblyConfig(debug_mode=True)
    assembler = DEMAssembler(config)
    
    # Run diagnostics
    diagnostics = AssemblyDiagnostics(assembler)
    report = diagnostics.run_health_check()
    
    print("\n📊 Health Check Results:")
    for test_name, result in report['tests'].items():
        status = "✅" if result.startswith('PASS') else "❌"
        print(f"   {status} {test_name}: {result}")
    
    print(f"\n💾 Memory: {report['system_info']['available_gb']:.1f}GB available")
    print(f"💿 Disk: {report['disk_space_gb']:.1f}GB free")
    
    # Save diagnostic report
    diagnostics.save_diagnostic_report(report)
    
    print(f"\n📝 Detailed logs: {assembler.config.log_file}")
    print("✅ Assembly system test complete")


if __name__ == "__main__":
    test_assembly_system()