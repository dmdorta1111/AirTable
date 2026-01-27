#!/usr/bin/env python
"""Verification script for chart renderer implementation."""

from src.pybase.services.pdf_generator import PDFGenerator

def main():
    gen = PDFGenerator()

    # Check if render_chart_section exists
    has_render = hasattr(gen, 'render_chart_section')
    print(f'Chart renderer method exists: {has_render}')

    # Check if _load_chart_image helper exists
    has_loader = hasattr(gen, '_load_chart_image')
    print(f'Image loader method exists: {has_loader}')

    # Check if _load_base64_image helper exists
    has_base64 = hasattr(gen, '_load_base64_image')
    print(f'Base64 loader method exists: {has_base64}')

    # Overall success
    success = has_render and has_loader and has_base64
    print(f'\nOverall: {"✓ PASS" if success else "✗ FAIL"}')

    return 0 if success else 1

if __name__ == '__main__':
    exit(main())
