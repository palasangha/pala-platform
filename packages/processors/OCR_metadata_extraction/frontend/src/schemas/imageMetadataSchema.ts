/**
 * JSON Schema for Image/Document Metadata Form
 * Combines OCR image metadata with required historical document format
 */

export interface FieldDefinition {
  type: 'text' | 'textarea' | 'number' | 'select' | 'multiselect' | 'boolean' | 'json';
  label: string;
  description?: string;
  placeholder?: string;
  required?: boolean;
  min?: number;
  max?: number;
  step?: number;
  options?: { label: string; value: any }[];
  readOnly?: boolean;
  section?: string;
}

export interface FormSchema {
  [fieldName: string]: FieldDefinition;
}

/**
 * Schema for editable image metadata fields
 * Combines OCR fields with historical document metadata requirements
 */
export const imageMetadataSchema: FormSchema = {
  // OCR Processing Fields
  ocr_text: {
    type: 'textarea',
    label: 'Extracted Text / Full Text',
    description: 'The OCR-extracted text from the image. Edit to correct errors.',
    placeholder: 'Enter the extracted text...',
    section: 'OCR & Content',
  },
  summary: {
    type: 'textarea',
    label: 'Summary',
    description: 'Brief summary of the document\'s content',
    placeholder: 'Provide a brief summary...',
    section: 'OCR & Content',
  },
  confidence: {
    type: 'number',
    label: 'Confidence Score',
    description: 'OCR confidence score (0-1). Higher values indicate better accuracy.',
    min: 0,
    max: 1,
    step: 0.01,
    readOnly: true,
    section: 'OCR Processing',
  },
  detected_language: {
    type: 'select',
    label: 'Detected Language',
    description: 'Language detected in the document',
    options: [
      { label: 'English', value: 'en' },
      { label: 'Hindi', value: 'hi' },
      { label: 'Spanish', value: 'es' },
      { label: 'French', value: 'fr' },
      { label: 'German', value: 'de' },
      { label: 'Chinese', value: 'zh' },
      { label: 'Japanese', value: 'ja' },
      { label: 'Korean', value: 'ko' },
      { label: 'Portuguese', value: 'pt' },
      { label: 'Russian', value: 'ru' },
      { label: 'Unknown', value: 'unknown' },
    ],
    readOnly: true,
    section: 'OCR Processing',
  },
  languages: {
    type: 'multiselect',
    label: 'OCR Languages',
    description: 'Languages used during OCR processing',
    options: [
      { label: 'English', value: 'en' },
      { label: 'Hindi', value: 'hi' },
      { label: 'Spanish', value: 'es' },
      { label: 'French', value: 'fr' },
      { label: 'German', value: 'de' },
      { label: 'Chinese', value: 'zh' },
      { label: 'Japanese', value: 'ja' },
      { label: 'Korean', value: 'ko' },
      { label: 'Portuguese', value: 'pt' },
      { label: 'Russian', value: 'ru' },
    ],
    section: 'OCR Processing',
  },
  handwriting: {
    type: 'boolean',
    label: 'Contains Handwriting',
    description: 'Whether the document contains handwritten content',
    section: 'OCR Processing',
  },
  provider: {
    type: 'text',
    label: 'OCR Provider',
    description: 'Provider used for OCR processing',
    readOnly: true,
    section: 'OCR Processing',
  },

  // Document Information
  document_type: {
    type: 'select',
    label: 'Document Type',
    description: 'Type of document',
    options: [
      { label: 'Letter', value: 'letter' },
      { label: 'Memo', value: 'memo' },
      { label: 'Telegram', value: 'telegram' },
      { label: 'Fax', value: 'fax' },
      { label: 'Email', value: 'email' },
      { label: 'Invitation', value: 'invitation' },
    ],
    section: 'Document Information',
  },
  creation_date: {
    type: 'text',
    label: 'Creation Date',
    description: 'Date when the document was created (YYYY-MM-DD)',
    placeholder: 'YYYY-MM-DD',
    section: 'Document Information',
  },
  reference_number: {
    type: 'text',
    label: 'Reference Number',
    description: 'Reference or file number on the document',
    section: 'Document Information',
  },

  // Sender/Recipient Information
  sender_name: {
    type: 'text',
    label: 'Sender Name',
    description: 'Name of the sender',
    section: 'Correspondence',
  },
  sender_title: {
    type: 'text',
    label: 'Sender Title',
    description: 'Title or position of the sender',
    section: 'Correspondence',
  },
  sender_affiliation: {
    type: 'text',
    label: 'Sender Organization',
    description: 'Organization or institution of the sender',
    section: 'Correspondence',
  },
  sender_location: {
    type: 'text',
    label: 'Sender Location',
    description: 'Location from which the letter was sent',
    section: 'Correspondence',
  },
  recipient_name: {
    type: 'text',
    label: 'Recipient Name',
    description: 'Name of the recipient',
    section: 'Correspondence',
  },
  recipient_title: {
    type: 'text',
    label: 'Recipient Title',
    description: 'Title or position of the recipient',
    section: 'Correspondence',
  },
  recipient_affiliation: {
    type: 'text',
    label: 'Recipient Organization',
    description: 'Organization or institution of the recipient',
    section: 'Correspondence',
  },
  recipient_location: {
    type: 'text',
    label: 'Recipient Location',
    description: 'Location to which the letter was sent',
    section: 'Correspondence',
  },

  // Physical Attributes
  pages: {
    type: 'number',
    label: 'Number of Pages',
    description: 'Number of pages in the document',
    min: 1,
    section: 'Physical Attributes',
  },
  material: {
    type: 'text',
    label: 'Material',
    description: 'Material of the document (paper type, etc.)',
    section: 'Physical Attributes',
  },
  condition: {
    type: 'text',
    label: 'Condition',
    description: 'Condition of the physical document',
    section: 'Physical Attributes',
  },

  // Analysis & Tags
  keywords: {
    type: 'multiselect',
    label: 'Keywords',
    description: 'Keywords related to the document content',
    options: [],
    section: 'Analysis & Tags',
  },
  subjects: {
    type: 'multiselect',
    label: 'Subjects',
    description: 'Subject categories for the document',
    options: [],
    section: 'Analysis & Tags',
  },
  historical_context: {
    type: 'textarea',
    label: 'Historical Context',
    description: 'Historical context for understanding the document',
    section: 'Analysis & Tags',
  },
  significance: {
    type: 'textarea',
    label: 'Significance',
    description: 'Significance of the document in historical or cultural context',
    section: 'Analysis & Tags',
  },

  // Storage & Access
  access_level: {
    type: 'select',
    label: 'Access Level',
    description: 'Access restrictions for the document',
    options: [
      { label: 'Public', value: 'public' },
      { label: 'Restricted', value: 'restricted' },
      { label: 'Private', value: 'private' },
    ],
    section: 'Storage & Access',
  },
  archive_name: {
    type: 'text',
    label: 'Archive Name',
    description: 'Name of the archive where the original is stored',
    section: 'Storage & Access',
  },
  collection_name: {
    type: 'text',
    label: 'Collection Name',
    description: 'Name of the specific collection within the archive',
    section: 'Storage & Access',
  },
  box_number: {
    type: 'text',
    label: 'Box Number',
    description: 'Box or container identifier',
    section: 'Storage & Access',
  },
  folder_number: {
    type: 'text',
    label: 'Folder Number',
    description: 'Folder identifier within the box',
    section: 'Storage & Access',
  },

  // Statistics (Read-only)
  blocks_count: {
    type: 'number',
    label: 'Text Blocks Count',
    description: 'Total number of text blocks detected',
    readOnly: true,
    section: 'OCR Processing',
  },
  words_count: {
    type: 'number',
    label: 'Words Count',
    description: 'Total number of words in extracted text',
    readOnly: true,
    section: 'OCR Processing',
  },
  pages_processed: {
    type: 'number',
    label: 'Pages Processed',
    description: 'Number of pages processed (for PDF documents)',
    readOnly: true,
    section: 'OCR Processing',
  },
  retry_count: {
    type: 'number',
    label: 'Retry Count',
    description: 'Number of processing attempts',
    readOnly: true,
    section: 'OCR Processing',
  },

  // Advanced
  file_info: {
    type: 'json',
    label: 'File Info',
    description: 'Additional file metadata',
    section: 'Advanced',
  },
  metadata: {
    type: 'json',
    label: 'Custom Metadata',
    description: 'Custom metadata object following required format',
    section: 'Advanced',
  },
};

/**
 * Get schema fields organized by section
 */
export function getFieldsBySection(): Record<string, string[]> {
  const sections: Record<string, string[]> = {};

  Object.entries(imageMetadataSchema).forEach(([fieldName, fieldDef]) => {
    const section = fieldDef.section || 'Other';
    if (!sections[section]) {
      sections[section] = [];
    }
    sections[section].push(fieldName);
  });

  return sections;
}

/**
 * Get schema fields in a specific order
 */
export const fieldOrder = Object.keys(imageMetadataSchema);

/**
 * Get only editable fields (excluding read-only fields)
 */
export function getEditableFields(): string[] {
  return fieldOrder.filter(
    (field) => !imageMetadataSchema[field]?.readOnly
  );
}

/**
 * Get field definition with fallback defaults
 */
export function getFieldDefinition(fieldName: string): FieldDefinition {
  return (
    imageMetadataSchema[fieldName] || {
      type: 'text',
      label: fieldName,
      description: 'Custom field',
    }
  );
}
