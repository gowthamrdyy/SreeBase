# Future Roadmap & Advanced Features

SreeBase is continuously evolving. Our ultimate goal is to provide a bracketless, document-oriented database that still supports the powerful relational guarantees found in advanced databases like **PostgreSQL**.

Here is a look at the advanced features we plan to implement in the future:

## 1. Relational Joins
Currently, SreeBase is a pure document store where collections are isolated. We plan to introduce SQL-style `JOIN` syntax adapted for our bracketless language.

**Planned Syntax Example:**
```sql
get orders
    join users on orders.user_id = users._id
    status = "shipped"
```
This will allow fetching embedded documents across collections without doing application-side joins.

## 2. ACID Transactions
A core feature of advanced SQL databases is the ability to guarantee atomic transactions. We plan to implement `BEGIN`, `COMMIT`, and `ROLLBACK` commands.

**Planned Syntax Example:**
```sql
begin transaction
insert into accounts
    balance = -100
insert into accounts
    balance = +100
commit
```

## 3. Advanced Aggregations (GROUP BY & HAVING)
While SreeBase currently supports basic aggregations (sum, count, avg), we will expand this to support grouping by multiple fields and filtering post-aggregation using a `having` clause.

**Planned Syntax Example:**
```sql
aggregate employees
    group by department
    select count() as num_employees
    having num_employees > 10
```

## 4. Foreign Keys and Constraints
To ensure data integrity, we plan to allow schema validation and referential integrity directly at the storage engine level.
- `UNIQUE` constraints (enforced by secondary indexes).
- `FOREIGN KEY` constraints (preventing deletion of parent records).

## 5. Security Enhancements
- **TLS/SSL Encryption**: Wrapping the current raw TCP socket protocol in TLS to encrypt data over the wire.
- **Granular RBAC**: Expanding roles beyond just `admin` and `read` to include collection-specific permissions (e.g., `write:users`).
