#!/usr/bin/env python3
"""
Seed script to generate large datasets for performance testing.

Generates test records with realistic data based on table schema.
Supports efficient batch insertion for 100K+ records.
"""

import argparse
import asyncio
import json
import random
import string
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import asyncpg
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert


# Field type generators
def generate_text_data() -> str:
    """Generate random text data."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(5, 50)))


def generate_long_text_data() -> str:
    """Generate random long text data."""
    words = ['lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipiscing', 'elit']
    return ' '.join(random.choices(words, k=random.randint(10, 100)))


def generate_number_data() -> float:
    """Generate random number data."""
    return round(random.uniform(0, 10000), 2)


def generate_checkbox_data() -> bool:
    """Generate random checkbox data."""
    return random.choice([True, False])


def generate_date_data() -> str:
    """Generate random date data."""
    start_date = datetime(2020, 1, 1)
    random_days = random.randint(0, 1825)  # ~5 years
    random_date = start_date + timedelta(days=random_days)
    return random_date.strftime("%Y-%m-%d")


def generate_datetime_data() -> str:
    """Generate random datetime data."""
    start_date = datetime(2020, 1, 1)
    random_days = random.randint(0, 1825)
    random_seconds = random.randint(0, 86400)
    random_dt = start_date + timedelta(days=random_days, seconds=random_seconds)
    return random_dt.isoformat()


def generate_email_data() -> str:
    """Generate random email data."""
    domains = ['example.com', 'test.com', 'demo.org', 'sample.net']
    username = ''.join(random.choices(string.ascii_lowercase, k=random.randint(5, 15)))
    return f"{username}@{random.choice(domains)}"


def generate_phone_data() -> str:
    """Generate random phone data."""
    return f"+1-{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}"


def generate_url_data() -> str:
    """Generate random URL data."""
    domains = ['example.com', 'test.com', 'demo.org']
    paths = ['page', 'item', 'product', 'article', 'post']
    return f"https://{random.choice(domains)}/{random.choice(paths)}/{random.randint(1, 1000)}"


def generate_single_select_data(options_str: str) -> str:
    """Generate random single select data."""
    try:
        options = json.loads(options_str)
        choices = options.get('choices', [])
        if choices:
            return random.choice(choices)
    except (json.JSONDecodeError, TypeError):
        pass
    return 'Option A'


def generate_multi_select_data(options_str: str) -> str:
    """Generate random multi select data."""
    try:
        options = json.loads(options_str)
        choices = options.get('choices', [])
        if choices:
            return json.dumps(random.choices(choices, k=random.randint(1, min(3, len(choices)))))
    except (json.JSONDecodeError, TypeError):
        pass
    return json.dumps(['Option A'])


# Field type to generator mapping
FIELD_GENERATORS = {
    'text': generate_text_data,
    'long_text': generate_long_text_data,
    'number': generate_number_data,
    'checkbox': generate_checkbox_data,
    'date': generate_date_data,
    'datetime': generate_datetime_data,
    'email': generate_email_data,
    'phone': generate_phone_data,
    'url': generate_url_data,
    'single_select': lambda: 'Option A',  # Will be replaced with field-specific options
    'multi_select': lambda: '["Option A"]',  # Will be replaced with field-specific options
}


async def get_table_fields(table_id: str, db_conn: asyncpg.Connection) -> list[dict[str, Any]]:
    """
    Get fields for a table.

    Args:
        table_id: Table UUID
        db_conn: Database connection

    Returns:
        List of field dictionaries
    """
    query = """
        SELECT id, name, field_type, options
        FROM fields
        WHERE table_id = $1 AND deleted_at IS NULL
        ORDER BY position
    """
    rows = await db_conn.fetch(query, table_id)
    return [dict(row) for row in rows]


async def get_table_owner_user_id(table_id: str, db_conn: asyncpg.Connection) -> str | None:
    """
    Get the owner user_id for a table.

    Args:
        table_id: Table UUID
        db_conn: Database connection

    Returns:
        User UUID or None
    """
    query = """
        SELECT u.id
        FROM users u
        JOIN workspaces w ON w.owner_id = u.id
        JOIN bases b ON b.workspace_id = w.id
        JOIN tables t ON t.base_id = b.id
        WHERE t.id = $1 AND u.deleted_at IS NULL
        LIMIT 1
    """
    row = await db_conn.fetchrow(query, table_id)
    return str(row['id']) if row else None


def generate_record_data(fields: list[dict[str, Any]], record_index: int) -> dict[str, Any]:
    """
    Generate realistic data for a record based on field schema.

    Args:
        fields: List of field definitions
        record_index: Record index for unique values

    Returns:
        Dictionary mapping field_id to generated value
    """
    record_data = {}

    for field in fields:
        field_id = str(field['id'])
        field_type = field['field_type']
        options = field.get('options', '{}')

        # Skip computed and system fields
        if field_type in ['formula', 'autonumber', 'created_by', 'last_modified_by',
                          'created_time', 'last_modified_time', 'lookup', 'rollup']:
            continue

        # Generate value based on field type
        if field_type == 'single_select':
            value = generate_single_select_data(options)
        elif field_type == 'multi_select':
            value = generate_multi_select_data(options)
        elif field_type in FIELD_GENERATORS:
            generator = FIELD_GENERATORS[field_type]
            # Add some variation based on record index
            random.seed(record_index + hash(field_id))
            value = generator()
        else:
            # Default to text for unknown types
            value = generate_text_data()

        record_data[field_id] = value

    return record_data


async def seed_records(
    table_id: str,
    count: int,
    batch_size: int = 1000,
    db_url: str | None = None,
) -> dict[str, Any]:
    """
    Seed records into a table.

    Args:
        table_id: Table UUID
        count: Number of records to create
        batch_size: Batch size for inserts
        db_url: Database connection URL (optional, uses default if not provided)

    Returns:
        Dictionary with seeding results
    """
    if db_url is None:
        from pybase.core.config import settings
        db_url = settings.database_url.replace('+asyncpg', '').replace('postgresql://', 'postgresql+asyncpg://')

    # Convert to asyncpg URL format
    if '+asyncpg' not in db_url:
        db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')

    start_time = time.perf_counter()
    records_created = 0
    errors = []

    conn = await asyncpg.connect(db_url)

    try:
        async with conn.transaction():
            # Get table fields
            fields = await get_table_fields(table_id, conn)
            if not fields:
                raise ValueError(f"No fields found for table {table_id}")

            # Get owner user_id
            user_id = await get_table_owner_user_id(table_id, conn)

            # Generate and insert records in batches
            for batch_start in range(0, count, batch_size):
                batch_end = min(batch_start + batch_size, count)
                batch_records = []

                for i in range(batch_start, batch_end):
                    record_data = generate_record_data(fields, i)
                    record_uuid = str(uuid4())

                    batch_records.append((
                        record_uuid,
                        table_id,
                        json.dumps(record_data),
                        user_id,
                        user_id,
                    ))

                # Batch insert using PostgreSQL INSERT
                insert_query = """
                    INSERT INTO records (id, table_id, data, created_by_id, last_modified_by_id, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                """

                await conn.executemany(insert_query, batch_records)
                records_created += len(batch_records)

                # Progress reporting
                progress = (records_created / count) * 100
                elapsed = time.perf_counter() - start_time
                rate = records_created / elapsed if elapsed > 0 else 0
                eta = (count - records_created) / rate if rate > 0 else 0

                sys.stdout.write(
                    f"\rProgress: {records_created}/{count} ({progress:.1f}%) | "
                    f"Rate: {rate:.0f} records/sec | "
                    f"ETA: {eta:.0f}s"
                )
                sys.stdout.flush()

    except Exception as e:
        errors.append(str(e))
        raise
    finally:
        await conn.close()

    elapsed = time.perf_counter() - start_time
    rate = count / elapsed if elapsed > 0 else 0

    return {
        'table_id': table_id,
        'records_created': records_created,
        'target_count': count,
        'elapsed_time': elapsed,
        'rate': rate,
        'errors': errors,
    }


def format_results(results: dict[str, Any]) -> None:
    """Format and print seeding results."""
    print("\n" + "=" * 70)
    print("SEEDING RESULTS")
    print("=" * 70)
    print(f"Table ID:       {results['table_id']}")
    print(f"Records:        {results['records_created']:,} / {results['target_count']:,}")
    print(f"Elapsed Time:   {results['elapsed_time']:.2f}s")
    print(f"Rate:           {results['rate']:.0f} records/sec")

    if results['errors']:
        print(f"\nErrors: {len(results['errors'])}")
        for error in results['errors']:
            print(f"  - {error}")

    print("=" * 70)

    if results['records_created'] == results['target_count']:
        print(f"✓ Successfully seeded {results['records_created']:,} records")
    else:
        print(f"✗ Seeded {results['records_created']:,} of {results['target_count']:,} records")


async def main_async():
    """Main async entry point."""
    parser = argparse.ArgumentParser(
        description="Seed large datasets for performance testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Seed 100K records into a table
  python scripts/seed_large_dataset.py --table <table_id> --count 100000

  # Seed with custom batch size for better performance
  python scripts/seed_large_dataset.py --table <table_id> --count 50000 --batch-size 5000

  # Seed with custom database URL
  python scripts/seed_large_dataset.py --table <table_id> --count 10000 --db-url postgresql://user:pass@localhost/db
        """
    )

    parser.add_argument(
        '--table',
        type=str,
        required=True,
        help='Table UUID to seed records into'
    )

    parser.add_argument(
        '--count',
        type=int,
        default=100000,
        help='Number of records to create (default: 100000)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for inserts (default: 1000)'
    )

    parser.add_argument(
        '--db-url',
        type=str,
        help='Database connection URL (optional, uses default from config if not provided)'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.count < 1:
        print("Error: Count must be at least 1")
        return 1

    if args.batch_size < 1:
        print("Error: Batch size must be at least 1")
        return 1

    if args.batch_size > args.count:
        print("Warning: Batch size is larger than count, adjusting to count")
        args.batch_size = args.count

    # Validate table_id format
    try:
        UUID(args.table)
    except ValueError:
        print(f"Error: Invalid table ID format: {args.table}")
        print("Table ID must be a valid UUID")
        return 1

    print("\n" + "=" * 70)
    print("LARGE DATASET SEEDING TOOL")
    print("=" * 70)
    print(f"Table ID:      {args.table}")
    print(f"Record Count:  {args.count:,}")
    print(f"Batch Size:    {args.batch_size}")
    print("=" * 70)
    print("\nStarting seeding...")

    try:
        results = await seed_records(
            table_id=args.table,
            count=args.count,
            batch_size=args.batch_size,
            db_url=args.db_url,
        )
        format_results(results)

        if results['records_created'] == results['target_count'] and not results['errors']:
            return 0
        else:
            return 1

    except KeyboardInterrupt:
        print("\n\nSeeding interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point."""
    try:
        # Run async main
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n\nSeeding interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
