#!/usr/bin/env python3
"""
Test script to demonstrate Ollama metadata extraction with meaningful Buddhist content
Shows the complete extraction and mapping workflow
"""

import asyncio
import json
import sys

sys.path.insert(0, '/Users/vijayaraghavanvedantham/Documents/GitHub/pala-platform/packages/agents/metadata-extraction-agent')

from providers.ollama_provider import OllamaMetadataProvider
from mappers.pala_mapper import PalaMapper


# Meaningful Buddhist text samples for testing
BUDDHIST_TEXT_SAMPLES = {
    "goenka_letter": """
    Letter to Dhamma Kamma Vipassana Centre Administration
    
    Date: 15th March 2024
    From: Dr. Rajesh Kumar, Department of Buddhist Philosophy
    To: The Director, Dhamma Kamma Vipassana Centre, Igatpuri
    
    Subject: Research Collaboration on Vipassana Meditation Techniques
    
    Dear Venerable Director,
    
    I hope this letter finds you in good health. I am writing to initiate a research collaboration 
    between Delhi University's Buddhist Studies Department and your esteemed centre.
    
    Our research focuses on the profound teachings of Satya Narayan Goenka (1924-2013), who dedicated 
    his life to spreading Vipassana meditation - the ancient meditation technique discovered by 
    Gautama Buddha approximately 2500 years ago.
    
    Goenka's lineage traces back to Sayagyi U Ba Khin, preserving the authentic teachings of Buddha 
    in the original Pali tradition. Through his efforts, Vipassana centers have been established 
    globally, with major centers in Kulu (Himachal Pradesh), Igatpuri (Maharashtra), and Bangalore.
    
    We have collected extensive documentation including:
    - Personal accounts from long-term meditators
    - Records of 10-day intensive courses
    - Teachings on the Four Noble Truths and the Eightfold Path
    - Documentation of Buddha's original insights
    
    We respectfully request access to your archives to study the methodology and transformative 
    impact of Vipassana practice as taught in Goenka's tradition.
    
    Thank you for considering our request. We look forward to your response.
    
    With deep respect,
    Dr. Rajesh Kumar
    Department of Buddhist Philosophy, Delhi University
    New Delhi, India
    """,
    
    "buddhist_manuscript": """
    Historical Manuscript - The Essence of Buddha's Teaching
    
    Compiled by: Monastery of Tashi Lhunpo
    Date: 14th Century
    Language: Tibetan Buddhist Sanskrit
    
    This sacred text preserves the core teachings of Gautama Buddha regarding enlightenment 
    and the nature of suffering. Buddha taught that suffering (dukkha) arises from ignorance 
    and craving, and can be eliminated through the practice of mindfulness meditation.
    
    The manuscript contains references to important Buddhist figures:
    - Gautama Buddha (563-483 BCE) - The historical Buddha who discovered the path to liberation
    - Ananda - Buddha's cousin and principal disciple
    - Mahakassapa - Buddha's foremost disciple in ascetic practice
    - Satya Narayan Goenka - Modern teacher who revived Vipassana meditation
    
    Key locations mentioned:
    - Bodh Gaya (Bihar) - Site of Buddha's enlightenment
    - Sarnath (Varanasi) - Where Buddha gave his first sermon
    - Lumbini (Nepal) - Birthplace of Buddha
    - Kusinara (Uttar Pradesh) - Place of Buddha's final nirvana
    
    The manuscript emphasizes Buddha's revolutionary approach to spiritual practice, accessible 
    to all people regardless of caste or social status. This democratization of spirituality 
    became a defining feature of Buddhist tradition.
    """,
    
    "vipassana_center_record": """
    Annual Report: Dhamma Kamma Vipassana Centre, Igatpuri
    Year: 2023-2024
    
    Executive Summary:
    Dhamma Kamma Centre, established under the guidance of Satya Narayan Goenka, has served 
    thousands of meditators seeking to study Buddha's ancient meditation technique known as Vipassana.
    
    Course Statistics:
    - 10-day intensive courses conducted: 24
    - Meditators trained: 1,200
    - Volunteer staff: 150
    - Countries represented: 45
    
    Notable Achievements:
    - Expansion of center facilities for better accommodation
    - Establishment of satellite centers in Kulu (Himachal Pradesh) and Nagpur
    - Publication of research studies on meditation benefits
    - Training of international teachers in Goenka's methodology
    
    Visitor Information:
    Director: Shree Prakash Sharma
    Location: Igatpuri, Taluka Igatpuri, District Nashik, Maharashtra State, India
    Affiliation: Global Vipassana Pagoda Trust (founded by Satya Narayan Goenka)
    
    The center remains dedicated to preserving Buddha's teachings and making Vipassana 
    meditation accessible to sincere seekers worldwide.
    """
}


async def test_buddhist_extraction():
    """Test Ollama extraction with meaningful Buddhist content"""
    
    print("\n" + "=" * 80)
    print("OLLAMA METADATA EXTRACTION - BUDDHIST TEXT SAMPLES")
    print("=" * 80 + "\n")
    
    provider = OllamaMetadataProvider()
    
    if not provider.is_available():
        print("ERROR: Ollama provider not available")
        return
    
    for sample_name, sample_text in BUDDHIST_TEXT_SAMPLES.items():
        print(f"\n{'=' * 80}")
        print(f"Sample: {sample_name.upper().replace('_', ' ')}")
        print(f"{'=' * 80}")
        
        print(f"\nText preview: {sample_text[:200]}...")
        print(f"Text length: {len(sample_text)} characters\n")
        
        try:
            # Extract metadata
            extracted = await provider.extract_metadata(
                ocr_text=sample_text,
                language="en",
                document_context="historical_buddhist_document"
            )
            
            print("EXTRACTED METADATA:")
            print(json.dumps(extracted, indent=2))
            
            # Map to Pala schema
            pala_mapped = PalaMapper.map_extracted_data(extracted)
            
            print("\nMAJOR FIELDS IN PALA SCHEMA:")
            print(f"  Parties (People): {len(pala_mapped['parties']['people'])} extracted")
            print(f"  Parties (Organizations): {len(pala_mapped['parties']['organizations'])} extracted")
            print(f"  Places: {len(pala_mapped['places']['locations'])} extracted")
            print(f"  Overall Confidence: {pala_mapped['quality_metrics']['overall_confidence']}")
            
            if pala_mapped['parties']['people']:
                print("\n  People found:")
                for person in pala_mapped['parties']['people']:
                    print(f"    - {person['name']}")
            
            if pala_mapped['parties']['organizations']:
                print("\n  Organizations found:")
                for org in pala_mapped['parties']['organizations']:
                    print(f"    - {org['name']}")
                    
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 80}")
    print("TEST COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_buddhist_extraction())
