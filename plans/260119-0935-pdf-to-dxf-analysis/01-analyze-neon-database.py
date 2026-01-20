#!/usr/bin/env python3
"""
Neon Database Analysis Script
Analyzes the database structure to find PDF-related tables and embeddings.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("ERROR: psycopg2-binary not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# Output directory
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

def load_config():
    """Load configuration from config.txt file."""
    config_file = Path(__file__).parent / "config.txt"
    if not config_file.exists():
        print(f"ERROR: Config file not found at {config_file}")
        print("Please copy config-template.txt to config.txt and fill in your credentials")
        sys.exit(1)
    
    config = {}
    with open(config_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
    return config

def analyze_database(conn):
    """Analyze database structure and find PDF-related tables."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "tables": [],
        "pdf_related_tables": [],
        "embedding_tables": [],
        "sample_data": {},
        "statistics": {}
    }
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Get all tables
        cur.execute("""
            SELECT table_name, table_schema
            FROM information_schema.tables 
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name
        """)
        tables = cur.fetchall()
        results["tables"] = [dict(t) for t in tables]
        print(f"Found {len(tables)} tables")
        
        # Analyze each table
        for table in tables:
            table_name = table["table_name"]
            schema = table["table_schema"]
            full_name = f"{schema}.{table_name}" if schema != "public" else table_name
            
            # Get column info
            cur.execute("""
                SELECT column_name, data_type, is_nullable, 
                       character_maximum_length, udt_name
                FROM information_schema.columns 
                WHERE table_name = %s AND table_schema = %s
                ORDER BY ordinal_position
            """, (table_name, schema))
            columns = [dict(c) for c in cur.fetchall()]
            
            # Check for PDF-related columns
            pdf_keywords = ['pdf', 'file', 'path', 'url', 'document', 'attachment', 'blob', 'storage']
            is_pdf_related = any(
                any(kw in col["column_name"].lower() for kw in pdf_keywords)
                for col in columns
            )
            
            # Check for embedding columns (vector type or large arrays)
            embedding_keywords = ['embedding', 'vector', 'embed']
            has_embeddings = any(
                col["udt_name"] == "vector" or 
                any(kw in col["column_name"].lower() for kw in embedding_keywords)
                for col in columns
            )
            
            table_info = {
                "name": full_name,
                "columns": columns,
                "is_pdf_related": is_pdf_related,
                "has_embeddings": has_embeddings
            }
            
            # Get row count
            try:
                cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table_name}"')
                table_info["row_count"] = cur.fetchone()["count"]
            except Exception as e:
                conn.rollback(); table_info["row_count"] = f"Error: {e}"
            
            if is_pdf_related:
                results["pdf_related_tables"].append(table_info)
                print(f"  📄 PDF-related table: {full_name} ({table_info['row_count']} rows)")
                
                # Get sample data
                try:
                    cur.execute(f'SELECT * FROM "{schema}"."{table_name}" LIMIT 5')
                    samples = cur.fetchall()
                    # Convert to serializable format
                    results["sample_data"][full_name] = [
                        {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v 
                         for k, v in dict(row).items()}
                        for row in samples
                    ]
                except Exception as e:
                    results["sample_data"][full_name] = f"Error: {e}"
            
            if has_embeddings:
                results["embedding_tables"].append(table_info)
                print(f"  🔢 Embedding table: {full_name}")
                
                # Try to get embedding dimensions
                for col in columns:
                    if col["udt_name"] == "vector" or "embed" in col["column_name"].lower():
                        try:
                            cur.execute(f'''
                                SELECT array_length("{col["column_name"]}", 1) as dim
                                FROM "{schema}"."{table_name}" 
                                WHERE "{col["column_name"]}" IS NOT NULL
                                LIMIT 1
                            ''')
                            result = cur.fetchone()
                            if result:
                                col["embedding_dimensions"] = result["dim"]
                        except:
                            pass
        
        # Get database statistics
        cur.execute("SELECT pg_database_size(current_database()) as size")
        results["statistics"]["database_size_bytes"] = cur.fetchone()["size"]
        results["statistics"]["total_tables"] = len(tables)
        results["statistics"]["pdf_related_tables"] = len(results["pdf_related_tables"])
        results["statistics"]["embedding_tables"] = len(results["embedding_tables"])
    
    return results

def main():
    print("=" * 60)
    print("NEON DATABASE ANALYSIS")
    print("=" * 60)
    
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")
    
    if not db_url:
        print("ERROR: NEON_DATABASE_URL not found in config.txt")
        sys.exit(1)
    
    print(f"Connecting to database...")
    
    try:
        conn = psycopg2.connect(db_url)
        print("Connected successfully!")
        
        results = analyze_database(conn)
        
        # Save results
        output_file = OUTPUT_DIR / "neon-analysis.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n✅ Results saved to: {output_file}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total tables: {results['statistics']['total_tables']}")
        print(f"PDF-related tables: {results['statistics']['pdf_related_tables']}")
        print(f"Embedding tables: {results['statistics']['embedding_tables']}")
        print(f"Database size: {results['statistics']['database_size_bytes'] / 1024 / 1024:.2f} MB")
        
        if results["pdf_related_tables"]:
            print("\nPDF-related tables found:")
            for t in results["pdf_related_tables"]:
                print(f"  - {t['name']}: {t['row_count']} rows")
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
