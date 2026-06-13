"""
SreeBase Query Language — Executor (AST → Storage Engine)
==========================================================

The executor is the bridge between the parsed AST and the storage engine.
It pattern-matches on statement types and translates them into storage
engine calls.

Collection routing
------------------
Each collection name maps to its own ``.sree`` file under a configurable
data directory.  The executor lazily creates ``StorageEngine`` instances
per collection and caches them for the lifetime of the ``Executor``.

Filter evaluation
-----------------
Conditions from GET/UPDATE/DELETE are evaluated in-memory by scanning
all documents (full table scan + filter).  This is correct for V1;
secondary indexes (Step 6) will make it fast.
"""

import os
import operator
from typing import Any, Callable, Dict, List, Optional

from sreebase.storage.engine import StorageEngine
from sreebase.database import Database
from sreebase.query.ast_nodes import (
    Condition,
    GetStatement,
    InsertStatement,
    UpdateStatement,
    DeleteStatement,
    ShowCollectionsStatement,
    CreateIndexStatement,
    CreateUserStatement,
    LoginStatement,
    AggregateStatement,
)
from sreebase.query.aggregator import Aggregator
from sreebase.query.lexer import Lexer
from sreebase.query.parser import Parser
from sreebase.errors import ExecutionError


# ---------------------------------------------------------------------- #
# Comparison operator dispatch table
# ---------------------------------------------------------------------- #
_OPS: Dict[str, Callable[[Any, Any], bool]] = {
    "=":  operator.eq,
    "!=": operator.ne,
    ">":  operator.gt,
    ">=": operator.ge,
    "<":  operator.lt,
    "<=": operator.le,
}


class Executor:
    """
    Executes parsed AST statements against ``StorageEngine`` instances.

    Parameters
    ----------
    data_dir : str
        Root directory for all ``.sree`` data files.  Each collection
        gets its own file: ``<data_dir>/<collection>.sree``.
    """

    def __init__(self, data_dir: str = "data") -> None:
        self.db = Database(data_dir=data_dir)

    # ------------------------------------------------------------------ #
    # Engine lifecycle
    # ------------------------------------------------------------------ #
    def close(self) -> None:
        """Close all open storage engines."""
        self.db.close()

    def __enter__(self) -> "Executor":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ------------------------------------------------------------------ #
    # High-level: execute raw query text
    # ------------------------------------------------------------------ #
    def execute(self, query: str, role: Optional[str] = None) -> Any:
        """
        Parse and execute a bracketless query string.

        Returns the result of the statement (varies by type — see below).
        For multi-statement input, returns a list of results.
        """
        tokens = Lexer(query).tokenize()
        statements = Parser(tokens).parse()

        if not statements:
            raise ExecutionError("Empty query — nothing to execute.")

        results = [self._dispatch(stmt, role) for stmt in statements]
        return results[0] if len(results) == 1 else results

    # ------------------------------------------------------------------ #
    # Dispatch
    # ------------------------------------------------------------------ #
    def _dispatch(self, stmt, role: Optional[str]) -> Any:
        # Check if system is bootstrapped
        users_exist = self.db.get_engine("_system.users").count() > 0

        if not role:
            # Anonymous access is strictly limited
            if isinstance(stmt, LoginStatement):
                pass
            elif isinstance(stmt, CreateUserStatement) and not users_exist:
                pass
            else:
                raise ExecutionError("Authentication required. Please login.")
        else:
            # RBAC checks
            restricted = (InsertStatement, UpdateStatement, DeleteStatement, CreateIndexStatement, CreateUserStatement)
            if role == "read" and isinstance(stmt, restricted):
                raise ExecutionError(f"Permission denied: role '{role}' cannot execute {type(stmt).__name__}")
            if role != "admin" and isinstance(stmt, CreateUserStatement):
                raise ExecutionError("Permission denied: only 'admin' can create users.")

        if isinstance(stmt, CreateIndexStatement):
            return self._exec_create_index(stmt)
        if isinstance(stmt, CreateUserStatement):
            return self._exec_create_user(stmt)
        if isinstance(stmt, LoginStatement):
            return self._exec_login(stmt)
        if isinstance(stmt, AggregateStatement):
            return self._exec_aggregate(stmt)
        if isinstance(stmt, ShowCollectionsStatement):
            return self._exec_show_collections()
        if isinstance(stmt, GetStatement):
            return self._exec_get(stmt)
        if isinstance(stmt, InsertStatement):
            return self._exec_insert(stmt)
        if isinstance(stmt, UpdateStatement):
            return self._exec_update(stmt)
        if isinstance(stmt, DeleteStatement):
            return self._exec_delete(stmt)
        raise ExecutionError(f"Unknown statement type: {type(stmt).__name__}")

    # ------------------------------------------------------------------ #
    # SECURITY & USERS
    # ------------------------------------------------------------------ #
    def _exec_create_user(self, stmt: CreateUserStatement) -> Dict[str, Any]:
        engine = self.db.get_engine("_system.users")
        existing = self._filter(engine, [Condition(field="username", op="=", value=stmt.username)])
        if existing:
            raise ExecutionError(f"User '{stmt.username}' already exists.")
            
        engine.insert({
            "username": stmt.username,
            "password": stmt.password,
            "role": stmt.role
        })
        return {"status": "ok", "message": f"User '{stmt.username}' created with role '{stmt.role}'"}

    def _exec_login(self, stmt: LoginStatement) -> Dict[str, Any]:
        engine = self.db.get_engine("_system.users")
        results = self._filter(engine, [
            Condition(field="username", op="=", value=stmt.username),
            Condition(field="password", op="=", value=stmt.password)
        ])
        if not results:
            raise ExecutionError("Invalid username or password.")
        
        user = results[0]
        return {"_internal_login_role": user["role"], "status": "ok", "message": f"Logged in as {user['username']}"}

    # ------------------------------------------------------------------ #
    # AGGREGATE
    # ------------------------------------------------------------------ #
    def _exec_aggregate(self, stmt: AggregateStatement) -> List[Dict[str, Any]]:
        engine = self.db.get_engine(stmt.collection)
        filtered_docs = self._filter(engine, stmt.conditions)
        return Aggregator.aggregate(stmt, filtered_docs)

    # ------------------------------------------------------------------ #
    # CREATE INDEX
    # ------------------------------------------------------------------ #
    def _exec_create_index(self, stmt: CreateIndexStatement) -> Dict[str, Any]:
        """Execute a CREATE INDEX statement."""
        self.db.create_index(stmt.collection, stmt.field)
        return {"status": "ok", "message": f"Index created on '{stmt.collection}' field '{stmt.field}'"}

    # ------------------------------------------------------------------ #
    # SHOW COLLECTIONS
    # ------------------------------------------------------------------ #
    def _exec_show_collections(self) -> List[Dict[str, Any]]:
        """
        Execute a SHOW COLLECTIONS query.
        """
        return self.db.list_collections()

    # ------------------------------------------------------------------ #
    # GET
    # ------------------------------------------------------------------ #
    def _exec_get(self, stmt: GetStatement) -> List[Dict[str, Any]]:
        """
        Execute a GET query.

        Returns a list of documents matching all conditions (AND logic).
        Applies optional sorting and limit.
        """
        engine = self.db.get_engine(stmt.collection)
        results = self._filter(engine, stmt.conditions)

        # Sorting.
        if stmt.sort is not None:
            field = stmt.sort.field
            asc = stmt.sort.ascending
            results.sort(
                key=lambda doc: doc.get(field, ""),
                reverse=(not asc),
            )

        # Limit.
        if stmt.limit is not None:
            results = results[: stmt.limit]

        return results

    # ------------------------------------------------------------------ #
    # INSERT
    # ------------------------------------------------------------------ #
    def _exec_insert(self, stmt: InsertStatement) -> Dict[str, Any]:
        """
        Execute an INSERT statement.

        Returns ``{"_id": <generated_id>, "inserted": <document>}``.
        """
        engine = self.db.get_engine(stmt.collection)
        doc_id = engine.insert(stmt.document)
        return {
            "_id": doc_id,
            "inserted": engine.get_by_id(doc_id),
        }

    # ------------------------------------------------------------------ #
    # UPDATE
    # ------------------------------------------------------------------ #
    def _exec_update(self, stmt: UpdateStatement) -> Dict[str, Any]:
        """
        Execute an UPDATE statement.

        Finds all documents matching the WHERE conditions, merges the SET
        assignments into each, and writes them back.

        Returns ``{"matched": N, "modified": N}``.
        """
        engine = self.db.get_engine(stmt.collection)
        matches = self._filter(engine, stmt.conditions)

        modified = 0
        for doc in matches:
            doc_id = doc[StorageEngine.ID_FIELD]
            # Merge the new field values into the existing document.
            merged = dict(doc)
            merged.update(stmt.assignments)
            engine.update(doc_id, merged)
            modified += 1

        return {"matched": len(matches), "modified": modified}

    # ------------------------------------------------------------------ #
    # DELETE
    # ------------------------------------------------------------------ #
    def _exec_delete(self, stmt: DeleteStatement) -> Dict[str, Any]:
        """
        Execute a DELETE statement.

        If no conditions, deletes **all** documents in the collection.
        Returns ``{"deleted": N}``.
        """
        engine = self.db.get_engine(stmt.collection)

        if not stmt.conditions:
            # Delete everything.
            all_docs = engine.get_all()
            count = 0
            for doc in all_docs:
                if engine.delete(doc[StorageEngine.ID_FIELD]):
                    count += 1
            return {"deleted": count}

        matches = self._filter(engine, stmt.conditions)
        count = 0
        for doc in matches:
            if engine.delete(doc[StorageEngine.ID_FIELD]):
                count += 1
        return {"deleted": count}

    # ------------------------------------------------------------------ #
    # Filtering (shared by GET / UPDATE / DELETE)
    # ------------------------------------------------------------------ #
    def _filter(
        self,
        engine: StorageEngine,
        conditions: List[Condition],
    ) -> List[Dict[str, Any]]:
        """
        Evaluate conditions against the collection.
        If an equality condition exists for an indexed field, performs an O(1)
        lookup to narrow down candidates before full evaluation.
        """
        if not conditions:
            return engine.get_all()

        # Check for indexed fields with equality operator
        indexed_conds = []
        unindexed_conds = []
        for cond in conditions:
            if cond.op == "=" and engine.has_index(cond.field):
                indexed_conds.append(cond)
            else:
                unindexed_conds.append(cond)

        if indexed_conds:
            # Get intersection of all indexed conditions
            candidates = None
            for cond in indexed_conds:
                matched_ids = engine.get_indexed_docs(cond.field, cond.value)
                if candidates is None:
                    candidates = matched_ids
                else:
                    candidates.intersection_update(matched_ids)
                
                # Short-circuit if intersection is empty
                if not candidates:
                    return []
                    
            # Fetch candidate docs and evaluate remaining conditions
            results = []
            for doc_id in candidates:
                doc = engine.get_by_id(doc_id)
                if doc and all(self._evaluate(doc, cond) for cond in unindexed_conds):
                    results.append(doc)
            return results

        # Fallback to full scan
        results = []
        for doc in engine.scan():
            if all(self._evaluate(doc, cond) for cond in conditions):
                results.append(doc)
        return results

    @staticmethod
    def _evaluate(doc: Dict[str, Any], cond: Condition) -> bool:
        """
        Evaluate a single condition against a document.

        Missing fields fail the condition (return False) for all operators
        except ``!=`` (a missing field is "not equal" to anything).
        """
        value = doc.get(cond.field)

        if value is None and cond.field not in doc:
            # Field is truly absent (not just set to null).
            return cond.op == "!="

        op_fn = _OPS.get(cond.op)
        if op_fn is None:
            raise ExecutionError(f"Unknown operator: {cond.op}")

        try:
            return op_fn(value, cond.value)
        except TypeError:
            # Incompatible types (e.g. comparing string to int).
            return False
