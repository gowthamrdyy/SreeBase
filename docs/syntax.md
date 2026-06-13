# Bracketless Query Syntax

SreeBase abandons braces, commas, and parentheses. Queries rely on **indentation** and clear English keywords.

## Inserting Data

```sql
insert into users
    name = "Alice"
    role = "developer"
    age = 28
```

## Querying Data

```sql
get users
    age >= 25
    role = "developer"
    sort by age desc
    limit 10
```

## Updating Data

```sql
update users
    where
        role = "developer"
    set
        salary = 150000
```

## Aggregation & Analytics

```sql
aggregate users
    where
        age >= 20
    group by role
    calculate avg(salary), count()
```
