"""
Change detection for incremental sync (Phase 4).

Tracks FreeCAD object UUIDs and computes per-object hashes to
identify added, modified, and deleted objects between exports.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def compute_object_hash(obj: Any) -> str:
    """Compute a hash for a single FreeCAD object capturing its state."""
    hasher = hashlib.sha256()

    # Include type
    hasher.update(getattr(obj, "TypeId", "").encode("utf-8"))

    # Include shape if present
    if hasattr(obj, "Shape") and not obj.Shape.isNull():
        try:
            hasher.update(obj.Shape.exportBrepToString().encode("utf-8"))
        except Exception:
            pass

    # Include key properties
    for prop_name in obj.PropertiesList:
        try:
            val = getattr(obj, prop_name)
            if isinstance(val, (int, float, str, bool)):
                hasher.update(f"{prop_name}={val}".encode())
        except Exception:
            continue

    return hasher.hexdigest()[:16]


@dataclass
class ChangeSet:
    """Represents changes between two exports."""
    added: list[str]  # object UUIDs
    modified: list[str]
    deleted: list[str]

    @property
    def is_empty(self) -> bool:
        return not self.added and not self.modified and not self.deleted

    @property
    def total_changes(self) -> int:
        return len(self.added) + len(self.modified) + len(self.deleted)


class ProvenanceTracker:
    """
    Tracks provenance mapping between FreeCAD UUIDs and export state.

    Maintains a persistent mapping file that survives across exports,
    enabling incremental change detection.
    """

    def __init__(self, mapping_path: str | Path):
        self.mapping_path = Path(mapping_path)
        self._mapping: dict[str, dict[str, str]] = {}
        self._load()

    def _load(self) -> None:
        if self.mapping_path.exists():
            with open(self.mapping_path) as f:
                self._mapping = json.load(f)

    def save(self) -> None:
        self.mapping_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.mapping_path, "w") as f:
            json.dump(self._mapping, f, indent=2)

    def get_element_id(self, source_uuid: str) -> str | None:
        """Get the iModel element ID for a FreeCAD UUID."""
        entry = self._mapping.get(source_uuid)
        return entry.get("elementId") if entry else None

    def set_mapping(self, source_uuid: str, element_id: str, obj_hash: str) -> None:
        """Store a UUID → element ID mapping with hash."""
        self._mapping[source_uuid] = {
            "elementId": element_id,
            "hash": obj_hash,
        }

    def detect_changes(self, current_objects: dict[str, str]) -> ChangeSet:
        """
        Detect changes between current state and last export.

        Args:
            current_objects: Dict mapping UUID → current hash

        Returns:
            ChangeSet with added, modified, and deleted UUIDs
        """
        previous_uuids = set(self._mapping.keys())
        current_uuids = set(current_objects.keys())

        added = list(current_uuids - previous_uuids)
        deleted = list(previous_uuids - current_uuids)
        modified = []

        for uuid in current_uuids & previous_uuids:
            prev_hash = self._mapping[uuid].get("hash", "")
            if prev_hash != current_objects[uuid]:
                modified.append(uuid)

        return ChangeSet(added=added, modified=modified, deleted=deleted)

    def remove(self, source_uuid: str) -> None:
        """Remove a mapping entry (for deleted objects)."""
        self._mapping.pop(source_uuid, None)
