"""BOM flattening service for hierarchical assemblies with quantity rollup."""

import json
from collections import defaultdict
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    BadRequestError,
    NotFoundError,
)
from pybase.extraction.base import ExtractedBOM
from pybase.schemas.extraction import (
    BOMExtractionOptions,
    BOMFlatteningStrategy,
    BOMHierarchyMode,
)


class BOMFlattenerService:
    """Service for flattening hierarchical BOMs with quantity rollup."""

    async def flatten_bom(
        self,
        db: AsyncSession,
        bom_data: dict[str, Any],
        flattening_options: Optional[BOMExtractionOptions] = None,
    ) -> dict[str, Any]:
        """
        Flatten hierarchical BOM with quantity rollup.

        Traverses parent-child relationships and calculates total quantities
        for each part by multiplying quantities up the hierarchy tree.

        Args:
            db: Database session (for potential future lookups)
            bom_data: BOM data with hierarchy information
            flattening_options: Options for how to flatten the BOM

        Returns:
            Dict containing:
                - flattened_items: List of flattened BOM items
                - total_items: Total unique items after flattening
                - hierarchy_depth: Maximum depth of original hierarchy
                - quantity_rolled_up: Whether quantities were rolled up
                - original_items: Count of items before flattening
                - merge_summary: Summary of merged items

        Raises:
            BadRequestError: If BOM data is invalid or missing hierarchy info

        """
        # Use default options if not provided
        if flattening_options is None:
            flattening_options = BOMExtractionOptions(
                hierarchy_mode=BOMHierarchyMode.FLATTENED,
                flattening_strategy=BOMFlatteningStrategy.PATH,
            )

        # Validate BOM data
        self._validate_bom_data(bom_data)

        # Extract BOM structure
        items = bom_data.get("items", [])
        parent_child_map = bom_data.get("parent_child_map", {})
        is_flat = bom_data.get("is_flat", True)

        # If already flat, return as-is with rollup flag
        if is_flat or not parent_child_map:
            return {
                "flattened_items": items,
                "total_items": len(items),
                "hierarchy_depth": 1,
                "quantity_rolled_up": False,
                "original_items": len(items),
                "merge_summary": {
                    "merged_count": 0,
                    "duplicates_found": 0,
                },
            }

        # Build item lookup map
        item_map = self._build_item_map(items)

        # Calculate hierarchy depth
        hierarchy_depth = self._calculate_hierarchy_depth(parent_child_map, item_map)

        # Roll up quantities through hierarchy
        rolled_up_quantities = self._roll_up_quantities(
            items, parent_child_map, item_map
        )

        # Generate flattened list based on strategy
        if flattening_options.flattening_strategy == BOMFlatteningStrategy.PATH:
            flattened_items = self._flatten_with_path(
                items, parent_child_map, item_map, flattening_options
            )
        elif flattening_options.flattening_strategy == BOMFlatteningStrategy.INDUCTED:
            flattened_items = self._flatten_inducted(
                items, parent_child_map, item_map, rolled_up_quantities
            )
        elif flattening_options.flattening_strategy == BOMFlatteningStrategy.LEVEL_PREFIX:
            flattened_items = self._flatten_with_level_prefix(
                items, parent_child_map, item_map, flattening_options
            )
        elif flattening_options.flattening_strategy == BOMFlatteningStrategy.PARENT_REFERENCE:
            flattened_items = self._flatten_with_parent_ref(
                items, parent_child_map, item_map
            )
        else:
            # Default to path strategy
            flattened_items = self._flatten_with_path(
                items, parent_child_map, item_map, flattening_options
            )

        # Merge duplicate items with rolled-up quantities
        merged_items, merge_summary = self._merge_duplicate_items(
            flattened_items, rolled_up_quantities
        )

        return {
            "flattened_items": merged_items,
            "total_items": len(merged_items),
            "hierarchy_depth": hierarchy_depth,
            "quantity_rolled_up": True,
            "original_items": len(items),
            "merge_summary": merge_summary,
        }

    async def preview_flattening(
        self,
        db: AsyncSession,
        bom_data: dict[str, Any],
        flattening_options: Optional[BOMExtractionOptions] = None,
    ) -> dict[str, Any]:
        """
        Preview BOM flattening without applying changes.

        Shows how the hierarchical BOM will be flattened and what the
        quantity rollup will look like.

        Args:
            db: Database session
            bom_data: BOM data with hierarchy information
            flattening_options: Options for how to flatten the BOM

        Returns:
            Dict containing:
                - hierarchy_tree: Visual representation of hierarchy
                - quantity_preview: Preview of rolled-up quantities
                - before_after: Comparison before/after flattening
                - duplicate_groups: Groups of items that will be merged
                - statistics: Statistics about the flattening

        Raises:
            BadRequestError: If BOM data is invalid

        """
        # Validate BOM data
        self._validate_bom_data(bom_data)

        # Extract structure
        items = bom_data.get("items", [])
        parent_child_map = bom_data.get("parent_child_map", {})

        # Build item map
        item_map = self._build_item_map(items)

        # Build hierarchy tree
        hierarchy_tree = self._build_hierarchy_tree(parent_child_map, item_map)

        # Calculate quantity rollup preview
        quantity_preview = self._preview_quantity_rollup(
            items, parent_child_map, item_map
        )

        # Find duplicate groups
        duplicate_groups = self._find_duplicate_groups(items)

        # Calculate statistics
        statistics = {
            "original_item_count": len(items),
            "unique_part_count": len(duplicate_groups),
            "hierarchy_depth": self._calculate_hierarchy_depth(
                parent_child_map, item_map
            ),
            "total_assemblies": len([
                item for item in items
                if item.get("item_id") in parent_child_map
            ]),
            "total_leaf_parts": len(items) - len([
                item for item in items
                if item.get("item_id") in parent_child_map
            ]),
        }

        return {
            "hierarchy_tree": hierarchy_tree,
            "quantity_preview": quantity_preview,
            "duplicate_groups": duplicate_groups,
            "statistics": statistics,
        }

    async def calculate_total_quantities(
        self,
        db: AsyncSession,
        bom_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Calculate total quantities for all parts in hierarchical BOM.

        Recursively traverses the hierarchy and calculates total quantities
        for each part by multiplying parent quantities.

        Args:
            db: Database session
            bom_data: BOM data with hierarchy information

        Returns:
            Dict containing:
                - quantities: Mapping of part_number to total quantity
                - calculation_details: Step-by-step calculation for each part
                - summary: Summary of quantity calculations

        Raises:
            BadRequestError: If BOM data is invalid

        """
        # Validate BOM data
        self._validate_bom_data(bom_data)

        # Extract structure
        items = bom_data.get("items", [])
        parent_child_map = bom_data.get("parent_child_map", {})

        # Build item map
        item_map = self._build_item_map(items)

        # Calculate rolled up quantities
        rolled_up = self._roll_up_quantities(items, parent_child_map, item_map)

        # Build calculation details
        calculation_details = []
        for item_id, quantity in rolled_up.items():
            item = item_map.get(item_id, {})
            part_number = item.get("part_number") or item.get("Part Number", "UNKNOWN")
            original_quantity = item.get("quantity", item.get("Quantity", 1))

            calculation_details.append({
                "item_id": item_id,
                "part_number": part_number,
                "original_quantity": original_quantity,
                "total_quantity": quantity,
                "multiplier": quantity / original_quantity if original_quantity > 0 else 0,
            })

        # Build summary
        summary = {
            "total_unique_parts": len(rolled_up),
            "max_quantity": max(rolled_up.values()) if rolled_up else 0,
            "total_quantity_sum": sum(rolled_up.values()),
        }

        return {
            "quantities": rolled_up,
            "calculation_details": calculation_details,
            "summary": summary,
        }

    # --- Helper Methods ---

    def _validate_bom_data(self, bom_data: dict[str, Any]) -> None:
        """Validate BOM data structure."""
        if not isinstance(bom_data, dict):
            raise BadRequestError("BOM data must be a dictionary")

        if "items" not in bom_data or not isinstance(bom_data["items"], list):
            raise BadRequestError("BOM data must contain 'items' list")

        if not bom_data["items"]:
            raise BadRequestError("BOM items list is empty")

    def _build_item_map(
        self, items: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Build lookup map of items by item_id."""
        item_map = {}
        for item in items:
            item_id = item.get("item_id") or item.get("id")
            if item_id:
                item_map[str(item_id)] = item
        return item_map

    def _calculate_hierarchy_depth(
        self,
        parent_child_map: dict[str, list[str]],
        item_map: dict[str, dict[str, Any]],
    ) -> int:
        """Calculate maximum depth of hierarchy."""
        max_depth = 1

        for parent_id in parent_child_map.keys():
            depth = self._calculate_item_depth(parent_id, parent_child_map, item_map, 1)
            max_depth = max(max_depth, depth)

        return max_depth

    def _calculate_item_depth(
        self,
        item_id: str,
        parent_child_map: dict[str, list[str]],
        item_map: dict[str, dict[str, Any]],
        current_depth: int,
    ) -> int:
        """Recursively calculate depth of an item in hierarchy."""
        children = parent_child_map.get(item_id, [])
        if not children:
            return current_depth

        max_child_depth = current_depth
        for child_id in children:
            child_depth = self._calculate_item_depth(
                child_id, parent_child_map, item_map, current_depth + 1
            )
            max_child_depth = max(max_child_depth, child_depth)

        return max_child_depth

    def _roll_up_quantities(
        self,
        items: list[dict[str, Any]],
        parent_child_map: dict[str, list[str]],
        item_map: dict[str, dict[str, Any]],
    ) -> dict[str, int]:
        """Calculate rolled-up quantities for all items."""
        rolled_up = {}

        # Find root items (items that are not children of any parent)
        all_children = set()
        for children in parent_child_map.values():
            all_children.update(children)

        root_items = []
        for item in items:
            item_id = item.get("item_id") or item.get("id")
            if item_id and str(item_id) not in all_children:
                root_items.append(str(item_id))

        # Roll up quantities from each root
        for root_id in root_items:
            self._roll_up_quantities_recursive(
                root_id, parent_child_map, item_map, rolled_up, multiplier=1
            )

        # Handle items with no hierarchy (standalone items)
        for item in items:
            item_id = item.get("item_id") or item.get("id")
            if item_id and str(item_id) not in rolled_up:
                quantity = item.get("quantity", item.get("Quantity", 1))
                try:
                    rolled_up[str(item_id)] = int(quantity)
                except (ValueError, TypeError):
                    rolled_up[str(item_id)] = 1

        return rolled_up

    def _roll_up_quantities_recursive(
        self,
        item_id: str,
        parent_child_map: dict[str, list[str]],
        item_map: dict[str, dict[str, Any]],
        rolled_up: dict[str, int],
        multiplier: int,
    ) -> None:
        """Recursively calculate rolled-up quantity for an item."""
        item = item_map.get(item_id, {})
        quantity = item.get("quantity", item.get("Quantity", 1))

        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            quantity = 1

        total_quantity = quantity * multiplier

        # Accumulate quantity if item already exists (from another path)
        if item_id in rolled_up:
            rolled_up[item_id] += total_quantity
        else:
            rolled_up[item_id] = total_quantity

        # Recursively process children
        children = parent_child_map.get(item_id, [])
        for child_id in children:
            self._roll_up_quantities_recursive(
                child_id, parent_child_map, item_map, rolled_up, total_quantity
            )

    def _flatten_with_path(
        self,
        items: list[dict[str, Any]],
        parent_child_map: dict[str, list[str]],
        item_map: dict[str, dict[str, Any]],
        options: BOMExtractionOptions,
    ) -> list[dict[str, Any]]:
        """Flatten BOM with path information."""
        flattened = []
        separator = options.path_separator

        # Find root items
        all_children = set()
        for children in parent_child_map.values():
            all_children.update(children)

        for item in items:
            item_id = str(item.get("item_id") or item.get("id"))
            if item_id not in all_children:
                # Root item - start path traversal
                self._flatten_with_path_recursive(
                    item_id,
                    parent_child_map,
                    item_map,
                    flattened,
                    path=[],
                    separator=separator,
                )

        return flattened

    def _flatten_with_path_recursive(
        self,
        item_id: str,
        parent_child_map: dict[str, list[str]],
        item_map: dict[str, dict[str, Any]],
        flattened: list[dict[str, Any]],
        path: list[str],
        separator: str,
    ) -> None:
        """Recursively flatten BOM with path tracking."""
        item = item_map.get(item_id, {})
        part_number = item.get("part_number") or item.get("Part Number", "")

        # Build current path
        current_path = path + [part_number] if part_number else path

        # Create flattened item
        flattened_item = {
            **item,
            "_hierarchy_path": separator.join(current_path),
            "_hierarchy_level": len(current_path),
        }

        # Only add leaf nodes (items with no children) to flattened list
        children = parent_child_map.get(item_id, [])
        if not children:
            flattened.append(flattened_item)
        else:
            # Process children
            for child_id in children:
                self._flatten_with_path_recursive(
                    child_id,
                    parent_child_map,
                    item_map,
                    flattened,
                    current_path,
                    separator,
                )

    def _flatten_inducted(
        self,
        items: list[dict[str, Any]],
        parent_child_map: dict[str, list[str]],
        item_map: dict[str, dict[str, Any]],
        rolled_up_quantities: dict[str, int],
    ) -> list[dict[str, Any]]:
        """Flatten BOM with inducted quantities (only leaf items)."""
        flattened = []

        # Only include leaf items (items with no children)
        for item in items:
            item_id = str(item.get("item_id") or item.get("id"))
            children = parent_child_map.get(item_id, [])

            if not children:
                # Leaf item - add with rolled-up quantity
                flattened_item = {
                    **item,
                    "_rolled_up_quantity": rolled_up_quantities.get(item_id, 1),
                }
                flattened.append(flattened_item)

        return flattened

    def _flatten_with_level_prefix(
        self,
        items: list[dict[str, Any]],
        parent_child_map: dict[str, list[str]],
        item_map: dict[str, dict[str, Any]],
        options: BOMExtractionOptions,
    ) -> list[dict[str, Any]]:
        """Flatten BOM with level prefix on part numbers."""
        flattened = []
        separator = options.level_prefix_separator

        # Find root items
        all_children = set()
        for children in parent_child_map.values():
            all_children.update(children)

        for item in items:
            item_id = str(item.get("item_id") or item.get("id"))
            if item_id not in all_children:
                self._flatten_with_level_prefix_recursive(
                    item_id,
                    parent_child_map,
                    item_map,
                    flattened,
                    level=1,
                    separator=separator,
                )

        return flattened

    def _flatten_with_level_prefix_recursive(
        self,
        item_id: str,
        parent_child_map: dict[str, list[str]],
        item_map: dict[str, dict[str, Any]],
        flattened: list[dict[str, Any]],
        level: int,
        separator: str,
    ) -> None:
        """Recursively flatten BOM with level prefix."""
        item = item_map.get(item_id, {})
        part_number = item.get("part_number") or item.get("Part Number", "")

        # Create flattened item with level prefix
        flattened_item = {
            **item,
            "_level_prefix": f"{level}{separator} ",
            "_hierarchy_level": level,
        }

        # Only add leaf nodes
        children = parent_child_map.get(item_id, [])
        if not children:
            flattened.append(flattened_item)
        else:
            for child_id in children:
                self._flatten_with_level_prefix_recursive(
                    child_id,
                    parent_child_map,
                    item_map,
                    flattened,
                    level + 1,
                    separator,
                )

    def _flatten_with_parent_ref(
        self,
        items: list[dict[str, Any]],
        parent_child_map: dict[str, list[str]],
        item_map: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Flatten BOM with parent reference information."""
        flattened = []

        # Build reverse map (child -> parent)
        child_parent_map = {}
        for parent_id, child_ids in parent_child_map.items():
            for child_id in child_ids:
                child_parent_map[child_id] = parent_id

        # Add parent reference to each item
        for item in items:
            item_id = str(item.get("item_id") or item.get("id"))
            children = parent_child_map.get(item_id, [])

            if not children:
                # Leaf item
                parent_id = child_parent_map.get(item_id)
                parent_item = item_map.get(parent_id, {}) if parent_id else {}
                parent_part_number = (
                    parent_item.get("part_number") or parent_item.get("Part Number", "")
                )

                flattened_item = {
                    **item,
                    "_parent_id": parent_id,
                    "_parent_part_number": parent_part_number,
                }
                flattened.append(flattened_item)

        return flattened

    def _merge_duplicate_items(
        self,
        items: list[dict[str, Any]],
        rolled_up_quantities: dict[str, int],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Merge duplicate items by part number and sum quantities."""
        merged = {}
        duplicates_found = 0

        for item in items:
            part_number = (
                item.get("part_number") or item.get("Part Number") or item.get("ITEM", "")
            )

            if not part_number:
                continue

            if part_number in merged:
                # Duplicate - merge quantities
                duplicates_found += 1
                existing = merged[part_number]
                existing_qty = existing.get("_rolled_up_quantity", 1)
                item_qty = item.get("_rolled_up_quantity", 1)
                existing["_rolled_up_quantity"] = existing_qty + item_qty
            else:
                # New item
                merged[part_number] = item

        merged_list = list(merged.values())

        merge_summary = {
            "merged_count": duplicates_found,
            "duplicates_found": duplicates_found,
            "final_unique_count": len(merged_list),
        }

        return merged_list, merge_summary

    def _build_hierarchy_tree(
        self,
        parent_child_map: dict[str, list[str]],
        item_map: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build visual hierarchy tree for preview."""
        tree = []

        # Find roots
        all_children = set()
        for children in parent_child_map.values():
            all_children.update(children)

        for item_id, children in parent_child_map.items():
            if str(item_id) not in all_children:
                # This is a root
                tree.append(
                    self._build_tree_node(item_id, parent_child_map, item_map)
                )

        return tree

    def _build_tree_node(
        self,
        item_id: str,
        parent_child_map: dict[str, list[str]],
        item_map: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Recursively build tree node."""
        item = item_map.get(item_id, {})
        part_number = item.get("part_number") or item.get("Part Number", "UNKNOWN")
        quantity = item.get("quantity", item.get("Quantity", 1))

        node = {
            "item_id": item_id,
            "part_number": part_number,
            "quantity": quantity,
            "children": [],
        }

        for child_id in parent_child_map.get(item_id, []):
            node["children"].append(
                self._build_tree_node(child_id, parent_child_map, item_map)
            )

        return node

    def _preview_quantity_rollup(
        self,
        items: list[dict[str, Any]],
        parent_child_map: dict[str, list[str]],
        item_map: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Preview quantity rollup calculations."""
        rolled_up = self._roll_up_quantities(items, parent_child_map, item_map)

        preview = []
        for item_id, total_qty in rolled_up.items():
            item = item_map.get(item_id, {})
            part_number = item.get("part_number") or item.get("Part Number", "UNKNOWN")
            original_qty = item.get("quantity", item.get("Quantity", 1))

            preview.append({
                "part_number": part_number,
                "original_quantity": original_qty,
                "total_quantity": total_qty,
                "multiplier": total_qty / original_qty if original_qty > 0 else 0,
            })

        return preview

    def _find_duplicate_groups(
        self, items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Find groups of duplicate items by part number."""
        groups = defaultdict(list)

        for item in items:
            part_number = (
                item.get("part_number") or item.get("Part Number") or item.get("ITEM", "")
            )
            if part_number:
                groups[part_number].append(item)

        # Convert to list of groups
        duplicate_groups = []
        for part_number, group_items in groups.items():
            if len(group_items) > 1:
                duplicate_groups.append({
                    "part_number": part_number,
                    "count": len(group_items),
                    "items": group_items,
                })

        return duplicate_groups
