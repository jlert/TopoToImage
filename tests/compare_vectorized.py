#!/usr/bin/env python3
"""
Verification harness for the vectorized rendering passes (branch: vectorize-rendering).

Compares the NEW vectorized implementations against VERBATIM copies of the
original per-pixel loop implementations (tag: pre-vectorization) on synthetic
terrain, reporting per-pixel differences and timing.

Run:  python tests/compare_vectorized.py
"""

import sys
import time
import math
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from terrain_renderer import TerrainRenderer
from shadow_method_3 import ShadowMethod3


# ---------------------------------------------------------------------------
# REFERENCE IMPLEMENTATIONS — verbatim copies of the original loops
# (from git tag pre-vectorization), with `self` removed where needed.
# ---------------------------------------------------------------------------

def reference_hillshade(elevation_data, light_direction=315, shading_intensity=50,
                        min_elevation=None, max_elevation=None):
    """Original calculate_hillshade from terrain_renderer.py (pre-vectorization)."""
    height, width = elevation_data.shape
    hillshade = np.full((height, width), 0.5, dtype=np.float32)

    if min_elevation is not None and max_elevation is not None:
        terrain_relief = max(50.0, max_elevation - min_elevation)
    else:
        valid_elevations = elevation_data[~np.isnan(elevation_data)]
        if len(valid_elevations) > 0:
            terrain_relief = max(50.0, np.max(valid_elevations) - np.min(valid_elevations))
        else:
            terrain_relief = 100.0

    light_rad = math.radians(light_direction)
    dx = -math.sin(light_rad)
    dy = math.cos(light_rad)
    sample_distance = 1.0
    x_offset = dx * sample_distance
    y_offset = dy * sample_distance

    for y in range(height):
        for x in range(width):
            current_elev = elevation_data[y, x]
            if np.isnan(current_elev):
                continue
            neighbor_x = x + x_offset
            neighbor_y = y + y_offset
            if (neighbor_x < 0 or neighbor_x >= width - 1 or
                    neighbor_y < 0 or neighbor_y >= height - 1):
                continue
            x0, x1 = int(neighbor_x), int(neighbor_x) + 1
            y0, y1 = int(neighbor_y), int(neighbor_y) + 1
            q00 = elevation_data[y0, x0]
            q01 = elevation_data[y1, x0]
            q10 = elevation_data[y0, x1]
            q11 = elevation_data[y1, x1]
            if np.isnan(q00) or np.isnan(q01) or np.isnan(q10) or np.isnan(q11):
                continue
            wx = neighbor_x - x0
            wy = neighbor_y - y0
            neighbor_elev = (q00 * (1 - wx) * (1 - wy) +
                             q10 * wx * (1 - wy) +
                             q01 * (1 - wx) * wy +
                             q11 * wx * wy)
            elev_diff = current_elev - neighbor_elev
            intensity_factor = shading_intensity / 100.0
            shaded_value_normalized = (elev_diff / terrain_relief) * intensity_factor * 1.2
            hillshade[y, x] = 0.5 + shaded_value_normalized

    return np.clip(hillshade, 0.0, 1.0)


def reference_method3_shadows(elevation_data, light_direction=315,
                              shadow_drop_distance=1.0, shadow_soft_edge=3):
    """Original ShadowMethod3.calculate_shadows core loop (pre-vectorization).

    Uses the unchanged helper methods (_angle_to_bresenham_vector,
    _get_edge_starting_points, _bresenham_line) from the current module.
    """
    helper = ShadowMethod3()
    height, width = elevation_data.shape
    shadow_map = np.zeros((height, width), dtype=np.float32)

    shadow_direction = light_direction % 360
    dx, dy = helper._angle_to_bresenham_vector(shadow_direction)

    clean_elevation = np.copy(elevation_data)
    clean_elevation[np.isnan(clean_elevation)] = 0.0

    if shadow_soft_edge > 0:
        shadow_gray_step = 1.0 / shadow_soft_edge
    else:
        shadow_gray_step = 1.0

    elevation_data = clean_elevation
    drop_distance = shadow_drop_distance
    starting_points = helper._get_edge_starting_points(shadow_direction, width, height)
    max_extent = max(width, height) * 2

    for start_x, start_y in starting_points:
        target_x = start_x + dx * max_extent // max(abs(dx), abs(dy), 1)
        target_y = start_y + dy * max_extent // max(abs(dx), abs(dy), 1)
        line_points = helper._bresenham_line(start_x, start_y, target_x, target_y)
        shadow_height = -float('inf')
        for x, y in line_points:
            if x < 0 or x >= width or y < 0 or y >= height:
                continue
            current_elev = elevation_data[y, x]
            shadow_height = max(shadow_height, current_elev - drop_distance)
            if shadow_height > current_elev:
                shadow_diff = shadow_height - current_elev
                shadow_intensity = min(1.0, shadow_diff * shadow_gray_step / drop_distance)
                shadow_map[y, x] = max(shadow_map[y, x], shadow_intensity)
                shadow_height = max(shadow_height - drop_distance, current_elev - drop_distance)
            else:
                shadow_height = current_elev - drop_distance

    return shadow_map


def reference_shadow_composite(result, shadow_layer, shadow_rgb):
    """Original shadow compositing loop from terrain_renderer.py (pre-vectorization)."""
    result = result.copy()
    shadow_r, shadow_g, shadow_b = shadow_rgb
    shadow_map = shadow_layer.astype(np.float32) / 255.0
    height, width = result.shape[:2]
    for y in range(height):
        for x in range(width):
            shadow_intensity = shadow_map[y, x]
            if shadow_intensity > 0:
                r_scale = ((1 - shadow_intensity) * (1 - shadow_r / 255.0)) + (shadow_r / 255.0)
                g_scale = ((1 - shadow_intensity) * (1 - shadow_g / 255.0)) + (shadow_g / 255.0)
                b_scale = ((1 - shadow_intensity) * (1 - shadow_b / 255.0)) + (shadow_b / 255.0)
                result[y, x, 0] = int(result[y, x, 0] * r_scale)
                result[y, x, 1] = int(result[y, x, 1] * g_scale)
                result[y, x, 2] = int(result[y, x, 2] * b_scale)
    return result


def new_shadow_composite(result, shadow_layer, shadow_rgb):
    """Vectorized compositing — mirrors the new code in terrain_renderer.py."""
    result = result.copy()
    shadow_r, shadow_g, shadow_b = shadow_rgb
    shadow_map = shadow_layer.astype(np.float32) / 255.0
    shadow_pixels = shadow_map > 0
    inverse_intensity = 1.0 - shadow_map.astype(np.float64)
    for channel, shadow_component in enumerate((shadow_r, shadow_g, shadow_b)):
        scale = (inverse_intensity * (1 - shadow_component / 255.0)) + (shadow_component / 255.0)
        shadowed = (result[:, :, channel] * scale).astype(np.uint8)
        result[:, :, channel] = np.where(shadow_pixels, shadowed, result[:, :, channel])
    return result


# ---------------------------------------------------------------------------
# Test terrain and comparison driver
# ---------------------------------------------------------------------------

def make_terrain(height=400, width=600, seed=42):
    """Smooth synthetic hills with a NaN (no-data) patch, float32 like real DEMs."""
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, (height, width))
    try:
        from scipy import ndimage
        terrain = ndimage.gaussian_filter(noise, sigma=12) * 3000.0
    except ImportError:
        terrain = noise * 100.0
    terrain = terrain.astype(np.float32)
    terrain[50:90, 100:160] = np.nan  # no-data patch
    return terrain


def report(label, ref, new, t_ref, t_new, scale_255=False):
    if np.isnan(ref).any() or np.isnan(new).any():
        nan_match = np.array_equal(np.isnan(ref), np.isnan(new))
        print(f"  NaN masks match: {nan_match}")
    diff = np.abs(ref.astype(np.float64) - new.astype(np.float64))
    max_diff = np.nanmax(diff)
    n_diff = int(np.sum(diff > 0))
    exact = "IDENTICAL" if max_diff == 0 else f"max diff {max_diff:.3e} at {n_diff} px"
    if scale_255 and max_diff > 0:
        exact += f" (={max_diff*255:.4f}/255 display levels)"
    speedup = t_ref / t_new if t_new > 0 else float('inf')
    print(f"  {label}: {exact} | old {t_ref:.2f}s, new {t_new:.3f}s ({speedup:.0f}x faster)")
    return max_diff


def main():
    terrain = make_terrain()
    print(f"Test terrain: {terrain.shape}, range "
          f"{np.nanmin(terrain):.0f}..{np.nanmax(terrain):.0f} m, with NaN patch\n")

    renderer = TerrainRenderer.__new__(TerrainRenderer)  # skip __init__ (no gradients needed)
    method3 = ShadowMethod3()
    worst_hs = worst_sh = worst_cp = 0.0

    print("=== Hillshade ===")
    for light in (315, 0, 90, 180, 270, 47, 203):
        t0 = time.perf_counter(); ref = reference_hillshade(terrain, light); t1 = time.perf_counter()
        new = renderer.calculate_hillshade(terrain, light_direction=light); t2 = time.perf_counter()
        print(f" light={light}°")
        worst_hs = max(worst_hs, report("hillshade", ref, new, t1 - t0, t2 - t1, scale_255=True))

    print("\n=== Shadow method 3 ===")
    for light, drop, soft in ((315, 1.0, 3), (315, 0.25, 0), (90, 1.0, 3),
                              (180, 2.0, 5), (47, 0.5, 3), (270, 1.0, 0)):
        t0 = time.perf_counter()
        ref = reference_method3_shadows(terrain, light, drop, soft)
        t1 = time.perf_counter()
        new = method3.calculate_shadows(terrain, light_direction=light,
                                        shadow_drop_distance=drop, shadow_soft_edge=soft)
        t2 = time.perf_counter()
        # New path includes prints; timing still representative
        print(f" light={light}°, drop={drop}, soft={soft}")
        worst_sh = max(worst_sh, report("shadows", ref, new, t1 - t0, t2 - t1, scale_255=True))

    print("\n=== Shadow compositing ===")
    rng = np.random.default_rng(7)
    rgb_image = rng.integers(0, 256, (400, 600, 4), dtype=np.uint8)
    shadow_layer = (reference_method3_shadows(terrain, 315, 1.0, 3) * 255).astype(np.uint8)
    for shadow_rgb in ((0, 0, 0), (40, 30, 80)):
        t0 = time.perf_counter(); ref = reference_shadow_composite(rgb_image, shadow_layer, shadow_rgb); t1 = time.perf_counter()
        new = new_shadow_composite(rgb_image, shadow_layer, shadow_rgb); t2 = time.perf_counter()
        print(f" shadow color {shadow_rgb}")
        worst_cp = max(worst_cp, report("composite", ref, new, t1 - t0, t2 - t1))

    print("\n=== Summary ===")
    print(f"worst hillshade diff:  {worst_hs:.3e}  (display-visible threshold ≈ 2e-3)")
    print(f"worst shadow diff:     {worst_sh:.3e}")
    print(f"worst composite diff:  {worst_cp:.3e}  (uint8 levels)")
    ok = worst_hs < 2e-3 and worst_sh < 2e-3 and worst_cp <= 1
    print("RESULT:", "PASS — outputs visually indistinguishable" if ok else "FAIL — investigate differences")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
