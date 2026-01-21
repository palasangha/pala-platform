/**
 * Verification Dashboard
 * Main page for the verification workflow with queue management
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  Eye, 
  AlertCircle,
  RefreshCw,
  Search
} from 'lucide-react';
import AppLayout from '@/components/Layout/AppLayout';
import * as verificationService from '@/services/verificationService';
import type { VerificationImage } from '@/services/verificationService';

type VerificationStatus = 'pending_verification' | 'verified' | 'rejected';

export default function VerificationDashboard() {
  const navigate = useNavigate();
  
  const [status, setStatus] = useState<VerificationStatus>('pending_verification');
  const [items, setItems] = useState<VerificationImage[]>([]);
  const [counts, setCounts] = useState({
    pending_verification: 0,
    verified: 0,
    rejected: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(0);
  const pageSize = 50;

  // Load queue data
  useEffect(() => {
    loadQueue();
    loadCounts();
  }, [status, page]);

  const loadQueue = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await verificationService.getVerificationQueue({
        status,
        skip: page * pageSize,
        limit: pageSize
      });
      setItems(data.items);
    } catch (err: any) {
      console.error('Failed to load queue:', err);
      setError(err.message || 'Failed to load verification queue');
    } finally {
      setLoading(false);
    }
  };

  const loadCounts = async () => {
    try {
      const data = await verificationService.getQueueCounts();
      setCounts(data.counts);
    } catch (err) {
      console.error('Failed to load counts:', err);
    }
  };

  const handleStatusChange = (newStatus: VerificationStatus) => {
    setStatus(newStatus);
    setPage(0);
    setSelectedItems(new Set());
  };

  const handleViewImage = (imageId: string) => {
    navigate(`/verification/${imageId}`);
  };

  const handleSelectItem = (imageId: string) => {
    const newSelected = new Set(selectedItems);
    if (newSelected.has(imageId)) {
      newSelected.delete(imageId);
    } else {
      newSelected.add(imageId);
    }
    setSelectedItems(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedItems.size === filteredItems.length) {
      setSelectedItems(new Set());
    } else {
      setSelectedItems(new Set(filteredItems.map(item => item.id)));
    }
  };

  const handleBatchVerify = async () => {
    if (selectedItems.size === 0) return;
    
    try {
      setLoading(true);
      await verificationService.batchVerify({
        image_ids: Array.from(selectedItems),
        notes: 'Batch verification'
      });
      setSelectedItems(new Set());
      await loadQueue();
      await loadCounts();
    } catch (err: any) {
      console.error('Batch verify failed:', err);
      setError(err.message || 'Batch verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleBatchReject = async () => {
    if (selectedItems.size === 0) return;
    
    const notes = prompt('Please provide a reason for rejection:');
    if (!notes) return;
    
    try {
      setLoading(true);
      await verificationService.batchReject({
        image_ids: Array.from(selectedItems),
        notes
      });
      setSelectedItems(new Set());
      await loadQueue();
      await loadCounts();
    } catch (err: any) {
      console.error('Batch reject failed:', err);
      setError(err.message || 'Batch rejection failed');
    } finally {
      setLoading(false);
    }
  };

  const filteredItems = items.filter(item =>
    item.original_filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.ocr_text?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <AppLayout>
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Verification Dashboard
          </h1>
          <p className="text-gray-600">
            Review and validate OCR metadata before publishing
          </p>
        </div>

        {/* Status Tabs */}
        <div className="flex gap-2 mb-6 border-b border-gray-200">
          <button
            onClick={() => handleStatusChange('pending_verification')}
            className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
              status === 'pending_verification'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <Clock className="w-5 h-5" />
            <span>Pending</span>
            <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-sm">
              {counts.pending_verification}
            </span>
          </button>
          
          <button
            onClick={() => handleStatusChange('verified')}
            className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
              status === 'verified'
                ? 'border-green-600 text-green-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <CheckCircle className="w-5 h-5" />
            <span>Verified</span>
            <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-sm">
              {counts.verified}
            </span>
          </button>
          
          <button
            onClick={() => handleStatusChange('rejected')}
            className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
              status === 'rejected'
                ? 'border-red-600 text-red-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <XCircle className="w-5 h-5" />
            <span>Rejected</span>
            <span className="bg-red-100 text-red-800 px-2 py-1 rounded-full text-sm">
              {counts.rejected}
            </span>
          </button>
        </div>

        {/* Toolbar */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder="Search files..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Batch Actions */}
            {selectedItems.size > 0 && status === 'pending_verification' && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">
                  {selectedItems.size} selected
                </span>
                <button
                  onClick={handleBatchVerify}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  Verify Selected
                </button>
                <button
                  onClick={handleBatchReject}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  Reject Selected
                </button>
              </div>
            )}
          </div>

          <button
            onClick={() => { loadQueue(); loadCounts(); }}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
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

        {/* Queue List */}
        {loading ? (
          <div className="text-center py-12">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-gray-400" />
            <p className="text-gray-600">Loading verification queue...</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 rounded-lg">
            <p className="text-gray-600 mb-2">No items found</p>
            <p className="text-gray-500 text-sm">
              {searchTerm ? 'Try adjusting your search' : 'All items in this status have been processed'}
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {status === 'pending_verification' && (
                    <th className="px-6 py-3 text-left">
                      <input
                        type="checkbox"
                        checked={filteredItems.length > 0 && selectedItems.size === filteredItems.length}
                        onChange={handleSelectAll}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                    </th>
                  )}
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    File
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    OCR Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredItems.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    {status === 'pending_verification' && (
                      <td className="px-6 py-4">
                        <input
                          type="checkbox"
                          checked={selectedItems.has(item.id)}
                          onChange={() => handleSelectItem(item.id)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                      </td>
                    )}
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900">
                        {item.original_filename}
                      </div>
                      <div className="text-sm text-gray-500">
                        {item.file_type.toUpperCase()}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        item.ocr_status === 'completed'
                          ? 'bg-green-100 text-green-800'
                          : item.ocr_status === 'processing'
                          ? 'bg-blue-100 text-blue-800'
                          : item.ocr_status === 'failed'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {item.ocr_status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {item.created_at ? new Date(item.created_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => handleViewImage(item.id)}
                        className="flex items-center gap-2 text-blue-600 hover:text-blue-800 transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                        <span className="text-sm">Review</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {filteredItems.length > 0 && (
          <div className="flex items-center justify-between mt-6">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="text-sm text-gray-600">
              Page {page + 1}
            </span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={items.length < pageSize}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
