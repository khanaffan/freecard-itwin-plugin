# FreeCAD → iTwin.js Export Plugin

Export FreeCAD drawings (`.FCStd`) to Bentley iTwin.js iModels with **round-trip fidelity** — every exported iModel contains sufficient data to fully recreate the original FreeCAD drawing.

## Architecture

```
FreeCAD (.FCStd) → Python Exporter → .fcitwin bundle → TypeScript Connector → iModel (.bim)
```

Three components:

1. **FreeCAD Export Plugin** (`freecad-plugin/`) — Python workbench that serializes FreeCAD documents into `.fcitwin` bundles
2. **Intermediate Format** (`.fcitwin`) — ZIP archive containing parametric trees, BREP shapes, tessellated meshes, sketches, and GUI state as JSON
3. **iTwin.js Connector** (`itwin-connector/`) — TypeScript connector that maps `.fcitwin` data into BIS-conformant iModel elements

## Requirements

- **FreeCAD** 0.21+
- **Node.js** 18+
- **Python** 3.10+

## Quick Start

### Export from FreeCAD

```python
# In FreeCAD's Python console or as a macro
from freecad_itwin import exporter
exporter.export_document(FreeCAD.ActiveDocument, "/path/to/output.fcitwin")
```

### Convert to iModel

```bash
cd itwin-connector
npm install
npm run convert -- --input /path/to/output.fcitwin --output /path/to/output.bim
```

## Development

### Python Plugin

```bash
cd freecad-plugin
pip install -e ".[dev]"
pytest
```

### TypeScript Connector

```bash
cd itwin-connector
npm install
npm test
```

## License

LGPL 2.1 — see [LICENSE](LICENSE)
