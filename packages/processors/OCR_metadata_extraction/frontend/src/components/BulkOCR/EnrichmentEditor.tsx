import React, { useState, useEffect } from 'react';
import { X, Save, AlertCircle, Loader, Check } from 'lucide-react';

interface EnrichmentData {
  filename: string;
  ocr_text: string;
  raw_mcp_responses: {
    [toolName: string]: any;
  };
  merged_result: {
    document_type?: string;
    title?: string;
    date_created?: string;
    author?: string;
    recipients?: string[];
    organizations?: string[];
    locations?: string[];
    keywords?: string[];
    subject?: string;
    summary?: string;
    language?: string;
    access_level?: string;
    archive_location?: string;
    collection?: string;
    box_number?: string;
    folder_number?: string;
    [key: string]: any;
  };
}

interface EnrichmentEditorProps {
  jobId: string;
  resultIndex: number;
  filename: string;
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void;
}

const EnrichmentEditor: React.FC<EnrichmentEditorProps> = ({
  jobId,
  resultIndex,
  filename,
  isOpen,
  onClose,
  onSave,
}) => {
  const [editedData, setEditedData] = useState<EnrichmentData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [activeTab, setActiveTab] = useState<'merged' | 'metadata' | 'content' | 'entities' | 'raw'>('merged');

  // Fetch enrichment data when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchEnrichmentData();
    }
  }, [isOpen, jobId, resultIndex]);

  const fetchEnrichmentData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `/api/bulk/job/${jobId}/result/${resultIndex}/enrichment`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch enrichment data');
      }

      const data = await response.json();
      if (data.enrichment) {
        setEditedData(JSON.parse(JSON.stringify(data.enrichment))); // Deep copy
      } else {
        setError('No enrichment data found');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load enrichment data';
      setError(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleMergedResultChange = (field: string, value: any) => {
    if (editedData) {
      setEditedData({
        ...editedData,
        merged_result: {
          ...editedData.merged_result,
          [field]: value,
        },
      });
    }
  };

  const handleArrayFieldChange = (field: string, value: string) => {
    const arrayValue = value
      .split(',')
      .map((item) => item.trim())
      .filter((item) => item.length > 0);

    handleMergedResultChange(field, arrayValue);
  };

  const handleSave = async () => {
    if (!editedData) return;

    setIsSaving(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `/api/bulk/job/${jobId}/result/${resultIndex}/enrichment`,
        {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ enrichment: editedData }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to save enrichment data');
      }

      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        onClose();
        onSave(); // Refresh parent data
      }, 1500);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to save enrichment data';
      setError(errorMsg);
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-screen overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold">Edit Enrichment Data</h2>
            <p className="text-sm text-blue-100 mt-1">{filename}</p>
          </div>
          <button
            onClick={onClose}
            disabled={isSaving}
            className="p-1 hover:bg-blue-500 rounded transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 mx-4 mt-4 flex items-start gap-3">
            <AlertCircle className="text-red-500 flex-shrink-0" size={20} />
            <div>
              <h3 className="font-semibold text-red-800">Error</h3>
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Success Alert */}
        {success && (
          <div className="bg-green-50 border-l-4 border-green-500 p-4 mx-4 mt-4 flex items-start gap-3">
            <Check className="text-green-500 flex-shrink-0" size={20} />
            <p className="text-green-800 font-medium">Enrichment data saved successfully!</p>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader size={32} className="animate-spin text-blue-600" />
            <p className="ml-3 text-gray-600">Loading enrichment data...</p>
          </div>
        )}

        {/* Content */}
        {!isLoading && editedData && (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Tabs */}
            <div className="bg-gray-100 border-b">
              <div className="flex overflow-x-auto px-4">
                <button
                  onClick={() => setActiveTab('merged')}
                  className={`px-4 py-3 font-medium border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === 'merged'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Merged Result
                </button>
                <button
                  onClick={() => setActiveTab('metadata')}
                  className={`px-4 py-3 font-medium border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === 'metadata'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Metadata
                </button>
                <button
                  onClick={() => setActiveTab('content')}
                  className={`px-4 py-3 font-medium border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === 'content'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Content Analysis
                </button>
                <button
                  onClick={() => setActiveTab('entities')}
                  className={`px-4 py-3 font-medium border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === 'entities'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Entities
                </button>
                <button
                  onClick={() => setActiveTab('raw')}
                  className={`px-4 py-3 font-medium border-b-2 transition-colors whitespace-nowrap ${
                    activeTab === 'raw'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Raw Data
                </button>
              </div>
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* Merged Result Tab */}
              {activeTab === 'merged' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Document Type
                    </label>
                    <input
                      type="text"
                      value={editedData.merged_result?.document_type || ''}
                      onChange={(e) =>
                        handleMergedResultChange('document_type', e.target.value)
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., letter, report, contract"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Title
                    </label>
                    <input
                      type="text"
                      value={editedData.merged_result?.title || ''}
                      onChange={(e) =>
                        handleMergedResultChange('title', e.target.value)
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Document title"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">
                        Date Created
                      </label>
                      <input
                        type="text"
                        value={editedData.merged_result?.date_created || ''}
                        onChange={(e) =>
                          handleMergedResultChange('date_created', e.target.value)
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="YYYY-MM-DD"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">
                        Author
                      </label>
                      <input
                        type="text"
                        value={editedData.merged_result?.author || ''}
                        onChange={(e) =>
                          handleMergedResultChange('author', e.target.value)
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Author name"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Subject
                    </label>
                    <input
                      type="text"
                      value={editedData.merged_result?.subject || ''}
                      onChange={(e) =>
                        handleMergedResultChange('subject', e.target.value)
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Document subject"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Summary
                    </label>
                    <textarea
                      value={editedData.merged_result?.summary || ''}
                      onChange={(e) =>
                        handleMergedResultChange('summary', e.target.value)
                      }
                      rows={4}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Document summary"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Access Level
                    </label>
                    <input
                      type="text"
                      value={editedData.merged_result?.access_level || ''}
                      onChange={(e) =>
                        handleMergedResultChange('access_level', e.target.value)
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., public, restricted, confidential"
                    />
                  </div>
                </div>
              )}

              {/* Metadata Tab */}
              {activeTab === 'metadata' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Recipients (comma-separated)
                    </label>
                    <textarea
                      value={(editedData.merged_result?.recipients || []).join(', ')}
                      onChange={(e) =>
                        handleArrayFieldChange('recipients', e.target.value)
                      }
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="John Smith, Jane Doe, ..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Organizations (comma-separated)
                    </label>
                    <textarea
                      value={(editedData.merged_result?.organizations || []).join(', ')}
                      onChange={(e) =>
                        handleArrayFieldChange('organizations', e.target.value)
                      }
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Organization A, Organization B, ..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Archive Location
                    </label>
                    <input
                      type="text"
                      value={editedData.merged_result?.archive_location || ''}
                      onChange={(e) =>
                        handleMergedResultChange('archive_location', e.target.value)
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Archive location/call number"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">
                        Box Number
                      </label>
                      <input
                        type="text"
                        value={editedData.merged_result?.box_number || ''}
                        onChange={(e) =>
                          handleMergedResultChange('box_number', e.target.value)
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Box #"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-gray-700 mb-2">
                        Folder Number
                      </label>
                      <input
                        type="text"
                        value={editedData.merged_result?.folder_number || ''}
                        onChange={(e) =>
                          handleMergedResultChange('folder_number', e.target.value)
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Folder #"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Collection
                    </label>
                    <input
                      type="text"
                      value={editedData.merged_result?.collection || ''}
                      onChange={(e) =>
                        handleMergedResultChange('collection', e.target.value)
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Collection name"
                    />
                  </div>
                </div>
              )}

              {/* Content Analysis Tab */}
              {activeTab === 'content' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Keywords (comma-separated)
                    </label>
                    <textarea
                      value={(editedData.merged_result?.keywords || []).join(', ')}
                      onChange={(e) =>
                        handleArrayFieldChange('keywords', e.target.value)
                      }
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="keyword1, keyword2, keyword3, ..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Language
                    </label>
                    <input
                      type="text"
                      value={editedData.merged_result?.language || ''}
                      onChange={(e) =>
                        handleMergedResultChange('language', e.target.value)
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., English, Hindi, Spanish"
                    />
                  </div>
                </div>
              )}

              {/* Entities Tab */}
              {activeTab === 'entities' && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-2">
                      Locations (comma-separated)
                    </label>
                    <textarea
                      value={(editedData.merged_result?.locations || []).join(', ')}
                      onChange={(e) =>
                        handleArrayFieldChange('locations', e.target.value)
                      }
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="New York, London, Mumbai, ..."
                    />
                  </div>

                  <div className="text-sm text-gray-500 bg-gray-50 p-3 rounded">
                    <p className="font-semibold mb-2">Note:</p>
                    <p>This tab shows entities extracted during enrichment processing. Edit the lists above to correct any extraction errors.</p>
                  </div>
                </div>
              )}

              {/* Raw Data Tab */}
              {activeTab === 'raw' && (
                <div className="bg-gray-50 p-4 rounded-lg overflow-auto max-h-96">
                  <pre className="text-xs whitespace-pre-wrap break-words">
                    {JSON.stringify(editedData.raw_mcp_responses, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="bg-gray-50 border-t px-6 py-4 flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={isSaving}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving || isLoading || !editedData}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {isSaving ? <Loader size={16} className="animate-spin" /> : <Save size={16} />}
            {isSaving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default EnrichmentEditor;
