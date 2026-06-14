# Aggregations

Aggregations group documents and calculate summary values.

## Count By Group

```sql
aggregate users
    group by role
    calculate count()
```

## Average Salary By Role

```sql
aggregate employees
    where
        active = true
    group by role
    calculate avg(salary), count()
```

## Supported Functions

| Function | Example | Meaning |
| --- | --- | --- |
| `count()` | `count()` | number of documents in the group |
| `sum(field)` | `sum(salary)` | sum numeric values |
| `avg(field)` | `avg(salary)` | average numeric values |

## Missing Or Non-Numeric Values

For `sum()` and `avg()`, non-numeric values are ignored. If no numeric values exist for `avg()`, the result is `0`.

## Practice

Group logs by status:

```sql
aggregate logs
    group by status
    calculate count()
```

