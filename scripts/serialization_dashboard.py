"""
Streamlit dashboard for serialization pipeline monitoring.

Displays:
- Serialization progress (models processed, success rate)
- Quality metrics (element_coverage, unrecoverable_unknown)
- Processing time statistics
- Error tracking
- Filtering by category, tags, model_type
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any

import streamlit as st

# Configure page
st.set_page_config(
    page_title="Serialization Monitor",
    page_icon="",
    layout="wide",
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {background: #f0f2f6; padding: 1rem; border-radius: 0.5rem;}
    .status-success {color: #00cc00;}
    .status-failed {color: #cc0000;}
    .status-partial {color: #ff9900;}
</style>
""", unsafe_allow_html=True)


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

@st.cache_resource
def get_sync_engine():
    """Create synchronous SQLAlchemy engine for Streamlit."""
    from sqlalchemy import create_engine
    from sqlalchemy.engine.url import make_url

    # Get DB URL from environment
    import os
    db_url = os.getenv("MODEL_DATA_DB_URL") or os.getenv("DATABASE_URL", "postgresql://pybase:pybase@localhost:5432/pybase")
    # Convert to synchronous
    db_url = str(db_url).replace("+asyncpg", "").replace("asyncpg", "psycopg2")

    return create_engine(db_url, pool_pre_ping=True)


def get_session():
    """Get database session."""
    from sqlalchemy.orm import sessionmaker
    engine = get_sync_engine()
    Session = sessionmaker(bind=engine)
    return Session()


# ============================================================================
# DATA FETCHING
# ============================================================================

def fetch_table_stats() -> dict:
    """Fetch table statistics."""
    import pandas as pd
    from sqlalchemy import text

    session = get_session()
    try:
        # Check if table exists
        check_sql = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'serialized_models'
            )
        """)
        exists = session.execute(check_sql).scalar()
        if not exists:
            return {"error": "Table does not exist"}

        # Get overview stats
        stats_sql = text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE model_type = 'part') as parts,
                COUNT(*) FILTER (WHERE model_type = 'assembly') as assemblies,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '1 hour') as last_hour,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as last_24h,
                MIN(created_at) as first_created,
                MAX(created_at) as last_created
            FROM serialized_models
        """)
        row = session.execute(stats_sql).fetchone()

        # Quality stats
        quality_sql = text("""
            SELECT
                AVG((serialized_content->>'element_coverage')::float) as avg_coverage,
                AVG((serialized_content->>'unrecoverable_unknown')::int) as avg_unknown,
                COUNT(*) FILTER (WHERE (serialized_content->>'element_coverage')::float < 80) as low_quality
            FROM serialized_models
            WHERE serialized_content ? 'element_coverage'
        """)
        quality_row = session.execute(quality_sql).fetchone()

        return {
            "total": row.total or 0,
            "parts": row.parts or 0,
            "assemblies": row.assemblies or 0,
            "last_hour": row.last_hour or 0,
            "last_24h": row.last_24h or 0,
            "first_created": row.first_created.isoformat() if row.first_created else None,
            "last_created": row.last_created.isoformat() if row.last_created else None,
            "avg_coverage": round(float(quality_row.avg_coverage or 0), 1),
            "avg_unknown": round(float(quality_row.avg_unknown or 0), 1),
            "low_quality": quality_row.low_quality or 0,
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()


def fetch_category_breakdown() -> list:
    """Fetch models by category."""
    from sqlalchemy import text

    session = get_session()
    try:
        sql = text("""
            SELECT
                COALESCE(category, 'None') as category,
                COUNT(*) as count,
                AVG(feature_count) as avg_features,
                AVG((serialized_content->>'element_coverage')::float) as avg_coverage
            FROM serialized_models
            GROUP BY category
            ORDER BY count DESC
        """)
        rows = session.execute(sql).fetchall()
        return [
            {
                "category": row.category,
                "count": row.count,
                "avg_features": round(row.avg_features or 0, 1),
                "avg_coverage": round(row.avg_coverage or 0, 1),
            }
            for row in rows
        ]
    except Exception as e:
        st.error(f"Error fetching categories: {e}")
        return []
    finally:
        session.close()


def fetch_recent_models(limit: int = 20) -> list:
    """Fetch recent models."""
    from sqlalchemy import text

    session = get_session()
    try:
        sql = text("""
            SELECT
                model_name,
                model_type,
                category,
                feature_count,
                (serialized_content->>'element_coverage')::float as coverage,
                (serialized_content->>'unrecoverable_unknown')::int as unknown,
                created_at
            FROM serialized_models
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        rows = session.execute(sql, {"limit": limit}).fetchall()
        return [
            {
                "model_name": row.model_name,
                "model_type": row.model_type,
                "category": row.category,
                "feature_count": row.feature_count,
                "coverage": round(float(row.coverage), 1) if row.coverage else None,
                "unknown": row.unknown,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    except Exception as e:
        st.error(f"Error fetching recent models: {e}")
        return []
    finally:
        session.close()


def fetch_quality_distribution() -> list:
    """Fetch quality metric distribution."""
    from sqlalchemy import text

    session = get_session()
    try:
        sql = text("""
            SELECT
                CASE
                    WHEN (serialized_content->>'element_coverage')::float >= 90 THEN 'Excellent (90%+)'
                    WHEN (serialized_content->>'element_coverage')::float >= 80 THEN 'Good (80-90%)'
                    WHEN (serialized_content->>'element_coverage')::float >= 50 THEN 'Fair (50-80%)'
                    ELSE 'Poor (<50%)'
                END as quality_bucket,
                COUNT(*) as count
            FROM serialized_models
            WHERE serialized_content ? 'element_coverage'
            GROUP BY quality_bucket
            ORDER BY
                CASE quality_bucket
                    WHEN 'Excellent (90%+)' THEN 1
                    WHEN 'Good (80-90%)' THEN 2
                    WHEN 'Fair (50-80%)' THEN 3
                    ELSE 4
                END
        """)
        rows = session.execute(sql).fetchall()
        return [{"bucket": row.quality_bucket, "count": row.count} for row in rows]
    except Exception as e:
        st.error(f"Error fetching quality distribution: {e}")
        return []
    finally:
        session.close()


def fetch_processing_trends() -> list:
    """Fetch processing count over time."""
    from sqlalchemy import text

    session = get_session()
    try:
        sql = text("""
            SELECT
                DATE_TRUNC('hour', created_at) as hour,
                COUNT(*) as count
            FROM serialized_models
            WHERE created_at > NOW() - INTERVAL '24 hours'
            GROUP BY hour
            ORDER BY hour
        """)
        rows = session.execute(sql).fetchall()
        return [
            {
                "hour": row.hour.isoformat() if row.hour else None,
                "count": row.count,
            }
            for row in rows
        ]
    except Exception as e:
        st.error(f"Error fetching trends: {e}")
        return []
    finally:
        session.close()


# ============================================================================
# DASHBOARD
# ============================================================================

def main():
    st.title("Serialization Pipeline Monitor")
    st.caption("Real-time monitoring of master serialization pipeline")

    # Auto-refresh
    auto_refresh = st.sidebar.toggle("Auto-refresh (30s)", value=False)
    if auto_refresh:
        st_autorefresh = st.empty()
        import time
        time.sleep(30)
        st_autorefresh.rerun()

    # Fetch all data
    stats = fetch_table_stats()
    categories = fetch_category_breakdown()
    recent = fetch_recent_models()
    quality_dist = fetch_quality_distribution()
    trends = fetch_processing_trends()

    # Error check
    if "error" in stats:
        st.error(f"Database error: {stats['error']}")
        st.info("Ensure the serialized_models table exists and database is accessible.")
        return

    # ============================================================================
    # OVERVIEW METRICS
    # ============================================================================

    st.subheader("Overview")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Models", f"{stats['total']:,}", delta=f"+{stats['last_24h']}" if stats['last_24h'] else "0")

    with col2:
        st.metric("Parts", f"{stats['parts']:,}")

    with col3:
        st.metric("Assemblies", f"{stats['assemblies']:,}")

    with col4:
        coverage_color = "" if stats['avg_coverage'] >= 80 else ""
        st.metric("Avg Coverage", f"{stats['avg_coverage']}%")

    with col5:
        st.metric("Last Hour", f"{stats['last_hour']}")

    # ============================================================================
    # QUALITY METRICS
    # ============================================================================

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Quality Distribution")
        if quality_dist:
            import pandas as pd
            df_quality = pd.DataFrame(quality_dist)
            st.bar_chart(df_quality.set_index("bucket")["count"])
        else:
            st.info("No quality data available")

    with col_right:
        st.subheader("Category Breakdown")
        if categories:
            import pandas as pd
            df_cat = pd.DataFrame(categories)
            st.dataframe(
                df_cat,
                column_config={
                    "category": st.column_config.TextColumn("Category"),
                    "count": st.column_config.NumberColumn("Models"),
                    "avg_features": st.column_config.NumberColumn("Avg Features"),
                    "avg_coverage": st.column_config.NumberColumn("Avg Coverage %"),
                },
                hide_index=True,
            )

    # ============================================================================
    # PROCESSING TRENDS
    # ============================================================================

    st.subheader("Processing Trends (Last 24h)")
    if trends:
        import pandas as pd
        df_trends = pd.DataFrame(trends)
        df_trends['hour'] = pd.to_datetime(df_trends['hour'])
        st.line_chart(df_trends.set_index("hour")["count"])
    else:
        st.info("No trend data available")

    # ============================================================================
    # RECENT MODELS
    # ============================================================================

    st.subheader("Recent Models")
    if recent:
        import pandas as pd
        df_recent = pd.DataFrame(recent)
        df_recent['created_at'] = pd.to_datetime(df_recent['created_at']).dt.strftime('%Y-%m-%d %H:%M')

        # Color code coverage
        def coverage_style(val):
            if val is None:
                return ""
            if val >= 90:
                return "color: #00cc00"
            elif val >= 80:
                return "color: #ff9900"
            else:
                return "color: #cc0000"

        st.dataframe(
            df_recent,
            column_config={
                "model_name": st.column_config.TextColumn("Model Name"),
                "model_type": st.column_config.TextColumn("Type"),
                "category": st.column_config.TextColumn("Category"),
                "feature_count": st.column_config.NumberColumn("Features"),
                "coverage": st.column_config.NumberColumn("Coverage %"),
                "unknown": st.column_config.NumberColumn("Unknown"),
                "created_at": st.column_config.TextColumn("Created"),
            },
            hide_index=True,
        )
    else:
        st.info("No recent models")

    # ============================================================================
    # FILTERS
    # ============================================================================

    with st.expander("Filters"):
        col1, col2, col3 = st.columns(3)

        with col1:
            selected_category = st.selectbox(
                "Filter by Category",
                ["All"] + [c["category"] for c in categories],
            )

        with col2:
            model_type_filter = st.selectbox(
                "Filter by Type",
                ["All", "part", "assembly"],
            )

        with col3:
            coverage_filter = st.selectbox(
                "Filter by Coverage",
                ["All", "Excellent (90%+)", "Good (80-90%)", "Fair (50-80%)", "Poor (<50%)"],
            )

        if selected_category != "All" or model_type_filter != "All" or coverage_filter != "All":
            st.info("Apply filters to query database (implementation needed)")

    # ============================================================================
    # LOW QUALITY ALERTS
    # ============================================================================

    if stats['low_quality'] > 0:
        st.warning(f"⚠️ {stats['low_quality']} models with low element coverage (<80%)")


if __name__ == "__main__":
    main()
