#!/usr/bin/env python3
"""
A3-link-by-folder.py
Links files in the same folder that share a common prefix.

Only processes files NOT already in a DocumentGroup.
Example: "88617-001-BRACKET.pdf" and "88617-001.dxf" in same folder → link them

Confidence: 0.80 (auto_folder)

Usage: python A3-link-by-folder.py
"""

import sys
import logging
import json
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import psycopg2
from psycopg2.extras import execute_values
from tqdm import tqdm

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
PLAN_DIR = SCRIPT_DIR.parent
CONFIG_FILE = PLAN_DIR / "config.txt"
OUTPUT_DIR = PLAN_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Role mapping by extension
EXTENSION_ROLE_MAP = {
    ".pdf": "drawing_pdf",
    ".dxf": "drawing_dxf",
    ".prt": "source_cad",
    ".asm": "source_cad",
    ".drw": "drawing_pdf",
}

# Minimum prefix length to consider as a match
MIN_PREFIX_LENGTH = 5


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


def get_folder(filepath):
    """Extract folder path from a filepath."""
    if not filepath:
        return None
    # Normalize path separators
    normalized = filepath.replace("\\", "/")
    if "/" in normalized:
        return normalized.rsplit("/", 1)[0]
    return ""


def get_filename(filepath):
    """Extract filename from a path."""
    if not filepath:
        return None
    normalized = filepath.replace("\\", "/")
    return normalized.split("/")[-1]


def get_basename(filename):
    """Get filename without extension."""
    if not filename:
        return None
    if "." in filename:
        return filename.rsplit(".", 1)[0]
    return filename


def get_extension(filepath):
    """Extract lowercase extension from a path."""
    if not filepath:
        return None
    if "." in filepath:
        return "." + filepath.rsplit(".", 1)[1].lower()
    return None


def get_role_for_extension(ext):
    """Map file extension to document role."""
    if not ext:
        return None
    return EXTENSION_ROLE_MAP.get(ext.lower())


def find_common_prefix(str1, str2):
    """Find the common prefix between two strings."""
    prefix = []
    for c1, c2 in zip(str1, str2):
        if c1 == c2:
            prefix.append(c1)
        else:
            break
    return "".join(prefix)


def extract_item_prefix(basename):
    """
    Extract the item/part number prefix from a basename.
    Examples:
        "88617-001-BRACKET" → "88617-001"
        "88617-001" → "88617-001"
        "DWG-12345-REV-A" → "DWG-12345"
    """
    if not basename:
        return None

    # Pattern: digits followed by dash and more digits (common part number format)
    match = re.match(r"^(\d{4,6}-\d{1,4})", basename)
    if match:
        return match.group(1)

    # Pattern: project prefix with number
    match = re.match(r"^([A-Z]{2,4}-\d{4,6})", basename, re.IGNORECASE)
    if match:
        return match.group(1)

    # Fallback: first segment before a descriptive part
    # Split on common separators like underscore, dash followed by letter
    parts = re.split(r"[-_](?=[A-Za-z])", basename)
    if parts and len(parts[0]) >= MIN_PREFIX_LENGTH:
        return parts[0]

    return None


def main():
    print("=" * 70)
    print("A3: LINK BY FOLDER")
    print("=" * 70)
    print("Linking files in same folder that share a common prefix")
    print("Confidence: 0.80 | Method: auto_folder")
    print("=" * 70)

    # Load config
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")

    if not db_url:
        logger.error("NEON_DATABASE_URL not found in config.txt")
        sys.exit(1)

    # Connect to database
    logger.info("Connecting to Neon PostgreSQL...")

    conn = None
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False

        logger.info("Connected successfully!")

        with conn.cursor() as cur:
            # Step 1: Fetch files NOT already in a DocumentGroup
            logger.info("Fetching unlinked files from CloudFiles...")
            cur.execute("""
                SELECT "ID", "CloudKey", "LocalPath", "FileType"
                FROM "CloudFiles"
                WHERE document_group_id IS NULL
            """)

            files = cur.fetchall()
            logger.info(f"Found {len(files):,} unlinked files")

            # Step 2: Group by folder
            logger.info("Grouping files by folder...")
            folder_files = defaultdict(list)

            for file_id, cloud_key, local_path, file_type in tqdm(
                files, desc="Organizing by folder"
            ):
                filepath = cloud_key or local_path
                if not filepath:
                    continue

                folder = get_folder(filepath)
                filename = get_filename(filepath)
                basename = get_basename(filename)
                ext = get_extension(filepath)
                role = get_role_for_extension(ext)

                if role and basename:  # Only include recognized file types
                    folder_files[folder].append(
                        {
                            "id": file_id,
                            "path": filepath,
                            "filename": filename,
                            "basename": basename,
                            "ext": ext,
                            "role": role,
                            "prefix": extract_item_prefix(basename),
                        }
                    )

            # Step 3: Within each folder, group by common prefix
            logger.info("Finding files with common prefixes within folders...")

            linkable_groups = []

            for folder, folder_members in tqdm(folder_files.items(), desc="Analyzing folders"):
                if len(folder_members) < 2:
                    continue

                # Group by extracted prefix
                prefix_groups = defaultdict(list)

                for member in folder_members:
                    prefix = member.get("prefix")
                    if prefix and len(prefix) >= MIN_PREFIX_LENGTH:
                        prefix_groups[prefix].append(member)

                # Only keep groups with 2+ files of different types
                for prefix, members in prefix_groups.items():
                    if len(members) >= 2:
                        # Check for different file types
                        roles = set(m["role"] for m in members)
                        if len(roles) >= 2:  # At least 2 different roles
                            linkable_groups.append(
                                {"folder": folder, "prefix": prefix, "members": members}
                            )

            logger.info(f"Found {len(linkable_groups):,} linkable folder groups")

            if not linkable_groups:
                print("\n✓ No additional folder-based links found")
                conn.close()
                return

            # Step 4: Create DocumentGroups and Members
            logger.info("Creating DocumentGroups...")

            groups_created = 0
            members_created = 0

            # Prepare batch inserts
            group_data = []

            for group in tqdm(linkable_groups, desc="Preparing groups"):
                # Use prefix as group name
                group_name = group["prefix"]
                group_data.append(
                    (
                        group_name,  # name
                        "auto_folder",  # linking_method
                        0.80,  # linking_confidence
                        False,  # needs_review
                    )
                )

            # Batch insert DocumentGroups
            execute_values(
                cur,
                """
                INSERT INTO document_groups (name, linking_method, linking_confidence, needs_review)
                VALUES %s
                RETURNING id
                """,
                group_data,
            )

            # Get the inserted group IDs
            inserted_ids = [row[0] for row in cur.fetchall()]
            groups_created = len(inserted_ids)

            logger.info(f"Created {groups_created:,} DocumentGroups")

            # DEBUG: Check array lengths match
            if len(inserted_ids) != len(linkable_groups):
                logger.warning(
                    f"Array mismatch! inserted_ids={len(inserted_ids)}, linkable_groups={len(linkable_groups)}"
                )
                logger.warning(
                    "This can happen if duplicate groups were inserted. Trimming to match."
                )
                # If mismatch, use only available IDs
                min_len = min(len(inserted_ids), len(linkable_groups))
                inserted_ids = inserted_ids[:min_len]
                linkable_groups = linkable_groups[:min_len]

            # Now insert members
            logger.info("Creating DocumentGroupMembers...")

            member_data = []
            update_data = []

            for idx, group in enumerate(tqdm(linkable_groups, desc="Linking members")):
                group_id = inserted_ids[idx]

                # Determine primary (prefer source_cad, then dxf, then pdf)
                members_sorted = sorted(
                    group["members"],
                    key=lambda m: (
                        0 if m["role"] == "source_cad" else 1 if m["role"] == "drawing_dxf" else 2
                    ),
                )

                for midx, member in enumerate(members_sorted):
                    is_primary = midx == 0
                    member_data.append((group_id, member["id"], member["role"], is_primary))
                    update_data.append((group_id, member["id"]))

            # Batch insert members
            if member_data:
                execute_values(
                    cur,
                    """
                    INSERT INTO document_group_members 
                    (group_id, cloud_file_id, role, is_primary)
                    VALUES %s
                    """,
                    member_data,
                )
                members_created = len(member_data)

                logger.info(f"Created {members_created:,} DocumentGroupMembers")

            # Update CloudFiles with document_group_id
            logger.info("Updating CloudFiles with group references...")

            for group_id, file_id in tqdm(update_data, desc="Updating CloudFiles"):
                cur.execute(
                    """
                    UPDATE "CloudFiles"
                    SET document_group_id = %s
                    WHERE "ID" = %s
                """,
                    (group_id, file_id),
                )

            # Commit all changes
            conn.commit()

            # Print summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Unlinked files analyzed: {len(files):,}")
            print(f"Folders processed:       {len(folder_files):,}")
            print(f"DocumentGroups created:  {groups_created:,}")
            print(f"Members linked:          {members_created:,}")

            # Role breakdown
            role_counts = defaultdict(int)
            for group in linkable_groups:
                for m in group["members"]:
                    role_counts[m["role"]] += 1

            print("\nBy Role:")
            for role, count in sorted(role_counts.items()):
                print(f"  {role}: {count:,}")

        conn.close()

        # Save report
        report = {
            "timestamp": datetime.now().isoformat(),
            "unlinked_files_analyzed": len(files),
            "folders_processed": len(folder_files),
            "groups_created": groups_created,
            "members_linked": members_created,
            "role_counts": dict(role_counts),
            "linking_method": "auto_folder",
            "linking_confidence": 0.80,
        }

        report_file = OUTPUT_DIR / "A3-folder-linking.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n[OK] Report saved to: {report_file}")

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        if "conn" in locals() and conn:
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
