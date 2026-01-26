"""
B2 Full Bucket Audit Script
Chunks through the bucket using prefix-based enumeration to get ALL files.
"""
import json
import sys
from pathlib import Path
from collections import Counter

# Output file for combined results
OUTPUT_FILE = Path("b2_full_audit_results.json")
PROGRESS_FILE = Path("b2_audit_progress.txt")

# Known prefixes to chunk through - based on the audit showing most files are under S:/
PREFIXES = [
    "",           # Root level files
    "J",          # JOBS CUSTOM FAB
    "M",          # Misc
    "S/0",        # S:/ paths starting with 0
    "S/1",
    "S/2",
    "S/3",
    "S/4",
    "S/5",
    "S/6",
    "S/7",
    "S/8",
    "S/9",
    "S/a",
    "S/b",
    "S/c",
    "S/d",
    "S/e",
    "S/f",
    "S/g",
    "S/h",
    "S/i",
    "S/j",
    "S/k",
    "S/l",
    "S/m",
    "S/n",
    "S/o",
    "S/p",
    "S/q",
    "S/r",
    "S/s",
    "S/t",
    "S/u",
    "S/v",
    "S/w",
    "S/x",
    "S/y",
    "S/z",
]

# Read existing results
ALL_FILES = []
if OUTPUT_FILE.exists():
    with open(OUTPUT_FILE, 'r') as f:
        ALL_FILES = json.load(f)
    print(f"Loaded {len(ALL_FILES)} existing files from {OUTPUT_FILE}")

print("=" * 70)
print("B2 FULL AUDIT - CHUNKED ENUMERATION")
print("=" * 70)
print()

# Determine which prefixes we still need to process
completed_prefixes = set()
for f in ALL_FILES:
    name = f.get("file_name", "")
    for p in PREFIXES:
        if name.startswith(p):
            completed_prefixes.add(p)
            break

remaining = [p for p in PREFIXES if p not in completed_prefixes]
print(f"Completed prefixes: {len(completed_prefixes)}/{len(PREFIXES)}")
print(f"Remaining prefixes: {len(remaining)}")
print()

print("To process remaining prefixes, use the MCP list_files tool with each prefix.")
print("Then combine results into b2_full_audit_results.json")
print()
print("Prefixes to process:")
for p in remaining:
    print(f"  '{p}'")
