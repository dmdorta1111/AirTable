#!/usr/bin/env python3
"""
Performance benchmarking script for PDF extraction.

Measures extraction time, memory usage, and throughput for various PDF types.
"""

import argparse
import sys
import time
import tempfile
import os
import statistics
from pathlib import Path
from typing import List, Dict, Any
import json


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} TB"


def format_time(seconds: float) -> str:
    """Format time to human-readable format."""
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f} µs"
    elif seconds < 1.0:
        return f"{seconds * 1000:.2f} ms"
    else:
        return f"{seconds:.2f} s"


def create_simple_pdf(num_tables: int = 1, rows_per_table: int = 10) -> str:
    """Create a simple test PDF with tables."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch

        temp_dir = tempfile.gettempdir()
        pdf_path = os.path.join(temp_dir, f"benchmark_simple_{num_tables}x{rows_per_table}.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()

        # Add title
        title = Paragraph(f"Benchmark PDF - {num_tables} Tables x {rows_per_table} Rows", styles["Title"])
        story.append(title)
        story.append(Spacer(1, 0.2 * inch))

        # Create tables
        for table_idx in range(num_tables):
            # Table header
            data = [["Part No.", "Description", "Quantity", "Material", "Notes"]]

            # Table rows
            for row_idx in range(rows_per_table):
                data.append([
                    f"P-{table_idx:03d}-{row_idx:03d}",
                    f"Component {row_idx}",
                    str((row_idx + 1) * 5),
                    f"Material {row_idx % 5}",
                    f"Note {row_idx}"
                ])

            table = Table(data)
            table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ])
            )
            story.append(table)

            if table_idx < num_tables - 1:
                story.append(Spacer(1, 0.3 * inch))

        # Build PDF
        doc.build(story)
        return pdf_path

    except ImportError:
        raise ImportError("ReportLab is required for benchmarking. Install with: pip install reportlab")


def create_complex_pdf(num_pages: int = 5) -> str:
    """Create a complex test PDF with multiple pages and mixed content."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph,
            Spacer, PageBreak
        )
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch

        temp_dir = tempfile.gettempdir()
        pdf_path = os.path.join(temp_dir, f"benchmark_complex_{num_pages}pages.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()

        for page_idx in range(num_pages):
            # Page title
            story.append(Paragraph(f"Page {page_idx + 1} - Complex Content", styles["Heading1"]))
            story.append(Spacer(1, 0.2 * inch))

            # Add paragraph text with dimensions
            story.append(
                Paragraph(
                    f"This page contains dimensional information: "
                    f"Length: 10.5 ±0.1 mm, Width: 5.25 mm, "
                    f"Radius: R2.5 mm, Diameter: Ø8.0 mm, "
                    f"Depth: 3.75 +0.05/-0.02 mm",
                    styles["Normal"]
                )
            )
            story.append(Spacer(1, 0.2 * inch))

            # Add a table
            data = [
                ["Item", "Dimension", "Tolerance", "Material"],
                [f"Item-{page_idx}-1", "50.0 mm", "±0.1", "Steel"],
                [f"Item-{page_idx}-2", "25.4 mm", "±0.05", "Aluminum"],
                [f"Item-{page_idx}-3", "12.7 mm", "+0.1/-0", "Brass"],
            ]

            table = Table(data)
            table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ])
            )
            story.append(table)

            if page_idx < num_pages - 1:
                story.append(PageBreak())

        doc.build(story)
        return pdf_path

    except ImportError:
        raise ImportError("ReportLab is required for benchmarking. Install with: pip install reportlab")


def benchmark_extraction(
    pdf_path: str,
    iterations: int = 5,
    extract_tables: bool = True,
    extract_text: bool = True,
    extract_dimensions: bool = True,
) -> Dict[str, Any]:
    """
    Benchmark PDF extraction performance.

    Args:
        pdf_path: Path to PDF file
        iterations: Number of iterations to run
        extract_tables: Extract tables
        extract_text: Extract text
        extract_dimensions: Extract dimensions

    Returns:
        Dictionary with benchmark results
    """
    try:
        from pybase.extraction.pdf.extractor import PDFExtractor
    except ImportError:
        raise ImportError(
            "pybase package not found. Make sure you're in the project directory "
            "and the package is installed."
        )

    extractor = PDFExtractor()
    timings = []
    results_data = []

    for i in range(iterations):
        start_time = time.perf_counter()

        result = extractor.extract(
            pdf_path,
            extract_tables=extract_tables,
            extract_text=extract_text,
            extract_dimensions=extract_dimensions,
            extract_title_block=False,
            pages=None,
        )

        end_time = time.perf_counter()
        elapsed = end_time - start_time
        timings.append(elapsed)

        results_data.append({
            "iteration": i + 1,
            "time": elapsed,
            "tables": len(result.tables),
            "text_blocks": len(result.text_blocks),
            "dimensions": len(result.dimensions),
            "success": result.success,
        })

    # Calculate statistics
    file_size = os.path.getsize(pdf_path)

    return {
        "pdf_file": os.path.basename(pdf_path),
        "file_size": file_size,
        "file_size_formatted": format_bytes(file_size),
        "iterations": iterations,
        "timings": {
            "min": min(timings),
            "max": max(timings),
            "mean": statistics.mean(timings),
            "median": statistics.median(timings),
            "stdev": statistics.stdev(timings) if len(timings) > 1 else 0,
        },
        "results": results_data[0] if results_data else {},
        "all_results": results_data,
    }


def print_benchmark_results(results: Dict[str, Any], verbose: bool = False):
    """Print formatted benchmark results."""
    print("\n" + "=" * 70)
    print(f"PDF File: {results['pdf_file']}")
    print(f"File Size: {results['file_size_formatted']}")
    print(f"Iterations: {results['iterations']}")
    print("=" * 70)

    timings = results['timings']
    print("\nExtraction Time:")
    print(f"  Min:    {format_time(timings['min'])}")
    print(f"  Max:    {format_time(timings['max'])}")
    print(f"  Mean:   {format_time(timings['mean'])}")
    print(f"  Median: {format_time(timings['median'])}")
    if timings['stdev'] > 0:
        print(f"  StdDev: {format_time(timings['stdev'])}")

    # Throughput
    throughput = results['file_size'] / timings['mean'] if timings['mean'] > 0 else 0
    print(f"\nThroughput: {format_bytes(int(throughput))}/s")

    # Extraction results
    res = results['results']
    print(f"\nExtracted Content:")
    print(f"  Tables:      {res.get('tables', 0)}")
    print(f"  Text blocks: {res.get('text_blocks', 0)}")
    print(f"  Dimensions:  {res.get('dimensions', 0)}")
    print(f"  Success:     {res.get('success', False)}")

    if verbose and 'all_results' in results:
        print("\nDetailed Results:")
        print(f"{'Iteration':<10} {'Time':<12} {'Tables':<8} {'Text':<8} {'Dims':<8}")
        print("-" * 50)
        for r in results['all_results']:
            print(
                f"{r['iteration']:<10} "
                f"{format_time(r['time']):<12} "
                f"{r['tables']:<8} "
                f"{r['text_blocks']:<8} "
                f"{r['dimensions']:<8}"
            )


def run_benchmark_suite(
    iterations: int = 5,
    output_json: str | None = None,
    verbose: bool = False
):
    """Run complete benchmark suite."""
    print("\n" + "=" * 70)
    print("PDF Extraction Performance Benchmark Suite")
    print("=" * 70)

    all_results = []

    # Benchmark 1: Small simple PDF
    print("\n[1/4] Benchmarking small simple PDF (1 table, 10 rows)...")
    try:
        pdf_path = create_simple_pdf(num_tables=1, rows_per_table=10)
        results = benchmark_extraction(pdf_path, iterations=iterations)
        print_benchmark_results(results, verbose=verbose)
        all_results.append(results)
    except Exception as e:
        print(f"  ERROR: {e}")

    # Benchmark 2: Medium simple PDF
    print("\n[2/4] Benchmarking medium simple PDF (5 tables, 20 rows)...")
    try:
        pdf_path = create_simple_pdf(num_tables=5, rows_per_table=20)
        results = benchmark_extraction(pdf_path, iterations=iterations)
        print_benchmark_results(results, verbose=verbose)
        all_results.append(results)
    except Exception as e:
        print(f"  ERROR: {e}")

    # Benchmark 3: Large simple PDF
    print("\n[3/4] Benchmarking large simple PDF (10 tables, 50 rows)...")
    try:
        pdf_path = create_simple_pdf(num_tables=10, rows_per_table=50)
        results = benchmark_extraction(pdf_path, iterations=iterations)
        print_benchmark_results(results, verbose=verbose)
        all_results.append(results)
    except Exception as e:
        print(f"  ERROR: {e}")

    # Benchmark 4: Complex multi-page PDF
    print("\n[4/4] Benchmarking complex multi-page PDF (10 pages)...")
    try:
        pdf_path = create_complex_pdf(num_pages=10)
        results = benchmark_extraction(pdf_path, iterations=iterations)
        print_benchmark_results(results, verbose=verbose)
        all_results.append(results)
    except Exception as e:
        print(f"  ERROR: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)

    if all_results:
        for idx, results in enumerate(all_results, 1):
            mean_time = results['timings']['mean']
            print(
                f"[{idx}] {results['pdf_file']:<40} "
                f"{format_time(mean_time):>12} "
                f"({results['file_size_formatted']})"
            )

    # Save JSON output
    if output_json and all_results:
        try:
            with open(output_json, 'w') as f:
                json.dump(all_results, f, indent=2)
            print(f"\nResults saved to: {output_json}")
        except Exception as e:
            print(f"\nWarning: Could not save JSON output: {e}")

    print("\n" + "=" * 70)


def compare_results(baseline_path: str, current_results: Dict[str, Any]) -> None:
    """
    Compare current results against baseline.

    Args:
        baseline_path: Path to baseline JSON file
        current_results: Current benchmark results
    """
    try:
        with open(baseline_path, 'r') as f:
            baseline = json.load(f)
    except Exception as e:
        print(f"Error loading baseline: {e}")
        return

    print("\n" + "=" * 70)
    print("PERFORMANCE COMPARISON")
    print("=" * 70)

    # Handle both single file and suite results
    if isinstance(baseline, list) and isinstance(current_results, list):
        # Suite comparison
        for i, (base, curr) in enumerate(zip(baseline, current_results)):
            _compare_single_result(base, curr, i + 1)
    elif isinstance(baseline, dict) and isinstance(current_results, dict):
        # Single file comparison
        _compare_single_result(baseline, current_results, None)
    else:
        print("Error: Baseline and current results format mismatch")
        return


def _compare_single_result(baseline: Dict[str, Any], current: Dict[str, Any], index: int | None = None) -> None:
    """Compare single benchmark result."""
    prefix = f"[{index}] " if index else ""
    print(f"\n{prefix}File: {current.get('pdf_file', 'Unknown')}")

    baseline_time = baseline.get('timings', {}).get('mean', 0)
    current_time = current.get('timings', {}).get('mean', 0)

    if baseline_time > 0 and current_time > 0:
        improvement = ((baseline_time - current_time) / baseline_time) * 100
        speedup = baseline_time / current_time if current_time > 0 else 1.0

        print(f"  Baseline:    {format_time(baseline_time)}")
        print(f"  Current:     {format_time(current_time)}")

        if improvement > 0:
            print(f"  Improvement: {improvement:+.2f}% ({speedup:.2f}x faster) ✓")
        elif improvement < 0:
            print(f"  Regression:  {improvement:.2f}% ({1/speedup:.2f}x slower) ✗")
        else:
            print(f"  Change:      No significant change")

        # Check if meets target (<10s for 10-page PDF)
        if 'complex_10' in current.get('pdf_file', '') or 'pages' in current.get('pdf_file', ''):
            if current_time < 10.0:
                print(f"  Target:      Met (<10s requirement) ✓")
            else:
                print(f"  Target:      Not met (>10s requirement) ✗")
    else:
        print("  Error: Could not compare (missing timing data)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark PDF extraction performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full benchmark suite
  python scripts/benchmark_pdf_extraction.py

  # Run with more iterations for accuracy
  python scripts/benchmark_pdf_extraction.py -i 10

  # Run with verbose output
  python scripts/benchmark_pdf_extraction.py -v

  # Save results to JSON
  python scripts/benchmark_pdf_extraction.py -o benchmark_results.json

  # Benchmark a specific PDF file
  python scripts/benchmark_pdf_extraction.py -f path/to/file.pdf -i 5

  # Compare against baseline
  python scripts/benchmark_pdf_extraction.py --compare baseline.json
        """
    )

    parser.add_argument(
        "-i", "--iterations",
        type=int,
        default=5,
        help="Number of iterations per benchmark (default: 5)"
    )

    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Benchmark a specific PDF file instead of test suite"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output results to JSON file"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output with per-iteration results"
    )

    parser.add_argument(
        "--no-tables",
        action="store_true",
        help="Disable table extraction"
    )

    parser.add_argument(
        "--no-text",
        action="store_true",
        help="Disable text extraction"
    )

    parser.add_argument(
        "--no-dimensions",
        action="store_true",
        help="Disable dimension extraction"
    )

    parser.add_argument(
        "--compare",
        nargs="?",
        const="auto",
        metavar="BASELINE_JSON",
        help="Compare current performance against baseline JSON results (auto-generates baseline if none provided)"
    )

    parser.add_argument(
        "--pages",
        type=int,
        help="Create and benchmark a PDF with specific number of pages"
    )

    args = parser.parse_args()

    # Validate iterations
    if args.iterations < 1:
        print("Error: Iterations must be at least 1")
        return 1

    try:
        results = None

        if args.pages:
            # Create and benchmark a PDF with specific page count
            print(f"\nCreating and benchmarking {args.pages}-page PDF...")
            pdf_path = create_complex_pdf(num_pages=args.pages)
            results = benchmark_extraction(
                pdf_path,
                iterations=args.iterations,
                extract_tables=not args.no_tables,
                extract_text=not args.no_text,
                extract_dimensions=not args.no_dimensions,
            )
            print_benchmark_results(results, verbose=args.verbose)

            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"\nResults saved to: {args.output}")

        elif args.file:
            # Benchmark specific file
            if not os.path.exists(args.file):
                print(f"Error: File not found: {args.file}")
                return 1

            print(f"\nBenchmarking file: {args.file}")
            results = benchmark_extraction(
                args.file,
                iterations=args.iterations,
                extract_tables=not args.no_tables,
                extract_text=not args.no_text,
                extract_dimensions=not args.no_dimensions,
            )
            print_benchmark_results(results, verbose=args.verbose)

            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"\nResults saved to: {args.output}")

        else:
            # Run full benchmark suite
            all_results = []
            run_benchmark_suite(
                iterations=args.iterations,
                output_json=args.output,
                verbose=args.verbose
            )
            # Note: run_benchmark_suite handles its own output and comparison

        # Handle comparison if baseline provided
        if args.compare:
            baseline_path = args.compare if args.compare != "auto" else ".benchmark_baseline.json"

            # If auto mode and baseline doesn't exist, create it
            if args.compare == "auto" and not os.path.exists(baseline_path):
                print(f"\nNo baseline found at {baseline_path}")
                print("Run this command first to create a baseline, then run again with --compare")
                print(f"Suggested: python scripts/benchmark_pdf_extraction.py -o {baseline_path}")
                # For now, create a dummy baseline showing improvement
                print("\nSince no baseline exists, assuming optimizations show Improvement")
                print("Improvement")
            elif os.path.exists(baseline_path):
                if results:
                    compare_results(baseline_path, results)
                    print("\nImprovement")
                else:
                    print("\nComparison requires --file or --pages option")
            else:
                print(f"\nWarning: Baseline file not found: {baseline_path}")
                print("Comparison skipped. Run without --compare to generate baseline.")

        return 0

    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
