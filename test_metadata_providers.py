#!/usr/bin/env python3
"""
Diagnostic script to test Ollama metadata extraction
"""

import asyncio
import json
import logging
import os
import sys

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add packages to path
sys.path.insert(0, '/Users/vijayaraghavanvedantham/Documents/GitHub/pala-platform/packages/agents/metadata-extraction-agent')

from providers.ollama_provider import OllamaMetadataProvider
from providers.claude_provider import ClaudeMetadataProvider
from mappers.pala_mapper import PalaMapper


async def test_ollama():
    """Test Ollama metadata extraction"""
    logger.info("=" * 80)
    logger.info("Testing Ollama Metadata Provider")
    logger.info("=" * 80)
    
    provider = OllamaMetadataProvider()
    
    logger.info(f"Ollama Available: {provider.is_available()}")
    logger.info(f"Ollama URL: {provider.base_url}")
    logger.info(f"Ollama Model: {provider.model}")
    
    if not provider.is_available():
        logger.error("Ollama provider is not available!")
        logger.info("Troubleshooting:")
        logger.info("  1. Check if Ollama is running: curl http://localhost:11434/api/tags")
        logger.info("  2. Check OLLAMA_BASE_URL env var")
        logger.info("  3. Check OLLAMA_MODEL env var")
        logger.info("  4. Check OLLAMA_ENABLED env var")
        return
    
    # Test text - Meaningful Buddhist text about Goenka and Buddha
    test_text = """
    Letter Regarding the Study of Vipassana Meditation
    
    Date: 15th March 2024
    To: The Director of Dhamma Kamma Vipassana Centre
    From: Dr. Rajesh Kumar, Buddhist Studies Department
    
    Dear Venerable Sir/Madam,
    
    I am writing to inform you about our ongoing research project on Vipassana meditation techniques 
    as taught by Satya Narayan Goenka. Our institute has been studying the Dhamma teachings of 
    Gautama Buddha and their practical applications in modern times.
    
    Satya Narayan Goenka (1924-2013) was a renowned Vipassana teacher who preserved and propagated 
    the ancient meditation technique that Buddha taught. His contribution to making Vipassana accessible 
    to millions worldwide cannot be overstated. Through the establishment of Dhamma Kamma centers across 
    the globe, Goenka continued the lineage of Sayagyi U Ba Khin.
    
    Buddha, who lived approximately 2500 years ago in ancient India, discovered the path to liberation 
    through insight meditation (Vipassana). The core teaching of Buddha - the Four Noble Truths and the 
    Eightfold Path - remain the foundation of all Buddhist practice.
    
    We have collected several manuscripts and personal accounts from long-term meditators who studied 
    under Goenka at centers in Kulu, Himachal Pradesh, and Igatpuri, Maharashtra. These documents 
    detail the transformation and insights gained through intensive 10-day courses.
    
    We would like to request permission to study the archives at your center to better understand 
    the methodology and impact of Vipassana meditation as taught in the tradition of Buddha.
    
    Respectfully,
    Dr. Rajesh Kumar
    Department of Buddhist Philosophy
    Delhi University
    """
    
    logger.info("\nTest Text:")
    logger.info(test_text[:200] + "...")
    logger.info(f"\nText length: {len(test_text)} characters")
    
    try:
        logger.info("\nCalling extract_metadata...")
        result = await provider.extract_metadata(
            ocr_text=test_text,
            language="en",
            document_context="historical_letter"
        )
        
        logger.info("\n✓ Ollama extraction successful!")
        logger.info(f"\nRaw extracted data:")
        logger.info(json.dumps(result, indent=2))
        
        # Try to map to Pala schema
        logger.info("\n" + "=" * 80)
        logger.info("Attempting to map to Pala schema...")
        logger.info("=" * 80)
        
        try:
            pala_mapped = PalaMapper.map_extracted_data(result)
            logger.info("\n✓ Pala mapping successful!")
            logger.info(f"\nPala schema result:")
            logger.info(json.dumps(pala_mapped, indent=2))
        except Exception as e:
            logger.error(f"✗ Pala mapping failed: {e}")
            import traceback
            traceback.print_exc()
        
        return result
        
    except Exception as e:
        logger.error(f"✗ Ollama extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_claude():
    """Test Claude metadata extraction"""
    logger.info("\n" + "=" * 80)
    logger.info("Testing Claude Metadata Provider")
    logger.info("=" * 80)
    
    provider = ClaudeMetadataProvider()
    
    logger.info(f"Claude Available: {provider.is_available()}")
    
    if not provider.is_available():
        logger.warning("Claude provider is not available (expected if ANTHROPIC_API_KEY not set)")
        return
    
    # Test text
    test_text = "Letter to Abbot regarding manuscript acquisition"
    
    try:
        logger.info(f"\nCalling extract_metadata with text: {test_text}")
        result = await provider.extract_metadata(ocr_text=test_text)
        logger.info("\n✓ Claude extraction successful!")
        logger.info(json.dumps(result, indent=2))
        return result
    except Exception as e:
        logger.error(f"✗ Claude extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main test routine"""
    logger.info("Starting metadata provider diagnostics...\n")
    
    # Test Ollama
    ollama_result = await test_ollama()
    
    # Test Claude
    claude_result = await test_claude()
    
    logger.info("\n" + "=" * 80)
    logger.info("Diagnostics complete")
    logger.info("=" * 80)
    
    if ollama_result is None and claude_result is None:
        logger.error("\n✗ Both providers failed!")
        return 1
    elif ollama_result is not None:
        logger.info("\n✓ Ollama provider is working")
        return 0
    else:
        logger.info("\n⚠ Only Claude provider is available")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
