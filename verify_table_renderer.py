#!/usr/bin/env python
"""Verify table renderer method exists."""

from src.pybase.services.pdf_generator import PDFGenerator

pdf_gen = PDFGenerator()
print('Table renderer method exists:', hasattr(pdf_gen, 'render_table_section'))
