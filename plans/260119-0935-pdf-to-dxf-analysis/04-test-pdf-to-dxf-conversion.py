#!/usr/bin/env python3
"""PDF to DXF Conversion Test Script - Tests multiple conversion methods"""
import json, sys, time, os
from datetime import datetime
from pathlib import Path

try:
    import fitz
except ImportError:
    print("ERROR: PyMuPDF not installed. Run: pip install pymupdf")
    sys.exit(1)

try:
    import ezdxf
except ImportError:
    print("ERROR: ezdxf not installed. Run: pip install ezdxf")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "output"
SAMPLES_DIR = OUTPUT_DIR / "samples"
CONVERSION_DIR = OUTPUT_DIR / "conversion-tests"
CONVERSION_DIR.mkdir(exist_ok=True)

def convert_pdf_to_dxf_pymupdf_ezdxf(pdf_path, output_path):
    """Convert PDF to DXF using PyMuPDF for extraction and ezdxf for writing."""
    result = {"success": False, "time_seconds": 0, "entities_created": 0, "errors": [], "warnings": []}
    start_time = time.time()
    
    try:
        doc = fitz.open(pdf_path)
        dwg = ezdxf.new("R2010")
        msp = dwg.modelspace()
        entities = 0
        
        for page_num, page in enumerate(doc):
            drawings = page.get_drawings()
            for drawing in drawings:
                try:
                    items = drawing.get("items", [])
                    for item in items:
                        if item[0] == "l":  # line
                            p1, p2 = item[1], item[2]
                            msp.add_line((p1.x, -p1.y), (p2.x, -p2.y))
                            entities += 1
                        elif item[0] == "re":  # rectangle
                            rect = item[1]
                            points = [(rect.x0, -rect.y0), (rect.x1, -rect.y0), 
                                     (rect.x1, -rect.y1), (rect.x0, -rect.y1), (rect.x0, -rect.y0)]
                            msp.add_lwpolyline(points)
                            entities += 1
                        elif item[0] == "c":  # curve (bezier)
                            pts = item[1:]
                            if len(pts) >= 2:
                                points = [(p.x, -p.y) for p in pts if hasattr(p, "x")]
                                if len(points) >= 2:
                                    msp.add_lwpolyline(points)
                                    entities += 1
                except Exception as e:
                    result["warnings"].append(f"Page {page_num}, drawing error: {str(e)[:50]}")
            
            # Extract text
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                bbox = span.get("bbox", [0, 0, 0, 0])
                                try:
                                    msp.add_text(text, dxfattribs={"insert": (bbox[0], -bbox[1]), "height": max(1, span.get("size", 10) * 0.5)})
                                    entities += 1
                                except:
                                    pass
        
        doc.close()
        dwg.saveas(output_path)
        result["success"] = True
        result["entities_created"] = entities
        
    except Exception as e:
        result["errors"].append(str(e))
    
    result["time_seconds"] = round(time.time() - start_time, 2)
    return result

def main():
    print("PDF TO DXF CONVERSION TESTING")
    print("=" * 60)
    
    samples = list(SAMPLES_DIR.glob("*.pdf"))
    if not samples:
        print(f"ERROR: No PDF samples found in {SAMPLES_DIR}")
        print("Run 03-download-and-analyze-samples.py first")
        sys.exit(1)
    
    print(f"Found {len(samples)} samples to test")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "samples_tested": len(samples),
        "method": "PyMuPDF + ezdxf",
        "conversions": [],
        "summary": {
            "total_success": 0,
            "total_failed": 0,
            "avg_time_seconds": 0,
            "total_entities": 0
        }
    }
    
    total_time = 0
    for i, pdf_path in enumerate(samples):
        print(f"Testing {i+1}/{len(samples)}: {pdf_path.name}")
        
        output_path = CONVERSION_DIR / f"{pdf_path.stem}.dxf"
        conversion = convert_pdf_to_dxf_pymupdf_ezdxf(pdf_path, output_path)
        conversion["input_file"] = pdf_path.name
        conversion["output_file"] = output_path.name if conversion["success"] else None
        conversion["output_size_kb"] = round(output_path.stat().st_size / 1024, 1) if output_path.exists() else 0
        
        results["conversions"].append(conversion)
        
        if conversion["success"]:
            results["summary"]["total_success"] += 1
            results["summary"]["total_entities"] += conversion["entities_created"]
            print(f"  SUCCESS: {conversion['entities_created']} entities, {conversion['time_seconds']}s")
        else:
            results["summary"]["total_failed"] += 1
            print(f"  FAILED: {conversion['errors']}")
        
        total_time += conversion["time_seconds"]
    
    results["summary"]["avg_time_seconds"] = round(total_time / len(samples), 2) if samples else 0
    
    output_file = OUTPUT_DIR / "conversion-tests.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print("")
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Success: {results['summary']['total_success']}/{len(samples)}")
    print(f"Failed: {results['summary']['total_failed']}/{len(samples)}")
    print(f"Avg time: {results['summary']['avg_time_seconds']}s per file")
    print(f"Total entities: {results['summary']['total_entities']}")
    print(f"Results saved to: {output_file}")
    print(f"DXF files saved to: {CONVERSION_DIR}")

if __name__ == "__main__":
    main()
