"""SQLAlchemy models for PyBase."""

from pybase.models.user import User, APIKey
from pybase.models.workspace import Workspace, WorkspaceMember
from pybase.models.base import Base as BaseModel
from pybase.models.table import Table
from pybase.models.field import Field
from pybase.models.record import Record
from pybase.models.comment import Comment
from pybase.models.view import View, ViewType
from pybase.models.operation_log import OperationLog
from pybase.models.automation import (
    Automation,
    AutomationAction,
    AutomationRun,
    Webhook,
    TriggerType,
    ActionType,
    AutomationRunStatus,
)
from pybase.models.werk24_usage import Werk24Usage
from pybase.models.unique_constraint import UniqueConstraint
from pybase.models.cad_model import (
    CADModel,
    CADModelEmbedding,
    CADAssemblyRelation,
    CADManufacturingFeature,
    CADRenderedView,
)
from pybase.models.extraction_job import (
    ExtractionJob,
    ExtractionJobStatus,
    ExtractionFormat,
)
from pybase.models.document_intelligence import (
    DocumentGroup,
    DocumentGroupMember,
    ExtractedMetadata,
    ExtractedDimension,
    ExtractedParameter,
    ExtractedMaterial,
    ExtractedBOMItem,
    LinkingMethod,
    DocumentRole,
    ExtractionSourceType,
    ExtractionStatus,
    DimensionType,
    ToleranceType,
)
from pybase.models.custom_report import (
    CustomReport,
    ReportSection,
    ReportDataSource,
    ReportTemplate,
    CustomReportSchedule,
    ReportFormat,
    ReportSectionType,
    ScheduleFrequency as CustomReportScheduleFrequency,
    ReportStatus as CustomReportStatus,
)

__all__ = [
    "User",
    "APIKey",
    "Workspace",
    "WorkspaceMember",
    "BaseModel",
    "Table",
    "Field",
    "Record",
    "Comment",
    "View",
    "ViewType",
    "OperationLog",
    "Automation",
    "AutomationAction",
    "AutomationRun",
    "Webhook",
    "TriggerType",
    "ActionType",
    "AutomationRunStatus",
    "Werk24Usage",
    "UniqueConstraint",
    "CADModel",
    "CADModelEmbedding",
    "CADAssemblyRelation",
    "CADManufacturingFeature",
    "CADRenderedView",
    "ExtractionJob",
    "ExtractionJobStatus",
    "ExtractionFormat",
    "DocumentGroup",
    "DocumentGroupMember",
    "ExtractedMetadata",
    "ExtractedDimension",
    "ExtractedParameter",
    "ExtractedMaterial",
    "ExtractedBOMItem",
    "LinkingMethod",
    "DocumentRole",
    "ExtractionSourceType",
    "ExtractionStatus",
    "DimensionType",
    "ToleranceType",
    "CustomReport",
    "ReportSection",
    "ReportDataSource",
    "ReportTemplate",
    "CustomReportSchedule",
    "ReportFormat",
    "ReportSectionType",
    "CustomReportScheduleFrequency",
    "CustomReportStatus",
]
