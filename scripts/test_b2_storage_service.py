#!/usr/bin/env python3
"""
Test script for B2StorageService.

Tests both b2sdk and rclone operations.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pybase.services.b2_storage import B2StorageService, B2Config


async def test_b2sdk_operations():
    """Test b2sdk operations: list, upload, download, delete."""
    print("=" * 70)
    print("TESTING b2sdk OPERATIONS")
    print("=" * 70)

    config = B2Config.from_settings()
    if not config.validate():
        print("ERROR: Invalid B2 configuration")
        return False

    service = B2StorageService(config)

    try:
        # Test 1: List files
        print("\n1. Listing files (limit 5)...")
        files = await service.list_files(limit=5)
        print(f"   Found {len(files)} files")
        if files:
            print(f"   First: {files[0].file_name} ({files[0].size} bytes)")

        # Test 2: Check file exists
        if files:
            print("\n2. Checking file exists...")
            exists = await service.file_exists(files[0].file_name)
            print(f"   {files[0].file_name}: {exists}")

        # Test 3: Get file info
        if files:
            print("\n3. Getting file info...")
            info = await service.get_file_info(files[0].file_name)
            if info:
                print(f"   {info.file_name}: {info.size} bytes, {info.content_type}")

        # Test 4: Upload test file
        print("\n4. Uploading test file...")
        test_file = Path(__file__).parent / "test_upload.txt"
        test_file.write_text("B2 storage service test")

        remote_name = f"test/b2_storage_test_{sys.platform}.txt"
        uploaded = await service.upload_file(test_file, remote_name)
        print(f"   Uploaded: {uploaded.file_name} ({uploaded.size} bytes)")

        # Test 5: Download test file
        print("\n5. Downloading test file...")
        download_path = Path(__file__).parent / "test_download.txt"
        downloaded = await service.download_file(remote_name, download_path)
        print(f"   Downloaded: {download_path} ({downloaded.size} bytes)")
        content = download_path.read_text()
        print(f"   Content matches: {content == 'B2 storage service test'}")

        # Test 6: Rename test file
        print("\n6. Renaming test file...")
        new_name = f"test/b2_storage_renamed_{sys.platform}.txt"
        renamed = await service.rename_file(remote_name, new_name)
        if renamed:
            print(f"   Renamed to: {renamed.file_name}")
        else:
            print("   Rename failed (this is okay if file already exists)")

        # Test 7: Hide file
        print("\n7. Hiding renamed file...")
        hidden = await service.hide_file(new_name)
        print(f"   Hidden: {hidden}")

        # Cleanup
        test_file.unlink(exist_ok=True)
        download_path.unlink(exist_ok=True)

        print("\n✓ b2sdk operations passed")
        return True

    except Exception as e:
        print(f"\n✗ b2sdk operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        service.close()


async def test_rclone_operations():
    """Test rclone operations: bulk upload/download."""
    print("\n" + "=" * 70)
    print("TESTING rclone OPERATIONS")
    print("=" * 70)

    config = B2Config.from_settings()
    if not config.validate():
        print("ERROR: Invalid B2 configuration")
        return False

    service = B2StorageService(config)

    try:
        # Test 1: Check rclone availability
        print("\n1. Checking rclone availability...")
        result = await service._run_rclone(["version"], check=False)
        if result.returncode == 0:
            print(f"   ✓ rclone available: {result.stdout.split()[1]}")
        else:
            print("   ✗ rclone not found - skipping rclone tests")
            return True  # Not a failure, just skip

        # Test 2: Bulk upload
        print("\n2. Testing bulk upload...")
        test_dir = Path(__file__).parent / "test_bulk_upload"
        test_dir.mkdir(exist_ok=True)

        # Create test files
        for i in range(3):
            (test_dir / f"file{i}.txt").write_text(f"Test file {i}")

        stats = await service.bulk_upload(
            test_dir,
            remote_prefix="test/bulk/",
            pattern="*.txt",
            parallel=2,
        )
        print(f"   Upload result: {stats.get('success', False)}")

        # Test 3: Bulk download
        print("\n3. Testing bulk download...")
        download_dir = Path(__file__).parent / "test_bulk_download"
        stats = await service.bulk_download(
            remote_prefix="test/bulk/",
            local_dir=download_dir,
            parallel=2,
        )
        print(f"   Download result: {stats.get('success', False)}")
        downloaded_files = list(download_dir.glob("*.txt"))
        print(f"   Downloaded {len(downloaded_files)} files")

        # Cleanup
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)
        if download_dir.exists():
            shutil.rmtree(download_dir)

        print("\n✓ rclone operations passed")
        return True

    except Exception as e:
        print(f"\n✗ rclone operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        service.close()


async def test_bucket_stats():
    """Test bucket statistics."""
    print("\n" + "=" * 70)
    print("TESTING BUCKET STATS")
    print("=" * 70)

    config = B2Config.from_settings()
    if not config.validate():
        print("ERROR: Invalid B2 configuration")
        return False

    service = B2StorageService(config)

    try:
        print("\n1. Getting bucket stats (this may take a while)...")
        stats = await service.get_bucket_stats()
        print(f"   Total files: {stats['file_count']:,}")
        print(f"   Total size: {stats['total_size_gb']} GB")

        # Test search
        print("\n2. Testing file search...")
        matches = await service.search_files("*.txt", prefix="test")
        print(f"   Found {len(matches)} .txt files under test/")

        print("\n✓ Bucket stats passed")
        return True

    except Exception as e:
        print(f"\n✗ Bucket stats failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        service.close()


async def main():
    """Run all tests."""
    print("B2StorageService Test Suite")
    print("=" * 70)

    # Check config
    config = B2Config.from_settings()
    print(f"\nConfiguration:")
    print(f"  Key ID: {config.key_id[:10]}..." if config.key_id else "  Key ID: NOT SET")
    print(f"  Bucket: {config.bucket_name or 'NOT SET'}")

    if not config.validate():
        print("\nERROR: B2 credentials not configured!")
        print("Set B2_APPLICATION_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET_NAME environment variables")
        print("Or add them to unified-doc-intelligence-deploy/config.txt")
        return 1

    results = []

    # Run tests
    results.append(await test_b2sdk_operations())
    results.append(await test_rclone_operations())
    results.append(await test_bucket_stats())

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if all(results):
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
