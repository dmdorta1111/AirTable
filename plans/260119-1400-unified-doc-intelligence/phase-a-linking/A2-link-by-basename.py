#!/usr/bin/env python3
"""
A2-link-by-basename.py
Links files that share the same basename (filename without extension).

Example: "88617-001.pdf", "88617-001.dxf", "88617-001.prt" → Same DocumentGroup

Confidence: 0.95 (auto_filename)

Usage: python A2-link-by-basename.py
"""

import sys
import logging
import json
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
    ".drw": "drawing_pdf",  # Creo drawing files
}


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


def get_basename(filepath):
    """Extract basename without extension from a path."""
    if not filepath:
        return None
    # Handle both forward and back slashes
    filename = filepath.replace("\\", "/").split("/")[-1]
    # Remove extension
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
    ext_lower = ext.lower()
    return EXTENSION_ROLE_MAP.get(ext_lower)


def main():
    print("=" * 70)
    print("A2: LINK BY BASENAME")
    print("=" * 70)
    print("Grouping files that share the same basename (filename without extension)")
    print("Confidence: 0.95 | Method: auto_filename")
    print("=" * 70)

    # Load config
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")

    if not db_url:
        logger.error("NEON_DATABASE_URL not found in config.txt")
        sys.exit(1)

    # Connect to database
    logger.info("Connecting to Neon PostgreSQL...")

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False

        logger.info("Connected successfully!")

        with conn.cursor() as cur:
            # Step 1: Fetch all CloudFiles
            logger.info("Fetching all files from CloudFiles...")
            cur.execute("""
                SELECT "ID", "CloudKey", "LocalPath", "FileType"
                FROM "CloudFiles"
            """)

            files = cur.fetchall()
            logger.info(f"Found {len(files):,} files")

            # Step 2: Group by basename
            logger.info("Grouping files by basename...")
            basename_groups = defaultdict(list)

            for file_id, cloud_key, local_path, file_type in tqdm(files, desc="Analyzing"):
                # Use CloudKey or LocalPath for the filename
                filepath = cloud_key or local_path
                if not filepath:
                    continue

                basename = get_basename(filepath)
                if not basename:
                    continue

                ext = get_extension(filepath)
                role = get_role_for_extension(ext)

                if role:  # Only include files with recognized extensions
                    basename_groups[basename].append(
                        {"id": file_id, "path": filepath, "ext": ext, "role": role}
                    )

            # Step 3: Filter groups with 2+ files
            linkable_groups = {
                bn: files for bn, files in basename_groups.items() if len(files) >= 2
            }

            logger.info(f"Found {len(linkable_groups):,} basenames with 2+ files")

            # Step 4: Create DocumentGroups and Members
            logger.info("Creating DocumentGroups...")

            groups_created = 0
            members_created = 0

            # Prepare batch inserts
            group_data = []

            for basename, members in tqdm(linkable_groups.items(), desc="Creating groups"):
                group_data.append(
                    (
                        basename,  # name
                        "auto_filename",  # linking_method
                        0.95,  # linking_confidence
                        False,  # needs_review
                    )
                )

            # Batch insert DocumentGroups
            if group_data:
                execute_values(
                    cur,
                    """
                    INSERT INTO document_groups (name, linking_method, linking_confidence, needs_review)
                    VALUES %s
                    RETURNING id, name
                    """,
                    group_data,
                )

                # Get the inserted group IDs
                inserted_groups = cur.fetchall()
                group_id_map = {name: gid for gid, name in inserted_groups}
                groups_created = len(inserted_groups)

                logger.info(f"Created {groups_created:,} DocumentGroups")

                # Now insert members
                logger.info("Creating DocumentGroupMembers...")

                member_data = []

                for basename, members in tqdm(linkable_groups.items(), desc="Linking members"):
                    group_id = group_id_map.get(basename)
                    if not group_id:
                        continue

                    # Determine primary (prefer source_cad, then dxf, then pdf)
                    members_sorted = sorted(
                        members,
                        key=lambda m: (
                            0
                            if m["role"] == "source_cad"
                            else 1
                            if m["role"] == "drawing_dxf"
                            else 2
                        ),
                    )

                    for idx, member in enumerate(members_sorted):
                        is_primary = idx == 0
                        member_data.append(
                            (
                                group_id,
                                member["id"],  # cloud_file_id
                                member["role"],  # role
                                is_primary,  # is_primary
                            )
                        )

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

                for basename, members in tqdm(linkable_groups.items(), desc="Updating CloudFiles"):
                    group_id = group_id_map.get(basename)
                    if not group_id:
                        continue

                    file_ids = [m["id"] for m in members]
                    cur.execute(
                        """
                        UPDATE "CloudFiles"
                        SET document_group_id = %s
                        WHERE "ID" = ANY(%s)
                    """,
                        (group_id, file_ids),
                    )

            # Commit all changes
            conn.commit()

            # Print summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Total files analyzed:    {len(files):,}")
            print(f"Basenames with 2+ files: {len(linkable_groups):,}")
            print(f"DocumentGroups created:  {groups_created:,}")
            print(f"Members linked:          {members_created:,}")

            # Role breakdown
            role_counts = defaultdict(int)
            for members in linkable_groups.values():
                for m in members:
                    role_counts[m["role"]] += 1

            print("\nBy Role:")
            for role, count in sorted(role_counts.items()):
                print(f"  {role}: {count:,}")

        conn.close()

        # Save report
        report = {
            "timestamp": datetime.now().isoformat(),
            "files_analyzed": len(files),
            "linkable_basenames": len(linkable_groups),
            "groups_created": groups_created,
            "members_linked": members_created,
            "role_counts": dict(role_counts),
            "linking_method": "auto_filename",
            "linking_confidence": 0.95,
        }

        report_file = OUTPUT_DIR / "A2-basename-linking.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n✓ Report saved to: {report_file}")

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
