"""Add data integrity constraints to document intelligence tables

This migration adds CHECK constraints to prevent:
- Circular/invalid document group member references
- Infinite/NaN dimension values in extracted_dimensions
- Negative dimension values (must be non-negative for engineering data)

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-26 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# Revision identifiers, used by Alembic
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add data integrity constraints."""

    # =========================================================================
    # Constraint 1: DocumentGroupMember - exactly one file reference must be set
    # =========================================================================
    # This prevents both cloud_file_id and cad_model_id being null (invalid)
    # or both being non-null (ambiguous polymorphic reference)
    op.create_check_constraint(
        "ck_dgm_exactly_one_file_ref",
        "document_group_members",
        "(cloud_file_id IS NOT NULL)::integer + (cad_model_id IS NOT NULL)::integer = 1",
        schema="pybase",
    )

    # =========================================================================
    # Constraint 2: ExtractedDimension - value must be finite and non-negative
    # =========================================================================
    # PostgreSQL Numeric type can store special values: Infinity, -Infinity, NaN
    # These are not valid for engineering dimensions - use isfinite() to reject
    # Also require value >= 0 (negative dimensions normalized to absolute value)
    op.create_check_constraint(
        "ck_extracted_dimensions_value_valid",
        "extracted_dimensions",
        "value IS NOT NULL AND isfinite(value) AND value >= 0",
        schema="pybase",
    )

    # =========================================================================
    # Constraint 3: ExtractedDimension - tolerance values must also be finite
    # =========================================================================
    # Tolerances can be zero or positive (stored as absolute values)
    # They should also be finite (not NaN or infinity)
    op.create_check_constraint(
        "ck_extracted_dimensions_tolerance_plus_valid",
        "extracted_dimensions",
        "tolerance_plus IS NULL OR (isfinite(tolerance_plus) AND tolerance_plus >= 0)",
        schema="pybase",
    )
    op.create_check_constraint(
        "ck_extracted_dimensions_tolerance_minus_valid",
        "extracted_dimensions",
        "tolerance_minus IS NULL OR (isfinite(tolerance_minus) AND tolerance_minus >= 0)",
        schema="pybase",
    )


def downgrade() -> None:
    """Remove data integrity constraints."""

    # Drop dimension tolerance constraints
    op.drop_constraint(
        "ck_extracted_dimensions_tolerance_minus_valid",
        "extracted_dimensions",
        schema="pybase",
    )
    op.drop_constraint(
        "ck_extracted_dimensions_tolerance_plus_valid",
        "extracted_dimensions",
        schema="pybase",
    )

    # Drop dimension value constraint
    op.drop_constraint(
        "ck_extracted_dimensions_value_valid",
        "extracted_dimensions",
        schema="pybase",
    )

    # Drop document group member constraint
    op.drop_constraint(
        "ck_dgm_exactly_one_file_ref",
        "document_group_members",
        schema="pybase",
    )
