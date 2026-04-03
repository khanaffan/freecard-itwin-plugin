"""
Assembly serializer for Phase 3.

Handles Assembly4 workbench structures: placement constraints,
link objects, and multi-body relationships.
"""

from __future__ import annotations

from typing import Any


def _serialize_placement(placement: Any) -> dict[str, Any]:
    """Serialize a FreeCAD Placement to a dict."""
    return {
        "position": [
            float(placement.Base.x),
            float(placement.Base.y),
            float(placement.Base.z),
        ],
        "rotation": [
            float(placement.Rotation.Q[0]),
            float(placement.Rotation.Q[1]),
            float(placement.Rotation.Q[2]),
            float(placement.Rotation.Q[3]),
        ],
    }


def _serialize_assembly_constraint(obj: Any) -> dict[str, Any] | None:
    """Serialize an Assembly4 constraint/LCS attachment."""
    data: dict[str, Any] = {
        "name": obj.Name,
        "type": getattr(obj, "TypeId", type(obj).__name__),
    }

    # Assembly4 uses expressions on Placement for constraints
    if hasattr(obj, "ExpressionEngine"):
        expressions = {}
        for prop, expr in obj.ExpressionEngine:
            expressions[prop] = str(expr)
        if expressions:
            data["expressions"] = expressions

    # Linked object reference
    if hasattr(obj, "LinkedObject") and obj.LinkedObject:
        data["linkedObject"] = obj.LinkedObject.Name
        if hasattr(obj, "LinkedObject") and hasattr(obj.LinkedObject, "Document"):
            linked_doc = obj.LinkedObject.Document
            if linked_doc and linked_doc.Name != obj.Document.Name:
                data["linkedDocument"] = linked_doc.FileName

    # Placement
    if hasattr(obj, "Placement"):
        data["placement"] = _serialize_placement(obj.Placement)

    # Attachment offset
    if hasattr(obj, "AttachmentOffset"):
        data["attachmentOffset"] = _serialize_placement(obj.AttachmentOffset)

    # Assembly4 specific: SolverId
    if hasattr(obj, "SolverId"):
        data["solverId"] = str(obj.SolverId)

    return data


def serialize_assembly(doc: Any) -> dict[str, Any]:
    """
    Serialize assembly structure from a FreeCAD document.

    Handles Assembly4 workbench link objects, LCS attachments,
    and placement constraints.
    """
    result: dict[str, Any] = {
        "assemblyType": "Assembly4",
        "components": [],
        "constraints": [],
        "externalReferences": [],
    }

    for obj in doc.Objects:
        type_id = getattr(obj, "TypeId", "")

        # App::Link objects (Assembly4 components)
        if type_id == "App::Link":
            component: dict[str, Any] = {
                "name": obj.Name,
                "label": getattr(obj, "Label", obj.Name),
                "type": "Link",
            }

            if hasattr(obj, "LinkedObject") and obj.LinkedObject:
                component["linkedObject"] = obj.LinkedObject.Name

                # Check for external document reference
                linked_doc = getattr(obj.LinkedObject, "Document", None)
                if linked_doc and linked_doc.Name != doc.Name:
                    ext_ref = {
                        "componentName": obj.Name,
                        "documentName": linked_doc.Name,
                        "filePath": getattr(linked_doc, "FileName", ""),
                    }
                    result["externalReferences"].append(ext_ref)
                    component["externalDocument"] = linked_doc.Name

            if hasattr(obj, "Placement"):
                component["placement"] = _serialize_placement(obj.Placement)

            # Assembly4 expressions
            if hasattr(obj, "ExpressionEngine"):
                expressions = {}
                for prop, expr in obj.ExpressionEngine:
                    expressions[prop] = str(expr)
                if expressions:
                    component["expressions"] = expressions

            result["components"].append(component)

        # Local Coordinate Systems (LCS)
        elif type_id == "PartDesign::CoordinateSystem":
            constraint_data = _serialize_assembly_constraint(obj)
            if constraint_data:
                result["constraints"].append(constraint_data)

    return result


def reconstruct_assembly(doc: Any, assembly_data: dict[str, Any]) -> dict[str, Any]:
    """
    Reconstruct assembly structure in a FreeCAD document.

    Returns results dict with counts and errors.
    """
    results: dict[str, Any] = {
        "components_created": 0,
        "constraints_applied": 0,
        "errors": [],
    }

    try:
        import FreeCAD  # noqa: F811
    except ImportError:
        results["errors"].append("FreeCAD module not available")
        return results

    # Create Link objects for components
    for component in assembly_data.get("components", []):
        try:
            link = doc.addObject("App::Link", component["name"])
            if "label" in component:
                link.Label = component["label"]

            # Resolve linked object
            linked_name = component.get("linkedObject")
            if linked_name:
                linked_obj = doc.getObject(linked_name)
                if linked_obj:
                    link.LinkedObject = linked_obj

            # Apply placement
            if "placement" in component:
                p = component["placement"]
                link.Placement = FreeCAD.Placement(
                    FreeCAD.Vector(*p["position"]),
                    FreeCAD.Rotation(*p["rotation"]),
                )

            # Apply expressions
            if "expressions" in component:
                for prop, expr in component["expressions"].items():
                    try:
                        link.setExpression(prop, expr)
                    except Exception:
                        pass

            results["components_created"] += 1
        except Exception as e:
            results["errors"].append(f"Component {component['name']}: {e}")

    doc.recompute()
    return results
