"""
Storage service for S3/S3-compatible object storage and SFTP operations.

Provides upload, download, and management operations for S3 and S3-compatible
storage (MinIO, AWS S3, etc.) and SFTP servers used for export file storage.
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import boto3
import paramiko
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from pybase.core.config import settings

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds


def _retry_with_backoff(
    func: Any,
    *args: Any,
    max_retries: int = MAX_RETRIES,
    base_delay: float = BASE_DELAY,
    **kwargs: Any,
) -> Any:
    """
    Execute function with exponential backoff retry.

    Args:
        func: Function to execute
        *args: Function arguments
        max_retries: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    import time

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            last_exception = e
            error_code = e.response.get("Error", {}).get("Code", "")

            # Don't retry on certain errors
            if error_code in ["NoSuchBucket", "AccessDenied", "Unauthorized"]:
                logger.error(f"Non-retryable S3 error: {error_code} - {e}")
                raise

            if attempt == max_retries:
                logger.error(f"Retry failed after {max_retries} attempts: {e}")
                raise

            # Calculate delay with exponential backoff
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay:.1f}s: {e}")
            time.sleep(delay)

    raise last_exception


def _retry_sftp_with_backoff(
    func: Any,
    *args: Any,
    max_retries: int = MAX_RETRIES,
    base_delay: float = BASE_DELAY,
    **kwargs: Any,
) -> Any:
    """
    Execute SFTP function with exponential backoff retry.

    Args:
        func: Function to execute
        *args: Function arguments
        max_retries: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff
        **kwargs: Function keyword arguments

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    import time

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except (paramiko.SSHException, OSError) as e:
            last_exception = e

            if attempt == max_retries:
                logger.error(f"SFTP retry failed after {max_retries} attempts: {e}")
                raise

            # Calculate delay with exponential backoff
            delay = base_delay * (2 ** attempt)
            logger.warning(f"SFTP retry {attempt + 1}/{max_retries} after {delay:.1f}s: {e}")
            time.sleep(delay)

    raise last_exception


@dataclass
class StorageConfig:
    """S3 storage configuration."""

    endpoint_url: Optional[str]
    access_key: str
    secret_key: str
    bucket_name: str
    region: str

    @classmethod
    def from_settings(cls) -> "StorageConfig":
        """Create config from application settings."""
        return cls(
            endpoint_url=settings.s3_endpoint_url,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            bucket_name=settings.s3_bucket_name,
            region=settings.s3_region,
        )


@dataclass
class SFTPConfig:
    """SFTP storage configuration."""

    host: str
    port: int
    username: str
    password: Optional[str]
    private_key_path: Optional[str]
    base_path: str

    @classmethod
    def from_settings(cls) -> "SFTPConfig":
        """Create config from application settings."""
        return cls(
            host=getattr(settings, "sftp_host", ""),
            port=getattr(settings, "sftp_port", 22),
            username=getattr(settings, "sftp_username", ""),
            password=getattr(settings, "sftp_password", None),
            private_key_path=getattr(settings, "sftp_private_key_path", None),
            base_path=getattr(settings, "sftp_base_path", "/uploads"),
        )


class StorageService:
    """Service for S3/S3-compatible storage and SFTP operations."""

    def __init__(
        self,
        config: Optional[StorageConfig] = None,
        sftp_config: Optional[SFTPConfig] = None,
    ) -> None:
        """Initialize storage service.

        Args:
            config: S3 storage configuration. If None, loads from settings.
            sftp_config: SFTP storage configuration. If None, loads from settings.
        """
        self.config = config or StorageConfig.from_settings()
        self.sftp_config = sftp_config or SFTPConfig.from_settings()
        self._s3_client: Optional[BaseClient] = None
        self._sftp_client: Optional[paramiko.SFTPClient] = None
        self._ssh_client: Optional[paramiko.SSHClient] = None
        self._ensure_bucket_exists()

    @property
    def s3_client(self) -> BaseClient:
        """Get or create S3 client.

        Returns:
            S3 client instance

        Raises:
            RuntimeError: If S3 configuration is invalid
        """
        if self._s3_client is None:
            if not self.config.access_key or not self.config.secret_key:
                raise RuntimeError("S3 access key and secret key are required")

            client_kwargs: dict[str, Any] = {
                "aws_access_key_id": self.config.access_key,
                "aws_secret_access_key": self.config.secret_key,
                "region_name": self.config.region,
            }

            # Add endpoint_url for S3-compatible storage (MinIO, etc.)
            if self.config.endpoint_url:
                client_kwargs["endpoint_url"] = self.config.endpoint_url

            self._s3_client = boto3.client("s3", **client_kwargs)

        return self._s3_client

    def _ensure_bucket_exists(self) -> None:
        """Ensure the S3 bucket exists, create if not."""
        try:
            _retry_with_backoff(
                self.s3_client.head_bucket,
                Bucket=self.config.bucket_name,
            )
            logger.debug(f"Bucket {self.config.bucket_name} exists")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")

            if error_code == "404" or error_code == "NoSuchBucket":
                logger.info(f"Bucket {self.config.bucket_name} not found, creating...")
                try:
                    _retry_with_backoff(
                        self.s3_client.create_bucket,
                        Bucket=self.config.bucket_name,
                    )
                    logger.info(f"Created bucket {self.config.bucket_name}")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    raise
            else:
                logger.error(f"Error checking bucket: {e}")
                raise

    def upload_file(
        self,
        file_path: str | Path,
        object_key: str,
        metadata: Optional[dict[str, str]] = None,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload a file to S3 storage.

        Args:
            file_path: Path to file to upload
            object_key: S3 object key (path in bucket)
            metadata: Optional metadata to attach to object
            content_type: Optional content type

        Returns:
            The object key

        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If upload fails
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            extra_args: dict[str, Any] = {}
            if metadata:
                extra_args["Metadata"] = metadata
            if content_type:
                extra_args["ContentType"] = content_type

            _retry_with_backoff(
                self.s3_client.upload_file,
                str(file_path),
                self.config.bucket_name,
                object_key,
                ExtraArgs=extra_args if extra_args else None,
            )

            logger.info(f"Uploaded {file_path.name} to {object_key}")
            return object_key

        except ClientError as e:
            logger.error(f"Failed to upload file: {e}")
            raise RuntimeError(f"S3 upload failed: {e}") from e

    def upload_bytes(
        self,
        data: bytes,
        object_key: str,
        metadata: Optional[dict[str, str]] = None,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload bytes to S3 storage.

        Args:
            data: Bytes data to upload
            object_key: S3 object key (path in bucket)
            metadata: Optional metadata to attach to object
            content_type: Optional content type

        Returns:
            The object key

        Raises:
            RuntimeError: If upload fails
        """
        try:
            extra_args: dict[str, Any] = {}
            if metadata:
                extra_args["Metadata"] = metadata
            if content_type:
                extra_args["ContentType"] = content_type

            _retry_with_backoff(
                self.s3_client.put_object,
                Bucket=self.config.bucket_name,
                Key=object_key,
                Body=data,
                **extra_args,
            )

            logger.info(f"Uploaded {len(data)} bytes to {object_key}")
            return object_key

        except ClientError as e:
            logger.error(f"Failed to upload bytes: {e}")
            raise RuntimeError(f"S3 upload failed: {e}") from e

    def download_file(
        self,
        object_key: str,
        file_path: str | Path,
    ) -> Path:
        """Download a file from S3 storage.

        Args:
            object_key: S3 object key to download
            file_path: Local path to save file

        Returns:
            Path to downloaded file

        Raises:
            RuntimeError: If download fails
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            _retry_with_backoff(
                self.s3_client.download_file,
                self.config.bucket_name,
                object_key,
                str(file_path),
            )

            logger.info(f"Downloaded {object_key} to {file_path}")
            return file_path

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404" or error_code == "NoSuchKey":
                raise RuntimeError(f"Object not found: {object_key}") from e

            logger.error(f"Failed to download file: {e}")
            raise RuntimeError(f"S3 download failed: {e}") from e

    def download_bytes(self, object_key: str) -> bytes:
        """Download object as bytes from S3 storage.

        Args:
            object_key: S3 object key to download

        Returns:
            Bytes data

        Raises:
            RuntimeError: If download fails
        """
        try:
            response = _retry_with_backoff(
                self.s3_client.get_object,
                Bucket=self.config.bucket_name,
                Key=object_key,
            )

            data = response["Body"].read()
            logger.info(f"Downloaded {len(data)} bytes from {object_key}")
            return data

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404" or error_code == "NoSuchKey":
                raise RuntimeError(f"Object not found: {object_key}") from e

            logger.error(f"Failed to download bytes: {e}")
            raise RuntimeError(f"S3 download failed: {e}") from e

    def generate_presigned_url(
        self,
        object_key: str,
        expiration_seconds: int = 3600,
    ) -> str:
        """Generate a presigned URL for temporary access.

        Args:
            object_key: S3 object key
            expiration_seconds: URL expiration time in seconds (default: 1 hour)

        Returns:
            Presigned URL string

        Raises:
            RuntimeError: If URL generation fails
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.config.bucket_name,
                    "Key": object_key,
                },
                ExpiresIn=expiration_seconds,
            )

            logger.debug(f"Generated presigned URL for {object_key}")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise RuntimeError(f"Failed to generate presigned URL: {e}") from e

    def delete_file(self, object_key: str) -> bool:
        """Delete a file from S3 storage.

        Args:
            object_key: S3 object key to delete

        Returns:
            True if deleted successfully

        Raises:
            RuntimeError: If deletion fails
        """
        try:
            _retry_with_backoff(
                self.s3_client.delete_object,
                Bucket=self.config.bucket_name,
                Key=object_key,
            )

            logger.info(f"Deleted {object_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete file: {e}")
            raise RuntimeError(f"S3 deletion failed: {e}") from e

    def list_files(
        self,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> list[dict[str, Any]]:
        """List files in bucket with optional prefix.

        Args:
            prefix: Object key prefix to filter
            max_keys: Maximum number of keys to return

        Returns:
            List of object info dicts with keys: Key, LastModified, Size, ETag

        Raises:
            RuntimeError: If listing fails
        """
        try:
            response = _retry_with_backoff(
                self.s3_client.list_objects_v2,
                Bucket=self.config.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys,
            )

            objects = response.get("Contents", [])
            logger.debug(f"Listed {len(objects)} objects with prefix '{prefix}'")
            return objects

        except ClientError as e:
            logger.error(f"Failed to list files: {e}")
            raise RuntimeError(f"S3 list failed: {e}") from e

    def file_exists(self, object_key: str) -> bool:
        """Check if a file exists in S3 storage.

        Args:
            object_key: S3 object key to check

        Returns:
            True if object exists
        """
        try:
            _retry_with_backoff(
                self.s3_client.head_object,
                Bucket=self.config.bucket_name,
                Key=object_key,
            )
            return True

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404" or error_code == "NoSuchKey":
                return False
            logger.error(f"Failed to check file existence: {e}")
            return False

    def get_file_metadata(self, object_key: str) -> dict[str, Any]:
        """Get metadata for a file in S3 storage.

        Args:
            object_key: S3 object key

        Returns:
            Metadata dict with keys: ContentLength, ContentType, Metadata, LastModified

        Raises:
            RuntimeError: If metadata retrieval fails
            FileNotFoundError: If object doesn't exist
        """
        try:
            response = _retry_with_backoff(
                self.s3_client.head_object,
                Bucket=self.config.bucket_name,
                Key=object_key,
            )

            metadata = {
                "ContentLength": response.get("ContentLength", 0),
                "ContentType": response.get("ContentType", ""),
                "Metadata": response.get("Metadata", {}),
                "LastModified": response.get("LastModified"),
            }

            return metadata

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404" or error_code == "NoSuchKey":
                raise FileNotFoundError(f"Object not found: {object_key}") from e

            logger.error(f"Failed to get file metadata: {e}")
            raise RuntimeError(f"Failed to get metadata: {e}") from e

    @property
    def sftp_client(self) -> paramiko.SFTPClient:
        """Get or create SFTP client.

        Returns:
            SFTP client instance

        Raises:
            RuntimeError: If SFTP configuration is invalid
        """
        if self._sftp_client is None:
            if not self.sftp_config.host or not self.sftp_config.username:
                raise RuntimeError("SFTP host and username are required")

            # Create SSH client
            self._ssh_client = paramiko.SSHClient()
            self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Connect using password or private key
            try:
                if self.sftp_config.private_key_path:
                    # Use private key authentication
                    private_key = paramiko.RSAKey.from_private_key_file(
                        self.sftp_config.private_key_path
                    )
                    _retry_sftp_with_backoff(
                        self._ssh_client.connect,
                        hostname=self.sftp_config.host,
                        port=self.sftp_config.port,
                        username=self.sftp_config.username,
                        pkey=private_key,
                        timeout=30,
                    )
                elif self.sftp_config.password:
                    # Use password authentication
                    _retry_sftp_with_backoff(
                        self._ssh_client.connect,
                        hostname=self.sftp_config.host,
                        port=self.sftp_config.port,
                        username=self.sftp_config.username,
                        password=self.sftp_config.password,
                        timeout=30,
                    )
                else:
                    raise RuntimeError("SFTP password or private key path is required")

                # Open SFTP client
                self._sftp_client = self._ssh_client.open_sftp()
                logger.debug(f"Connected to SFTP server {self.sftp_config.host}")

            except (paramiko.SSHException, OSError) as e:
                logger.error(f"Failed to connect to SFTP server: {e}")
                raise RuntimeError(f"SFTP connection failed: {e}") from e

        return self._sftp_client

    def upload_file_to_sftp(
        self,
        file_path: str | Path,
        remote_path: str,
    ) -> str:
        """Upload a file to SFTP server.

        Args:
            file_path: Path to local file to upload
            remote_path: Remote path on SFTP server (relative to base_path)

        Returns:
            Full remote path

        Raises:
            FileNotFoundError: If local file doesn't exist
            RuntimeError: If upload fails
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Combine base_path with remote_path
        full_remote_path = f"{self.sftp_config.base_path.rstrip('/')}/{remote_path.lstrip('/')}"

        try:
            # Ensure remote directory exists
            remote_dir = str(Path(full_remote_path).parent)
            try:
                self.sftp_client.stat(remote_dir)
            except FileNotFoundError:
                # Create directory recursively
                self._ensure_remote_dir(remote_dir)

            # Upload file
            _retry_sftp_with_backoff(
                self.sftp_client.put,
                str(file_path),
                full_remote_path,
            )

            logger.info(f"Uploaded {file_path.name} to SFTP://{full_remote_path}")
            return full_remote_path

        except (paramiko.SSHException, OSError) as e:
            logger.error(f"Failed to upload file to SFTP: {e}")
            raise RuntimeError(f"SFTP upload failed: {e}") from e

    def upload_bytes_to_sftp(
        self,
        data: bytes,
        remote_path: str,
    ) -> str:
        """Upload bytes to SFTP server.

        Args:
            data: Bytes data to upload
            remote_path: Remote path on SFTP server (relative to base_path)

        Returns:
            Full remote path

        Raises:
            RuntimeError: If upload fails
        """
        # Combine base_path with remote_path
        full_remote_path = f"{self.sftp_config.base_path.rstrip('/')}/{remote_path.lstrip('/')}"

        try:
            # Ensure remote directory exists
            remote_dir = str(Path(full_remote_path).parent)
            try:
                self.sftp_client.stat(remote_dir)
            except FileNotFoundError:
                # Create directory recursively
                self._ensure_remote_dir(remote_dir)

            # Upload bytes using temporary file-like object
            from io import BytesIO

            with BytesIO(data) as bio:
                _retry_sftp_with_backoff(
                    self.sftp_client.putfo,
                    bio,
                    full_remote_path,
                )

            logger.info(f"Uploaded {len(data)} bytes to SFTP://{full_remote_path}")
            return full_remote_path

        except (paramiko.SSHException, OSError) as e:
            logger.error(f"Failed to upload bytes to SFTP: {e}")
            raise RuntimeError(f"SFTP upload failed: {e}") from e

    def download_file_from_sftp(
        self,
        remote_path: str,
        file_path: str | Path,
    ) -> Path:
        """Download a file from SFTP server.

        Args:
            remote_path: Remote path on SFTP server (relative to base_path)
            file_path: Local path to save file

        Returns:
            Path to downloaded file

        Raises:
            RuntimeError: If download fails
            FileNotFoundError: If remote file doesn't exist
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Combine base_path with remote_path
        full_remote_path = f"{self.sftp_config.base_path.rstrip('/')}/{remote_path.lstrip('/')}"

        try:
            _retry_sftp_with_backoff(
                self.sftp_client.get,
                full_remote_path,
                str(file_path),
            )

            logger.info(f"Downloaded SFTP://{full_remote_path} to {file_path}")
            return file_path

        except FileNotFoundError as e:
            logger.error(f"Remote file not found: {full_remote_path}")
            raise FileNotFoundError(f"Remote file not found: {remote_path}") from e
        except (paramiko.SSHException, OSError) as e:
            logger.error(f"Failed to download file from SFTP: {e}")
            raise RuntimeError(f"SFTP download failed: {e}") from e

    def download_bytes_from_sftp(self, remote_path: str) -> bytes:
        """Download file as bytes from SFTP server.

        Args:
            remote_path: Remote path on SFTP server (relative to base_path)

        Returns:
            Bytes data

        Raises:
            RuntimeError: If download fails
            FileNotFoundError: If remote file doesn't exist
        """
        # Combine base_path with remote_path
        full_remote_path = f"{self.sftp_config.base_path.rstrip('/')}/{remote_path.lstrip('/')}"

        try:
            from io import BytesIO

            with BytesIO() as bio:
                _retry_sftp_with_backoff(
                    self.sftp_client.getfo,
                    full_remote_path,
                    bio,
                )
                data = bio.getvalue()

            logger.info(f"Downloaded {len(data)} bytes from SFTP://{full_remote_path}")
            return data

        except FileNotFoundError as e:
            logger.error(f"Remote file not found: {full_remote_path}")
            raise FileNotFoundError(f"Remote file not found: {remote_path}") from e
        except (paramiko.SSHException, OSError) as e:
            logger.error(f"Failed to download bytes from SFTP: {e}")
            raise RuntimeError(f"SFTP download failed: {e}") from e

    def delete_file_from_sftp(self, remote_path: str) -> bool:
        """Delete a file from SFTP server.

        Args:
            remote_path: Remote path on SFTP server (relative to base_path)

        Returns:
            True if deleted successfully

        Raises:
            RuntimeError: If deletion fails
        """
        # Combine base_path with remote_path
        full_remote_path = f"{self.sftp_config.base_path.rstrip('/')}/{remote_path.lstrip('/')}"

        try:
            _retry_sftp_with_backoff(
                self.sftp_client.remove,
                full_remote_path,
            )

            logger.info(f"Deleted SFTP://{full_remote_path}")
            return True

        except FileNotFoundError:
            logger.warning(f"Remote file not found (already deleted?): {full_remote_path}")
            return True
        except (paramiko.SSHException, OSError) as e:
            logger.error(f"Failed to delete file from SFTP: {e}")
            raise RuntimeError(f"SFTP deletion failed: {e}") from e

    def file_exists_sftp(self, remote_path: str) -> bool:
        """Check if a file exists on SFTP server.

        Args:
            remote_path: Remote path on SFTP server (relative to base_path)

        Returns:
            True if file exists
        """
        # Combine base_path with remote_path
        full_remote_path = f"{self.sftp_config.base_path.rstrip('/')}/{remote_path.lstrip('/')}"

        try:
            self.sftp_client.stat(full_remote_path)
            return True
        except FileNotFoundError:
            return False
        except (paramiko.SSHException, OSError) as e:
            logger.error(f"Failed to check file existence on SFTP: {e}")
            return False

    def list_files_sftp(
        self,
        prefix: str = "",
    ) -> list[dict[str, Any]]:
        """List files on SFTP server with optional prefix.

        Args:
            prefix: Path prefix to filter (relative to base_path)

        Returns:
            List of file info dicts with keys: filename, st_size, st_mtime

        Raises:
            RuntimeError: If listing fails
        """
        # Combine base_path with prefix
        full_path = f"{self.sftp_config.base_path.rstrip('/')}/{prefix.lstrip('/')}"

        try:
            files = []
            for entry in _retry_sftp_with_backoff(
                self.sftp_client.listdir_attr,
                full_path if full_path != self.sftp_config.base_path.rstrip('/') else self.sftp_config.base_path,
            ):
                files.append({
                    "filename": entry.filename,
                    "st_size": entry.st_size,
                    "st_mtime": entry.st_mtime,
                })

            logger.debug(f"Listed {len(files)} files with prefix '{prefix}'")
            return files

        except (paramiko.SSHException, OSError) as e:
            logger.error(f"Failed to list files on SFTP: {e}")
            raise RuntimeError(f"SFTP list failed: {e}") from e

    def _ensure_remote_dir(self, remote_dir: str) -> None:
        """Ensure remote directory exists, create if not.

        Args:
            remote_dir: Remote directory path (absolute)
        """
        if remote_dir == "/":
            return

        # Try to stat parent directory
        parent_dir = str(Path(remote_dir).parent)
        try:
            self.sftp_client.stat(parent_dir)
        except FileNotFoundError:
            # Recursively create parent
            self._ensure_remote_dir(parent_dir)

        # Try to create the directory
        try:
            self.sftp_client.mkdir(remote_dir)
        except OSError:
            # Directory might already exist or was created by another process
            pass

    def close_sftp_connection(self) -> None:
        """Close SFTP and SSH connections."""
        if self._sftp_client:
            try:
                self._sftp_client.close()
                logger.debug("SFTP client closed")
            except Exception as e:
                logger.warning(f"Error closing SFTP client: {e}")
            finally:
                self._sftp_client = None

        if self._ssh_client:
            try:
                self._ssh_client.close()
                logger.debug("SSH client closed")
            except Exception as e:
                logger.warning(f"Error closing SSH client: {e}")
            finally:
                self._ssh_client = None


# Singleton instance for convenience
_default_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get the default storage service instance.

    Returns:
        Storage service instance
    """
    global _default_storage_service
    if _default_storage_service is None:
        _default_storage_service = StorageService()
    return _default_storage_service
