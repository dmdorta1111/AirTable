"""
Post-Serialization Indexing Script

Runs AFTER master_serialize_and_index.py completes.
Enhances serialized models with multi-modal embeddings and search capabilities.

Usage:
    python scripts/post_serialize_index.py --category EMJAC --batch-size 100
"""

import asyncio
import argparse
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pybase.services.brep_graph_encoder import BRepGraphEncoder
from pybase.services.sketch_similarity import SketchSimilarity
from pybase.services.parametric_miner import ParametricMiner
from pybase.services.embedding_generator import EmbeddingGenerator
from pybase.services.serialize_metrics import SerializationMetricsCollector


def get_db_connection(config_path=".env"):
    """Get database connection from config."""
    from dotenv import load_dotenv
    load_dotenv(config_path)

    import os
    db_url = os.getenv("MODEL_DATA_DB_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found in .env file")

    return psycopg2.connect(db_url)


def process_serialized_models_batch(
    conn,
    batch_size=100,
    category_filter=None,
    status_filter="completed"
):
    """
    Process a batch of serialized models to add embeddings.

    Args:
        conn: Database connection
        batch_size: Number of models to process
        category_filter: Optional category filter
        status_filter: Process only models with this status

    Returns:
        Dictionary with processing results
    """
    encoders = {
        "brep": BRepGraphEncoder(),
        "sketch": SketchSimilarity(),
        "parametric": ParametricMiner(),
        "embedding": EmbeddingGenerator(),
    }

    # Fetch serialized models
    query = """
        SELECT id, model_name, serialized_content
        FROM serialized_models
        WHERE 1=1
    """

    params = []

    if category_filter:
        query += " AND category = %s"
        params.append(category_filter)

    if status_filter:
        query += " AND model_name NOT IN (SELECT model_name FROM cad_models)"
        # Only process if not already indexed

    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(batch_size)

    cursor = conn.cursor()
    cursor.execute(query, params)

    rows = cursor.fetchall()

    if not rows:
        return {"status": "no_models", "count": 0}

    results = {
        "processed": 0,
        "skipped": 0,
        "errors": [],
        "start_time": datetime.now(),
    }

    print(f"\nProcessing {len(rows)} serialized models...")

    for row in rows:
        model_id, model_name, serialized_content = row

        try:
            # Parse JSON content
            import json
            data = json.loads(serialized_content)

            # 1. B-Rep graph embedding (from feature_geometry)
            if "feature_geometry" in data:
                brep_emb = encoders["brep"].encode_graph(data["feature_geometry"])
                print(f"  ✓ {model_name}: B-Rep graph embedding ({len(brep_emb)}-dim)")

            # 2. Sketch embeddings (from sketches)
            if "sketches" in data and data["sketches"]:
                sketch_embs = [
                    encoders["sketch"].encode_sketch(s)
                    for s in data["sketches"]
                ]
                print(f"  ✓ {model_name}: {len(sketch_embs)} sketch embeddings")

            # 3. Parametric pattern embedding (from parameters/relations)
            if "parameters" in data or "relations" in data:
                param_emb = encoders["parametric"].encode_parametric_structure(
                    data.get("parameters", {}),
                    data.get("relations", {})
                )
                print(f"  ✓ {model_name}: Parametric embedding ({len(param_emb)}-dim)")

            # 4. Text description for CLIP embedding
            description = generate_description(data)
            text_emb = encoders["embedding"].encode_text(description)
            print(f"  ✓ {model_name}: Text embedding ({len(text_emb)}-dim)")

            # Store in cad_models and cad_model_embeddings tables
            store_model_embeddings(conn, model_id, model_name, data, {
                "brep_graph": locals().get('brep_emb'),
                "sketch": sketch_embs if 'sketch_embs' in locals() else None,
                "parametric": locals().get('param_emb'),
                "text": text_emb,
            })

            results["processed"] += 1

        except Exception as e:
            results["errors"].append(f"{model_name}: {str(e)}")
            results["skipped"] += 1

    results["end_time"] = datetime.now()
    results["duration"] = (results["end_time"] - results["start_time"]).total_seconds()

    return results


def generate_description(serialized_data):
    """Generate text description from serialized data for CLIP encoding."""
    parts = []

    # Model name
    if "model_name" in serialized_data:
        parts.append(f"CAD model: {serialized_data['model_name']}")

    # Category
    if "category" in serialized_data:
        parts.append(f"Category: {serialized_data['category']}")

    # Feature summary
    if "features" in serialized_data:
        feature_types = {}
        for feature in serialized_data["features"]:
            ftype = feature.get("type", "UNKNOWN")
            feature_types[ftype] = feature_types.get(ftype, 0) + 1

        feature_summary = ", ".join([f"{count} {ftype}" for ftype, count in feature_types.items()])
        parts.append(f"Features: {feature_summary}")

    # Parameters
    if "parameters" in serialized_data and "parameters" in serialized_data["parameters"]:
        params = serialized_data["parameters"]["parameters"][:5]  # First 5
        param_summary = ", ".join([f"{p['name']}={p['value']}" for p in params])
        parts.append(f"Parameters: {param_summary}")

    return ". ".join(parts)


def store_model_embeddings(conn, model_id, model_name, serialized_data, embeddings):
    """Store model and embeddings in database."""
    cursor = conn.cursor()

    # Create cad_model record
    cursor.execute("""
        INSERT INTO cad_models (id, model_name, part_number, model_type, category, tags, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (model_name) DO UPDATE SET
            status = EXCLUDED.status,
            updated_at = NOW()
        RETURNING id
    """, (
        model_id,
        model_name,
        model_name,  # part_number = model_name
        serialized_data.get("model_type", "part"),
        serialized_data.get("category"),
        serialized_data.get("tags", []),
        "indexed",
    ))

    # Store embeddings
    for emb_type, emb_vector in embeddings.items():
        if emb_vector is not None:
            cursor.execute("""
                INSERT INTO cad_model_embeddings (model_id, embedding_type, embedding_vector, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (
                model_id,
                emb_type,
                emb_vector.tolist() if hasattr(emb_vector, 'tolist') else emb_vector,
            ))

    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Post-serialization indexing")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size")
    parser.add_argument("--max-models", type=int, help="Maximum models to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")

    args = parser.parse_args()

    print("="*70)
    print("POST-SERIALIZATION INDEXING")
    print("="*70)
    print(f"Category filter: {args.category or 'None'}")
    print(f"Batch size: {args.batch_size}")
    print(f"Max models: {args.max_models or 'No limit'}")

    if args.dry_run:
        print("\nDRY RUN MODE - No changes will be made")
        return

    try:
        conn = get_db_connection()

        total_processed = 0
        batch_num = 0

        while True:
            batch_num += 1
            print(f"\n{'='*70}")
            print(f"Batch {batch_num}")
            print(f"{'='*70}")

            results = process_serialized_models_batch(
                conn,
                batch_size=args.batch_size,
                category_filter=args.category,
            )

            if results["status"] == "no_models":
                print("\n✓ All models processed!")
                break

            print(f"\nBatch results:")
            print(f"  Processed: {results['processed']}")
            print(f"  Skipped:   {results['skipped']}")
            print(f"  Errors:    {len(results['errors'])}")
            print(f"  Duration:  {results['duration']:.1f}s")

            if results["errors"]:
                print("\nErrors:")
                for error in results["errors"][:10]:  # Show first 10
                    print(f"  - {error}")

            total_processed += results["processed"]

            if args.max_models and total_processed >= args.max_models:
                print(f"\nReached max models limit: {args.max_models}")
                break

        conn.close()

        print(f"\n{'='*70}")
        print(f"TOTAL MODELS PROCESSED: {total_processed}")
        print(f"{'='*70}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
