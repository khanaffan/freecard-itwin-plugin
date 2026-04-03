"""
Parametric feature tree serializer.

Serializes FreeCAD's parametric feature tree (Pad, Pocket, Fillet, etc.)
into a structured JSON representation for round-trip preservation.
"""

from __future__ import annotations

from typing import Any


def _extract_parameters(obj: Any) -> dict[str, Any]:
    """Extract serializable parameters from a FreeCAD feature object."""
    params: dict[str, Any] = {}
    type_id = getattr(obj, "TypeId", "")

    # Common PartDesign feature parameters
    if hasattr(obj, "Length"):
        params["Length"] = float(obj.Length)
    if hasattr(obj, "Length2"):
        params["Length2"] = float(obj.Length2)
    if hasattr(obj, "Angle"):
        params["Angle"] = float(obj.Angle)
    if hasattr(obj, "Size"):
        params["Size"] = float(obj.Size)
    if hasattr(obj, "Radius"):
        params["Radius"] = float(obj.Radius)
    if hasattr(obj, "Reversed"):
        params["Reversed"] = bool(obj.Reversed)
    if hasattr(obj, "Symmetric"):
        params["Symmetric"] = bool(obj.Symmetric)
    if hasattr(obj, "Midplane"):
        params["Midplane"] = bool(obj.Midplane)

    # Type-specific parameters
    if "Pad" in type_id or "Pocket" in type_id:
        if hasattr(obj, "Type"):
            params["Type"] = str(obj.Type)
        if hasattr(obj, "UpToFace"):
            params["UpToFace"] = str(obj.UpToFace) if obj.UpToFace else None
    elif "Fillet" in type_id:
        if hasattr(obj, "Base"):
            params["Base"] = _serialize_link_sub(obj.Base)
    elif "Chamfer" in type_id:
        if hasattr(obj, "Base"):
            params["Base"] = _serialize_link_sub(obj.Base)
        if hasattr(obj, "ChamferType"):
            params["ChamferType"] = str(obj.ChamferType)
    elif "Revolution" in type_id:
        if hasattr(obj, "Axis"):
            params["Axis"] = [float(obj.Axis.x), float(obj.Axis.y), float(obj.Axis.z)]
        if hasattr(obj, "Base"):
            params["Base"] = [float(obj.Base.x), float(obj.Base.y), float(obj.Base.z)]
    elif "Boolean" in type_id or "Cut" in type_id or "Fuse" in type_id:
        if hasattr(obj, "Tool"):
            params["Tool"] = obj.Tool.Name if obj.Tool else None
        if hasattr(obj, "Shapes"):
            params["Shapes"] = [s.Name for s in obj.Shapes] if obj.Shapes else []

    # Placement
    if hasattr(obj, "Placement"):
        p = obj.Placement
        params["Placement"] = {
            "Position": [float(p.Base.x), float(p.Base.y), float(p.Base.z)],
            "Rotation": [
                float(p.Rotation.Q[0]),
                float(p.Rotation.Q[1]),
                float(p.Rotation.Q[2]),
                float(p.Rotation.Q[3]),
            ],
        }

    return params


def _serialize_link_sub(link_sub: Any) -> dict[str, Any] | None:
    """Serialize a (Link, SubElements) tuple."""
    if link_sub is None:
        return None
    try:
        obj, subs = link_sub
        return {
            "object": obj.Name if obj else None,
            "subElements": list(subs) if subs else [],
        }
    except (TypeError, ValueError):
        return None


def _get_dependencies(obj: Any) -> list[str]:
    """Get the names of objects that this feature depends on."""
    deps = []
    for dep in getattr(obj, "OutList", []):
        deps.append(dep.Name)
    # Also check Profile/Sketch links common in PartDesign
    if hasattr(obj, "Profile") and obj.Profile:
        profile = obj.Profile
        if hasattr(profile, "__len__"):
            deps.extend(p.Name for p in profile if hasattr(p, "Name"))
        elif hasattr(profile, "Name"):
            deps.append(profile.Name)
    if hasattr(obj, "Sketch") and obj.Sketch:
        deps.append(obj.Sketch.Name)
    return list(set(deps))


# Feature types we know how to serialize
PARAMETRIC_TYPES = {
    "PartDesign::Pad",
    "PartDesign::Pocket",
    "PartDesign::Fillet",
    "PartDesign::Chamfer",
    "PartDesign::Revolution",
    "PartDesign::Groove",
    "PartDesign::Hole",
    "PartDesign::Mirrored",
    "PartDesign::LinearPattern",
    "PartDesign::PolarPattern",
    "PartDesign::MultiTransform",
    "PartDesign::AdditivePipe",
    "PartDesign::SubtractivePipe",
    "PartDesign::AdditiveLoft",
    "PartDesign::SubtractiveLoft",
    "Part::Cut",
    "Part::Fuse",
    "Part::Common",
    "Part::Extrusion",
    "Part::Revolution",
    "Part::Fillet",
    "Part::Chamfer",
    "Part::Box",
    "Part::Cylinder",
    "Part::Sphere",
    "Part::Cone",
    "Part::Torus",
}


def serialize_parametric_tree(doc: Any) -> dict[str, Any]:
    """
    Serialize the parametric feature tree of a FreeCAD document.

    Returns a dict with a "features" list, ordered by dependency.
    """
    features = []
    index = 0

    for obj in doc.Objects:
        type_id = getattr(obj, "TypeId", "")
        if type_id not in PARAMETRIC_TYPES:
            continue

        feature = {
            "name": obj.Name,
            "label": getattr(obj, "Label", obj.Name),
            "type": type_id,
            "index": index,
            "parameters": _extract_parameters(obj),
            "dependsOn": _get_dependencies(obj),
        }
        features.append(feature)
        index += 1

    return {"features": features, "featureCount": len(features)}
