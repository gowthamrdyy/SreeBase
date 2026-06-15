# Insert Data

Use `insert into` to add a document to a collection.

## Basic Insert

```sql
insert into users
    name = "Maya"
    role = "developer"
    age = 28
```

## Supported Values

```sql
insert into examples
    title = "Hello"
    count = 10
    price = 19.99
    active = true
    deleted_at = null
```

## Custom `_id`

If you want to choose the document ID yourself:

```sql
insert into users
    _id = "user-001"
    name = "Maya"
```

If `_id` already exists, SreeBase raises a duplicate-key error.

## Practice

Create a `courses` collection:

```sql
insert into courses
    title = "SreeBase Basics"
    level = "beginner"
    lessons = 12
```

Then read it:

```sql
get courses
```

