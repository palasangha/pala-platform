"""
OCR Chain Service for executing sequential OCR provider chains
"""

import logging
import os
from datetime import datetime
from .ocr_service import OCRService

logger = logging.getLogger(__name__)


class OCRChainService:
    """Service for executing chains of OCR providers"""

    def __init__(self):
        """Initialize the chain service with OCR service"""
        self.ocr_service = OCRService()

    def execute_chain(self, image_path, steps, languages=None, handwriting=False, job_id=None):
        """
        Execute a chain of OCR providers on a single image

        Args:
            image_path: Path to the image file
            steps: List of step configurations, each containing:
                - step_number: Sequential step number
                - provider: OCR provider name
                - input_source: "original_image", "previous_step", "step_N", or "combined"
                - input_step_numbers: List of step numbers (if input_source is "step_N" or "combined")
                - prompt: Custom prompt for the provider (optional)
                - enabled: Whether step is enabled (optional, default: True)
            languages: List of language codes
            handwriting: Boolean for handwriting detection
            job_id: Optional job ID for tracking intermediate images

        Returns:
            dict: Complete chain execution results with all step outputs
                {
                    'success': bool,
                    'steps': [
                        {
                            'step_number': int,
                            'provider': str,
                            'input_source': str,
                            'prompt': str,
                            'output': {
                                'text': str,
                                'full_text': str,
                                'confidence': float,
                            },
                            'metadata': {
                                'processing_time_ms': int,
                                'timestamp': str (ISO format),
                                'input_length': int,
                                'output_length': int,
                            },
                            'error': str (if failed),
                        }
                    ],
                    'final_output': str,
                    'total_processing_time_ms': int,
                }
        """
        import time
        start_time = time.time()

        logger.info(f"Starting chain execution with {len(steps)} steps for image: {image_path}")

        # Validate chain
        is_valid, error_msg = self.validate_chain(steps)
        if not is_valid:
            logger.error(f"Chain validation failed: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'steps': []
            }

        # Track outputs from all steps for input routing
        previous_outputs = {}
        step_results = []
        final_output = None

        # Execute each step
        for step in steps:
            step_number = step.get('step_number')
            provider_name = step.get('provider')
            input_source = step.get('input_source', 'original_image')
            prompt = step.get('prompt', '')
            enabled = step.get('enabled', True)

            # Skip disabled steps
            if not enabled:
                logger.debug(f"Skipping disabled step {step_number}")
                continue

            step_start = time.time()

            try:
                # Determine input for this step
                input_for_step = self._resolve_input(
                    step,
                    previous_outputs,
                    image_path
                )

                # Determine if we're processing text or image
                is_image_input = (input_source == 'original_image')

                logger.info(f"Executing step {step_number} with provider '{provider_name}' (input: {input_source})")

                # Validate file exists for image input
                if is_image_input and not os.path.exists(input_for_step):
                    raise FileNotFoundError(f"Image file not found: {input_for_step}")

                # Process with the specified provider
                if is_image_input:
                    # Original image processing
                    output = self.ocr_service.process_image(
                        image_path=input_for_step,
                        languages=languages,
                        handwriting=handwriting,
                        provider=provider_name,
                        custom_prompt=prompt if prompt else None,
                        job_id=job_id
                    )
                else:
                    # Text-based processing (for AI providers like Claude)
                    output = self._process_text_with_provider(
                        text_input=input_for_step,
                        provider_name=provider_name,
                        prompt=prompt,
                        languages=languages
                    )

                step_time = (time.time() - step_start) * 1000  # Convert to ms

                # Prepare step result
                step_result = {
                    'step_number': step_number,
                    'provider': provider_name,
                    'input_source': input_source,
                    'prompt': prompt,
                    'output': {
                        'text': output.get('text', ''),
                        'full_text': output.get('full_text', output.get('text', '')),
                        'confidence': output.get('confidence', 0.0),
                    },
                    'metadata': {
                        'processing_time_ms': int(step_time),
                        'timestamp': datetime.utcnow().isoformat(),
                        'input_length': len(str(input_for_step)),
                        'output_length': len(output.get('text', '')),
                    }
                }

                # Store output for future steps
                previous_outputs[step_number] = output
                final_output = output.get('text', '')

                step_results.append(step_result)
                logger.info(f"Step {step_number} completed successfully in {int(step_time)}ms")

            except Exception as e:
                step_time = (time.time() - step_start) * 1000
                error_msg = str(e)

                logger.error(f"Error in step {step_number}: {error_msg}", exc_info=True)

                step_result = {
                    'step_number': step_number,
                    'provider': provider_name,
                    'input_source': input_source,
                    'prompt': prompt,
                    'error': error_msg,
                    'metadata': {
                        'processing_time_ms': int(step_time),
                        'timestamp': datetime.utcnow().isoformat(),
                    }
                }

                step_results.append(step_result)

                # If step fails, store empty output for next steps to handle gracefully
                previous_outputs[step_number] = {'text': '', 'confidence': 0.0}

                # Continue to next step instead of stopping (fail gracefully)

        total_time = (time.time() - start_time) * 1000

        return {
            'success': len(step_results) > 0,
            'steps': step_results,
            'final_output': final_output or '',
            'total_processing_time_ms': int(total_time),
        }

    def _resolve_input(self, step, previous_outputs, original_image_path):
        """
        Resolve the input for a step based on input_source configuration

        Args:
            step: Step configuration
            previous_outputs: Dictionary of previous step outputs
            original_image_path: Path to the original image

        Returns:
            str: Either a file path (for image input) or text content (for text input)
        """
        input_source = step.get('input_source', 'original_image')
        step_number = step.get('step_number')

        if input_source == 'original_image':
            return original_image_path

        elif input_source == 'previous_step':
            if step_number == 1:
                return original_image_path
            prev_step_num = step_number - 1
            return previous_outputs.get(prev_step_num, {}).get('text', '')

        elif input_source == 'step_N':
            input_step_numbers = step.get('input_step_numbers', [])
            if input_step_numbers:
                step_num = input_step_numbers[0]
                return previous_outputs.get(step_num, {}).get('text', '')
            return ''

        elif input_source == 'combined':
            input_step_numbers = step.get('input_step_numbers', [])
            texts = []
            for step_num in input_step_numbers:
                text = previous_outputs.get(step_num, {}).get('text', '')
                if text:
                    texts.append(text)
            return '\n\n---\n\n'.join(texts)

        return original_image_path

    def _process_text_with_provider(self, text_input, provider_name, prompt, languages=None):
        """
        Process text input with a provider (e.g., Claude for text processing)

        Args:
            text_input: Text to process
            provider_name: Provider name
            prompt: Custom prompt to use
            languages: Language codes (for context)

        Returns:
            dict: Processing result
        """
        provider = self.ocr_service.get_provider(provider_name)

        # Validate provider exists
        if not provider:
            raise ValueError(f"Provider '{provider_name}' not found or not available")

        # For text-based providers, we need to create a temporary approach
        # Some providers like Claude can process text directly via custom_prompt
        # Others may need the text embedded in the prompt

        try:
            # For AI providers, use text processing capability
            if hasattr(provider, 'process_text'):
                result = provider.process_text(
                    text=text_input,
                    custom_prompt=prompt
                )
            else:
                # Fall back to processing as part of custom prompt
                combined_prompt = f"{prompt}\n\n{text_input}" if prompt else text_input
                result = {
                    'text': combined_prompt,
                    'full_text': combined_prompt,
                    'confidence': 0.8,
                }

            return result

        except Exception as e:
            logger.error(f"Error processing text with {provider_name}: {str(e)}")
            raise

    def validate_chain(self, steps):
        """
        Validate chain configuration

        Args:
            steps: List of step configurations

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not steps or len(steps) == 0:
            return False, "Chain must have at least one step"

        # Validate step numbers and order
        for i, step in enumerate(steps):
            if step.get('step_number') != i + 1:
                return False, f"Step numbers must be sequential (expected {i+1}, got {step.get('step_number')})"

            if not step.get('provider'):
                return False, f"Step {i+1} must have a provider"

            input_source = step.get('input_source', 'original_image')
            if input_source not in ['original_image', 'previous_step', 'step_N', 'combined']:
                return False, f"Step {i+1} has invalid input_source: {input_source}"

            # Validate input source references
            if input_source == 'previous_step' and i == 0:
                return False, "Step 1 cannot use 'previous_step' as input"

            # Check for circular dependencies
            if input_source == 'step_N':
                input_steps = step.get('input_step_numbers', [])
                if not input_steps:
                    return False, f"Step {i+1} has input_source='step_N' but no input_step_numbers"

                for input_step_num in input_steps:
                    if input_step_num >= step.get('step_number', i+1):
                        return False, f"Step {i+1} cannot reference step {input_step_num} (cannot reference self or future steps)"

            elif input_source == 'combined':
                input_steps = step.get('input_step_numbers', [])
                if not input_steps:
                    return False, f"Step {i+1} has input_source='combined' but no input_step_numbers"

                for input_step_num in input_steps:
                    if input_step_num >= step.get('step_number', i+1):
                        return False, f"Step {i+1} cannot reference step {input_step_num} (cannot reference self or future steps)"

        return True, None

    def generate_timeline(self, chain_results):
        """
        Generate timeline visualization data from chain results

        Args:
            chain_results: Complete chain execution results from execute_chain()

        Returns:
            dict: Timeline visualization data
        """
        timeline = {
            'steps': [],
            'total_time_ms': chain_results.get('total_processing_time_ms', 0),
            'success': chain_results.get('success', False),
        }

        for step_result in chain_results.get('steps', []):
            step_item = {
                'step_number': step_result.get('step_number'),
                'provider': step_result.get('provider'),
                'input_source': step_result.get('input_source'),
                'success': 'error' not in step_result,
                'processing_time_ms': step_result.get('metadata', {}).get('processing_time_ms', 0),
                'timestamp': step_result.get('metadata', {}).get('timestamp'),
            }

            if 'output' in step_result:
                # Truncate output preview to 200 chars
                output_text = step_result['output'].get('text', '')
                step_item['output_preview'] = output_text[:200] + ('...' if len(output_text) > 200 else '')
                step_item['confidence'] = step_result['output'].get('confidence', 0.0)
            else:
                step_item['output_preview'] = ''
                step_item['error'] = step_result.get('error', 'Unknown error')

            timeline['steps'].append(step_item)

        return timeline
