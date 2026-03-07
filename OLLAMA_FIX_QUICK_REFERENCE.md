# Quick Fix Reference: Ollama Metadata Generation

## TL;DR - What Was Wrong

The `metadata-extraction-agent` with Ollama was not generating metadata because:

1. **Missing `format: json` parameter** in Ollama API request
2. **Mapper not handling flat Ollama output** (only expected nested structures)

## TL;DR - What Was Fixed

### Fix #1: Added format parameter to Ollama API
**File**: `packages/agents/metadata-extraction-agent/providers/ollama_provider.py` (line ~131)

```python
# BEFORE (not working)
response = requests.post(
    f"{self.base_url}/api/generate",
    json={
        "model": self.model,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.3,
    },
    timeout=120,
)

# AFTER (working)
response = requests.post(
    f"{self.base_url}/api/generate",
    json={
        "model": self.model,
        "prompt": prompt,
        "format": "json",  # <-- THIS WAS MISSING
        "stream": False,
        "temperature": 0.3,
    },
    timeout=120,
)
```

### Fix #2: Updated mapper to handle flat structures
**File**: `packages/agents/metadata-extraction-agent/mappers/pala_mapper.py`

Updated methods to fallback from nested to flat structure:
- `_extract_parties()` - handles `people`/`organizations` directly
- `_extract_document_type()` - handles string type values
- `_extract_document_date()` - handles string date values
- `_extract_summary()` - handles string summary values
- `_extract_key_topics()` - handles list topic values directly
- `_extract_tone_sentiment()` - handles string tone values

**Pattern**:
```python
# OLD: Only checked nested structure
parties_data = PalaMapper._as_dict(data.get("parties"))
people = PalaMapper._as_list(parties_data.get("people"))

# NEW: Also checks flat structure
parties_data = PalaMapper._as_dict(data.get("parties"))
people = PalaMapper._as_list(parties_data.get("people"))

if not people:  # Fallback to flat structure
    people = PalaMapper._as_list(data.get("people"))
```

## Testing

```bash
cd /Users/vijayaraghavanvedantham/Documents/GitHub/pala-platform
source .venv/bin/activate
python3 test_metadata_providers.py
```

**Expected output after fix**:
```
✓ Ollama extraction successful!
Raw extracted data: {
  "people": [{"name": "Dr. Karma Tenzin", "role": "Sender"}],
  "organizations": [{"name": "Tashi Lhunpo Monastery"}],
  "confidence": 0.6
}

✓ Pala mapping successful!
Pala schema result: {
  "parties": {
    "people": [{"name": "Dr. Karma Tenzin", "role": "Sender", "confidence": 0.0}],
    "organizations": [{"name": "Tashi Lhunpo Monastery", ...}],
    "overall_confidence": 0.6
  },
  ...
}
```

## Why This Matters

1. **Ollama JSON Format Parameter**: Tells Ollama to respond with structured JSON instead of free-form text
   - Without it: Returns text like "The document mentions Dr. Karma Tenzin..."
   - With it: Returns proper JSON like `{"people": [...], "organizations": [...]}`

2. **Provider Flexibility**: The mapper now works with both:
   - Claude's nested structure: `{"parties": {"people": [...]}}`
   - Ollama's flat structure: `{"people": [...]}`

## Files Changed

| File | Change | Type |
|------|--------|------|
| `providers/ollama_provider.py` | Added `"format": "json"` | 1-line fix |
| `mappers/pala_mapper.py` | Added fallback logic to 6 methods | Enhancement |

## Impact

- ✓ Ollama metadata extraction now works correctly
- ✓ People, organizations, and confidence scores properly extracted
- ✓ Pala schema properly populated
- ✓ Still backward compatible with nested structures from other providers
- ✓ No breaking changes to existing code

## Related Issues

- Similar issue found in entity-agent initially - but it was already using format parameter correctly
- metadata-agent was using format parameter correctly
- This was a regression/oversight in metadata-extraction-agent

## Next Steps

1. Test with different Ollama models (currently using minicpm-v)
2. Improve prompt to extract more fields (places, storage_location, access_level)
3. Test with real document data from production
4. Monitor confidence scores
5. Consider adding retry logic for Ollama timeouts
