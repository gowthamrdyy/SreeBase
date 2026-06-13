# Welcome to SreeBase

**The Bracketless, Enterprise-Grade NoSQL Database**

SreeBase is an incredibly fast, highly scalable database that completely abandons the JSON brackets. Built entirely in Python, it relies on a sophisticated indentation-aware query language.

## Key Features

* **Zero Brackets**: Query your data in plain, English-like syntax.
* **O(1) Secondary Indexes**: Hash-maps in RAM provide instantaneous lookups.
* **Append-Only Log**: Bitcask-inspired storage format ensuring massive write throughput without B-Tree overhead.
* **Aggregations**: Native analytical grouping (`calculate sum()`, `avg()`).
* **Role-Based Access Control**: Enterprise-grade security via native TCP handshakes.

Navigate to **[Query Syntax](syntax.md)** to learn how to write SreeBase queries, or check out the **[Python SDK](api.md)** if you are building an application!
