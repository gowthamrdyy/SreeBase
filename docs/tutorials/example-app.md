# Example App With Python

This example uses the SDK to create a small learning tracker.

## Start SreeBase

```bash
sreebase serve
```

## Python Script

```python
from reddybase.client.driver import Client, ReddyBaseError

def main():
    with Client(host="127.0.0.1", port=6969) as client:
        client.login("admin", "supersecret")

        courses = client.collection("courses")

        courses.insert({
            "title": "SreeBase Basics",
            "level": "beginner",
            "lessons": 12,
            "published": True,
        })

        courses.insert({
            "title": "Storage Engines",
            "level": "intermediate",
            "lessons": 8,
            "published": True,
        })

        beginner_courses = courses.get(
            where={"level": "beginner", "lessons": (">=", 5)},
            sort=("lessons", "desc"),
        )

        print(beginner_courses)

if __name__ == "__main__":
    try:
        main()
    except ReddyBaseError as exc:
        print(f"SreeBase error: {exc}")
```

## What This Shows

- Connect to a running server.
- Authenticate.
- Select a collection.
- Insert documents.
- Query with safe tuple comparisons.
- Sort results.

## Next Ideas

- Add a FastAPI route that reads courses.
- Store user progress.
- Add an index on `level`.

