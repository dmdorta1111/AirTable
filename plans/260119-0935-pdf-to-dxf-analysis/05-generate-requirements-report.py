#!/usr/bin/env python3
"""Requirements Report Generator - Consolidates all analysis results"""
import json, sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"

def load_json_safe(path):
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

def format_bytes(b):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.2f} {unit}"
        b = b / 1024
    return f"{b:.2f} PB"

def main():
    print("GENERATING REQUIREMENTS REPORT")
    
    neon_data = load_json_safe(OUTPUT_DIR / "neon-analysis.json")
    b2_data = load_json_safe(OUTPUT_DIR / "backblaze-analysis.json")
    pdf_data = load_json_safe(OUTPUT_DIR / "pdf-analysis.json")
    conv_data = load_json_safe(OUTPUT_DIR / "conversion-tests.json")
    
    report = []
    report.append("# PDF to DXF Conversion - Requirements Report")
    report.append("")
    report.append(f"**Generated:** {datetime.now().isoformat()}")
    report.append("")
    report.append("---")
    report.append("")
    
    report.append("## 1. Neon Database Analysis")
    report.append("")
    if neon_data and "error" not in neon_data:
        stats = neon_data.get("statistics", {})
        report.append(f"- **Total Tables:** {stats.get('total_tables', 'N/A')}")
        report.append(f"- **PDF-related Tables:** {stats.get('pdf_related_tables', 'N/A')}")
        report.append(f"- **Embedding Tables:** {stats.get('embedding_tables', 'N/A')}")
        report.append(f"- **Database Size:** {format_bytes(stats.get('database_size_bytes', 0))}")
        if neon_data.get("pdf_related_tables"):
            report.append("")
            report.append("### PDF-related Tables:")
            for t in neon_data["pdf_related_tables"]:
                report.append(f"- **{t['name']}**: {t.get('row_count', 'N/A')} rows")
    else:
        report.append("*Run 01-analyze-neon-database.py first*")
    report.append("")
    
    report.append("## 2. Backblaze B2 Storage Analysis")
    report.append("")
    if b2_data and "error" not in b2_data:
        files = b2_data.get("files", {})
        storage = b2_data.get("storage", {})
        pdf_analysis = b2_data.get("pdf_analysis", {})
        report.append(f"- **Bucket:** {b2_data.get('bucket_name', 'N/A')}")
        report.append(f"- **Total Files Scanned:** {files.get('total_count', 0):,}")
        report.append(f"- **PDF Files:** {files.get('pdf_count', 0):,}")
        report.append(f"- **Total Storage:** {format_bytes(storage.get('total_bytes', 0))}")
        report.append(f"- **PDF Storage:** {format_bytes(storage.get('pdf_bytes', 0))}")
        report.append(f"- **Avg PDF Size:** {pdf_analysis.get('average_size_mb', 'N/A')} MB")
        report.append("")
        report.append("### PDF Size Distribution:")
        for k, v in pdf_analysis.get("size_distribution", {}).items():
            report.append(f"- {k}: {v:,}")
    else:
        report.append("*Run 02-analyze-backblaze-storage.py first*")
    report.append("")
    
    report.append("## 3. PDF Content Analysis")
    report.append("")
    if pdf_data and "error" not in pdf_data:
        summary = pdf_data.get("summary", {})
        report.append(f"- **Samples Analyzed:** {pdf_data.get('sample_count', 0)}")
        report.append(f"- **Total Pages:** {summary.get('total_pages', 0)}")
        report.append("")
        report.append("### Content Types:")
        for ct, count in summary.get("content_types", {}).items():
            pct = count / max(1, pdf_data["sample_count"]) * 100
            report.append(f"- **{ct}:** {count} ({pct:.0f}%)")
        report.append("")
        report.append("### DXF Quality Estimate:")
        for q, count in summary.get("quality_distribution", {}).items():
            pct = count / max(1, pdf_data["sample_count"]) * 100
            report.append(f"- **{q}:** {count} ({pct:.0f}%)")
    else:
        report.append("*Run 03-download-and-analyze-samples.py first*")
    report.append("")
    
    report.append("## 4. Conversion Test Results")
    report.append("")
    if conv_data and "error" not in conv_data:
        summary = conv_data.get("summary", {})
        report.append(f"- **Method:** {conv_data.get('method', 'N/A')}")
        report.append(f"- **Success Rate:** {summary.get('total_success', 0)}/{conv_data.get('samples_tested', 0)}")
        report.append(f"- **Avg Time:** {summary.get('avg_time_seconds', 0)}s per file")
        report.append(f"- **Entities Created:** {summary.get('total_entities', 0):,}")
    else:
        report.append("*Run 04-test-pdf-to-dxf-conversion.py first*")
    report.append("")
    
    report.append("## 5. Recommendations")
    report.append("")
    if b2_data and conv_data:
        pdf_count = b2_data.get("files", {}).get("pdf_count", 100000)
        avg_time = conv_data.get("summary", {}).get("avg_time_seconds", 1)
        total_hours = pdf_count * avg_time / 3600
        report.append(f"### Estimated Processing Time for {pdf_count:,} files:")
        report.append(f"- Single-threaded: {total_hours:.1f} hours")
        report.append(f"- 8 workers: {total_hours/8:.1f} hours")
        report.append(f"- 50 workers: {total_hours/50:.1f} hours")
    report.append("")
    report.append("### Next Steps:")
    report.append("1. Review content type distribution")
    report.append("2. Decide handling for raster PDFs")
    report.append("3. Set up batch processing infrastructure")
    report.append("4. Implement error handling and progress tracking")
    
    output_file = OUTPUT_DIR / "REQUIREMENTS-REPORT.md"
    with open(output_file, "w") as f:
        f.write(chr(10).join(report))
    
    print(f"Report saved to: {output_file}")

if __name__ == "__main__":
    main()
