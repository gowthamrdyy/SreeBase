# Read Data

Use `get` to read documents from a collection.

## Read Everything

```sql
get users
```

## Equality Filter

```sql
get users
    role = "developer"
```

## Comparison Filters

```sql
get users
    age >= 18
```

Available operators:

| Operator | Meaning |
| --- | --- |
| `=` | equal |
| `!=` | not equal |
| `>` | greater than |
| `>=` | greater than or equal |
| `<` | less than |
| `<=` | less than or equal |

## Multiple Conditions

Conditions are combined with AND logic.

```sql
get users
    role = "developer"
    active = true
    age >= 21
```

## Sort

```sql
get users
    sort by age asc
```

```sql
get users
    sort by age desc
```

## Limit

```sql
get users
    sort by age desc
    limit 5
```

## Practice

Find the top 3 active developers by salary:

```sql
get employees
    role = "developer"
    active = true
    sort by salary desc
    limit 3
```

