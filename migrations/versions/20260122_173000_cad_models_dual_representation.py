"""Add CAD models dual-representation schema (B-Rep + DeepSDF)

Implements CosCAD-inspired dual storage:
- B-Rep genome for parametric editing
- DeepSDF latent for similarity search
- Multiple embedding types for cross-modal retrieval
- Assembly hierarchy support
- Manufacturing feature metadata

Revision ID: 3c4d5e6f7g8h
Revises: 2a3b4c5d6e7f
Create Date: 2026-01-22 17:30:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = '3c4d5e6f7g8h'
down_revision: Union[str, None] = '2a3b4c5d6e7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Enable pgvector extension if not already enabled
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Enable postgis for spatial queries on bounding boxes
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')

    # ================================================================
    # CAD MODELS TABLE - Dual Representation (B-Rep + DeepSDF)
    # ================================================================
    op.create_table(
        'cad_models',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=True),

        # File metadata
        sa.Column('file_name', sa.String(500), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=False),  # step, iges, dxf, ifc, etc.
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('file_hash', sa.String(64), nullable=True),  # SHA-256 for deduplication
        sa.Column('storage_path', sa.String(1000), nullable=True),  # B2/S3 path

        # B-Rep Genome Storage
        sa.Column('brep_genome', postgresql.JSONB(), nullable=True),  # Feature tree, topology
        sa.Column('brep_topology_compressed', postgresql.BYTEA(), nullable=True),  # Compressed B-Rep
        sa.Column('feature_tree', postgresql.JSONB(), nullable=True),  # Parametric history
        sa.Column('face_count', sa.Integer(), nullable=True),
        sa.Column('edge_count', sa.Integer(), nullable=True),
        sa.Column('vertex_count', sa.Integer(), nullable=True),

        # DeepSDF Implicit Representation
        sa.Column('deepsdf_latent', postgresql.ARRAY(sa.Float(), dimensions=1), nullable=True),  # 256-dim

        # Point cloud for rendering/analysis
        sa.Column('point_cloud', postgresql.JSONB(), nullable=True),  # {points: [[x,y,z],...], count: N}
        sa.Column('point_cloud_compressed', postgresql.BYTEA(), nullable=True),

        # Bounding box (3D)
        sa.Column('bounding_box', postgresql.JSONB(), nullable=True),  # {min: [x,y,z], max: [x,y,z]}

        # Manufacturing metadata
        sa.Column('material', sa.String(200), nullable=True),
        sa.Column('mass_kg', sa.Float(), nullable=True),
        sa.Column('volume_cm3', sa.Float(), nullable=True),
        sa.Column('surface_area_cm2', sa.Float(), nullable=True),

        # Category/classification
        sa.Column('category_label', sa.String(200), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=True),

        # Source info
        sa.Column('source_system', sa.String(100), nullable=True),  # creo, solidworks, autocad, etc.
        sa.Column('extraction_version', sa.String(50), nullable=True),

        # Timestamps
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),

        # Foreign keys
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['pybase.users.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['workspace_id'],
            ['pybase.workspaces.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='pybase',
    )

    # ================================================================
    # MULTIMODAL EMBEDDINGS TABLE
    # ================================================================
    op.create_table(
        'cad_model_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('cad_model_id', postgresql.UUID(as_uuid=False), nullable=False),

        # B-Rep graph embedding (UV-Net, BC-NET, etc.)
        sa.Column('brep_graph_embedding', postgresql.ARRAY(sa.Float(), dimensions=1), nullable=True),  # 512-dim

        # CLIP embeddings for cross-modal retrieval
        sa.Column('clip_text_embedding', postgresql.ARRAY(sa.Float(), dimensions=1), nullable=True),  # 512-dim
        sa.Column('clip_image_embedding', postgresql.ARRAY(sa.Float(), dimensions=1), nullable=True),  # 512-dim

        # Point cloud geometry embedding (PointNet++, DGCNN)
        sa.Column('geometry_embedding', postgresql.ARRAY(sa.Float(), dimensions=1), nullable=True),  # 1024-dim

        # Fused/combined embedding for general queries
        sa.Column('fused_embedding', postgresql.ARRAY(sa.Float(), dimensions=1), nullable=True),  # 512-dim

        # LSH buckets for coarse filtering (Tri-Index optimization)
        sa.Column('lsh_bucket_1', sa.Integer(), nullable=True),
        sa.Column('lsh_bucket_2', sa.Integer(), nullable=True),
        sa.Column('lsh_bucket_3', sa.Integer(), nullable=True),
        sa.Column('lsh_bucket_4', sa.Integer(), nullable=True),

        # Product quantization codes (compressed feature representation)
        sa.Column('pq_codes', postgresql.BYTEA(), nullable=True),

        # Metadata
        sa.Column('model_version', sa.String(50), nullable=True),  # Encoder version used
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ['cad_model_id'],
            ['pybase.cad_models.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cad_model_id', name='uq_cad_model_embeddings_cad_model_id'),
        schema='pybase',
    )

    # ================================================================
    # ASSEMBLY HIERARCHY TABLE
    # ================================================================
    op.create_table(
        'cad_assembly_relations',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('parent_model_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('child_model_id', postgresql.UUID(as_uuid=False), nullable=False),

        # Transformation matrix (4x4 for position/orientation)
        sa.Column('transform_matrix', postgresql.ARRAY(sa.Float(), dimensions=2), nullable=True),

        # Assembly metadata
        sa.Column('instance_name', sa.String(200), nullable=True),  # Instance name in assembly
        sa.Column('instance_count', sa.Integer(), nullable=False, server_default='1'),  # For repeated parts
        sa.Column('relation_type', sa.String(50), nullable=False, server_default='component'),  # component, subassembly, etc.
        sa.Column('constraints', postgresql.JSONB(), nullable=True),  # Mating constraints

        # Timestamps
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ['parent_model_id'],
            ['pybase.cad_models.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['child_model_id'],
            ['pybase.cad_models.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='pybase',
    )

    # ================================================================
    # MANUFACTURING FEATURES TABLE
    # ================================================================
    op.create_table(
        'cad_manufacturing_features',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('cad_model_id', postgresql.UUID(as_uuid=False), nullable=False),

        # Feature identification
        sa.Column('feature_type', sa.String(100), nullable=False),  # hole, fillet, chamfer, pocket, etc.
        sa.Column('feature_name', sa.String(200), nullable=True),
        sa.Column('feature_identifier', sa.String(200), nullable=True),  # CAD system's internal ID

        # Feature parameters
        sa.Column('parameters', postgresql.JSONB(), nullable=True),  # {diameter: 10, depth: 5, ...}
        sa.Column('tolerance', postgresql.JSONB(), nullable=True),  # GD&T info

        # Location/extent
        sa.Column('location', postgresql.JSONB(), nullable=True),  # Center point or reference location
        sa.Column('extent', postgresql.JSONB(), nullable=True),  # Bounding box of feature

        # Classification
        sa.Column('machining_operation', sa.String(100), nullable=True),  # drill, mill, turn, etc.
        sa.Column('is_additive', sa.Boolean(), nullable=False, server_default='false'),

        # Timestamps
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ['cad_model_id'],
            ['pybase.cad_models.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='pybase',
    )

    # ================================================================
    # RENDERED VIEWS TABLE (for image-based retrieval)
    # ================================================================
    op.create_table(
        'cad_rendered_views',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('cad_model_id', postgresql.UUID(as_uuid=False), nullable=False),

        # View specification
        sa.Column('view_type', sa.String(50), nullable=False),  # front, top, iso, canonical_0, etc.
        sa.Column('view_angle', postgresql.JSONB(), nullable=True),  # {azimuth: 45, elevation: 30}

        # Storage reference
        sa.Column('storage_bucket', sa.String(200), nullable=True),  # B2/S3 bucket
        sa.Column('storage_key', sa.String(500), nullable=True),  # File key

        # View embedding for retrieval
        sa.Column('view_embedding', postgresql.ARRAY(sa.Float(), dimensions=1), nullable=True),  # 512-dim

        # Metadata
        sa.Column('resolution', postgresql.ARRAY(sa.Integer()), nullable=True),  # [width, height]
        sa.Column('render_settings', postgresql.JSONB(), nullable=True),  # Renderer settings

        # Timestamps
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),

        sa.ForeignKeyConstraint(
            ['cad_model_id'],
            ['pybase.cad_models.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='pybase',
    )

    # ================================================================
    # INDEXES - CAD MODELS
    # ================================================================
    op.create_index(
        'ix_cad_models_user_id',
        'cad_models',
        ['user_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_cad_models_workspace_id',
        'cad_models',
        ['workspace_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_cad_models_file_hash',
        'cad_models',
        ['file_hash'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_cad_models_file_type',
        'cad_models',
        ['file_type'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_cad_models_category',
        'cad_models',
        ['category_label'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_cad_models_tags',
        'cad_models',
        ['tags'],
        unique=False,
        schema='pybase',
        postgresql_using='gin',
    )

    # ================================================================
    # INDEXES - EMBEDDINGS (HNSW for vector similarity search)
    # ================================================================
    # Note: HNSW indexes require pgvector extension
    # These will be created after data is populated via separate migration
    # to avoid errors during empty table creation

    # Indexes for LSH bucket filtering
    op.create_index(
        'ix_cad_embeddings_lsh',
        'cad_model_embeddings',
        ['lsh_bucket_1', 'lsh_bucket_2', 'lsh_bucket_3', 'lsh_bucket_4'],
        unique=False,
        schema='pybase',
    )

    # ================================================================
    # INDEXES - ASSEMBLY RELATIONS
    # ================================================================
    op.create_index(
        'ix_cad_assembly_parent',
        'cad_assembly_relations',
        ['parent_model_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_cad_assembly_child',
        'cad_assembly_relations',
        ['child_model_id'],
        unique=False,
        schema='pybase',
    )

    # ================================================================
    # INDEXES - MANUFACTURING FEATURES
    # ================================================================
    op.create_index(
        'ix_cad_features_model_id',
        'cad_manufacturing_features',
        ['cad_model_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_cad_features_type',
        'cad_manufacturing_features',
        ['feature_type'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_cad_features_machining',
        'cad_manufacturing_features',
        ['machining_operation'],
        unique=False,
        schema='pybase',
    )

    # ================================================================
    # INDEXES - RENDERED VIEWS
    # ================================================================
    op.create_index(
        'ix_cad_views_model_id',
        'cad_rendered_views',
        ['cad_model_id'],
        unique=False,
        schema='pybase',
    )
    op.create_index(
        'ix_cad_views_type',
        'cad_rendered_views',
        ['view_type'],
        unique=False,
        schema='pybase',
    )

    # ================================================================
    # MATERIALIZED VIEW FOR SIMILARITY SEARCH
    # ================================================================
    op.execute("""
        CREATE MATERIALIZED VIEW pybase.cad_model_search_index AS
        SELECT
            cm.id,
            cm.file_name,
            cm.file_type,
            cm.category_label,
            cm.tags,
            cm.bounding_box,
            cm.material,
            emb.brep_graph_embedding,
            emb.clip_text_embedding,
            emb.clip_image_embedding,
            emb.geometry_embedding,
            emb.fused_embedding,
            emb.lsh_bucket_1,
            emb.lsh_bucket_2,
            emb.lsh_bucket_3,
            emb.lsh_bucket_4,
            cm.created_at
        FROM pybase.cad_models cm
        LEFT JOIN pybase.cad_model_embeddings emb ON cm.id = emb.cad_model_id
    """)

    # Index on materialized view for faster lookups
    op.create_index(
        'ix_cad_search_idx_category',
        'cad_model_search_index',
        ['category_label'],
        unique=False,
        schema='pybase',
    )

    # Add PostGIS columns for spatial queries
    op.execute("""
        ALTER TABLE pybase.cad_models
        ADD COLUMN IF NOT EXISTS bbox_3d geometry(PolygonZ, 0)
    """)

    op.execute("""
        ALTER TABLE pybase.cad_models
        ADD COLUMN IF NOT EXISTS centroid_3d geometry(PointZ, 0)
    """)

    # Spatial index for bounding box queries
    op.execute("""
        CREATE INDEX ix_cad_models_bbox_gist
        ON pybase.cad_models USING GIST (bbox_3d)
    """)


def downgrade() -> None:
    """Downgrade database schema."""

    # Drop materialized view
    op.execute('DROP MATERIALIZED VIEW IF EXISTS pybase.cad_model_search_index')

    # Drop indexes
    op.drop_index('ix_cad_models_bbox_gist', table_name='cad_models', schema='pybase')
    op.drop_index('ix_cad_search_idx_category', table_name='cad_model_search_index', schema='pybase')

    # Drop PostGIS columns
    op.execute('ALTER TABLE pybase.cad_models DROP COLUMN IF EXISTS centroid_3d')
    op.execute('ALTER TABLE pybase.cad_models DROP COLUMN IF EXISTS bbox_3d')

    # Drop table indexes
    op.drop_index('ix_cad_views_type', table_name='cad_rendered_views', schema='pybase')
    op.drop_index('ix_cad_views_model_id', table_name='cad_rendered_views', schema='pybase')

    op.drop_index('ix_cad_features_machining', table_name='cad_manufacturing_features', schema='pybase')
    op.drop_index('ix_cad_features_type', table_name='cad_manufacturing_features', schema='pybase')
    op.drop_index('ix_cad_features_model_id', table_name='cad_manufacturing_features', schema='pybase')

    op.drop_index('ix_cad_assembly_child', table_name='cad_assembly_relations', schema='pybase')
    op.drop_index('ix_cad_assembly_parent', table_name='cad_assembly_relations', schema='pybase')

    op.drop_index('ix_cad_embeddings_lsh', table_name='cad_model_embeddings', schema='pybase')

    op.drop_index('ix_cad_models_tags', table_name='cad_models', schema='pybase')
    op.drop_index('ix_cad_models_category', table_name='cad_models', schema='pybase')
    op.drop_index('ix_cad_models_file_type', table_name='cad_models', schema='pybase')
    op.drop_index('ix_cad_models_file_hash', table_name='cad_models', schema='pybase')
    op.drop_index('ix_cad_models_workspace_id', table_name='cad_models', schema='pybase')
    op.drop_index('ix_cad_models_user_id', table_name='cad_models', schema='pybase')

    # Drop tables (reverse order due to foreign keys)
    op.drop_table('cad_rendered_views', schema='pybase')
    op.drop_table('cad_manufacturing_features', schema='pybase')
    op.drop_table('cad_assembly_relations', schema='pybase')
    op.drop_table('cad_model_embeddings', schema='pybase')
    op.drop_table('cad_models', schema='pybase')

    # Note: We don't drop pgvector/postgis extensions as other tables might use them
