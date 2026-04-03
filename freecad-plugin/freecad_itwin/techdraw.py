"""
TechDraw page serializer for Phase 3.

Exports TechDraw pages as SVG + structured JSON containing
dimensions, annotations, views, and balloon references.
"""

from __future__ import annotations

from typing import Any


def _serialize_view(view: Any) -> dict[str, Any]:
    """Serialize a TechDraw view."""
    data: dict[str, Any] = {
        "name": view.Name,
        "type": getattr(view, "TypeId", type(view).__name__),
    }

    if hasattr(view, "Source") and view.Source:
        sources = view.Source if isinstance(view.Source, (list, tuple)) else [view.Source]
        data["sourceObject"] = sources[0].Name if sources else ""

    if hasattr(view, "Direction"):
        d = view.Direction
        data["direction"] = [float(d.x), float(d.y), float(d.z)]

    if hasattr(view, "X") and hasattr(view, "Y"):
        data["position"] = [float(view.X), float(view.Y)]

    if hasattr(view, "Scale"):
        data["scale"] = float(view.Scale)

    return data


def _serialize_dimension(dim: Any) -> dict[str, Any]:
    """Serialize a TechDraw dimension."""
    data: dict[str, Any] = {
        "type": getattr(dim, "TypeId", type(dim).__name__),
        "references": [],
        "value": 0.0,
        "position": [0.0, 0.0],
    }

    if hasattr(dim, "References2D"):
        for ref in dim.References2D:
            try:
                data["references"].append(f"{ref[0].Name}:{ref[1]}")
            except (IndexError, TypeError):
                pass

    # Try to get the measured value
    for attr in ("RawValue", "Value"):
        if hasattr(dim, attr):
            data["value"] = float(getattr(dim, attr))
            break

    if hasattr(dim, "X") and hasattr(dim, "Y"):
        data["position"] = [float(dim.X), float(dim.Y)]

    if hasattr(dim, "FormatSpec"):
        data["formatSpec"] = str(dim.FormatSpec)

    return data


def _serialize_annotation(ann: Any) -> dict[str, Any]:
    """Serialize a TechDraw annotation."""
    data: dict[str, Any] = {
        "type": getattr(ann, "TypeId", type(ann).__name__),
        "text": "",
        "position": [0.0, 0.0],
    }

    if hasattr(ann, "Text"):
        data["text"] = str(ann.Text) if isinstance(ann.Text, str) else "\n".join(ann.Text)

    if hasattr(ann, "X") and hasattr(ann, "Y"):
        data["position"] = [float(ann.X), float(ann.Y)]

    return data


def serialize_techdraw_page(page: Any) -> dict[str, Any]:
    """
    Serialize a TechDraw page to a structured dict.

    Captures views, dimensions, annotations, and page metadata.
    """
    result: dict[str, Any] = {
        "pageName": page.Name,
        "template": "",
        "scale": 1.0,
        "views": [],
        "dimensions": [],
        "annotations": [],
    }

    if hasattr(page, "Template") and page.Template:
        tmpl = page.Template
        result["template"] = (
            str(tmpl.Template) if hasattr(tmpl, "Template") else str(tmpl)
        )

    if hasattr(page, "Scale"):
        result["scale"] = float(page.Scale)

    # Collect views, dimensions, annotations from page's children
    for view in getattr(page, "Views", []):
        type_id = getattr(view, "TypeId", "")

        if "Dimension" in type_id:
            result["dimensions"].append(_serialize_dimension(view))
        elif "Annotation" in type_id or "Balloon" in type_id:
            result["annotations"].append(_serialize_annotation(view))
        elif "View" in type_id or "DrawView" in type_id:
            result["views"].append(_serialize_view(view))

    return result


def export_techdraw_svg(page: Any) -> bytes | None:
    """
    Export a TechDraw page to SVG bytes.

    Requires FreeCAD's TechDraw module.
    """
    try:
        import TechDraw

        svg_string = TechDraw.writeSVGPage(page)
        return svg_string.encode("utf-8")
    except Exception:
        return None
