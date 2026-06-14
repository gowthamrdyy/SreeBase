# Storage Engine

SreeBase stores each collection in an append-only `.sree` file.

## File Per Collection

```text
data/
  users.sree
  logs.sree
  _system.users.sree
```

## Append-Only Writes

When you insert or update a document, SreeBase appends a new record to the file.

When you delete a document, SreeBase appends a tombstone.

## In-Memory Index

At startup, SreeBase replays the file and builds an in-memory map:

```text
document_id -> file offset
```

This lets point reads seek directly to the latest version of a document.

## Recovery

On restart, the engine reads records from the beginning of the file:

- latest write wins
- tombstones remove documents
- torn trailing records are truncated

## Compaction

Compaction rewrites live documents into a new file and swaps it into place.

Current compaction uses an exclusive lock. That means reads and writes wait while compaction runs, but the behavior is simple and correct.

## Sync Policy

The storage engine supports:

- `EVERY_WRITE`: fsync after every write
- `BATCH`: fsync after a batch of writes or manual sync

