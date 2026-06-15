# Delete Data

Use `delete from` to remove documents.

## Delete Matching Documents

```sql
delete from users
    active = false
```

## Delete One Document

```sql
delete from users
    _id = "user-001"
```

## Delete Everything

```sql
delete from users
```

!!! danger
    Delete without conditions removes every document in the collection.

## How Delete Works

SreeBase appends a tombstone record. During recovery, tombstones tell the storage engine that the document is no longer live.

