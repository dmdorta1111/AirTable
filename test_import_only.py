import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Starting import test...")
print("Python version:", sys.version)
print("Path:", sys.path[:3])

try:
    print("\n1. Attempting to import pybase...")
    import pybase
    print("   SUCCESS")
except Exception as e:
    print(f"   FAILED: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n2. Attempting to import pybase.fields...")
    import pybase.fields
    print("   SUCCESS")
except Exception as e:
    print(f"   FAILED: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n3. Attempting to import pybase.fields.base...")
    import pybase.fields.base
    print("   SUCCESS")
except Exception as e:
    print(f"   FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\nDone")
