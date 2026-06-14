# SreeBase Tutorial

SreeBase is a lightweight educational document database written in Python. It is built to help you learn how a small database can combine an append-only storage engine, a custom query language, indexes, a TCP server, a CLI, and a Python SDK.

This documentation is organized like a course. Start with the basics, write your first queries, then move into SDK usage and operational topics.

## What You Will Learn

| Section | Best for | What you learn |
| --- | --- | --- |
| [Get Started](tutorials/index.md) | New users | Installation, first database, core ideas |
| [Query Language](syntax.md) | Query writers | Insert, get, update, delete, indexes, aggregations |
| [Build Apps](api.md) | Python developers | Use `reddybase` from your application |
| [Operations](tutorials/security.md) | Admins and maintainers | Users, roles, storage, troubleshooting |
| [Cheat Sheet](tutorials/cheat-sheet.md) | Everyone | Quick command reference |

## Why SreeBase Is Different

- It uses indentation instead of JSON-like braces for queries.
- Each collection is stored in its own `.sree` append-only file.
- Documents are Python/JSON-style key-value objects.
- Secondary indexes are stored in memory and rebuilt from metadata.
- The TCP server supports basic authentication and admin/read roles.

!!! note "Learning project, not MongoDB"
    SreeBase is not a MongoDB replacement. It does not include replication, sharding, TLS, transactions, or a mature query planner. It is a compact project for learning database internals and building small local experiments.

## A First Query

```sql
insert into employees
    name = "Anika"
    department = "Engineering"
    salary = 90000
```

```sql
get employees
    department = "Engineering"
    sort by salary desc
    limit 5
```

## Recommended Learning Path

1. [Install and run SreeBase](tutorials/installation.md)
2. [Create your first database records](tutorials/first-database.md)
3. [Learn the query syntax](syntax.md)
4. [Use the Python SDK](api.md)
5. [Review admin and security basics](tutorials/security.md)

