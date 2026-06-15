# Troubleshooting

## Server Will Not Start

Check whether port `6969` is already in use.

Try another port:

```bash
sreebase serve --port 6970
```

Then connect:

```bash
sreebase shell -p 6970
```

## Authentication Required

After the first user exists, anonymous queries are rejected.

Use:

```bash
sreebase shell -u admin
```

## Invalid Username Or Password

Check:

- the username spelling
- the password
- whether the server is using the expected `--data-dir`

## Query Fails With Parser Error

Common causes:

- missing newline
- wrong indentation
- missing quotes around strings
- using unsupported values such as lists or objects

## Delete Removed Too Much Data

`delete from collection` deletes all documents in a collection.

Prefer filtered deletes:

```sql
delete from users
    _id = "user-001"
```

## SDK Comparison Does Not Work

Use tuple comparisons:

```python
users.get(where={"age": (">=", 18)})
```

Do not place operators inside strings.

