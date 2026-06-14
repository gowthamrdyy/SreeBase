# Core Concepts

## Database

In SreeBase, a database is a folder that stores collection files.

```text
data/
  users.sree
  orders.sree
  _system.users.sree
```

## Collection

A collection is a named group of documents. It is similar to a table in SQL or a collection in MongoDB.

```sql
insert into users
    name = "Maya"
```

The collection name is `users`.

## Document

A document is a key-value object.

```text
{
  "_id": "generated-id",
  "name": "Maya",
  "role": "developer"
}
```

SreeBase automatically adds `_id` if you do not provide one.

## Query

A query is text that tells SreeBase what to do.

```sql
get users
    role = "developer"
```

## Index

An index speeds up equality lookups for one field.

```sql
create index on users field role
```

After that, this query can use the index:

```sql
get users
    role = "developer"
```

## Role

SreeBase has two roles:

- `admin`: can read, write, create users, and access system collections.
- `read`: can read normal collections only.

## Storage Engine

SreeBase uses append-only files. Inserts, updates, and deletes append records instead of rewriting the whole file immediately.

Compaction can later rewrite the file to keep only live documents.

