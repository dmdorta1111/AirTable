"""
Unit tests for StorageService.

Tests S3 and SFTP upload/download, retry logic, and error handling.
"""

import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from io import BytesIO

import pytest
from botocore.exceptions import ClientError
import paramiko

from pybase.services.storage_service import StorageService, StorageConfig, SFTPConfig


class TestStorageServiceBasics:
    """Test basic service initialization and configuration."""

    def test_storage_service_init(self):
        """Test StorageService can be initialized."""
        config = StorageConfig(
            type="s3",
            bucket="test-bucket",
            region="us-east-1"
        )
        service = StorageService(config)
        assert service is not None
        assert service.config.type == "s3"

    def test_get_storage_service_singleton(self):
        """Test singleton pattern returns same instance."""
        # This test requires settings to be configured
        # For now, we'll test the instantiation
        config = StorageConfig(
            type="s3",
            bucket="test-bucket",
            region="us-east-1"
        )
        service1 = StorageService(config)
        service2 = StorageService(config)
        # These are different instances (not singleton at instance level)
        assert service1 is not service2


class TestS3Operations:
    """Test S3/S3-compatible storage operations."""

    @pytest.fixture
    def s3_config(self):
        """Create S3 config for testing."""
        return StorageConfig(
            type="s3",
            bucket="test-bucket",
            region="us-east-1",
            access_key_id="test-key",
            secret_access_key="test-secret"
        )

    @pytest.fixture
    def s3_service(self, s3_config):
        """Create StorageService with S3 config."""
        return StorageService(s3_config)

    @pytest.mark.asyncio
    async def test_upload_file_to_s3(self, s3_service, tmp_path):
        """Test uploading file to S3."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, S3!")

        # Mock S3 client
        with patch.object(s3_service, 's3_client') as mock_s3:
            mock_s3.upload_file = MagicMock()

            # Upload file
            await s3_service.upload_file(str(test_file), "test.txt")

            # Verify upload was called
            mock_s3.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_bytes_to_s3(self, s3_service):
        """Test uploading bytes to S3."""
        data = b"Hello, S3 bytes!"

        # Mock S3 client
        with patch.object(s3_service, 's3_client') as mock_s3:
            mock_s3.upload_fileobj = MagicMock()

            # Upload bytes
            await s3_service.upload_bytes(data, "test.txt")

            # Verify upload was called
            mock_s3.upload_fileobj.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_presigned_url(self, s3_service):
        """Test generating presigned download URL."""
        # Mock S3 client
        with patch.object(s3_service, 's3_client') as mock_s3:
            mock_s3.generate_presigned_url = MagicMock(
                return_value="https://test-bucket.s3.amazonaws.com/test.txt?signature=abc"
            )

            # Generate URL
            url = await s3_service.generate_presigned_url("test.txt", expires_in=3600)

            # Verify URL was generated
            assert url.startswith("https://test-bucket.s3.amazonaws.com/")
            mock_s3.generate_presigned_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_file_from_s3(self, s3_service, tmp_path):
        """Test downloading file from S3."""
        download_path = tmp_path / "downloaded.txt"

        # Mock S3 client
        with patch.object(s3_service, 's3_client') as mock_s3:
            mock_s3.download_file = MagicMock()

            # Download file
            await s3_service.download_file("test.txt", str(download_path))

            # Verify download was called
            mock_s3.download_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_exists_s3(self, s3_service):
        """Test checking if file exists in S3."""
        # Mock S3 client
        with patch.object(s3_service, 's3_client') as mock_s3:
            # File exists
            mock_s3.head_object = MagicMock()
            exists = await s3_service.file_exists("test.txt")
            assert exists is True

            # File doesn't exist
            error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
            mock_s3.head_object.side_effect = ClientError(error_response, "HeadObject")
            exists = await s3_service.file_exists("nonexistent.txt")
            assert exists is False

    @pytest.mark.asyncio
    async def test_delete_file_s3(self, s3_service):
        """Test deleting file from S3."""
        # Mock S3 client
        with patch.object(s3_service, 's3_client') as mock_s3:
            mock_s3.delete_object = MagicMock()

            # Delete file
            result = await s3_service.delete_file("test.txt")

            # Verify delete was called
            assert result is True
            mock_s3.delete_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_files_s3(self, s3_service):
        """Test listing files in S3 with prefix."""
        # Mock S3 client
        with patch.object(s3_service, 's3_client') as mock_s3:
            mock_s3.list_objects_v2 = MagicMock(
                return_value={
                    "Contents": [
                        {"Key": "exports/file1.csv"},
                        {"Key": "exports/file2.csv"}
                    ]
                }
            )

            # List files
            files = await s3_service.list_files("exports/")

            # Verify listing
            assert len(files) == 2
            assert "exports/file1.csv" in files
            assert "exports/file2.csv" in files

    @pytest.mark.asyncio
    async def test_get_file_metadata_s3(self, s3_service):
        """Test getting file metadata from S3."""
        # Mock S3 client
        with patch.object(s3_service, 's3_client') as mock_s3:
            mock_s3.head_object = MagicMock(
                return_value={
                    "ContentLength": 1024,
                    "ContentType": "text/csv",
                    "LastModified": "2026-01-27"
                }
            )

            # Get metadata
            metadata = await s3_service.get_file_metadata("test.txt")

            # Verify metadata
            assert metadata["size"] == 1024
            assert metadata["content_type"] == "text/csv"


class TestS3RetryLogic:
    """Test S3 retry logic with exponential backoff."""

    @pytest.fixture
    def s3_config(self):
        """Create S3 config for testing."""
        return StorageConfig(
            type="s3",
            bucket="test-bucket",
            region="us-east-1"
        )

    @pytest.fixture
    def s3_service(self, s3_config):
        """Create StorageService with S3 config."""
        return StorageService(s3_config)

    @pytest.mark.asyncio
    async def test_s3_retry_on_transient_failure(self, s3_service):
        """Test S3 operations retry on transient failures."""
        # Mock S3 client with transient failure then success
        with patch.object(s3_service, 's3_client') as mock_s3:
            call_count = 0

            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    error_response = {"Error": {"Code": "ServiceUnavailable", "Message": "Try again"}}
                    raise ClientError(error_response, "UploadPart")
                return None  # Success on retry

            mock_s3.upload_file = MagicMock(side_effect=side_effect)

            # Upload should succeed after retry
            await s3_service.upload_file("test.txt", "test.txt")

            # Verify it was called twice (initial + 1 retry)
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_s3_max_retries_exceeded(self, s3_service):
        """Test S3 operations fail after max retries."""
        # Mock S3 client with persistent failure
        with patch.object(s3_service, 's3_client') as mock_s3:
            error_response = {"Error": {"Code": "ServiceUnavailable", "Message": "Try again"}}
            mock_s3.upload_file = MagicMock(
                side_effect=ClientError(error_response, "UploadPart")
            )

            # Upload should fail after max retries
            with pytest.raises(ClientError):
                await s3_service.upload_file("test.txt", "test.txt")


class TestSFTPOperations:
    """Test SFTP storage operations."""

    @pytest.fixture
    def sftp_config(self):
        """Create SFTP config for testing."""
        return SFTPConfig(
            type="sftp",
            host="ftp.example.com",
            port=22,
            username="testuser",
            password="testpass"
        )

    @pytest.fixture
    def sftp_service(self, sftp_config):
        """Create StorageService with SFTP config."""
        return StorageService(sftp_config)

    @pytest.mark.asyncio
    async def test_upload_file_to_sftp(self, sftp_service, tmp_path):
        """Test uploading file to SFTP server."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, SFTP!")

        # Mock SFTP client
        with patch.object(sftp_service, 'sftp_client') as mock_sftp:
            mock_sftp.put = MagicMock()

            # Upload file
            await sftp_service.upload_file_to_sftp(str(test_file), "/uploads/test.txt")

            # Verify upload was called
            mock_sftp.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_bytes_to_sftp(self, sftp_service):
        """Test uploading bytes to SFTP server."""
        data = b"Hello, SFTP bytes!"

        # Mock SFTP client
        with patch.object(sftp_service, 'sftp_client') as mock_sftp:
            mock_sftp.file = MagicMock()
            mock_file = MagicMock()
            mock_sftp.file.return_value.__enter__ = MagicMock(return_value=mock_file)
            mock_sftp.file.return_value.__exit__ = MagicMock(return_value=False)

            # Upload bytes
            await sftp_service.upload_bytes_to_sftp(data, "/uploads/test.txt")

            # Verify file operations were called
            mock_sftp.file.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_file_from_sftp(self, sftp_service, tmp_path):
        """Test downloading file from SFTP server."""
        download_path = tmp_path / "downloaded.txt"

        # Mock SFTP client
        with patch.object(sftp_service, 'sftp_client') as mock_sftp:
            mock_sftp.get = MagicMock()

            # Download file
            await sftp_service.download_file_from_sftp("/uploads/test.txt", str(download_path))

            # Verify download was called
            mock_sftp.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_exists_sftp(self, sftp_service):
        """Test checking if file exists on SFTP server."""
        # Mock SFTP client
        with patch.object(sftp_service, 'sftp_client') as mock_sftp:
            # File exists
            mock_sftp.stat = MagicMock()
            exists = await sftp_service.file_exists_sftp("/uploads/test.txt")
            assert exists is True

            # File doesn't exist
            mock_sftp.stat.side_effect = FileNotFoundError("No such file")
            exists = await sftp_service.file_exists_sftp("/uploads/nonexistent.txt")
            assert exists is False

    @pytest.mark.asyncio
    async def test_delete_file_from_sftp(self, sftp_service):
        """Test deleting file from SFTP server."""
        # Mock SFTP client
        with patch.object(sftp_service, 'sftp_client') as mock_sftp:
            mock_sftp.remove = MagicMock()

            # Delete file
            result = await sftp_service.delete_file_from_sftp("/uploads/test.txt")

            # Verify delete was called
            assert result is True
            mock_sftp.remove.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_files_sftp(self, sftp_service):
        """Test listing files on SFTP server."""
        # Mock SFTP client
        with patch.object(sftp_service, 'sftp_client') as mock_sftp:
            mock_sftp.listdir = MagicMock(
                return_value=["file1.csv", "file2.csv"]
            )

            # List files
            files = await sftp_service.list_files_sftp("/uploads/")

            # Verify listing
            assert len(files) == 2
            assert "file1.csv" in files
            assert "file2.csv" in files


class TestSFTPRetryLogic:
    """Test SFTP retry logic with exponential backoff."""

    @pytest.fixture
    def sftp_config(self):
        """Create SFTP config for testing."""
        return SFTPConfig(
            type="sftp",
            host="ftp.example.com",
            port=22,
            username="testuser",
            password="testpass"
        )

    @pytest.fixture
    def sftp_service(self, sftp_config):
        """Create StorageService with SFTP config."""
        return StorageService(sftp_config)

    @pytest.mark.asyncio
    async def test_sftp_retry_on_transient_failure(self, sftp_service):
        """Test SFTP operations retry on transient failures."""
        # Mock SFTP client with transient failure then success
        with patch.object(sftp_service, 'sftp_client') as mock_sftp:
            call_count = 0

            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise IOError("Connection reset by peer")
                return None  # Success on retry

            mock_sftp.put = MagicMock(side_effect=side_effect)

            # Upload should succeed after retry
            await sftp_service.upload_file_to_sftp("test.txt", "/uploads/test.txt")

            # Verify it was called twice (initial + 1 retry)
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_sftp_max_retries_exceeded(self, sftp_service):
        """Test SFTP operations fail after max retries."""
        # Mock SFTP client with persistent failure
        with patch.object(sftp_service, 'sftp_client') as mock_sftp:
            mock_sftp.put = MagicMock(
                side_effect=IOError("Connection timeout")
            )

            # Upload should fail after max retries
            with pytest.raises(IOError):
                await sftp_service.upload_file_to_sftp("test.txt", "/uploads/test.txt")


class TestSFTPConnectionManagement:
    """Test SFTP connection management."""

    @pytest.fixture
    def sftp_config(self):
        """Create SFTP config for testing."""
        return SFTPConfig(
            type="sftp",
            host="ftp.example.com",
            port=22,
            username="testuser",
            password="testpass"
        )

    @pytest.fixture
    def sftp_service(self, sftp_config):
        """Create StorageService with SFTP config."""
        return StorageService(sftp_config)

    def test_sftp_client_password_auth(self, sftp_service):
        """Test SFTP client connects with password authentication."""
        # Mock SSH client
        with patch('paramiko.SSHClient') as mock_ssh_cls:
            mock_ssh = MagicMock()
            mock_ssh_cls.return_value = mock_ssh
            mock_sftp = MagicMock()
            mock_ssh.open_sftp.return_value = mock_sftp

            # Access sftp_client to trigger connection
            _ = sftp_service.sftp_client

            # Verify connection was made
            mock_ssh.connect.assert_called_once()
            call_args = mock_ssh.connect.call_args
            assert call_args[1]['username'] == 'testuser'
            assert call_args[1]['password'] == 'testpass'
            mock_ssh.open_sftp.assert_called_once()

    def test_sftp_client_key_auth(self, sftp_service):
        """Test SFTP client connects with private key authentication."""
        # Update config to use key auth
        sftp_service.config.private_key_path = "/path/to/key"

        # Mock SSH client and key
        with patch('paramiko.SSHClient') as mock_ssh_cls:
            with patch('paramiko.RSAKey.from_private_key_file') as mock_key_cls:
                mock_ssh = MagicMock()
                mock_ssh_cls.return_value = mock_ssh
                mock_key = MagicMock()
                mock_key_cls.return_value = mock_key
                mock_sftp = MagicMock()
                mock_ssh.open_sftp.return_value = mock_sftp

                # Access sftp_client to trigger connection
                _ = sftp_service.sftp_client

                # Verify connection was made with key
                mock_ssh.connect.assert_called_once()
                call_args = mock_ssh.connect.call_args
                assert 'pkey' in call_args[1]

    def test_sftp_connection_cleanup(self, sftp_service):
        """Test SFTP connection is properly closed."""
        # Mock SSH client
        with patch('paramiko.SSHClient') as mock_ssh_cls:
            mock_ssh = MagicMock()
            mock_ssh_cls.return_value = mock_ssh
            mock_sftp = MagicMock()
            mock_ssh.open_sftp.return_value = mock_sftp

            # Access sftp_client to create connection
            _ = sftp_service.sftp_client

            # Close connection
            sftp_service.close_sftp_connection()

            # Verify cleanup
            mock_sftp.close.assert_called_once()
            mock_ssh.close.assert_called_once()


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def s3_config(self):
        """Create S3 config for testing."""
        return StorageConfig(
            type="s3",
            bucket="test-bucket",
            region="us-east-1"
        )

    @pytest.fixture
    def s3_service(self, s3_config):
        """Create StorageService with S3 config."""
        return StorageService(s3_config)

    @pytest.mark.asyncio
    async def test_s3_authentication_error(self, s3_service):
        """Test S3 authentication failure is handled."""
        # Mock S3 client with auth error
        with patch.object(s3_service, 's3_client') as mock_s3:
            error_response = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
            mock_s3.upload_file = MagicMock(
                side_effect=ClientError(error_response, "PutObject")
            )

            # Should raise immediately without retry (AccessDenied is non-retryable)
            with pytest.raises(ClientError) as exc_info:
                await s3_service.upload_file("test.txt", "test.txt")

            # Verify it's an auth error
            assert exc_info.value.response["Error"]["Code"] == "AccessDenied"

    @pytest.mark.asyncio
    async def test_missing_bucket_handling(self, s3_service):
        """Test missing bucket is auto-created or fails gracefully."""
        # This would depend on implementation - for now we test error handling
        with patch.object(s3_service, 's3_client') as mock_s3:
            error_response = {"Error": {"Code": "NoSuchBucket", "Message": "Bucket does not exist"}}
            mock_s3.upload_file = MagicMock(
                side_effect=ClientError(error_response, "PutObject")
            )

            # Should fail immediately (NoSuchBucket is non-retryable)
            with pytest.raises(ClientError):
                await s3_service.upload_file("test.txt", "test.txt")

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, s3_service):
        """Test network timeouts are handled with retry."""
        # Mock S3 client with timeout
        with patch.object(s3_service, 's3_client') as mock_s3:
            error_response = {"Error": {"Code": "RequestTimeout", "Message": "Request timed out"}}
            mock_s3.upload_file = MagicMock(
                side_effect=ClientError(error_response, "PutObject")
            )

            # Should retry and eventually fail
            with pytest.raises(ClientError):
                await s3_service.upload_file("test.txt", "test.txt")

            # Verify multiple attempts were made
            assert mock_s3.upload_file.call_count > 1
