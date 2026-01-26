"""
Hybrid B2 Storage Service.

Routes operations to best tool:
- b2sdk: list, search, single upload/download, rename, delete
- rclone: bulk upload/download, sync operations

Prerequisites:
- pip install b2sdk
- Install rclone: https://rclone.org/install/
"""

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Optional

from b2sdk.v1 import (
    B2Api,
    InMemoryAccountInfo,
    DownloadDestLocalFile,
)

logger = logging.getLogger(__name__)


@dataclass
class B2Config:
    """B2 configuration."""

    key_id: str
    application_key: str
    bucket_name: str
    realm: str = "production"

    @classmethod
    def from_settings(cls) -> "B2Config":
        """Create config from environment variables."""
        key_id = os.getenv("B2_APPLICATION_KEY_ID", "")
        app_key = os.getenv("B2_APPLICATION_KEY", "")
        bucket_name = os.getenv("B2_BUCKET_NAME", "")

        if not all([key_id, app_key, bucket_name]):
            # Try loading from config.txt
            config_file = Path(__file__).parent.parent.parent.parent / "unified-doc-intelligence-deploy" / "config.txt"
            if config_file.exists():
                with open(config_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()
                            if key == "B2_APPLICATION_KEY_ID":
                                key_id = value
                            elif key == "B2_APPLICATION_KEY":
                                app_key = value
                            elif key == "B2_BUCKET_NAME":
                                bucket_name = value

        return cls(
            key_id=key_id,
            application_key=app_key,
            bucket_name=bucket_name,
        )

    def validate(self) -> bool:
        """Validate config has required values."""
        return bool(self.key_id and self.application_key and self.bucket_name)


@dataclass
class B2FileInfo:
    """B2 file information."""

    file_name: str
    file_id: str
    size: int
    content_type: str
    content_md5: str | None
    upload_timestamp: int
    action: str = "upload"  # upload, hide, delete, folder

    @classmethod
    def from_b2_file(cls, file_info) -> "B2FileInfo":
        """Create from b2sdk file info."""
        return cls(
            file_name=file_info.file_name,
            file_id=file_info.id_,
            size=file_info.size or 0,
            content_type=file_info.content_type or "application/octet-stream",
            content_md5=file_info.content_md5,
            upload_timestamp=file_info.upload_timestamp,
            action="start" if file_info.api_name == "start" else "upload",
        )


class B2StorageService:
    """
    Hybrid B2 storage service using b2sdk and rclone.

    Routes operations to best tool:
    - b2sdk: list, search, single upload/download, rename, delete
    - rclone: bulk upload/download, sync operations
    """

    def __init__(self, config: B2Config | None = None):
        """Initialize B2 storage service.

        Args:
            config: B2 configuration. If None, loads from environment.
        """
        self.config = config or B2Config.from_settings()
        self._api: B2Api | None = None
        self._bucket = None
        self._rclone_config_path: Path | None = None

    @property
    def api(self) -> B2Api:
        """Get or create B2 API instance."""
        if self._api is None:
            if not self.config.validate():
                raise ValueError("Invalid B2 configuration. Set B2_APPLICATION_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET_NAME")

            info = InMemoryAccountInfo()
            self._api = B2Api(info)
            self._api.authorize_account(self.config.realm, self.config.key_id, self.config.application_key)
            logger.info(f"Authenticated to B2 realm: {self.config.realm}")

        return self._api

    @property
    def bucket(self):
        """Get or create B2 bucket instance."""
        if self._bucket is None:
            self._bucket = self.api.get_bucket_by_name(self.config.bucket_name)
            logger.info(f"Connected to B2 bucket: {self.config.bucket_name}")
        return self._bucket

    # ==========================================================================
    # b2sdk Operations: List, Search, Single File Ops
    # ==========================================================================

    async def list_files(
        self,
        prefix: str = "",
        recursive: bool = True,
        limit: int | None = None,
    ) -> list[B2FileInfo]:
        """List files in bucket with optional prefix.

        Args:
            prefix: File name prefix to filter
            recursive: List recursively
            limit: Max number of files to return

        Returns:
            List of B2FileInfo objects
        """
        files = []
        count = 0

        for file_info, _ in self.bucket.ls(folder_to_list=prefix, recursive=recursive):
            if file_info.file_name == prefix:  # Skip folder marker
                continue

            files.append(B2FileInfo.from_b2_file(file_info))
            count += 1

            if limit and count >= limit:
                break

        logger.info(f"Listed {len(files)} files with prefix '{prefix}'")
        return files

    async def list_files_iter(
        self,
        prefix: str = "",
        recursive: bool = True,
    ) -> AsyncIterator[B2FileInfo]:
        """Iterate over files in bucket.

        Args:
            prefix: File name prefix to filter
            recursive: List recursively

        Yields:
            B2FileInfo objects
        """
        for file_info, _ in self.bucket.ls(folder_to_list=prefix, recursive=recursive):
            if file_info.file_name == prefix:
                continue
            yield B2FileInfo.from_b2_file(file_info)

    async def get_file_info(self, file_name: str) -> B2FileInfo | None:
        """Get information about a specific file.

        Args:
            file_name: Full file path in bucket

        Returns:
            B2FileInfo or None if not found
        """
        try:
            file_info = self.bucket.get_file_info_by_name(file_name)
            return B2FileInfo.from_b2_file(file_info)
        except Exception as e:
            logger.debug(f"File not found: {file_name} - {e}")
            return None

    async def file_exists(self, file_name: str) -> bool:
        """Check if file exists in bucket.

        Args:
            file_name: Full file path in bucket

        Returns:
            True if file exists
        """
        return await self.get_file_info(file_name) is not None

    async def upload_file(
        self,
        local_path: str | Path,
        remote_name: str | None = None,
        content_type: str | None = None,
    ) -> B2FileInfo:
        """Upload a single file to B2.

        Args:
            local_path: Path to local file
            remote_name: Remote file name. Defaults to local file name
            content_type: Content type. Auto-detected if None

        Returns:
            B2FileInfo of uploaded file
        """
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        remote_name = remote_name or str(local_path.name)

        file_info = self.bucket.upload_local_file(
            local_file=str(local_path),
            file_name=remote_name,
            content_type=content_type,
        )

        logger.info(f"Uploaded {local_path} -> {remote_name} ({file_info.size} bytes)")
        return B2FileInfo.from_b2_file(file_info)

    async def download_file(
        self,
        remote_name: str,
        local_path: str | Path,
    ) -> B2FileInfo:
        """Download a single file from B2.

        Args:
            remote_name: Remote file name
            local_path: Local path to save file

        Returns:
            B2FileInfo of downloaded file
        """
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        file_info = self.bucket.get_file_info_by_name(remote_name)

        download_dest = DownloadDestLocalFile(str(local_path))
        self.bucket.download_file_by_name(remote_name, download_dest)

        logger.info(f"Downloaded {remote_name} -> {local_path} ({file_info.size} bytes)")
        return B2FileInfo.from_b2_file(file_info)

    async def delete_file(self, remote_name: str) -> bool:
        """Delete a file from B2.

        Args:
            remote_name: Remote file name

        Returns:
            True if deleted
        """
        try:
            file_info = self.bucket.get_file_info_by_name(remote_name)
            self.bucket.delete_file_version(file_info.id_, remote_name)
            logger.info(f"Deleted: {remote_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {remote_name}: {e}")
            return False

    async def hide_file(self, remote_name: str) -> bool:
        """Hide a file in B2 (soft delete).

        Args:
            remote_name: Remote file name

        Returns:
            True if hidden
        """
        try:
            self.bucket.hide_file(remote_name)
            logger.info(f"Hidden: {remote_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to hide {remote_name}: {e}")
            return False

    async def rename_file(self, old_name: str, new_name: str) -> B2FileInfo | None:
        """Rename a file (B2 uses copy+delete pattern).

        Args:
            old_name: Current file name
            new_name: New file name

        Returns:
            B2FileInfo of new file or None if failed
        """
        try:
            # B2 doesn't support rename directly, need to copy+delete
            old_file = self.bucket.get_file_info_by_name(old_name)

            # Download to temp
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name

            try:
                # Download
                self.bucket.download_file_by_id(old_file.id_, DownloadDestLocalFile(tmp_path))

                # Upload as new name
                new_file = self.bucket.upload_local_file(
                    local_file=tmp_path,
                    file_name=new_name,
                    content_type=old_file.content_type,
                )

                # Delete old
                self.bucket.delete_file_version(old_file.id_, old_name)

                logger.info(f"Renamed: {old_name} -> {new_name}")
                return B2FileInfo.from_b2_file(new_file)

            finally:
                os.unlink(tmp_path)

        except Exception as e:
            logger.error(f"Failed to rename {old_name} -> {new_name}: {e}")
            return None

    async def copy_file(self, source_name: str, dest_name: str) -> B2FileInfo | None:
        """Copy a file within B2.

        Args:
            source_name: Source file name
            dest_name: Destination file name

        Returns:
            B2FileInfo of new file or None if failed
        """
        try:
            source_file = self.bucket.get_file_info_by_name(source_name)

            # Download to temp and upload
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name

            try:
                self.bucket.download_file_by_id(source_file.id_, DownloadDestLocalFile(tmp_path))
                new_file = self.bucket.upload_local_file(
                    local_file=tmp_path,
                    file_name=dest_name,
                    content_type=source_file.content_type,
                )

                logger.info(f"Copied: {source_name} -> {dest_name}")
                return B2FileInfo.from_b2_file(new_file)

            finally:
                os.unlink(tmp_path)

        except Exception as e:
            logger.error(f"Failed to copy {source_name} -> {dest_name}: {e}")
            return None

    # ==========================================================================
    # rclone Operations: Bulk Upload/Download, Sync
    # ==========================================================================

    def _setup_rclone_config(self) -> Path:
        """Setup rclone config file with B2 credentials.

        Returns:
            Path to rclone config file
        """
        import tempfile
        tmp_dir = Path(tempfile.gettempdir())
        config_path = tmp_dir / f"rclone_b2_{os.getpid()}.conf"

        config_content = f"""[b2remote]
type = b2
account = {self.config.key_id}
key = {self.config.application_key}
"""

        config_path.write_text(config_content)
        self._rclone_config_path = config_path
        return config_path

    def _cleanup_rclone_config(self):
        """Cleanup rclone config file."""
        if self._rclone_config_path and self._rclone_config_path.exists():
            self._rclone_config_path.unlink()
            self._rclone_config_path = None

    async def _run_rclone(
        self,
        args: list[str],
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run rclone command.

        Args:
            args: Rclone arguments (without 'rclone' prefix)
            check: Whether to raise exception on non-zero exit

        Returns:
            Completed process result
        """
        config_path = self._setup_rclone_config()

        try:
            cmd = [
                "rclone",
                f"--config={config_path}",
                *args,
            ]

            logger.debug(f"Running: {' '.join(cmd)}")

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate()

            result = subprocess.CompletedProcess(
                args=cmd,
                returncode=proc.returncode,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
            )

            if check and proc.returncode != 0:
                raise RuntimeError(f"rclone failed: {result.stderr}")

            return result

        finally:
            self._cleanup_rclone_config()

    async def bulk_upload(
        self,
        local_dir: str | Path,
        remote_prefix: str = "",
        pattern: str = "*",
        check_existing: bool = False,
        parallel: int = 4,
    ) -> dict:
        """Bulk upload files using rclone.

        Args:
            local_dir: Local directory path
            remote_prefix: Remote prefix/folder
            pattern: File pattern to match
            check_existing: Skip files that exist remotely
            parallel: Number of parallel transfers

        Returns:
            Dict with stats: transferred, errors, etc.
        """
        local_dir = Path(local_dir)
        if not local_dir.exists():
            raise FileNotFoundError(f"Local directory not found: {local_dir}")

        remote_path = f"b2remote:{self.config.bucket_name}/{remote_prefix}".rstrip("/")

        args = [
            "copy",
            str(local_dir),
            remote_path,
            "--progress",
            f"--transfers={parallel}",
            "--b2-upload-cutoff=200M",
            "--b2-chunk-size=8M",
        ]

        if pattern:
            args.extend(["--include", pattern])

        if check_existing:
            args.append("--ignore-existing")

        result = await self._run_rclone(args, check=False)

        # Parse output for stats
        stats = {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

        # Try to parse stats from output
        if "Transferred:" in result.stdout:
            for line in result.stdout.split("\n"):
                if "Transferred:" in line:
                    stats["summary"] = line.strip()

        logger.info(f"Bulk upload completed: {stats.get('success', False)}")
        return stats

    async def bulk_download(
        self,
        remote_prefix: str = "",
        local_dir: str | Path = ".",
        pattern: str = "*",
        parallel: int = 4,
    ) -> dict:
        """Bulk download files using rclone.

        Args:
            remote_prefix: Remote prefix/folder
            local_dir: Local directory path
            pattern: File pattern to match
            parallel: Number of parallel transfers

        Returns:
            Dict with stats
        """
        local_dir = Path(local_dir)
        local_dir.mkdir(parents=True, exist_ok=True)

        remote_path = f"b2remote:{self.config.bucket_name}/{remote_prefix}".rstrip("/")

        args = [
            "copy",
            remote_path,
            str(local_dir),
            "--progress",
            f"--transfers={parallel}",
        ]

        if pattern:
            args.extend(["--include", pattern])

        result = await self._run_rclone(args, check=False)

        stats = {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

        logger.info(f"Bulk download completed: {stats.get('success', False)}")
        return stats

    async def sync(
        self,
        local_dir: str | Path,
        remote_prefix: str = "",
        direction: str = "up",  # up, down, or both
        delete: bool = False,
        parallel: int = 4,
    ) -> dict:
        """Sync files between local and B2 using rclone.

        Args:
            local_dir: Local directory path
            remote_prefix: Remote prefix/folder
            direction: Sync direction (up/down/both)
            delete: Delete files that don't exist at source
            parallel: Number of parallel transfers

        Returns:
            Dict with stats
        """
        local_dir = Path(local_dir)
        local_dir.mkdir(parents=True, exist_ok=True)

        remote_path = f"b2remote:{self.config.bucket_name}/{remote_prefix}".rstrip("/")

        if direction == "up":
            args = ["sync", str(local_dir), remote_path]
        elif direction == "down":
            args = ["sync", remote_path, str(local_dir)]
        else:  # both - two-way sync not supported directly, use sync down then up
            # For two-way, we need bi-directional merge (not true sync)
            return await self._bidirectional_sync(local_dir, remote_prefix, delete, parallel)

        args.extend([
            "--progress",
            f"--transfers={parallel}",
        ])

        if delete:
            args.append("--delete-during")

        result = await self._run_rclone(args, check=False)

        stats = {
            "success": result.returncode == 0,
            "direction": direction,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

        logger.info(f"Sync completed ({direction}): {stats.get('success', False)}")
        return stats

    async def _bidirectional_sync(
        self,
        local_dir: Path,
        remote_prefix: str,
        delete: bool,
        parallel: int,
    ) -> dict:
        """Two-way sync (merge changes both ways).

        Args:
            local_dir: Local directory
            remote_prefix: Remote prefix
            delete: Whether to delete
            parallel: Parallel transfers

        Returns:
            Dict with combined stats
        """
        # Use rclone bisync for two-way sync
        remote_path = f"b2remote:{self.config.bucket_name}/{remote_prefix}".rstrip("/")

        args = [
            "bisync",
            str(local_dir),
            remote_path,
            "--progress",
            f"--transfers={parallel}",
            "--resync",
        ]

        if delete:
            args.append("--remove-source-files")

        result = await self._run_rclone(args, check=False)

        stats = {
            "success": result.returncode == 0,
            "direction": "both",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

        logger.info(f"Two-way sync completed: {stats.get('success', False)}")
        return stats

    async def check_existing(
        self,
        local_dir: str | Path,
        remote_prefix: str = "",
    ) -> list[dict]:
        """Check which local files exist remotely.

        Args:
            local_dir: Local directory
            remote_prefix: Remote prefix

        Returns:
            List of dicts with file status
        """
        local_dir = Path(local_dir)
        if not local_dir.exists():
            raise FileNotFoundError(f"Local directory not found: {local_dir}")

        remote_path = f"b2remote:{self.config.bucket_name}/{remote_prefix}".rstrip("/")

        # Use rclone check to compare
        args = [
            "check",
            str(local_dir),
            remote_path,
            "--one-way",
            "--combined",
        ]

        result = await self._run_rclone(args, check=False)

        # Parse check output
        status = []
        if result.stdout:
            for line in result.stdout.split("\n"):
                if line.strip():
                    # Format: "file_name: OK/MISSING/DIFFERENT"
                    status.append({"line": line})

        return status

    # ==========================================================================
    # Utility Methods
    # ==========================================================================

    async def get_bucket_stats(self) -> dict:
        """Get bucket statistics.

        Returns:
            Dict with file count, total size
        """
        total_files = 0
        total_size = 0

        async for file_info in self.list_files_iter(recursive=True):
            total_files += 1
            total_size += file_info.size

        return {
            "file_count": total_files,
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_size_gb": round(total_size / (1024 * 1024 * 1024), 2),
        }

    async def search_files(
        self,
        pattern: str,
        prefix: str = "",
    ) -> list[B2FileInfo]:
        """Search for files by name pattern.

        Args:
            pattern: Glob pattern to match
            prefix: Prefix to limit search scope

        Returns:
            List of matching files
        """
        import fnmatch

        matches = []
        async for file_info in self.list_files_iter(prefix=prefix, recursive=True):
            if fnmatch.fnmatch(file_info.file_name.lower(), pattern.lower()):
                matches.append(file_info)

        return matches

    def close(self):
        """Close connections and cleanup."""
        self._cleanup_rclone_config()


# Singleton instance for app-wide use
_b2_service: B2StorageService | None = None


def get_b2_service() -> B2StorageService:
    """Get or create B2 storage service singleton."""
    global _b2_service
    if _b2_service is None:
        config = B2Config.from_settings()
        _b2_service = B2StorageService(config)
    return _b2_service
