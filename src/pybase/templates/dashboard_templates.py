"""
Dashboard template configurations for the dashboard builder.

This module defines pre-built dashboard templates that users can select
when creating new dashboards. Templates match the frontend templates
in DashboardTemplates.tsx.
"""

from typing import Literal, TypedDict


class TemplateWidget(TypedDict):
    """Widget configuration for dashboard templates."""

    type: Literal["chart", "pivot", "metric", "text"]
    title: str
    description: str
    chartType: Literal["line", "bar", "pie", "scatter", "gauge"] | None


class DashboardTemplate(TypedDict):
    """Dashboard template configuration."""

    id: str
    name: str
    description: str
    category: Literal["engineering", "project", "quality", "operations", "general"]
    icon_name: str  # Icon identifier for frontend mapping
    widgets: list[TemplateWidget]
    tags: list[str]


# Pre-defined dashboard templates
TEMPLATES: list[DashboardTemplate] = [
    {
        "id": "engineering-cost-tracking",
        "name": "Engineering Cost Tracking",
        "description": "Track and analyze engineering costs, spending trends, and budget utilization",
        "category": "engineering",
        "icon_name": "dollar-sign",
        "tags": ["costs", "budget", "spending", "finance"],
        "widgets": [
            {
                "type": "metric",
                "title": "Total Monthly Spend",
                "description": "Current month total engineering costs",
                "chartType": None,
            },
            {
                "type": "chart",
                "chartType": "line",
                "title": "Cost Trend Over Time",
                "description": "Monthly spending trends for the past year",
            },
            {
                "type": "chart",
                "chartType": "pie",
                "title": "Cost by Category",
                "description": "Breakdown of costs by engineering department",
            },
            {
                "type": "chart",
                "chartType": "bar",
                "title": "Top Projects by Cost",
                "description": "Highest spending projects this quarter",
            },
            {
                "type": "pivot",
                "title": "Cost Analysis Table",
                "description": "Detailed pivot table of costs by project and category",
                "chartType": None,
            },
        ],
    },
    {
        "id": "quality-metrics",
        "name": "Quality Metrics Dashboard",
        "description": "Monitor defects, quality trends, and compliance metrics for engineering quality",
        "category": "quality",
        "icon_name": "check-circle",
        "tags": ["quality", "defects", "compliance", "testing"],
        "widgets": [
            {
                "type": "metric",
                "title": "Open Defects",
                "description": "Total number of open quality issues",
                "chartType": None,
            },
            {
                "type": "chart",
                "chartType": "line",
                "title": "Defect Trend",
                "description": "Defect count trends over the past 6 months",
            },
            {
                "type": "chart",
                "chartType": "bar",
                "title": "Defects by Severity",
                "description": "Distribution of defects by severity level",
            },
            {
                "type": "chart",
                "chartType": "pie",
                "title": "Defects by Component",
                "description": "Which components have the most issues",
            },
            {
                "type": "chart",
                "chartType": "gauge",
                "title": "Quality Score",
                "description": "Overall quality score based on defect metrics",
            },
        ],
    },
    {
        "id": "project-status",
        "name": "Project Status Overview",
        "description": "Track project progress, milestones, and deliverables across engineering teams",
        "category": "project",
        "icon_name": "target",
        "tags": ["projects", "milestones", "progress", "status"],
        "widgets": [
            {
                "type": "metric",
                "title": "Active Projects",
                "description": "Number of projects currently in progress",
                "chartType": None,
            },
            {
                "type": "chart",
                "chartType": "bar",
                "title": "Projects by Status",
                "description": "Project count by status (on track, at risk, delayed)",
            },
            {
                "type": "chart",
                "chartType": "line",
                "title": "Milestone Completion",
                "description": "Milestone completion trend over time",
            },
            {
                "type": "chart",
                "chartType": "pie",
                "title": "Project Distribution",
                "description": "Projects by engineering team or department",
            },
            {
                "type": "pivot",
                "title": "Project Details Table",
                "description": "Detailed view of all projects with key metrics",
                "chartType": None,
            },
        ],
    },
    {
        "id": "lead-time-analysis",
        "name": "Lead Time Analysis",
        "description": "Analyze lead times, cycle times, and delivery performance for engineering workflows",
        "category": "operations",
        "icon_name": "clock",
        "tags": ["lead time", "cycle time", "performance", "delivery"],
        "widgets": [
            {
                "type": "metric",
                "title": "Average Lead Time",
                "description": "Average time from start to completion (days)",
                "chartType": None,
            },
            {
                "type": "chart",
                "chartType": "line",
                "title": "Lead Time Trend",
                "description": "Lead time trends over the past quarter",
            },
            {
                "type": "chart",
                "chartType": "bar",
                "title": "Lead Time by Process",
                "description": "Comparison of lead times across different processes",
            },
            {
                "type": "chart",
                "chartType": "scatter",
                "title": "Lead Time vs Complexity",
                "description": "Correlation between project complexity and lead time",
            },
            {
                "type": "pivot",
                "title": "Lead Time Breakdown",
                "description": "Detailed breakdown of lead times by stage",
                "chartType": None,
            },
        ],
    },
    {
        "id": "resource-utilization",
        "name": "Resource Utilization",
        "description": "Track engineering resource allocation, capacity, and utilization rates",
        "category": "operations",
        "icon_name": "users",
        "tags": ["resources", "capacity", "utilization", "team"],
        "widgets": [
            {
                "type": "metric",
                "title": "Team Utilization",
                "description": "Overall team utilization percentage",
                "chartType": None,
            },
            {
                "type": "chart",
                "chartType": "bar",
                "title": "Utilization by Team",
                "description": "Resource utilization comparison across teams",
            },
            {
                "type": "chart",
                "chartType": "line",
                "title": "Capacity Trend",
                "description": "Team capacity and utilization over time",
            },
            {
                "type": "chart",
                "chartType": "pie",
                "title": "Time Allocation",
                "description": "How team time is allocated across activities",
            },
            {
                "type": "pivot",
                "title": "Resource Details",
                "description": "Detailed resource allocation by person and project",
                "chartType": None,
            },
        ],
    },
    {
        "id": "risk-management",
        "name": "Risk Management Dashboard",
        "description": "Monitor engineering risks, issues, and mitigation actions across projects",
        "category": "project",
        "icon_name": "alert-triangle",
        "tags": ["risk", "issues", "mitigation", "safety"],
        "widgets": [
            {
                "type": "metric",
                "title": "Open Risks",
                "description": "Total number of active risks",
                "chartType": None,
            },
            {
                "type": "chart",
                "chartType": "bar",
                "title": "Risks by Severity",
                "description": "Risk count by severity level (high, medium, low)",
            },
            {
                "type": "chart",
                "chartType": "pie",
                "title": "Risks by Category",
                "description": "Distribution of risks by type",
            },
            {
                "type": "chart",
                "chartType": "line",
                "title": "Risk Trend",
                "description": "Open risk count trend over the past 3 months",
            },
            {
                "type": "pivot",
                "title": "Risk Register",
                "description": "Comprehensive risk register with mitigation status",
                "chartType": None,
            },
        ],
    },
    {
        "id": "performance-kpis",
        "name": "Performance KPIs",
        "description": "Track key performance indicators and operational metrics for engineering",
        "category": "general",
        "icon_name": "activity",
        "tags": ["KPIs", "performance", "metrics", "operations"],
        "widgets": [
            {
                "type": "metric",
                "title": "Overall KPI Score",
                "description": "Composite performance score",
                "chartType": None,
            },
            {
                "type": "chart",
                "chartType": "gauge",
                "title": "Quality KPI",
                "description": "Quality performance indicator",
            },
            {
                "type": "chart",
                "chartType": "gauge",
                "title": "Delivery KPI",
                "description": "On-time delivery performance",
            },
            {
                "type": "chart",
                "chartType": "line",
                "title": "KPI Trends",
                "description": "All KPIs tracked over time",
            },
            {
                "type": "pivot",
                "title": "KPI Details",
                "description": "Detailed KPI breakdown by metric",
                "chartType": None,
            },
        ],
    },
    {
        "id": "sprint-velocity",
        "name": "Sprint Velocity Tracker",
        "description": "Monitor agile sprint velocity, burn-down, and team productivity metrics",
        "category": "project",
        "icon_name": "trending-up",
        "tags": ["agile", "sprint", "velocity", "productivity"],
        "widgets": [
            {
                "type": "metric",
                "title": "Current Sprint Velocity",
                "description": "Story points completed in current sprint",
                "chartType": None,
            },
            {
                "type": "chart",
                "chartType": "bar",
                "title": "Velocity by Sprint",
                "description": "Sprint velocity over the past 6 sprints",
            },
            {
                "type": "chart",
                "chartType": "line",
                "title": "Sprint Burn-down",
                "description": "Daily burn-down for current sprint",
            },
            {
                "type": "chart",
                "chartType": "pie",
                "title": "Story Point Distribution",
                "description": "Story points by team member",
            },
            {
                "type": "pivot",
                "title": "Sprint Summary",
                "description": "Detailed sprint metrics and completion rates",
                "chartType": None,
            },
        ],
    },
]


def get_template_by_id(template_id: str) -> DashboardTemplate | None:
    """Get a dashboard template by its ID.

    Args:
        template_id: The unique identifier for the template

    Returns:
        The template configuration if found, None otherwise
    """
    for template in TEMPLATES:
        if template["id"] == template_id:
            return template
    return None


def get_templates_by_category(
    category: Literal["engineering", "project", "quality", "operations", "general"],
) -> list[DashboardTemplate]:
    """Get all templates for a specific category.

    Args:
        category: The category to filter by

    Returns:
        List of templates in the specified category
    """
    return [t for t in TEMPLATES if t["category"] == category]


def get_all_categories() -> list[str]:
    """Get all unique template categories.

    Returns:
        List of category names
    """
    return list(set(t["category"] for t in TEMPLATES))
