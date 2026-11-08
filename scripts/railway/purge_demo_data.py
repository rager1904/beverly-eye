#!/usr/bin/env python3
"""Remove the demo patients and users that earlier migrations seeded.

The script is idempotent. It is intentionally opt-in: the backend startup
sequence only runs it when ``UBUNTUCARE_PURGE_DEMO_DATA=1`` is set, so pushing
the repository does not delete data by itself.

Usage (inside the backend container or with DATABASE_URL exported):

    python scripts/railway/purge_demo_data.py --dry-run
    python scripts/railway/purge_demo_data.py --yes
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from urllib.parse import urlsplit, urlunsplit

# Patients and users created by migrations 004, 005, and 006.
DEMO_PATIENT_IDS = [f"a1000001-0000-4000-8000-00000000000{i}" for i in range(1, 10)]
DEMO_PATIENT_IDS.append("a1000001-0000-4000-8000-00000000000a")
DEMO_PATIENT_IDS = sorted(set(DEMO_PATIENT_IDS))

DEMO_USERNAMES = [
    "admin",
    "uth_admin",
    "moh_officer",
    "dr_mwamba",
    "nurse_banda",
    "chw_mulenga",
    "pharm_tembo",
    "lab_kasonde",
    "patient",
]


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "")
    if not value:
        raise RuntimeError("DATABASE_URL is not set.")
    parts = urlsplit(value)
    scheme = "postgresql" if parts.scheme in {"postgres", "postgresql", "postgresql+asyncpg"} else parts.scheme
    return urlunsplit((scheme, parts.netloc, parts.path, parts.query, parts.fragment))


async def _table_exists(conn, table: str) -> bool:
    return bool(await conn.fetchval("SELECT to_regclass($1)", f"public.{table}"))


async def _tables_with_column(conn, column: str) -> list[str]:
    rows = await conn.fetch(
        """
        SELECT c.table_name
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON t.table_schema = c.table_schema
         AND t.table_name = c.table_name
         AND t.table_type = 'BASE TABLE'
        WHERE c.table_schema = 'public' AND c.column_name = $1
        ORDER BY c.table_name
        """,
        column,
    )
    return [row["table_name"] for row in rows]


async def _foreign_keys_referencing(
    conn, parent_tables: list[str]
) -> list[tuple[str, str, str, str]]:
    """Return (child, child_col, parent, parent_col) for FKs to the parents."""
    if not parent_tables:
        return []
    rows = await conn.fetch(
        """
        SELECT tc.table_name AS child,
               kcu.column_name AS child_col,
               ccu.table_name AS parent,
               ccu.column_name AS parent_col
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON tc.constraint_name = ccu.constraint_name
         AND tc.table_schema = ccu.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
          AND ccu.table_name = ANY($1::text[])
          AND ccu.column_name = 'id'
        ORDER BY ccu.table_name, tc.table_name, kcu.column_name
        """,
        parent_tables,
    )
    return [
        (row["child"], row["child_col"], row["parent"], row["parent_col"])
        for row in rows
    ]


def _delete_order(
    tables: list[str], references: list[tuple[str, str, str, str]]
) -> list[str]:
    """Order tables so children are deleted before their parents."""
    table_set = set(tables)
    children: dict[str, set[str]] = {table: set() for table in tables}
    for child, _child_col, parent, _parent_col in references:
        if child in table_set and parent in table_set and child != parent:
            children[parent].add(child)

    order: list[str] = []
    visited: set[str] = set()

    def visit(table: str, stack: set[str]) -> None:
        if table in visited or table in stack:
            return
        stack.add(table)
        for child in sorted(children[table]):
            visit(child, stack)
        stack.discard(table)
        visited.add(table)
        order.append(table)

    for table in tables:
        visit(table, set())
    return order


async def _user_reference_columns(conn) -> list[tuple[str, str, str]]:
    rows = await conn.fetch(
        """
        SELECT tc.table_name, kcu.column_name, c.is_nullable
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON tc.constraint_name = ccu.constraint_name
         AND tc.table_schema = ccu.table_schema
        JOIN information_schema.columns c
          ON c.table_schema = tc.table_schema
         AND c.table_name = tc.table_name
         AND c.column_name = kcu.column_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = 'public'
          AND ccu.table_name = 'users'
          AND ccu.column_name = 'id'
        ORDER BY tc.table_name, kcu.column_name
        """
    )
    return [(row["table_name"], row["column_name"], row["is_nullable"]) for row in rows]


async def purge(dry_run: bool) -> None:
    import asyncpg

    conn = await asyncpg.connect(database_url())
    deleted: dict[str, int] = {}
    try:
        async with conn.transaction():
            user_rows = await conn.fetch(
                "SELECT id, username FROM users WHERE username = ANY($1::text[])",
                DEMO_USERNAMES,
            )
            user_ids = [str(row["id"]) for row in user_rows]
            print(f"Demo users found: {len(user_ids)}")
            for row in user_rows:
                print(f"  - {row['username']} ({row['id']})")

            patient_count = await conn.fetchval(
                "SELECT count(*) FROM patients WHERE id::text = ANY($1::text[])",
                DEMO_PATIENT_IDS,
            )
            print(f"Demo patients found: {patient_count}")

            # Delete rows that reference demo patients. This covers clinical
            # records, appointments, and legacy tables that use NO ACTION
            # foreign keys instead of CASCADE. Children are deleted before
            # parents, and child tables without a patient_id column are cleared
            # through a subquery.
            patient_tables = [
                table
                for table in await _tables_with_column(conn, "patient_id")
                if table != "patients"
            ]
            references = await _foreign_keys_referencing(conn, patient_tables)
            patient_table_set = set(patient_tables)

            for child, child_col, parent, parent_col in references:
                if child in patient_table_set or parent not in patient_table_set:
                    continue
                subquery = (
                    f'SELECT "{parent_col}" FROM "{parent}" '
                    "WHERE patient_id::text = ANY($1::text[])"
                )
                count = await conn.fetchval(
                    f'SELECT count(*) FROM "{child}" WHERE "{child_col}" IN ({subquery})',
                    DEMO_PATIENT_IDS,
                )
                if not count:
                    continue
                deleted[f"{child}.{child_col}"] = int(count)
                if not dry_run:
                    await conn.execute(
                        f'DELETE FROM "{child}" WHERE "{child_col}" IN ({subquery})',
                        DEMO_PATIENT_IDS,
                    )

            for table in _delete_order(patient_tables, references):
                count = await conn.fetchval(
                    f'SELECT count(*) FROM "{table}" WHERE patient_id::text = ANY($1::text[])',
                    DEMO_PATIENT_IDS,
                )
                if not count:
                    continue
                deleted[f"{table}.patient_id"] = int(count)
                if not dry_run:
                    await conn.execute(
                        f'DELETE FROM "{table}" WHERE patient_id::text = ANY($1::text[])',
                        DEMO_PATIENT_IDS,
                    )

            if patient_count:
                deleted["patients"] = int(patient_count)
                if not dry_run:
                    await conn.execute(
                        "DELETE FROM patients WHERE id::text = ANY($1::text[])",
                        DEMO_PATIENT_IDS,
                    )

            # Detach or remove any remaining references to the demo users.
            if user_ids:
                for table, column, nullable in await _user_reference_columns(conn):
                    if table == "user_roles":
                        continue
                    if not await _table_exists(conn, table):
                        continue
                    count = await conn.fetchval(
                        f'SELECT count(*) FROM "{table}" WHERE "{column}"::text = ANY($1::text[])',
                        user_ids,
                    )
                    if not count:
                        continue
                    key = f"{table}.{column}"
                    deleted[key] = int(count)
                    if dry_run:
                        continue
                    if nullable == "YES":
                        await conn.execute(
                            f'UPDATE "{table}" SET "{column}" = NULL WHERE "{column}"::text = ANY($1::text[])',
                            user_ids,
                        )
                    else:
                        await conn.execute(
                            f'DELETE FROM "{table}" WHERE "{column}"::text = ANY($1::text[])',
                            user_ids,
                        )

            # Roles and sessions cascade, but delete explicitly so the report
            # is complete and the operation also works on older schemas.
            for table in ("user_roles", "user_sessions"):
                if not await _table_exists(conn, table) or not user_ids:
                    continue
                count = await conn.fetchval(
                    f'SELECT count(*) FROM "{table}" WHERE user_id::text = ANY($1::text[])',
                    user_ids,
                )
                if count:
                    deleted[table] = int(count)
                    if not dry_run:
                        await conn.execute(
                            f'DELETE FROM "{table}" WHERE user_id::text = ANY($1::text[])',
                            user_ids,
                        )

            if user_ids:
                deleted["users"] = len(user_ids)
                if not dry_run:
                    await conn.execute(
                        "DELETE FROM users WHERE id::text = ANY($1::text[])",
                        user_ids,
                    )

            if dry_run:
                raise _DryRun()

        print("\nDemo data removed:" if not dry_run else "\nDry run - nothing was deleted:")
        if not deleted:
            print("  (nothing to remove)")
        for key, value in sorted(deleted.items()):
            print(f"  {key}: {value}")
    except _DryRun:
        print("\nDry run - nothing was deleted:")
        if not deleted:
            print("  (nothing to remove)")
        for key, value in sorted(deleted.items()):
            print(f"  {key}: {value}")
    finally:
        await conn.close()


class _DryRun(Exception):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Confirm permanent deletion.")
    args = parser.parse_args()

    if not args.dry_run and not args.yes:
        enabled = os.getenv("UBUNTUCARE_PURGE_DEMO_DATA", "").strip().lower()
        if enabled not in {"1", "true", "yes", "on"}:
            print(
                "Refusing to delete data. Pass --yes or set UBUNTUCARE_PURGE_DEMO_DATA=1.",
                file=sys.stderr,
            )
            return 2

    asyncio.run(purge(dry_run=args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
