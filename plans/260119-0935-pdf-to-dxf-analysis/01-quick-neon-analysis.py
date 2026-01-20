#!/usr/bin/env python3
"""Quick Neon Database Analysis - Focused on key tables"""
import json, sys
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

def load_config():
    config_file = Path(__file__).parent / "config.txt"
    config = {}
    with open(config_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
    return config

def main():
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True

    results = {
        "timestamp": datetime.now().isoformat(),
        "key_tables": [],
        "cloudfiles_info": {},
        "synced_files_info": {},
        "statistics": {}
    }

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Count CloudFiles
        cur.execute('SELECT COUNT(*) as count FROM "CloudFiles"')
        cloudfiles_count = cur.fetchone()["count"]
        print(f"CloudFiles: {cloudfiles_count} rows")

        # Get CloudFiles columns
        cur.execute("""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_name = 'CloudFiles' ORDER BY ordinal_position
        """)
        cloudfiles_cols = [dict(c) for c in cur.fetchall()]

        # Sample CloudFiles
        cur.execute('SELECT * FROM "CloudFiles" LIMIT 5')
        cloudfiles_sample = [dict(r) for r in cur.fetchall()]

        results["cloudfiles_info"] = {
            "row_count": cloudfiles_count,
            "columns": cloudfiles_cols,
            "sample": [{k: str(v)[:200] if v else None for k,v in row.items()} for row in cloudfiles_sample]
        }

        # Count _synced_files
        cur.execute('SELECT COUNT(*) as count FROM "_synced_files"')
        synced_count = cur.fetchone()["count"]
        print(f"_synced_files: {synced_count} rows")

        # Get _synced_files columns
        cur.execute("""
            SELECT column_name, data_type, udt_name FROM information_schema.columns
            WHERE table_name = '_synced_files' ORDER BY ordinal_position
        """)
        synced_cols = [dict(c) for c in cur.fetchall()]

        # Sample _synced_files
        cur.execute('SELECT * FROM "_synced_files" LIMIT 3')
        synced_sample = [dict(r) for r in cur.fetchall()]

        results["synced_files_info"] = {
            "row_count": synced_count,
            "columns": synced_cols,
            "sample": [{k: str(v)[:200] if v else None for k,v in row.items()} for row in synced_sample]
        }

        # Count PDF references
        cur.execute("""
            SELECT COUNT(*) as count FROM "CloudFiles"
            WHERE "LocalPath" ILIKE '%.pdf' OR "CloudKey" ILIKE '%.pdf' OR "FileType" ILIKE '%pdf%'
        """)
        result = cur.fetchone()
        pdf_count = result["count"] if result else 0
        print(f"PDF files in CloudFiles: {pdf_count}")

        results["statistics"] = {
            "cloudfiles_total": cloudfiles_count,
            "synced_files_total": synced_count,
            "pdf_count_estimate": pdf_count
        }

    conn.close()

    output_file = OUTPUT_DIR / "neon-analysis.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    main()
