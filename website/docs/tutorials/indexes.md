# Indexes

Indexes make equality lookups faster.

## Create An Index

```sql
create index on users field role
```

## Query With An Indexed Field

```sql
get users
    role = "developer"
```

## Good Index Fields

Choose fields that appear often in equality filters:

- `username`
- `email`
- `role`
- `status`
- `department`

## What Indexes Do Not Speed Up Yet

Current SreeBase indexes are simple hash maps. They do not speed up:

- range filters such as `age > 18`
- sorting
- text search
- compound conditions across multiple fields unless each equality field has its own index

## Index Persistence

SreeBase stores index definitions in system metadata. When a collection is reopened, the index is rebuilt from the stored documents.

