"""Add HNSW vector indexes for CAD model similarity search

Creates pgvector HNSW indexes for fast ANN (Approximate Nearest Neighbor) search.
Run this migration after populating embeddings data.

Revision ID: 4d5e6f7g8h9i
Revises: 3c4d5e6f7g8h
Create Date: 2026-01-22 17:30:10.000000+00:00
"""

from typing import Sequence, Union

from alembic import op

# Revision identifiers, used by Alembic
revision: str = '4d5e6f7g8h9i'
down_revision: Union[str, None] = '3c4d5e6f7g8h'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""

    # NOTE: HNSW indexes commented out because embedding columns are FLOAT[]
    # HNSW indexes require VECTOR type from pgvector extension.
    # To enable HNSW indexes:
    # 1. Change embedding columns from FLOAT[] to VECTOR(N) type
    # 2. Uncomment the index creation statements below
    # 3. Run this migration again

    # Note: Using RAW SQL for HNSW indexes as they're pgvector-specific
    # The m=16, ef_construction=100 parameters are CosCAD-recommended settings

    # B-Rep graph embedding index (for geometry-to-geometry search)
    # op.execute("""
    #     CREATE INDEX ix_cad_embeddings_brep_graph_hnsw
    #     ON pybase.cad_model_embeddings
    #     USING hnsw (brep_graph_embedding vector_cosine_ops)
    #     WITH (m = 16, ef_construction = 100)
    #     WHERE brep_graph_embedding IS NOT NULL
    # """)

    # CLIP text embedding index (for text-to-CAD search)
    # op.execute("""
    #     CREATE INDEX ix_cad_embeddings_clip_text_hnsw
    #     ON pybase.cad_model_embeddings
    #     USING hnsw (clip_text_embedding vector_cosine_ops)
    #     WITH (m = 16, ef_construction = 100)
    #     WHERE clip_text_embedding IS NOT NULL
    # """)

    # CLIP image embedding index (for image-to-CAD search)
    # op.execute("""
    #     CREATE INDEX ix_cad_embeddings_clip_image_hnsw
    #     ON pybase.cad_model_embeddings
    #     USING hnsw (clip_image_embedding vector_cosine_ops)
    #     WITH (m = 16, ef_construction = 100)
    #     WHERE clip_image_embedding IS NOT NULL
    # """)

    # Point cloud geometry embedding index (for shape similarity)
    # op.execute("""
    #     CREATE INDEX ix_cad_embeddings_geometry_hnsw
    #     ON pybase.cad_model_embeddings
    #     USING hnsw (geometry_embedding vector_cosine_ops)
    #     WITH (m = 16, ef_construction = 100)
    #     WHERE geometry_embedding IS NOT NULL
    # """)

    # Fused embedding index (for general cross-modal queries)
    # op.execute("""
    #     CREATE INDEX ix_cad_embeddings_fused_hnsw
    #     ON pybase.cad_model_embeddings
    #     USING hnsw (fused_embedding vector_cosine_ops)
    #     WITH (m = 16, ef_construction = 100)
    #     WHERE fused_embedding IS NOT NULL
    # """)

    # DeepSDF latent index (direct implicit similarity search)
    # op.execute("""
    #     CREATE INDEX ix_cad_models_deepsdf_latent_hnsw
    #     ON pybase.cad_models
    #     USING hnsw (deepsdf_latent vector_cosine_ops)
    #     WITH (m = 16, ef_construction = 100)
    #     WHERE deepsdf_latent IS NOT NULL
    # """)

    # Rendered view embedding index (for sketch-to-CAD search)
    # op.execute("""
    #     CREATE INDEX ix_cad_views_view_embedding_hnsw
    #     ON pybase.cad_rendered_views
    #     USING hnsw (view_embedding vector_cosine_ops)
    #     WITH (m = 16, ef_construction = 64)
    #     WHERE view_embedding IS NOT NULL
    # """)


def downgrade() -> None:
    """Downgrade database schema."""

    op.execute('DROP INDEX IF EXISTS pybase.ix_cad_views_view_embedding_hnsw')
    op.execute('DROP INDEX IF EXISTS pybase.ix_cad_models_deepsdf_latent_hnsw')
    op.execute('DROP INDEX IF EXISTS pybase.ix_cad_embeddings_fused_hnsw')
    op.execute('DROP INDEX IF EXISTS pybase.ix_cad_embeddings_geometry_hnsw')
    op.execute('DROP INDEX IF EXISTS pybase.ix_cad_embeddings_clip_image_hnsw')
    op.execute('DROP INDEX IF EXISTS pybase.ix_cad_embeddings_clip_text_hnsw')
    op.execute('DROP INDEX IF EXISTS pybase.ix_cad_embeddings_brep_graph_hnsw')
