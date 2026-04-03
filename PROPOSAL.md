# Proposal: FreeCAD → iTwin.js Export Plugin

**Author:** Affan Khan
**Date:** April 2026
**Status:** Draft

---

## 1. Executive Summary

This proposal outlines the design of an **export plugin for FreeCAD** that converts FreeCAD drawings (`.FCStd` files) into **Bentley iTwin.js iModels**. The plugin's core design principle is **round-trip fidelity** — every exported iModel must contain sufficient data to **fully recreate the original FreeCAD drawing**, including parametric definitions, constraint history, topology, visual styling, and metadata.

---

## 2. Problem Statement

FreeCAD is a powerful open-source parametric 3D CAD modeler used across engineering disciplines. However, it exists in isolation from the Bentley iTwin ecosystem, which provides cloud-based infrastructure for managing, visualizing, and analyzing digital twins of built assets.

There is currently **no connector or plugin** that bridges FreeCAD and iTwin.js. Engineers who use FreeCAD cannot participate in iTwin-based workflows without manually re-modeling their designs.

### Goals

| # | Goal | Description |
|---|------|-------------|
| G1 | **Lossless Export** | Export FreeCAD models to iModels with enough fidelity to recreate the original `.FCStd` file. |
| G2 | **Parametric Preservation** | Store FreeCAD's parametric tree, constraints, and sketch definitions as structured data inside the iModel. |
| G3 | **Visual Fidelity** | Preserve colors, line styles, transparency, and display modes. |
| G4 | **Incremental Sync** | Support change-detection so only modified objects generate new ChangeSets. |
| G5 | **Open Source** | Release under LGPL 2.1 (matching FreeCAD's license). |

---

## 3. Technical Background

### 3.1 FreeCAD `.FCStd` File Format

The `.FCStd` file is a **ZIP archive** containing:

| File | Purpose |
|------|---------|
| `Document.xml` | Full parametric object tree — features, constraints, properties, dependencies |
| `GuiDocument.xml` | Visual state — colors, line widths, visibility, display modes |
| `*.brp` | OpenCASCADE BREP serialized shapes (boundary representation geometry) |
| `*.svg` | TechDraw 2D drawing pages |
| `Thumbnail.png` | Preview image |

Key FreeCAD concepts that must survive the round-trip:

- **Parametric Feature Tree** — ordered list of modeling operations (Pad, Pocket, Fillet, etc.)
- **Sketches & Constraints** — 2D sketches with geometric and dimensional constraints
- **Part / Assembly hierarchy** — nested part containers and assembly links
- **Properties** — typed key-value metadata on every object
- **TechDraw Pages** — 2D engineering drawings with dimensions, annotations, views

### 3.2 iTwin.js iModel Architecture

An iModel is a **SQLite-based distributed database** governed by BIS (Base Infrastructure Schemas). Key concepts:

- **Elements** — the fundamental data unit (physical, drawing, definition, etc.)
- **Models** — containers that sub-model elements (PhysicalModel, DrawingModel, etc.)
- **Aspects** — additional property bundles attached to elements
- **Schemas** — ECSchema definitions that describe element classes and properties
- **ChangeSets** — incremental diffs pushed to iModelHub for versioning

iTwin.js provides a **Connector Framework** (`@itwin/imodel-bridge`) for writing custom importers that map external data into BIS-conformant iModels.

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FreeCAD Application                   │
│                                                         │
│  ┌───────────────┐    ┌──────────────────────────────┐  │
│  │  FreeCAD       │    │  FreeCAD-iTwin Export Plugin  │  │
│  │  Document      │───▶│  (Python Workbench)           │  │
│  │  (.FCStd)      │    │                              │  │
│  └───────────────┘    └──────────┬───────────────────┘  │
│                                  │                       │
└──────────────────────────────────┼───────────────────────┘
                                   │  JSON/BREP intermediate
                                   ▼
                    ┌──────────────────────────────┐
                    │  Intermediate Exchange Format │
                    │  (.fcitwin bundle)            │
                    │                              │
                    │  ├── manifest.json           │
                    │  ├── parametric-tree.json    │
                    │  ├── sketches/               │
                    │  ├── shapes/  (*.brep)       │
                    │  ├── drawings/ (*.svg)       │
                    │  ├── gui-state.json          │
                    │  └── properties.json         │
                    └──────────┬───────────────────┘
                               │
                               ▼
                    ┌──────────────────────────────┐
                    │  iTwin.js Connector           │
                    │  (TypeScript / Node.js)       │
                    │                              │
                    │  FreeCADConnector extends     │
                    │  BaseConnector                │
                    │                              │
                    │  ┌────────────────────────┐  │
                    │  │ FreeCAD Domain Schema   │  │
                    │  │ (ECSchema extension)    │  │
                    │  └────────────────────────┘  │
                    └──────────┬───────────────────┘
                               │
                               ▼
                    ┌──────────────────────────────┐
                    │  iModel (.bim)                │
                    │                              │
                    │  BIS Elements + FreeCAD       │
                    │  Domain Extensions            │
                    │                              │
                    │  ☑ Geometry (tessellated)     │
                    │  ☑ Parametric tree (aspects)  │
                    │  ☑ Sketches (aspects)         │
                    │  ☑ Constraints (aspects)      │
                    │  ☑ BREP blobs (aspects)       │
                    │  ☑ Visual styling             │
                    │  ☑ TechDraw pages             │
                    └──────────────────────────────┘
```

### 4.1 Component Breakdown

#### Component 1: FreeCAD Export Workbench (Python)

A FreeCAD Workbench/Macro that:

1. Traverses the active `FreeCAD.Document` object tree
2. Serializes the **parametric feature tree** — each feature's type, parameters, and dependency links
3. Exports **sketch geometry + constraints** as structured JSON
4. Exports **BREP shapes** (`.brp` files from OpenCASCADE)
5. Exports **tessellated meshes** (for visualization in iTwin viewers that don't have BREP support)
6. Captures **GUI state** — colors, transparency, line widths, visibility
7. Captures **TechDraw pages** as SVG + structured annotation data
8. Packages everything into a `.fcitwin` bundle (ZIP archive)

#### Component 2: Intermediate Exchange Format (`.fcitwin`)

A ZIP-based bundle serving as the bridge between the Python and TypeScript worlds:

```
manifest.json            — version, source file hash, object count, FreeCAD version
parametric-tree.json     — ordered feature list with full parameter definitions
sketches/
  ├── Sketch001.json     — geometry primitives + constraints
  └── Sketch002.json
shapes/
  ├── Body001.brep       — OpenCASCADE BREP (exact geometry)
  └── Body001.mesh.obj   — tessellated mesh (for iTwin visualization)
drawings/
  ├── Page001.svg        — TechDraw rendering
  └── Page001.json       — structured annotation/dimension data
gui-state.json           — visual properties per object
properties.json          — user-defined properties and metadata
```

#### Component 3: iTwin.js FreeCAD Connector (TypeScript)

A custom connector built on `@itwin/imodel-bridge` that:

1. **Reads** the `.fcitwin` bundle
2. **Registers** a custom FreeCAD ECSchema extending BIS
3. **Maps** FreeCAD objects to iModel elements:
   - Part bodies → `PhysicalElement` with tessellated geometry
   - Sketches → custom `FreeCAD:Sketch` elements
   - TechDraw pages → `DrawingGraphic` elements in a `DrawingModel`
4. **Stores round-trip data** as ElementAspects:
   - `FreeCAD:ParametricDefinition` — the full parametric tree JSON
   - `FreeCAD:SketchConstraints` — constraint definitions
   - `FreeCAD:BrepGeometry` — raw BREP blob for exact geometry reconstruction
   - `FreeCAD:GuiState` — visual styling data
5. **Computes provenance** — maps FreeCAD object UUIDs to iModel element IDs for incremental sync

---

## 5. FreeCAD Domain ECSchema

A custom ECSchema extension to store FreeCAD-specific data inside the iModel:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ECSchema schemaName="FreeCAD" alias="fc"
          version="01.00.00"
          xmlns="http://www.bentley.com/schemas/Bentley.ECXML.3.2">

  <ECSchemaReference name="BisCore" version="01.00.14" alias="bis"/>
  <ECSchemaReference name="CoreCustomAttributes" version="01.00.03" alias="CoreCA"/>

  <!-- Source document metadata -->
  <ECEntityClass typeName="SourceDocument" modifier="Sealed">
    <BaseClass>bis:DefinitionElement</BaseClass>
    <ECProperty propertyName="FreeCadVersion" typeName="string"/>
    <ECProperty propertyName="SourceFileHash" typeName="string"/>
    <ECProperty propertyName="OriginalFileName" typeName="string"/>
  </ECEntityClass>

  <!-- Parametric feature definition stored as aspect -->
  <ECEntityClass typeName="ParametricDefinition" modifier="Sealed">
    <BaseClass>bis:ElementMultiAspect</BaseClass>
    <ECProperty propertyName="FeatureType" typeName="string"/>
    <ECProperty propertyName="FeatureIndex" typeName="int"/>
    <ECProperty propertyName="ParametersJson" typeName="string"/>
    <ECProperty propertyName="DependsOn" typeName="string"/>
  </ECEntityClass>

  <!-- Sketch with constraints -->
  <ECEntityClass typeName="SketchDefinition" modifier="Sealed">
    <BaseClass>bis:ElementUniqueAspect</BaseClass>
    <ECProperty propertyName="GeometryJson" typeName="string"/>
    <ECProperty propertyName="ConstraintsJson" typeName="string"/>
    <ECProperty propertyName="PlaneOrigin" typeName="point3d"/>
    <ECProperty propertyName="PlaneNormal" typeName="point3d"/>
  </ECEntityClass>

  <!-- Raw BREP for exact reconstruction -->
  <ECEntityClass typeName="BrepGeometry" modifier="Sealed">
    <BaseClass>bis:ElementUniqueAspect</BaseClass>
    <ECProperty propertyName="BrepData" typeName="binary"/>
    <ECProperty propertyName="BrepFormat" typeName="string"/>
  </ECEntityClass>

  <!-- Visual styling from FreeCAD GUI -->
  <ECEntityClass typeName="GuiStyle" modifier="Sealed">
    <BaseClass>bis:ElementUniqueAspect</BaseClass>
    <ECProperty propertyName="ShapeColor" typeName="string"/>
    <ECProperty propertyName="LineColor" typeName="string"/>
    <ECProperty propertyName="LineWidth" typeName="double"/>
    <ECProperty propertyName="Transparency" typeName="double"/>
    <ECProperty propertyName="Visibility" typeName="boolean"/>
    <ECProperty propertyName="DisplayMode" typeName="string"/>
  </ECEntityClass>

  <!-- TechDraw page reference -->
  <ECEntityClass typeName="TechDrawPage" modifier="Sealed">
    <BaseClass>bis:DrawingGraphic</BaseClass>
    <ECProperty propertyName="PageTemplate" typeName="string"/>
    <ECProperty propertyName="Scale" typeName="double"/>
    <ECProperty propertyName="AnnotationsJson" typeName="string"/>
    <ECProperty propertyName="SvgData" typeName="string"/>
  </ECEntityClass>

</ECSchema>
```

---

## 6. Data Mapping: FreeCAD → iModel

| FreeCAD Concept | iModel Element | Round-Trip Data (Aspect) |
|----------------|----------------|--------------------------|
| Part::Feature (Body) | `bis:PhysicalElement` in `PhysicalModel` | `fc:ParametricDefinition` (feature tree) + `fc:BrepGeometry` (BREP blob) |
| Sketcher::SketchObject | `bis:GeometricElement3d` | `fc:SketchDefinition` (geometry + constraints JSON) |
| Part::Pad, Pocket, Fillet, etc. | Not a separate element — stored as aspects on the parent Body | `fc:ParametricDefinition` (one aspect per feature, ordered by `FeatureIndex`) |
| App::Part (container) | `bis:PhysicalElement` (parent in assembly hierarchy) | Standard BIS parent-child relationship |
| Assembly (A2plus/Assembly4) | `bis:PhysicalElement` with child models | Assembly constraints as `fc:ParametricDefinition` aspects |
| TechDraw::DrawPage | `fc:TechDrawPage` in `DrawingModel` | SVG + annotation JSON |
| TechDraw::DrawViewPart | `bis:DrawingGraphic` | View projection parameters |
| Object properties | `bis:ElementMultiAspect` | Arbitrary key-value properties |
| Colors/Styling | `bis:RenderMaterial` + `fc:GuiStyle` | Full GUI state for reconstruction |

---

## 7. Round-Trip Reconstruction Strategy

The key design decision enabling round-trip fidelity is **dual representation**:

1. **Visualization Layer** — tessellated meshes and BIS-standard geometry that any iTwin.js viewer can render natively.
2. **Reconstruction Layer** — FreeCAD-specific aspects containing the exact data needed to rebuild the `.FCStd` file.

### Reconstruction Process (iModel → FreeCAD)

```
iModel (.bim)
    │
    ▼
iTwin.js Reconstruction Tool
    │
    ├── Read fc:ParametricDefinition aspects → rebuild feature tree
    ├── Read fc:SketchDefinition aspects → rebuild sketches + constraints
    ├── Read fc:BrepGeometry aspects → restore exact BREP shapes
    ├── Read fc:GuiStyle aspects → restore visual properties
    ├── Read fc:TechDrawPage elements → restore drawing pages
    │
    ▼
Generate .fcitwin bundle
    │
    ▼
FreeCAD Import Plugin (Python)
    │
    ├── Create new FreeCAD document
    ├── Replay parametric feature tree in order
    ├── Restore sketches with constraints
    ├── Validate BREP shapes match parametric results
    ├── Apply visual styling
    ├── Recreate TechDraw pages
    │
    ▼
Reconstructed .FCStd file ✓
```

### Integrity Verification

After reconstruction, the plugin computes a **shape hash** (based on BREP topology) and compares it against the original hash stored in the `SourceDocument` element. This provides confidence that the round-trip was lossless.

---

## 8. Implementation Phases

### Phase 1 — Foundation (MVP)

- FreeCAD Python exporter: serialize Document.xml data, BREP shapes, and tessellated meshes to `.fcitwin`
- iTwin.js connector: import physical elements with tessellated geometry
- FreeCAD ECSchema v1: `SourceDocument`, `BrepGeometry`, `GuiStyle`
- Basic visual styling preservation

**Outcome:** FreeCAD models viewable in iTwin.js with stored BREP for reconstruction.

### Phase 2 — Parametric Fidelity

- Serialize full parametric feature tree with parameters and dependencies
- Serialize sketch geometry and constraints
- `ParametricDefinition` and `SketchDefinition` aspects
- FreeCAD import plugin (Python) for round-trip reconstruction
- Shape hash verification

**Outcome:** Full round-trip: FreeCAD → iModel → FreeCAD with parametric history intact.

### Phase 3 — Drawings & Assemblies

- TechDraw page export with structured annotations
- Assembly support (A2plus, Assembly3, Assembly4 workbenches)
- Assembly constraint preservation
- Multi-document assembly linking

**Outcome:** Complete engineering drawing and assembly workflow support.

### Phase 4 — Incremental Sync & Cloud

- Change detection based on FreeCAD object UUIDs
- Incremental ChangeSet generation
- Integration with iTwin Synchronizer
- Cloud-hosted connector option via iTwin Platform

**Outcome:** Live synchronization between FreeCAD projects and iTwin digital twins.

---

## 9. Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| FreeCAD Export Plugin | Python 3.10+, FreeCAD API | Native FreeCAD scripting language |
| Intermediate Format | JSON + BREP + OBJ in ZIP | Human-readable, debuggable, language-agnostic |
| iTwin.js Connector | TypeScript, Node.js 18+ | iTwin.js SDK language |
| iTwin.js SDK | `@itwin/core-backend`, `@itwin/imodel-bridge` | Official connector framework |
| BREP Handling | OpenCASCADE (via FreeCAD) | Same kernel FreeCAD uses |
| Mesh Tessellation | FreeCAD `Mesh` module | Built-in tessellation from BREP |
| Testing | pytest (Python), Jest (TypeScript) | Standard for each ecosystem |

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| FreeCAD parametric tree too complex to serialize fully | Loss of parametric history | Phase approach: start with BREP-only round-trip, incrementally add parametric features |
| BIS schema doesn't map well to CAD concepts | Poor data organization in iModel | Use ElementAspects extensively to attach FreeCAD-specific data without forcing BIS misuse |
| Large BREP blobs cause iModel performance issues | Slow sync and large file sizes | Compress BREP data, use lazy loading, store tessellated mesh separately for visualization |
| FreeCAD Python API instability across versions | Plugin breakage on FreeCAD updates | Pin minimum FreeCAD version (0.21+), use stable API surface, CI matrix testing |
| OpenCASCADE BREP format changes | BREP reconstruction failures | Store BREP format version, implement format migration on import |
| Assembly workbench fragmentation (A2plus vs Assembly3 vs Assembly4) | Incomplete assembly support | Phase 3 targets Assembly4 first (most active), add others incrementally |

---

## 11. Success Criteria

1. **Round-trip fidelity**: A FreeCAD model exported to iModel and reconstructed back produces a geometrically identical `.FCStd` file (verified by shape hash comparison).
2. **Visual accuracy**: The model rendered in an iTwin.js viewer is visually indistinguishable from the FreeCAD 3D view.
3. **Parametric survival**: After round-trip, modifying a parameter in the reconstructed FreeCAD file correctly regenerates dependent features.
4. **Drawing completeness**: TechDraw pages reconstructed from the iModel contain all dimensions, annotations, and views.
5. **Incremental efficiency**: Re-exporting after a small change produces a ChangeSet proportional to the change size, not the full model.

---

## 12. Open Questions

1. **Macro vs Workbench?** — Should the FreeCAD exporter be a simple macro or a full Workbench with UI? (Recommendation: start as macro, graduate to Workbench in Phase 3.)
2. **STEP as alternative intermediate?** — Should we also support STEP export as an alternative to BREP blobs for wider tool compatibility?
3. **iModel standalone vs iModelHub?** — Should Phase 1 target standalone `.bim` files or require iModelHub from the start? (Recommendation: standalone first.)
4. **FreeCAD version baseline?** — What's the minimum supported FreeCAD version? (Recommendation: 0.21+ for stable Python API and TechDraw.)

---

## 13. References

- [iTwin.js Documentation — Writing a Connector](https://www.itwinjs.org/learning/writeaconnector/)
- [iTwin.js Documentation — iModel Connectors](https://www.itwinjs.org/learning/imodel-connectors/)
- [BIS Schema Customization](https://imodeljs.github.io/iModelJs-docs-output/bis/intro/schema-customization/)
- [FreeCAD File Format (.FCStd)](https://wiki.freecad.org/File_Format_FCStd)
- [FreeCAD Python Scripting Tutorial](https://wiki.freecad.org/Python_scripting_tutorial)
- [FreeCAD Python API Reference](https://freecad-python-api.readthedocs.io/en/latest/)
- [iTwin.js GitHub Repository](https://github.com/iTwin/itwinjs-core)
