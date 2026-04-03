"""
FreeCAD document exporter — serializes FreeCAD documents to .fcitwin bundles.

This module is designed to run inside FreeCAD's Python environment where
the FreeCAD and FreeCADGui modules are available. For testing outside
FreeCAD, mock objects are used.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

from .bundle import BundleWriter, GuiStateEntry, ObjectEntry


def _get_object_uuid(obj: Any) -> str:
    """Get or generate a stable UUID for a FreeCAD object."""
    # FreeCAD 0.21+ objects may have an ID property
    if hasattr(obj, "ID") and obj.ID:
        return str(obj.ID)
    # Fall back to name-based UUID for determinism
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"freecad:{obj.Document.Name}/{obj.Name}"))


def _color_to_hex(color_tuple: tuple) -> str:
    """Convert FreeCAD color tuple (r, g, b, a) with 0-1 floats to hex string."""
    if not color_tuple:
        return "#000000"
    r, g, b = int(color_tuple[0] * 255), int(color_tuple[1] * 255), int(color_tuple[2] * 255)
    return f"#{r:02x}{g:02x}{b:02x}"


def _compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _export_brep(obj: Any) -> bytes | None:
    """Export an object's shape as BREP bytes."""
    if not hasattr(obj, "Shape") or obj.Shape.isNull():
        return None
    return obj.Shape.exportBrepToString().encode("utf-8")


def _tessellate_to_obj(obj: Any, name: str) -> bytes | None:
    """Tessellate an object's shape to OBJ format."""
    if not hasattr(obj, "Shape") or obj.Shape.isNull():
        return None
    try:
        mesh_data = obj.Shape.tessellate(0.1)  # tolerance
        vertices, faces = mesh_data
        lines = [f"# FreeCAD tessellation of {name}\n"]
        for v in vertices:
            lines.append(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for f in faces:
            lines.append(f"f {f[0]+1} {f[1]+1} {f[2]+1}\n")
        return "".join(lines).encode("utf-8")
    except Exception:
        return None


def _get_gui_state(obj: Any) -> GuiStateEntry | None:
    """Extract visual properties from a FreeCAD object's ViewObject."""
    try:
        import FreeCADGui  # noqa: F811

        if not FreeCADGui.activeDocument():
            return None
    except ImportError:
        pass

    view = getattr(obj, "ViewObject", None)
    if view is None:
        return None

    entry = GuiStateEntry(object_id=_get_object_uuid(obj))
    if hasattr(view, "ShapeColor"):
        entry.shape_color = _color_to_hex(view.ShapeColor)
    if hasattr(view, "LineColor"):
        entry.line_color = _color_to_hex(view.LineColor)
    if hasattr(view, "LineWidth"):
        entry.line_width = float(view.LineWidth)
    if hasattr(view, "Transparency"):
        entry.transparency = float(view.Transparency) / 100.0
    if hasattr(view, "Visibility"):
        entry.visibility = bool(view.Visibility)
    if hasattr(view, "DisplayMode"):
        entry.display_mode = str(view.DisplayMode)
    return entry


def _get_freecad_version() -> str:
    """Get the running FreeCAD version string."""
    try:
        import FreeCAD

        ver = FreeCAD.Version()
        return f"{ver[0]}.{ver[1]}.{ver[2]}"
    except Exception:
        return "unknown"


def _is_exportable(obj: Any) -> bool:
    """Check if a FreeCAD object should be exported."""
    type_id = getattr(obj, "TypeId", "")
    # Skip internal objects
    skip_types = {"App::Origin", "App::Line", "App::Plane"}
    if type_id in skip_types:
        return False
    # Must have a shape or be a container
    has_shape = hasattr(obj, "Shape") and not getattr(obj.Shape, "isNull", lambda: True)()
    is_container = type_id in {
        "App::Part",
        "PartDesign::Body",
        "App::DocumentObjectGroup",
    }
    return has_shape or is_container


def _get_parent_uuid(obj: Any) -> str | None:
    """Get the UUID of the object's parent container."""
    for parent in getattr(obj, "InList", []):
        parent_type = getattr(parent, "TypeId", "")
        if parent_type in {"App::Part", "PartDesign::Body", "App::DocumentObjectGroup"}:
            return _get_object_uuid(parent)
    return None


def export_document(
    doc: Any,
    output_path: str,
    source_path: str | None = None,
) -> str:
    """
    Export a FreeCAD document to a .fcitwin bundle.

    Args:
        doc: FreeCAD.Document object
        output_path: Path for the output .fcitwin file
        source_path: Path to the source .FCStd file (for hash computation)

    Returns:
        Path to the created .fcitwin file
    """
    writer = BundleWriter(output_path)

    file_hash = ""
    file_name = doc.Name + ".FCStd"
    if source_path and Path(source_path).exists():
        file_hash = _compute_file_hash(source_path)
        file_name = Path(source_path).name

    writer.set_source(
        file_name=file_name,
        file_hash=file_hash,
        freecad_version=_get_freecad_version(),
    )

    for obj in doc.Objects:
        if not _is_exportable(obj):
            continue

        obj_uuid = _get_object_uuid(obj)
        entry = ObjectEntry(
            id=obj_uuid,
            name=obj.Name,
            type=getattr(obj, "TypeId", type(obj).__name__),
            parent_id=_get_parent_uuid(obj),
        )

        # Export BREP shape
        brep_data = _export_brep(obj)
        if brep_data:
            entry.shape_file = writer.add_shape(obj.Name, brep_data)

        # Export tessellated mesh
        mesh_data = _tessellate_to_obj(obj, obj.Name)
        if mesh_data:
            entry.mesh_file = writer.add_mesh(obj.Name, mesh_data)

        writer.add_object(entry)

        # Capture GUI state
        gui_entry = _get_gui_state(obj)
        if gui_entry:
            writer.add_gui_state(gui_entry)

    result = writer.write()
    return str(result)
