"""
SreeBase — Centralized exception hierarchy.
============================================

Keeping all engine errors in one module means callers (the executor,
the future TCP server) can catch ``SreeBaseError`` to handle anything,
or catch a specific subclass for fine-grained control.
"""


class SreeBaseError(Exception):
    """Root of all SreeBase exceptions."""


# ---- Storage layer ------------------------------------------------------ #

class StorageError(SreeBaseError):
    """Base for storage-engine failures."""


class DuplicateKeyError(StorageError):
    """Inserting a document whose ``_id`` already exists."""


class CorruptRecordError(StorageError):
    """A frame on disk failed structural validation."""


# ---- Query layer -------------------------------------------------------- #

class QueryError(SreeBaseError):
    """Base for query language failures."""


class LexerError(QueryError):
    """Raised when the source text cannot be tokenized."""


class ParserError(QueryError):
    """Raised when tokens cannot form a valid statement (AST)."""


class ExecutionError(QueryError):
    """Raised when a structurally valid AST cannot be executed."""
