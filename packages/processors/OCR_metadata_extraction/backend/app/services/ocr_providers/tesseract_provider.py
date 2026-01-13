import os
from PIL import Image
from .base_provider import BaseOCRProvider
from ..pdf_service import PDFService

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None

class TesseractProvider(BaseOCRProvider):
    """Tesseract OCR Provider"""

    def __init__(self, tesseract_cmd=None):
        """
        Initialize Tesseract provider

        Args:
            tesseract_cmd: Path to tesseract executable (optional)
        """
        # Check if Tesseract is enabled
        enabled = os.getenv('TESSERACT_ENABLED', 'true').lower() in ('true', '1', 'yes')

        if not enabled:
            self._available = False
            print("Tesseract provider is disabled via TESSERACT_ENABLED environment variable")
            return

        self.tesseract_cmd = tesseract_cmd or os.getenv('TESSERACT_CMD')

        if not TESSERACT_AVAILABLE:
            self._available = False
            print("Tesseract not available: pytesseract package not installed")
            return

        try:
            # Set tesseract command path if provided
            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

            # Test if tesseract is available
            version = pytesseract.get_tesseract_version()
            self._available = True
            print(f"Tesseract version {version} initialized")
        except Exception as e:
            print(f"Tesseract initialization failed: {e}")
            self._available = False

    def get_name(self):
        return "tesseract"

    def is_available(self):
        return self._available and TESSERACT_AVAILABLE

    def process_image(self, image_path, languages=None, handwriting=False, custom_prompt=None):
        """Process image or PDF using Tesseract OCR"""
        if not self.is_available():
            raise Exception("Tesseract provider is not available")

        # Note: custom_prompt is not used by Tesseract OCR
        try:
            # Check if file is a PDF and convert if necessary
            temp_image_paths = []
            image_paths_to_process = []
            
            if PDFService.is_pdf(image_path):
                try:
                    temp_image_paths = PDFService.pdf_to_temp_images(image_path, dpi=150)
                    image_paths_to_process = temp_image_paths
                except Exception as pdf_error:
                    raise Exception(f"Failed to convert PDF to images: {str(pdf_error)}")
            else:
                image_paths_to_process = [image_path]
            
            # Aggregate results from all pages
            all_text = []
            all_blocks = []
            all_confidences = []
            
            for page_idx, img_path in enumerate(image_paths_to_process):
                try:
                    # Open image
                    image = Image.open(img_path)

                    # Convert RGBA to RGB if necessary
                    if image.mode == 'RGBA':
                        image = image.convert('RGB')
                    # Convert other single-channel modes to RGB
                    elif image.mode not in ('RGB', 'L'):
                        image = image.convert('RGB')

                    # Map language codes to Tesseract format
                    lang = self._map_languages(languages)

                    # Configure Tesseract
                    config = '--psm 3'  # Fully automatic page segmentation

                    # For handwriting, use different PSM mode
                    if handwriting:
                        config = '--psm 6'  # Assume a single uniform block of text

                    # Extract text
                    text = pytesseract.image_to_string(image, lang=lang, config=config)
                    
                    # Add page indicator for PDFs
                    if len(image_paths_to_process) > 1:
                        text = f"--- Page {page_idx + 1} ---\n{text}"
                    
                    all_text.append(text)

                    # Get detailed data with bounding boxes and confidence
                    data = pytesseract.image_to_data(image, lang=lang, config=config, output_type=pytesseract.Output.DICT)

                    # Extract blocks with confidence
                    current_block = {'text': '', 'confidence': 0, 'words': 0}

                    for i in range(len(data['text'])):
                        if data['text'][i].strip():
                            conf = float(data['conf'][i])
                            if conf > 0:  # Only include recognized text
                                current_block['text'] += data['text'][i] + ' '
                                current_block['confidence'] += conf
                                current_block['words'] += 1

                        # End of line or block
                        if data['block_num'][i] != data['block_num'][min(i + 1, len(data['text']) - 1)]:
                            if current_block['words'] > 0:
                                current_block['confidence'] /= current_block['words']
                                all_blocks.append({
                                    'text': current_block['text'].strip(),
                                    'confidence': current_block['confidence'] / 100.0,  # Tesseract uses 0-100 scale
                                    'page': page_idx + 1 if len(image_paths_to_process) > 1 else None
                                })
                                all_confidences.append(current_block['confidence'] / 100.0)
                            current_block = {'text': '', 'confidence': 0, 'words': 0}
                
                except Exception as page_error:
                    if len(image_paths_to_process) > 1:
                        all_text.append(f"--- Page {page_idx + 1} (Error) ---\n[Failed to process: {str(page_error)}]")
                    else:
                        raise

            # Cleanup temporary files
            if temp_image_paths:
                PDFService.cleanup_temp_images(temp_image_paths)
            
            # Combine results
            combined_text = '\n\n'.join(all_text)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0

            return {
                'text': combined_text.strip(),
                'full_text': combined_text.strip(),
                'words': [],
                'blocks': all_blocks,
                'confidence': avg_confidence,
                'pages_processed': len(image_paths_to_process),
                'file_info': {
                    'is_pdf': PDFService.is_pdf(image_path),
                    'filename': os.path.basename(image_path)
                }
            }

        except Exception as e:
            raise Exception(f"Tesseract OCR processing failed: {str(e)}")

    def _map_languages(self, languages):
        """Map language codes to Tesseract format"""
        if not languages:
            return 'eng'

        # Tesseract language code mapping
        lang_map = {
            'en': 'eng',
            'hi': 'hin',
            'es': 'spa',
            'fr': 'fra',
            'de': 'deu',
            'zh': 'chi_sim',
            'ja': 'jpn',
            'ar': 'ara',
            'ru': 'rus',
            'pt': 'por',
            'it': 'ita',
            'ko': 'kor'
        }

        # Convert language codes and join with +
        tesseract_langs = [lang_map.get(lang, lang) for lang in languages]
        return '+'.join(tesseract_langs)
