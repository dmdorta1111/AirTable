import os
import sys

# Set the database URL
os.environ["DATABASE_URL"] = (
    "postgresql://neondb_owner:npg_0KrSgPup6IOB@ep-divine-morning-ah0xhu01-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)

print("Testing Neon database connection...")
print(f"URL: {os.environ['DATABASE_URL'][:80]}...")

try:
    import psycopg2

    print("✅ psycopg2 available")
except ImportError:
    print("Installing psycopg2-binary...")
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2

try:
    # Connect to database
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    print("✅ Database connection successful!")

    # Run a simple query
    cursor = conn.cursor()
    cursor.execute("SELECT version()")
    version = cursor.fetchone()[0]
    print(f"Database version: {version}")

    # Check tables
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)

    tables = cursor.fetchall()
    print(f"Found {len(tables)} tables in public schema:")

    for table in tables:
        print(f"  - {table[0]}")

    cursor.close()
    conn.close()

    print("\n✅ Database test PASSED")

except Exception as e:
    print(f"❌ Database connection failed: {e}")
    sys.exit(1)
