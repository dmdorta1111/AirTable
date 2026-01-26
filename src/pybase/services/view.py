"""View service for business logic."""

import json
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from pybase.models.base import Base
from pybase.models.table import Table
from pybase.models.view import View, ViewType
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.view import ViewCreate, ViewUpdate, ViewDuplicate


class ViewService:
    """Service for view operations."""

    async def create_view(
        self,
        db: AsyncSession,
        user_id: str,
        view_data: ViewCreate,
    ) -> View:
        """Create a new view for a table.

        Args:
            db: Database session
            user_id: User ID creating the view
            view_data: View creation data

        Returns:
            Created view

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have access

        """
        # Check if table exists and user has access
        table = await self._get_table_with_access(db, str(view_data.table_id), user_id)

        # Determine position (append to end)
        max_position_query = select(func.max(View.position)).where(
            View.table_id == str(view_data.table_id),
            View.deleted_at.is_(None),
        )
        result = await db.execute(max_position_query)
        max_position = result.scalar() or 0

        # If setting as default, unset other defaults
        if view_data.is_default:
            await self._unset_default_views(db, str(view_data.table_id))

        # Serialize configurations to JSON
        field_config = None
        if view_data.field_config:
            field_config = json.dumps(view_data.field_config.model_dump(mode="json"))

        filters = json.dumps([f.model_dump(mode="json") for f in view_data.filters])
        sorts = json.dumps([s.model_dump(mode="json") for s in view_data.sorts])

        groups = None
        if view_data.groups:
            groups = json.dumps(view_data.groups.model_dump(mode="json"))

        # Get type-specific config
        type_config = self._get_type_config(view_data)

        # Create view
        view = View(
            table_id=str(view_data.table_id),
            created_by_id=user_id,
            name=view_data.name,
            description=view_data.description,
            view_type=view_data.view_type.value,
            is_default=view_data.is_default,
            is_locked=view_data.is_locked,
            is_personal=view_data.is_personal,
            position=view_data.position if view_data.position is not None else max_position + 1,
            color=view_data.color,
            row_height=view_data.row_height.value,
            field_config=field_config,
            filters=filters,
            sorts=sorts,
            groups=groups,
            type_config=type_config,
        )
        db.add(view)
        await db.commit()
        await db.refresh(view)

        return view

    async def get_view_by_id(
        self,
        db: AsyncSession,
        view_id: str,
        user_id: str,
    ) -> View:
        """Get a view by ID, checking user access.

        Args:
            db: Database session
            view_id: View ID
            user_id: User ID requesting access

        Returns:
            View

        Raises:
            NotFoundError: If view not found
            PermissionDeniedError: If user doesn't have access

        """
        view = await db.get(View, view_id)
        if not view or view.is_deleted:
            raise NotFoundError("View not found")

        # Check user access to table
        await self._get_table_with_access(db, view.table_id, user_id)

        # Personal views are only visible to creator
        if view.is_personal and view.created_by_id != user_id:
            raise PermissionDeniedError("This is a personal view")

        return view

    async def list_views(
        self,
        db: AsyncSession,
        table_id: UUID,
        user_id: str,
        view_type: Optional[str] = None,
        include_personal: bool = True,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[View], int]:
        """List views for a table.

        Args:
            db: Database session
            table_id: Table ID
            user_id: User ID
            view_type: Optional view type filter
            include_personal: Include personal views (only user's own)
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (views, total count)

        """
        # Check user access to table
        await self._get_table_with_access(db, str(table_id), user_id)

        offset = (page - 1) * page_size

        # Base conditions
        conditions = [
            View.table_id == str(table_id),
            View.deleted_at.is_(None),
        ]

        if view_type:
            conditions.append(View.view_type == view_type)

        # Personal views filter
        if include_personal:
            # Show non-personal views OR user's personal views
            from sqlalchemy import or_

            conditions.append(
                or_(
                    View.is_personal.is_(False),
                    View.created_by_id == user_id,
                )
            )
        else:
            conditions.append(View.is_personal.is_(False))

        # Count query
        count_query = select(func.count()).select_from(View).where(*conditions)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query
        query = (
            select(View).where(*conditions).order_by(View.position).offset(offset).limit(page_size)
        )
        result = await db.execute(query)
        views = result.scalars().all()

        return list(views), total

    async def update_view(
        self,
        db: AsyncSession,
        view_id: str,
        user_id: str,
        view_data: ViewUpdate,
    ) -> View:
        """Update a view.

        Args:
            db: Database session
            view_id: View ID
            user_id: User ID making request
            view_data: View update data

        Returns:
            Updated view

        Raises:
            NotFoundError: If view not found
            PermissionDeniedError: If user doesn't have permission

        """
        view = await self.get_view_by_id(db, view_id, user_id)

        # Check if view is locked (only creator or workspace admin can modify)
        if view.is_locked:
            # Allow creator to modify
            if view.created_by_id != user_id:
                # Check if user is workspace admin
                table = await self._get_table(db, view.table_id)
                base = await self._get_base(db, table.base_id)
                member = await self._get_workspace_member(db, base.workspace_id, user_id)
                if not member or member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
                    raise PermissionDeniedError("This view is locked")

        # If setting as default, unset other defaults
        if view_data.is_default:
            await self._unset_default_views(db, view.table_id)

        # Update basic fields
        if view_data.name is not None:
            view.name = view_data.name
        if view_data.description is not None:
            view.description = view_data.description
        if view_data.is_default is not None:
            view.is_default = view_data.is_default
        if view_data.is_locked is not None:
            view.is_locked = view_data.is_locked
        if view_data.is_personal is not None:
            view.is_personal = view_data.is_personal
        if view_data.position is not None:
            view.position = view_data.position
        if view_data.color is not None:
            view.color = view_data.color
        if view_data.row_height is not None:
            view.row_height = view_data.row_height.value

        # Update configurations
        if view_data.field_config is not None:
            view.field_config = json.dumps(view_data.field_config.model_dump(mode="json"))
        if view_data.filters is not None:
            view.filters = json.dumps([f.model_dump(mode="json") for f in view_data.filters])
        if view_data.sorts is not None:
            view.sorts = json.dumps([s.model_dump(mode="json") for s in view_data.sorts])
        if view_data.groups is not None:
            view.groups = json.dumps(view_data.groups.model_dump(mode="json"))

        # Update type-specific config
        type_config = self._get_type_config_update(view_data)
        if type_config:
            view.type_config = type_config

        await db.commit()
        await db.refresh(view)

        return view

    async def delete_view(
        self,
        db: AsyncSession,
        view_id: str,
        user_id: str,
    ) -> None:
        """Delete (soft delete) a view.

        Args:
            db: Database session
            view_id: View ID
            user_id: User ID making request

        Raises:
            NotFoundError: If view not found
            PermissionDeniedError: If user doesn't have permission
            ConflictError: If trying to delete the only view

        """
        view = await self.get_view_by_id(db, view_id, user_id)

        # Check if this is the only view for the table
        count_query = (
            select(func.count())
            .select_from(View)
            .where(
                View.table_id == view.table_id,
                View.deleted_at.is_(None),
            )
        )
        result = await db.execute(count_query)
        count = result.scalar() or 0
        if count <= 1:
            raise ConflictError("Cannot delete the only view of a table")

        # Check permissions
        # Personal views can be deleted by creator
        # Other views require workspace admin/owner
        if view.created_by_id != user_id:
            table = await self._get_table(db, view.table_id)
            base = await self._get_base(db, table.base_id)
            member = await self._get_workspace_member(db, base.workspace_id, user_id)
            if not member or member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
                raise PermissionDeniedError("Only view creator or workspace admin can delete views")

        # If deleting default view, set another as default
        if view.is_default:
            await self._set_next_default(db, view.table_id, view_id)

        view.soft_delete()
        await db.commit()

    async def duplicate_view(
        self,
        db: AsyncSession,
        view_id: str,
        user_id: str,
        duplicate_data: ViewDuplicate,
    ) -> View:
        """Duplicate a view.

        Args:
            db: Database session
            view_id: View ID to duplicate
            user_id: User ID making request
            duplicate_data: Duplicate options

        Returns:
            New duplicated view

        """
        original = await self.get_view_by_id(db, view_id, user_id)

        # Determine position (append after original)
        max_position_query = select(func.max(View.position)).where(
            View.table_id == original.table_id,
            View.deleted_at.is_(None),
        )
        result = await db.execute(max_position_query)
        max_position = result.scalar() or 0

        # Create duplicate
        new_view = View(
            table_id=original.table_id,
            created_by_id=user_id,
            name=duplicate_data.name,
            description=original.description,
            view_type=original.view_type,
            is_default=False,  # Never copy default status
            is_locked=False,  # Start unlocked
            is_personal=False,  # Start as shared
            position=max_position + 1,
            color=original.color,
            row_height=original.row_height,
            field_config=original.field_config if duplicate_data.include_field_config else "{}",
            filters=original.filters if duplicate_data.include_filters else "[]",
            sorts=original.sorts if duplicate_data.include_sorts else "[]",
            groups=original.groups if duplicate_data.include_groups else "{}",
            type_config=original.type_config,
        )
        db.add(new_view)
        await db.commit()
        await db.refresh(new_view)

        return new_view

    async def get_default_view(
        self,
        db: AsyncSession,
        table_id: str,
        user_id: str,
    ) -> View:
        """Get the default view for a table.

        Args:
            db: Database session
            table_id: Table ID
            user_id: User ID

        Returns:
            Default view

        """
        await self._get_table_with_access(db, table_id, user_id)

        # Find default view
        query = select(View).where(
            View.table_id == table_id,
            View.is_default.is_(True),
            View.deleted_at.is_(None),
        )
        result = await db.execute(query)
        view = result.scalar_one_or_none()

        if view:
            return view

        # If no default, return first view
        query = (
            select(View)
            .where(View.table_id == table_id, View.deleted_at.is_(None))
            .order_by(View.position)
            .limit(1)
        )
        result = await db.execute(query)
        view = result.scalar_one_or_none()

        if not view:
            raise NotFoundError("No views found for this table")

        return view

    async def reorder_views(
        self,
        db: AsyncSession,
        table_id: str,
        user_id: str,
        view_ids: list[str],
    ) -> list[View]:
        """Reorder views for a table.

        Args:
            db: Database session
            table_id: Table ID
            user_id: User ID making request
            view_ids: Ordered list of view IDs

        Returns:
            Reordered views

        """
        await self._get_table_with_access(db, table_id, user_id)

        # Update positions
        for position, view_id in enumerate(view_ids):
            view = await db.get(View, view_id)
            if view and view.table_id == table_id and not view.is_deleted:
                view.position = position

        await db.commit()

        # Return reordered views
        query = (
            select(View)
            .where(View.table_id == table_id, View.deleted_at.is_(None))
            .order_by(View.position)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_view_data(
        self,
        db: AsyncSession,
        view_id: str,
        user_id: str,
        page: int = 1,
        page_size: int = 100,
        override_filters: Optional[list] = None,
        override_sorts: Optional[list] = None,
        search: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get view data with filters and sorts applied.

        Args:
            db: Database session
            view_id: View ID
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of records per page
            override_filters: Additional filters to apply
            override_sorts: Override view sorts
            search: Search query across all fields

        Returns:
            Tuple of (records as dicts, total count)

        Raises:
            NotFoundError: If view not found
            PermissionDeniedError: If user doesn't have access

        """
        from pybase.models.record import Record

        # Get view and verify access
        view = await self.get_view_by_id(db, view_id, user_id)

        # Get all records from the table
        query = select(Record).where(
            Record.table_id == view.table_id,
            Record.deleted_at.is_(None),
        )
        result = await db.execute(query)
        records = result.scalars().all()

        # Convert records to dict format
        records_data = []
        for record in records:
            try:
                data = json.loads(record.data) if isinstance(record.data, str) else record.data
            except (json.JSONDecodeError, TypeError):
                data = {}

            record_dict = {
                "id": str(record.id),
                "table_id": str(record.table_id),
                "data": data,
                "row_height": record.row_height or 32,
                "created_by_id": str(record.created_by_id) if record.created_by_id else None,
                "last_modified_by_id": str(record.last_modified_by_id) if record.last_modified_by_id else None,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            }
            records_data.append(record_dict)

        # Apply view filters
        filters = view.get_filters_list() if hasattr(view, "get_filters_list") else []
        if filters:
            records_data = self._apply_filters(records_data, filters)

        # Apply additional filters if provided
        if override_filters:
            override_filters_list = [f.model_dump() for f in override_filters]
            records_data = self._apply_filters(records_data, override_filters_list)

        # Apply search if provided
        if search:
            records_data = self._apply_search(records_data, search)

        # Apply sorts
        sorts = override_sorts if override_sorts is not None else (view.get_sorts_list() if hasattr(view, "get_sorts_list") else [])
        if sorts:
            if override_sorts:
                sorts = [s.model_dump() for s in sorts]
            records_data = self._apply_sorts(records_data, sorts)

        # Get total count after filtering
        total = len(records_data)

        # Apply pagination
        offset = (page - 1) * page_size
        records_data = records_data[offset : offset + page_size]

        return records_data, total

    # ==========================================================================
    # Helper Methods
    # ==========================================================================

    def _apply_filters(
        self,
        records: list[dict[str, Any]],
        filters: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Apply filters to records.

        Args:
            records: List of record dicts
            filters: List of filter conditions

        Returns:
            Filtered records

        """
        if not filters:
            return records

        filtered_records = []
        for record in records:
            if self._record_matches_filters(record, filters):
                filtered_records.append(record)

        return filtered_records

    def _record_matches_filters(
        self,
        record: dict[str, Any],
        filters: list[dict[str, Any]],
    ) -> bool:
        """Check if a record matches all filter conditions.

        Args:
            record: Record dict
            filters: List of filter conditions

        Returns:
            True if record matches filters

        """
        and_conditions = []
        or_conditions = []

        for filter_cond in filters:
            field_id = str(filter_cond.get("field_id", ""))
            operator = filter_cond.get("operator", "")
            value = filter_cond.get("value")
            conjunction = filter_cond.get("conjunction", "and")

            # Get field value from record
            field_value = record.get("data", {}).get(field_id)

            # Evaluate condition
            matches = self._evaluate_filter(field_value, operator, value)

            if conjunction == "or":
                or_conditions.append(matches)
            else:
                and_conditions.append(matches)

        # All AND conditions must be true
        all_ands = all(and_conditions) if and_conditions else True
        # At least one OR condition must be true (if any OR conditions exist)
        any_ors = any(or_conditions) if or_conditions else True

        return all_ands and (any_ors if or_conditions else True)

    def _evaluate_filter(
        self,
        field_value: Any,
        operator: str,
        filter_value: Any,
    ) -> bool:
        """Evaluate a single filter condition.

        Args:
            field_value: Value from record
            operator: Filter operator
            filter_value: Value to compare against

        Returns:
            True if condition matches

        """
        if operator == "equals":
            return field_value == filter_value
        elif operator == "not_equals":
            return field_value != filter_value
        elif operator == "contains":
            return filter_value in str(field_value) if field_value else False
        elif operator == "not_contains":
            return filter_value not in str(field_value) if field_value else True
        elif operator == "is_empty":
            return field_value is None or field_value == "" or field_value == []
        elif operator == "is_not_empty":
            return field_value is not None and field_value != "" and field_value != []
        elif operator == "gt":
            return field_value > filter_value if field_value is not None else False
        elif operator == "lt":
            return field_value < filter_value if field_value is not None else False
        elif operator == "gte":
            return field_value >= filter_value if field_value is not None else False
        elif operator == "lte":
            return field_value <= filter_value if field_value is not None else False
        elif operator == "in":
            return field_value in filter_value if filter_value else False
        elif operator == "not_in":
            return field_value not in filter_value if filter_value else True
        elif operator == "starts_with":
            return str(field_value).startswith(str(filter_value)) if field_value else False
        elif operator == "ends_with":
            return str(field_value).endswith(str(filter_value)) if field_value else False
        else:
            # Unsupported operator, default to True
            return True

    def _apply_search(
        self,
        records: list[dict[str, Any]],
        search: str,
    ) -> list[dict[str, Any]]:
        """Apply search query to records.

        Args:
            records: List of record dicts
            search: Search query

        Returns:
            Filtered records

        """
        if not search:
            return records

        search_lower = search.lower()
        filtered_records = []

        for record in records:
            # Search across all field values
            data = record.get("data", {})
            for value in data.values():
                if search_lower in str(value).lower():
                    filtered_records.append(record)
                    break

        return filtered_records

    def _apply_sorts(
        self,
        records: list[dict[str, Any]],
        sorts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Apply sort rules to records.

        Args:
            records: List of record dicts
            sorts: List of sort rules

        Returns:
            Sorted records

        """
        if not sorts:
            return records

        # Apply sorts in reverse order (last sort first)
        for sort_rule in reversed(sorts):
            field_id = str(sort_rule.get("field_id", ""))
            direction = sort_rule.get("direction", "asc")

            reverse = direction == "desc"

            records = sorted(
                records,
                key=lambda r: r.get("data", {}).get(field_id) or "",
                reverse=reverse,
            )

        return records

    def _get_type_config(self, view_data: ViewCreate) -> Optional[str]:
        """Extract and serialize type-specific config."""
        config = None
        if view_data.view_type == ViewType.GRID and view_data.grid_config:
            config = view_data.grid_config.model_dump(mode="json")
        elif view_data.view_type == ViewType.KANBAN and view_data.kanban_config:
            config = view_data.kanban_config.model_dump(mode="json")
        elif view_data.view_type == ViewType.CALENDAR and view_data.calendar_config:
            config = view_data.calendar_config.model_dump(mode="json")
        elif view_data.view_type == ViewType.GALLERY and view_data.gallery_config:
            config = view_data.gallery_config.model_dump(mode="json")
        elif view_data.view_type == ViewType.FORM and view_data.form_config:
            config = view_data.form_config.model_dump(mode="json")
        elif view_data.view_type == ViewType.GANTT and view_data.gantt_config:
            config = view_data.gantt_config.model_dump(mode="json")
        elif view_data.view_type == ViewType.TIMELINE and view_data.timeline_config:
            config = view_data.timeline_config.model_dump(mode="json")

        return json.dumps(config) if config else None

    def _get_type_config_update(self, view_data: ViewUpdate) -> Optional[str]:
        """Extract and serialize type-specific config for update."""
        config = None
        if view_data.grid_config:
            config = view_data.grid_config.model_dump(mode="json")
        elif view_data.kanban_config:
            config = view_data.kanban_config.model_dump(mode="json")
        elif view_data.calendar_config:
            config = view_data.calendar_config.model_dump(mode="json")
        elif view_data.gallery_config:
            config = view_data.gallery_config.model_dump(mode="json")
        elif view_data.form_config:
            config = view_data.form_config.model_dump(mode="json")
        elif view_data.gantt_config:
            config = view_data.gantt_config.model_dump(mode="json")
        elif view_data.timeline_config:
            config = view_data.timeline_config.model_dump(mode="json")

        return json.dumps(config) if config else None

    async def _unset_default_views(self, db: AsyncSession, table_id: str) -> None:
        """Unset default flag on all views for a table."""
        query = select(View).where(
            View.table_id == table_id,
            View.is_default.is_(True),
            View.deleted_at.is_(None),
        )
        result = await db.execute(query)
        for view in result.scalars().all():
            view.is_default = False

    async def _set_next_default(
        self, db: AsyncSession, table_id: str, exclude_view_id: str
    ) -> None:
        """Set the next view as default."""
        query = (
            select(View)
            .where(
                View.table_id == table_id,
                View.id != exclude_view_id,
                View.deleted_at.is_(None),
            )
            .order_by(View.position)
            .limit(1)
        )
        result = await db.execute(query)
        next_view = result.scalar_one_or_none()
        if next_view:
            next_view.is_default = True

    async def _get_table_with_access(
        self,
        db: AsyncSession,
        table_id: str,
        user_id: str,
    ) -> Table:
        """Get table and verify user access."""
        table = await self._get_table(db, table_id)
        base = await self._get_base(db, table.base_id)
        member = await self._get_workspace_member(db, base.workspace_id, user_id)
        if not member:
            raise PermissionDeniedError("You don't have access to this table")
        return table

    async def _get_table(self, db: AsyncSession, table_id: str) -> Table:
        """Get table by ID."""
        table = await db.get(Table, table_id)
        if not table or table.is_deleted:
            raise NotFoundError("Table not found")
        return table

    async def _get_base(self, db: AsyncSession, base_id: str) -> Base:
        """Get base by ID."""
        base = await db.get(Base, base_id)
        if not base or base.is_deleted:
            raise NotFoundError("Base not found")
        return base

    async def _get_workspace(self, db: AsyncSession, workspace_id: str) -> Workspace:
        """Get workspace by ID."""
        workspace = await db.get(Workspace, workspace_id)
        if not workspace or workspace.is_deleted:
            raise NotFoundError("Workspace not found")
        return workspace

    async def _get_workspace_member(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
    ) -> Optional[WorkspaceMember]:
        """Get workspace member."""
        query = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
