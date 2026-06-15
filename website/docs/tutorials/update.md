# Update Data

Use `update` to modify matching documents.

## Update Matching Documents

```sql
update users
    where
        role = "developer"
    set
        active = true
```

## Update One Document By ID

```sql
update users
    where
        _id = "user-001"
    set
        role = "admin"
```

## Update All Documents

If you omit `where`, every document in the collection is updated.

```sql
update users
    set
        active = false
```

!!! warning
    Update without `where` is powerful. Use it only when you really want to change every document.

## How Update Works

SreeBase reads matching documents, merges the new fields, and appends updated versions to the storage file.

