"""Add document intelligence tables for unified engineering document extraction

This migration adds tables for:
- DocumentGroups: Master records for linked file sets
- DocumentGroupMembers: Junction linking files to groups
- ExtractedMetadata: Unified extraction tracking with JSONB storage
- ExtractedDimensions: Searchable dimensional data index
- ExtractedParameters: CAD parameters key-value index
- ExtractedMaterials: Material specifications and properties
- ExtractedBOMItems: Bill of Materials entries

Also adds columns to existing CloudFiles table:
- extraction_status: Tracks extraction progress
- document_group_id: Links to parent DocumentGroup

Revision ID: a1b2c3d4e5f6
Revises: 5e6f7g8h9i0j
Create Date: 2026-01-25 17:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "5e6f7g8h9i0j"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create document intelligence tables and enums."""

    # =========================================================================
    # Create ENUM types
    # =========================================================================
    linking_method_enum = postgresql.ENUM(
        "auto_filename",
        "auto_folder",
        "auto_project",
        "manual",
        name="linking_method",
        create_type=True,
    )
    linking_method_enum.create(op.get_bind(), checkfirst=True)

    document_role_enum = postgresql.ENUM(
        "source_cad",
        "drawing_pdf",
        "drawing_dxf",
        "udf",
        name="document_role",
        create_type=True,
    )
    document_role_enum.create(op.get_bind(), checkfirst=True)

    extraction_source_type_enum = postgresql.ENUM(
        "pdf",
        "dxf",
        "creo_part",
        "creo_asm",
        "autocad",
        name="extraction_source_type",
        create_type=True,
    )
    extraction_source_type_enum.create(op.get_bind(), checkfirst=True)

    extraction_status_enum = postgresql.ENUM(
        "pending",
        "processing",
        "completed",
        "failed",
        "skipped",
        name="extraction_status",
        create_type=True,
    )
    extraction_status_enum.create(op.get_bind(), checkfirst=True)

    dimension_type_enum = postgresql.ENUM(
        "linear",
        "angular",
        "radial",
        "diameter",
        "ordinate",
        "arc_length",
        "tolerance",
        name="dimension_type",
        create_type=True,
    )
    dimension_type_enum.create(op.get_bind(), checkfirst=True)

    tolerance_type_enum = postgresql.ENUM(
        "symmetric",
        "asymmetric",
        "limits",
        "basic",
        "reference",
        name="tolerance_type",
        create_type=True,
    )
    tolerance_type_enum.create(op.get_bind(), checkfirst=True)

    # =========================================================================
    # Create pg_trgm extension for text search indexes
    # =========================================================================
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # =========================================================================
    # TABLE 1: document_groups (create FIRST before FK references it)
    # =========================================================================
    op.create_table(
        "document_groups",
        sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
        # Identity fields
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("project_code", sa.String(100), nullable=True),
        sa.Column("item_number", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        # Linking metadata
        sa.Column("linking_method", sa.String(50), nullable=False, server_default="auto_filename"),
        sa.Column("linking_confidence", sa.Numeric(3, 2), nullable=False, server_default="1.0"),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default="false"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="pybase",
    )

    # Indexes for document_groups
    op.create_index("ix_document_groups_name", "document_groups", ["name"], schema="pybase")
    op.create_index("ix_document_groups_project_code", "document_groups", ["project_code"], schema="pybase")
    op.create_index("ix_document_groups_item_number", "document_groups", ["item_number"], schema="pybase")
    op.create_index("ix_document_groups_needs_review", "document_groups", ["needs_review"], schema="pybase")
    op.create_index("ix_document_groups_created_at", "document_groups", ["created_at"], schema="pybase")

    # =========================================================================
    # Add columns to existing CloudFiles table (AFTER document_groups exists)
    # =========================================================================
    op.add_column(
        "CloudFiles",
        sa.Column(
            "extraction_status",
            sa.String(50),
            nullable=False,
            server_default="pending",
        ),
        schema="pybase",
    )
    op.add_column(
        "CloudFiles",
        sa.Column(
            "document_group_id",
            sa.UUID(as_uuid=False),
            nullable=True,
        ),
        schema="pybase",
    )

    # Add FK for document_group_id (now document_groups exists)
    op.create_foreign_key(
        "fk_cloudfiles_document_group",
        "CloudFiles",
        "document_groups",
        ["document_group_id"],
        ["id"],
        ondelete="SET NULL",
        source_schema="pybase",
        referent_schema="pybase",
    )

    # Add indexes for new CloudFiles columns
    op.create_index(
        "ix_cloudfiles_extraction_status",
        "CloudFiles",
        ["extraction_status"],
        schema="pybase",
    )
    op.create_index(
        "ix_cloudfiles_document_group_id",
        "CloudFiles",
        ["document_group_id"],
        schema="pybase",
    )

    # =========================================================================
    # TABLE 2: document_group_members
    # =========================================================================
    op.create_table(
        "document_group_members",
        sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
        # Parent group reference
        sa.Column(
            "group_id",
            sa.UUID(as_uuid=False),
            sa.ForeignKey("pybase.document_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Polymorphic file references
        # CloudFiles.ID is INTEGER (existing table)
        sa.Column("cloud_file_id", sa.Integer(), nullable=True),
        # cad_models.id is text/UUID (existing table in pybase schema)
        sa.Column(
            "cad_model_id",
            sa.String(),
            sa.ForeignKey("pybase.cad_models.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("udf_definition_id", sa.String(), nullable=True),
        # Member metadata
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="pybase",
    )

    # Indexes for document_group_members
    op.create_index("ix_dgm_group_id", "document_group_members", ["group_id"], schema="pybase")
    op.create_index("ix_dgm_cloud_file_id", "document_group_members", ["cloud_file_id"], schema="pybase")
    op.create_index("ix_dgm_cad_model_id", "document_group_members", ["cad_model_id"], schema="pybase")
    op.create_index("ix_dgm_role", "document_group_members", ["role"], schema="pybase")
    op.create_index(
        "ix_dgm_unique_group_cloud",
        "document_group_members",
        ["group_id", "cloud_file_id"],
        unique=True,
        schema="pybase",
        postgresql_where=sa.text("cloud_file_id IS NOT NULL"),
    )
    op.create_index(
        "ix_dgm_unique_group_cad",
        "document_group_members",
        ["group_id", "cad_model_id"],
        unique=True,
        schema="pybase",
        postgresql_where=sa.text("cad_model_id IS NOT NULL"),
    )

    # =========================================================================
    # TABLE 3: extracted_metadata
    # =========================================================================
    op.create_table(
        "extracted_metadata",
        sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
        # Source references
        sa.Column("cloud_file_id", sa.Integer(), nullable=True),
        sa.Column(
            "cad_model_id",
            sa.String(),
            sa.ForeignKey("pybase.cad_models.id", ondelete="CASCADE"),
            nullable=True,
        ),
        # Source identification
        sa.Column("source_type", sa.String(50), nullable=False),
        # Extraction tracking
        sa.Column("extraction_type", sa.String(50), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("extraction_status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("extraction_completeness", sa.Numeric(3, 2), nullable=True),
        # Raw extracted data
        sa.Column("raw_data", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("worker_id", sa.String(100), nullable=True),
        # Summary flags
        sa.Column("has_dimensions", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("has_parameters", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("has_bom", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("has_feature_tree", sa.Boolean(), nullable=False, server_default="false"),
        # Summary counts
        sa.Column("dimension_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parameter_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feature_count", sa.Integer(), nullable=False, server_default="0"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="pybase",
    )

    # Indexes for extracted_metadata
    op.create_index("ix_em_cloud_file_id", "extracted_metadata", ["cloud_file_id"], schema="pybase")
    op.create_index("ix_em_cad_model_id", "extracted_metadata", ["cad_model_id"], schema="pybase")
    op.create_index("ix_em_source_type", "extracted_metadata", ["source_type"], schema="pybase")
    op.create_index("ix_em_extraction_status", "extracted_metadata", ["extraction_status"], schema="pybase")
    op.create_index("ix_em_extracted_at", "extracted_metadata", ["extracted_at"], schema="pybase")
    op.create_index(
        "ix_em_has_dimensions",
        "extracted_metadata",
        ["has_dimensions"],
        schema="pybase",
        postgresql_where=sa.text("has_dimensions = true"),
    )
    op.create_index(
        "ix_em_has_bom",
        "extracted_metadata",
        ["has_bom"],
        schema="pybase",
        postgresql_where=sa.text("has_bom = true"),
    )
    op.create_index(
        "ix_em_raw_data",
        "extracted_metadata",
        ["raw_data"],
        schema="pybase",
        postgresql_using="gin",
    )

    # =========================================================================
    # TABLE 4: extracted_dimensions
    # =========================================================================
    op.create_table(
        "extracted_dimensions",
        sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
        # Parent references
        sa.Column(
            "metadata_id",
            sa.UUID(as_uuid=False),
            sa.ForeignKey("pybase.extracted_metadata.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("cloud_file_id", sa.Integer(), nullable=True),
        # Dimension value
        sa.Column("value", sa.Numeric(15, 6), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False, server_default="mm"),
        # Tolerance data
        sa.Column("tolerance_plus", sa.Numeric(10, 6), nullable=True),
        sa.Column("tolerance_minus", sa.Numeric(10, 6), nullable=True),
        sa.Column("tolerance_type", sa.String(50), nullable=True),
        # Dimension metadata
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("dimension_type", sa.String(50), nullable=False, server_default="linear"),
        sa.Column("layer", sa.String(100), nullable=True),
        sa.Column("feature_id", sa.String(100), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        # Position data
        sa.Column("position_x", sa.Numeric(15, 6), nullable=True),
        sa.Column("position_y", sa.Numeric(15, 6), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="pybase",
    )

    # Indexes for extracted_dimensions
    op.create_index("ix_ed_metadata_id", "extracted_dimensions", ["metadata_id"], schema="pybase")
    op.create_index("ix_ed_cloud_file_id", "extracted_dimensions", ["cloud_file_id"], schema="pybase")
    op.create_index("ix_ed_value", "extracted_dimensions", ["value"], schema="pybase")
    op.create_index("ix_ed_value_unit", "extracted_dimensions", ["value", "unit"], schema="pybase")
    op.create_index("ix_ed_label", "extracted_dimensions", ["label"], schema="pybase")
    op.create_index("ix_ed_dimension_type", "extracted_dimensions", ["dimension_type"], schema="pybase")
    op.create_index("ix_ed_layer", "extracted_dimensions", ["layer"], schema="pybase")
    op.create_index("ix_ed_value_range", "extracted_dimensions", ["value", "tolerance_plus", "tolerance_minus"], schema="pybase")
    op.create_index(
        "ix_ed_label_trgm",
        "extracted_dimensions",
        ["label"],
        schema="pybase",
        postgresql_using="gin",
        postgresql_ops={"label": "gin_trgm_ops"},
    )

    # =========================================================================
    # TABLE 5: extracted_parameters
    # =========================================================================
    op.create_table(
        "extracted_parameters",
        sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
        # Parent references
        sa.Column(
            "metadata_id",
            sa.UUID(as_uuid=False),
            sa.ForeignKey("pybase.extracted_metadata.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cad_model_id",
            sa.String(),
            sa.ForeignKey("pybase.cad_models.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Parameter identity
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("value_numeric", sa.Numeric(20, 8), nullable=True),
        sa.Column("value_type", sa.String(50), nullable=False, server_default="string"),
        # Categorization
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("is_designated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("units", sa.String(50), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="pybase",
    )

    # Indexes for extracted_parameters
    op.create_index("ix_ep_metadata_id", "extracted_parameters", ["metadata_id"], schema="pybase")
    op.create_index("ix_ep_cad_model_id", "extracted_parameters", ["cad_model_id"], schema="pybase")
    op.create_index("ix_ep_name", "extracted_parameters", ["name"], schema="pybase")
    op.create_index("ix_ep_value", "extracted_parameters", ["value"], schema="pybase")
    op.create_index("ix_ep_value_numeric", "extracted_parameters", ["value_numeric"], schema="pybase")
    op.create_index("ix_ep_category", "extracted_parameters", ["category"], schema="pybase")
    op.create_index(
        "ix_ep_is_designated",
        "extracted_parameters",
        ["is_designated"],
        schema="pybase",
        postgresql_where=sa.text("is_designated = true"),
    )
    op.create_index("ix_ep_name_value", "extracted_parameters", ["name", "value"], schema="pybase")
    op.create_index(
        "ix_ep_name_trgm",
        "extracted_parameters",
        ["name"],
        schema="pybase",
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_ep_value_trgm",
        "extracted_parameters",
        ["value"],
        schema="pybase",
        postgresql_using="gin",
        postgresql_ops={"value": "gin_trgm_ops"},
    )

    # =========================================================================
    # TABLE 6: extracted_materials
    # =========================================================================
    op.create_table(
        "extracted_materials",
        sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
        # Parent references
        sa.Column(
            "metadata_id",
            sa.UUID(as_uuid=False),
            sa.ForeignKey("pybase.extracted_metadata.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("cloud_file_id", sa.Integer(), nullable=True),
        # Material identification
        sa.Column("material_name", sa.String(255), nullable=False),
        sa.Column("material_spec", sa.String(255), nullable=True),
        # Material properties
        sa.Column("finish", sa.String(100), nullable=True),
        sa.Column("thickness", sa.Numeric(10, 4), nullable=True),
        sa.Column("thickness_unit", sa.String(20), nullable=False, server_default="mm"),
        # Additional properties
        sa.Column("properties", postgresql.JSONB(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="pybase",
    )

    # Indexes for extracted_materials
    op.create_index("ix_emat_metadata_id", "extracted_materials", ["metadata_id"], schema="pybase")
    op.create_index("ix_emat_cloud_file_id", "extracted_materials", ["cloud_file_id"], schema="pybase")
    op.create_index("ix_emat_material_name", "extracted_materials", ["material_name"], schema="pybase")
    op.create_index("ix_emat_material_spec", "extracted_materials", ["material_spec"], schema="pybase")
    op.create_index("ix_emat_finish", "extracted_materials", ["finish"], schema="pybase")
    op.create_index(
        "ix_emat_properties",
        "extracted_materials",
        ["properties"],
        schema="pybase",
        postgresql_using="gin",
    )
    op.create_index(
        "ix_emat_material_name_trgm",
        "extracted_materials",
        ["material_name"],
        schema="pybase",
        postgresql_using="gin",
        postgresql_ops={"material_name": "gin_trgm_ops"},
    )

    # =========================================================================
    # TABLE 7: extracted_bom_items
    # =========================================================================
    op.create_table(
        "extracted_bom_items",
        sa.Column("id", sa.UUID(as_uuid=False), primary_key=True, nullable=False),
        # Parent reference
        sa.Column(
            "metadata_id",
            sa.UUID(as_uuid=False),
            sa.ForeignKey("pybase.extracted_metadata.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # BOM item data
        sa.Column("item_number", sa.String(50), nullable=True),
        sa.Column("part_number", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="1.0"),
        # Additional fields
        sa.Column("material", sa.String(255), nullable=True),
        sa.Column("source_table", sa.String(100), nullable=True),
        # Extended properties
        sa.Column("properties", postgresql.JSONB(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="pybase",
    )

    # Indexes for extracted_bom_items
    op.create_index("ix_ebom_metadata_id", "extracted_bom_items", ["metadata_id"], schema="pybase")
    op.create_index("ix_ebom_part_number", "extracted_bom_items", ["part_number"], schema="pybase")
    op.create_index("ix_ebom_item_number", "extracted_bom_items", ["item_number"], schema="pybase")
    op.create_index("ix_ebom_material", "extracted_bom_items", ["material"], schema="pybase")
    op.create_index(
        "ix_ebom_properties",
        "extracted_bom_items",
        ["properties"],
        schema="pybase",
        postgresql_using="gin",
    )
    op.create_index(
        "ix_ebom_part_number_trgm",
        "extracted_bom_items",
        ["part_number"],
        schema="pybase",
        postgresql_using="gin",
        postgresql_ops={"part_number": "gin_trgm_ops"},
    )


def downgrade() -> None:
    """Drop document intelligence tables and enums."""

    # Drop tables in reverse order (respecting FK dependencies)
    op.drop_table("extracted_bom_items", schema="pybase")
    op.drop_table("extracted_materials", schema="pybase")
    op.drop_table("extracted_parameters", schema="pybase")
    op.drop_table("extracted_dimensions", schema="pybase")
    op.drop_table("extracted_metadata", schema="pybase")
    op.drop_table("document_group_members", schema="pybase")
    op.drop_table("document_groups", schema="pybase")

    # Drop CloudFiles columns
    op.drop_index("ix_cloudfiles_document_group_id", table_name="CloudFiles", schema="pybase")
    op.drop_index("ix_cloudfiles_extraction_status", table_name="CloudFiles", schema="pybase")
    op.drop_constraint("fk_cloudfiles_document_group", "CloudFiles", schema="pybase")
    op.drop_column("CloudFiles", "document_group_id", schema="pybase")
    op.drop_column("CloudFiles", "extraction_status", schema="pybase")

    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS tolerance_type")
    op.execute("DROP TYPE IF EXISTS dimension_type")
    op.execute("DROP TYPE IF EXISTS extraction_status")
    op.execute("DROP TYPE IF EXISTS extraction_source_type")
    op.execute("DROP TYPE IF EXISTS document_role")
    op.execute("DROP TYPE IF EXISTS linking_method")
