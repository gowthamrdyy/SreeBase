# SreeBase Cheat Sheet

## Server

```bash
sreebase serve
sreebase serve --host 127.0.0.1 --port 6969 --data-dir ./data
```

## Shell

```bash
sreebase shell
sreebase shell -u admin
```

## Users

```sql
create user admin password "secret" role admin
login admin password "secret"
```

## Insert

```sql
insert into users
    name = "Maya"
    age = 28
```

## Get

```sql
get users
    age >= 18
    sort by age desc
    limit 10
```

## Update

```sql
update users
    where
        name = "Maya"
    set
        active = true
```

## Delete

```sql
delete from users
    name = "Maya"
```

## Index

```sql
create index on users field name
```

## Aggregate

```sql
aggregate users
    group by role
    calculate count()
```

## SDK

```python
from reddybase.client.driver import Client

with Client() as client:
    client.login("admin", "secret")
    users = client.collection("users")
    users.insert({"name": "Maya", "age": 28})
    users.get(where={"age": (">=", 18)}, sort=("age", "desc"))
```

