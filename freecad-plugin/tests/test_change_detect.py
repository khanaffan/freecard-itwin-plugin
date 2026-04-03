"""Tests for the change detection and provenance tracking (Phase 4)."""



from freecad_itwin.change_detect import ChangeSet, ProvenanceTracker


class TestChangeSet:
    def test_empty(self):
        cs = ChangeSet(added=[], modified=[], deleted=[])
        assert cs.is_empty
        assert cs.total_changes == 0

    def test_non_empty(self):
        cs = ChangeSet(added=["a"], modified=["b"], deleted=["c"])
        assert not cs.is_empty
        assert cs.total_changes == 3


class TestProvenanceTracker:
    def test_new_tracker(self, tmp_path):
        tracker = ProvenanceTracker(tmp_path / "provenance.json")
        assert tracker.get_element_id("uuid-1") is None

    def test_set_and_get(self, tmp_path):
        tracker = ProvenanceTracker(tmp_path / "provenance.json")
        tracker.set_mapping("uuid-1", "elem-1", "hash-a")
        assert tracker.get_element_id("uuid-1") == "elem-1"

    def test_persistence(self, tmp_path):
        path = tmp_path / "provenance.json"
        tracker = ProvenanceTracker(path)
        tracker.set_mapping("uuid-1", "elem-1", "hash-a")
        tracker.save()

        tracker2 = ProvenanceTracker(path)
        assert tracker2.get_element_id("uuid-1") == "elem-1"

    def test_detect_changes_added(self, tmp_path):
        tracker = ProvenanceTracker(tmp_path / "provenance.json")
        current = {"uuid-1": "hash-a", "uuid-2": "hash-b"}
        changes = tracker.detect_changes(current)
        assert set(changes.added) == {"uuid-1", "uuid-2"}
        assert changes.modified == []
        assert changes.deleted == []

    def test_detect_changes_modified(self, tmp_path):
        tracker = ProvenanceTracker(tmp_path / "provenance.json")
        tracker.set_mapping("uuid-1", "elem-1", "hash-a")
        tracker.save()

        tracker2 = ProvenanceTracker(tmp_path / "provenance.json")
        changes = tracker2.detect_changes({"uuid-1": "hash-b"})
        assert changes.added == []
        assert changes.modified == ["uuid-1"]
        assert changes.deleted == []

    def test_detect_changes_deleted(self, tmp_path):
        tracker = ProvenanceTracker(tmp_path / "provenance.json")
        tracker.set_mapping("uuid-1", "elem-1", "hash-a")
        tracker.save()

        tracker2 = ProvenanceTracker(tmp_path / "provenance.json")
        changes = tracker2.detect_changes({})
        assert changes.added == []
        assert changes.modified == []
        assert changes.deleted == ["uuid-1"]

    def test_detect_changes_mixed(self, tmp_path):
        tracker = ProvenanceTracker(tmp_path / "provenance.json")
        tracker.set_mapping("uuid-1", "elem-1", "hash-a")
        tracker.set_mapping("uuid-2", "elem-2", "hash-b")
        tracker.set_mapping("uuid-3", "elem-3", "hash-c")
        tracker.save()

        tracker2 = ProvenanceTracker(tmp_path / "provenance.json")
        current = {
            "uuid-1": "hash-a",  # unchanged
            "uuid-2": "hash-x",  # modified
            "uuid-4": "hash-d",  # added
            # uuid-3 deleted
        }
        changes = tracker2.detect_changes(current)
        assert changes.added == ["uuid-4"]
        assert changes.modified == ["uuid-2"]
        assert changes.deleted == ["uuid-3"]

    def test_remove(self, tmp_path):
        tracker = ProvenanceTracker(tmp_path / "provenance.json")
        tracker.set_mapping("uuid-1", "elem-1", "hash-a")
        tracker.remove("uuid-1")
        assert tracker.get_element_id("uuid-1") is None
