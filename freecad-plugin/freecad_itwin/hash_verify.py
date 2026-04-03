"""
Shape hash computation for round-trip verification.

Computes topology-based hashes of FreeCAD shapes to verify
that round-trip export/import produces geometrically identical results.
"""

from __future__ import annotations

import hashlib
from typing import Any


def compute_shape_hash(shape: Any) -> str:
    """
    Compute a topology-based hash of a shape.

    The hash captures the shape's BREP representation which encodes
    vertices, edges, faces, and their topology. Two shapes with
    identical geometry and topology will produce the same hash.
    """
    try:
        brep_str = shape.exportBrepToString()
        return hashlib.sha256(brep_str.encode("utf-8")).hexdigest()
    except Exception:
        return ""


def compute_document_hash(doc: Any) -> str:
    """
    Compute a combined hash of all shapes in a document.

    This provides a single verification hash for the entire document.
    """
    hasher = hashlib.sha256()
    shape_count = 0

    for obj in doc.Objects:
        if hasattr(obj, "Shape") and not obj.Shape.isNull():
            try:
                brep_str = obj.Shape.exportBrepToString()
                hasher.update(f"{obj.Name}:".encode())
                hasher.update(brep_str.encode("utf-8"))
                shape_count += 1
            except Exception:
                continue

    if shape_count == 0:
        return ""

    return hasher.hexdigest()


def verify_round_trip(original_hash: str, reconstructed_doc: Any) -> dict[str, Any]:
    """
    Verify that a reconstructed document matches the original.

    Args:
        original_hash: Hash stored during export
        reconstructed_doc: The reconstructed FreeCAD document

    Returns:
        Dict with verification results
    """
    reconstructed_hash = compute_document_hash(reconstructed_doc)

    return {
        "original_hash": original_hash,
        "reconstructed_hash": reconstructed_hash,
        "match": original_hash == reconstructed_hash,
        "verified": bool(original_hash and reconstructed_hash),
    }
