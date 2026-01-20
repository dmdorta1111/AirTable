#!/usr/bin/env python3
"""Test script to debug Path issues"""

import sys
from pathlib import Path

# Test basic Path operations
try:
    script_dir = Path(__file__).parent
    print(f"Script dir: {script_dir}")
    print(f"Script dir exists: {script_dir.exists()}")
    print(f"Script dir type: {type(script_dir)}")

    plan_dir = script_dir.parent
    print(f"Plan dir: {plan_dir}")
    print(f"Plan dir exists: {plan_dir.exists()}")

    config_file = plan_dir / "config.txt"
    print(f"Config file: {config_file}")
    print(f"Config file exists: {config_file.exists()}")

    output_dir = plan_dir / "output"
    print(f"Output dir: {output_dir}")
    print(f"Output dir type: {type(output_dir)}")

    # Try mkdir
    output_dir.mkdir(exist_ok=True)
    print(f"mkdir succeeded")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("Test passed!")
