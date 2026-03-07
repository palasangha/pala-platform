# Ollama Metadata Extraction Fix Summary

## Problem Identified
The `metadata-extraction-agent` was not generating any metadata when using the Ollama provider, while the older `metadata-agent` and `entity-agent` were working correctly.

## Root Cause Analysis

### Issue #1: Missing Dependencies
**Symptom**: `ModuleNotFoundError: No module named 'requests'`  
**Cause**: Required packages (`requests` and `ollama`) were not installed in the virtual environment  
**Location**: `packages/agents/metadata-extraction-agent/requirements.txt` had the packages listed but they weren't installed  
**Fix**: Installed `requests` and `ollama` packages via pip

### Issue #2: Architecture Difference - Format Parameter
**Symptom**: Ollama returning unstructured/incomplete JSON  
**Cause**: The newer `metadata-extraction-agent` was missing the `'format': 'json'` parameter in the Ollama API request  
**Location**: `packages/agents/metadata-extraction-agent/providers/ollama_provider.py`, line ~131

**Comparison with working implementations:**

#### metadata-agent (✓ Working)
```python
response = requests.post(
    f'{self.ollama_host}/api/generate',
    json={
        'model': self.model,
        'prompt': prompt,
        'format': 'json',  # <-- FORMAT PARAMETER
        'stream': False,
        'temperature': 0.3
    },
    timeout=30
)
```

#### entity-agent (✓ Working)
```python
response = requests.post(
    f'{self.ollama_host}/api/generate',
    json={
        'model': self.model,
        'prompt': prompt,
        'format': 'json',  # <-- FORMAT PARAMETER
        'stream': False,
        'temperature': 0.3
    },
    timeout=30
)
```

#### metadata-extraction-agent (✗ NOT Working)
```python
response = requests.post(
    f"{self.base_url}/api/generate",
    json={
        "model": self.model,
        "prompt": prompt,
        # MISSING 'format': 'json'
        "stream": False,
        "temperature": 0.3,
    },
    timeout=120,
)
```

**Fix**: Added `"format": "json"` parameter to the Ollama API request

### Issue #3: Mapper Structure Mismatch
**Symptom**: Extracted metadata not being populated in Pala schema (parties, summary, etc. all empty)  
**Cause**: The `PalaMapper` expected nested field structures (e.g., `{"parties": {"people": [...]}}`), but Ollama returns flat structures (e.g., `{"people": [...], "organizations": [...]}`)

**Example of structure mismatch:**

Ollama returns:
```json
{
  "people": [{"name": "Dr. Karma Tenzin", "role": "Sender"}],
  "organizations": [{"name": "Monastery"}],
  "confidence": 0.6
}
```

But PalaMapper expected:
```json
{
  "parties": {
    "people": [{"name": "Dr. Karma Tenzin", "role": "Sender"}],
    "organizations": [{"name": "Monastery"}],
    "confidence": 0.6
  }
}
```

**Fix**: Updated `PalaMapper` methods to handle both flat and nested structures:

1. **_extract_parties()**: Now checks for flat `people`/`organizations` fields if nested `parties` is empty
2. **_extract_document_type()**: Handles flat string values
3. **_extract_document_date()**: Handles flat string date values
4. **_extract_summary()**: Handles flat string summary values
5. **_extract_key_topics()**: Handles flat list topic values
6. **_extract_tone_sentiment()**: Handles flat string tone values

## Changes Made

### 1. Fixed OllamaMetadataProvider
**File**: `packages/agents/metadata-extraction-agent/providers/ollama_provider.py`
- Added `"format": "json"` parameter to API request (line ~131)

**Before**:
```python
json={
    "model": self.model,
    "prompt": prompt,
    "stream": False,
    "temperature": 0.3,
}
```

**After**:
```python
json={
    "model": self.model,
    "prompt": prompt,
    "format": "json",  # NEW
    "stream": False,
    "temperature": 0.3,
}
```

### 2. Enhanced PalaMapper for Provider Flexibility
**File**: `packages/agents/metadata-extraction-agent/mappers/pala_mapper.py`

Added fallback logic to each extraction method to handle both:
- **Nested structures** from Claude or other structured providers
- **Flat structures** from Ollama's direct JSON output

Example pattern applied to all field extractors:
```python
@staticmethod
def _extract_parties(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract parties (people and organizations)"""
    # Handle both nested structure (parties.people) and flat structure (people directly)
    parties_data = PalaMapper._as_dict(data.get("parties"))
    
    # Try nested structure first
    people = PalaMapper._as_list(parties_data.get("people"))
    organizations = PalaMapper._as_list(parties_data.get("organizations"))
    overall_confidence = parties_data.get("confidence", 0.0)
    
    # If nested structure is empty, try flat structure from Ollama
    if not people and not organizations:
        people = PalaMapper._as_list(data.get("people"))
        organizations = PalaMapper._as_list(data.get("organizations"))
        overall_confidence = data.get("confidence", 0.0)
    
    return {
        "people": [...],
        "organizations": [...],
        "overall_confidence": overall_confidence,
    }
```

## Testing Results

### Before Fixes
```
Raw extracted data: {"text": "...", "confidence": 0.6}
Pala schema: Empty parties, places, topics, etc.
```

### After Fixes
```
Raw extracted data: {
  "people": [{"name": "Dr. Karma Tenzin", "role": "Sender"}],
  "organizations": [{"name": "Monastery's Collection"}],
  "confidence": 0.6
}

Pala schema parties: {
  "people": [{"name": "Dr. Karma Tenzin", "role": "Sender", "confidence": 0.0}],
  "organizations": [{"name": "Monastery's Collection", ...}],
  "overall_confidence": 0.6
}
```

## Key Takeaways

1. **Format Parameter is Critical**: The `'format': 'json'` parameter in Ollama API requests is essential for getting structured JSON output. Without it, Ollama defaults to free-form text generation.

2. **Provider-Agnostic Design**: The mapper now supports multiple provider output formats, making it more robust and extensible for future providers.

3. **Architectural Consistency**: The fixes ensure `metadata-extraction-agent` follows the same patterns as `metadata-agent` and `entity-agent`, which were already working with Ollama.

4. **Dependency Management**: Always verify that required packages from requirements.txt are actually installed in the virtual environment.

## Files Modified

1. `packages/agents/metadata-extraction-agent/providers/ollama_provider.py`
   - Added `"format": "json"` parameter

2. `packages/agents/metadata-extraction-agent/mappers/pala_mapper.py`
   - Updated 6 extraction methods to handle both flat and nested structures:
     - `_extract_parties()`
     - `_extract_document_type()`
     - `_extract_document_date()`
     - `_extract_summary()`
     - `_extract_key_topics()`
     - `_extract_tone_sentiment()`

## Next Steps

- Run full integration tests with metadata-extraction-agent in the MCP server
- Test with different Ollama models to ensure compatibility
- Consider updating the prompt to extract more fields (places, storage_location, etc.)
- Monitor performance and confidence scores on production data
