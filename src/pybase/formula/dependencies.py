"""Formula dependency tracking for PyBase.

Tracks formula field dependencies for efficient recalculation and
circular reference detection.
"""

from collections import defaultdict, deque


class FormulaDependencyGraph:
    """
    Track formula field dependencies for recalculation.

    Maintains a bidirectional graph of field dependencies:
    - dependencies: field_id -> set of field_ids that depend on this field
    - reverse: field_id -> set of field_ids this field depends on
    """

    def __init__(self):
        """Initialize empty dependency graph."""
        # Forward mapping: field_id -> set of dependent field_ids
        # If field A changes, all fields in dependencies[A] need recalculation
        self.dependencies: dict[str, set[str]] = defaultdict(set)

        # Reverse mapping: field_id -> set of fields it depends on
        # To calculate field A, we need all fields in reverse[A]
        self.reverse: dict[str, set[str]] = defaultdict(set)

    def add_formula_field(self, field_id: str, depends_on: set[str]) -> tuple[bool, str | None]:
        """
        Add a formula field to the dependency graph.

        Args:
            field_id: ID of the formula field
            depends_on: Set of field IDs this formula references

        Returns:
            Tuple of (success, error_message)
        """
        # Check for circular reference before adding
        if self.detect_circular_reference(field_id, depends_on):
            return False, "Circular reference detected in formula dependencies"

        # Remove old dependencies if field already exists
        if field_id in self.reverse:
            old_deps = self.reverse[field_id]
            for old_dep in old_deps:
                self.dependencies[old_dep].discard(field_id)

        # Add new dependencies
        self.reverse[field_id] = depends_on.copy()
        for dep in depends_on:
            self.dependencies[dep].add(field_id)

        return True, None

    def remove_formula_field(self, field_id: str) -> None:
        """
        Remove a formula field from the dependency graph.

        Args:
            field_id: ID of the formula field to remove
        """
        # Remove from reverse mapping
        if field_id in self.reverse:
            for dep in self.reverse[field_id]:
                self.dependencies[dep].discard(field_id)
            del self.reverse[field_id]

        # Remove from dependencies mapping
        self.dependencies.pop(field_id, None)

    def get_affected_fields(self, changed_field_id: str) -> list[str]:
        """
        Get formula fields that need recalculation when a field changes.

        Uses BFS to traverse the dependency tree and find all
        transitive dependents of the changed field.

        Args:
            changed_field_id: ID of the field that changed

        Returns:
            List of field IDs that need recalculation
        """
        affected = []
        to_process = deque([changed_field_id])
        seen = set()

        while to_process:
            current = to_process.popleft()

            if current in seen:
                continue
            seen.add(current)

            # Add all fields that depend on current field
            for dependent in self.dependencies[current]:
                if dependent not in seen:
                    affected.append(dependent)
                    to_process.append(dependent)

        return affected

    def get_evaluation_order(self, field_ids: set[str]) -> list[str]:
        """
        Get evaluation order for multiple formula fields.

        Uses topological sort (Kahn's algorithm) to determine
        the order in which fields should be evaluated.

        Args:
            field_ids: Set of formula field IDs to evaluate

        Returns:
            Ordered list of field IDs, or empty list if cycle detected
        """
        # Build in-degree count for relevant fields
        in_degree = {fid: 0 for fid in field_ids}
        queue = deque()

        # Calculate in-degrees based on dependencies
        for fid in field_ids:
            for dep in self.reverse[fid]:
                if dep in field_ids:
                    in_degree[fid] += 1

        # Start with fields that have no dependencies
        for fid in field_ids:
            if in_degree[fid] == 0:
                queue.append(fid)

        # Topological sort
        result = []
        while queue:
            fid = queue.popleft()
            result.append(fid)

            # Reduce in-degree of dependents
            for dependent in self.dependencies[fid]:
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        # Check if we have all fields (no cycle)
        if len(result) != len(field_ids):
            # Cycle detected
            return []

        return result

    def detect_circular_reference(self, field_id: str, depends_on: set[str]) -> bool:
        """
        Check if adding this dependency would create a cycle.

        Uses DFS to detect cycles in the dependency graph.

        Args:
            field_id: ID of the formula field being added/updated
            depends_on: Set of field IDs this formula references

        Returns:
            True if circular reference detected
        """
        if not depends_on:
            return False

        # Check if field_id is in its own dependencies
        if field_id in depends_on:
            return True

        # DFS to check for cycles
        visited = set()
        to_check = list(depends_on)

        while to_check:
            current = to_check.pop()

            if current == field_id:
                return True

            if current in visited:
                continue
            visited.add(current)

            # Check all fields that current depends on
            for dep in self.reverse.get(current, set()):
                to_check.append(dep)

        return False

    def get_dependencies(self, field_id: str) -> set[str]:
        """
        Get direct dependencies of a field.

        Args:
            field_id: ID of the formula field

        Returns:
            Set of field IDs that this field depends on
        """
        return self.reverse.get(field_id, set()).copy()

    def get_dependents(self, field_id: str) -> set[str]:
        """
        Get direct dependents of a field.

        Args:
            field_id: ID of the field

        Returns:
            Set of field IDs that depend on this field
        """
        return self.dependencies.get(field_id, set()).copy()

    def clear(self) -> None:
        """Clear all dependencies from the graph."""
        self.dependencies.clear()
        self.reverse.clear()

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"FormulaDependencyGraph("
            f"fields={len(self.reverse)}, "
            f"edges={sum(len(deps) for deps in self.dependencies.values())})"
        )
