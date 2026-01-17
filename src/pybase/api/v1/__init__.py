"""API v1 routes."""

from fastapi import APIRouter

from pybase.api.v1 import (
    auth,
    automations,
    bases,
    extraction,
    fields,
    health,
    realtime,
    records,
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
router.include_router(tables.router, prefix="/tables", tags=["tables"])
router.include_router(fields.router, prefix="/fields", tags=["fields"])
router.include_router(records.router, prefix="/records", tags=["records"])
router.include_router(views.router, prefix="/views", tags=["views"])
router.include_router(extraction.router, prefix="/extraction", tags=["extraction"])
router.include_router(realtime.router, prefix="/realtime", tags=["realtime"])
router.include_router(automations.router, prefix="/automations", tags=["automations"])
router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])

__all__ = ["router"]
