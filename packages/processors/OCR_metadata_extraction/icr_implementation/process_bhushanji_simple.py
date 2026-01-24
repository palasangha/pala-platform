#!/usr/bin/env python3
"""
Simple Batch OCR for Bhushanji Documents using EasyOCR/Tesseract
Falls back to simpler OCR libraries when PaddleOCR has issues
"""

import os
import sys
from pathlib import Path
import json
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bhushanji_simple_ocr.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Try EasyOCR first
try:
    import easyocr
    HAS_EASYOCR = True
    logger.info("✅ EasyOCR available")
except ImportError:
    HAS_EASYOCR = False
    logger.warning("EasyOCR not available")

# Try Tesseract
try:
    import pytesseract
    from PIL import Image
    HAS_TESSERACT = True
    logger.info("✅ Tesseract available")
except ImportError:
    HAS_TESSERACT = False
    logger.warning("Tesseract not available")

def convert_pdf_to_images(pdf_path, output_dir):
    """Convert PDF to images using PyMuPDF."""
    import fitz  # PyMuPDF
    doc = fitz.open(pdf_path)
    image_paths = []
    
    pdf_name = Path(pdf_path).stem
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
        img_path = output_dir / f"{pdf_name}_page_{i+1}.png"
        pix.save(str(img_path))
        image_paths.append(str(img_path))
        logger.info(f"  Converted page {i+1}/{len(doc)}")
    
    doc.close()
    return image_paths

def ocr_with_easy(image_path):
    """OCR using EasyOCR."""
    global reader
    if 'reader' not in globals():
        logger.info("Initializing EasyOCR reader...")
        reader = easyocr.Reader(['en'], gpu=False)
    
    result = reader.readtext(image_path)
    texts = [item[1] for item in result]
    boxes = [item[0] for item in result]
    scores = [item[2] for item in result]
    
    return {
        'texts': texts,
        'boxes': boxes,
        'scores': scores,
        'method': 'easyocr'
    }

def ocr_with_tesseract(image_path):
    """OCR using Tesseract."""
    from PIL import Image
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    
    texts = []
    boxes = []
    scores = []
    
    for i in range(len(data['text'])):
        if data['text'][i].strip():
            texts.append(data['text'][i])
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            boxes.append([[x, y], [x+w, y], [x+w, y+h], [x, y+h]])
            scores.append(float(data['conf'][i])/100 if data['conf'][i] != '-1' else 0.0)
    
    return {
        'texts': texts,
        'boxes': boxes,
        'scores': scores,
        'full_text': text,
        'method': 'tesseract'
    }

def process_image(image_path):
    """Process single image with available OCR."""
    if HAS_EASYOCR:
        return ocr_with_easy(image_path)
    elif HAS_TESSERACT:
        return ocr_with_tesseract(image_path)
    else:
        logger.error("No OCR engine available!")
        return None

def process_document(pdf_path, output_dir):
    """Process a single PDF document."""
    logger.info(f"\n{'='*80}")
    logger.info(f"Processing: {Path(pdf_path).name}")
    logger.info(f"{'='*80}")
    
    temp_dir = output_dir / "temp_images"
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # Convert PDF to images
        image_paths = convert_pdf_to_images(pdf_path, temp_dir)
        logger.info(f"Converted to {len(image_paths)} pages")
        
        # Process each page
        all_results = []
        for i, img_path in enumerate(image_paths, 1):
            logger.info(f"Processing page {i}/{len(image_paths)}...")
            result = process_image(img_path)
            if result:
                result['page_num'] = i
                all_results.append(result)
                logger.info(f"  Extracted {len(result['texts'])} text elements")
        
        # Save results
        result_file = output_dir / f"{Path(pdf_path).stem}_results.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'source_pdf': str(pdf_path),
                'processed_date': datetime.now().isoformat(),
                'num_pages': len(all_results),
                'pages': all_results
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Results saved to: {result_file.name}")
        
        # Generate markdown
        markdown_file = output_dir / f"{Path(pdf_path).stem}.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(f"# {Path(pdf_path).stem}\n\n")
            f.write(f"**Processed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Pages:** {len(all_results)}\n\n")
            f.write("---\n\n")
            
            for page in all_results:
                f.write(f"## Page {page['page_num']}\n\n")
                if 'full_text' in page:
                    f.write(page['full_text'])
                else:
                    f.write('\n\n'.join(page['texts']))
                f.write("\n\n---\n\n")
        
        logger.info(f"✅ Markdown saved to: {markdown_file.name}")
        
        # Cleanup
        for img_path in image_paths:
            Path(img_path).unlink()
        
        return True, len(all_results)
        
    except Exception as e:
        logger.error(f"❌ Error processing {pdf_path}: {e}", exc_info=True)
        return False, 0

def main():
    """Main batch processing."""
    print("="*80)
    print("🚀 SIMPLE OCR BATCH PROCESSING - Bhushanji Documents")
    print("="*80)
    print()
    
    # Check OCR availability
    if not (HAS_EASYOCR or HAS_TESSERACT):
        print("❌ No OCR engine available!")
        print("Install with: pip install easyocr  OR  pip install pytesseract")
        return
    
    # Setup
    bhushanji_dir = Path.home() / "Bhushanji"
    output_dir = Path(__file__).parent / "outputs" / "bhushanji"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_files = list(bhushanji_dir.rglob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    if not pdf_files:
        logger.error("No PDF files found")
        return
    
    # Process
    successful = 0
    failed = 0
    total_pages = 0
    start_time = datetime.now()
    
    for pdf_file in pdf_files:
        success, pages = process_document(pdf_file, output_dir)
        if success:
            successful += 1
            total_pages += pages
        else:
            failed += 1
    
    duration = (datetime.now() - start_time).total_seconds()
    
    # Summary
    print("\n" + "="*80)
    print("📊 PROCESSING SUMMARY")
    print("="*80)
    print(f"Total Documents: {len(pdf_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total Pages: {total_pages}")
    print(f"Duration: {duration:.1f}s")
    print(f"📁 Results: {output_dir}")
    print("="*80)

if __name__ == "__main__":
    main()
