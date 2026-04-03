"""
.fcitwin bundle format — ZIP-based intermediate exchange format.

A .fcitwin bundle is a ZIP archive containing:
  manifest.json          — metadata, object list, file references
  shapes/<name>.brep     — OpenCASCADE BREP geometry
  shapes/<name>.obj      — tessellated mesh for visualization
  gui-state.json         — visual properties per object
  sketches/<name>.json   — sketch geometry + constraints (Phase 2)
  parametric-tree.json   — parametric feature tree (Phase 2)
  drawings/<name>.json   — TechDraw page data (Phase 3)
  drawings/<name>.svg    — TechDraw SVG rendering (Phase 3)
  properties.json        — user-defined properties (Phase 2)
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ObjectEntry:
    """An object in the .fcitwin manifest."""

    id: str
    name: str
    type: str
    parent_id: str | None = None
    shape_file: str | None = None
    mesh_file: str | None = None
    sketch_file: str | None = None
    drawing_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id, "name": self.name, "type": self.type}
        if self.parent_id:
            d["parentId"] = self.parent_id
        if self.shape_file:
            d["shapeFile"] = self.shape_file
        if self.mesh_file:
            d["meshFile"] = self.mesh_file
        if self.sketch_file:
            d["sketchFile"] = self.sketch_file
        if self.drawing_file:
            d["drawingFile"] = self.drawing_file
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ObjectEntry:
        return cls(
            id=d["id"],
            name=d["name"],
            type=d["type"],
            parent_id=d.get("parentId"),
            shape_file=d.get("shapeFile"),
            mesh_file=d.get("meshFile"),
            sketch_file=d.get("sketchFile"),
            drawing_file=d.get("drawingFile"),
        )


@dataclass
class Manifest:
    """The manifest.json content for a .fcitwin bundle."""

    version: str = "0.1.0"
    generator: str = "freecad-itwin-0.1.0"
    source_file_name: str = ""
    source_file_hash: str = ""
    freecad_version: str = ""
    objects: list[ObjectEntry] = field(default_factory=list)
    parametric_tree_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "version": self.version,
            "generator": self.generator,
            "source": {
                "fileName": self.source_file_name,
                "fileHash": self.source_file_hash,
                "freecadVersion": self.freecad_version,
            },
            "objects": [o.to_dict() for o in self.objects],
        }
        if self.parametric_tree_file:
            d["parametricTreeFile"] = self.parametric_tree_file
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Manifest:
        src = d.get("source", {})
        return cls(
            version=d["version"],
            generator=d.get("generator", ""),
            source_file_name=src.get("fileName", ""),
            source_file_hash=src.get("fileHash", ""),
            freecad_version=src.get("freecadVersion", ""),
            objects=[ObjectEntry.from_dict(o) for o in d.get("objects", [])],
            parametric_tree_file=d.get("parametricTreeFile"),
        )


@dataclass
class GuiStateEntry:
    """Visual properties for a single object."""

    object_id: str
    shape_color: str | None = None
    line_color: str | None = None
    line_width: float | None = None
    transparency: float | None = None
    visibility: bool = True
    display_mode: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"objectId": self.object_id}
        if self.shape_color is not None:
            d["shapeColor"] = self.shape_color
        if self.line_color is not None:
            d["lineColor"] = self.line_color
        if self.line_width is not None:
            d["lineWidth"] = self.line_width
        if self.transparency is not None:
            d["transparency"] = self.transparency
        d["visibility"] = self.visibility
        if self.display_mode is not None:
            d["displayMode"] = self.display_mode
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GuiStateEntry:
        return cls(
            object_id=d["objectId"],
            shape_color=d.get("shapeColor"),
            line_color=d.get("lineColor"),
            line_width=d.get("lineWidth"),
            transparency=d.get("transparency"),
            visibility=d.get("visibility", True),
            display_mode=d.get("displayMode"),
        )


class BundleWriter:
    """Writes a .fcitwin ZIP bundle."""

    def __init__(self, output_path: str | Path):
        self.output_path = Path(output_path)
        self.manifest = Manifest()
        self._gui_state: list[GuiStateEntry] = []
        self._files: dict[str, bytes] = {}

    def set_source(
        self, file_name: str, file_hash: str, freecad_version: str
    ) -> None:
        self.manifest.source_file_name = file_name
        self.manifest.source_file_hash = file_hash
        self.manifest.freecad_version = freecad_version

    def add_object(self, entry: ObjectEntry) -> None:
        self.manifest.objects.append(entry)

    def add_shape(self, name: str, brep_data: bytes) -> str:
        path = f"shapes/{name}.brep"
        self._files[path] = brep_data
        return path

    def add_mesh(self, name: str, obj_data: bytes) -> str:
        path = f"shapes/{name}.obj"
        self._files[path] = obj_data
        return path

    def add_gui_state(self, entry: GuiStateEntry) -> None:
        self._gui_state.append(entry)

    def add_sketch(self, name: str, sketch_json: dict) -> str:
        path = f"sketches/{name}.json"
        self._files[path] = json.dumps(sketch_json, indent=2).encode("utf-8")
        return path

    def add_drawing(self, name: str, drawing_json: dict, svg_data: bytes | None = None) -> str:
        json_path = f"drawings/{name}.json"
        self._files[json_path] = json.dumps(drawing_json, indent=2).encode("utf-8")
        if svg_data is not None:
            svg_path = f"drawings/{name}.svg"
            self._files[svg_path] = svg_data
        return json_path

    def set_parametric_tree(self, tree_json: dict) -> None:
        path = "parametric-tree.json"
        self._files[path] = json.dumps(tree_json, indent=2).encode("utf-8")
        self.manifest.parametric_tree_file = path

    def set_properties(self, properties_json: dict) -> None:
        self._files["properties.json"] = json.dumps(properties_json, indent=2).encode("utf-8")

    def write(self) -> Path:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self.output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(self.manifest.to_dict(), indent=2))
            if self._gui_state:
                gui_data = [g.to_dict() for g in self._gui_state]
                zf.writestr("gui-state.json", json.dumps(gui_data, indent=2))
            for path, data in self._files.items():
                zf.writestr(path, data)
        return self.output_path


class BundleReader:
    """Reads a .fcitwin ZIP bundle."""

    def __init__(self, bundle_path: str | Path):
        self.bundle_path = Path(bundle_path)
        if not self.bundle_path.exists():
            raise FileNotFoundError(f"Bundle not found: {self.bundle_path}")
        self._zf = zipfile.ZipFile(self.bundle_path, "r")
        self.manifest = Manifest.from_dict(
            json.loads(self._zf.read("manifest.json"))
        )

    def close(self) -> None:
        self._zf.close()

    def __enter__(self) -> BundleReader:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def read_gui_state(self) -> list[GuiStateEntry]:
        if "gui-state.json" not in self._zf.namelist():
            return []
        data = json.loads(self._zf.read("gui-state.json"))
        return [GuiStateEntry.from_dict(d) for d in data]

    def read_mesh(self, mesh_path: str) -> str | None:
        """Read tessellated mesh (OBJ format) as string."""
        if mesh_path not in self._zf.namelist():
            return None
        return self._zf.read(mesh_path).decode("utf-8")

    def read_file(self, path: str) -> bytes:
        return self._zf.read(path)

    def read_json(self, path: str) -> Any:
        return json.loads(self._zf.read(path))

    def read_parametric_tree(self) -> dict | None:
        if self.manifest.parametric_tree_file:
            return self.read_json(self.manifest.parametric_tree_file)
        return None

    def list_files(self) -> list[str]:
        return self._zf.namelist()
