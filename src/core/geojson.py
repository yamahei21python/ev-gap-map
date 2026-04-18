"""GeoJSON utilities"""

from typing import List, Dict, Any


def create_polygon(
    lon_min: float,
    lat_min: float,
    lon_max: float,
    lat_max: float,
) -> List[List[List[float]]]:
    """
    Create polygon coordinates from bounding box

    Returns:
        Polygon coordinates (closed ring)
    """
    return [
        [
            [lon_min, lat_min],
            [lon_max, lat_min],
            [lon_max, lat_max],
            [lon_min, lat_max],
            [lon_min, lat_min],
        ]
    ]


def create_feature(
    geometry_type: str,
    coordinates: Any,
    properties: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create GeoJSON feature

    Args:
        geometry_type: Point, Polygon, etc.
        coordinates: Geometry coordinates
        properties: Feature properties
    """
    return {
        "type": "Feature",
        "geometry": {
            "type": geometry_type,
            "coordinates": coordinates,
        },
        "properties": properties,
    }


def create_feature_collection(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create GeoJSON FeatureCollection"""
    return {
        "type": "FeatureCollection",
        "features": features,
    }


def polygon_to_feature(
    lon_min: float,
    lat_min: float,
    lon_max: float,
    lat_max: float,
    properties: Dict[str, Any],
) -> Dict[str, Any]:
    """Create polygon feature from bounding box"""
    return create_feature(
        "Polygon",
        create_polygon(lon_min, lat_min, lon_max, lat_max),
        properties,
    )


def point_to_feature(
    lon: float,
    lat: float,
    properties: Dict[str, Any],
) -> Dict[str, Any]:
    """Create point feature"""
    return create_feature("Point", [lon, lat], properties)
