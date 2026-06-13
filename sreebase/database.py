"""
SreeBase Database Abstraction.
==============================

Manages the lifecycle of multiple StorageEngines and tracks 
metadata about collections in a hidden system collection.
"""

import os
import time
import threading
from typing import Dict, List

from sreebase.storage.engine import StorageEngine

SYSTEM_COLLECTION = "_system.collections"

class Database:
    """
    Manages active collections and their metadata.
    """
    def __init__(self, data_dir: str):
        self._data_dir = data_dir
        self._engines: Dict[str, StorageEngine] = {}
        self._lock = threading.RLock()
        
        os.makedirs(self._data_dir, exist_ok=True)
        
        # Ensure the system collection engine is initialized immediately
        self._sys_engine = self._get_or_create_engine(SYSTEM_COLLECTION)

    def _get_or_create_engine(self, name: str) -> StorageEngine:
        with self._lock:
            if name not in self._engines:
                filepath = os.path.join(self._data_dir, f"{name}.sree")
                
                # Check if this is a brand new collection
                is_new = not os.path.exists(filepath)
                
                engine = StorageEngine(filepath)
                self._engines[name] = engine
                
                # Log metadata for non-system collections
                if is_new and name != SYSTEM_COLLECTION:
                    self._sys_engine.insert({
                        "_id": name,
                        "name": name,
                        "created_at": time.time(),
                        "indexes": []
                    })
                elif not is_new and name != SYSTEM_COLLECTION:
                    # Rebuild persisted indexes
                    doc = self._sys_engine.get_by_id(name)
                    if doc and "indexes" in doc:
                        for field in doc["indexes"]:
                            engine.create_index(field)
                    
            return self._engines[name]

    def get_engine(self, name: str) -> StorageEngine:
        """Get the storage engine for a collection, creating it if necessary."""
        return self._get_or_create_engine(name)

    def list_collections(self) -> List[dict]:
        """
        Return a list of user collections with dynamically computed stats.
        """
        collections = []
        with self._lock:
            # We use the system collection as the source of truth for what collections exist
            sys_docs = self._sys_engine.get_all()
            
            for doc in sys_docs:
                name = doc["name"]
                if name.startswith("_system."):
                    continue
                
                # Ensure it's actively loaded so we can read stats
                engine = self._get_or_create_engine(name)
                
                # Dynamically calculate stats
                try:
                    file_size = os.path.getsize(engine.filepath)
                except FileNotFoundError:
                    file_size = 0
                    
                collections.append({
                    "name": name,
                    "created_at": doc.get("created_at"),
                    "document_count": engine.count(),
                    "disk_size_bytes": file_size
                })
                
        # Sort by creation time
        collections.sort(key=lambda x: x.get("created_at", 0))
        return collections

    def close(self):
        """Close all active storage engines."""
        with self._lock:
            for engine in self._engines.values():
                engine.close()
            self._engines.clear()

    def create_index(self, collection: str, field: str) -> None:
        """Create a secondary index and persist its definition."""
        with self._lock:
            engine = self.get_engine(collection)
            engine.create_index(field)
            
            # Persist
            if collection != SYSTEM_COLLECTION:
                doc = self._sys_engine.get_by_id(collection)
                if doc:
                    indexes = doc.get("indexes", [])
                    if field not in indexes:
                        indexes.append(field)
                        doc["indexes"] = indexes
                        self._sys_engine.update(collection, doc)

    def drop_index(self, collection: str, field: str) -> None:
        """Drop a secondary index and update its definition."""
        with self._lock:
            engine = self.get_engine(collection)
            engine.drop_index(field)
            
            # Persist
            if collection != SYSTEM_COLLECTION:
                doc = self._sys_engine.get_by_id(collection)
                if doc:
                    indexes = doc.get("indexes", [])
                    if field in indexes:
                        indexes.remove(field)
                        doc["indexes"] = indexes
                        self._sys_engine.update(collection, doc)
