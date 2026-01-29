# AMI Metadata Parser Tool

## Overview

The AMI Metadata Parser is a tool integrated into the Context Agent that extracts structured metadata from filenames following the AMI (Archival Management Initiative) Master naming convention. This tool helps automate the extraction of important metadata like document type, date, sender, recipient, and other archival information directly from standardized filenames.

## Purpose

This tool was created to parse filenames that follow the AMI Master naming convention used for historical document digitization projects. It extracts metadata that can be used to populate Archipelago digital repository fields automatically, reducing manual data entry and ensuring consistency.

## Naming Convention

The AMI Master naming convention follows this pattern:

```
{MASTER_ID}_{(COLLECTION_SERIES_PAGE)}_{DOCTYPE}_{MEDIUM}_{YEAR}_{FROM}_TO_{RECIPIENT}.{EXT}
```

### Example Filename

```
MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG
```

### Components Breakdown

| Component | Description | Example |
|-----------|-------------|---------|
| **Master ID** | Unique identifier with version number | `MSALTMEBA00100004.00` |
| **Collection** | Collection number | `01` |
| **Series** | Series number within collection | `02` |
| **Page** | Page number | `0071` |
| **Document Type** | 2-letter code for document type | `LT` (Letter) |
| **Medium** | Writing/creation medium | `MIX` (Mixed) |
| **Year** | 4-digit year | `1990` |
| **Sender** | Person/entity who created/sent document | `BK MODI` |
| **Recipient** | Person/entity who received document | `REVSNGOENKA` |
| **Extension** | File format | `.JPG` |

## Supported Document Types

| Code | Full Name | Description |
|------|-----------|-------------|
| `LT` | Letter | Correspondence |
| `BK` | Book | Published books |
| `NB` | Notebook | Notebooks |
| `DY` | Diary | Personal diaries |
| `NL` | Newsletter | Newsletters |
| `TR` | Transcript | Transcriptions |
| `MG` | Magazine | Magazines |
| `NP` | Newspaper | Newspapers |
| `PC` | Postcard | Postcards |
| `PH` | Photograph | Photographs |
| `AU` | Audio | Audio recordings |
| `VD` | Video | Video recordings |
| `DC` | Document | General documents |
| `PM` | Palm Leaf Manuscript | Palm leaf manuscripts |
| `PT` | Painting | Paintings |

## Supported Medium Types

| Code | Full Name |
|------|-----------|
| `MIX` | Mixed |
| `PEN` | Pen |
| `PENCIL` | Pencil |
| `TYPE` | Typewriter |
| `PRINT` | Printed |
| `HAND` | Handwritten |
| `CARVE` | Carved |
| `CHALK` | Chalk |
| `MARKER` | Marker |

## Usage

### As an MCP Tool

The tool is automatically registered with the MCP server when the Context Agent starts. It can be invoked via the MCP protocol:

```json
{
  "name": "parse_ami_filename",
  "arguments": {
    "filename": "MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG"
  }
}
```

### Direct Python Usage

```python
from tools.ami_metadata_parser import AMIMetadataParser

parser = AMIMetadataParser()
result = parser.parse("MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG")

# Access parsed metadata
print(result['master_identifier'])  # MSALTMEBA00100004.00
print(result['document_type'])      # LT
print(result['year'])               # 1990
print(result['sender'])             # BK MODI
print(result['recipient'])          # REVSNGOENKA

# Get Archipelago field mappings
archipelago_fields = parser.get_archipelago_fields(result)
print(archipelago_fields)

# Get formatted summary
summary = parser.format_metadata_summary(result)
print(summary)
```

### Response Format

The parser returns a dictionary with the following structure:

```python
{
    'filename': 'MSALTMEBA00100004.00_(01_02_0071)_LT_MIX_1990_BK MODI_TO_REVSNGOENKA.JPG',
    'parsed': True,
    'master_identifier': 'MSALTMEBA00100004.00',
    'collection': '01',
    'series': '02',
    'page_number': '0071',
    'sequence': 'Collection 01, Series 02, Page 0071',
    'document_type': 'LT',
    'document_type_full': 'Letter',
    'medium': 'MIX',
    'medium_full': 'Mixed',
    'date': '1990',
    'year': '1990',
    'sender': 'BK MODI',
    'recipient': 'REVSNGOENKA',
    'from_person': 'BK MODI',
    'to_person': 'REVSNGOENKA',
    'parsing_notes': [
        'Master ID: MSALTMEBA00100004.00',
        'Sequence: Collection 01, Series 02, Page 0071',
        'Document Type: Letter (LT)',
        'Medium: Mixed (MIX)',
        'Year: 1990',
        'Recipient: REVSNGOENKA',
        'Sender: BK MODI'
    ],
    'summary': '...',  # Formatted text summary
    'archipelago_fields': {  # Mapped fields for Archipelago
        'master_identifier': 'MSALTMEBA00100004.00',
        'page_no': '0071',
        'sequence_id': 'Collection 01, Series 02, Page 0071',
        'item_type': 'Letter',
        'medium': 'Mixed',
        'original_date': '1990',
        'letter_from': 'BK MODI',
        'letter_to': 'REVSNGOENKA',
        'subject': 'Letter from BK MODI to REVSNGOENKA',
        'creator': 'BK MODI'
    }
}
```

## Archipelago Field Mappings

The parser automatically maps parsed metadata to Archipelago digital repository fields:

| Parsed Field | Archipelago Field | Notes |
|--------------|-------------------|-------|
| `master_identifier` | `master_identifier` | Direct mapping |
| `page_number` | `page_no` | Page number only |
| `sequence` | `sequence_id` | Full sequence string |
| `document_type_full` | `item_type` | Human-readable type |
| `medium_full` | `medium` | Human-readable medium |
| `year` | `original_date` | Document date |
| `sender` | `letter_from` | For letters only |
| `recipient` | `letter_to` | For letters only |
| `sender` | `creator` | General creator field |

## Testing

Run the integration tests:

```bash
cd /mnt/sda1/mango1_home/pala-platform/packages/agents/context-agent
python3 test_ami_parser_integration.py
```

Run the standalone parser tests:

```bash
python3 tools/ami_metadata_parser.py
```

## Error Handling

The parser gracefully handles malformed filenames:

- Returns `parsed: False` for filenames that don't match the expected pattern
- Extracts as much information as possible from partially conformant filenames
- Never throws exceptions; always returns a valid response structure
- Includes `parsing_notes` array to explain what was found or any issues

## Example Use Cases

### 1. Bulk Metadata Extraction

```python
import os
from tools.ami_metadata_parser import AMIMetadataParser

parser = AMIMetadataParser()
directory = "/path/to/images"

for filename in os.listdir(directory):
    if filename.endswith(('.jpg', '.JPG', '.tif', '.TIF')):
        result = parser.parse(filename)
        if result['parsed']:
            print(f"Processed: {filename}")
            # Save archipelago_fields to database or CSV
```

### 2. Quality Control

```python
# Check if filenames follow naming convention
parser = AMIMetadataParser()
result = parser.parse(filename)

if not result['parsed']:
    print(f"WARNING: {filename} does not follow AMI naming convention")
    print(f"Notes: {result['parsing_notes']}")
```

### 3. Automated Cataloging

```python
# Extract metadata for catalog entry
result = parser.parse(filename)
if result['parsed']:
    catalog_entry = {
        'title': result.get('subject', filename),
        'creator': result.get('sender', 'Unknown'),
        'date': result.get('year', 'Undated'),
        'type': result.get('document_type_full', 'Document'),
        'identifier': result.get('master_identifier', '')
    }
```

## Source Files

- **Parser Implementation**: `packages/agents/context-agent/tools/ami_metadata_parser.py`
- **Integration**: `packages/agents/context-agent/main.py`
- **Tests**: `packages/agents/context-agent/test_ami_parser_integration.py`
- **Documentation**: `packages/agents/context-agent/AMI_METADATA_PARSER_DOCUMENTATION.md`

## Related Documentation

- AMI Master Excel specification: `/mnt/sda1/mango1_home/Downloads/AMI Master main.xlsx`
- Context Agent documentation: `packages/agents/context-agent/README.md`
- MCP Server integration: `packages/mcp-server/README.md`

## Future Enhancements

Potential improvements for future versions:

1. **Validation Rules**: Add validation for date ranges, identifier formats
2. **Alternative Formats**: Support for additional naming conventions
3. **Batch Processing**: Built-in batch processing capabilities
4. **Export Formats**: Direct export to CSV, JSON, or database
5. **OCR Integration**: Parse metadata from scanned labels on documents
6. **Machine Learning**: Auto-detect document types from filenames that don't follow convention

## Support

For issues or questions:

1. Check the parsing notes in the response for clues
2. Review the AMI Master Excel file for the latest convention
3. Run the test suite to verify installation
4. Check logs in the Context Agent output

## Version History

- **v1.0.0** (2026-01-28): Initial release
  - Basic AMI filename parsing
  - 15 document types supported
  - 9 medium types supported
  - Archipelago field mapping
  - MCP tool integration
  - Comprehensive test suite
