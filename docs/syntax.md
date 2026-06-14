# Bracketless Query Syntax

SreeBase queries are written as plain text. Instead of braces and commas, blocks are created with indentation.

## Rules To Remember

- The first line starts the command.
- Indented lines belong to that command.
- A blank line in the CLI executes the query.
- Strings use double quotes.
- Supported values are strings, numbers, booleans, and `null`.
- Conditions use `=`, `!=`, `>`, `>=`, `<`, or `<=`.

## Insert

```sql
insert into users
    name = "Maya"
    role = "developer"
    age = 28
    active = true
```

## Get

```sql
get users
    role = "developer"
    age >= 21
    sort by age desc
    limit 10
```

## Update

```sql
update users
    where
        role = "developer"
    set
        active = true
```

## Delete

```sql
delete from users
    active = false
```

!!! warning "Delete without conditions"
    `delete from users` deletes every document in the `users` collection.

## Create Index

```sql
create index on users field role
```

Indexes speed up equality filters such as:

```sql
get users
    role = "developer"
```

## Show Collections

```sql
show collections
```

## Aggregate

```sql
aggregate users
    where
        active = true
    group by role
    calculate avg(age), count()
```

## Users and Login

The first user can be created anonymously on a fresh database:

```sql
create user admin password "supersecret" role admin
```

After that, log in before running normal queries:

```sql
login admin password "supersecret"
```

## Supported Roles

| Role | Can read normal collections | Can write normal collections | Can manage users | Can access `_system.*` |
| --- | --- | --- | --- | --- |
| `admin` | Yes | Yes | Yes | Yes |
| `read` | Yes | No | No | No |

