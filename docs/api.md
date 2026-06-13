# Python SDK (`reddybase`)

The official SreeBase Python SDK is the recommended way to connect your web apps (FastAPI, Django) to the SreeBase engine.

## Installation

Ensure SreeBase is running on port 6969, and simply import the driver:

```python
from reddybase.client.driver import Client

client = Client(host="127.0.0.1", port=6969)
client.login("admin", "supersecret")
```

## ORM Usage

The `Collection` object wraps raw queries into standard Python method calls. 

### Inserting
```python
users = client.collection("users")
users.insert({
    "name": "Bob",
    "role": "manager",
    "salary": 180000
})
```

### Querying
You can pass strict operators in the string value.
```python
managers = users.get(where={"role": "manager", "salary": "> 100000"})
```

### Aggregations
```python
stats = users.aggregate(
    group_by="role",
    calculate=["avg(salary)", "count()"]
)
```
