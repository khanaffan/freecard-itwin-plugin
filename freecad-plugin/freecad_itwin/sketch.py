"""
Sketch geometry and constraint serializer.

Serializes FreeCAD Sketcher objects into structured JSON for
round-trip preservation in iModels.
"""

from __future__ import annotations

from typing import Any


def _serialize_geometry(geo: Any, index: int) -> dict[str, Any]:
    """Serialize a single sketch geometry element."""
    geo_type = type(geo).__name__
    data: dict[str, Any] = {"id": index, "type": geo_type}

    if geo_type == "LineSegment":
        data["data"] = {
            "startPoint": [float(geo.StartPoint.x), float(geo.StartPoint.y)],
            "endPoint": [float(geo.EndPoint.x), float(geo.EndPoint.y)],
        }
    elif geo_type == "Circle":
        data["data"] = {
            "center": [float(geo.Center.x), float(geo.Center.y)],
            "radius": float(geo.Radius),
        }
    elif geo_type == "ArcOfCircle":
        data["data"] = {
            "center": [float(geo.Center.x), float(geo.Center.y)],
            "radius": float(geo.Radius),
            "startAngle": float(geo.FirstParameter),
            "endAngle": float(geo.LastParameter),
        }
    elif geo_type == "Point":
        data["data"] = {
            "point": [float(geo.X), float(geo.Y)],
        }
    elif geo_type == "BSplineCurve":
        poles = [[float(p.x), float(p.y)] for p in geo.getPoles()]
        data["data"] = {
            "poles": poles,
            "knots": list(geo.getKnots()),
            "multiplicities": list(geo.getMultiplicities()),
            "degree": int(geo.Degree),
            "periodic": bool(geo.isPeriodic()),
        }
    elif geo_type == "Ellipse":
        data["data"] = {
            "center": [float(geo.Center.x), float(geo.Center.y)],
            "majorRadius": float(geo.MajorRadius),
            "minorRadius": float(geo.MinorRadius),
        }
    else:
        # Generic fallback — store string representation
        data["data"] = {"repr": str(geo)}

    return data


# Constraint type mapping
CONSTRAINT_TYPE_MAP = {
    "Coincident": "Coincident",
    "PointOnObject": "PointOnObject",
    "Vertical": "Vertical",
    "Horizontal": "Horizontal",
    "Parallel": "Parallel",
    "Perpendicular": "Perpendicular",
    "Tangent": "Tangent",
    "Equal": "Equal",
    "Symmetric": "Symmetric",
    "Block": "Block",
    "Distance": "Distance",
    "DistanceX": "DistanceX",
    "DistanceY": "DistanceY",
    "Radius": "Radius",
    "Diameter": "Diameter",
    "Angle": "Angle",
    "InternalAlignment": "InternalAlignment",
}


def _serialize_constraint(constraint: Any) -> dict[str, Any]:
    """Serialize a single sketch constraint."""
    c_type = str(constraint.Type)
    data: dict[str, Any] = {
        "type": CONSTRAINT_TYPE_MAP.get(c_type, c_type),
        "geometryRefs": [],
    }

    # Geometry references
    if hasattr(constraint, "First") and constraint.First >= 0:
        data["geometryRefs"].append(int(constraint.First))
    if hasattr(constraint, "Second") and constraint.Second >= 0:
        data["geometryRefs"].append(int(constraint.Second))
    if hasattr(constraint, "Third") and constraint.Third >= 0:
        data["geometryRefs"].append(int(constraint.Third))

    # Value for dimensional constraints
    if hasattr(constraint, "Value") and constraint.Value != 0:
        data["value"] = float(constraint.Value)

    # Named constraints
    if hasattr(constraint, "Name") and constraint.Name:
        data["name"] = str(constraint.Name)

    return data


def serialize_sketch(sketch_obj: Any) -> dict[str, Any]:
    """
    Serialize a FreeCAD Sketcher object to a dict.

    Returns sketch geometry, constraints, and support plane data.
    """
    result: dict[str, Any] = {
        "geometry": [],
        "constraints": [],
        "plane": {
            "origin": [0.0, 0.0, 0.0],
            "normal": [0.0, 0.0, 1.0],
        },
    }

    # Geometry
    if hasattr(sketch_obj, "Geometry"):
        for i, geo in enumerate(sketch_obj.Geometry):
            result["geometry"].append(_serialize_geometry(geo, i))

    # Constraints
    if hasattr(sketch_obj, "Constraints"):
        for constraint in sketch_obj.Constraints:
            result["constraints"].append(_serialize_constraint(constraint))

    # Support plane from placement
    if hasattr(sketch_obj, "Placement"):
        p = sketch_obj.Placement
        result["plane"]["origin"] = [
            float(p.Base.x),
            float(p.Base.y),
            float(p.Base.z),
        ]
        # Normal from placement rotation applied to Z axis
        try:
            z_axis = p.Rotation.multVec(type(p.Base)(0, 0, 1))
            result["plane"]["normal"] = [
                float(z_axis.x),
                float(z_axis.y),
                float(z_axis.z),
            ]
        except Exception:
            pass

    return result
