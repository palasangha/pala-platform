#!/usr/bin/env python3
"""
Batch OCR Processing for Bhushanji JPG Images
Supports both Hindi and English text
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
        logging.FileHandler('logs/bhushanji_jpg_ocr.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Try EasyOCR first (supports Hindi)
try:
    import easyocr
    HAS_EASYOCR = True
    logger.info("✅ EasyOCR available (supports Hindi)")
except ImportError:
    HAS_EASYOCR = False
    logger.warning("EasyOCR not available - installing...")

# Try Tesseract
try:
    import pytesseract
    from PIL import Image
    HAS_TESSERACT = True
    logger.info("✅ Tesseract available")
except ImportError:
    HAS_TESSERACT = False
    logger.warning("Tesseract not available")

def get_language_for_path(file_path):
    """Determine language based on folder name."""
    path_str = str(file_path)
    if 'hin-typed' in path_str or 'hin-written' in path_str:
        return 'hindi'
    return 'english'

def ocr_with_easyocr(image_path, lang='en'):
    """OCR using EasyOCR - supports multiple languages."""
    global reader_cache
    
    # Initialize reader for the language
    cache_key = lang
    if 'reader_cache' not in globals():
        globals()['reader_cache'] = {}
    
    if cache_key not in globals()['reader_cache']:
        logger.info(f"Initializing EasyOCR reader for language: {lang}...")
        lang_codes = ['hi', 'en'] if lang == 'hindi' else ['en']
        globals()['reader_cache'][cache_key] = easyocr.Reader(lang_codes, gpu=False)
    
    reader = globals()['reader_cache'][cache_key]
    result = reader.readtext(str(image_path))
    
    texts = [item[1] for item in result]
    boxes = [item[0] for item in result]
    scores = [item[2] for item in result]
    
    return {
        'texts': texts,
        'boxes': boxes,
        'scores': scores,
        'method': 'easyocr',
        'language': lang,
        'num_elements': len(texts),
        'avg_confidence': sum(scores) / len(scores) if scores else 0.0
    }

def ocr_with_tesseract(image_path, lang='eng'):
    """OCR using Tesseract - supports Hindi with hin language."""
    from PIL import Image
    import numpy as np
    
    # Tesseract language codes
    tesseract_lang = 'hin+eng' if lang == 'hindi' else 'eng'
    
    # Open and convert image to numpy array
    img = Image.open(str(image_path))
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img_array = np.array(img)
    
    text = pytesseract.image_to_string(img_array, lang=tesseract_lang)
    data = pytesseract.image_to_data(img_array, lang=tesseract_lang, output_type=pytesseract.Output.DICT)
    
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
        'method': 'tesseract',
        'language': lang,
        'num_elements': len(texts),
        'avg_confidence': sum(scores) / len(scores) if scores else 0.0
    }

def process_image(image_path, language='english'):
    """Process single image with available OCR."""
    if HAS_EASYOCR:
        return ocr_with_easyocr(image_path, 'hindi' if language == 'hindi' else 'en')
    elif HAS_TESSERACT:
        return ocr_with_tesseract(image_path, 'hindi' if language == 'hindi' else 'eng')
    else:
        logger.error("No OCR engine available!")
        return None

def process_jpg_file(image_path, output_dir):
    """Process a single JPG image."""
    logger.info(f"\n{'='*80}")
    logger.info(f"Processing: {Path(image_path).name}")
    logger.info(f"{'='*80}")
    
    try:
        # Determine language
        language = get_language_for_path(image_path)
        logger.info(f"Detected language: {language}")
        
        # Process image
        result = process_image(image_path, language)
        
        if not result:
            return False
        
        logger.info(f"  Extracted {result['num_elements']} text elements")
        logger.info(f"  Average confidence: {result['avg_confidence']:.3f}")
        
        # Save results
        result_file = output_dir / f"{Path(image_path).stem}_results.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'source_image': str(image_path),
                'processed_date': datetime.now().isoformat(),
                'language': language,
                **result
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Results saved to: {result_file.name}")
        
        # Generate markdown
        markdown_file = output_dir / f"{Path(image_path).stem}.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(f"# {Path(image_path).stem}\n\n")
            f.write(f"**Source:** {Path(image_path).name}\n")
            f.write(f"**Language:** {language.title()}\n")
            f.write(f"**Processed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Elements Extracted:** {result['num_elements']}\n")
            f.write(f"**Confidence:** {result['avg_confidence']:.1%}\n\n")
            f.write("---\n\n")
            
            if 'full_text' in result:
                f.write(result['full_text'])
            else:
                f.write('\n\n'.join(result['texts']))
            f.write("\n\n---\n\n")
        
        logger.info(f"✅ Markdown saved to: {markdown_file.name}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error processing {image_path}: {e}", exc_info=True)
        return False

def main():
    """Main batch processing."""
    print("="*80)
    print("🚀 JPG OCR BATCH PROCESSING - Bhushanji Images")
    print("="*80)
    print()
    
    # Check OCR availability
    if not (HAS_EASYOCR or HAS_TESSERACT):
        print("❌ No OCR engine available!")
        print("Install with: pip install easyocr  OR  pip install pytesseract")
        return
    
    # Setup
    bhushanji_dir = Path.home() / "Bhushanji"
    output_dir = Path(__file__).parent / "outputs" / "bhushanji_images"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all JPG files
    jpg_files = list(bhushanji_dir.rglob("*.JPG"))
    jpg_files.extend(bhushanji_dir.rglob("*.jpg"))
    jpg_files.extend(bhushanji_dir.rglob("*.jpeg"))
    jpg_files.extend(bhushanji_dir.rglob("*.JPEG"))
    
    logger.info(f"Found {len(jpg_files)} JPG/JPEG files")
    
    if not jpg_files:
        logger.error("No JPG files found")
        return
    
    # Categorize by language
    hindi_typed = [f for f in jpg_files if 'hin-typed' in str(f)]
    hindi_written = [f for f in jpg_files if 'hin-written' in str(f)]
    english = [f for f in jpg_files if 'eng' in str(f)]
    
    logger.info(f"  Hindi (typed): {len(hindi_typed)}")
    logger.info(f"  Hindi (handwritten): {len(hindi_written)}")
    logger.info(f"  English: {len(english)}")
    
    # Process
    successful = 0
    failed = 0
    start_time = datetime.now()
    
    for jpg_file in jpg_files:
        if process_jpg_file(jpg_file, output_dir):
            successful += 1
        else:
            failed += 1
    
    duration = (datetime.now() - start_time).total_seconds()
    
    # Summary
    print("\n" + "="*80)
    print("📊 PROCESSING SUMMARY")
    print("="*80)
    print(f"Total Images: {len(jpg_files)}")
    print(f"  Hindi (typed): {len(hindi_typed)}")
    print(f"  Hindi (handwritten): {len(hindi_written)}")
    print(f"  English: {len(english)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Duration: {duration:.1f}s")
    print(f"📁 Results: {output_dir}")
    print("="*80)
    
    # Save summary
    summary_file = output_dir / "processing_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'processed_date': datetime.now().isoformat(),
            'total_images': len(jpg_files),
            'hindi_typed': len(hindi_typed),
            'hindi_handwritten': len(hindi_written),
            'english': len(english),
            'successful': successful,
            'failed': failed,
            'duration_seconds': duration,
            'images': [str(f) for f in jpg_files]
        }, f, indent=2)
    
    logger.info(f"Summary saved to: {summary_file}")

if __name__ == "__main__":
    main()
