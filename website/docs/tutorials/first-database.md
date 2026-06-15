# Your First Database

In this lesson you will create a collection, insert documents, and query them back.

## 1. Start the Server

```bash
sreebase serve
```

## 2. Open the Shell

```bash
sreebase shell -u admin
```

## 3. Insert Documents

```sql
insert into books
    title = "Database Systems"
    author = "Navya"
    pages = 420
    available = true
```

```sql
insert into books
    title = "Python Backends"
    author = "Arjun"
    pages = 260
    available = true
```

## 4. Read All Books

```sql
get books
```

## 5. Filter Books

```sql
get books
    pages > 300
```

## 6. Sort and Limit

```sql
get books
    available = true
    sort by pages desc
    limit 1
```

## What Happened

- `books` became a collection.
- Each insert created one document.
- SreeBase stored those documents in `books.sree`.
- `get books` scanned the live documents and returned matches.

