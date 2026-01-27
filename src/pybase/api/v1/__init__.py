"""API v1 routes."""

from fastapi import APIRouter

from pybase.api.v1 import (
    analytics,
    audit,
    auth,
    automations,
    bases,
    cad_indexing,
    cad_search,
    charts,
    comments,
    dashboards,
    extraction,
    fields,
    health,
    realtime,
    records,
    reports,
    search,
    tables,
    users,
    views,
    webhooks,
    workspaces,
)

router = APIRouter()

# Include all v1 routes
router.include_router(health.router, tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
router.include_router(bases.router, prefix="/bases", tags=["bases"])
router.include_router(comments.router, prefix="/comments", tags=["comments"])
router.include_router(tables.router, prefix="/tables", tags=["tables"])
router.include_router(fields.router, prefix="/fields", tags=["fields"])
router.include_router(records.router, prefix="/records", tags=["records"])
router.include_router(views.router, prefix="/views", tags=["views"])
router.include_router(dashboards.router, prefix="/dashboards", tags=["dashboards"])
router.include_router(charts.router, prefix="/charts", tags=["charts"])
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
router.include_router(extraction.router, prefix="/extraction", tags=["extraction"])
router.include_router(cad_indexing.router, prefix="/cad", tags=["cad"])
router.include_router(cad_search.router, prefix="/cad", tags=["cad"])
router.include_router(realtime.router, prefix="/realtime", tags=["realtime"])
router.include_router(search.router, prefix="/search", tags=["search"])
router.include_router(automations.router, prefix="/automations", tags=["automations"])
router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(audit.router, prefix="/audit", tags=["audit"])

__all__ = ["router"]
