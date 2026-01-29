import React, { useState } from 'react';
import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';

interface DocumentClassificationProps {
  documentId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const DocumentClassification: React.FC<DocumentClassificationProps> = ({
  documentId,
  isOpen,
  onClose,
  onSuccess
}) => {
  const { accessToken } = useAuthStore();
  const [classification, setClassification] = useState('PUBLIC');
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClassify = async () => {
    if (!reason.trim()) {
      setError('Please provide a reason for classification');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      await axios.post(
        `/api/documents/${documentId}/classify`,
        {
          classification,
          reason
        },
        {
          headers: {
            Authorization: `Bearer ${accessToken}`
          }
        }
      );

      // Reset form
      setClassification('PUBLIC');
      setReason('');
      onClose();

      if (onSuccess) {
        onSuccess();
      }
    } catch (err: any) {
      const message = err.response?.data?.error || 'Failed to classify document';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex justify-between items-center p-6 border-b">
          <h2 className="text-xl font-bold text-gray-900">Classify Document</h2>
          <button
            onClick={onClose}
            disabled={loading}
            className="text-gray-500 hover:text-gray-700 disabled:opacity-50"
          >
            ✕
          </button>
        </div>

        <div className="p-6 space-y-4">
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-bold text-gray-700 mb-3">Classification Type</label>
            <div className="space-y-3">
              <label className={`p-3 border-2 rounded-md cursor-pointer transition ${
                classification === 'PUBLIC' ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
              }`}>
                <input
                  type="radio"
                  value="PUBLIC"
                  checked={classification === 'PUBLIC'}
                  onChange={(e) => setClassification(e.target.value)}
                  disabled={loading}
                  className="mr-3"
                />
                <span className="font-bold">PUBLIC</span>
                <p className="text-sm text-gray-600 ml-6">Open for review by all reviewers and teachers</p>
              </label>

              <label className={`p-3 border-2 rounded-md cursor-pointer transition ${
                classification === 'PRIVATE' ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
              }`}>
                <input
                  type="radio"
                  value="PRIVATE"
                  checked={classification === 'PRIVATE'}
                  onChange={(e) => setClassification(e.target.value)}
                  disabled={loading}
                  className="mr-3"
                />
                <span className="font-bold">PRIVATE</span>
                <p className="text-sm text-gray-600 ml-6">Restricted - only teachers can review</p>
              </label>
            </div>
          </div>

          <div>
            <label htmlFor="reason" className="block text-sm font-bold text-gray-700 mb-2">
              Reason for Classification *
            </label>
            <textarea
              id="reason"
              placeholder="Explain why you're classifying this document as PUBLIC or PRIVATE..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              disabled={loading}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
            />
          </div>
        </div>

        <div className="flex gap-3 justify-end p-6 border-t">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleClassify}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {loading && (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            )}
            {loading ? 'Classifying...' : 'Classify'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DocumentClassification;
