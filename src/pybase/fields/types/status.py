"""Status field type handler."""

from typing import Any

from pybase.fields.types.single_select import SingleSelectFieldHandler


class StatusFieldHandler(SingleSelectFieldHandler):
    """
    Handler for status field type.

    Special single-select with status groups (todo, in_progress, complete).
    Options:
        - statuses: list of {id, name, color, group} objects
            - group: "todo" | "in_progress" | "complete"
        - allow_new: whether to allow creating new statuses (default: False)
    """

    field_type = "status"

    # Valid status groups
    GROUPS = {"todo", "in_progress", "complete"}

    # Default status configuration
    DEFAULT_STATUSES = [
        {"id": "todo", "name": "To Do", "color": "gray", "group": "todo"},
        {"id": "in_progress", "name": "In Progress", "color": "yellow", "group": "in_progress"},
        {"id": "done", "name": "Done", "color": "green", "group": "complete"},
    ]

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate status field value.

        Args:
            value: Value to validate (status name)
            options: Optional dict with:
                - statuses: list of {id, name, color, group} dicts
                - allow_new: whether to allow values not in statuses (default: False)

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return True

        if not isinstance(value, str):
            raise ValueError(f"Status field requires string value, got {type(value).__name__}")

        options = options or {}
        statuses = options.get("statuses", cls.DEFAULT_STATUSES)
        allow_new = options.get("allow_new", False)  # Default False for status

        # Extract valid status names
        valid_names = {status.get("name") for status in statuses if status.get("name")}

        if value not in valid_names:
            if not allow_new:
                raise ValueError(
                    f"Invalid status '{value}'. Valid statuses: {', '.join(sorted(valid_names))}"
                )

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for status field (first todo status)."""
        return None

    @classmethod
    def get_default_options(cls) -> dict[str, Any]:
        """Get default options for a new status field."""
        return {
            "statuses": cls.DEFAULT_STATUSES.copy(),
            "allow_new": False,
        }

    @classmethod
    def add_status(
        cls,
        options: dict[str, Any],
        name: str,
        group: str,
        color: str | None = None,
    ) -> dict[str, Any]:
        """
        Add a new status to field options.

        Args:
            options: Current field options
            name: Status name
            group: Status group ("todo", "in_progress", "complete")
            color: Optional color

        Returns:
            Updated options dict

        Raises:
            ValueError: If group is invalid
        """
        if group not in cls.GROUPS:
            raise ValueError(f"Invalid group '{group}'. Must be one of: {', '.join(cls.GROUPS)}")

        statuses = list(options.get("statuses", cls.DEFAULT_STATUSES))

        # Check for duplicate
        if any(s.get("name") == name for s in statuses):
            return options

        # Default color based on group
        if color is None:
            color = {"todo": "gray", "in_progress": "yellow", "complete": "green"}.get(
                group, "gray"
            )

        from uuid import uuid4

        statuses.append(
            {
                "id": str(uuid4()),
                "name": name,
                "color": color,
                "group": group,
            }
        )

        return {**options, "statuses": statuses}

    @classmethod
    def get_status_group(
        cls,
        options: dict[str, Any],
        name: str,
    ) -> str | None:
        """
        Get group for a status.

        Args:
            options: Field options
            name: Status name

        Returns:
            Group string ("todo", "in_progress", "complete") or None
        """
        statuses = options.get("statuses", cls.DEFAULT_STATUSES)
        for status in statuses:
            if status.get("name") == name:
                return status.get("group")
        return None

    @classmethod
    def get_statuses_by_group(
        cls,
        options: dict[str, Any],
        group: str,
    ) -> list[dict[str, Any]]:
        """
        Get all statuses in a group.

        Args:
            options: Field options
            group: Group name

        Returns:
            List of status dicts in the group
        """
        statuses = options.get("statuses", cls.DEFAULT_STATUSES)
        return [s for s in statuses if s.get("group") == group]

    @classmethod
    def is_complete(cls, options: dict[str, Any], value: str) -> bool:
        """Check if a status value is in the 'complete' group."""
        return cls.get_status_group(options, value) == "complete"

    @classmethod
    def is_in_progress(cls, options: dict[str, Any], value: str) -> bool:
        """Check if a status value is in the 'in_progress' group."""
        return cls.get_status_group(options, value) == "in_progress"

    @classmethod
    def is_todo(cls, options: dict[str, Any], value: str) -> bool:
        """Check if a status value is in the 'todo' group."""
        return cls.get_status_group(options, value) == "todo"
