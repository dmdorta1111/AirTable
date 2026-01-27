"""Dashboard templates package."""

from src.pybase.templates.dashboard_templates import (
    TEMPLATES,
    DashboardTemplate,
    TemplateWidget,
    get_all_categories,
    get_template_by_id,
    get_templates_by_category,
)

__all__ = [
    "TEMPLATES",
    "DashboardTemplate",
    "TemplateWidget",
    "get_template_by_id",
    "get_templates_by_category",
    "get_all_categories",
]
