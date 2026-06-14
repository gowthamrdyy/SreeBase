# Python SDK: `reddybase`

The `reddybase` package is the Python client for talking to a running SreeBase TCP server.

## Connect

```python
from reddybase.client.driver import Client

client = Client(host="127.0.0.1", port=6969)
client.login("admin", "supersecret")
```

Use a context manager when possible:

```python
from reddybase.client.driver import Client

with Client() as client:
    client.login("admin", "supersecret")
    users = client.collection("users")
    print(users.get())
```

## Collections

```python
users = client.collection("users")
```

Collection names must be simple identifiers such as `users`, `server_logs`, or `app.events`.

## Insert

```python
users.insert({
    "name": "Maya",
    "role": "developer",
    "salary": 120000,
    "active": True,
})
```

Supported SDK literal values:

- `str`
- `int`
- finite `float`
- `bool`
- `None`

Other Python objects are rejected so they cannot accidentally become unsafe query text.

## Get

Equality filters use normal values:

```python
developers = users.get(where={"role": "developer"})
```

Comparisons use tuple conditions:

```python
senior_developers = users.get(
    where={
        "role": "developer",
        "salary": (">=", 100000),
    },
    sort=("salary", "desc"),
    limit=10,
)
```

!!! tip "Use tuple comparisons"
    Do not write operators inside strings. Use `(">", 10)`, `(">=", 10)`, `("!=", "guest")`, and similar tuples.

## Update

```python
users.update(
    where={"role": "developer"},
    set_fields={"active": True}
)
```

## Delete

```python
users.delete(where={"active": False})
```

!!! warning
    Calling `users.delete()` without a filter deletes every document in the collection.

## Aggregate

```python
stats = users.aggregate(
    group_by="role",
    calculate=["avg(salary)", "count()"],
    where={"active": True}
)
```

## Raw Queries

For advanced usage, you can send query text directly:

```python
result = client.raw_query("""
get users
    role = "developer"
""")
```

Use the collection methods when taking input from users. They validate identifiers and escape string values.

## Error Handling

```python
from reddybase.client.driver import Client, ReddyBaseError

try:
    with Client() as client:
        client.login("admin", "wrong-password")
except ReddyBaseError as exc:
    print(f"SreeBase error: {exc}")
```

