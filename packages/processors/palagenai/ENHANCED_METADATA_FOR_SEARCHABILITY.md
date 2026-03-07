# Enhanced Metadata Schema for Searchability

**Date:** 2026-01-28
**Purpose:** Design comprehensive metadata to make documents easily searchable across various parameters

---

## Table of Contents

1. [Search Requirements Analysis](#search-requirements-analysis)
2. [Current Searchability Assessment](#current-searchability-assessment)
3. [Enhanced Metadata Schema](#enhanced-metadata-schema)
4. [Search Index Strategy](#search-index-strategy)
5. [Implementation Roadmap](#implementation-roadmap)
6. [Search Use Cases](#search-use-cases)

---

## Search Requirements Analysis

### Primary Search Parameters (Must Have)

1. **Temporal Search**
   - Date ranges (creation, sent, received)
   - Year, decade, century
   - Date precision (exact, approximate, before, after)
   - Era/period (e.g., "1960s", "Pre-independence", "Post-1990")

2. **People Search**
   - By name (exact, fuzzy)
   - By role (sender, recipient, mentioned)
   - By affiliation/organization
   - By title/position
   - By relationship to other people

3. **Location Search**
   - Geographic search (country, state, city)
   - Institutional locations (organizations, buildings)
   - Coordinates-based proximity search
   - Place mentioned vs place of origin

4. **Content Search**
   - Full-text search
   - Keyword search
   - Subject/topic classification
   - Language
   - Summary/abstract search

5. **Document Type & Format**
   - Document type (letter, memo, etc.)
   - Physical format (handwritten, typed, printed)
   - Language(s)
   - Page count
   - Condition

### Secondary Search Parameters (Nice to Have)

6. **Historical Context**
   - Events mentioned
   - Historical significance level
   - Related historical movements
   - Cultural context

7. **Relationships**
   - Reply to / response from
   - Part of correspondence chain
   - References other documents
   - Related by topic/theme

8. **Archival Information**
   - Collection name
   - Box/folder numbers
   - Archive location
   - Digital repository URL

9. **Access & Rights**
   - Access level (public/restricted/private)
   - Copyright status
   - Usage rights
   - Sensitivity level

10. **Quality & Completeness**
    - OCR confidence
    - Metadata completeness score
    - Verification status
    - Needs review

---

## Current Searchability Assessment

### ✓ Well-Supported Search Parameters

| Parameter | Current Support | Searchability Score |
|-----------|----------------|---------------------|
| Keywords | Excellent (with relevance & frequency) | 10/10 |
| Subjects/Topics | Good (with confidence scores) | 9/10 |
| People Names | Good (with roles & biographies) | 8/10 |
| Organizations | Good (with type & location) | 8/10 |
| Locations | Good (with type & context) | 8/10 |
| Events | Good (with dates & descriptions) | 8/10 |
| Historical Context | Good (narrative text) | 7/10 |
| Significance | Good (assessment text) | 7/10 |
| Document Type | Basic (enum only) | 7/10 |
| Access Level | Basic (enum only) | 7/10 |
| Languages | Basic (array) | 7/10 |

### ⚠ Partially Supported (Need Enhancement)

| Parameter | Current Issues | Searchability Score |
|-----------|---------------|---------------------|
| Dates | Not extracted from filename/content | 2/10 |
| Sender/Recipient | Empty or incorrect in document section | 2/10 |
| Physical Attributes | Completely missing | 0/10 |
| Storage Location | Empty strings | 2/10 |
| Full Text | Not populated | 0/10 |
| Relationships | Present but not indexed | 5/10 |

### ✗ Missing Critical Features

| Parameter | Impact on Search | Priority |
|-----------|-----------------|----------|
| **Normalized Dates** | Cannot filter by date range | CRITICAL |
| **Person ID / Authority Control** | Cannot disambiguate same names | HIGH |
| **Location Coordinates** | Cannot do proximity search | HIGH |
| **Text Vectors/Embeddings** | Cannot do semantic search | HIGH |
| **Faceted Classification** | Cannot drill-down search | MEDIUM |
| **Cross-references** | Cannot find related docs | MEDIUM |

---

## Enhanced Metadata Schema

### 1. Enhanced Identification & Classification

```json
{
  "metadata": {
    "id": "uuid-v4",                          // ← ADD: Unique ID
    "collection_id": "collection-name",       // ← ADD: Collection ID
    "ami_metadata": {                         // ← NEW: AMI filename metadata
      "master_identifier": "MSALTMEBA00100004.00",
      "collection": "01",
      "series": "02",
      "page_number": "0071",
      "sequence_id": "Collection 01, Series 02, Page 0071"
    },
    "document_type": "letter",
    "document_subtype": "personal",           // ← NEW: Refinement
    "format": {                               // ← NEW: Format details
      "writing_method": "handwritten",        // handwritten|typed|printed|mixed
      "medium": "ink",                        // ink|pencil|typewriter
      "quality": "good"                       // excellent|good|fair|poor
    },
    "classification": {                       // ← NEW: Multi-level classification
      "primary_subject": "Vipassana_meditation",
      "secondary_subjects": [
        "Retreat_organization",
        "Family_correspondence",
        "Teacher_student_relationship"
      ],
      "topics": [
        "Meditation courses",
        "Dhamma practice",
        "Administrative challenges"
      ],
      "themes": [
        "Spiritual development",
        "Family duty",
        "Organizational growth"
      ],
      "genre": "personal_narrative"
    },
    "temporal_classification": {             // ← NEW: Era/period
      "decade": "1960s",
      "era": "Early Vipassana Movement",
      "historical_period": "Post-independence India"
    }
  }
}
```

### 2. Enhanced Date Handling

```json
{
  "document": {
    "date": {
      "creation_date": "1969-09-29",          // ← FIX: Extract from filename
      "sent_date": "1969-09-29",              // ← FIX: Same as creation
      "received_date": null,                  // Unknown
      "date_precision": "exact",              // exact|approximate|inferred|unknown
      "date_source": "document_header",       // document_header|content|filename|inferred
      "date_display": "29th September 1969",  // Human-readable format
      "temporal_markers": {                   // ← NEW: Additional temporal info
        "year": 1969,
        "month": 9,
        "day": 29,
        "decade": "1960s",
        "quarter": "Q3",
        "season": "monsoon",                  // For South Asian context
        "day_of_week": "Monday",
        "is_approximate": false
      },
      "mentioned_dates": [                    // ← NEW: Other dates in document
        {
          "date": "1969-08-14",
          "context": "meditation retreat held in Mumbai from August 14 to 24",
          "type": "event_start"
        },
        {
          "date": "1969-08-12",
          "context": "on 12th August, I reached Hyderabad",
          "type": "travel_date"
        }
      ]
    },
    "reference_number": "extract_if_present",  // From letterhead or content
    "languages": ["English"],                   // ← FIX: Should be "English" not "en"
    "script": ["Latin"],                        // ← NEW: Writing system
    "language_details": {                       // ← NEW: Language metadata
      "primary": "English",
      "secondary": [],
      "mixed_language": false,
      "transliteration_present": true,          // "Vipassanā", "Dhamma"
      "regional_terms": ["kothi", "bhaiya"]     // Local vocabulary
    }
  }
}
```

### 3. Enhanced Correspondence with Authority Control

```json
{
  "document": {
    "correspondence": {                          // ← FIX: Remove duplicate nesting
      "sender": {
        "name": "Satyanarayan Goenka",         // ← FIX: Extract from signature
        "name_variants": [                      // ← NEW: Alternative names
          "S.N. Goenka",
          "Goenkaji",
          "Satya Narayan Goenka"
        ],
        "authority_id": "person-sng-001",       // ← NEW: Unique person ID
        "title": "",
        "affiliation": "Vipassana Teacher",     // ← FIX: Should populate
        "role_in_correspondence": "author",
        "location": {                           // ← FIX: From content
          "city": "New Delhi",
          "state": "Delhi",
          "country": "India",
          "location_type": "origin",
          "coordinates": {
            "latitude": 28.6139,
            "longitude": 77.2090
          }
        },
        "contact_info": {
          "address": null,
          "telephone": null,
          "fax": null,
          "email": null
        },
        "biography": "S.N. Goenka was a teacher of Vipassanā meditation...",
        "relationships": [                      // ← NEW: Social graph
          {
            "person_id": "person-babu-001",
            "relationship": "correspondent",
            "context": "Regular letter recipient"
          }
        ]
      },
      "recipient": {
        "name": "Babu bhaiya",                 // ← FIX: From salutation
        "name_variants": [],
        "authority_id": "person-babu-001",      // ← NEW
        "title": "",
        "affiliation": "",
        "role_in_correspondence": "recipient",
        "location": {
          "city": null,                         // Not mentioned
          "state": null,
          "country": null,
          "location_type": "destination"
        },
        "biography": "Close family member or relative...",
        "relationships": [
          {
            "person_id": "person-sng-001",
            "relationship": "correspondent",
            "context": "Regular letter sender"
          }
        ]
      },
      "cc": [],
      "correspondence_metadata": {              // ← NEW: Correspondence context
        "correspondence_type": "personal",      // personal|official|formal|informal
        "relationship_type": "family",          // family|professional|academic|administrative
        "tone": "respectful",                   // formal|informal|respectful|urgent
        "purpose": "report",                    // report|request|response|notification
        "response_to": null,                    // ID of letter this responds to
        "elicited_response": null              // ID of response to this letter
      }
    }
  }
}
```

### 4. Enhanced Content with Search Features

```json
{
  "content": {
    "full_text": "Complete OCR text here...",   // ← FIX: Must populate
    "full_text_clean": "Cleaned version...",   // ← NEW: Pre-processed for search
    "summary": "Brief summary...",
    "summary_lengths": {                        // ← NEW: Multiple summary versions
      "short": "One-line summary (< 150 chars)",
      "medium": "Paragraph summary (< 500 chars)",
      "long": "Detailed summary (< 2000 chars)"
    },
    "salutation": "Dear Babu bhaiya,",
    "body": ["paragraph1", "paragraph2", ...],
    "closing": "Your younger brother,",         // ← FIX: Must extract
    "signature": "Satyanarayan",
    "attachments": [],
    "annotations": [],
    "content_features": {                       // ← NEW: Content characteristics
      "word_count": 2847,
      "paragraph_count": 15,
      "sentence_count": 87,
      "has_quotes": false,
      "has_lists": false,
      "has_tables": false,
      "language_style": "narrative",            // narrative|formal|informal|technical
      "readability_score": 12.5,                // Flesch-Kincaid grade level
      "sentiment": {                            // ← NEW: Sentiment analysis
        "overall": "positive",
        "confidence": 0.75,
        "tone_markers": [
          "respectful",
          "detailed",
          "reflective"
        ]
      }
    },
    "named_entities": {                         // ← NEW: NER extracted entities
      "persons": ["Vijay Adukia", "Radhe", "Vimala", ...],
      "places": ["Mumbai", "Madras", "Hyderabad", "Tadepalli Gudum", ...],
      "organizations": ["Vipassana Research Institute", ...],
      "dates": ["August 14", "August 24", "12th August", ...],
      "numbers": ["15-16", "500", "10-day", ...]
    },
    "text_embeddings": {                        // ← NEW: For semantic search
      "model": "sentence-transformers/all-mpnet-base-v2",
      "version": "2.2.0",
      "embedding_id": "embedding-uuid",
      "dimensions": 768,
      "stored_in": "vector_db"                  // Reference to vector store
    }
  }
}
```

### 5. Enhanced Analysis with Structured Data

```json
{
  "analysis": {
    "keywords": [
      {
        "keyword": "Vipassanā",
        "normalized": "vipassana",              // ← NEW: For case-insensitive search
        "relevance": 0.8,
        "frequency": 6,
        "category": "practice",                 // ← NEW: Keyword category
        "first_mention": "paragraph 1",
        "context": "meditation technique"
      },
      // ... more keywords
    ],
    "subjects": [
      {
        "subject": "personal_matters",
        "confidence": 0.8,
        "subject_hierarchy": [                  // ← NEW: Hierarchical classification
          "correspondence",
          "personal_correspondence",
          "family_letters"
        ],
        "library_classification": {             // ← NEW: Standard classifications
          "lcc": "BQ4570",                      // Library of Congress
          "ddc": "294.3",                       // Dewey Decimal
          "custom": "VIP-CORR-FAMILY"           // Custom taxonomy
        }
      }
    ],
    "events": [
      {
        "name": "Third Vipassana Meditation Retreat in Mumbai",
        "date": "1969-08-14",
        "date_end": "1969-08-24",               // ← NEW: Event duration
        "location": "Mumbai, India",
        "location_coordinates": {               // ← NEW: Geographic data
          "latitude": 19.0760,
          "longitude": 72.8777
        },
        "description": "...",
        "event_type": "meditation_course",      // ← NEW: Event classification
        "participants_count": "15-16",          // ← NEW: Attendee info
        "significance": "high",
        "related_events": [                     // ← NEW: Event relationships
          "event-mumbai-2",
          "event-madras-1"
        ]
      }
    ],
    "locations": [
      {
        "name": "Mumbai",
        "name_variants": ["Bombay"],            // ← NEW: Historical names
        "type": "city",
        "coordinates": {
          "latitude": 19.0760,
          "longitude": 72.8777
        },
        "country": "India",
        "state": "Maharashtra",
        "role": "event_location",               // ← NEW: Why mentioned
        "mention_count": 12,                    // ← NEW: Frequency
        "importance": "primary",                // primary|secondary|incidental
        "context": "Location of meditation retreat",
        "related_locations": [                  // ← NEW: Location relationships
          "loc-madras",
          "loc-hyderabad"
        ]
      }
    ],
    "people": [
      {
        "name": "Babu bhaiya",
        "authority_id": "person-babu-001",      // ← NEW: Links to authority record
        "role": "recipient",
        "affiliation": null,
        "biography": "...",
        "mention_count": 1,                     // ← NEW: How often mentioned
        "importance": "primary",                // primary|secondary|incidental
        "relationships": [                      // ← NEW: Social graph
          {
            "person_id": "person-sng-001",
            "relationship_type": "family",
            "relationship_description": "Addressee of letter"
          }
        ]
      }
    ],
    "organizations": [
      {
        "name": "Vipassana Research Institute",
        "name_variants": ["VRI"],               // ← NEW: Abbreviations
        "authority_id": "org-vri-001",          // ← NEW: Unique org ID
        "type": "religious_organization",
        "location": "India",
        "description": "...",
        "mention_count": 1,
        "importance": "secondary",
        "related_organizations": []
      }
    ],
    "historical_context": "Detailed narrative...",
    "historical_context_structured": {          // ← NEW: Structured context
      "time_period": {
        "era": "Early Vipassana Movement",
        "decade": "1960s",
        "historical_events": [
          "Goenka's early teaching period in India"
        ]
      },
      "geographic_context": {
        "region": "Western India",
        "political_context": "Post-independence India"
      },
      "cultural_context": {
        "religious_movement": "Vipassana meditation revival",
        "social_context": "Spiritual seeking in modern India"
      }
    },
    "significance": "Detailed assessment...",
    "significance_structured": {                // ← NEW: Structured significance
      "significance_level": "medium",           // low|medium|high|exceptional
      "significance_types": [                   // ← NEW: Multi-dimensional
        "biographical",                         // About person's life
        "organizational",                       // About institution
        "historical",                           // Historical importance
        "cultural"                              // Cultural significance
      ],
      "research_value": "high",
      "public_interest": "medium",
      "uniqueness": "medium"                    // How unique/rare this document is
    },
    "relationships": [
      {
        "document_id": "doc-uuid-2",
        "relationship_type": "response_to",
        "description": "...",
        "confidence": 0.8,                      // ← NEW: Confidence in relationship
        "relationship_strength": "strong"       // ← NEW: Strength indicator
      }
    ],
    "cross_references": {                       // ← NEW: Internal references
      "mentioned_documents": [],
      "mentioned_letters": [],
      "mentioned_courses": [
        "Mumbai Course Aug 1969",
        "Madras Course July 1969"
      ]
    }
  }
}
```

### 6. NEW: Physical & Digitization Metadata

```json
{
  "physical": {                                 // ← NEW: Physical characteristics
    "original_exists": true,
    "physical_location": {
      "archive": "Vipassana Research Institute",
      "collection": "S.N. Goenka Correspondence",
      "box": "Box 12",
      "folder": "Folder 3",
      "item_number": "043"
    },
    "physical_attributes": {
      "size": "A4 (210 x 297 mm)",
      "paper_type": "Standard writing paper",
      "paper_quality": "good",
      "paper_color": "white",
      "writing_instrument": "ink pen",
      "ink_color": "blue",
      "condition": "good",
      "condition_notes": "",
      "letterhead": "None",
      "watermark": "None",
      "pages": 7,
      "sides": "single-sided",
      "binding": "unbound",
      "damage": [],
      "conservation_needed": false
    }
  },
  "digitization": {
    "digitization_info": {
      "date": "2024-03-15",                     // ← FIX: Actual date
      "operator": "Digital Archive Team",       // ← FIX: Actual operator
      "equipment": "Epson Perfection V850",     // ← FIX: Actual equipment
      "resolution": "600 DPI",                  // ← FIX: Actual resolution
      "color_mode": "24-bit color",
      "file_format": "JPEG",
      "file_size": "2.4 MB",
      "file_dimensions": "4960 x 7016 pixels"
    },
    "ocr_metadata": {                           // ← NEW: OCR quality metrics
      "ocr_engine": "Tesseract 5.0",
      "ocr_language": "eng",
      "ocr_confidence": 0.94,
      "ocr_date": "2024-03-16",
      "manual_corrections": false,
      "verification_status": "unverified"       // unverified|in_review|verified
    },
    "versions": [                               // ← NEW: Version tracking
      {
        "version": "raw_scan",
        "file_path": "/archives/raw/doc_001.tif",
        "format": "TIFF",
        "size": "45 MB"
      },
      {
        "version": "processed",
        "file_path": "/archives/processed/doc_001.jpg",
        "format": "JPEG",
        "size": "2.4 MB"
      },
      {
        "version": "ocr_text",
        "file_path": "/archives/text/doc_001.txt",
        "format": "TXT",
        "size": "12 KB"
      }
    ]
  }
}
```

### 7. NEW: Searchability & Discovery Metadata

```json
{
  "searchability": {                            // ← NEW: Search optimization
    "completeness_score": 0.85,                 // 0-1 score of metadata completeness
    "quality_score": 0.92,                      // Overall metadata quality
    "verification_status": "auto",              // auto|review_needed|verified
    "last_indexed": "2024-03-16T10:30:00Z",
    "index_version": "v2.1",
    "search_boost": 1.0,                        // For relevance ranking
    "facets": {                                 // ← NEW: Pre-computed facets
      "decade": "1960s",
      "document_type": "letter",
      "language": "English",
      "collection": "S.N. Goenka Correspondence",
      "has_images": false,
      "has_attachments": false,
      "person_count": 8,
      "location_count": 5,
      "organization_count": 1
    },
    "tags": [                                   // ← NEW: User-friendly tags
      "Vipassana",
      "Meditation Retreats",
      "1969",
      "S.N. Goenka",
      "Mumbai",
      "Personal Correspondence",
      "Historical Letters"
    ],
    "auto_tags": [                              // ← NEW: AI-generated tags
      "Organizational Challenges",
      "Family Matters",
      "Spiritual Practice",
      "Early Movement History"
    ]
  }
}
```

### 8. NEW: Access & Rights Management

```json
{
  "access": {
    "access_level": "public",                   // public|restricted|private
    "access_restrictions": {
      "restriction_type": null,                 // ip_range|user_group|location
      "restriction_details": "",
      "expiration_date": null
    },
    "rights": {                                 // ← NEW: Detailed rights info
      "copyright_status": "in_copyright",       // in_copyright|public_domain|unknown
      "copyright_holder": "Vipassana Research Institute",
      "license": "All Rights Reserved",         // Or CC license
      "usage_rights": {
        "can_view": true,
        "can_download": true,
        "can_print": true,
        "can_share": false,
        "can_modify": false,
        "attribution_required": true
      },
      "sensitive_content": {                    // ← NEW: Content warnings
        "has_personal_info": true,
        "has_financial_info": false,
        "has_medical_info": false,
        "has_sensitive_topics": false,
        "privacy_level": "medium"
      }
    },
    "citation": {                               // ← NEW: How to cite
      "recommended_citation": "Goenka, S.N. (1969). Letter to Babu bhaiya...",
      "permalink": "https://archive.vri.org/documents/doc-uuid",
      "doi": null
    }
  }
}
```

### 9. NEW: Audit & Provenance

```json
{
  "provenance": {                               // ← NEW: Document history
    "original_source": "S.N. Goenka Personal Papers",
    "acquisition_date": "2020-01-15",
    "acquisition_method": "donation",
    "donor": "Goenka Family Trust",
    "chain_of_custody": [
      {
        "date": "1969-09-29",
        "event": "created",
        "actor": "S.N. Goenka"
      },
      {
        "date": "1969-09-29",
        "event": "sent",
        "actor": "S.N. Goenka"
      },
      {
        "date": "2020-01-15",
        "event": "acquired",
        "actor": "VRI Archives"
      },
      {
        "date": "2024-03-15",
        "event": "digitized",
        "actor": "Digital Archive Team"
      }
    ],
    "processing_history": [
      {
        "date": "2024-03-16",
        "process": "OCR",
        "operator": "Automated System",
        "version": "v1.0"
      },
      {
        "date": "2024-03-16",
        "process": "Enrichment",
        "operator": "MCP Server",
        "version": "v2.0"
      }
    ]
  },
  "metadata_provenance": {                      // ← NEW: Metadata history
    "created_by": "Automated Enrichment Pipeline",
    "created_at": "2024-03-16T10:30:00Z",
    "modified_by": [],
    "modified_at": [],
    "metadata_version": "2.0",
    "confidence_scores": {
      "overall": 0.87,
      "dates": 0.95,
      "people": 0.82,
      "locations": 0.90,
      "content": 0.88
    }
  }
}
```

---

## Search Index Strategy

### MongoDB Indexes (Current Database)

```javascript
// Primary indexes for fast lookups
db.enriched_documents.createIndex({ "metadata.id": 1 }, { unique: true })
db.enriched_documents.createIndex({ "metadata.collection_id": 1 })

// Date range searches
db.enriched_documents.createIndex({ "document.date.sent_date": 1 })
db.enriched_documents.createIndex({ "document.date.creation_date": 1 })
db.enriched_documents.createIndex({ "document.date.temporal_markers.year": 1 })
db.enriched_documents.createIndex({ "document.date.temporal_markers.decade": 1 })

// People searches
db.enriched_documents.createIndex({ "document.correspondence.sender.name": "text" })
db.enriched_documents.createIndex({ "document.correspondence.recipient.name": "text" })
db.enriched_documents.createIndex({ "document.correspondence.sender.authority_id": 1 })
db.enriched_documents.createIndex({ "analysis.people.name": "text" })
db.enriched_documents.createIndex({ "analysis.people.authority_id": 1 })

// Location searches
db.enriched_documents.createIndex({
  "document.correspondence.sender.location.coordinates": "2dsphere"
}) // For proximity searches
db.enriched_documents.createIndex({ "analysis.locations.name": "text" })
db.enriched_documents.createIndex({
  "analysis.locations.coordinates": "2dsphere"
})

// Content searches
db.enriched_documents.createIndex({
  "content.full_text": "text",
  "content.summary": "text",
  "analysis.keywords.keyword": "text"
}, {
  name: "full_text_search",
  weights: {
    "content.full_text": 10,
    "content.summary": 5,
    "analysis.keywords.keyword": 3
  }
})

// Classification searches
db.enriched_documents.createIndex({ "metadata.classification.primary_subject": 1 })
db.enriched_documents.createIndex({ "metadata.classification.secondary_subjects": 1 })
db.enriched_documents.createIndex({ "analysis.subjects.subject": 1 })

// Organization searches
db.enriched_documents.createIndex({ "analysis.organizations.name": "text" })
db.enriched_documents.createIndex({ "analysis.organizations.authority_id": 1 })

// Event searches
db.enriched_documents.createIndex({ "analysis.events.name": "text" })
db.enriched_documents.createIndex({ "analysis.events.date": 1 })

// Archival searches
db.enriched_documents.createIndex({ "physical.physical_location.archive": 1 })
db.enriched_documents.createIndex({ "physical.physical_location.collection": 1 })
db.enriched_documents.createIndex({ "physical.physical_location.box": 1 })

// Faceted search support
db.enriched_documents.createIndex({ "searchability.facets.decade": 1 })
db.enriched_documents.createIndex({ "searchability.facets.document_type": 1 })
db.enriched_documents.createIndex({ "searchability.facets.language": 1 })
db.enriched_documents.createIndex({ "searchability.facets.collection": 1 })

// Tags for quick filtering
db.enriched_documents.createIndex({ "searchability.tags": 1 })
db.enriched_documents.createIndex({ "searchability.auto_tags": 1 })

// Quality filtering
db.enriched_documents.createIndex({ "searchability.completeness_score": 1 })
db.enriched_documents.createIndex({ "searchability.verification_status": 1 })

// Compound indexes for common queries
db.enriched_documents.createIndex({
  "document.date.temporal_markers.year": 1,
  "metadata.document_type": 1
})
db.enriched_documents.createIndex({
  "analysis.people.authority_id": 1,
  "document.date.temporal_markers.year": 1
})
```

### Elasticsearch Integration (Recommended)

For better full-text search and faceted navigation:

```json
{
  "mappings": {
    "properties": {
      "metadata": {
        "properties": {
          "id": { "type": "keyword" },
          "collection_id": { "type": "keyword" },
          "document_type": { "type": "keyword" },
          "classification": {
            "properties": {
              "primary_subject": { "type": "keyword" },
              "secondary_subjects": { "type": "keyword" },
              "topics": {
                "type": "text",
                "fields": {
                  "keyword": { "type": "keyword" }
                }
              }
            }
          }
        }
      },
      "document": {
        "properties": {
          "date": {
            "properties": {
              "creation_date": { "type": "date" },
              "sent_date": { "type": "date" },
              "temporal_markers": {
                "properties": {
                  "year": { "type": "integer" },
                  "decade": { "type": "keyword" }
                }
              }
            }
          },
          "correspondence": {
            "properties": {
              "sender": {
                "properties": {
                  "name": {
                    "type": "text",
                    "fields": {
                      "keyword": { "type": "keyword" },
                      "suggest": { "type": "completion" }
                    }
                  },
                  "authority_id": { "type": "keyword" },
                  "location": {
                    "properties": {
                      "coordinates": { "type": "geo_point" }
                    }
                  }
                }
              },
              "recipient": {
                "properties": {
                  "name": {
                    "type": "text",
                    "fields": {
                      "keyword": { "type": "keyword" },
                      "suggest": { "type": "completion" }
                    }
                  },
                  "authority_id": { "type": "keyword" }
                }
              }
            }
          },
          "languages": { "type": "keyword" }
        }
      },
      "content": {
        "properties": {
          "full_text": {
            "type": "text",
            "analyzer": "english"
          },
          "full_text_clean": {
            "type": "text",
            "analyzer": "standard"
          },
          "summary": { "type": "text" },
          "text_embeddings": {
            "properties": {
              "embedding_id": { "type": "keyword" }
            }
          }
        }
      },
      "analysis": {
        "properties": {
          "keywords": {
            "type": "nested",
            "properties": {
              "keyword": {
                "type": "text",
                "fields": {
                  "keyword": { "type": "keyword" }
                }
              },
              "normalized": { "type": "keyword" },
              "relevance": { "type": "float" },
              "frequency": { "type": "integer" }
            }
          },
          "people": {
            "type": "nested",
            "properties": {
              "name": { "type": "text" },
              "authority_id": { "type": "keyword" },
              "role": { "type": "keyword" }
            }
          },
          "locations": {
            "type": "nested",
            "properties": {
              "name": { "type": "text" },
              "coordinates": { "type": "geo_point" },
              "type": { "type": "keyword" }
            }
          },
          "events": {
            "type": "nested",
            "properties": {
              "name": { "type": "text" },
              "date": { "type": "date" },
              "location": { "type": "text" }
            }
          },
          "organizations": {
            "type": "nested",
            "properties": {
              "name": { "type": "text" },
              "authority_id": { "type": "keyword" }
            }
          }
        }
      },
      "searchability": {
        "properties": {
          "completeness_score": { "type": "float" },
          "quality_score": { "type": "float" },
          "verification_status": { "type": "keyword" },
          "facets": {
            "properties": {
              "decade": { "type": "keyword" },
              "document_type": { "type": "keyword" },
              "language": { "type": "keyword" },
              "collection": { "type": "keyword" }
            }
          },
          "tags": { "type": "keyword" },
          "auto_tags": { "type": "keyword" }
        }
      }
    }
  }
}
```

### Vector Database (for Semantic Search)

Use Pinecone, Weaviate, or Milvus for similarity search:

```python
# Store text embeddings for semantic search
{
  "id": "doc-uuid",
  "values": [0.12, -0.45, 0.78, ...],  # 768-dimensional vector
  "metadata": {
    "document_id": "doc-uuid",
    "title": "Letter from S.N. Goenka to Babu bhaiya",
    "date": "1969-09-29",
    "document_type": "letter",
    "collection": "S.N. Goenka Correspondence"
  }
}
```

---

## Search Use Cases

### 1. Date Range Search

**Query:** "Find all letters from 1969"

```json
{
  "query": {
    "range": {
      "document.date.temporal_markers.year": {
        "gte": 1969,
        "lte": 1969
      }
    }
  }
}
```

### 2. Person Search

**Query:** "Find all letters sent by S.N. Goenka"

```json
{
  "query": {
    "bool": {
      "should": [
        { "match": { "document.correspondence.sender.name": "S.N. Goenka" }},
        { "term": { "document.correspondence.sender.authority_id": "person-sng-001" }},
        { "match": { "document.correspondence.sender.name_variants": "Satyanarayan Goenka" }}
      ]
    }
  }
}
```

### 3. Location-Based Search

**Query:** "Find all documents mentioning events within 50km of Mumbai"

```json
{
  "query": {
    "bool": {
      "must": [
        {
          "geo_distance": {
            "distance": "50km",
            "analysis.locations.coordinates": {
              "lat": 19.0760,
              "lon": 72.8777
            }
          }
        }
      ]
    }
  }
}
```

### 4. Topic/Subject Search

**Query:** "Find all documents about meditation retreats"

```json
{
  "query": {
    "bool": {
      "should": [
        { "match": { "metadata.classification.topics": "meditation retreats" }},
        { "match": { "analysis.keywords.keyword": "meditation retreat" }},
        { "match": { "content.full_text": "meditation retreat" }}
      ]
    }
  }
}
```

### 5. Faceted Search

**Query:** "Browse 1960s letters about Vipassana from Mumbai collection"

```json
{
  "query": {
    "bool": {
      "must": [
        { "term": { "searchability.facets.decade": "1960s" }},
        { "match": { "searchability.tags": "Vipassana" }},
        { "match": { "searchability.facets.collection": "Mumbai" }}
      ]
    }
  },
  "aggs": {
    "by_year": {
      "terms": { "field": "document.date.temporal_markers.year" }
    },
    "by_sender": {
      "terms": { "field": "document.correspondence.sender.name.keyword" }
    }
  }
}
```

### 6. Semantic Search

**Query:** "Find documents similar to this one about organizing meditation courses"

```python
# Query vector database with document embedding
results = vector_db.query(
    vector=document_embedding,
    top_k=10,
    filter={"document_type": "letter"}
)
```

### 7. Complex Multi-Criteria Search

**Query:** "Find letters sent by S.N. Goenka in the 1960s mentioning Mumbai or Hyderabad, about meditation courses, with high significance"

```json
{
  "query": {
    "bool": {
      "must": [
        { "term": { "document.correspondence.sender.authority_id": "person-sng-001" }},
        { "range": { "document.date.temporal_markers.year": { "gte": 1960, "lte": 1969 }}},
        { "bool": {
          "should": [
            { "match": { "analysis.locations.name": "Mumbai" }},
            { "match": { "analysis.locations.name": "Hyderabad" }}
          ]
        }},
        { "match": { "metadata.classification.topics": "meditation courses" }},
        { "range": { "analysis.significance_structured.significance_level": { "gte": "medium" }}}
      ]
    }
  },
  "sort": [
    { "document.date.sent_date": "desc" },
    { "searchability.quality_score": "desc" }
  ]
}
```

---

## Implementation Roadmap

### Phase 1: Critical Fixes (Week 1-2)

1. **Generate Unique IDs**
   - Implement UUID generation for metadata.id
   - Create collection_id from directory structure or user input

2. **Fix Date Extraction**
   - Integrate AMI filename parser for date extraction
   - Parse dates from document headers
   - Extract mentioned dates from content

3. **Fix Correspondence Data**
   - Remove duplicate nesting
   - Map sender from signature field
   - Map recipient from salutation field
   - Populate from people analysis

4. **Populate Full Text**
   - Copy ocr_text to content.full_text
   - Create cleaned version for better search

5. **Add Basic Facets**
   - Generate decade, document_type, language facets
   - Add to searchability section

### Phase 2: Enhanced Metadata (Week 3-4)

6. **Authority Control**
   - Create person authority records
   - Assign authority IDs to people
   - Link mentions to authority records

7. **Geographic Enhancement**
   - Add coordinates to locations
   - Implement location type classification
   - Add location relationships

8. **Temporal Enhancement**
   - Add temporal_markers (year, decade, etc.)
   - Extract and index mentioned dates
   - Add date precision indicators

9. **Classification Enhancement**
   - Multi-level subject classification
   - Add topics and themes
   - Library classification codes

10. **Physical Attributes**
    - Extract page count from OCR
    - Add letterhead detection
    - Populate size and format info

### Phase 3: Searchability Features (Week 5-6)

11. **Text Embeddings**
    - Generate embeddings for semantic search
    - Set up vector database
    - Implement similarity search API

12. **Named Entity Recognition**
    - Extract entities from full text
    - Add to content.named_entities
    - Create entity-based indexes

13. **Search Optimization**
    - Add normalized fields for case-insensitive search
    - Implement search boost scoring
    - Add auto-tagging

14. **Faceted Search**
    - Pre-compute common facets
    - Implement facet API
    - Add drill-down support

### Phase 4: Advanced Features (Week 7-8)

15. **Relationships**
    - Implement document relationship detection
    - Create correspondence chains
    - Add cross-reference extraction

16. **Provenance Tracking**
    - Add chain of custody
    - Track processing history
    - Version tracking

17. **Quality Metrics**
    - Calculate completeness scores
    - Add quality indicators
    - Implement verification workflow

18. **Search API**
    - RESTful search endpoint
    - GraphQL interface
    - Advanced query builder

---

## Summary

This enhanced metadata schema provides:

✓ **30+ search dimensions** (vs current ~10)
✓ **Structured data** for precise filtering
✓ **Geographic search** with coordinates
✓ **Temporal search** with multiple precision levels
✓ **Authority control** for people and organizations
✓ **Semantic search** via embeddings
✓ **Faceted navigation** for browsing
✓ **Relationship graphs** for connected documents
✓ **Quality metrics** for filtering results
✓ **Multi-language** and script support

**Estimated Improvement:** From 30% schema compliance to 95%+, with 10x improvement in searchability and discoverability.
