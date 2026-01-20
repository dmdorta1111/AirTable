#!/usr/bin/env python3
"""
A1-migrate-schema.py
Executes the schema migration SQL to create document intelligence tables.

Usage: python A1-migrate-schema.py
"""

import sys
import logging
from datetime import datetime
from pathlib import Path

import psycopg2

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
PLAN_DIR = SCRIPT_DIR.parent
CONFIG_FILE = PLAN_DIR / "config.txt"
SCHEMA_FILE = PLAN_DIR / "output" / "schema-migration.sql"
OUTPUT_DIR = PLAN_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_config():
    """Load configuration from config.txt file."""
    if not CONFIG_FILE.exists():
        logger.error(f"Config file not found: {CONFIG_FILE}")
        logger.info("Please copy config-template.txt to config.txt and fill in your credentials")
        sys.exit(1)

    config = {}
    with open(CONFIG_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


def main():
    print("=" * 70)
    print("A1: SCHEMA MIGRATION")
    print("=" * 70)

    # Load config
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")

    if not db_url:
        logger.error("NEON_DATABASE_URL not found in config.txt")
        sys.exit(1)

    # Verify schema file exists
    if not SCHEMA_FILE.exists():
        logger.error(f"Schema file not found: {SCHEMA_FILE}")
        sys.exit(1)

    logger.info(f"Reading schema from: {SCHEMA_FILE}")

    # Read SQL
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        sql_content = f.read()

    logger.info(f"Schema file size: {len(sql_content):,} bytes")

    # Connect to database
    logger.info("Connecting to Neon PostgreSQL...")

    try:
        conn = psycopg2.connect(db_url)
        # Don't use autocommit - the SQL has its own BEGIN/COMMIT
        conn.autocommit = False

        logger.info("Connected successfully!")

        with conn.cursor() as cur:
            logger.info("Executing schema migration...")

            # Execute the full SQL script
            cur.execute(sql_content)

            # Commit the transaction
            conn.commit()

            logger.info("Schema migration completed successfully!")

            # Verify tables were created
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN (
                    'document_groups',
                    'document_group_members',
                    'extracted_metadata',
                    'extraction_jobs',
                    'extracted_dimensions',
                    'extracted_parameters',
                    'extracted_materials',
                    'extracted_bom_items'
                )
                ORDER BY table_name
            """)

            tables = [row[0] for row in cur.fetchall()]

            print("\n" + "=" * 70)
            print("CREATED TABLES:")
            print("=" * 70)
            for table in tables:
                print(f"  ✓ {table}")

            # Check enum types
            cur.execute("""
                SELECT typname FROM pg_type 
                WHERE typtype = 'e' 
                AND typname IN (
                    'linking_method', 
                    'document_role', 
                    'extraction_source_type',
                    'extraction_status',
                    'dimension_type',
                    'tolerance_type'
                )
                ORDER BY typname
            """)

            enums = [row[0] for row in cur.fetchall()]

            print("\nCREATED ENUM TYPES:")
            for enum in enums:
                print(f"  ✓ {enum}")

            # Check CloudFiles columns
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'CloudFiles' 
                AND column_name IN ('extraction_status', 'document_group_id')
            """)

            cf_columns = [row[0] for row in cur.fetchall()]

            print("\nCLOUDFILES COLUMNS ADDED:")
            for col in cf_columns:
                print(f"  ✓ {col}")

        conn.close()

        print("\n" + "=" * 70)
        print("✓ MIGRATION SUCCESSFUL")
        print("=" * 70)

        # Write success log
        log_file = OUTPUT_DIR / "A1-migration.log"
        with open(log_file, "w") as f:
            f.write(f"Migration completed at: {datetime.now().isoformat()}\n")
            f.write(f"Tables created: {', '.join(tables)}\n")
            f.write(f"Enums created: {', '.join(enums)}\n")
            f.write(f"CloudFiles columns: {', '.join(cf_columns)}\n")

        logger.info(f"Log saved to: {log_file}")

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
