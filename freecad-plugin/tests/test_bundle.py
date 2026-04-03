"""Tests for the .fcitwin bundle format (read/write)."""


import pytest

from freecad_itwin.bundle import (
    BundleReader,
    BundleWriter,
    GuiStateEntry,
    Manifest,
    ObjectEntry,
)


class TestObjectEntry:
    def test_to_dict_minimal(self):
        entry = ObjectEntry(id="uuid-1", name="Body", type="PartDesign::Body")
        d = entry.to_dict()
        assert d == {"id": "uuid-1", "name": "Body", "type": "PartDesign::Body"}

    def test_to_dict_full(self):
        entry = ObjectEntry(
            id="uuid-1",
            name="Body",
            type="PartDesign::Body",
            parent_id="uuid-0",
            shape_file="shapes/Body.brep",
            mesh_file="shapes/Body.obj",
        )
        d = entry.to_dict()
        assert d["parentId"] == "uuid-0"
        assert d["shapeFile"] == "shapes/Body.brep"
        assert d["meshFile"] == "shapes/Body.obj"

    def test_round_trip(self):
        entry = ObjectEntry(
            id="uuid-1", name="Body", type="Part::Feature",
            parent_id="p", shape_file="s.brep", mesh_file="m.obj",
            sketch_file="sk.json", drawing_file="dr.json",
        )
        restored = ObjectEntry.from_dict(entry.to_dict())
        assert restored.id == entry.id
        assert restored.parent_id == entry.parent_id
        assert restored.sketch_file == entry.sketch_file


class TestManifest:
    def test_to_dict(self):
        m = Manifest(
            source_file_name="test.FCStd",
            source_file_hash="abc123",
            freecad_version="0.21.0",
        )
        d = m.to_dict()
        assert d["source"]["fileName"] == "test.FCStd"
        assert d["version"] == "0.1.0"

    def test_round_trip(self):
        m = Manifest(
            source_file_name="test.FCStd",
            source_file_hash="abc",
            freecad_version="0.21.0",
            objects=[ObjectEntry(id="1", name="Box", type="Part::Box")],
        )
        restored = Manifest.from_dict(m.to_dict())
        assert restored.source_file_name == "test.FCStd"
        assert len(restored.objects) == 1
        assert restored.objects[0].name == "Box"


class TestGuiStateEntry:
    def test_to_dict(self):
        g = GuiStateEntry(
            object_id="uuid-1",
            shape_color="#ff0000",
            transparency=0.5,
            visibility=True,
        )
        d = g.to_dict()
        assert d["objectId"] == "uuid-1"
        assert d["shapeColor"] == "#ff0000"
        assert d["transparency"] == 0.5

    def test_from_dict(self):
        d = {"objectId": "uuid-1", "shapeColor": "#00ff00", "visibility": False}
        g = GuiStateEntry.from_dict(d)
        assert g.object_id == "uuid-1"
        assert g.shape_color == "#00ff00"
        assert g.visibility is False


class TestBundleWriterReader:
    def test_write_and_read_basic(self, tmp_path):
        bundle_path = tmp_path / "test.fcitwin"
        writer = BundleWriter(bundle_path)
        writer.set_source("test.FCStd", "hash123", "0.21.0")
        writer.add_object(ObjectEntry(
            id="uuid-1", name="Body", type="PartDesign::Body",
            shape_file="shapes/Body.brep", mesh_file="shapes/Body.obj",
        ))
        writer.add_shape("Body", b"BREP DATA HERE")
        writer.add_mesh("Body", b"v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
        writer.add_gui_state(GuiStateEntry(
            object_id="uuid-1", shape_color="#ff0000", transparency=0.25,
        ))
        writer.write()

        assert bundle_path.exists()

        with BundleReader(bundle_path) as reader:
            assert reader.manifest.source_file_name == "test.FCStd"
            assert reader.manifest.source_file_hash == "hash123"
            assert len(reader.manifest.objects) == 1
            assert reader.manifest.objects[0].name == "Body"

            gui = reader.read_gui_state()
            assert len(gui) == 1
            assert gui[0].shape_color == "#ff0000"

            brep = reader.read_file("shapes/Body.brep")
            assert brep == b"BREP DATA HERE"

            mesh = reader.read_mesh("shapes/Body.obj")
            assert "v 0 0 0" in mesh

    def test_write_with_sketches(self, tmp_path):
        bundle_path = tmp_path / "sketch.fcitwin"
        writer = BundleWriter(bundle_path)
        writer.set_source("sketch.FCStd", "h", "0.21.0")

        sketch_data = {
            "geometry": [
                {
                    "id": 0, "type": "LineSegment",
                    "data": {"startPoint": [0, 0], "endPoint": [10, 0]},
                },
            ],
            "constraints": [{"type": "Horizontal", "geometryRefs": [0]}],
            "plane": {"origin": [0, 0, 0], "normal": [0, 0, 1]},
        }
        sketch_path = writer.add_sketch("Sketch001", sketch_data)
        writer.add_object(ObjectEntry(
            id="s1", name="Sketch001", type="Sketcher::SketchObject",
            sketch_file=sketch_path,
        ))
        writer.write()

        with BundleReader(bundle_path) as reader:
            obj = reader.manifest.objects[0]
            assert obj.sketch_file == "sketches/Sketch001.json"
            sketch = reader.read_json(obj.sketch_file)
            assert len(sketch["geometry"]) == 1
            assert sketch["geometry"][0]["type"] == "LineSegment"

    def test_write_with_parametric_tree(self, tmp_path):
        bundle_path = tmp_path / "param.fcitwin"
        writer = BundleWriter(bundle_path)
        writer.set_source("param.FCStd", "h", "0.21.0")

        tree = {
            "features": [
                {"name": "Pad", "type": "PartDesign::Pad", "index": 0,
                 "parameters": {"Length": 10.0}, "dependsOn": ["Sketch"]},
            ],
            "featureCount": 1,
        }
        writer.set_parametric_tree(tree)
        writer.add_object(ObjectEntry(id="p1", name="Body", type="PartDesign::Body"))
        writer.write()

        with BundleReader(bundle_path) as reader:
            assert reader.manifest.parametric_tree_file == "parametric-tree.json"
            tree_data = reader.read_parametric_tree()
            assert tree_data is not None
            assert len(tree_data["features"]) == 1

    def test_write_with_drawings(self, tmp_path):
        bundle_path = tmp_path / "draw.fcitwin"
        writer = BundleWriter(bundle_path)
        writer.set_source("draw.FCStd", "h", "0.21.0")

        drawing = {
            "pageName": "Page001",
            "template": "A4_Landscape",
            "scale": 1.0,
            "views": [{"name": "View1", "type": "DrawViewPart", "sourceObject": "Body"}],
            "dimensions": [],
            "annotations": [],
        }
        svg_data = b"<svg>test</svg>"
        draw_path = writer.add_drawing("Page001", drawing, svg_data)
        writer.add_object(ObjectEntry(
            id="d1", name="Page001", type="TechDraw::DrawPage",
            drawing_file=draw_path,
        ))
        writer.write()

        with BundleReader(bundle_path) as reader:
            obj = reader.manifest.objects[0]
            assert obj.drawing_file == "drawings/Page001.json"
            drawing_data = reader.read_json(obj.drawing_file)
            assert drawing_data["pageName"] == "Page001"
            svg = reader.read_file("drawings/Page001.svg")
            assert svg == b"<svg>test</svg>"

    def test_list_files(self, tmp_path):
        bundle_path = tmp_path / "files.fcitwin"
        writer = BundleWriter(bundle_path)
        writer.set_source("f.FCStd", "h", "0.21.0")
        writer.add_shape("Body", b"brep")
        writer.add_mesh("Body", b"obj")
        writer.add_gui_state(GuiStateEntry(object_id="1"))
        writer.add_object(ObjectEntry(id="1", name="Body", type="Part::Feature"))
        writer.write()

        with BundleReader(bundle_path) as reader:
            files = reader.list_files()
            assert "manifest.json" in files
            assert "gui-state.json" in files
            assert "shapes/Body.brep" in files
            assert "shapes/Body.obj" in files

    def test_reader_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            BundleReader("/nonexistent/path.fcitwin")
