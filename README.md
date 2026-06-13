<p align="center">
  <h1 align="center">SreeBase</h1>
  <p align="center"><strong>A Lightweight, Educational Bracketless NoSQL Database</strong></p>
  <p align="center">
    <a href="https://github.com/gowthamrdyy/sreebase/actions"><img src="https://img.shields.io/badge/tests-78%20passing-success" alt="Tests"></a>
    <a href="https://github.com/gowthamrdyy/sreebase/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
    <a href="https://github.com/gowthamrdyy/sreebase/releases"><img src="https://img.shields.io/github/v/release/gowthamrdyy/sreebase" alt="Release"></a>
    <a href="https://python.org"><img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python Version"></a>
  </p>
</p>

SreeBase is an educational, lightweight NoSQL document database built entirely in Python. It features a custom English-like bracketless query language, O(1) secondary indexing, and a simple append-only storage engine.

---

## 🚀 Why SreeBase?

SreeBase was built to explore database internals and query language parsing using advanced data structures:

- **Bitcask-style Append-Only Log:** Data is written sequentially (`.sree` files) for near-instantaneous disk I/O, avoiding the massive write-amplification overhead of B-Trees.
- **Group Commit & Background Compaction:** Highly concurrent write paths with batched `fsync` grouping. A background-safe compaction engine hot-swaps active logs without pausing reads.
- **Custom AST & Parser:** A bespoke lexer and recursive-descent parser. No JSON brackets required. Write queries like plain English.
- **O(1) Secondary Indexes:** Hash-map based secondary indexing directly in RAM that stays perfectly in sync with mutations.
- **Aggregation Pipeline:** Powerful `aggregate` syntax supporting filtering (`where`), grouping (`group by`), and statistical math (`sum()`, `avg()`, `count()`).
- **RBAC Security:** Role-Based Access Control to separate admin and read-only users.

## ⚡ Quick Start (Docker)
## ⚡ Quick Start

SreeBase is packaged natively. You can install it globally on your machine using `pip`.

```bash
# Install globally
pip install sreebase

# Start the SreeBase TCP server in the background
sreebase serve &
```

Your database is now running on `127.0.0.1:6969`. All data is persistently saved to the `./data` folder in your current directory.

---

## 💻 The Professional CLI

SreeBase comes with an interactive, professional REPL client boasting command history, arrow-key support, and ASCII-rendered tabular results.

### 1. The Bootstrap Setup (First Time Only)
SreeBase is highly secure by default. When you spin up a completely fresh database, you must connect anonymously to create your initial admin account.

```bash
# Connect to the shell anonymously
sreebase shell
```

Then, create your root user:
```sql
sreebase> create user admin password "supersecret" role admin
```
Type `exit` to leave. Your database is now permanently locked down and secured!

### 2. Standard Login
From now on, you must use your `-u` argument to connect securely. SreeBase will automatically hide your keystrokes and prompt for your password:

```bash
# Connect securely
sreebase shell -u admin
```

### Bracketless Querying

Forget trailing commas, curly braces, and nested parentheses. Just type your logic. 
Submit a **blank line** to execute a multi-line query.

```sql
sreebase> insert into employees
      ...     name = "Gowtham"
      ...     department = "Engineering"
      ...     salary = 125000
      ... 

{
  "_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "inserted": {
    "name": "Gowtham",
    "department": "Engineering",
    "salary": 125000
  }
}
```

```sql
sreebase> aggregate employees
      ...     where
      ...         salary >= 50000
      ...     group by department
      ...     calculate avg(salary), count()
      ... 

+-------------+---------------+-----------+
| department  | avg(salary)   | count()   |
+-------------+---------------+-----------+
| Engineering | 125000.0      | 1         |
+-------------+---------------+-----------+
1 rows in set
```

---

## 🐍 Official Python SDK (`reddybase`)

Building an application? Use the official `reddybase` Python driver for a beautiful, Pythonic ORM that transparently compiles your code into the underlying SreeBase syntax over TCP.

```python
from reddybase.client.driver import Client

# 1. Connect and Authenticate
client = Client(host="127.0.0.1", port=6969)
client.login("admin", "supersecret")

# 2. Get a Collection reference
logs = client.collection("server_logs")

# 3. Insert Data
logs.insert({"server_id": "srv-alpha", "cpu": 95.5, "status": "critical"})

# 4. Query Data (SDK parses operators dynamically!)
critical_logs = logs.get(where={"status": '= "critical"', "cpu": "> 90"})

# 5. Aggregations
analytics = logs.aggregate(group_by="server_id", calculate=["avg(cpu)"])
```

---
**SreeBase — Engineered with precision.**
