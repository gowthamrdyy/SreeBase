"""
Tests for the SreeBase Storage Engine (v2 — offset-indexed).
"""

import os
import tempfile
import pytest

from sreebase.storage.engine import StorageEngine, SyncPolicy
from sreebase.errors import DuplicateKeyError, StorageError


@pytest.fixture
def db_path(tmp_path):
    """Return a path to a temporary .sree file."""
    return str(tmp_path / "test_db.sree")


@pytest.fixture
def engine(db_path):
    """Provide a fresh StorageEngine instance; close it after test."""
    eng = StorageEngine(db_path)
    yield eng
    eng.close()


# ---------------------------------------------------------------------- #
# Insert
# ---------------------------------------------------------------------- #
class TestInsert:
    def test_insert_auto_id(self, engine):
        doc_id = engine.insert({"name": "Gowtham", "role": "architect"})
        assert isinstance(doc_id, str)
        assert len(doc_id) == 32  # uuid4.hex

    def test_insert_custom_id(self, engine):
        doc_id = engine.insert({"_id": "user-42", "name": "Sree"})
        assert doc_id == "user-42"

    def test_insert_duplicate_raises(self, engine):
        engine.insert({"_id": "dup-1", "x": 1})
        with pytest.raises(DuplicateKeyError):
            engine.insert({"_id": "dup-1", "x": 2})

    def test_insert_non_dict_raises(self, engine):
        with pytest.raises(StorageError):
            engine.insert("not a dict")

    def test_insert_increments_count(self, engine):
        assert engine.count() == 0
        engine.insert({"a": 1})
        engine.insert({"b": 2})
        assert engine.count() == 2


# ---------------------------------------------------------------------- #
# Get
# ---------------------------------------------------------------------- #
class TestGet:
    def test_get_by_id(self, engine):
        engine.insert({"_id": "g1", "val": 42})
        doc = engine.get_by_id("g1")
        assert doc is not None
        assert doc["val"] == 42

    def test_get_by_id_missing(self, engine):
        assert engine.get_by_id("nonexistent") is None

    def test_get_all(self, engine):
        engine.insert({"_id": "a", "x": 1})
        engine.insert({"_id": "b", "x": 2})
        all_docs = engine.get_all()
        assert len(all_docs) == 2
        ids = {d["_id"] for d in all_docs}
        assert ids == {"a", "b"}

    def test_get_returns_copy(self, engine):
        """Mutating the returned doc must not affect internal state."""
        engine.insert({"_id": "c1", "val": "original"})
        doc = engine.get_by_id("c1")
        doc["val"] = "mutated"
        assert engine.get_by_id("c1")["val"] == "original"


# ---------------------------------------------------------------------- #
# Update
# ---------------------------------------------------------------------- #
class TestUpdate:
    def test_update_existing(self, engine):
        engine.insert({"_id": "u1", "name": "old"})
        result = engine.update("u1", {"name": "new"})
        assert result["name"] == "new"
        assert result["_id"] == "u1"
        assert engine.get_by_id("u1")["name"] == "new"

    def test_update_nonexistent_raises(self, engine):
        with pytest.raises(StorageError):
            engine.update("ghost", {"x": 1})

    def test_update_upsert(self, engine):
        result = engine.update("up1", {"x": 99}, upsert=True)
        assert result["_id"] == "up1"
        assert engine.get_by_id("up1")["x"] == 99


# ---------------------------------------------------------------------- #
# Delete
# ---------------------------------------------------------------------- #
class TestDelete:
    def test_delete_existing(self, engine):
        engine.insert({"_id": "d1", "val": 1})
        assert engine.delete("d1") is True
        assert engine.get_by_id("d1") is None
        assert engine.count() == 0

    def test_delete_nonexistent(self, engine):
        assert engine.delete("ghost") is False


# ---------------------------------------------------------------------- #
# Recovery / Hydration
# ---------------------------------------------------------------------- #
class TestRecovery:
    def test_hydrate_on_reopen(self, db_path):
        """Closing and re-opening the engine must recover all documents."""
        eng1 = StorageEngine(db_path)
        eng1.insert({"_id": "r1", "v": 1})
        eng1.insert({"_id": "r2", "v": 2})
        eng1.close()

        eng2 = StorageEngine(db_path)
        assert eng2.count() == 2
        assert eng2.get_by_id("r1")["v"] == 1
        assert eng2.get_by_id("r2")["v"] == 2
        eng2.close()

    def test_hydrate_respects_updates(self, db_path):
        """After re-open, the latest version of a document must win."""
        eng1 = StorageEngine(db_path)
        eng1.insert({"_id": "h1", "ver": 1})
        eng1.update("h1", {"ver": 2})
        eng1.close()

        eng2 = StorageEngine(db_path)
        assert eng2.get_by_id("h1")["ver"] == 2
        eng2.close()

    def test_hydrate_respects_deletes(self, db_path):
        """Tombstoned documents must not reappear after re-open."""
        eng1 = StorageEngine(db_path)
        eng1.insert({"_id": "hd1", "val": "dead"})
        eng1.delete("hd1")
        eng1.close()

        eng2 = StorageEngine(db_path)
        assert eng2.get_by_id("hd1") is None
        assert eng2.count() == 0
        eng2.close()

    def test_context_manager(self, db_path):
        """Engine works as a context manager."""
        with StorageEngine(db_path) as eng:
            eng.insert({"_id": "ctx", "ok": True})
        # File handle should be closed here; verify by re-opening.
        with StorageEngine(db_path) as eng:
            assert eng.get_by_id("ctx")["ok"] is True


# ---------------------------------------------------------------------- #
# Group Commit (SyncPolicy)
# ---------------------------------------------------------------------- #
class TestSyncPolicy:
    def test_batch_policy(self, db_path):
        """Test that BATCH policy defers fsync until threshold."""
        eng = StorageEngine(db_path, sync_policy=SyncPolicy.BATCH, sync_batch_size=3)
        assert eng._unflushed_writes == 0

        eng.insert({"_id": "1"})
        assert eng._unflushed_writes == 1

        eng.insert({"_id": "2"})
        assert eng._unflushed_writes == 2

        # 3rd write should trigger fsync and reset counter
        eng.insert({"_id": "3"})
        assert eng._unflushed_writes == 0
        eng.close()

    def test_manual_sync(self, db_path):
        """Test that sync() manually flushes and resets the counter."""
        eng = StorageEngine(db_path, sync_policy=SyncPolicy.BATCH, sync_batch_size=100)
        eng.insert({"_id": "1"})
        assert eng._unflushed_writes == 1
        eng.sync()
        assert eng._unflushed_writes == 0
        eng.close()


# ---------------------------------------------------------------------- #
# Compaction
# ---------------------------------------------------------------------- #
class TestCompaction:
    def test_compaction_reclaims_space(self, db_path):
        """Compaction must reduce file size by dropping dead bytes."""
        eng = StorageEngine(db_path)

        # 1. Insert a document
        eng.insert({"_id": "c1", "data": "A" * 1024})  # 1KB payload
        
        # 2. Update it multiple times (creating dead bytes)
        for i in range(5):
            eng.update("c1", {"data": f"B{i}" * 1024})
        
        # 3. Delete a document (creating a tombstone)
        eng.insert({"_id": "c2", "data": "C" * 1024})
        eng.delete("c2")

        # 4. Insert a document that stays alive
        eng.insert({"_id": "c3", "data": "D" * 1024})

        # Measure bloated file size
        eng.sync()
        bloated_size = os.path.getsize(db_path)

        # Compact
        eng.compact()
        compacted_size = os.path.getsize(db_path)

        # File size must be significantly smaller (we dropped ~6 payloads)
        assert compacted_size < bloated_size

        # Data must remain intact
        assert eng.count() == 2
        assert "B4" in eng.get_by_id("c1")["data"]
        assert "D" in eng.get_by_id("c3")["data"]
        assert eng.get_by_id("c2") is None

        eng.close()
