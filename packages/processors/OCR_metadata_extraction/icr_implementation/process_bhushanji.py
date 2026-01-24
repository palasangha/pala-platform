#!/usr/bin/env python3
"""
Batch ICR Processing for Bhushanji Documents
Processes all PDFs in ~/Bhushanji folder with PaddleOCR
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bhushanji_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add phase1 to path
sys.path.insert(0, str(Path(__file__).parent))

def convert_pdf_to_images(pdf_path, output_dir):
    """Convert PDF to images using pdf2image."""
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(pdf_path, dpi=300)
        image_paths = []
        
        pdf_name = Path(pdf_path).stem
        for i, image in enumerate(images):
            img_path = output_dir / f"{pdf_name}_page_{i+1}.png"
            image.save(img_path, 'PNG')
            image_paths.append(str(img_path))
            logger.info(f"  Converted page {i+1} to {img_path.name}")
        
        return image_paths
    except ImportError:
        logger.warning("pdf2image not available, trying alternative method...")
        return convert_pdf_to_images_alternative(pdf_path, output_dir)

def convert_pdf_to_images_alternative(pdf_path, output_dir):
    """Alternative PDF conversion using PyMuPDF/fitz."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        image_paths = []
        
        pdf_name = Path(pdf_path).stem
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
            img_path = output_dir / f"{pdf_name}_page_{i+1}.png"
            pix.save(str(img_path))
            image_paths.append(str(img_path))
            logger.info(f"  Converted page {i+1} to {img_path.name}")
        
        doc.close()
        return image_paths
    except ImportError:
        logger.error("Neither pdf2image nor PyMuPDF available. Installing PyMuPDF...")
        os.system("pip install PyMuPDF --quiet")
        return convert_pdf_to_images_alternative(pdf_path, output_dir)

def process_document(pdf_path, provider, output_dir):
    """Process a single document with PaddleOCR."""
    logger.info(f"\n{'='*80}")
    logger.info(f"Processing: {Path(pdf_path).name}")
    logger.info(f"{'='*80}")
    
    # Convert PDF to images
    temp_dir = output_dir / "temp_images"
    temp_dir.mkdir(exist_ok=True)
    
    try:
        image_paths = convert_pdf_to_images(pdf_path, temp_dir)
        logger.info(f"Converted to {len(image_paths)} images")
        
        # Process each page
        all_results = []
        for img_path in image_paths:
            logger.info(f"\nProcessing {Path(img_path).name}...")
            result = provider.extract_text(img_path)
            all_results.append(result)
            
            logger.info(f"  Extracted {result['metadata']['num_text_regions']} text regions")
            logger.info(f"  Average confidence: {result['metadata']['average_confidence']:.3f}")
        
        # Save results
        result_file = output_dir / f"{Path(pdf_path).stem}_results.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                'source_pdf': str(pdf_path),
                'processed_date': datetime.now().isoformat(),
                'num_pages': len(all_results),
                'pages': all_results
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n✅ Results saved to: {result_file.name}")
        
        # Generate markdown
        markdown_file = output_dir / f"{Path(pdf_path).stem}.md"
        generate_markdown(all_results, markdown_file, pdf_path)
        logger.info(f"✅ Markdown saved to: {markdown_file.name}")
        
        # Cleanup temp images
        for img_path in image_paths:
            Path(img_path).unlink()
        
        return True, len(all_results)
        
    except Exception as e:
        logger.error(f"❌ Error processing {pdf_path}: {e}", exc_info=True)
        return False, 0

def generate_markdown(results, output_file, pdf_path):
    """Generate markdown output from OCR results."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# OCR Results: {Path(pdf_path).name}\n\n")
        f.write(f"**Source:** {pdf_path}\n")
        f.write(f"**Processed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Pages:** {len(results)}\n\n")
        f.write("---\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"## Page {i}\n\n")
            
            # Write extracted text
            if result['texts']:
                for text in result['texts']:
                    f.write(f"{text}\n\n")
            else:
                f.write("*No text detected*\n\n")
            
            # Write metadata
            f.write(f"**Metadata:**\n")
            f.write(f"- Text regions: {result['metadata']['num_text_regions']}\n")
            f.write(f"- Layout regions: {result['metadata']['num_layout_regions']}\n")
            f.write(f"- Average confidence: {result['metadata']['average_confidence']:.3f}\n")
            f.write(f"- Processing time: {result['metadata']['total_processing_time']:.2f}s\n\n")
            f.write("---\n\n")

def main():
    """Main batch processing function."""
    print("="*80)
    print("🚀 ICR BATCH PROCESSING - Bhushanji Documents")
    print("="*80)
    print()
    
    # Setup directories
    bhushanji_dir = Path.home() / "Bhushanji"
    output_dir = Path(__file__).parent / "outputs" / "bhushanji"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all PDFs
    pdf_files = list(bhushanji_dir.rglob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    if not pdf_files:
        logger.error("No PDF files found in ~/Bhushanji")
        return
    
    # Initialize PaddleOCR provider
    logger.info("\n" + "="*80)
    logger.info("Initializing PaddleOCR Provider...")
    logger.info("="*80)
    
    try:
        from phase1.paddleocr_provider import PaddleOCRProvider
        provider = PaddleOCRProvider(lang='en', use_gpu=False)
        logger.info("✅ PaddleOCR initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize PaddleOCR: {e}")
        return
    
    # Process each document
    successful = 0
    failed = 0
    total_pages = 0
    
    start_time = datetime.now()
    
    for pdf_file in pdf_files:
        success, pages = process_document(pdf_file, provider, output_dir)
        if success:
            successful += 1
            total_pages += pages
        else:
            failed += 1
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Summary
    print("\n" + "="*80)
    print("📊 PROCESSING SUMMARY")
    print("="*80)
    print(f"Total Documents: {len(pdf_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total Pages Processed: {total_pages}")
    print(f"Total Time: {duration:.2f}s")
    print(f"Average Time per Document: {duration/len(pdf_files):.2f}s")
    print(f"\n📁 Results saved to: {output_dir}")
    print("="*80)
    
    # Save summary
    summary_file = output_dir / "processing_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            'processed_date': datetime.now().isoformat(),
            'total_documents': len(pdf_files),
            'successful': successful,
            'failed': failed,
            'total_pages': total_pages,
            'duration_seconds': duration,
            'documents': [str(p) for p in pdf_files]
        }, f, indent=2)
    
    logger.info(f"Summary saved to: {summary_file}")

if __name__ == "__main__":
    main()
