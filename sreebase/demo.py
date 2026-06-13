"""
SreeBase Demo — End-to-end showcase of the bracketless query engine.
====================================================================

Run:  python -m sreebase.demo
"""

import os
import shutil

from sreebase.query.executor import Executor


DEMO_DIR = "data/_demo"


def banner(text: str) -> None:
    print(f"\n{'═' * 60}")
    print(f"  {text}")
    print(f"{'═' * 60}")


def section(text: str) -> None:
    print(f"\n── {text} {'─' * (55 - len(text))}")


def pprint_docs(docs) -> None:
    if not docs:
        print("  (no results)")
        return
    for doc in docs:
        print(f"  {doc}")


def main() -> None:
    # Clean slate for the demo.
    if os.path.exists(DEMO_DIR):
        shutil.rmtree(DEMO_DIR)

    banner("SreeBase Engine Demo — Bracketless Query Language")

    with Executor(data_dir=DEMO_DIR) as db:

        # ============================================================== #
        # INSERT
        # ============================================================== #
        section("INSERT — Adding documents")

        r1 = db.execute(
            'insert into users\n'
            '    name = "Gowtham"\n'
            '    role = "architect"\n'
            '    age = 28\n'
            '    city = "Chennai"\n'
        )
        print(f"  Inserted: {r1['_id']}")

        r2 = db.execute(
            'insert into users\n'
            '    name = "Sree"\n'
            '    role = "engineer"\n'
            '    age = 22\n'
            '    city = "Bangalore"\n'
        )
        print(f"  Inserted: {r2['_id']}")

        r3 = db.execute(
            'insert into users\n'
            '    name = "Kiran"\n'
            '    role = "designer"\n'
            '    age = 30\n'
            '    city = "Chennai"\n'
        )
        print(f"  Inserted: {r3['_id']}")

        r4 = db.execute(
            'insert into users\n'
            '    name = "Arun"\n'
            '    role = "intern"\n'
            '    age = 19\n'
            '    city = "Delhi"\n'
        )
        print(f"  Inserted: {r4['_id']}")

        # ============================================================== #
        # GET — All
        # ============================================================== #
        section("GET — All users")
        pprint_docs(db.execute("get users\n"))

        # ============================================================== #
        # GET — Filtered
        # ============================================================== #
        section("GET — Users older than 25")
        pprint_docs(db.execute("get users\n    age > 25\n"))

        section("GET — Users in Chennai")
        pprint_docs(db.execute('get users\n    city = "Chennai"\n'))

        section("GET — Users in Chennai AND age > 25")
        pprint_docs(db.execute(
            'get users\n    age > 25\n    city = "Chennai"\n'
        ))

        # ============================================================== #
        # GET — Sorted + Limited
        # ============================================================== #
        section("GET — All users sorted by name (ascending)")
        pprint_docs(db.execute(
            "get users\n    sort by name asc\n"
        ))

        section("GET — Top 2 oldest users")
        pprint_docs(db.execute(
            "get users\n    sort by age desc\n    limit 2\n"
        ))

        # ============================================================== #
        # UPDATE
        # ============================================================== #
        section("UPDATE — Promote Sree to 'senior engineer'")
        update_result = db.execute(
            'update users\n'
            '    where\n'
            f'        _id = "{r2["_id"]}"\n'
            '    set\n'
            '        role = "senior engineer"\n'
        )
        print(f"  Result: {update_result}")

        section("GET — Verify Sree's update")
        pprint_docs(db.execute(
            f'get users\n    _id = "{r2["_id"]}"\n'
        ))

        # ============================================================== #
        # DELETE
        # ============================================================== #
        section("DELETE — Remove users under 20")
        del_result = db.execute("delete from users\n    age < 20\n")
        print(f"  Result: {del_result}")

        section("GET — Remaining users after delete")
        pprint_docs(db.execute("get users\n"))

        # ============================================================== #
        # Collection isolation
        # ============================================================== #
        section("INSERT — Adding to a different collection (logs)")
        db.execute(
            'insert into logs\n'
            '    level = "INFO"\n'
            '    message = "System started"\n'
        )
        db.execute(
            'insert into logs\n'
            '    level = "ERROR"\n'
            '    message = "Disk full"\n'
        )

        section("GET — Logs collection (separate from users)")
        pprint_docs(db.execute("get logs\n"))

        section("GET — Users still intact")
        pprint_docs(db.execute("get users\n"))

    banner("Demo complete! Data files are in: " + DEMO_DIR)


if __name__ == "__main__":
    main()
