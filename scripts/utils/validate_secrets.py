#!/usr/bin/env python3
"""
Secrets validation script to scan for exposed credentials in the codebase.

This script scans files for known credential patterns including:
- Neon database URLs with specific passwords
- Backblaze B2 application keys
- Generic API keys and tokens
- Passwords in connection strings
- Placeholder values that indicate incomplete configuration

Usage:
    python scripts/utils/validate_secrets.py --check
    python scripts/utils/validate_secrets.py --scan-all
    python scripts/utils/validate_secrets.py --scan-all --strict
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Pattern


# Known compromised credentials that should NEVER be in the codebase
CRITICAL_SECRETS = [
    # Neon database passwords from security incident
    r"npg_0KrSgPup6IOB",
    r"npg_[A-Za-z0-9]{20,}",  # Generic Neon passwords
    # Neon database hosts
    r"ep-divine-morning-ah0xhu01-pooler\.c-3\.us-east-1\.aws\.neon\.tech",
    r"ep-[a-z-]+-pooler\.[a-z0-9-]+\.[a-z]{2}\.[a-z]+\.neon\.tech",
    # Backblaze B2 keys from security incident
    r"K005QhHpX05u5MvEju\+c2YRPCeSbPZc",
    r"K005JFIj26NGw8Sjmuo72o1VvJSuaSE",
    r"K005[A-Za-z0-9/+]{39}",  # Generic B2 application keys
    r"005fd102a3aebfc000000000[57]",  # B2 key IDs from incident
    r"005[a-f0-9]{24}",  # Generic B2 key IDs
]

# Generic credential patterns (may have false positives)
GENERIC_PATTERNS = [
    # API keys
    r"(?i)(api[_-]?key|apikey|secret[_-]?key|access[_-]?key)['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}['\"]?",
    # Tokens
    r"(?i)(token|auth[_-]?token|bearer[_-]?token|jwt)['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9_\-\.]{20,}['\"]?",
    # Passwords in URLs
    r"(?i)(postgresql|mysql|redis|mongodb|postgres)://[^:]+:[^@]+@",
    # AWS keys
    r"(?i)aws_access_key_id\s*=\s*['\"]?[A-Z0-9]{20}['\"]?",
    r"(?i)aws_secret_access_key\s*=\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?",
    # Private keys (SSH, GPG, etc.)
    r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
    # Base64-encoded secrets (long strings)
    r"[A-Za-z0-9+/]{64,}={0,2}",
]

# Placeholder patterns that indicate incomplete configuration
PLACEHOLDER_PATTERNS = [
    r"(?i)CHANGE[_-]?ME",
    r"(?i)placeholder",
    r"(?i)your[_-]?(_[a-z]+)?[_-]?here",
    r"(?i)example\.com",
    r"(?i)test[_-]?credential",
    r"(?i)xxx{3,}",
]

# Directories and files to exclude from scanning
EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    "build",
    "dist",
    ".eggs",
    "*.egg-info",
    ".auto-claude",
    ".opencode",
    ".idea",
    ".vscode",
}

EXCLUDE_FILES = {
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.dll",
    "*.dylib",
    "*.exe",
    "*.bin",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.jpg",
    "*.jpeg",
    "*.png",
    "*.gif",
    "*.pdf",
    "*.log",
}


def compile_patterns(patterns: list[str]) -> list[Pattern]:
    """Compile regex patterns for efficient matching."""
    return [re.compile(pattern) for pattern in patterns]


def should_exclude_path(path: Path) -> bool:
    """Check if a path should be excluded from scanning."""
    # Check if parent directory is in exclude list
    for parent in path.parents:
        if parent.name in EXCLUDE_DIRS or any(
            parent.match(f"**/{dir}") for dir in EXCLUDE_DIRS
        ):
            return True

    # Check file extension
    if path.suffix.lstrip(".").lower() in {
        ext.lstrip("*.").lower() for ext in EXCLUDE_FILES if ext.startswith("*")
    }:
        return True

    # Check exact file name patterns
    for pattern in EXCLUDE_FILES:
        if path.match(pattern):
            return True

    return False


def scan_file(
    file_path: Path, patterns: list[Pattern], pattern_type: str
) -> list[dict]:
    """Scan a single file for credential patterns."""
    findings = []

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            for pattern in patterns:
                matches = pattern.finditer(line)
                for match in matches:
                    findings.append({
                        "file": str(file_path),
                        "line": line_num,
                        "pattern_type": pattern_type,
                        "match": match.group(0)[:100],  # Truncate long matches
                        "context": line.strip()[:200],
                    })

    except (UnicodeDecodeError, PermissionError, OSError):
        # Skip files we can't read
        pass

    return findings


def scan_directory(
    root_dir: Path,
    critical_patterns: list[Pattern],
    generic_patterns: list[Pattern],
    placeholder_patterns: list[Pattern],
    verbose: bool = False,
) -> dict[str, list[dict]]:
    """Scan all files in a directory for credential patterns."""
    results = {
        "critical": [],
        "generic": [],
        "placeholders": [],
    }

    files_scanned = 0

    for file_path in root_dir.rglob("*"):
        # Skip directories
        if not file_path.is_file():
            continue

        # Skip excluded paths
        if should_exclude_path(file_path):
            continue

        files_scanned += 1

        if verbose and files_scanned % 100 == 0:
            print(f"Scanned {files_scanned} files...", file=sys.stderr)

        # Scan for critical secrets
        critical_findings = scan_file(file_path, critical_patterns, "critical")
        results["critical"].extend(critical_findings)

        # Scan for generic patterns
        generic_findings = scan_file(file_path, generic_patterns, "generic")
        results["generic"].extend(generic_findings)

        # Scan for placeholders
        placeholder_findings = scan_file(
            file_path, placeholder_patterns, "placeholder"
        )
        results["placeholders"].extend(placeholder_findings)

    if verbose:
        print(f"Total files scanned: {files_scanned}", file=sys.stderr)

    return results


def print_findings(results: dict[str, list[dict]], verbose: bool = False) -> None:
    """Print scan results in a user-friendly format."""
    critical_count = len(results["critical"])
    generic_count = len(results["generic"])
    placeholder_count = len(results["placeholders"])

    print("=" * 80)
    print("🔒 SECRETS VALIDATION SCAN RESULTS")
    print("=" * 80)

    if critical_count > 0:
        print(f"\n🚨 CRITICAL SECRETS FOUND: {critical_count}")
        print("-" * 80)
        for finding in results["critical"][:20]:  # Limit to first 20
            print(
                f"  File: {finding['file']}:{finding['line']}\n"
                f"  Match: {finding['match']}\n"
                f"  Context: {finding['context']}\n"
            )
        if critical_count > 20:
            print(f"  ... and {critical_count - 20} more critical findings")
        print("\n⚠️  These are known compromised credentials that MUST be removed!")

    if generic_count > 0 and verbose:
        print(f"\n⚠️  GENERIC PATTERNS FOUND: {generic_count}")
        print("-" * 80)
        print("  (These may be false positives - review manually)")
        for finding in results["generic"][:10]:
            print(
                f"  {finding['file']}:{finding['line']} - {finding['match'][:50]}"
            )
        if generic_count > 10:
            print(f"  ... and {generic_count - 10} more")

    if placeholder_count > 0:
        print(f"\n📝 PLACEHOLDERS FOUND: {placeholder_count}")
        print("-" * 80)
        for finding in results["placeholders"][:10]:
            print(
                f"  {finding['file']}:{finding['line']} - {finding['match'][:50]}"
            )
        if placeholder_count > 10:
            print(f"  ... and {placeholder_count - 10} more")
        print("\n💡 Replace placeholders with actual values in production")

    if critical_count == 0 and generic_count == 0:
        print("\n✅ No secrets detected in the codebase!")

    print("\n" + "=" * 80)


def main() -> int:
    """Main entry point for the secrets validation script."""
    parser = argparse.ArgumentParser(
        description="Validate that no exposed credentials are in the codebase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick check for critical secrets only (fast)
  python scripts/utils/validate_secrets.py --check

  # Comprehensive scan with verbose output
  python scripts/utils/validate_secrets.py --scan-all --verbose

  # Strict mode: fail on any finding
  python scripts/utils/validate_secrets.py --scan-all --strict

Exit codes:
  0 - No secrets found
  1 - Critical secrets detected
  2 - Generic patterns detected (in strict mode)
  3 - Placeholders detected (in strict mode)
        """,
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="Quick check for critical secrets only (default behavior)",
    )

    parser.add_argument(
        "--scan-all",
        action="store_true",
        help="Scan all files including generic patterns and placeholders",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any finding (including generic patterns and placeholders)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    parser.add_argument(
        "--directory",
        type=Path,
        default=Path.cwd(),
        help="Root directory to scan (default: current directory)",
    )

    args = parser.parse_args()

    # Compile patterns
    critical_patterns = compile_patterns(CRITICAL_SECRETS)
    generic_patterns = compile_patterns(GENERIC_PATTERNS)
    placeholder_patterns = compile_patterns(PLACEHOLDER_PATTERNS)

    # Scan directory
    if args.verbose:
        print(f"Scanning directory: {args.directory}", file=sys.stderr)

    results = scan_directory(
        args.directory,
        critical_patterns,
        generic_patterns,
        placeholder_patterns,
        verbose=args.verbose,
    )

    # Print results
    if args.scan_all or args.verbose:
        print_findings(results, verbose=args.verbose)

    # Determine exit code
    critical_count = len(results["critical"])
    generic_count = len(results["generic"])
    placeholder_count = len(results["placeholders"])

    if critical_count > 0:
        print("❌ CRITICAL: Exposed credentials detected!", file=sys.stderr)
        return 1

    if args.strict:
        if generic_count > 0:
            print("❌ FAIL: Generic credential patterns detected (strict mode)", file=sys.stderr)
            return 2
        if placeholder_count > 0:
            print("❌ FAIL: Placeholders detected (strict mode)", file=sys.stderr)
            return 3

    if not args.check and not args.scan_all:
        # Default: just run quick check
        print_findings(results, verbose=False)

    return 0


if __name__ == "__main__":
    sys.exit(main())
