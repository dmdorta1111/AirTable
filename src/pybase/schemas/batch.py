"""Batch record operation schemas for request/response validation."""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from pybase.schemas.record import RecordCreate, RecordResponse, RecordUpdate


# --- Request Schemas ---


class BatchRecordCreate(BaseModel):
    """Schema for batch record creation."""

    records: list[RecordCreate] = Field(
        ..., description="List of records to create", min_length=1, max_length=100
    )

    @field_validator("records")
    @classmethod
    def validate_batch_size(cls, v: list[RecordCreate]) -> list[RecordCreate]:
        """Validate batch size does not exceed maximum."""
        if len(v) > 100:
            raise ValueError("Batch size cannot exceed 100 records")
        if len(v) == 0:
            raise ValueError("Batch must contain at least 1 record")
        return v


class RecordUpdateItem(BaseModel):
    """Schema for a single record update in a batch."""

    record_id: str = Field(..., description="ID of the record to update")
    data: Optional[dict[str, Any]] = Field(None, description="Field values as {field_id: value}")
    row_height: Optional[int] = Field(None, ge=16, le=400, description="Row height in pixels")


class BatchRecordUpdate(BaseModel):
    """Schema for batch record updates."""

    records: list[RecordUpdateItem] = Field(
        ..., description="List of records to update", min_length=1, max_length=100
    )

    @field_validator("records")
    @classmethod
    def validate_batch_size(cls, v: list[RecordUpdateItem]) -> list[RecordUpdateItem]:
        """Validate batch size does not exceed maximum."""
        if len(v) > 100:
            raise ValueError("Batch size cannot exceed 100 records")
        if len(v) == 0:
            raise ValueError("Batch must contain at least 1 record")
        return v


class BatchRecordDelete(BaseModel):
    """Schema for batch record deletion."""

    record_ids: list[str] = Field(
        ..., description="List of record IDs to delete", min_length=1, max_length=100
    )

    @field_validator("record_ids")
    @classmethod
    def validate_batch_size(cls, v: list[str]) -> list[str]:
        """Validate batch size does not exceed maximum."""
        if len(v) > 100:
            raise ValueError("Batch size cannot exceed 100 records")
        if len(v) == 0:
            raise ValueError("Batch must contain at least 1 record")
        return v


# --- Response Schemas ---


class RecordOperationResult(BaseModel):
    """Result of a single record operation in a batch."""

    record_id: Optional[str] = Field(None, description="ID of the record (for updates/deletes)")
    success: bool = Field(..., description="Whether the operation succeeded")
    record: Optional[RecordResponse] = Field(None, description="Record data if operation succeeded")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    error_code: Optional[str] = Field(
        None, description="Error code for programmatic error handling"
    )


class BatchOperationResponse(BaseModel):
    """Response schema for batch record operations."""

    total: int = Field(..., description="Total number of operations attempted")
    successful: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    results: list[RecordOperationResult] = Field(
        ..., description="Individual operation results in order"
    )
