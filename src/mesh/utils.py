"""Mesh code utilities - polygon generation"""

from typing import Dict, Any, Tuple
import jismesh.utils as ju


def get_mesh_level(meshcode: str) -> int:
    """Get mesh level from mesh code"""
    return ju.to_meshlevel(meshcode)


def get_mesh_polygon(meshcode: str) -> Dict[str, float]:
    """
    Get bounding box from mesh code

    Returns:
        dict with lat_min, lon_min, lat_max, lon_max
    """
    lat, lon = ju.to_meshpoint(meshcode, 0, 0)
    level = ju.to_meshlevel(meshcode)

    if level == 3:
        dlat = 1.0 / 120.0  # 1km
        dlon = 1.0 / 80.0
    elif level == 4:
        dlat = 1.0 / 240.0  # 500m
        dlon = 1.0 / 160.0
    else:
        dlat = 1.0 / 120.0
        dlon = 1.0 / 80.0

    return {
        "lat_min": lat,
        "lon_min": lon,
        "lat_max": lat + dlat,
        "lon_max": lon + dlon,
    }


def to_meshcode(lat: float, lon: float, level: int = 3) -> str:
    """Convert coordinates to mesh code"""
    return str(ju.to_meshcode(lat, lon, level))


def get_mesh_counts(
    lat: float,
    lon: float,
    level: int = 3,
) -> Dict[str, Any]:
    """Get mesh info for coordinates"""
    code = to_meshcode(lat, lon, level)
    polygon = get_mesh_polygon(code)
    return {
        "mesh_code": code,
        **polygon,
    }


def normalize_to_3rd_mesh(meshcode: str) -> str:
    """Normalize mesh code to 3rd level (1km)"""
    code_str = str(meshcode)
    if len(code_str) >= 8:
        return code_str[:8]
    return code_str


def get_mesh_center(
    lat_min: float, lon_min: float, lat_max: float, lon_max: float
) -> Tuple[float, float]:
    """Get center coordinates of a mesh bounding box"""
    center_lat = (lat_min + lat_max) / 2.0
    center_lon = (lon_min + lon_max) / 2.0
    return center_lat, center_lon
