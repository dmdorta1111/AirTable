#!/usr/bin/env python3
"""
B2StorageService Usage Examples.

Shows how to use the hybrid B2 storage service.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pybase.services.b2_storage import B2StorageService, B2Config


async def main():
    """Run usage examples."""

    # ============================================================
    # 1. Initialize Service
    # ============================================================
    # Method A: From environment variables (B2_APPLICATION_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET_NAME)
    service = B2StorageService()

    # Method B: From config file (automatically reads unified-doc-intelligence-deploy/config.txt)
    config = B2Config.from_settings()
    service = B2StorageService(config)

    # ============================================================
    # 2. List Files (uses b2sdk - fast for queries)
    # ============================================================
    print("\n--- List Files ---")
    files = await service.list_files(prefix="S/", limit=10)
    for f in files:
        print(f"  {f.file_name} ({f.size} bytes)")

    # ============================================================
    # 3. Check File Exists (uses b2sdk)
    # ============================================================
    print("\n--- Check File Exists ---")
    exists = await service.file_exists("S/example.txt")
    print(f"  File exists: {exists}")

    # ============================================================
    # 4. Upload Single File (uses b2sdk - good for small files)
    # ============================================================
    print("\n--- Upload Single File ---")
    await service.upload_file(
        local_path="local_file.txt",
        remote_name="uploaded/file.txt"
    )

    # ============================================================
    # 5. Bulk Upload (uses rclone - parallel transfers)
    # ============================================================
    print("\n--- Bulk Upload ---")
    stats = await service.bulk_upload(
        local_dir="./files_to_upload",
        remote_prefix="batch/",
        parallel=8  # 8 parallel transfers
    )
    print(f"  Success: {stats.get('success')}")

    # ============================================================
    # 6. Sync Directory (uses rclone - optimized sync)
    # ============================================================
    print("\n--- Sync Directory ---")
    stats = await service.sync(
        local_dir="./my_folder",
        remote_prefix="backup/",
        direction="up",  # or "down" or "both"
        delete=False  # Set True to delete files not in source
    )
    print(f"  Sync result: {stats.get('success')}")

    # ============================================================
    # 7. Search Files (uses b2sdk with glob pattern)
    # ============================================================
    print("\n--- Search Files ---")
    matches = await service.search_files("*.pdf", prefix="S/docs/")
    print(f"  Found {len(matches)} PDF files")

    # ============================================================
    # 8. Rename File (uses b2sdk - copy+delete)
    # ============================================================
    print("\n--- Rename File ---")
    await service.rename_file(
        old_name="old/path.txt",
        new_name="new/path.txt"
    )

    # ============================================================
    # 9. Download File (uses b2sdk)
    # ============================================================
    print("\n--- Download File ---")
    await service.download_file(
        remote_name="remote/file.txt",
        local_path="./downloaded.txt"
    )

    # ============================================================
    # 10. Bulk Download (uses rclone - parallel)
    # ============================================================
    print("\n--- Bulk Download ---")
    stats = await service.bulk_download(
        remote_prefix="backup/",
        local_dir="./restored_files/",
        parallel=8
    )

    # ============================================================
    # 11. Delete File (uses b2sdk)
    # ============================================================
    print("\n--- Delete File ---")
    await service.delete_file("unwanted.txt")

    # ============================================================
    # 12. Get Bucket Stats (uses b2sdk - may be slow for large buckets)
    # ============================================================
    print("\n--- Bucket Stats ---")
    stats = await service.get_bucket_stats()
    print(f"  Files: {stats['file_count']:,}")
    print(f"  Size: {stats['total_size_gb']} GB")

    # Cleanup
    service.close()


if __name__ == "__main__":
    asyncio.run(main())
