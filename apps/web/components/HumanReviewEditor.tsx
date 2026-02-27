/**
 * Human Review Editor
 * 
 * Full editing interface for reviewing OCR-extracted text and metadata
 * before storing in the system. Allows reviewers to:
 * - Edit OCR text directly
 * - Modify all metadata fields
 * - Add comments and annotations
 * - Approve or reject for re-processing
 */

'use client';

import { useState, useEffect } from 'react';

interface DocumentMetadata {
  document: {
    type?: string;
    title?: string;
    date?: {
      year?: number;
      month?: number;
      day?: number;
      display?: string;
    };
    language?: string;
  };
  people?: Array<{
    name: string;
    role?: string;
    biography?: string;
  }>;
  organizations?: Array<{
    name: string;
    type?: string;
  }>;
  locations?: Array<{
    name: string;
    type?: string;
  }>;
  content?: {
    summary?: string;
    keywords?: string[];
    subjects?: string[];
  };
  analysis?: {
    sentiment?: string;
    themes?: string[];
  };
}

interface ReviewData {
  job_id: string;
  file_index: number;
  ocr_text: string;
  enriched_metadata: DocumentMetadata;
  original_file_path: string;
  quality_metrics?: {
    completeness_score?: number;
    missing_fields?: string[];
  };
}

interface HumanReviewEditorProps {
  data: ReviewData;
  onApprove: (editedData: ReviewData, comments: string) => void;
  onReject: (reason: string) => void;
  onCancel: () => void;
}

export default function HumanReviewEditor({ 
  data, 
  onApprove, 
  onReject, 
  onCancel 
}: HumanReviewEditorProps) {
  // Editable state
  const [ocrText, setOcrText] = useState(data.ocr_text);
  const [metadata, setMetadata] = useState<DocumentMetadata>(data.enriched_metadata);
  const [comments, setComments] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  
  // UI state
  const [activeTab, setActiveTab] = useState<'text' | 'metadata' | 'quality'>('text');
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // Track changes
  useEffect(() => {
    const textChanged = ocrText !== data.ocr_text;
    const metadataChanged = JSON.stringify(metadata) !== JSON.stringify(data.enriched_metadata);
    setHasChanges(textChanged || metadataChanged);
  }, [ocrText, metadata, data]);

  // Metadata helpers
  const updateDocumentField = (field: string, value: string | number | undefined) => {
    setMetadata({
      ...metadata,
      document: {
        ...metadata.document,
        [field]: value
      }
    });
  };

  const updateDateField = (field: string, value: string | number | undefined) => {
    setMetadata({
      ...metadata,
      document: {
        ...metadata.document,
        date: {
          ...metadata.document?.date,
          [field]: value
        }
      }
    });
  };

  const updateContentField = (field: string, value: string | number | undefined) => {
    setMetadata({
      ...metadata,
      content: {
        ...metadata.content,
        [field]: value
      }
    });
  };

  const addPerson = () => {
    setMetadata({
      ...metadata,
      people: [...(metadata.people || []), { name: '', role: '', biography: '' }]
    });
  };

  const updatePerson = (index: number, field: string, value: string) => {
    const people = [...(metadata.people || [])];
    people[index] = { ...people[index], [field]: value };
    setMetadata({ ...metadata, people });
  };

  const removePerson = (index: number) => {
    const people = [...(metadata.people || [])];
    people.splice(index, 1);
    setMetadata({ ...metadata, people });
  };

  const handleApprove = () => {
    const editedData: ReviewData = {
      ...data,
      ocr_text: ocrText,
      enriched_metadata: metadata
    };
    onApprove(editedData, comments);
  };

  const handleReject = () => {
    if (!rejectReason.trim()) {
      alert('Please provide a reason for rejection');
      return;
    }
    onReject(rejectReason);
    setShowRejectModal(false);
  };

  return (
    <div className="h-full flex flex-col bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Human Review Editor</h2>
            <p className="text-sm text-slate-600 mt-1">
              Review and edit OCR extraction and enriched metadata
            </p>
          </div>
          <div className="flex items-center gap-3">
            {hasChanges && (
              <span className="text-sm text-amber-600 font-medium">● Unsaved changes</span>
            )}
            <button
              onClick={onCancel}
              className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-lg border border-slate-300"
            >
              Cancel
            </button>
            <button
              onClick={() => setShowRejectModal(true)}
              className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-700 rounded-lg"
            >
              Reject
            </button>
            <button
              onClick={handleApprove}
              className="px-4 py-2 text-sm text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg font-medium"
            >
              Approve & Continue
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-slate-200 px-6">
        <div className="flex gap-6">
          {(['text', 'metadata', 'quality'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-slate-600 hover:text-slate-900'
              }`}
            >
              {tab === 'text' && '📝 OCR Text'}
              {tab === 'metadata' && '🏷️ Metadata'}
              {tab === 'quality' && '📊 Quality Metrics'}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* OCR Text Tab */}
        {activeTab === 'text' && (
          <div className="max-w-4xl mx-auto">
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="mb-4">
                <label className="block text-sm font-semibold text-slate-700 mb-2">
                  Extracted Text (Editable)
                </label>
                <p className="text-xs text-slate-500 mb-3">
                  Review and correct any OCR errors in the extracted text
                </p>
              </div>
              <textarea
                value={ocrText}
                onChange={(e) => setOcrText(e.target.value)}
                className="w-full h-96 px-4 py-3 border border-slate-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Extracted text will appear here..."
              />
              <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                <span>{ocrText.length} characters</span>
                <span>{ocrText.split(/\s+/).filter(w => w).length} words</span>
              </div>
            </div>
          </div>
        )}

        {/* Metadata Tab */}
        {activeTab === 'metadata' && (
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Document Info */}
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Document Information</h3>
              
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">Type</label>
                  <input
                    type="text"
                    value={metadata.document?.type || ''}
                    onChange={(e) => updateDocumentField('type', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., Letter, Manuscript"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">Language</label>
                  <input
                    type="text"
                    value={metadata.document?.language || ''}
                    onChange={(e) => updateDocumentField('language', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., English, Sanskrit"
                  />
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-slate-700 mb-2">Title</label>
                <input
                  type="text"
                  value={metadata.document?.title || ''}
                  onChange={(e) => updateDocumentField('title', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                  placeholder="Document title"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Date</label>
                <div className="grid grid-cols-4 gap-3">
                  <input
                    type="number"
                    value={metadata.document?.date?.year || ''}
                    onChange={(e) => updateDateField('year', parseInt(e.target.value))}
                    className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    placeholder="Year"
                  />
                  <input
                    type="number"
                    value={metadata.document?.date?.month || ''}
                    onChange={(e) => updateDateField('month', parseInt(e.target.value))}
                    className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    placeholder="Month"
                  />
                  <input
                    type="number"
                    value={metadata.document?.date?.day || ''}
                    onChange={(e) => updateDateField('day', parseInt(e.target.value))}
                    className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    placeholder="Day"
                  />
                  <input
                    type="text"
                    value={metadata.document?.date?.display || ''}
                    onChange={(e) => updateDateField('display', e.target.value)}
                    className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    placeholder="Display"
                  />
                </div>
              </div>
            </div>

            {/* People */}
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-slate-900">People</h3>
                <button
                  onClick={addPerson}
                  className="px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-lg border border-blue-200"
                >
                  + Add Person
                </button>
              </div>

              <div className="space-y-4">
                {metadata.people?.map((person, index) => (
                  <div key={index} className="border border-slate-200 rounded-lg p-4">
                    <div className="flex items-start justify-between mb-3">
                      <span className="text-sm font-medium text-slate-700">Person {index + 1}</span>
                      <button
                        onClick={() => removePerson(index)}
                        className="text-sm text-red-600 hover:text-red-700"
                      >
                        Remove
                      </button>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <input
                        type="text"
                        value={person.name}
                        onChange={(e) => updatePerson(index, 'name', e.target.value)}
                        className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                        placeholder="Name"
                      />
                      <input
                        type="text"
                        value={person.role || ''}
                        onChange={(e) => updatePerson(index, 'role', e.target.value)}
                        className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
                        placeholder="Role"
                      />
                    </div>
                    <textarea
                      value={person.biography || ''}
                      onChange={(e) => updatePerson(index, 'biography', e.target.value)}
                      className="w-full mt-3 px-3 py-2 border border-slate-300 rounded-lg text-sm"
                      rows={2}
                      placeholder="Biography"
                    />
                  </div>
                ))}
                {(!metadata.people || metadata.people.length === 0) && (
                  <p className="text-sm text-slate-500 text-center py-4">No people added yet</p>
                )}
              </div>
            </div>

            {/* Content Analysis */}
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Content Analysis</h3>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-slate-700 mb-2">Summary</label>
                <textarea
                  value={metadata.content?.summary || ''}
                  onChange={(e) => updateContentField('summary', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  rows={4}
                  placeholder="Brief summary of the document..."
                />
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-slate-700 mb-2">Keywords (comma-separated)</label>
                <input
                  type="text"
                  value={metadata.content?.keywords?.join(', ') || ''}
                  onChange={(e) => updateContentField('keywords', e.target.value.split(',').map(k => k.trim()))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  placeholder="heritage, history, letter"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Subjects (comma-separated)</label>
                <input
                  type="text"
                  value={metadata.content?.subjects?.join(', ') || ''}
                  onChange={(e) => updateContentField('subjects', e.target.value.split(',').map(s => s.trim()))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                  placeholder="Personal correspondence, Historical events"
                />
              </div>
            </div>

            {/* Review Comments */}
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Review Comments</h3>
              <textarea
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                rows={4}
                placeholder="Add any comments or notes about this review..."
              />
            </div>
          </div>
        )}

        {/* Quality Metrics Tab */}
        {activeTab === 'quality' && (
          <div className="max-w-4xl mx-auto">
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Quality Metrics</h3>
              
              {data.quality_metrics && (
                <>
                  <div className="mb-6">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-slate-700">Completeness Score</span>
                      <span className="text-2xl font-bold text-blue-600">
                        {Math.round((data.quality_metrics.completeness_score || 0) * 100)}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all"
                        style={{ width: `${(data.quality_metrics.completeness_score || 0) * 100}%` }}
                      />
                    </div>
                  </div>

                  {data.quality_metrics.missing_fields && data.quality_metrics.missing_fields.length > 0 && (
                    <div className="mb-6">
                      <h4 className="text-sm font-semibold text-slate-700 mb-3">Missing Fields</h4>
                      <div className="space-y-2">
                        {data.quality_metrics.missing_fields.map((field, index) => (
                          <div key={index} className="flex items-center gap-2 text-sm text-amber-700 bg-amber-50 px-3 py-2 rounded-lg">
                            <span>⚠️</span>
                            <span>{field}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-4 bg-slate-50 rounded-lg">
                      <p className="text-xs text-slate-500 mb-1">OCR Text Length</p>
                      <p className="text-2xl font-bold text-slate-900">{ocrText.length}</p>
                      <p className="text-xs text-slate-500">characters</p>
                    </div>
                    
                    <div className="text-center p-4 bg-slate-50 rounded-lg">
                      <p className="text-xs text-slate-500 mb-1">People Identified</p>
                      <p className="text-2xl font-bold text-slate-900">{metadata.people?.length || 0}</p>
                      <p className="text-xs text-slate-500">entities</p>
                    </div>
                    
                    <div className="text-center p-4 bg-slate-50 rounded-lg">
                      <p className="text-xs text-slate-500 mb-1">Keywords</p>
                      <p className="text-2xl font-bold text-slate-900">{metadata.content?.keywords?.length || 0}</p>
                      <p className="text-xs text-slate-500">extracted</p>
                    </div>
                  </div>
                </>
              )}

              {!data.quality_metrics && (
                <p className="text-sm text-slate-500 text-center py-8">No quality metrics available</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full p-6">
            <h3 className="text-lg font-bold text-slate-900 mb-4">Reject Document</h3>
            <p className="text-sm text-slate-600 mb-4">
              Please provide a reason for rejecting this document. It will be sent back for re-processing.
            </p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm mb-4"
              rows={4}
              placeholder="Reason for rejection..."
              autoFocus
            />
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowRejectModal(false)}
                className="px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-700 rounded-lg"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
