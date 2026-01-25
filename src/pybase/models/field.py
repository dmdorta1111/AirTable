"""
Field model - defines column schema in a table.

Fields define the type and configuration of data in each column.
"""

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import BaseModel, SoftDeleteModel

if TYPE_CHECKING:
    from pybase.models.table import Table
    from pybase.models.unique_constraint import UniqueConstraint


class FieldType(str, Enum):
    """Available field types."""

    # Basic Types
    TEXT = "text"
    LONG_TEXT = "long_text"
    NUMBER = "number"
    CHECKBOX = "checkbox"

    # Selection Types
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"

    # Date/Time Types
    DATE = "date"
    DATETIME = "datetime"
    DURATION = "duration"

    # Reference Types
    LINKED_RECORD = "linked_record"
    LOOKUP = "lookup"
    ROLLUP = "rollup"

    # Computed Types
    FORMULA = "formula"
    AUTONUMBER = "autonumber"

    # Media Types
    ATTACHMENT = "attachment"
    URL = "url"
    EMAIL = "email"
    PHONE = "phone"

    # User Types
    USER = "user"
    CREATED_BY = "created_by"
    LAST_MODIFIED_BY = "last_modified_by"

    # Timestamp Types
    CREATED_TIME = "created_time"
    LAST_MODIFIED_TIME = "last_modified_time"

    # Special Types
    BARCODE = "barcode"
    RATING = "rating"
    CURRENCY = "currency"
    PERCENT = "percent"

    # Engineering Types (Phase 2/3)
    DIMENSION = "dimension"
    GDT = "gdt"  # Geometric Dimensioning & Tolerancing
    THREAD = "thread"
    SURFACE_FINISH = "surface_finish"
    MATERIAL = "material"
    DRAWING_REF = "drawing_ref"
    BOM_ITEM = "bom_item"
    REVISION = "revision"


class Field(SoftDeleteModel):
    """
    Field model - defines a column in a table.

    Contains the field type, configuration options, and display settings.
    """

    __tablename__: str = "fields"  # type: ignore[assignment]

    # Foreign key to table
    table_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Basic info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Field type
    field_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Type-specific options (JSON stored as text)
    # Contains configuration like:
    # - number: precision, format
    # - single_select: choices
    # - linked_record: linked_table_id
    # - formula: expression
    # - dimension: unit, tolerance
    options: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Ordering
    position: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Display settings
    width: Mapped[int] = mapped_column(
        Integer,
        default=200,
        nullable=False,
    )
    is_visible: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Validation
    is_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_unique: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # System fields
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_computed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    table: Mapped["Table"] = relationship(
        "Table",
        back_populates="fields",
    )
    unique_constraints: Mapped[list["UniqueConstraint"]] = relationship(
        "UniqueConstraint",
        back_populates="field",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_fields_table_name", "table_id", "name"),
        Index("ix_fields_table_position", "table_id", "position"),
        Index("ix_fields_table_type", "table_id", "field_type"),
    )

    def __repr__(self) -> str:
        return f"<Field {self.name} ({self.field_type})>"

    @property
    def is_system_field(self) -> bool:
        """Check if field is a system-managed field."""
        return self.field_type in (
            FieldType.AUTONUMBER.value,
            FieldType.CREATED_BY.value,
            FieldType.LAST_MODIFIED_BY.value,
            FieldType.CREATED_TIME.value,
            FieldType.LAST_MODIFIED_TIME.value,
        )

    @property
    def is_editable(self) -> bool:
        """Check if field value can be directly edited."""
        return not (self.is_computed or self.is_system_field or self.is_locked)
