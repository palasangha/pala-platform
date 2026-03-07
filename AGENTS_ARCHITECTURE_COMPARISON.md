# Architecture Comparison: metadata-agent vs metadata-extraction-agent

## Quick Comparison Table

| Aspect | metadata-agent | metadata-extraction-agent | entity-agent |
|--------|---|---|---|
| **Purpose** | Document classification & archival metadata | Unified metadata extraction | Named Entity Recognition |
| **Tools** | 4 specialized tools | 1 unified tool | 5 NER tools |
| **Provider Support** | Ollama only | Claude + Ollama (extensible) | Ollama (with Claude disambiguation) |
| **Output Schema** | Tool-specific | Pala/Archipelago/Combined | Tool-specific |
| **Architecture** | Tool classes | Provider abstraction | Tool classes + Provider abstraction |
| **Status** | ✓ Working | ✓ Fixed | ✓ Working |

## Detailed Comparison

### 1. metadata-agent (Focused, Domain-Specific)

**Location**: `packages/agents/metadata-agent/`

**Structure**:
```
metadata-agent/
├── main.py (Agent orchestration + 4 tool handlers)
├── tools/
│   ├── document_classifier.py (Document type: letter, memo, etc.)
│   ├── storage_extractor.py (Archive location info)
│   ├── access_determiner.py (Public/Restricted/Private)
│   └── __init__.py
├── Dockerfile
└── requirements.txt
```

**Tools**:
1. `extract_document_type` - Classify as letter/memo/telegram/fax/email/invitation
2. `extract_storage_info` - Parse archive, collection, box, folder
3. `extract_digitization_metadata` - Scanning date, operator, equipment
4. `determine_access_level` - Public/restricted/private classification

**Ollama Usage**:
```python
response = requests.post(
    f'{self.ollama_host}/api/generate',
    json={
        'model': self.model,
        'prompt': prompt,
        'format': 'json',  # ✓ Specifies JSON format
        'stream': False,
        'temperature': 0.3
    },
    timeout=30
)
```

**Strengths**:
- ✓ Simple, focused responsibility
- ✓ Each tool does one thing well
- ✓ Easy to test independently
- ✓ Uses Ollama JSON format parameter
- ✓ Has fallback heuristics for each tool

**Limitations**:
- ✗ Only supports Ollama
- ✗ Cannot generate full unified metadata
- ✗ No schema abstraction (tool-specific output)
- ✗ Cannot easily add new providers

### 2. metadata-extraction-agent (Unified, Provider-Agnostic)

**Location**: `packages/agents/metadata-extraction-agent/`

**Structure**:
```
metadata-extraction-agent/
├── main.py (Agent orchestration + 1 unified tool)
├── providers/
│   ├── base_provider.py (Interface)
│   ├── claude_provider.py (Claude implementation)
│   ├── ollama_provider.py (Ollama implementation)
│   └── __init__.py
├── mappers/
│   ├── pala_mapper.py (→ Pala schema v1.0.0)
│   ├── archipelago_mapper.py (→ Archipelago Commons)
│   └── __init__.py
├── tests/
├── Dockerfile
└── requirements.txt
```

**Tool**:
1. `extract_metadata` - Unified extraction with:
   - `text` (required) - OCR extracted text
   - `model` (required) - Provider selection (claude/ollama/gemini/openai)
   - `output_type` (required) - Schema (pala/archipelago/combined)
   - `language` (optional) - ISO language code
   - `document_context` (optional) - Context hint
   - `custom_prompt` (optional) - Override prompt

**Provider Pattern**:
```python
class BaseMetadataProvider(ABC):
    @abstractmethod
    async def extract_metadata(
        self,
        ocr_text: str,
        language: Optional[str] = None,
        document_context: Optional[str] = None,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract structured metadata"""
```

**Ollama Implementation** (NOW FIXED):
```python
response = requests.post(
    f"{self.base_url}/api/generate",
    json={
        "model": self.model,
        "prompt": prompt,
        "format": "json",  # ✓ FIXED - Was missing before
        "stream": False,
        "temperature": 0.3,
    },
    timeout=120,
)
```

**Output Structure**:
```python
{
    "schema_version": "1.0.0",
    "extraction_metadata": {
        "model_used": "ollama",
        "timestamp": "ISO8601",
        "processing_time_ms": int,
        "input_length": int
    },
    "confidence_scores": {
        "overall": float,
        "field_name": float,
        ...
    },
    "pala_metadata": {...},        # if output_type includes pala
    "archipelago_metadata": {...}, # if output_type includes archipelago
    "extracted_fields": {...}      # if output_type is "combined"
}
```

**Strengths**:
- ✓ Provider-agnostic (Claude, Ollama, extensible for Gemini/OpenAI)
- ✓ Unified single tool vs. multiple tools
- ✓ Multiple output schemas (Pala, Archipelago, Combined)
- ✓ Consistent confidence scoring
- ✓ Extensible mapper pattern
- ✓ Flexible parameter passing (custom_prompt, document_context)

**Limitations**:
- ✗ Was missing Ollama format parameter (NOW FIXED)
- ✗ Mapper expected nested structures (NOW FIXED with fallback logic)
- ✗ More complex architecture
- ✗ More dependencies

### 3. entity-agent (Hybrid: Ollama + Claude)

**Location**: `packages/agents/entity-agent/`

**Structure**:
```
entity-agent/
├── main.py (Agent orchestration + 5 tool handlers)
├── tools/
│   ├── ner_extractor.py (Ollama-based NER)
│   ├── entity_disambiguator.py (Claude-based disambiguation)
│   ├── relationship_mapper.py (Ollama)
│   └── __init__.py
├── Dockerfile
└── requirements.txt
```

**Tools**:
1. `extract_people` - Extract + disambiguate person names
2. `extract_organizations` - Extract organization names
3. `extract_locations` - Extract geographic entities
4. `extract_events` - Extract historical events
5. `generate_relationships` - Map entity connections

**Hybrid Approach**:
```python
# Step 1: Extract using Ollama
raw_people = await self.ner_extractor.extract_people(text)

# Step 2: Disambiguate using Claude (if available)
people = await self.disambiguator.disambiguate_people(
    raw_people.get('people', []),
    text[:2000]
)
```

**Ollama Usage** (Correct):
```python
response = requests.post(
    f'{self.ollama_host}/api/generate',
    json={
        'model': self.model,
        'prompt': prompt,
        'format': 'json',  # ✓ Uses format parameter
        'stream': False,
        'temperature': 0.3
    },
    timeout=30
)
```

**Strengths**:
- ✓ Combines Ollama efficiency with Claude accuracy
- ✓ Uses format parameter correctly
- ✓ Focused on entity recognition
- ✓ Fallback mechanisms

**Limitations**:
- ✗ Requires both Ollama and Claude (expensive)
- ✗ Tool-specific outputs (no unified schema)

## Key Differences Highlighted

### 1. Format Parameter
```
✓ metadata-agent:           json={'format': 'json', ...}
✗ metadata-extraction-agent: json={...}  [MISSING - NOW FIXED]
✓ entity-agent:             json={'format': 'json', ...}
```

### 2. Provider Pattern
```
metadata-agent:               Direct tool classes
metadata-extraction-agent:    Provider abstraction (extensible)
entity-agent:                 Tool classes + Provider components
```

### 3. Schema Output
```
metadata-agent:               Tool-specific JSON
metadata-extraction-agent:    Unified (Pala/Archipelago/Combined)
entity-agent:                 Tool-specific JSON
```

### 4. Mapper Flexibility
```
metadata-agent:               No mapper (raw output)
metadata-extraction-agent:    Flexible mappers (now handle flat + nested)
entity-agent:                 No mapper (raw output)
```

## When to Use Which Agent

### Use metadata-agent when:
- You need quick, focused document classification
- Only Ollama is available
- You want simple, independent tools
- Minimal dependencies preferred
- Domain-specific metadata (document type, storage, access level)

### Use metadata-extraction-agent when:
- You need unified metadata extraction
- Want flexibility to switch between Claude and Ollama
- Need standard schema output (Pala/Archipelago)
- Planning to add more providers (Gemini, OpenAI, etc.)
- Want confidence scores and structured extraction_metadata

### Use entity-agent when:
- You need Named Entity Recognition specifically
- Want high-accuracy entity disambiguation
- Can afford Claude API calls for disambiguation
- Need to extract people, organizations, locations, events

## Migration Path

If migrating from `metadata-agent` to `metadata-extraction-agent`:

1. Replace tool calls:
   ```
   OLD: Call extract_document_type + extract_storage_info + determine_access_level
   NEW: Call extract_metadata with model="ollama", output_type="combined"
   ```

2. Map responses:
   ```
   OLD: Three separate tool results
   NEW: Single unified result with pala_metadata containing all fields
   ```

3. Add provider flexibility:
   ```
   # Can now switch providers at runtime
   model = "claude"  # or "ollama"
   result = await agent.extract_metadata({
       "text": ocr_text,
       "model": model,
       "output_type": "pala"
   })
   ```

## Fix Summary

The `metadata-extraction-agent` was not generating metadata because:

1. **Missing Ollama format parameter** - Fixed by adding `"format": "json"`
2. **Mapper expected nested structures** - Fixed by adding fallback logic to handle flat Ollama output

These fixes align `metadata-extraction-agent` with the working patterns in `metadata-agent` and `entity-agent`.
