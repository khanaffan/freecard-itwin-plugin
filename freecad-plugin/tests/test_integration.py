"""
Integration test for the full export pipeline.

Creates a synthetic .fcitwin bundle with all data types
(shapes, sketches, parametric tree, drawings, GUI state)
and verifies the bundle can be read back correctly.
"""

from pathlib import Path

from freecad_itwin.bundle import (
    BundleReader,
    BundleWriter,
    GuiStateEntry,
    ObjectEntry,
)


def _create_full_bundle(tmp_path: Path) -> Path:
    """Create a comprehensive .fcitwin bundle for testing."""
    bundle_path = tmp_path / "integration.fcitwin"
    writer = BundleWriter(bundle_path)

    writer.set_source("TestModel.FCStd", "sha256hash", "0.21.2")

    # Parametric tree
    tree = {
        "features": [
            {
                "name": "Sketch",
                "label": "Sketch",
                "type": "Sketcher::SketchObject",
                "index": 0,
                "parameters": {},
                "dependsOn": [],
            },
            {
                "name": "Pad",
                "label": "Pad",
                "type": "PartDesign::Pad",
                "index": 1,
                "parameters": {"Length": 20.0, "Type": "Length", "Reversed": False},
                "dependsOn": ["Sketch"],
            },
            {
                "name": "Pocket",
                "label": "Pocket",
                "type": "PartDesign::Pocket",
                "index": 2,
                "parameters": {"Length": 5.0, "Type": "Length"},
                "dependsOn": ["Sketch002"],
            },
            {
                "name": "Fillet",
                "label": "Fillet",
                "type": "PartDesign::Fillet",
                "index": 3,
                "parameters": {"Size": 2.0},
                "dependsOn": ["Pad"],
            },
        ],
        "featureCount": 4,
    }
    writer.set_parametric_tree(tree)

    # Sketch
    sketch = {
        "geometry": [
            {"id": 0, "type": "LineSegment", "data": {"startPoint": [0, 0], "endPoint": [50, 0]}},
            {"id": 1, "type": "LineSegment", "data": {"startPoint": [50, 0], "endPoint": [50, 30]}},
            {"id": 2, "type": "LineSegment", "data": {"startPoint": [50, 30], "endPoint": [0, 30]}},
            {"id": 3, "type": "LineSegment", "data": {"startPoint": [0, 30], "endPoint": [0, 0]}},
        ],
        "constraints": [
            {"type": "Horizontal", "geometryRefs": [0]},
            {"type": "Vertical", "geometryRefs": [1]},
            {"type": "Horizontal", "geometryRefs": [2]},
            {"type": "Vertical", "geometryRefs": [3]},
            {"type": "Coincident", "geometryRefs": [0, 1]},
            {"type": "Coincident", "geometryRefs": [1, 2]},
            {"type": "Coincident", "geometryRefs": [2, 3]},
            {"type": "Coincident", "geometryRefs": [3, 0]},
            {"type": "DistanceX", "geometryRefs": [0], "value": 50.0, "name": "Width"},
            {"type": "DistanceY", "geometryRefs": [1], "value": 30.0, "name": "Height"},
        ],
        "plane": {"origin": [0, 0, 0], "normal": [0, 0, 1]},
    }
    sketch_path = writer.add_sketch("Sketch", sketch)

    # Body with BREP and mesh
    brep_data = b"CASCADE BREP REPRESENTATION v1\n(mock data)"
    mesh_data = (
        b"# Tessellation of Body\n"
        b"v 0.0 0.0 0.0\nv 50.0 0.0 0.0\nv 50.0 30.0 0.0\nv 0.0 30.0 0.0\n"
        b"v 0.0 0.0 20.0\nv 50.0 0.0 20.0\nv 50.0 30.0 20.0\nv 0.0 30.0 20.0\n"
        b"f 1 2 3\nf 1 3 4\nf 5 6 7\nf 5 7 8\n"
        b"f 1 2 6\nf 1 6 5\nf 2 3 7\nf 2 7 6\n"
    )
    shape_path = writer.add_shape("Body", brep_data)
    mesh_path = writer.add_mesh("Body", mesh_data)

    # Drawing
    drawing = {
        "pageName": "Page001",
        "template": "A4_Landscape",
        "scale": 1.0,
        "views": [
            {"name": "Front", "type": "DrawViewPart", "sourceObject": "Body",
             "direction": [0, 0, 1], "position": [100, 150], "scale": 1.0},
            {"name": "Side", "type": "DrawViewPart", "sourceObject": "Body",
             "direction": [1, 0, 0], "position": [250, 150], "scale": 1.0},
        ],
        "dimensions": [
            {
                "type": "DistanceX", "references": ["Front:Edge1"],
                "value": 50.0, "position": [100, 50],
            },
            {
                "type": "DistanceY", "references": ["Front:Edge2"],
                "value": 30.0, "position": [180, 150],
            },
        ],
        "annotations": [
            {"type": "Text", "text": "TestModel Rev A", "position": [200, 20]},
        ],
    }
    svg_data = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="297" height="210"/></svg>'
    draw_path = writer.add_drawing("Page001", drawing, svg_data)

    # Objects
    writer.add_object(ObjectEntry(
        id="uuid-body", name="Body", type="PartDesign::Body",
        shape_file=shape_path, mesh_file=mesh_path,
    ))
    writer.add_object(ObjectEntry(
        id="uuid-sketch", name="Sketch", type="Sketcher::SketchObject",
        parent_id="uuid-body", sketch_file=sketch_path,
    ))
    writer.add_object(ObjectEntry(
        id="uuid-page", name="Page001", type="TechDraw::DrawPage",
        drawing_file=draw_path,
    ))

    # GUI state
    writer.add_gui_state(GuiStateEntry(
        object_id="uuid-body",
        shape_color="#4488cc",
        line_color="#000000",
        line_width=2.0,
        transparency=0.0,
        visibility=True,
        display_mode="Flat Lines",
    ))

    # Properties
    writer.set_properties({
        "uuid-body": {
            "Material": "Steel AISI 304",
            "Weight": 1.5,
            "Revision": "A",
        }
    })

    writer.write()
    return bundle_path


class TestIntegrationFullBundle:
    def test_full_bundle_creation_and_reading(self, tmp_path):
        """Verify a comprehensive bundle can be written and read back."""
        bundle_path = _create_full_bundle(tmp_path)
        assert bundle_path.exists()

        with BundleReader(bundle_path) as reader:
            # Manifest
            assert reader.manifest.version == "0.1.0"
            assert reader.manifest.source_file_name == "TestModel.FCStd"
            assert reader.manifest.source_file_hash == "sha256hash"
            assert reader.manifest.freecad_version == "0.21.2"
            assert len(reader.manifest.objects) == 3

            # Objects
            body = reader.manifest.objects[0]
            assert body.name == "Body"
            assert body.type == "PartDesign::Body"
            assert body.shape_file == "shapes/Body.brep"
            assert body.mesh_file == "shapes/Body.obj"

            sketch_obj = reader.manifest.objects[1]
            assert sketch_obj.name == "Sketch"
            assert sketch_obj.parent_id == "uuid-body"

            page_obj = reader.manifest.objects[2]
            assert page_obj.name == "Page001"
            assert page_obj.drawing_file == "drawings/Page001.json"

            # BREP
            brep = reader.read_file("shapes/Body.brep")
            assert b"CASCADE" in brep

            # Mesh (OBJ)
            mesh = reader.read_mesh("shapes/Body.obj")
            assert "v 50.0 0.0 0.0" in mesh
            assert "f 1 2 3" in mesh

            # Parametric tree
            tree = reader.read_parametric_tree()
            assert tree is not None
            assert tree["featureCount"] == 4
            assert tree["features"][1]["type"] == "PartDesign::Pad"
            assert tree["features"][1]["parameters"]["Length"] == 20.0
            assert tree["features"][3]["parameters"]["Size"] == 2.0

            # Sketch
            sketch_data = reader.read_json("sketches/Sketch.json")
            assert len(sketch_data["geometry"]) == 4
            assert len(sketch_data["constraints"]) == 10
            named = [c for c in sketch_data["constraints"] if c.get("name")]
            assert len(named) == 2

            # Drawing
            draw_data = reader.read_json("drawings/Page001.json")
            assert draw_data["pageName"] == "Page001"
            assert len(draw_data["views"]) == 2
            assert len(draw_data["dimensions"]) == 2
            assert len(draw_data["annotations"]) == 1

            svg = reader.read_file("drawings/Page001.svg")
            assert b"<svg" in svg

            # GUI state
            gui = reader.read_gui_state()
            assert len(gui) == 1
            assert gui[0].shape_color == "#4488cc"
            assert gui[0].display_mode == "Flat Lines"

            # Properties
            props = reader.read_json("properties.json")
            assert props["uuid-body"]["Material"] == "Steel AISI 304"

            # File listing
            files = reader.list_files()
            assert len(files) >= 8

    def test_bundle_file_count(self, tmp_path):
        """Verify all expected files are in the bundle."""
        bundle_path = _create_full_bundle(tmp_path)

        with BundleReader(bundle_path) as reader:
            files = set(reader.list_files())
            expected = {
                "manifest.json",
                "gui-state.json",
                "parametric-tree.json",
                "properties.json",
                "shapes/Body.brep",
                "shapes/Body.obj",
                "sketches/Sketch.json",
                "drawings/Page001.json",
                "drawings/Page001.svg",
            }
            assert expected.issubset(files)
