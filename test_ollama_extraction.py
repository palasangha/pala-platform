#!/usr/bin/env python3
"""Test Ollama metadata extraction to debug response format."""

import json
import aiohttp
import asyncio

async def test_ollama_extraction():
    """Test Ollama extraction with sample document text."""
    
    # Sample PDF-extracted text
    sample_text = """From Refusals to Last-Minute Rescue
29 September 1969
New Delhi

Ministry of External Affairs
Government of India

To: The Foreign Secretary

Subject: Vietnam Negotiations - Recent Developments

The attached documents chronicle recent diplomatic communications regarding the Vietnam War negotiations. Ambassador Johnson has indicated that significant progress may be possible in the coming weeks.

Key Points:
- Paris Peace Talks continuing
- Soviet Union offering limited support
- US government considering new proposals
- Indian delegation recommends cautious optimism

Prepared by: Dr. Ashok Mehta
Date: 29 September 1969
Confidentiality: Limited Distribution"""

    prompt = """You are an expert historical document analyst. Extract structured metadata from the provided OCR text.

Return ONLY valid JSON with these exact fields (use null for unknown, include all fields):
{
  "document_type": {
    "value": "letter|memo|telegram|email|report|other",
    "confidence": 0.0-1.0
  },
  "document_date": {
    "value": "YYYY-MM-DD or null",
    "confidence": 0.0-1.0
  },
  "parties": {
    "people": [{"name": "name", "role": "sender|recipient|mentioned", "confidence": 0.0-1.0}],
    "organizations": [{"name": "name", "role": "sender|recipient|mentioned", "confidence": 0.0-1.0}],
    "confidence": 0.0-1.0
  },
  "places": {
    "locations": [{"name": "location", "role": "mentioned", "confidence": 0.0-1.0}],
    "confidence": 0.0-1.0
  },
  "storage_location": {
    "archive": null,
    "collection": null,
    "box": null,
    "folder": null,
    "confidence": 0.0-1.0
  },
  "access_level": {
    "value": "public|restricted|private",
    "reasoning": "brief reason",
    "confidence": 0.0-1.0
  },
  "summary": {
    "value": "brief summary or null",
    "confidence": 0.0-1.0
  },
  "key_topics": {
    "topics": ["topic1", "topic2"],
    "confidence": 0.0-1.0
  },
  "tone_sentiment": {
    "tone": "formal|informal|urgent|neutral",
    "sentiment": "positive|negative|neutral",
    "confidence": 0.0-1.0
  },
  "language": "en",
  "notes": null
}

CRITICAL: Return ONLY JSON, no markdown, no extra text."""

    base_url = "http://localhost:11434"
    model = "mistral"
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"Testing {model} at {base_url}...")
            print(f"Text length: {len(sample_text)} chars\n")
            
            async with session.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": f"{prompt}\n\nDocument text:\n\n{sample_text}",
                    "stream": False,
                    "format": "json",
                },
                timeout=aiohttp.ClientTimeout(total=120),
            ) as response:
                if response.status != 200:
                    print(f"Error: HTTP {response.status}")
                    return
                
                result = await response.json()
                response_text = result.get("response", "")
                
                print("=" * 80)
                print("RAW RESPONSE:")
                print("=" * 80)
                print(response_text)
                print("\n" + "=" * 80)
                
                # Try to parse
                try:
                    parsed = json.loads(response_text)
                    print("JSON PARSE: SUCCESS")
                    print(json.dumps(parsed, indent=2))
                except json.JSONDecodeError as e:
                    print(f"JSON PARSE: FAILED - {e}")
                    
                    # Try regex fallback
                    import re
                    json_match = re.search(r"\{[\s\S]*\}", response_text)
                    if json_match:
                        print("\nAttempting regex extraction...")
                        try:
                            parsed = json.loads(json_match.group())
                            print("REGEX EXTRACTION: SUCCESS")
                            print(json.dumps(parsed, indent=2))
                        except json.JSONDecodeError as e2:
                            print(f"REGEX EXTRACTION: FAILED - {e2}")
                    else:
                        print("No JSON found in response")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ollama_extraction())
