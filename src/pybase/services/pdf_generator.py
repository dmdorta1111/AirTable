"""PDF generation service for custom reports with multi-section layout engine."""

import io
import json
from datetime import datetime
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, letter, landscape, portrait
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    Paragraph,
    Image,
)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import NotFoundError
from pybase.models.custom_report import (
    CustomReport,
    ReportSection,
    ReportSectionType,
)
from pybase.models.field import Field
from pybase.models.record import Record


class PDFGenerator:
    """Service for generating professional PDF reports with multi-section layouts."""

    def __init__(self) -> None:
        """Initialize PDF generator with default settings."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self) -> None:
        """Setup custom paragraph styles for reports."""
        # Custom title style
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#0066cc"),
                spaceAfter=30,
                alignment=TA_CENTER,
            )
        )

        # Custom subtitle style
        self.styles.add(
            ParagraphStyle(
                name="CustomSubtitle",
                parent=self.styles["Heading2"],
                fontSize=16,
                textColor=colors.HexColor("#333333"),
                spaceAfter=20,
                alignment=TA_CENTER,
            )
        )

        # Custom heading style
        self.styles.add(
            ParagraphStyle(
                name="CustomHeading",
                parent=self.styles["Heading3"],
                fontSize=14,
                textColor=colors.HexColor("#0066cc"),
                spaceAfter=12,
                spaceBefore=20,
            )
        )

        # Custom normal style
        self.styles.add(
            ParagraphStyle(
                name="CustomNormal",
                parent=self.styles["Normal"],
                fontSize=10,
                textColor=colors.black,
                spaceAfter=12,
            )
        )

        # Custom table header style
        self.styles.add(
            ParagraphStyle(
                name="TableHeader",
                parent=self.styles["Normal"],
                fontSize=10,
                textColor=colors.white,
                alignment=TA_CENTER,
            )
        )

    async def generate_report_pdf(
        self,
        report: CustomReport,
        db: AsyncSession,
        output_path: Optional[str] = None,
    ) -> bytes:
        """Generate PDF for a custom report with all sections.

        Args:
            report: CustomReport instance to generate PDF for
            db: Database session for fetching data
            output_path: Optional file path to save PDF (if None, returns bytes)

        Returns:
            PDF bytes if output_path is None, otherwise saves to file

        Raises:
            NotFoundError: If required data not found
            ValueError: If report configuration is invalid

        """
        # Parse report configuration
        layout_config = report.get_layout_config_dict()
        style_config = report.get_style_config_dict()

        # Setup PDF document
        page_size = self._get_page_size(
            layout_config.get("page_size", "A4"),
            layout_config.get("orientation", "portrait"),
        )
        margins = layout_config.get(
            "margins",
            {"top": 20, "bottom": 20, "left": 15, "right": 15},
        )

        # Create PDF buffer or file
        if output_path:
            output_buffer = output_path
        else:
            output_buffer = io.BytesIO()

        # Create document template
        doc = SimpleDocTemplate(
            output_buffer,
            pagesize=page_size,
            topMargin=margins.get("top", 20),
            bottomMargin=margins.get("bottom", 20),
            leftMargin=margins.get("left", 15),
            rightMargin=margins.get("right", 15),
        )

        # Build PDF content
        story = []
        story = await self._build_report_content(
            report, db, story, layout_config, style_config
        )

        # Generate PDF
        doc.build(story)

        # Return bytes if no output path
        if not output_path:
            return output_buffer.getvalue()
        return b""

    async def _build_report_content(
        self,
        report: CustomReport,
        db: AsyncSession,
        story: list,
        layout_config: dict[str, Any],
        style_config: dict[str, Any],
    ) -> list:
        """Build PDF content from report sections.

        Args:
            report: CustomReport instance
            db: Database session
            story: Current story list
            layout_config: Layout configuration
            style_config: Style configuration

        Returns:
            Updated story list with all content

        """
        # Add report header
        story.extend(
            await self._create_report_header(report, layout_config, style_config)
        )

        # Add description if present
        if report.description:
            story.append(Spacer(1, 0.1 * inch))
            desc = Paragraph(report.description, self.styles["CustomNormal"])
            story.append(desc)
            story.append(Spacer(1, 0.2 * inch))

        # Process sections in order
        sections = sorted(
            [s for s in report.sections if s.is_visible],
            key=lambda s: s.order,
        )

        for section in sections:
            section_story = await self._render_section(
                section, db, layout_config, style_config
            )
            story.extend(section_story)

        return story

    async def _create_report_header(
        self,
        report: CustomReport,
        layout_config: dict[str, Any],
        style_config: dict[str, Any],
    ) -> list:
        """Create report header with title and metadata.

        Args:
            report: CustomReport instance
            layout_config: Layout configuration
            style_config: Style configuration

        Returns:
            List of flowables for header

        """
        header_elements = []

        # Add logo if configured
        logo_url = style_config.get("logo_url")
        if logo_url:
            try:
                logo = Image(logo_url, width=1.5 * inch, height=0.75 * inch)
                logo.hAlign = TA_CENTER if style_config.get("header_style") == "centered" else TA_LEFT
                header_elements.append(logo)
                header_elements.append(Spacer(1, 0.2 * inch))
            except Exception:
                # Logo loading failed, continue without it
                pass

        # Add title
        title_alignment = TA_CENTER
        if style_config.get("header_style") == "left":
            title_alignment = TA_LEFT
        elif style_config.get("header_style") == "right":
            title_alignment = TA_RIGHT

        title_style = ParagraphStyle(
            name="ReportTitle",
            parent=self.styles["CustomTitle"],
            alignment=title_alignment,
        )
        title = Paragraph(report.name, title_style)
        header_elements.append(title)
        header_elements.append(Spacer(1, 0.2 * inch))

        # Add generation timestamp
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        timestamp_style = ParagraphStyle(
            name="Timestamp",
            parent=self.styles["CustomNormal"],
            fontSize=8,
            alignment=title_alignment,
            textColor=colors.gray,
        )
        timestamp_para = Paragraph(f"Generated: {timestamp}", timestamp_style)
        header_elements.append(timestamp_para)
        header_elements.append(Spacer(1, 0.3 * inch))

        return header_elements

    async def _render_section(
        self,
        section: ReportSection,
        db: AsyncSession,
        layout_config: dict[str, Any],
        style_config: dict[str, Any],
    ) -> list:
        """Render a single report section based on its type.

        Args:
            section: ReportSection instance
            db: Database session
            layout_config: Layout configuration
            style_config: Style configuration

        Returns:
            List of flowables for this section

        """
        section_type = section.section_type_enum
        section_config = section.get_section_config_dict()

        if section_type == ReportSectionType.TABLE:
            return await self.render_table_section(section, db, layout_config, style_config)
        elif section_type == ReportSectionType.CHART:
            return await self.render_chart_section(section, layout_config, style_config)
        elif section_type == ReportSectionType.TEXT:
            return await self.render_text_section(section, layout_config, style_config)
        elif section_type == ReportSectionType.IMAGE:
            return await self.render_image_section(section, layout_config, style_config)
        elif section_type == ReportSectionType.PAGE_BREAK:
            return [PageBreak()]
        elif section_type == ReportSectionType.HEADER:
            return await self._render_header_section(section, layout_config, style_config)
        elif section_type == ReportSectionType.FOOTER:
            # Footers are handled by document template, skip in content
            return []
        else:
            return []

    async def render_table_section(
        self,
        section: ReportSection,
        db: AsyncSession,
        layout_config: dict[str, Any],
        style_config: dict[str, Any],
    ) -> list:
        """Render a table section with data from data source.

        Args:
            section: ReportSection instance with type TABLE
            db: Database session
            layout_config: Layout configuration
            style_config: Style configuration

        Returns:
            List of flowables for table section

        """
        from pybase.models.custom_report import ReportDataSource

        section_elements = []
        section_config = section.get_section_config_dict()

        # Add section title if present
        if section.title:
            title = Paragraph(section.title, self.styles["CustomHeading"])
            section_elements.append(title)
            section_elements.append(Spacer(1, 0.1 * inch))

        # Fetch data from data source
        data_source_id = section_config.get("data_source_id")
        if not data_source_id:
            no_data = Paragraph("No data source configured", self.styles["CustomNormal"])
            section_elements.append(no_data)
            return section_elements

        # Fetch data source configuration
        data_source = await db.get(ReportDataSource, str(data_source_id))
        if not data_source:
            no_data = Paragraph("Data source not found", self.styles["CustomNormal"])
            section_elements.append(no_data)
            return section_elements

        # Fetch table data
        table_data = await self._fetch_table_data(data_source, db, section_config)

        if not table_data or len(table_data) < 1:
            # No data available
            no_data = Paragraph("No data available", self.styles["CustomNormal"])
            section_elements.append(no_data)
            return section_elements

        # Create table
        table = Table(table_data)
        table_style = self._create_table_style(section_config, len(table_data))
        table.setStyle(table_style)

        section_elements.append(table)
        section_elements.append(Spacer(1, 0.2 * inch))

        return section_elements

    async def render_chart_section(
        self,
        section: ReportSection,
        layout_config: dict[str, Any],
        style_config: dict[str, Any],
    ) -> list:
        """Render a chart section with image embedding.

        Supports multiple image sources:
        - HTTP/HTTPS URLs
        - Base64 encoded images (data:image/...)
        - Local file paths
        - Chart data for generation (future enhancement)

        Args:
            section: ReportSection instance with type CHART
            layout_config: Layout configuration
            style_config: Style configuration

        Returns:
            List of flowables for chart section

        """
        section_elements = []
        section_config = section.get_section_config_dict()

        # Add section title if present
        if section.title:
            title = Paragraph(section.title, self.styles["CustomHeading"])
            section_elements.append(title)
            section_elements.append(Spacer(1, 0.1 * inch))

        # Get chart image source
        image_source = section_config.get("image_url") or section_config.get("url") or section_config.get("image")

        if not image_source:
            # Check if chart data is provided for generation
            chart_data = section_config.get("chart_data")
            if chart_data:
                # Future: Generate chart from data using matplotlib/plotly
                placeholder = Paragraph(
                    "[Chart generation from data - not yet implemented]",
                    self.styles["CustomNormal"]
                )
            else:
                # No chart source provided
                placeholder = Paragraph(
                    "[No chart configured]", self.styles["CustomNormal"]
                )
            section_elements.append(placeholder)
            section_elements.append(Spacer(1, 0.2 * inch))
            return section_elements

        try:
            # Determine image source type and load accordingly
            chart_image = await self._load_chart_image(image_source, section_config)

            # Apply configured dimensions
            width = section_config.get("width", 6 * inch)
            height = section_config.get("height", 4 * inch)
            chart_image.drawWidth = width
            chart_image.drawHeight = height
            chart_image.hAlign = TA_CENTER

            section_elements.append(chart_image)

        except FileNotFoundError:
            # Image file not found
            error_msg = Paragraph(
                f"Chart image not found: {image_source}", self.styles["CustomNormal"]
            )
            section_elements.append(error_msg)
        except ImportError:
            # Unsupported format or missing library
            error_msg = Paragraph(
                "Chart image format not supported", self.styles["CustomNormal"]
            )
            section_elements.append(error_msg)
        except Exception as e:
            # Generic error
            error_msg = Paragraph(
                f"Could not load chart image: {str(e)}", self.styles["CustomNormal"]
            )
            section_elements.append(error_msg)

        section_elements.append(Spacer(1, 0.2 * inch))
        return section_elements

    async def _load_chart_image(
        self,
        image_source: str,
        section_config: dict[str, Any],
    ) -> Image:
        """Load chart image from various sources.

        Args:
            image_source: Image URL, base64 data, or file path
            section_config: Section configuration for additional settings

        Returns:
            ReportLab Image object

        Raises:
            FileNotFoundError: If local file not found
            ImportError: If image format not supported
            Exception: For other loading errors

        """
        import base64
        import os
        import urllib.request
        from typing import Union

        # Check for base64 encoded image
        if image_source.startswith("data:image/"):
            return self._load_base64_image(image_source)

        # Check for local file path
        if not image_source.startswith(("http://", "https://", "ftp://")):
            if os.path.exists(image_source):
                return Image(image_source)
            else:
                raise FileNotFoundError(f"Image file not found: {image_source}")

        # Remote URL - download and create temporary image
        try:
            # Download image to temporary buffer
            with urllib.request.urlopen(image_source) as response:
                image_data = response.read()

            # Create image from bytes
            img_buffer = io.BytesIO(image_data)
            return Image(img_buffer)

        except Exception as e:
            raise Exception(f"Failed to load image from URL: {str(e)}")

    def _load_base64_image(self, data_uri: str) -> Image:
        """Load image from base64 data URI.

        Args:
            data_uri: Base64 data URI (e.g., "data:image/png;base64,...")

        Returns:
            ReportLab Image object

        Raises:
            ImportError: If format not supported
            Exception: If decoding fails

        """
        import base64

        try:
            # Parse data URI
            # Format: data:image/<type>;base64,<data>
            if not data_uri.startswith("data:image/"):
                raise ImportError("Invalid base64 image format")

            # Extract the base64 data
            _, base64_data = data_uri.split(";", 1)
            if not base64_data.startswith("base64,"):
                raise ImportError("Invalid base64 encoding")

            encoded_data = base64_data.split("base64,", 1)[1]

            # Decode base64
            image_data = base64.b64decode(encoded_data)

            # Create image from bytes
            img_buffer = io.BytesIO(image_data)
            return Image(img_buffer)

        except Exception as e:
            raise Exception(f"Failed to decode base64 image: {str(e)}")

    async def render_text_section(
        self,
        section: ReportSection,
        layout_config: dict[str, Any],
        style_config: dict[str, Any],
    ) -> list:
        """Render a text section with rich content.

        Args:
            section: ReportSection instance with type TEXT
            layout_config: Layout configuration
            style_config: Style configuration

        Returns:
            List of flowables for text section

        """
        section_elements = []
        section_config = section.get_section_config_dict()

        # Add section title if present
        if section.title:
            title = Paragraph(section.title, self.styles["CustomHeading"])
            section_elements.append(title)
            section_elements.append(Spacer(1, 0.1 * inch))

        # Get text content
        content = section_config.get("content", "")
        content_format = section_config.get("format", "html")

        if content:
            # For now, treat as plain text (HTML parsing would require additional libraries)
            # In a full implementation, you would use a proper HTML to PDF converter
            text_para = Paragraph(content, self.styles["CustomNormal"])
            section_elements.append(text_para)
        else:
            placeholder = Paragraph("[No content]", self.styles["CustomNormal"])
            section_elements.append(placeholder)

        section_elements.append(Spacer(1, 0.2 * inch))
        return section_elements

    async def render_image_section(
        self,
        section: ReportSection,
        layout_config: dict[str, Any],
        style_config: dict[str, Any],
    ) -> list:
        """Render an image section with embedded image.

        Args:
            section: ReportSection instance with type IMAGE
            layout_config: Layout configuration
            style_config: Style configuration

        Returns:
            List of flowables for image section

        """
        section_elements = []
        section_config = section.get_section_config_dict()

        # Add section title if present
        if section.title:
            title = Paragraph(section.title, self.styles["CustomHeading"])
            section_elements.append(title)
            section_elements.append(Spacer(1, 0.1 * inch))

        # Get image URL
        image_url = section_config.get("url")
        if image_url:
            try:
                width = section_config.get("width", 6 * inch)
                height = section_config.get("height", 4 * inch)
                img = Image(image_url, width=width, height=height)

                # Set alignment
                alignment = section_config.get("alignment", "center")
                if alignment == "left":
                    img.hAlign = TA_LEFT
                elif alignment == "right":
                    img.hAlign = TA_RIGHT
                else:
                    img.hAlign = TA_CENTER

                section_elements.append(img)
            except Exception:
                # Image loading failed
                error_msg = Paragraph(
                    "Image could not be loaded", self.styles["CustomNormal"]
                )
                section_elements.append(error_msg)
        else:
            placeholder = Paragraph("[Image URL not provided]", self.styles["CustomNormal"])
            section_elements.append(placeholder)

        section_elements.append(Spacer(1, 0.2 * inch))
        return section_elements

    async def _render_header_section(
        self,
        section: ReportSection,
        layout_config: dict[str, Any],
        style_config: dict[str, Any],
    ) -> list:
        """Render a header section for page headers.

        Args:
            section: ReportSection instance with type HEADER
            layout_config: Layout configuration
            style_config: Style configuration

        Returns:
            List of flowables for header section

        """
        # Headers are typically handled by document template
        # This is a placeholder for inline headers
        section_elements = []
        section_config = section.get_section_config_dict()

        content = section_config.get("content", section.title or "")
        if content:
            header_style = ParagraphStyle(
                name="InlineHeader",
                parent=self.styles["CustomHeading"],
                alignment=TA_CENTER,
            )
            header = Paragraph(content, header_style)
            section_elements.append(header)
            section_elements.append(Spacer(1, 0.2 * inch))

        return section_elements

    async def _fetch_table_data(
        self,
        data_source: "ReportDataSource",
        db: AsyncSession,
        section_config: dict[str, Any],
    ) -> list[list[str]]:
        """Fetch table data from data source.

        Args:
            data_source: ReportDataSource instance
            db: Database session
            section_config: Section configuration

        Returns:
            2D list of table data (headers + rows)

        """
        # Get configurations
        tables_config = data_source.get_tables_config_dict()
        fields_config = data_source.get_fields_config_dict()
        sort_config = data_source.get_sort_config_dict()

        # Get primary table
        primary_table_id = tables_config.get("primary_table")
        if not primary_table_id:
            return []

        # Get fields to display
        fields_list = fields_config.get("fields", [])
        if not fields_list:
            # If no fields specified, fetch all fields for the table
            from pybase.models.table import Table

            table = await db.get(Table, str(primary_table_id))
            if not table:
                return []

            # Get all fields for this table
            query = select(Field).where(
                Field.table_id == str(primary_table_id),
                Field.deleted_at.is_(None),
            )
            query = query.order_by(Field.created_at)
            result = await db.execute(query)
            all_fields = result.scalars().all()

            # Create field configs from all fields
            fields_list = [
                {
                    "table_id": str(primary_table_id),
                    "field_id": str(field.id),
                    "alias": field.name,
                    "aggregate": "none",
                    "visible": True,
                }
                for field in all_fields
            ]

        # Build header row
        headers = [field.get("alias", "Field") for field in fields_list if field.get("visible", True)]
        if not headers:
            return []

        # Fetch records
        from pybase.models.record import Record

        query = select(Record).where(
            Record.table_id == str(primary_table_id),
            Record.deleted_at.is_(None),
        )

        # Apply sorting
        sort_by = sort_config.get("sort_by", [])
        if sort_by:
            # For simplicity, just use first sort field
            # Full implementation would handle multiple sorts
            pass

        query = query.order_by(Record.created_at)

        # Apply limit
        limit = sort_config.get("limit", 1000)
        query = query.limit(limit)

        result = await db.execute(query)
        records = result.scalars().all()

        # Build data rows
        data_rows = []
        for record in records:
            # Parse record data
            try:
                record_data = json.loads(record.data) if isinstance(record.data, str) else record.data
            except (json.JSONDecodeError, TypeError):
                record_data = {}

            # Extract field values
            row = []
            for field_config in fields_list:
                if not field_config.get("visible", True):
                    continue

                field_id = field_config.get("field_id")
                value = record_data.get(str(field_id), "")

                # Format value for display
                formatted_value = self._format_cell_value(value, field_config)
                row.append(formatted_value)

            data_rows.append(row)

        # Combine headers and data
        table_data = [headers] + data_rows

        return table_data

    def _format_cell_value(self, value: Any, field_config: dict[str, Any]) -> str:
        """Format a cell value for display in PDF table.

        Args:
            value: Raw field value
            field_config: Field configuration

        Returns:
            Formatted string value

        """
        if value is None:
            return ""

        # Handle different value types
        if isinstance(value, bool):
            return "Yes" if value else "No"
        elif isinstance(value, (int, float)):
            # Format numbers
            aggregate = field_config.get("aggregate", "none")
            if aggregate == "sum":
                return str(value)
            elif aggregate == "avg":
                return f"{value:.2f}"
            else:
                return str(value)
        elif isinstance(value, list):
            # Handle multi-select or linked records
            return ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            # Handle complex objects
            return json.dumps(value)
        else:
            return str(value)

    def _create_table_style(
        self,
        section_config: dict[str, Any],
        row_count: int,
    ) -> TableStyle:
        """Create table style based on configuration.

        Args:
            section_config: Section configuration
            row_count: Number of rows in table

        Returns:
            ReportLab TableStyle instance

        """
        # Base style
        table_style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0066cc")),  # Header background
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),  # Header text
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),  # Data background
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ])

        # Add alternating row colors if configured
        if section_config.get("stripe_rows", True):
            for i in range(2, row_count, 2):
                table_style.add("BACKGROUND", (0, i - 1), (-1, i - 1), colors.white)

        # Apply custom colors if configured
        custom_colors = section_config.get("colors", {})
        if custom_colors.get("header_background"):
            table_style.add(
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor(custom_colors["header_background"]),
            )
        if custom_colors.get("row_background"):
            table_style.add(
                "BACKGROUND",
                (0, 1),
                (-1, -1),
                colors.HexColor(custom_colors["row_background"]),
            )

        return table_style

    def _get_page_size(self, size_name: str, orientation: str):
        """Get ReportLab pagesize based on configuration.

        Args:
            size_name: Page size name (A4, Letter, etc.)
            orientation: Page orientation (portrait, landscape)

        Returns:
            ReportLab pagesize tuple

        """
        # Base page sizes
        sizes = {
            "A4": A4,
            "Letter": letter,
            "Legal": (8.5 * inch, 14 * inch),
            "Tabloid": (11 * inch, 17 * inch),
        }

        base_size = sizes.get(size_name, A4)

        # Apply orientation
        if orientation and orientation.lower() == "landscape":
            return landscape(base_size)
        return portrait(base_size)

    def _apply_style_config(self, style_config: dict[str, Any]) -> dict[str, Any]:
        """Apply style configuration to PDF styles.

        Args:
            style_config: Style configuration from report

        Returns:
            Updated style configuration

        """
        # Update font family if specified
        font_family = style_config.get("font_family", "Arial")
        # In a full implementation, you would register custom fonts here

        # Update font size
        font_size = style_config.get("font_size", 10)

        # Update colors
        colors_config = style_config.get("colors", {})
        primary_color = colors_config.get("primary", "#0066cc")

        # Update custom styles
        self.styles["CustomTitle"].textColor = colors.HexColor(primary_color)
        self.styles["CustomHeading"].textColor = colors.HexColor(primary_color)
        self.styles["CustomNormal"].fontSize = font_size

        return style_config

    def _apply_style_config(self, style_config: dict[str, Any]) -> dict[str, Any]:
        """Apply style configuration to PDF styles.

        Args:
            style_config: Style configuration from report

        Returns:
            Updated style configuration

        """
        # Update font family if specified
        font_family = style_config.get("font_family", "Arial")
        # In a full implementation, you would register custom fonts here

        # Update font size
        font_size = style_config.get("font_size", 10)

        # Update colors
        colors_config = style_config.get("colors", {})
        primary_color = colors_config.get("primary", "#0066cc")

        # Update custom styles
        self.styles["CustomTitle"].textColor = colors.HexColor(primary_color)
        self.styles["CustomHeading"].textColor = colors.HexColor(primary_color)
        self.styles["CustomNormal"].fontSize = font_size

        return style_config
