"""Field type handlers for PyBase.

This module provides field type handlers for all 30+ field types supported by PyBase.
Each handler implements serialization, deserialization, and validation logic.
"""

from pybase.fields.base import BaseFieldTypeHandler

# Import basic field type handlers
from pybase.fields.types.checkbox import CheckboxFieldHandler
from pybase.fields.types.date import DateFieldHandler
from pybase.fields.types.number import NumberFieldHandler
from pybase.fields.types.text import TextFieldHandler

# Import standard field type handlers (Phase 1)
from pybase.fields.types.currency import CurrencyFieldHandler
from pybase.fields.types.percent import PercentFieldHandler
from pybase.fields.types.datetime_field import DateTimeFieldHandler
from pybase.fields.types.time_field import TimeFieldHandler
from pybase.fields.types.duration import DurationFieldHandler
from pybase.fields.types.single_select import SingleSelectFieldHandler
from pybase.fields.types.multi_select import MultiSelectFieldHandler
from pybase.fields.types.status import StatusFieldHandler

# Import advanced field type handlers (Phase 2)
from pybase.fields.types.email import EmailFieldHandler
from pybase.fields.types.phone import PhoneFieldHandler
from pybase.fields.types.url import URLFieldHandler
from pybase.fields.types.rating import RatingFieldHandler
from pybase.fields.types.autonumber import AutonumberFieldHandler
from pybase.fields.types.attachment import AttachmentFieldHandler
from pybase.fields.types.system_fields import (
    CreatedTimeFieldHandler,
    ModifiedTimeFieldHandler,
    CreatedByFieldHandler,
    ModifiedByFieldHandler,
)

# Import relational field type handlers (Phase 3)
from pybase.fields.types.link import LinkFieldHandler
from pybase.fields.types.lookup import LookupFieldHandler
from pybase.fields.types.rollup import RollupFieldHandler

# Import formula field handler (Phase 4)
from pybase.fields.types.formula import FormulaFieldHandler

# Import engineering field type handlers (Phase 5)
from pybase.fields.types.engineering import (
    DimensionFieldHandler,
    GDTFieldHandler,
    ThreadFieldHandler,
    SurfaceFinishFieldHandler,
    MaterialFieldHandler,
)

# Registry of field type handlers
FIELD_HANDLERS: dict[str, type[BaseFieldTypeHandler]] = {
    # Basic types (existing)
    TextFieldHandler.field_type: TextFieldHandler,
    NumberFieldHandler.field_type: NumberFieldHandler,
    CheckboxFieldHandler.field_type: CheckboxFieldHandler,
    DateFieldHandler.field_type: DateFieldHandler,
    # Standard types (Phase 1)
    CurrencyFieldHandler.field_type: CurrencyFieldHandler,
    PercentFieldHandler.field_type: PercentFieldHandler,
    DateTimeFieldHandler.field_type: DateTimeFieldHandler,
    TimeFieldHandler.field_type: TimeFieldHandler,
    DurationFieldHandler.field_type: DurationFieldHandler,
    SingleSelectFieldHandler.field_type: SingleSelectFieldHandler,
    MultiSelectFieldHandler.field_type: MultiSelectFieldHandler,
    StatusFieldHandler.field_type: StatusFieldHandler,
    # Advanced types (Phase 2)
    EmailFieldHandler.field_type: EmailFieldHandler,
    PhoneFieldHandler.field_type: PhoneFieldHandler,
    URLFieldHandler.field_type: URLFieldHandler,
    RatingFieldHandler.field_type: RatingFieldHandler,
    AutonumberFieldHandler.field_type: AutonumberFieldHandler,
    AttachmentFieldHandler.field_type: AttachmentFieldHandler,
    CreatedTimeFieldHandler.field_type: CreatedTimeFieldHandler,
    ModifiedTimeFieldHandler.field_type: ModifiedTimeFieldHandler,
    CreatedByFieldHandler.field_type: CreatedByFieldHandler,
    ModifiedByFieldHandler.field_type: ModifiedByFieldHandler,
    # Relational types (Phase 3)
    LinkFieldHandler.field_type: LinkFieldHandler,
    LookupFieldHandler.field_type: LookupFieldHandler,
    RollupFieldHandler.field_type: RollupFieldHandler,
    # Formula type (Phase 4)
    FormulaFieldHandler.field_type: FormulaFieldHandler,
    # Engineering types (Phase 5)
    DimensionFieldHandler.field_type: DimensionFieldHandler,
    GDTFieldHandler.field_type: GDTFieldHandler,
    ThreadFieldHandler.field_type: ThreadFieldHandler,
    SurfaceFinishFieldHandler.field_type: SurfaceFinishFieldHandler,
    MaterialFieldHandler.field_type: MaterialFieldHandler,
}


def get_field_handler(field_type: str) -> type[BaseFieldTypeHandler] | None:
    """
    Get field handler for given field type.

    Args:
        field_type: Field type identifier

    Returns:
        Field handler class or None if not found
    """
    return FIELD_HANDLERS.get(field_type)


def register_field_handler(handler: type[BaseFieldTypeHandler]) -> None:
    """
    Register a new field handler.

    Args:
        handler: Field handler class to register
    """
    FIELD_HANDLERS[handler.field_type] = handler


def list_field_types() -> list[str]:
    """
    List all registered field types.

    Returns:
        List of field type identifiers
    """
    return list(FIELD_HANDLERS.keys())


# Export all handlers
__all__ = [
    "BaseFieldTypeHandler",
    "FIELD_HANDLERS",
    "get_field_handler",
    "register_field_handler",
    "list_field_types",
    # Basic handlers
    "TextFieldHandler",
    "NumberFieldHandler",
    "CheckboxFieldHandler",
    "DateFieldHandler",
    # Standard handlers (Phase 1)
    "CurrencyFieldHandler",
    "PercentFieldHandler",
    "DateTimeFieldHandler",
    "TimeFieldHandler",
    "DurationFieldHandler",
    "SingleSelectFieldHandler",
    "MultiSelectFieldHandler",
    "StatusFieldHandler",
    # Advanced handlers (Phase 2)
    "EmailFieldHandler",
    "PhoneFieldHandler",
    "URLFieldHandler",
    "RatingFieldHandler",
    "AutonumberFieldHandler",
    "AttachmentFieldHandler",
    "CreatedTimeFieldHandler",
    "ModifiedTimeFieldHandler",
    "CreatedByFieldHandler",
    "ModifiedByFieldHandler",
    # Relational handlers (Phase 3)
    "LinkFieldHandler",
    "LookupFieldHandler",
    "RollupFieldHandler",
    # Formula handler (Phase 4)
    "FormulaFieldHandler",
    # Engineering handlers (Phase 5)
    "DimensionFieldHandler",
    "GDTFieldHandler",
    "ThreadFieldHandler",
    "SurfaceFinishFieldHandler",
    "MaterialFieldHandler",
]
