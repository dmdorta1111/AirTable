"""BOM comparison service for highlighting new vs existing parts."""

import json
from collections import defaultdict
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
)
from pybase.models.base import Base
from pybase.models.field import Field
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


class BOMComparisonService:
    """Service for comparing BOM data against existing parts database."""

    async def compare_bom_to_database(
        self,
        db: AsyncSession,
        user_id: str,
        bom_items: list[dict[str, Any]],
        table_id: str,
        field_mapping: dict[str, str],
        comparison_options: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Compare BOM items against existing database records.

        Identifies new parts, existing parts, and highlights differences
        between BOM data and database records.

        Args:
            db: Database session
            user_id: User ID requesting comparison
            bom_items: List of BOM items to compare
            table_id: Table ID to compare against
            field_mapping: Mapping of BOM fields to table field IDs
            comparison_options: Optional comparison settings

        Returns:
            Dict containing:
                - new_parts: Parts not found in database
                - existing_parts: Parts found in database with comparison
                - summary: Comparison statistics and metadata

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have access to table
            BadRequestError: If BOM data or field mapping is invalid

        """
        # Use default options if not provided
        if comparison_options is None:
            comparison_options = {
                "include_field_differences": True,
                "highlight_value_changes": True,
                "group_by_match_status": True,
            }

        # Verify table exists and user has access
        table = await self._get_table_with_access(db, table_id, user_id)

        # Validate field mapping
        self._validate_field_mapping(field_mapping)

        # Get all existing records from table
        records = await self._get_table_records(db, table_id)

        # Build lookup index from existing records
        record_index = self._build_record_index(records, field_mapping)

        # Compare each BOM item
        new_parts = []
        existing_parts = []
        updated_parts = []

        for idx, item in enumerate(bom_items):
            part_number = self._extract_part_number(item)

            if not part_number:
                # No part number - treat as new
                new_parts.append({
                    **item,
                    "_comparison_index": idx,
                    "_status": "no_part_number",
                })
                continue

            if part_number not in record_index:
                # Part not found in database
                new_parts.append({
                    **item,
                    "_comparison_index": idx,
                    "_status": "new",
                })
            else:
                # Part found - compare details
                existing_record = record_index[part_number]
                comparison_result = self._compare_item_to_record(
                    item, existing_record, field_mapping, comparison_options
                )

                if comparison_result["has_differences"]:
                    updated_parts.append({
                        **item,
                        "_comparison_index": idx,
                        "_status": "updated",
                        "_existing_record": existing_record,
                        "_differences": comparison_result["differences"],
                    })
                    existing_parts.append({
                        **item,
                        "_comparison_index": idx,
                        "_status": "existing_with_changes",
                        "_existing_record": existing_record,
                        "_differences": comparison_result["differences"],
                    })
                else:
                    existing_parts.append({
                        **item,
                        "_comparison_index": idx,
                        "_status": "existing_match",
                        "_existing_record": existing_record,
                    })

        # Build summary statistics
        summary = {
            "total_bom_items": len(bom_items),
            "new_parts_count": len(new_parts),
            "existing_parts_count": len(existing_parts),
            "updated_parts_count": len(updated_parts),
            "database_records_count": len(records),
            "match_percentage": round(
                (len(existing_parts) / len(bom_items) * 100) if bom_items else 0, 2
            ),
        }

        return {
            "new_parts": new_parts,
            "existing_parts": existing_parts,
            "updated_parts": updated_parts,
            "summary": summary,
        }

    async def highlight_new_parts(
        self,
        db: AsyncSession,
        user_id: str,
        bom_items: list[dict[str, Any]],
        table_id: str,
        field_mapping: dict[str, str],
    ) -> dict[str, Any]:
        """
        Highlight only new parts from BOM that don't exist in database.

        Filters BOM items to return only parts not found in the database,
        useful for identifying parts that need to be added or quoted.

        Args:
            db: Database session
            user_id: User ID requesting highlight
            bom_items: List of BOM items to filter
            table_id: Table ID to check against
            field_mapping: Mapping of BOM fields to table field IDs

        Returns:
            Dict containing:
                - new_parts: List of parts not in database
                - filtered_count: Number of new parts found
                - original_count: Total BOM items processed
                - existing_part_numbers: List of part numbers that already exist

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have access to table

        """
        # Verify table access
        await self._get_table_with_access(db, table_id, user_id)

        # Get existing records
        records = await self._get_table_records(db, table_id)
        record_index = self._build_record_index(records, field_mapping)

        # Extract existing part numbers
        existing_part_numbers = set(record_index.keys())

        # Filter for new parts only
        new_parts = []
        for idx, item in enumerate(bom_items):
            part_number = self._extract_part_number(item)

            if not part_number or part_number not in existing_part_numbers:
                new_parts.append({
                    **item,
                    "_comparison_index": idx,
                    "_is_new": True,
                })

        return {
            "new_parts": new_parts,
            "filtered_count": len(new_parts),
            "original_count": len(bom_items),
            "existing_part_numbers": sorted(list(existing_part_numbers)),
        }

    async def compare_multiple_boms(
        self,
        db: AsyncSession,
        user_id: str,
        bom_data_list: list[dict[str, Any]],
        comparison_mode: str = "union",
    ) -> dict[str, Any]:
        """
        Compare multiple BOMs to identify common and unique parts.

        Analyzes multiple BOMs to find parts that are:
        - Common across all BOMs
        - Unique to specific BOMs
        - Shared between some but not all BOMs

        Args:
            db: Database session
            user_id: User ID requesting comparison
            bom_data_list: List of BOM data dictionaries with items
            comparison_mode: How to compare ('union', 'intersection', 'difference')

        Returns:
            Dict containing:
                - common_parts: Parts found in all BOMs
                - unique_parts: Parts unique to each BOM
                - shared_parts: Parts shared between some BOMs
                - statistics: Comparison statistics

        Raises:
            BadRequestError: If BOM data list is invalid

        """
        if not bom_data_list or len(bom_data_list) < 2:
            raise BadRequestError(
                "At least two BOMs are required for comparison"
            )

        # Extract part numbers from each BOM
        bom_part_maps = []
        for bom_idx, bom_data in enumerate(bom_data_list):
            items = bom_data.get("items", [])
            part_map = defaultdict(list)

            for item in items:
                part_number = self._extract_part_number(item)
                if part_number:
                    part_map[part_number].append(item)

            bom_part_maps.append({
                "bom_index": bom_idx,
                "part_map": part_map,
                "part_numbers": set(part_map.keys()),
            })

        # Analyze based on comparison mode
        if comparison_mode == "union":
            result = self._compare_union(bom_part_maps)
        elif comparison_mode == "intersection":
            result = self._compare_intersection(bom_part_maps)
        elif comparison_mode == "difference":
            result = self._compare_difference(bom_part_maps)
        else:
            raise BadRequestError(
                f"Invalid comparison_mode: {comparison_mode}. "
                "Must be 'union', 'intersection', or 'difference'"
            )

        return result

    async def generate_comparison_report(
        self,
        db: AsyncSession,
        user_id: str,
        bom_items: list[dict[str, Any]],
        table_id: str,
        field_mapping: dict[str, str],
    ) -> dict[str, Any]:
        """
        Generate detailed comparison report for BOM vs database.

        Creates a comprehensive report showing:
        - New parts requiring action
        - Existing parts with field differences
        - Statistics and recommendations

        Args:
            db: Database session
            user_id: User ID requesting report
            bom_items: List of BOM items to report on
            table_id: Table ID to compare against
            field_mapping: Mapping of BOM fields to table field IDs

        Returns:
            Dict containing:
                - report_sections: Organized report data
                - recommendations: Action items based on comparison
                - statistics: Summary statistics
                - visualization_data: Data for charts/graphs

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have access to table

        """
        # Perform comparison
        comparison_result = await self.compare_bom_to_database(
            db, user_id, bom_items, table_id, field_mapping
        )

        # Generate report sections
        report_sections = {
            "executive_summary": self._generate_executive_summary(
                comparison_result
            ),
            "new_parts_section": self._generate_new_parts_section(
                comparison_result["new_parts"]
            ),
            "existing_parts_section": self._generate_existing_parts_section(
                comparison_result["existing_parts"]
            ),
            "field_differences_section": self._generate_differences_section(
                comparison_result["updated_parts"]
            ),
        }

        # Generate recommendations
        recommendations = self._generate_recommendations(comparison_result)

        # Prepare visualization data
        visualization_data = self._prepare_visualization_data(comparison_result)

        return {
            "report_sections": report_sections,
            "recommendations": recommendations,
            "statistics": comparison_result["summary"],
            "visualization_data": visualization_data,
            "generated_at": comparison_result.get("generated_at"),
        }

    # --- Helper Methods ---

    async def _get_table_with_access(
        self,
        db: AsyncSession,
        table_id: str,
        user_id: str,
    ) -> Table:
        """Get table and verify user has access."""
        table = await db.get(Table, table_id)
        if not table or table.is_deleted:
            raise NotFoundError("Table not found")

        # Check workspace access
        base = await self._get_base(db, str(table.base_id))
        workspace = await self._get_workspace(db, str(base.workspace_id))
        member = await self._get_workspace_member(db, str(workspace.id), user_id)
        if not member:
            raise PermissionDeniedError("You don't have access to this table")

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

    async def _get_table_records(
        self,
        db: AsyncSession,
        table_id: str,
    ) -> list[Record]:
        """Get all records for a table."""
        query = select(Record).where(
            Record.table_id == table_id,
            Record.is_deleted.is_(False),
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    def _validate_field_mapping(
        self,
        field_mapping: dict[str, str],
    ) -> None:
        """Validate field mapping structure."""
        if not isinstance(field_mapping, dict):
            raise BadRequestError("Field mapping must be a dictionary")

        if not field_mapping:
            raise BadRequestError("Field mapping cannot be empty")

        # Check for part number mapping
        has_part_number = any(
            key.lower() in ["part_number", "part number", "part-number"]
            for key in field_mapping.keys()
        )

        if not has_part_number:
            raise BadRequestError(
                "Field mapping must include part number field"
            )

    def _build_record_index(
        self,
        records: list[Record],
        field_mapping: dict[str, str],
    ) -> dict[str, dict[str, Any]]:
        """Build lookup index from records by part number."""
        index = {}

        # Find the part number field ID
        part_number_field_id = None
        for bom_field, table_field_id in field_mapping.items():
            if bom_field.lower() in ["part_number", "part number", "part-number"]:
                part_number_field_id = table_field_id
                break

        if not part_number_field_id:
            return index

        for record in records:
            try:
                data = json.loads(record.data) if isinstance(record.data, str) else record.data
                part_number = data.get(part_number_field_id)

                if part_number:
                    index[str(part_number)] = {
                        "id": str(record.id),
                        "data": data,
                    }
            except (json.JSONDecodeError, TypeError):
                continue

        return index

    def _extract_part_number(
        self,
        item: dict[str, Any],
    ) -> Optional[str]:
        """Extract part number from item using common field names."""
        part_number = (
            item.get("part_number") or
            item.get("Part Number") or
            item.get("PART_NUMBER") or
            item.get("partNumber") or
            item.get("item_number") or
            item.get("Item Number")
        )
        return str(part_number) if part_number else None

    def _compare_item_to_record(
        self,
        item: dict[str, Any],
        existing_record: dict[str, Any],
        field_mapping: dict[str, str],
        options: dict[str, Any],
    ) -> dict[str, Any]:
        """Compare BOM item to existing record and identify differences."""
        differences = []
        record_data = existing_record.get("data", {})

        for bom_field, table_field_id in field_mapping.items():
            bom_value = item.get(bom_field)
            record_value = record_data.get(table_field_id)

            # Skip if values match
            if bom_value == record_value:
                continue

            # Normalize values for comparison
            bom_normalized = self._normalize_value(bom_value)
            record_normalized = self._normalize_value(record_value)

            if bom_normalized != record_normalized:
                differences.append({
                    "field": bom_field,
                    "field_id": table_field_id,
                    "bom_value": bom_value,
                    "record_value": record_value,
                    "change_type": self._determine_change_type(
                        bom_value, record_value
                    ),
                })

        return {
            "has_differences": len(differences) > 0,
            "differences": differences if options.get("include_field_differences") else [],
            "difference_count": len(differences),
        }

    def _normalize_value(
        self,
        value: Any,
    ) -> str:
        """Normalize value for comparison."""
        if value is None:
            return ""
        return str(value).strip().lower()

    def _determine_change_type(
        self,
        bom_value: Any,
        record_value: Any,
    ) -> str:
        """Determine the type of change between values."""
        if record_value is None:
            return "added"
        if bom_value is None:
            return "removed"
        return "modified"

    def _compare_union(
        self,
        bom_part_maps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compare BOMs using union mode (all unique parts)."""
        all_parts = set()
        common_parts = set()

        # Get all part numbers
        for bom_data in bom_part_maps:
            all_parts.update(bom_data["part_numbers"])

        # Find parts common to all BOMs
        if bom_part_maps:
            common_parts = bom_part_maps[0]["part_numbers"].copy()
            for bom_data in bom_part_maps[1:]:
                common_parts.intersection_update(bom_data["part_numbers"])

        # Find unique parts per BOM
        unique_parts = []
        for bom_data in bom_part_maps:
            other_parts = set()
            for other_bom in bom_part_maps:
                if other_bom["bom_index"] != bom_data["bom_index"]:
                    other_parts.update(other_bom["part_numbers"])

            unique_to_bom = bom_data["part_numbers"] - other_parts
            unique_parts.append({
                "bom_index": bom_data["bom_index"],
                "unique_part_numbers": list(unique_to_bom),
                "count": len(unique_to_bom),
            })

        return {
            "common_parts": list(common_parts),
            "common_count": len(common_parts),
            "unique_parts": unique_parts,
            "total_unique_count": sum(p["count"] for p in unique_parts),
            "all_parts_count": len(all_parts),
        }

    def _compare_intersection(
        self,
        bom_part_maps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compare BOMs using intersection mode (common parts only)."""
        if not bom_part_maps:
            return {
                "common_parts": [],
                "common_count": 0,
            }

        common_parts = bom_part_maps[0]["part_numbers"].copy()
        for bom_data in bom_part_maps[1:]:
            common_parts.intersection_update(bom_data["part_numbers"])

        return {
            "common_parts": list(common_parts),
            "common_count": len(common_parts),
        }

    def _compare_difference(
        self,
        bom_part_maps: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compare BOMs using difference mode (parts not in all BOMs)."""
        if len(bom_part_maps) < 2:
            return {
                "different_parts": [],
                "different_count": 0,
            }

        # Find parts in first BOM that are not in others
        first_bom_parts = bom_part_maps[0]["part_numbers"]
        other_bom_parts = set()
        for bom_data in bom_part_maps[1:]:
            other_bom_parts.update(bom_data["part_numbers"])

        different_parts = first_bom_parts - other_bom_parts

        return {
            "different_parts": list(different_parts),
            "different_count": len(different_parts),
            "reference_bom_index": bom_part_maps[0]["bom_index"],
        }

    def _generate_executive_summary(
        self,
        comparison_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate executive summary of comparison."""
        summary = comparison_result["summary"]

        return {
            "title": "BOM Comparison Executive Summary",
            "total_items": summary["total_bom_items"],
            "match_rate": f"{summary['match_percentage']}%",
            "new_items": summary["new_parts_count"],
            "existing_items": summary["existing_parts_count"],
            "updated_items": summary["updated_parts_count"],
            "key_findings": self._generate_key_findings(summary),
        }

    def _generate_key_findings(
        self,
        summary: dict[str, Any],
    ) -> list[str]:
        """Generate key findings from statistics."""
        findings = []

        if summary["new_parts_count"] > 0:
            findings.append(
                f"Found {summary['new_parts_count']} new parts requiring database entry"
            )

        if summary["updated_parts_count"] > 0:
            findings.append(
                f"Identified {summary['updated_parts_count']} parts with data differences"
            )

        if summary["match_percentage"] >= 90:
            findings.append(
                "High match rate indicates good data consistency"
            )
        elif summary["match_percentage"] < 50:
            findings.append(
                "Low match rate suggests significant data discrepancies"
            )

        return findings

    def _generate_new_parts_section(
        self,
        new_parts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate new parts report section."""
        return {
            "title": "New Parts Requiring Action",
            "count": len(new_parts),
            "parts": [
                {
                    "part_number": self._extract_part_number(p),
                    "description": p.get("description", ""),
                    "quantity": p.get("quantity", ""),
                }
                for p in new_parts
            ],
        }

    def _generate_existing_parts_section(
        self,
        existing_parts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate existing parts report section."""
        exact_matches = [
            p for p in existing_parts
            if p.get("_status") == "existing_match"
        ]

        return {
            "title": "Existing Parts in Database",
            "total_count": len(existing_parts),
            "exact_match_count": len(exact_matches),
            "with_changes_count": len(existing_parts) - len(exact_matches),
        }

    def _generate_differences_section(
        self,
        updated_parts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate field differences report section."""
        return {
            "title": "Parts with Data Differences",
            "count": len(updated_parts),
            "differences": [
                {
                    "part_number": self._extract_part_number(p),
                    "field_count": len(p.get("_differences", [])),
                    "fields_changed": [
                        d["field"] for d in p.get("_differences", [])
                    ],
                }
                for p in updated_parts
            ],
        }

    def _generate_recommendations(
        self,
        comparison_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate actionable recommendations."""
        recommendations = []
        summary = comparison_result["summary"]

        # New parts recommendations
        if summary["new_parts_count"] > 0:
            recommendations.append({
                "priority": "high",
                "category": "data_entry",
                "action": "add_new_parts",
                "description": f"Add {summary['new_parts_count']} new parts to database",
                "estimated_time": f"{summary['new_parts_count'] * 2} minutes",
            })

        # Updated parts recommendations
        if summary["updated_parts_count"] > 0:
            recommendations.append({
                "priority": "medium",
                "category": "data_review",
                "action": "review_differences",
                "description": f"Review {summary['updated_parts_count']} parts with data differences",
                "estimated_time": f"{summary['updated_parts_count']} minutes",
            })

        return recommendations

    def _prepare_visualization_data(
        self,
        comparison_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Prepare data for charts and visualizations."""
        summary = comparison_result["summary"]

        return {
            "pie_chart": {
                "new_parts": summary["new_parts_count"],
                "existing_parts": summary["existing_parts_count"],
                "updated_parts": summary["updated_parts_count"],
            },
            "bar_chart": {
                "bom_items": summary["total_bom_items"],
                "database_records": summary["database_records_count"],
                "matched": summary["existing_parts_count"],
                "unmatched": summary["new_parts_count"],
            },
            "summary_text": (
                f"Compared {summary['total_bom_items']} BOM items against "
                f"{summary['database_records_count']} database records. "
                f"Match rate: {summary['match_percentage']}%"
            ),
        }
