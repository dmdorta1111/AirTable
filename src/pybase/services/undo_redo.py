"""Undo/Redo service for managing operation history."""

import json
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import and_, delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from pybase.models.field import Field
from pybase.models.operation_log import OperationLog
from pybase.models.record import Record
from pybase.models.view import View
from pybase.schemas.operation_log import OperationLogCreate


class UndoRedoService:
    """Service for undo/redo operations."""

    # Operation types
    OPERATION_CREATE = "create"
    OPERATION_UPDATE = "update"
    OPERATION_DELETE = "delete"

    # Entity types
    ENTITY_RECORD = "record"
    ENTITY_FIELD = "field"
    ENTITY_VIEW = "view"

    # Maximum operations per user
    MAX_OPERATIONS_PER_USER = 100

    # Operations retention period (24 hours)
    RETENTION_PERIOD_HOURS = 24

    def __init__(self) -> None:
        """Initialize undo/redo service."""
        pass

    async def log_operation(
        self,
        db: AsyncSession,
        user_id: str,
        operation_type: str,
        entity_type: str,
        entity_id: str,
        before_data: Optional[dict[str, Any]] = None,
        after_data: Optional[dict[str, Any]] = None,
    ) -> OperationLog:
        """Log an operation to the operation history.

        Args:
            db: Database session
            user_id: User ID performing the operation
            operation_type: Type of operation (create, update, delete)
            entity_type: Type of entity (record, field, view)
            entity_id: ID of the entity
            before_data: State before operation
            after_data: State after operation

        Returns:
            Created operation log

        Raises:
            ConflictError: If operation type or entity type is invalid

        """
        # Validate operation type
        valid_operations = [
            self.OPERATION_CREATE,
            self.OPERATION_UPDATE,
            self.OPERATION_DELETE,
        ]
        if operation_type not in valid_operations:
            raise ConflictError(f"Invalid operation type: {operation_type}")

        # Validate entity type
        valid_entities = [
            self.ENTITY_RECORD,
            self.ENTITY_FIELD,
            self.ENTITY_VIEW,
        ]
        if entity_type not in valid_entities:
            raise ConflictError(f"Invalid entity type: {entity_type}")

        # Check if user exceeded operation limit
        await self._enforce_operation_limit(db, user_id)

        # Create operation log
        operation_log = OperationLog(
            user_id=user_id,
            operation_type=operation_type,
            entity_type=entity_type,
            entity_id=entity_id,
        )

        # Set before and after data
        if before_data is not None:
            operation_log.set_before_data(before_data)
        if after_data is not None:
            operation_log.set_after_data(after_data)

        db.add(operation_log)

        return operation_log

    async def get_user_operations(
        self,
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        operation_type: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> tuple[list[OperationLog], int]:
        """Get operations for a user with pagination and filtering.

        Args:
            db: Database session
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            operation_type: Optional filter by operation type
            entity_type: Optional filter by entity type

        Returns:
            Tuple of (operations, total count)

        """
        offset = (page - 1) * page_size

        # Build base query
        count_query = select(func.count()).select_from(OperationLog)
        count_query = count_query.where(OperationLog.user_id == user_id)

        data_query = select(OperationLog)
        data_query = data_query.where(OperationLog.user_id == user_id)

        # Apply filters if provided
        if operation_type:
            count_query = count_query.where(OperationLog.operation_type == operation_type)
            data_query = data_query.where(OperationLog.operation_type == operation_type)

        if entity_type:
            count_query = count_query.where(OperationLog.entity_type == entity_type)
            data_query = data_query.where(OperationLog.entity_type == entity_type)

        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated data, ordered by most recent first
        data_query = data_query.order_by(desc(OperationLog.created_at))
        data_query = data_query.offset(offset)
        data_query = data_query.limit(page_size)
        result = await db.execute(data_query)
        operations = result.scalars().all()

        return list(operations), total

    async def undo_operation(
        self,
        db: AsyncSession,
        user_id: str,
        operation_id: str,
    ) -> OperationLog:
        """Undo an operation by reverting to the before state.

        Args:
            db: Database session
            user_id: User ID performing the undo
            operation_id: Operation ID to undo

        Returns:
            The operation that was undone

        Raises:
            NotFoundError: If operation not found
            PermissionDeniedError: If user doesn't own the operation
            ConflictError: If operation cannot be undone

        """
        # Get operation
        operation = await db.get(OperationLog, operation_id)
        if not operation:
            raise NotFoundError("Operation not found")

        # Check if user owns this operation
        if operation.user_id != user_id:
            raise PermissionDeniedError("You can only undo your own operations")

        # Perform undo based on entity type
        if operation.entity_type == self.ENTITY_RECORD:
            await self._undo_record_operation(db, operation)
        elif operation.entity_type == self.ENTITY_FIELD:
            await self._undo_field_operation(db, operation)
        elif operation.entity_type == self.ENTITY_VIEW:
            await self._undo_view_operation(db, operation)
        else:
            raise ConflictError(f"Unsupported entity type: {operation.entity_type}")

        return operation

    async def redo_operation(
        self,
        db: AsyncSession,
        user_id: str,
        operation_id: str,
    ) -> OperationLog:
        """Redo an operation by applying the after state.

        Args:
            db: Database session
            user_id: User ID performing the redo
            operation_id: Operation ID to redo

        Returns:
            The operation that was redone

        Raises:
            NotFoundError: If operation not found
            PermissionDeniedError: If user doesn't own the operation
            ConflictError: If operation cannot be redone

        """
        # Get operation
        operation = await db.get(OperationLog, operation_id)
        if not operation:
            raise NotFoundError("Operation not found")

        # Check if user owns this operation
        if operation.user_id != user_id:
            raise PermissionDeniedError("You can only redo your own operations")

        # Perform redo based on entity type
        if operation.entity_type == self.ENTITY_RECORD:
            await self._redo_record_operation(db, operation)
        elif operation.entity_type == self.ENTITY_FIELD:
            await self._redo_field_operation(db, operation)
        elif operation.entity_type == self.ENTITY_VIEW:
            await self._redo_view_operation(db, operation)
        else:
            raise ConflictError(f"Unsupported entity type: {operation.entity_type}")

        return operation

    async def cleanup_old_operations(
        self,
        db: AsyncSession,
        hours: Optional[int] = None,
    ) -> int:
        """Clean up old operations beyond retention period.

        Args:
            db: Database session
            hours: Number of hours to retain (defaults to RETENTION_PERIOD_HOURS)

        Returns:
            Number of operations deleted

        """
        retention_hours = hours or self.RETENTION_PERIOD_HOURS
        cutoff_time = datetime.utcnow() - timedelta(hours=retention_hours)

        # Delete old operations
        delete_query = delete(OperationLog).where(
            OperationLog.created_at < cutoff_time
        )
        result = await db.execute(delete_query)
        return result.rowcount

    async def _enforce_operation_limit(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> None:
        """Enforce maximum operations per user by deleting oldest.

        Args:
            db: Database session
            user_id: User ID

        """
        # Count user's operations
        count_query = select(func.count()).select_from(OperationLog)
        count_query = count_query.where(OperationLog.user_id == user_id)
        result = await db.execute(count_query)
        count = result.scalar() or 0

        # If over limit, delete oldest operations
        if count >= self.MAX_OPERATIONS_PER_USER:
            # Get operations to delete (oldest ones)
            excess = count - self.MAX_OPERATIONS_PER_USER + 1

            # Subquery to find oldest operations
            subquery = (
                select(OperationLog.id)
                .where(OperationLog.user_id == user_id)
                .order_by(OperationLog.created_at.asc())
                .limit(excess)
            )

            # Delete them
            delete_query = delete(OperationLog).where(
                and_(
                    OperationLog.user_id == user_id,
                    OperationLog.id.in_(subquery),
                )
            )
            await db.execute(delete_query)

    async def _undo_record_operation(
        self,
        db: AsyncSession,
        operation: OperationLog,
    ) -> None:
        """Undo a record operation.

        Args:
            db: Database session
            operation: Operation to undo

        Raises:
            ConflictError: If operation cannot be undone

        """
        before_data = operation.get_before_data()

        if operation.operation_type == self.OPERATION_CREATE:
            # Undo create: delete the record
            record = await db.get(Record, operation.entity_id)
            if record and not record.is_deleted:
                record.soft_delete()

        elif operation.operation_type == self.OPERATION_UPDATE:
            # Undo update: revert to before data
            record = await db.get(Record, operation.entity_id)
            if record and not record.is_deleted and before_data:
                record.data = json.dumps(before_data)

        elif operation.operation_type == self.OPERATION_DELETE:
            # Undo delete: restore the record
            record = await db.get(Record, operation.entity_id)
            if record and record.is_deleted:
                # Restore from before_data
                if before_data:
                    record.data = json.dumps(before_data)
                record.deleted_at = None
                record.deleted_by_id = None

        else:
            raise ConflictError(f"Unsupported operation type: {operation.operation_type}")

    async def _redo_record_operation(
        self,
        db: AsyncSession,
        operation: OperationLog,
    ) -> None:
        """Redo a record operation.

        Args:
            db: Database session
            operation: Operation to redo

        Raises:
            ConflictError: If operation cannot be redone

        """
        after_data = operation.get_after_data()

        if operation.operation_type == self.OPERATION_CREATE:
            # Redo create: ensure record exists
            record = await db.get(Record, operation.entity_id)
            if record:
                # If it was soft-deleted, restore it
                if record.is_deleted:
                    record.deleted_at = None
                    record.deleted_by_id = None
                # Update with after data if available
                if after_data:
                    record.data = json.dumps(after_data)

        elif operation.operation_type == self.OPERATION_UPDATE:
            # Redo update: apply after data
            record = await db.get(Record, operation.entity_id)
            if record and not record.is_deleted and after_data:
                record.data = json.dumps(after_data)

        elif operation.operation_type == self.OPERATION_DELETE:
            # Redo delete: ensure record is deleted
            record = await db.get(Record, operation.entity_id)
            if record and not record.is_deleted:
                record.soft_delete()

        else:
            raise ConflictError(f"Unsupported operation type: {operation.operation_type}")

    async def _undo_field_operation(
        self,
        db: AsyncSession,
        operation: OperationLog,
    ) -> None:
        """Undo a field operation.

        Args:
            db: Database session
            operation: Operation to undo

        Raises:
            ConflictError: If operation cannot be undone

        """
        before_data = operation.get_before_data()

        if operation.operation_type == self.OPERATION_CREATE:
            # Undo create: delete the field
            field = await db.get(Field, operation.entity_id)
            if field and not field.is_deleted:
                field.soft_delete()

        elif operation.operation_type == self.OPERATION_UPDATE:
            # Undo update: revert to before data
            field = await db.get(Field, operation.entity_id)
            if field and not field.is_deleted and before_data:
                # Update field properties from before_data
                if "name" in before_data:
                    field.name = before_data["name"]
                if "description" in before_data:
                    field.description = before_data["description"]
                if "config" in before_data:
                    field.config = json.dumps(before_data["config"])

        elif operation.operation_type == self.OPERATION_DELETE:
            # Undo delete: restore the field
            field = await db.get(Field, operation.entity_id)
            if field and field.is_deleted:
                if before_data:
                    # Restore field properties
                    if "name" in before_data:
                        field.name = before_data["name"]
                    if "description" in before_data:
                        field.description = before_data["description"]
                    if "config" in before_data:
                        field.config = json.dumps(before_data["config"])
                field.deleted_at = None
                field.deleted_by_id = None

        else:
            raise ConflictError(f"Unsupported operation type: {operation.operation_type}")

    async def _redo_field_operation(
        self,
        db: AsyncSession,
        operation: OperationLog,
    ) -> None:
        """Redo a field operation.

        Args:
            db: Database session
            operation: Operation to redo

        Raises:
            ConflictError: If operation cannot be redone

        """
        after_data = operation.get_after_data()

        if operation.operation_type == self.OPERATION_CREATE:
            # Redo create: ensure field exists
            field = await db.get(Field, operation.entity_id)
            if field:
                if field.is_deleted:
                    field.deleted_at = None
                    field.deleted_by_id = None
                if after_data:
                    if "name" in after_data:
                        field.name = after_data["name"]
                    if "description" in after_data:
                        field.description = after_data["description"]
                    if "config" in after_data:
                        field.config = json.dumps(after_data["config"])

        elif operation.operation_type == self.OPERATION_UPDATE:
            # Redo update: apply after data
            field = await db.get(Field, operation.entity_id)
            if field and not field.is_deleted and after_data:
                if "name" in after_data:
                    field.name = after_data["name"]
                if "description" in after_data:
                    field.description = after_data["description"]
                if "config" in after_data:
                    field.config = json.dumps(after_data["config"])

        elif operation.operation_type == self.OPERATION_DELETE:
            # Redo delete: ensure field is deleted
            field = await db.get(Field, operation.entity_id)
            if field and not field.is_deleted:
                field.soft_delete()

        else:
            raise ConflictError(f"Unsupported operation type: {operation.operation_type}")

    async def _undo_view_operation(
        self,
        db: AsyncSession,
        operation: OperationLog,
    ) -> None:
        """Undo a view operation.

        Args:
            db: Database session
            operation: Operation to undo

        Raises:
            ConflictError: If operation cannot be undone

        """
        before_data = operation.get_before_data()

        if operation.operation_type == self.OPERATION_CREATE:
            # Undo create: delete the view
            view = await db.get(View, operation.entity_id)
            if view and not view.is_deleted:
                view.soft_delete()

        elif operation.operation_type == self.OPERATION_UPDATE:
            # Undo update: revert to before data
            view = await db.get(View, operation.entity_id)
            if view and not view.is_deleted and before_data:
                # Update view properties from before_data
                if "name" in before_data:
                    view.name = before_data["name"]
                if "config" in before_data:
                    view.config = json.dumps(before_data["config"])
                if "filters" in before_data:
                    view.filters = json.dumps(before_data["filters"])
                if "sorts" in before_data:
                    view.sorts = json.dumps(before_data["sorts"])

        elif operation.operation_type == self.OPERATION_DELETE:
            # Undo delete: restore the view
            view = await db.get(View, operation.entity_id)
            if view and view.is_deleted:
                if before_data:
                    # Restore view properties
                    if "name" in before_data:
                        view.name = before_data["name"]
                    if "config" in before_data:
                        view.config = json.dumps(before_data["config"])
                    if "filters" in before_data:
                        view.filters = json.dumps(before_data["filters"])
                    if "sorts" in before_data:
                        view.sorts = json.dumps(before_data["sorts"])
                view.deleted_at = None
                view.deleted_by_id = None

        else:
            raise ConflictError(f"Unsupported operation type: {operation.operation_type}")

    async def _redo_view_operation(
        self,
        db: AsyncSession,
        operation: OperationLog,
    ) -> None:
        """Redo a view operation.

        Args:
            db: Database session
            operation: Operation to redo

        Raises:
            ConflictError: If operation cannot be redone

        """
        after_data = operation.get_after_data()

        if operation.operation_type == self.OPERATION_CREATE:
            # Redo create: ensure view exists
            view = await db.get(View, operation.entity_id)
            if view:
                if view.is_deleted:
                    view.deleted_at = None
                    view.deleted_by_id = None
                if after_data:
                    if "name" in after_data:
                        view.name = after_data["name"]
                    if "config" in after_data:
                        view.config = json.dumps(after_data["config"])
                    if "filters" in after_data:
                        view.filters = json.dumps(after_data["filters"])
                    if "sorts" in after_data:
                        view.sorts = json.dumps(after_data["sorts"])

        elif operation.operation_type == self.OPERATION_UPDATE:
            # Redo update: apply after data
            view = await db.get(View, operation.entity_id)
            if view and not view.is_deleted and after_data:
                if "name" in after_data:
                    view.name = after_data["name"]
                if "config" in after_data:
                    view.config = json.dumps(after_data["config"])
                if "filters" in after_data:
                    view.filters = json.dumps(after_data["filters"])
                if "sorts" in after_data:
                    view.sorts = json.dumps(after_data["sorts"])

        elif operation.operation_type == self.OPERATION_DELETE:
            # Redo delete: ensure view is deleted
            view = await db.get(View, operation.entity_id)
            if view and not view.is_deleted:
                view.soft_delete()

        else:
            raise ConflictError(f"Unsupported operation type: {operation.operation_type}")
