"""
SreeBase Storage Engine v2 — Offset-Indexed Append Log
=======================================================

A Bitcask/LSM-inspired storage core.

Index   : doc_id -> RecordPointer(offset, length)   (RAM holds pointers, not data)
Log     : length-prefixed binary frames, append-only, crash-resilient
Writes  : insert / update append new frames; delete appends a tombstone
Reads   : O(1) index lookup -> single seek+read from disk
Recovery: replay frames sequentially; last-write-wins; tombstones unset keys
Safety  : single RLock guards index + file handle for concurrency

On-disk frame format
--------------------
::

    ┌──────────────┬───────────────┬─────────────────────────────┐
    │  MAGIC (1B)  │  LENGTH (4B)  │  JSON PAYLOAD (N bytes)     │
    │  0x5B / 0x5C │  big-endian   │  UTF-8 encoded              │
    └──────────────┴───────────────┴─────────────────────────────┘
       0x5B = live record (PUT)
       0x5C = tombstone   (DELETE)
"""

import os
import json
import uuid
import struct
import threading
from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Iterator, Set

from sreebase.errors import (
    StorageError,
    DuplicateKeyError,
    CorruptRecordError,
)

# ---------------------------------------------------------------------- #
# On-disk frame constants
# ---------------------------------------------------------------------- #
MAGIC_PUT = 0x5B        # live record
MAGIC_TOMBSTONE = 0x5C  # deletion marker
HEADER_FMT = ">BI"      # 1 unsigned byte + 1 unsigned int (big-endian)
HEADER_SIZE = struct.calcsize(HEADER_FMT)  # == 5 bytes


class SyncPolicy(Enum):
    """Configuration for fsync durability guarantees."""
    EVERY_WRITE = auto()  # Strict ACID durability (fsync on every append)
    BATCH = auto()        # High throughput (fsync every N writes or manually)


@dataclass(frozen=True)
class RecordPointer:
    """
    Where a document's frame lives in the log.

    We store the *payload* offset/length (i.e. pointing past the header),
    so reads can grab exactly the JSON bytes in one shot.
    """
    offset: int   # byte offset of the payload within the .sree file
    length: int   # payload length in bytes


class StorageEngine:
    """
    The offset-indexed append-only storage core for SreeBase.

    Public surface
    --------------
    insert(document)        -> str            (create; fails on dup _id)
    get_by_id(doc_id)       -> dict | None    (point read)
    update(doc_id, doc)     -> dict           (full replace; upsert-able)
    delete(doc_id)          -> bool           (tombstone)
    get_all()               -> list[dict]     (full scan via pointers)
    scan()                  -> iterator       (streaming full scan)
    """

    ID_FIELD = "_id"

    def __init__(
        self,
        filepath: str,
        sync_policy: SyncPolicy = SyncPolicy.EVERY_WRITE,
        sync_batch_size: int = 100,
    ) -> None:
        """
        Initialize the engine against a given ``.sree`` file.

        Parameters
        ----------
        filepath : str
            Path to the storage file. Created if it does not exist.
            The ``.sree`` extension is appended automatically if missing.
        sync_policy : SyncPolicy
            Whether to fsync on every write or batch them.
        sync_batch_size : int
            If using BATCH policy, automatically fsync after this many writes.
        """
        if not filepath.endswith(".sree"):
            filepath = f"{filepath}.sree"
        self._filepath: str = filepath

        self._sync_policy = sync_policy
        self._sync_batch_size = sync_batch_size
        self._unflushed_writes: int = 0

        # doc_id -> RecordPointer.  The whole point: RAM holds only pointers.
        self._index: Dict[str, RecordPointer] = {}

        # field_name -> field_value -> set of doc_ids
        self._indexes: Dict[str, Dict[Any, Set[str]]] = {}

        # One reentrant lock guards both the index and the file handle.
        self._lock = threading.RLock()

        # Track where the next append will land (EOF). Maintained manually
        # so we never rely on the OS file position across interleaved I/O.
        self._write_offset: int = 0

        # Ensure the parent directory exists before we touch the file.
        parent = os.path.dirname(os.path.abspath(self._filepath))
        os.makedirs(parent, exist_ok=True)

        # Long-lived handle, binary, read + append.
        self._fh = open(self._filepath, "a+b")

        # Replay the existing log to rebuild the in-memory index.
        self._hydrate()

    # ------------------------------------------------------------------ #
    # Frame encode / decode
    # ------------------------------------------------------------------ #
    @staticmethod
    def _encode_frame(magic: int, payload: bytes) -> bytes:
        """Prepend a 5-byte header to the payload."""
        return struct.pack(HEADER_FMT, magic, len(payload)) + payload

    def _serialize(self, document: Dict[str, Any]) -> bytes:
        """Document -> compact UTF-8 JSON payload."""
        return json.dumps(
            document, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")

    # ------------------------------------------------------------------ #
    # Startup recovery (hydration)
    # ------------------------------------------------------------------ #
    def _hydrate(self) -> None:
        """
        Replay the log frame-by-frame to rebuild the offset index.

        - PUT frames set/overwrite the pointer (last-write-wins).
        - TOMBSTONE frames remove the key.
        - A truncated/torn frame at the tail (from a crash mid-write) is
          detected and the file is truncated back to the last good frame,
          self-healing the log.
        """
        with self._lock:
            self._index.clear()
            self._fh.seek(0, os.SEEK_END)
            file_size = self._fh.tell()
            self._fh.seek(0, os.SEEK_SET)

            offset = 0
            while offset < file_size:
                # --- read header ---
                header = self._fh.read(HEADER_SIZE)
                if len(header) < HEADER_SIZE:
                    # Torn header -> truncate the partial tail.
                    self._truncate_to(offset)
                    break

                magic, length = struct.unpack(HEADER_FMT, header)
                payload_offset = offset + HEADER_SIZE

                if magic not in (MAGIC_PUT, MAGIC_TOMBSTONE):
                    raise CorruptRecordError(
                        f"Bad magic byte {magic:#x} at offset {offset}"
                    )

                # --- read payload ---
                payload = self._fh.read(length)
                if len(payload) < length:
                    # Torn payload -> truncate the partial tail.
                    self._truncate_to(offset)
                    break

                try:
                    document = json.loads(payload.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    raise CorruptRecordError(
                        f"Unparseable payload at offset {offset}"
                    )

                doc_id = document.get(self.ID_FIELD)
                if doc_id is not None:
                    doc_id = str(doc_id)
                    if magic == MAGIC_PUT:
                        self._index[doc_id] = RecordPointer(
                            payload_offset, length
                        )
                    else:  # tombstone
                        self._index.pop(doc_id, None)

                # Advance past this whole frame.
                offset = payload_offset + length

            self._write_offset = offset
            self._fh.seek(self._write_offset, os.SEEK_SET)

    def _truncate_to(self, size: int) -> None:
        """Cut the file back to ``size`` bytes and fsync (self-healing)."""
        self._fh.flush()
        self._fh.truncate(size)
        os.fsync(self._fh.fileno())

    # ------------------------------------------------------------------ #
    # Low-level append (shared by insert/update/delete)
    # ------------------------------------------------------------------ #
    def _append(self, magic: int, document: Dict[str, Any]) -> RecordPointer:
        """
        Append one frame durably and return the payload pointer.
        Caller **must** hold ``self._lock``.
        """
        payload = self._serialize(document)
        frame = self._encode_frame(magic, payload)

        self._fh.seek(self._write_offset, os.SEEK_SET)
        self._fh.write(frame)
        self._fh.flush()                # flush Python's buffer -> OS

        # Group commit / fsync logic
        if self._sync_policy == SyncPolicy.EVERY_WRITE:
            os.fsync(self._fh.fileno())     # flush OS cache -> disk platter
        else:
            self._unflushed_writes += 1
            if self._unflushed_writes >= self._sync_batch_size:
                os.fsync(self._fh.fileno())
                self._unflushed_writes = 0

        payload_offset = self._write_offset + HEADER_SIZE
        self._write_offset += len(frame)
        return RecordPointer(payload_offset, len(payload))

    def sync(self) -> None:
        """
        Force a manual fsync to disk. Useful when using BATCH sync policy
        to ensure all recent writes are durably saved.
        """
        with self._lock:
            if self._fh and not self._fh.closed:
                self._fh.flush()
                os.fsync(self._fh.fileno())
                self._unflushed_writes = 0

    # ------------------------------------------------------------------ #
    # Index management
    # ------------------------------------------------------------------ #
    def _add_to_indexes(self, doc_id: str, document: Dict[str, Any]) -> None:
        for field, index_map in self._indexes.items():
            value = document.get(field)
            if value is not None:
                try:
                    if value not in index_map:
                        index_map[value] = set()
                    index_map[value].add(doc_id)
                except TypeError:
                    pass  # Unhashable types (dicts/lists) can't be indexed

    def _remove_from_indexes(self, doc_id: str, document: Dict[str, Any]) -> None:
        for field, index_map in self._indexes.items():
            value = document.get(field)
            if value is not None:
                try:
                    if value in index_map:
                        index_map[value].discard(doc_id)
                        if not index_map[value]:
                            del index_map[value]
                except TypeError:
                    pass

    def create_index(self, field: str) -> None:
        """Create a secondary index on a specific field."""
        with self._lock:
            if field in self._indexes:
                return
            
            index_map = {}
            self._indexes[field] = index_map
            
            # Scan existing documents to build the index
            for doc in self.scan():
                value = doc.get(field)
                if value is not None:
                    try:
                        if value not in index_map:
                            index_map[value] = set()
                        index_map[value].add(doc[self.ID_FIELD])
                    except TypeError:
                        pass

    def drop_index(self, field: str) -> None:
        """Drop a secondary index."""
        with self._lock:
            self._indexes.pop(field, None)
            
    def has_index(self, field: str) -> bool:
        """Check if an index exists for a field."""
        with self._lock:
            return field in self._indexes
            
    def get_indexed_docs(self, field: str, value: Any) -> Set[str]:
        """O(1) lookup of document IDs for an indexed field/value."""
        with self._lock:
            if field not in self._indexes:
                return set()
            try:
                return self._indexes[field].get(value, set()).copy()
            except TypeError:
                return set()

    # ------------------------------------------------------------------ #
    # Write path
    # ------------------------------------------------------------------ #
    def insert(self, document: Dict[str, Any]) -> str:
        """
        Create a new document.  Auto-generates ``_id`` if absent.

        Returns
        -------
        str
            The document id.

        Raises
        ------
        StorageError
            If ``document`` is not a dict.
        DuplicateKeyError
            If the supplied ``_id`` already exists.
        """
        if not isinstance(document, dict):
            raise StorageError("Document must be a dictionary (JSON object).")

        # Work on a shallow copy so we never mutate the caller's object.
        record = dict(document)

        # Assign an id if the caller didn't supply one.
        doc_id = record.get(self.ID_FIELD)
        doc_id = uuid.uuid4().hex if doc_id is None else str(doc_id)
        record[self.ID_FIELD] = doc_id

        with self._lock:
            if doc_id in self._index:
                raise DuplicateKeyError(
                    f"_id '{doc_id}' already exists."
                )

            # 1. Durably append to disk FIRST (write-ahead principle).
            #    If the process dies after the disk write but before the
            #    index update, _hydrate() will recover it.
            ptr = self._append(MAGIC_PUT, record)

            # 2. Update the in-memory index.
            self._index[doc_id] = ptr
            
            # 3. Update secondary indexes
            self._add_to_indexes(doc_id, record)

        return doc_id

    def update(
        self,
        doc_id: Any,
        document: Dict[str, Any],
        upsert: bool = False,
    ) -> Dict[str, Any]:
        """
        Full-replace the document at ``doc_id`` by appending a new version.

        If the id doesn't exist: raises unless ``upsert=True``.
        The ``_id`` field is always preserved/forced to ``doc_id``.
        """
        if not isinstance(document, dict):
            raise StorageError("Document must be a dictionary (JSON object).")

        key = str(doc_id)
        record = dict(document)
        record[self.ID_FIELD] = key

        with self._lock:
            if key not in self._index and not upsert:
                raise StorageError(f"Cannot update: _id '{key}' not found.")
                
            old_doc = None
            if key in self._index:
                old_doc = self._read_pointer(self._index[key])
                
            ptr = self._append(MAGIC_PUT, record)
            self._index[key] = ptr
            
            if old_doc is not None:
                self._remove_from_indexes(key, old_doc)
            self._add_to_indexes(key, record)

        return dict(record)

    def delete(self, doc_id: Any) -> bool:
        """
        Soft-delete by appending a tombstone, then drop the key from index.

        Returns ``True`` if a document was removed, ``False`` if the id
        didn't exist.
        """
        key = str(doc_id)
        with self._lock:
            if key not in self._index:
                return False
                
            old_doc = self._read_pointer(self._index[key])
                
            # Tombstone payload only needs the id for recovery replay.
            self._append(MAGIC_TOMBSTONE, {self.ID_FIELD: key})
            self._index.pop(key, None)
            
            self._remove_from_indexes(key, old_doc)
            return True

    # ------------------------------------------------------------------ #
    # Read path
    # ------------------------------------------------------------------ #
    def _read_pointer(self, ptr: RecordPointer) -> Dict[str, Any]:
        """One seek + read to materialize a document. Caller holds lock."""
        self._fh.seek(ptr.offset, os.SEEK_SET)
        payload = self._fh.read(ptr.length)
        # Restore the write cursor so subsequent appends stay correct.
        self._fh.seek(self._write_offset, os.SEEK_SET)
        return json.loads(payload.decode("utf-8"))

    def get_by_id(self, doc_id: Any) -> Optional[Dict[str, Any]]:
        """O(1) index lookup + single disk read."""
        key = str(doc_id)
        with self._lock:
            ptr = self._index.get(key)
            if ptr is None:
                return None
            return self._read_pointer(ptr)

    def scan(self) -> Iterator[Dict[str, Any]]:
        """
        Stream every live document.

        Used by the query executor's WHERE filtering. Snapshots the
        pointer set under the lock, then reads each — so a long scan
        doesn't hold the write lock the whole time.
        """
        with self._lock:
            pointers = list(self._index.values())
        for ptr in pointers:
            with self._lock:
                yield self._read_pointer(ptr)

    def get_all(self) -> List[Dict[str, Any]]:
        """Materialize all live documents into a list."""
        return list(self.scan())

    # ------------------------------------------------------------------ #
    # Lifecycle / introspection / compaction
    # ------------------------------------------------------------------ #
    @property
    def filepath(self) -> str:
        """Path to the underlying ``.sree`` data file."""
        return self._filepath

    def count(self) -> int:
        """Number of live documents in the index."""
        with self._lock:
            return len(self._index)

    def close(self) -> None:
        """Flush and close the underlying file handle. Idempotent."""
        with self._lock:
            if self._fh and not self._fh.closed:
                self.sync()
                self._fh.close()

    def compact(self) -> None:
        """
        Rewrite the log to drop dead bytes (overwritten docs and tombstones).

        Uses a "catch-up" strategy to minimize lock contention:
        1. Snapshot live pointers and current EOF.
        2. Read live data and write to ``.compacting`` (lock is only held briefly per read).
        3. Take the lock exclusively to block writes.
        4. Copy any new writes that happened during step 2 to ``.compacting``.
        5. Swap the file atomically and re-hydrate the index.
        """
        compact_path = f"{self._filepath}.compacting"

        # 1. Snapshot
        with self._lock:
            snapshot = list(self._index.values())
            catchup_offset = self._write_offset

        # 2. Build the compacted file (concurrent appends can happen here)
        with open(compact_path, "wb") as cfh:
            for ptr in snapshot:
                # Need the lock just for the brief read from the main file
                # to prevent file pointer races.
                with self._lock:
                    doc = self._read_pointer(ptr)

                payload = self._serialize(doc)
                frame = self._encode_frame(MAGIC_PUT, payload)
                cfh.write(frame)
            
            cfh.flush()
            os.fsync(cfh.fileno())

            # 3. Swap phase (exclusive lock)
            with self._lock:
                # Flush any pending writes to the main file so we can read them.
                self.sync()

                # 4. Catch-up: copy everything written since `catchup_offset`
                if self._write_offset > catchup_offset:
                    self._fh.seek(catchup_offset, os.SEEK_SET)
                    remaining = self._fh.read(self._write_offset - catchup_offset)
                    cfh.write(remaining)
                    cfh.flush()
                    os.fsync(cfh.fileno())

                # 5. Swap the files
                self._fh.close()
                os.replace(compact_path, self._filepath)
                
                # Re-open and re-hydrate completely (fast because it's compacted).
                self._fh = open(self._filepath, "a+b")
                self._write_offset = 0
                self._hydrate()

    # Context-manager sugar:  ``with StorageEngine("data") as db: ...``
    def __enter__(self) -> "StorageEngine":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
