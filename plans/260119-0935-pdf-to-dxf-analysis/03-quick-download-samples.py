#!/usr/bin/env python3
"""Quick PDF Sample Download and Analysis Script"""
import json, sys
from datetime import datetime
from pathlib import Path

try:
    from b2sdk.v2 import B2Api, InMemoryAccountInfo
except ImportError:
    print("ERROR: b2sdk not installed. Run: pip install b2sdk")
    sys.exit(1)

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: PyMuPDF not installed. Run: pip install pymupdf")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
SAMPLES_DIR = OUTPUT_DIR / "samples"
OUTPUT_DIR.mkdir(exist_ok=True)
SAMPLES_DIR.mkdir(exist_ok=True)

def load_config():
    config_file = SCRIPT_DIR / "config.txt"
    config = {}
    with open(config_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config

def analyze_pdf(pdf_path):
    """Analyze PDF content type and DXF conversion quality."""
    analysis = {
        "path": str(pdf_path),
        "filename": Path(pdf_path).name,
        "is_valid": False,
        "page_count": 0,
        "content_type": "unknown",
        "has_vector_graphics": False,
        "has_images": False,
        "has_text": False,
        "image_count": 0,
        "vector_path_count": 0,
        "text_block_count": 0,
        "pdf_version": "",
        "producer": "",
        "creator": "",
        "estimated_dxf_quality": "unknown",
        "notes": []
    }
    try:
        doc = fitz.open(pdf_path)
        analysis["is_valid"] = True
        analysis["page_count"] = len(doc)
        analysis["pdf_version"] = doc.metadata.get("format", "")
        analysis["producer"] = doc.metadata.get("producer", "")
        analysis["creator"] = doc.metadata.get("creator", "")

        total_images, total_drawings, total_text_blocks = 0, 0, 0
        for page in doc:
            total_images += len(page.get_images())
            total_drawings += len(page.get_drawings())
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    total_text_blocks += 1

        analysis["image_count"] = total_images
        analysis["vector_path_count"] = total_drawings
        analysis["text_block_count"] = total_text_blocks
        analysis["has_vector_graphics"] = total_drawings > 10
        analysis["has_images"] = total_images > 0
        analysis["has_text"] = total_text_blocks > 0

        # Classify content type
        if total_drawings > 100 and total_images == 0:
            analysis["content_type"] = "vector"
            analysis["estimated_dxf_quality"] = "excellent"
        elif total_drawings > 100 and total_images > 0:
            analysis["content_type"] = "mixed"
            analysis["estimated_dxf_quality"] = "good"
        elif total_images > 0 and total_drawings < 10:
            analysis["content_type"] = "raster"
            analysis["estimated_dxf_quality"] = "poor"
        elif total_text_blocks > 0 and total_drawings < 10 and total_images == 0:
            analysis["content_type"] = "text_only"
            analysis["estimated_dxf_quality"] = "fair"

        doc.close()
    except Exception as e:
        analysis["notes"].append(f"Error: {e}")
    return analysis

def main():
    print("PDF SAMPLE DOWNLOAD AND ANALYSIS")
    print("=" * 60)

    config = load_config()

    # Check for existing samples first
    existing_samples = list(SAMPLES_DIR.glob("*.pdf"))
    if existing_samples:
        print(f"Found {len(existing_samples)} existing samples")
        samples = [{"local_path": str(p), "original_path": "local"} for p in existing_samples]
    else:
        # Download samples from B2
        key_id = config.get("B2_APPLICATION_KEY_ID")
        app_key = config.get("B2_APPLICATION_KEY")
        bucket_name = config.get("B2_BUCKET_NAME")

        if not all([key_id, app_key, bucket_name]):
            print(f"ERROR: Missing B2 config. Place PDFs manually in: {SAMPLES_DIR}")
            sys.exit(1)

        print("Connecting to Backblaze B2...")
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", key_id, app_key)
        bucket = b2_api.get_bucket_by_name(bucket_name)

        print("Scanning for PDF files...")
        pdf_files = []
        for file_version, _ in bucket.ls(recursive=True):
            if file_version.file_name.lower().endswith(".pdf"):
                pdf_files.append({
                    "name": file_version.file_name,
                    "size": file_version.size,
                    "id": file_version.id_
                })
            if len(pdf_files) >= 500:
                break

        print(f"Found {len(pdf_files)} PDFs, selecting 10 samples across size range...")

        # Sort by size and pick 10 samples across the distribution
        pdf_files.sort(key=lambda x: x["size"])
        n = len(pdf_files)
        indices = [int(i * n / 10) for i in range(10)] if n >= 10 else list(range(n))
        to_download = [pdf_files[i] for i in indices[:10]]

        samples = []
        for i, pdf_info in enumerate(to_download):
            local_path = SAMPLES_DIR / f"sample_{i+1:02d}.pdf"
            print(f"  Downloading {i+1}/10: {pdf_info['name'][:50]}... ({pdf_info['size']/1024:.1f} KB)")
            try:
                downloaded = bucket.download_file_by_id(pdf_info["id"])
                downloaded.save_to(str(local_path))
                samples.append({"local_path": str(local_path), "original_path": pdf_info["name"]})
                print(f"    Saved to: {local_path.name}")
            except Exception as e:
                print(f"    Error: {e}")

    if not samples:
        print("ERROR: No samples available")
        sys.exit(1)

    print(f"\nAnalyzing {len(samples)} samples...")
    results = {
        "timestamp": datetime.now().isoformat(),
        "sample_count": len(samples),
        "analyses": [],
        "summary": {
            "content_types": {},
            "quality_distribution": {},
            "total_pages": 0
        }
    }

    for sample in samples:
        analysis = analyze_pdf(sample["local_path"])
        analysis["original_b2_path"] = sample.get("original_path", "")
        results["analyses"].append(analysis)

        ct = analysis["content_type"]
        results["summary"]["content_types"][ct] = results["summary"]["content_types"].get(ct, 0) + 1

        q = analysis["estimated_dxf_quality"]
        results["summary"]["quality_distribution"][q] = results["summary"]["quality_distribution"].get(q, 0) + 1
        results["summary"]["total_pages"] += analysis["page_count"]

        print(f"  {analysis['filename']}: {ct}, quality={q}, pages={analysis['page_count']}")

    output_file = OUTPUT_DIR / "pdf-analysis.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Samples analyzed: {results['sample_count']}")
    print(f"Total pages: {results['summary']['total_pages']}")
    print(f"\nContent Types:")
    for ct, count in results["summary"]["content_types"].items():
        print(f"  {ct}: {count}")
    print(f"\nDXF Quality Estimates:")
    for q, count in results["summary"]["quality_distribution"].items():
        print(f"  {q}: {count}")
    print(f"\nResults saved to: {output_file}")

if __name__ == "__main__":
    main()
