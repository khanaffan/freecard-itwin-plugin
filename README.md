# FreeCAD → iTwin.js Export Plugin

[![License: LGPL v2.1](https://img.shields.io/badge/License-LGPL_v2.1-blue.svg)](LICENSE)

Export FreeCAD drawings (`.FCStd`) to Bentley iTwin.js iModels with **round-trip fidelity** — every exported iModel contains sufficient data to fully recreate the original FreeCAD drawing, including parametric definitions, constraint history, BREP topology, visual styling, and metadata.

---

## Table of Contents

- [Why This Plugin?](#why-this-plugin)
- [Architecture](#architecture)
- [The `.fcitwin` Bundle Format](#the-fcitwin-bundle-format)
- [FreeCAD Domain ECSchema](#freecad-domain-ecschema)
- [Data Mapping](#data-mapping)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Development](#development)
- [Project Structure](#project-structure)
- [Roadmap](#roadmap)
- [License](#license)

---

## Why This Plugin?

FreeCAD is a powerful open-source parametric 3D CAD modeler, but it exists in isolation from the Bentley iTwin ecosystem. Engineers who use FreeCAD cannot participate in iTwin-based digital twin workflows without manually re-modeling their designs.

This plugin bridges that gap with a **dual-representation** approach:

1. **Visualization Layer** — tessellated meshes and BIS-standard geometry that any iTwin.js viewer can render natively
2. **Reconstruction Layer** — FreeCAD-specific aspects containing the exact data needed to rebuild the original `.FCStd` file

## Architecture

```
┌──────────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  FreeCAD Application │     │  .fcitwin Bundle  │     │  iModel (.bim)   │
│                      │     │  (ZIP archive)    │     │                  │
│  Python Exporter ────┼────▶│  manifest.json    │     │  BIS Elements    │
│  Parametric Tree     │     │  shapes/*.brep    │────▶│  + FreeCAD       │
│  Sketch Serializer   │     │  shapes/*.obj     │     │    Domain        │
│  TechDraw Exporter   │     │  sketches/*.json  │     │    Aspects       │
│  Assembly Exporter   │     │  gui-state.json   │     │                  │
│                      │     │  parametric-tree  │     │  Geometry        │
│  Python Importer ◀───┼─────│  drawings/*.svg   │◀────│  BREP blobs      │
│                      │     │                   │     │  GUI style       │
└──────────────────────┘     └──────────────────┘     └──────────────────┘
     freecad-plugin/                                    itwin-connector/
```

Three components:

| Component | Language | Directory | Purpose |
|-----------|----------|-----------|---------|
| **FreeCAD Export Plugin** | Python 3.9+ | `freecad-plugin/` | Serializes FreeCAD documents into `.fcitwin` bundles and reconstructs documents from them |
| **Intermediate Format** | JSON + BREP + OBJ | `.fcitwin` ZIP | Language-agnostic, human-readable bridge between Python and TypeScript |
| **iTwin.js Connector** | TypeScript (Node 18+) | `itwin-connector/` | Maps `.fcitwin` data into BIS-conformant iModel elements with FreeCAD domain aspects |

---

## The `.fcitwin` Bundle Format

A `.fcitwin` file is a ZIP archive serving as the bridge between FreeCAD and iTwin.js:

```
manifest.json              ← object list, source info, file references
shapes/
  ├── Body001.brep         ← OpenCASCADE BREP (exact geometry)
  └── Body001.obj          ← tessellated mesh (for iTwin visualization)
sketches/
  ├── Sketch001.json       ← geometry primitives + constraints
  └── Sketch002.json
drawings/
  ├── Page001.json         ← structured annotation/dimension data
  └── Page001.svg          ← TechDraw SVG rendering
parametric-tree.json       ← ordered feature list with parameters & dependencies
gui-state.json             ← colors, transparency, visibility per object
properties.json            ← user-defined key-value metadata
```

A JSON schema for `manifest.json` is available at [`freecad-plugin/freecad_itwin/manifest_schema.json`](freecad-plugin/freecad_itwin/manifest_schema.json).

---

## FreeCAD Domain ECSchema

A custom ECSchema ([`FreeCAD.ecschema.xml`](itwin-connector/src/FreeCAD.ecschema.xml)) extends BIS to store FreeCAD-specific data inside iModels:

| Schema Class | Base Class | Purpose |
|-------------|------------|---------|
| `SourceDocument` | `bis:DefinitionElement` | Source file metadata, FreeCAD version, shape hash |
| `ParametricDefinition` | `bis:ElementMultiAspect` | One aspect per feature (Pad, Fillet, etc.) with parameters and dependencies |
| `SketchDefinition` | `bis:ElementUniqueAspect` | Sketch geometry and constraints with support plane |
| `BrepGeometry` | `bis:ElementUniqueAspect` | Compressed OpenCASCADE BREP blob for exact reconstruction |
| `GuiStyle` | `bis:ElementUniqueAspect` | Colors, transparency, line widths, visibility, display mode |
| `TechDrawPage` | `bis:DrawingGraphic` | Drawing page template, scale, annotations, SVG data |

---

## Data Mapping

| FreeCAD Concept | iModel Element | Round-Trip Aspect |
|----------------|----------------|-------------------|
| Part Body | `PhysicalElement` with tessellated mesh | `BrepGeometry` + `ParametricDefinition[]` |
| Sketch | `GeometricElement3d` | `SketchDefinition` (geometry + constraints) |
| Pad, Pocket, Fillet, etc. | Aspects on parent Body | `ParametricDefinition` (ordered by `FeatureIndex`) |
| Part container | `PhysicalElement` (parent) | BIS parent-child relationship |
| Assembly (Assembly4) | `PhysicalElement` hierarchy | Assembly constraints as `ParametricDefinition` |
| TechDraw page | `TechDrawPage` in `DrawingModel` | SVG + annotation JSON |
| Colors / styling | `RenderMaterial` + `GuiStyle` | Full GUI state for reconstruction |

---

## Quick Start

### Requirements

- **FreeCAD** 0.21+ (for export/import — uses FreeCAD's Python API)
- **Python** 3.9+
- **Node.js** 18+

### Export from FreeCAD

```python
# In FreeCAD's Python console or as a macro
from freecad_itwin import exporter

exporter.export_document(
    FreeCAD.ActiveDocument,
    "/path/to/output.fcitwin",
    source_path="/path/to/source.FCStd",  # optional, for hash verification
)
```

### Convert to iModel Elements

```bash
cd itwin-connector
npm install
npm run build
npm run convert -- --input /path/to/output.fcitwin --output /path/to/output.elements.json
```

### Round-Trip: Import Back to FreeCAD

```python
from freecad_itwin import importer

results = importer.import_bundle(
    "/path/to/output.fcitwin",
    doc=FreeCAD.ActiveDocument,  # or None to create new document
    verify_hash=True,
)
print(f"Created {results['objects_created']} objects")
print(f"Replayed {results['features_replayed']} parametric features")
print(f"Hash match: {results['hash_verified']}")
```

### Incremental Sync (Change Detection)

```python
from freecad_itwin.change_detect import ProvenanceTracker, compute_object_hash
from freecad_itwin.exporter import _get_object_uuid

tracker = ProvenanceTracker("/path/to/provenance.json")

# Build current state
current = {}
for obj in doc.Objects:
    uuid = _get_object_uuid(obj)
    current[uuid] = compute_object_hash(obj)

# Detect what changed since last export
changes = tracker.detect_changes(current)
print(f"Added: {len(changes.added)}, Modified: {len(changes.modified)}, Deleted: {len(changes.deleted)}")
```

---

## API Reference

### Python — `freecad_itwin`

| Module | Key Exports | Description |
|--------|------------|-------------|
| `bundle` | `BundleWriter`, `BundleReader`, `Manifest`, `ObjectEntry`, `GuiStateEntry` | Read/write `.fcitwin` ZIP bundles |
| `exporter` | `export_document()` | Export a FreeCAD document to `.fcitwin` |
| `importer` | `import_bundle()` | Reconstruct a FreeCAD document from `.fcitwin` |
| `parametric` | `serialize_parametric_tree()` | Serialize feature tree (Pad, Pocket, Fillet, etc.) |
| `sketch` | `serialize_sketch()` | Serialize sketch geometry and constraints |
| `assembly` | `serialize_assembly()`, `reconstruct_assembly()` | Assembly4 serialization and reconstruction |
| `techdraw` | `serialize_techdraw_page()`, `export_techdraw_svg()` | TechDraw page export |
| `hash_verify` | `compute_shape_hash()`, `compute_document_hash()`, `verify_round_trip()` | Round-trip integrity verification |
| `change_detect` | `ProvenanceTracker`, `ChangeSet`, `compute_object_hash()` | Incremental change detection |

### TypeScript — `freecad-itwin-connector`

| Export | Description |
|--------|-------------|
| `BundleReader` | Reads `.fcitwin` ZIP bundles — manifest, GUI state, BREP, meshes, sketches, drawings |
| `FreeCADConnector` | Maps bundle data to `IModelElement[]` with parsed meshes, compressed BREP, and all aspects |
| `Manifest`, `ObjectEntry`, `GuiStateEntry` | Type definitions matching the bundle format |
| `ParametricFeature`, `SketchData`, `DrawingData` | Type definitions for FreeCAD domain data |

---

## Development

### Python Plugin

```bash
cd freecad-plugin
pip install -e ".[dev]"

# Run tests (25 tests)
pytest

# Lint
ruff check .

# Auto-fix lint issues
ruff check . --fix
```

### TypeScript Connector

```bash
cd itwin-connector
npm install

# Build
npm run build

# Run tests (15 tests)
npm test

# Lint
npm run lint
```

### CI

GitHub Actions CI runs on every push and PR to `main`:

- **Python**: tests on 3.10, 3.11, 3.12 with pytest + ruff
- **TypeScript**: build + lint + test with Node 18

---

## Project Structure

```
freecard-itwin-plugin/
├── freecad-plugin/                     # Python FreeCAD plugin
│   ├── freecad_itwin/
│   │   ├── __init__.py                 # Package init (v0.1.0)
│   │   ├── bundle.py                   # .fcitwin ZIP bundle read/write
│   │   ├── exporter.py                 # FreeCAD → .fcitwin export
│   │   ├── importer.py                 # .fcitwin → FreeCAD reconstruction
│   │   ├── parametric.py               # Parametric feature tree serializer
│   │   ├── sketch.py                   # Sketch geometry + constraint serializer
│   │   ├── assembly.py                 # Assembly4 serializer/reconstructor
│   │   ├── techdraw.py                 # TechDraw page serializer
│   │   ├── hash_verify.py              # Shape hash for round-trip verification
│   │   ├── change_detect.py            # Incremental change detection
│   │   └── manifest_schema.json        # JSON Schema for manifest.json
│   ├── tests/
│   │   ├── test_bundle.py              # Bundle format tests (13 tests)
│   │   ├── test_change_detect.py       # Change detection tests (10 tests)
│   │   └── test_integration.py         # Full pipeline integration tests (2 tests)
│   └── pyproject.toml
├── itwin-connector/                    # TypeScript iTwin.js connector
│   ├── src/
│   │   ├── index.ts                    # Public API exports
│   │   ├── connector.ts                # FreeCADConnector — bundle → iModel elements
│   │   ├── bundle-reader.ts            # .fcitwin ZIP bundle reader
│   │   ├── types.ts                    # TypeScript type definitions
│   │   ├── cli.ts                      # CLI convert tool
│   │   └── FreeCAD.ecschema.xml        # BIS domain schema extension
│   ├── tests/
│   │   └── connector.test.ts           # Bundle reader + connector tests (15 tests)
│   ├── package.json
│   ├── tsconfig.json
│   └── jest.config.js
├── .github/workflows/ci.yml            # CI pipeline
├── PROPOSAL.md                         # Full design proposal
├── LICENSE                             # LGPL 2.1
└── README.md
```

---

## Roadmap

The plugin was developed across four phases:

| Phase | Status | Scope |
|-------|--------|-------|
| **1 — Foundation** | ✅ Complete | Bundle format, BREP/mesh export, ECSchema, connector core, visual styling |
| **2 — Parametric Fidelity** | ✅ Complete | Feature tree serialization, sketch constraints, round-trip import, shape hash verification |
| **3 — Drawings & Assemblies** | ✅ Complete | TechDraw pages (SVG + JSON), Assembly4 support, multi-document linking |
| **4 — Incremental Sync** | ✅ Complete | Change detection, provenance tracking, incremental ChangeSet support |

### Future Work

- **FreeCAD Workbench UI** — toolbar buttons, progress dialogs, settings panel
- **iTwin Synchronizer integration** — auto-trigger exports on file save
- **Cloud-hosted connector** — deploy on iTwin Platform as a service
- **Additional assembly workbenches** — A2plus, Assembly3 support
- **STEP intermediate format** — alternative to BREP for wider tool interop
- **Performance optimization** — parallel tessellation, streaming bundles, lazy loading

---

## License

This project is licensed under the [GNU Lesser General Public License v2.1](LICENSE), matching FreeCAD's license.
