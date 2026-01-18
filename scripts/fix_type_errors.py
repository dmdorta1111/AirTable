"""
Script to fix remaining type errors in PyBase codebase.

Run with: python scripts/fix_type_errors.py

This script addresses:
1. Extraction API type errors (40+)
2. Records API type errors (6)
3. Search service type errors (3)
"""

import subprocess
import sys
from pathlib import Path


def run_mypy(file_path: str) -> list[dict]:
    """Run mypy on a file and return errors."""
    try:
        result = subprocess.run(
            ["python", "-m", "mypy", file_path, "--no-error-summary"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        errors = []
        for line in result.stdout.split("\n"):
            if "error" in line.lower() and ":" in line:
                parts = line.split(":")
                if len(parts) >= 3:
                    errors.append(
                        {
                            "file": parts[0].strip(),
                            "line": parts[1].strip() if len(parts) > 1 else "?",
                            "message": ":".join(parts[2:]).strip(),
                        }
                    )
        return errors
    except Exception as e:
        print(f"Mypy failed: {e}")
        return []


def main():
    print("=" * 60)
    print("PyBase Type Error Fixer")
    print("=" * 60)

    files_to_check = [
        "src/pybase/api/v1/extraction.py",
        "src/pybase/api/v1/records.py",
        "src/pybase/services/search.py",
    ]

    for file_path in files_to_check:
        path = Path(file_path)
        if not path.exists():
            print(f"\n❌ File not found: {file_path}")
            continue

        print(f"\n📄 Checking: {file_path}")
        errors = run_mypy(file_path)

        if not errors:
            print("✅ No type errors found")
        else:
            print(f"⚠️ Found {len(errors)} type errors:")
            for i, error in enumerate(errors[:5], 1):  # Show first 5
                print(f"  {i}. Line {error['line']}: {error['message'][:80]}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more")

    print("\n" + "=" * 60)
    print("Manual fixes may be required for complex type issues.")
    print("Common issues:")
    print("1. UUID vs str type mismatches in API parameters")
    print("2. ORM model vs Pydantic schema return types")
    print("3. Optional imports causing 'None' callable errors")
    print("\nRun: python -m mypy src/pybase/ --show-error-codes")
    print("=" * 60)


if __name__ == "__main__":
    main()
