/**
 * Inline Step Editor Component
 * 
 * Flexible component for editing OCR text and metadata inline
 * Replaces the modal-based HumanReviewEditor
 */

'use client';

import { useState } from 'react';

interface InlineStepEditorProps {
  stepId: 'ocr' | 'metadata';
  ocrText: string;
  metadata: EditableMetadata;
  onSave: (ocrText: string, metadata: EditableMetadata) => void;
  onCancel: () => void;
}

interface EditableMetadata {
  document?: {
    type?: string;
    title?: string;
    language?: string;
  };
  content?: {
    summary?: string;
    keywords?: string[];
  };
}

export default function InlineStepEditor({
  stepId,
  ocrText: initialOcrText,
  metadata: initialMetadata,
  onSave,
  onCancel
}: InlineStepEditorProps) {
  const [ocrText, setOcrText] = useState(initialOcrText);
  const [metadata, setMetadata] = useState(initialMetadata || {});
  const [activeTab, setActiveTab] = useState<'text' | 'metadata'>(stepId === 'ocr' ? 'text' : 'metadata');

  const handleSave = () => {
    onSave(ocrText, metadata);
  };

  // Simple metadata field update
  const updateMetadataField = (path: string, value: unknown) => {
    const keys = path.split('.');
    const newMetadata = { ...metadata } as Record<string, unknown>;
    let current: Record<string, unknown> = newMetadata;
    
    for (let i = 0; i < keys.length - 1; i++) {
      if (!current[keys[i]]) current[keys[i]] = {};
      current = current[keys[i]] as Record<string, unknown>;
    }
    current[keys[keys.length - 1]] = value;
    
    setMetadata(newMetadata as EditableMetadata);
  };

  return (
    <div className="bg-white rounded-lg border-2 border-blue-500 p-4">
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-semibold text-slate-900">
          ✏️ Editing: {stepId === 'ocr' ? 'OCR Text' : 'Metadata'}
        </h4>
        <div className="flex gap-2">
          <button
            onClick={onCancel}
            className="px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 rounded-lg border border-slate-300"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-3 py-1.5 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-lg"
          >
            Save Changes
          </button>
        </div>
      </div>

      {/* Tabs */}
      {stepId === 'metadata' && (
        <div className="flex gap-2 mb-4 border-b border-slate-200">
          <button
            onClick={() => setActiveTab('text')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'text'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            OCR Text
          </button>
          <button
            onClick={() => setActiveTab('metadata')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'metadata'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            Metadata
          </button>
        </div>
      )}

      {/* OCR Text Editor */}
      {(stepId === 'ocr' || activeTab === 'text') && (
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Extracted Text
          </label>
          <textarea
            value={ocrText}
            onChange={(e) => setOcrText(e.target.value)}
            className="w-full h-64 px-3 py-2 border border-slate-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="OCR extracted text..."
          />
          <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
            <span>{ocrText.length} characters</span>
            <span>{ocrText.split(/\s+/).filter(w => w).length} words</span>
          </div>
        </div>
      )}

      {/* Metadata Editor */}
      {stepId === 'metadata' && activeTab === 'metadata' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Document Type</label>
              <input
                type="text"
                value={metadata.document?.type || ''}
                onChange={(e) => updateMetadataField('document.type', e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                placeholder="e.g., Letter, Manuscript"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Language</label>
              <input
                type="text"
                value={metadata.document?.language || ''}
                onChange={(e) => updateMetadataField('document.language', e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                placeholder="e.g., English"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Title</label>
            <input
              type="text"
              value={metadata.document?.title || ''}
              onChange={(e) => updateMetadataField('document.title', e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
              placeholder="Document title"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Summary</label>
            <textarea
              value={metadata.content?.summary || ''}
              onChange={(e) => updateMetadataField('content.summary', e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
              rows={3}
              placeholder="Brief summary..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Keywords (comma-separated)</label>
            <input
              type="text"
              value={metadata.content?.keywords?.join(', ') || ''}
              onChange={(e) => updateMetadataField('content.keywords', e.target.value.split(',').map((k: string) => k.trim()))}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
              placeholder="keyword1, keyword2, keyword3"
            />
          </div>

          <details className="mt-4">
            <summary className="cursor-pointer text-sm font-medium text-slate-700 hover:text-slate-900">
              View Full Metadata JSON
            </summary>
            <pre className="mt-2 p-3 bg-slate-900 text-slate-100 text-xs rounded-lg overflow-x-auto">
              {JSON.stringify(metadata, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}
