"""
Tests for the SreeBase Executor (end-to-end query execution).
"""

import os
import pytest

from sreebase.query.executor import Executor
from sreebase.errors import DuplicateKeyError


@pytest.fixture
def executor(tmp_path):
    # Ensure a fresh data_dir per test
    data_dir = str(tmp_path / "data")
    os.makedirs(data_dir, exist_ok=True)
    exe = Executor(data_dir=data_dir)
    
    # Run tests as admin to bypass RBAC
    original_execute = exe.execute
    def admin_execute(query, role="admin"):
        return original_execute(query, role=role)
    exe.execute = admin_execute
    
    yield exe
    exe.close()


# ---------------------------------------------------------------------- #
# INSERT + GET round-trip
# ---------------------------------------------------------------------- #
class TestInsertAndGet:
    def test_insert_and_get_all(self, executor):
        executor.execute(
            'insert into users\n'
            '    name = "Gowtham"\n'
            '    role = "architect"\n'
        )
        executor.execute(
            'insert into users\n'
            '    name = "Sree"\n'
            '    role = "engineer"\n'
        )
        result = executor.execute("get users\n")
        assert len(result) == 2
        names = {d["name"] for d in result}
        assert names == {"Gowtham", "Sree"}

    def test_insert_returns_id(self, executor):
        result = executor.execute(
            'insert into users\n'
            '    name = "Test"\n'
        )
        assert "_id" in result
        assert "inserted" in result
        assert result["inserted"]["name"] == "Test"


# ---------------------------------------------------------------------- #
# GET with filters
# ---------------------------------------------------------------------- #
class TestGetFiltered:
    def _seed(self, executor):
        for name, age, city in [
            ("Gowtham", 28, "Chennai"),
            ("Sree", 22, "Bangalore"),
            ("Kiran", 30, "Chennai"),
            ("Arun", 19, "Delhi"),
        ]:
            executor.execute(
                f'insert into people\n'
                f'    name = "{name}"\n'
                f'    age = {age}\n'
                f'    city = "{city}"\n'
            )

    def test_filter_gt(self, executor):
        self._seed(executor)
        result = executor.execute("get people\n    age > 25\n")
        names = {d["name"] for d in result}
        assert names == {"Gowtham", "Kiran"}

    def test_filter_eq(self, executor):
        self._seed(executor)
        result = executor.execute(
            'get people\n    city = "Chennai"\n'
        )
        names = {d["name"] for d in result}
        assert names == {"Gowtham", "Kiran"}

    def test_filter_combined(self, executor):
        self._seed(executor)
        result = executor.execute(
            'get people\n    age > 20\n    city = "Chennai"\n'
        )
        names = {d["name"] for d in result}
        assert names == {"Gowtham", "Kiran"}

    def test_filter_no_match(self, executor):
        self._seed(executor)
        result = executor.execute(
            'get people\n    age > 100\n'
        )
        assert result == []


# ---------------------------------------------------------------------- #
# GET with sort and limit
# ---------------------------------------------------------------------- #
class TestGetSortLimit:
    def _seed(self, executor):
        for name, age in [("C", 30), ("A", 20), ("B", 25)]:
            executor.execute(
                f'insert into items\n'
                f'    name = "{name}"\n'
                f'    age = {age}\n'
            )

    def test_sort_asc(self, executor):
        self._seed(executor)
        result = executor.execute(
            "get items\n    sort by name asc\n"
        )
        assert [d["name"] for d in result] == ["A", "B", "C"]

    def test_sort_desc(self, executor):
        self._seed(executor)
        result = executor.execute(
            "get items\n    sort by age desc\n"
        )
        assert [d["age"] for d in result] == [30, 25, 20]

    def test_limit(self, executor):
        self._seed(executor)
        result = executor.execute(
            "get items\n    sort by age asc\n    limit 2\n"
        )
        assert len(result) == 2
        assert result[0]["age"] == 20


# ---------------------------------------------------------------------- #
# UPDATE
# ---------------------------------------------------------------------- #
class TestUpdate:
    def test_update_matching(self, executor):
        executor.execute(
            'insert into users\n'
            '    _id = "u1"\n'
            '    name = "Gowtham"\n'
            '    role = "dev"\n'
        )
        result = executor.execute(
            'update users\n'
            '    where\n'
            '        _id = "u1"\n'
            '    set\n'
            '        role = "architect"\n'
        )
        assert result["matched"] == 1
        assert result["modified"] == 1

        docs = executor.execute("get users\n")
        assert docs[0]["role"] == "architect"
        # Original fields preserved.
        assert docs[0]["name"] == "Gowtham"

    def test_update_no_match(self, executor):
        executor.execute(
            'insert into users\n    name = "X"\n'
        )
        result = executor.execute(
            'update users\n'
            '    where\n'
            '        name = "Z"\n'
            '    set\n'
            '        role = "ghost"\n'
        )
        assert result["matched"] == 0
        assert result["modified"] == 0


# ---------------------------------------------------------------------- #
# DELETE
# ---------------------------------------------------------------------- #
class TestDelete:
    def test_delete_matching(self, executor):
        executor.execute('insert into users\n    name = "A"\n    age = 15\n')
        executor.execute('insert into users\n    name = "B"\n    age = 25\n')
        result = executor.execute("delete from users\n    age < 18\n")
        assert result["deleted"] == 1

        remaining = executor.execute("get users\n")
        assert len(remaining) == 1
        assert remaining[0]["name"] == "B"

    def test_delete_all(self, executor):
        executor.execute('insert into logs\n    msg = "a"\n')
        executor.execute('insert into logs\n    msg = "b"\n')
        result = executor.execute("delete from logs\n")
        assert result["deleted"] == 2
        assert executor.execute("get logs\n") == []


# ---------------------------------------------------------------------- #
# Collection isolation
# ---------------------------------------------------------------------- #
class TestCollectionIsolation:
    def test_separate_collections(self, executor):
        executor.execute('insert into users\n    name = "A"\n')
        executor.execute('insert into logs\n    msg = "hello"\n')
        assert len(executor.execute("get users\n")) == 1
        assert len(executor.execute("get logs\n")) == 1
        # Deleting from one doesn't affect the other.
        executor.execute("delete from users\n")
        assert len(executor.execute("get users\n")) == 0
        assert len(executor.execute("get logs\n")) == 1


# ---------------------------------------------------------------------- #
# Show Collections
# ---------------------------------------------------------------------- #
class TestShowCollections:
    def test_show_collections(self, executor):
        # Initial should be empty (excluding internal system collection)
        cols = executor.execute('show collections\n')
        assert len(cols) == 0
        
        executor.execute('insert into aaa\n    val = 1\n')
        executor.execute('insert into bbb\n    val = 2\n')
        
        cols = executor.execute('show collections\n')
        assert len(cols) == 2
        
        # Verify metadata
        names = {c["name"] for c in cols}
        assert names == {"aaa", "bbb"}
        assert cols[0]["document_count"] == 1
        assert cols[0]["disk_size_bytes"] > 0
        assert "created_at" in cols[0]


# ---------------------------------------------------------------------- #
# Secondary Indexes
# ---------------------------------------------------------------------- #
class TestSecondaryIndexes:
    def test_create_index(self, executor):
        # Seed some data
        executor.execute('insert into items\n    type = "book"\n    name = "A"\n')
        executor.execute('insert into items\n    type = "movie"\n    name = "B"\n')
        executor.execute('insert into items\n    type = "book"\n    name = "C"\n')
        
        # Create an index
        res = executor.execute('create index on items field type\n')
        assert res["status"] == "ok"
        
        # Check engine state
        engine = executor.db.get_engine("items")
        assert engine.has_index("type")
        assert len(engine.get_indexed_docs("type", "book")) == 2
        assert len(engine.get_indexed_docs("type", "movie")) == 1
        
        # Test query uses index correctly
        results = executor.execute('get items\n    type = "book"\n')
        assert len(results) == 2
        assert {d["name"] for d in results} == {"A", "C"}
        
    def test_index_updates_on_mutation(self, executor):
        executor.execute('create index on users field role\n')
        
        # Insert adds to index
        doc_id = executor.execute('insert into users\n    name = "G"\n    role = "admin"\n')["_id"]
        engine = executor.db.get_engine("users")
        assert doc_id in engine.get_indexed_docs("role", "admin")
        
        # Update moves index
        executor.execute(f'update users\n    where\n        _id = "{doc_id}"\n    set\n        role = "guest"\n')
        assert doc_id not in engine.get_indexed_docs("role", "admin")
        assert doc_id in engine.get_indexed_docs("role", "guest")
        
        # Delete removes from index
        executor.execute(f'delete from users\n    _id = "{doc_id}"\n')
        assert doc_id not in engine.get_indexed_docs("role", "guest")
