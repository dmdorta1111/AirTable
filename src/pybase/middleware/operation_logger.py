"""Operation logger middleware for tracking operations."""

import json
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.operation_log import OperationLog
from pybase.services.undo_redo import UndoRedoService


class OperationLogger:
    """Middleware for logging operations to enable undo/redo functionality.

    This middleware intercepts operations and logs them with before/after state
    to the operation_logs table. It provides both a context manager and decorator
    interface for flexible integration with service methods.

    Usage as context manager:
        async with OperationLogger.log_operation(
            db=db,
            user_id=user_id,
            operation_type=UndoRedoService.OPERATION_CREATE,
            entity_type=UndoRedoService.ENTITY_RECORD,
            entity_id=record_id,
            before_data=None,
        ):
            # Perform operation
            record = await create_record(...)

        # After context, after_data can be set
        # Or use the return value

    Usage as decorator:
        @OperationLogger.log_operation_decorator(
            operation_type=UndoRedoService.OPERATION_UPDATE,
            entity_type=UndoRedoService.ENTITY_RECORD,
            get_entity_id=lambda result: result.id,
            get_before_data=lambda **kwargs: kwargs.get("before_data"),
            get_after_data=lambda result: result.data,
        )
        async def update_record(db, user_id, record_id, ...):
            # Operation is automatically logged
            pass
    """

    def __init__(self) -> None:
        """Initialize operation logger with undo/redo service."""
        self.undo_redo_service = UndoRedoService()

    @asynccontextmanager
    async def log_operation(
        self,
        db: AsyncSession,
        user_id: str,
        operation_type: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        before_data: Optional[dict[str, Any]] = None,
        after_data: Optional[dict[str, Any]] = None,
    ) -> AsyncGenerator[None, None]:
        """Log an operation using context manager pattern.

        This context manager logs the operation before execution and allows
        updating after_data after the operation completes.

        Args:
            db: Database session
            user_id: User ID performing the operation
            operation_type: Type of operation (create, update, delete)
            entity_type: Type of entity (record, field, view)
            entity_id: Entity ID (can be None for create operations)
            before_data: State before operation
            after_data: State after operation (optional, can be set later)

        Yields:
            None

        Example:
            async with operation_logger.log_operation(
                db=db,
                user_id=user_id,
                operation_type=UndoRedoService.OPERATION_CREATE,
                entity_type=UndoRedoService.ENTITY_RECORD,
                entity_id=None,
                before_data=None,
            ):
                record = Record(...)
                db.add(record)
                await db.flush()
                # entity_id is now available
                yield
        """
        # Log operation with initial data
        operation_log = await self.undo_redo_service.log_operation(
            db=db,
            user_id=user_id,
            operation_type=operation_type,
            entity_type=entity_type,
            entity_id=entity_id or "",
            before_data=before_data,
            after_data=after_data,
        )

        try:
            yield
        except Exception:
            # If operation fails, delete the log entry
            await db.delete(operation_log)
            raise

    async def log_create_operation(
        self,
        db: AsyncSession,
        user_id: str,
        entity_type: str,
        entity_id: str,
        after_data: dict[str, Any],
    ) -> OperationLog:
        """Log a create operation.

        Args:
            db: Database session
            user_id: User ID performing the operation
            entity_type: Type of entity (record, field, view)
            entity_id: ID of created entity
            after_data: State after creation

        Returns:
            Created operation log

        """
        return await self.undo_redo_service.log_operation(
            db=db,
            user_id=user_id,
            operation_type=UndoRedoService.OPERATION_CREATE,
            entity_type=entity_type,
            entity_id=entity_id,
            before_data=None,
            after_data=after_data,
        )

    async def log_update_operation(
        self,
        db: AsyncSession,
        user_id: str,
        entity_type: str,
        entity_id: str,
        before_data: dict[str, Any],
        after_data: dict[str, Any],
    ) -> OperationLog:
        """Log an update operation.

        Args:
            db: Database session
            user_id: User ID performing the operation
            entity_type: Type of entity (record, field, view)
            entity_id: ID of updated entity
            before_data: State before update
            after_data: State after update

        Returns:
            Created operation log

        """
        return await self.undo_redo_service.log_operation(
            db=db,
            user_id=user_id,
            operation_type=UndoRedoService.OPERATION_UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            before_data=before_data,
            after_data=after_data,
        )

    async def log_delete_operation(
        self,
        db: AsyncSession,
        user_id: str,
        entity_type: str,
        entity_id: str,
        before_data: dict[str, Any],
    ) -> OperationLog:
        """Log a delete operation.

        Args:
            db: Database session
            user_id: User ID performing the operation
            entity_type: Type of entity (record, field, view)
            entity_id: ID of deleted entity
            before_data: State before deletion

        Returns:
            Created operation log

        """
        return await self.undo_redo_service.log_operation(
            db=db,
            user_id=user_id,
            operation_type=UndoRedoService.OPERATION_DELETE,
            entity_type=entity_type,
            entity_id=entity_id,
            before_data=before_data,
            after_data=None,
        )

    @staticmethod
    def log_operation_decorator(
        operation_type: str,
        entity_type: str,
        get_entity_id: Callable[[Any], str],
        get_before_data: Optional[Callable[..., dict[str, Any]]] = None,
        get_after_data: Optional[Callable[[Any], dict[str, Any]]] = None,
        get_user_id: Optional[Callable[..., str]] = None,
    ) -> Callable:
        """Decorator to automatically log operations.

        Args:
            operation_type: Type of operation (create, update, delete)
            entity_type: Type of entity (record, field, view)
            get_entity_id: Function to extract entity ID from result/args
            get_before_data: Optional function to extract before data from args
            get_after_data: Optional function to extract after data from result
            get_user_id: Optional function to extract user_id from args

        Returns:
            Decorator function

        Example:
            @OperationLogger.log_operation_decorator(
                operation_type=UndoRedoService.OPERATION_UPDATE,
                entity_type=UndoRedoService.ENTITY_RECORD,
                get_entity_id=lambda args, kwargs: kwargs.get("record_id"),
                get_before_data=lambda args, kwargs: args[0].data if args else None,
                get_after_data=lambda result, args, kwargs: result.data,
                get_user_id=lambda args, kwargs: kwargs.get("user_id"),
            )
            async def update_record(record, user_id, record_id, ...):
                # Operation is automatically logged
                pass

        """

        def decorator(func: Callable) -> Callable:
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                # Extract db session from args/kwargs
                db = kwargs.get("db") or (args[0] if args else None)
                if not db:
                    raise ValueError("Database session not found in arguments")

                # Extract user_id
                user_id = get_user_id(args, kwargs) if get_user_id else kwargs.get("user_id")
                if not user_id:
                    raise ValueError("user_id not found in arguments")

                # Get before data if applicable
                before_data = None
                if get_before_data and operation_type in [
                    UndoRedoService.OPERATION_UPDATE,
                    UndoRedoService.OPERATION_DELETE,
                ]:
                    before_data = get_before_data(args, kwargs)

                # Execute the operation
                result = await func(*args, **kwargs)

                # Get entity ID and after data
                entity_id = get_entity_id(result, args, kwargs) if callable(get_entity_id) else get_entity_id

                after_data = None
                if get_after_data and operation_type in [
                    UndoRedoService.OPERATION_CREATE,
                    UndoRedoService.OPERATION_UPDATE,
                ]:
                    after_data = get_after_data(result, args, kwargs)

                # Log the operation
                operation_logger = OperationLogger()
                await operation_logger.undo_redo_service.log_operation(
                    db=db,
                    user_id=user_id,
                    operation_type=operation_type,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    before_data=before_data,
                    after_data=after_data,
                )

                return result

            return wrapper

        return decorator

    async def capture_entity_state(
        self,
        db: AsyncSession,
        entity_type: str,
        entity_id: str,
    ) -> dict[str, Any]:
        """Capture the current state of an entity for logging.

        This helper method retrieves the current state of an entity
        to use as before_data or after_data in operation logging.

        Args:
            db: Database session
            entity_type: Type of entity (record, field, view)
            entity_id: ID of the entity

        Returns:
            Dictionary representing the entity's current state

        Raises:
            NotFoundError: If entity not found

        """
        from pybase.core.exceptions import NotFoundError
        from pybase.models.field import Field
        from pybase.models.record import Record
        from pybase.models.view import View

        if entity_type == UndoRedoService.ENTITY_RECORD:
            entity = await db.get(Record, entity_id)
            if not entity:
                raise NotFoundError(f"Record not found: {entity_id}")
            return {
                "id": str(entity.id),
                "table_id": str(entity.table_id),
                "data": json.loads(entity.data) if entity.data else {},
                "row_height": entity.row_height,
            }

        elif entity_type == UndoRedoService.ENTITY_FIELD:
            entity = await db.get(Field, entity_id)
            if not entity:
                raise NotFoundError(f"Field not found: {entity_id}")
            return {
                "id": str(entity.id),
                "table_id": str(entity.table_id),
                "name": entity.name,
                "description": entity.description,
                "field_type": entity.field_type,
                "config": json.loads(entity.config) if entity.config else {},
            }

        elif entity_type == UndoRedoService.ENTITY_VIEW:
            entity = await db.get(View, entity_id)
            if not entity:
                raise NotFoundError(f"View not found: {entity_id}")
            return {
                "id": str(entity.id),
                "table_id": str(entity.table_id),
                "name": entity.name,
                "type": entity.type,
                "config": json.loads(entity.config) if entity.config else {},
                "filters": json.loads(entity.filters) if entity.filters else [],
                "sorts": json.loads(entity.sorts) if entity.sorts else [],
            }

        else:
            raise NotFoundError(f"Unsupported entity type: {entity_type}")
