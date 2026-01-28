"""API v1 routes."""

from fastapi import APIRouter

from pybase.api.v1 import (
    analytics,
    auth,
    automations,
    bases,
    cad_indexing,
    cad_search,
    charts,
    comments,
    custom_reports,
    dashboards,
    extraction,
    fields,
    health,
    metrics,
    oidc,
    realtime,
    records,
    reports,
    saml,
    scim,
    search,
    sso_config,
    tables,
    trash,
    undo_redo,
    users,
    views,
    webhooks,
    workspaces,
)

router = APIRouter()

# Include all v1 routes
router.include_router(health.router, tags=["health"])
router.include_router(metrics.router, tags=["metrics"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
router.include_router(bases.router, prefix="/bases", tags=["bases"])
router.include_router(comments.router, prefix="/comments", tags=["comments"])
router.include_router(tables.router, prefix="/tables", tags=["tables"])
router.include_router(undo_redo.router, prefix="/undo-redo", tags=["undo-redo"])
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
router.include_router(custom_reports.router, prefix="/custom-reports", tags=["custom-reports"])
router.include_router(
    custom_reports.templates_router, prefix="/report-templates", tags=["report-templates"]
)
router.include_router(trash.router, prefix="/trash", tags=["trash"])
# SSO routes
router.include_router(oidc.router, prefix="/oidc", tags=["sso", "oidc"])
router.include_router(saml.router, prefix="/saml", tags=["sso", "saml"])
router.include_router(sso_config.router, prefix="/sso", tags=["sso", "config"])
router.include_router(scim.router, prefix="/scim", tags=["sso", "scim"])

__all__ = ["router"]
