/**
 * Verification Detail Page
 * Side-by-side view for reviewing and editing image metadata
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  Save,
  AlertCircle,
  RefreshCw,
  History
} from 'lucide-react';
import AppLayout from '@/components/Layout/AppLayout';
import * as verificationService from '@/services/verificationService';
import type { VerificationImage, AuditEntry } from '@/services/verificationService';

export default function VerificationDetail() {
  const { imageId } = useParams<{ imageId: string }>();
  const navigate = useNavigate();

  const [image, setImage] = useState<VerificationImage | null>(null);
  const [auditTrail, setAuditTrail] = useState<AuditEntry[]>([]);
  const [editedText, setEditedText] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAuditTrail, setShowAuditTrail] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  useEffect(() => {
    if (imageId) {
      loadImage();
    }
  }, [imageId]);

  useEffect(() => {
    if (image) {
      setEditedText(image.ocr_text || '');
      setHasUnsavedChanges(false);
    }
  }, [image]);

  const loadImage = async () => {
    if (!imageId) return;
    
    try {
      setLoading(true);
      setError(null);
      const data = await verificationService.getImageForVerification(imageId);
      setImage(data.image);
      setAuditTrail(data.audit_trail);
    } catch (err: any) {
      console.error('Failed to load image:', err);
      setError(err.message || 'Failed to load image details');
    } finally {
      setLoading(false);
    }
  };

  const handleTextChange = (text: string) => {
    setEditedText(text);
    setHasUnsavedChanges(text !== (image?.ocr_text || ''));
  };

  const handleSaveEdit = async () => {
    if (!imageId || !image) return;
    
    try {
      setSaving(true);
      setError(null);
      const data = await verificationService.editImageMetadata(imageId, {
        ocr_text: editedText,
        version: image.version,
        notes: notes || undefined
      });
      setImage(data.image);
      setNotes('');
      setHasUnsavedChanges(false);
      await loadImage(); // Reload to get updated audit trail
    } catch (err: any) {
      console.error('Failed to save edit:', err);
      if (err.response?.status === 409) {
        setError('Version conflict - the image was updated by another user. Please refresh and try again.');
      } else {
        setError(err.message || 'Failed to save changes');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleVerify = async () => {
    if (!imageId || !image) return;
    
    try {
      setSaving(true);
      setError(null);
      await verificationService.verifyImage(imageId, {
        version: image.version,
        notes: notes || undefined
      });
      navigate('/verification');
    } catch (err: any) {
      console.error('Failed to verify:', err);
      if (err.response?.status === 409) {
        setError('Version conflict - please refresh and try again.');
      } else {
        setError(err.message || 'Failed to verify image');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleReject = async () => {
    if (!imageId || !image) return;
    
    const reason = prompt('Please provide a reason for rejection:');
    if (!reason) return;
    
    try {
      setSaving(true);
      setError(null);
      await verificationService.rejectImage(imageId, {
        version: image.version,
        notes: reason
      });
      navigate('/verification');
    } catch (err: any) {
      console.error('Failed to reject:', err);
      if (err.response?.status === 409) {
        setError('Version conflict - please refresh and try again.');
      } else {
        setError(err.message || 'Failed to reject image');
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-screen">
          <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      </AppLayout>
    );
  }

  if (!image) {
    return (
      <AppLayout>
        <div className="container mx-auto px-4 py-8">
          <div className="text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Image Not Found</h2>
            <p className="text-gray-600 mb-4">The requested image could not be loaded.</p>
            <button
              onClick={() => navigate('/verification')}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/verification')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-6 h-6" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {image.original_filename}
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <span className={`px-2 py-1 text-xs rounded-full ${
                  image.verification_status === 'verified'
                    ? 'bg-green-100 text-green-800'
                    : image.verification_status === 'rejected'
                    ? 'bg-red-100 text-red-800'
                    : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {image.verification_status.replace('_', ' ')}
                </span>
                <span className="text-sm text-gray-500">
                  Version {image.version}
                </span>
              </div>
            </div>
          </div>

          <button
            onClick={() => setShowAuditTrail(!showAuditTrail)}
            className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <History className="w-5 h-5" />
            <span>Audit Trail</span>
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
            <div>
              <p className="text-red-800 font-medium">Error</p>
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="grid grid-cols-2 gap-6 mb-6">
          {/* Document Preview */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Document Preview</h2>
            <div className="border border-gray-300 rounded-lg overflow-hidden bg-gray-50 flex items-center justify-center" style={{ minHeight: '500px' }}>
              <img
                src={`${import.meta.env.VITE_API_URL || 'http://localhost:5000'}/api/ocr/image/${imageId}`}
                alt={image.original_filename}
                className="max-w-full max-h-[500px] object-contain"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                  (e.target as HTMLImageElement).parentElement!.innerHTML = '<div class="text-gray-500">Preview not available</div>';
                }}
              />
            </div>
            <div className="mt-4 text-sm text-gray-600">
              <p><strong>File Type:</strong> {image.file_type.toUpperCase()}</p>
              <p><strong>OCR Status:</strong> {image.ocr_status}</p>
              {image.ocr_processed_at && (
                <p><strong>Processed:</strong> {new Date(image.ocr_processed_at).toLocaleString()}</p>
              )}
            </div>
          </div>

          {/* Metadata Editor */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">OCR Text</h2>
            <textarea
              value={editedText}
              onChange={(e) => handleTextChange(e.target.value)}
              className="w-full h-[500px] p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
              placeholder="No OCR text available"
            />
            
            {hasUnsavedChanges && (
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-yellow-800 text-sm">You have unsaved changes</p>
              </div>
            )}

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Notes (optional)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows={3}
                placeholder="Add notes about your changes..."
              />
            </div>

            <div className="mt-4 flex items-center gap-3">
              <button
                onClick={handleSaveEdit}
                disabled={!hasUnsavedChanges || saving}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Save className="w-5 h-5" />
                <span>Save Changes</span>
              </button>
            </div>
          </div>
        </div>

        {/* Audit Trail */}
        {showAuditTrail && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-lg font-semibold mb-4">Audit Trail</h2>
            {auditTrail.length === 0 ? (
              <p className="text-gray-500 text-sm">No audit entries yet</p>
            ) : (
              <div className="space-y-3">
                {auditTrail.map((entry) => (
                  <div key={entry.id} className="border-l-4 border-blue-500 pl-4 py-2">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium text-gray-900">
                          {entry.action === 'edit' ? 'Edited' : 
                           entry.action === 'verify' ? 'Verified' : 
                           entry.action === 'reject' ? 'Rejected' : entry.action}
                        </p>
                        {entry.field_name && (
                          <p className="text-sm text-gray-600">Field: {entry.field_name}</p>
                        )}
                        {entry.notes && (
                          <p className="text-sm text-gray-700 mt-1">{entry.notes}</p>
                        )}
                      </div>
                      <p className="text-sm text-gray-500">
                        {new Date(entry.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        {image.verification_status === 'pending_verification' && (
          <div className="flex items-center justify-between bg-white rounded-lg shadow p-6">
            <div className="text-sm text-gray-600">
              Review the OCR text and make any necessary corrections before verifying.
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handleReject}
                disabled={saving}
                className="flex items-center gap-2 px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                <XCircle className="w-5 h-5" />
                <span>Reject</span>
              </button>
              <button
                onClick={handleVerify}
                disabled={saving || hasUnsavedChanges}
                className="flex items-center gap-2 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
              >
                <CheckCircle className="w-5 h-5" />
                <span>Verify</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
