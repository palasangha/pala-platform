import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Download, RefreshCw, ArrowLeft, Loader, CheckCircle, AlertCircle } from 'lucide-react';
import ChainTimeline from '@/components/OCRChain/ChainTimeline';
import { chainAPI } from '@/services/api';

interface ChainResult {
  file: string;
  file_path: string;
  text: string;
  chain_steps?: any[];
  status: string;
  metadata?: any;
}

interface JobData {
  id: string;
  job_id: string;
  status: string;
  progress: {
    current: number;
    total: number;
    percentage: number;
    filename: string;
  };
  chain_config?: {
    steps: any[];
  };
  checkpoint?: {
    results: ChainResult[];
  };
  total_files?: number;
  consumed_count?: number;
}

export default function OCRChainResults() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [job, setJob] = useState<JobData | null>(null);
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [failureCount, setFailureCount] = useState(0);
  const MAX_FAILURES = 10; // Stop polling after 10 consecutive failures
  const blobUrlRef = useRef<string | null>(null); // Track blob URL for cleanup
  const abortControllerRef = useRef<AbortController | null>(null); // Track pending requests

  // Load job data
  useEffect(() => {
    // Create abort controller for this effect
    abortControllerRef.current = new AbortController();

    loadJobData();
    const interval = setInterval(() => {
      // Stop polling if job is completed or max failures reached
      setJob(currentJob => {
        if (currentJob?.status === 'completed' || currentJob?.status === 'failed') {
          clearInterval(interval);
        }
        return currentJob;
      });
      loadJobData();
    }, 2000);

    return () => {
      clearInterval(interval);
      // Cancel any pending requests on unmount
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [jobId]);


  const loadJobData = async () => {
    if (!jobId) return;
    try {
      setError(null); // Clear previous errors before attempting to load
      const data = await chainAPI.getChainResults(jobId);
      setJob(data.job);
      setFailureCount(0); // Reset failure counter on success
      setLoading(false);
    } catch (err) {
      console.error('Failed to load job:', err);
      const newFailureCount = failureCount + 1;
      setFailureCount(newFailureCount);

      // Stop polling if max failures reached
      if (newFailureCount >= MAX_FAILURES) {
        setError('Failed to load job after multiple attempts');
      } else {
        setError('Failed to load job details');
      }
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!jobId) return;
    try {
      setExporting(true);
      const blob = await chainAPI.exportChainResults(jobId);

      // Create a download link for the blob
      const url = window.URL.createObjectURL(blob);
      blobUrlRef.current = url; // Store for cleanup

      const link = document.createElement('a');
      link.href = url;
      link.download = `chain_results_${jobId.substring(0, 8)}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Schedule revocation after click to ensure download starts
      setTimeout(() => {
        if (blobUrlRef.current) {
          window.URL.revokeObjectURL(blobUrlRef.current);
          blobUrlRef.current = null;
        }
      }, 100);
    } catch (err) {
      console.error('Failed to export:', err);
      setError('Failed to export results');
    } finally {
      setExporting(false);
    }
  };

  // Cleanup blob URLs on component unmount
  useEffect(() => {
    return () => {
      if (blobUrlRef.current) {
        window.URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <Loader size={40} className="animate-spin text-blue-500 mx-auto mb-4" />
          <p className="text-gray-600">Loading job details...</p>
        </div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 flex items-gap gap-4">
          <AlertCircle size={24} className="text-red-600 flex-shrink-0" />
          <div>
            <h2 className="font-semibold text-red-900">Error</h2>
            <p className="text-red-800">{error || 'Job not found'}</p>
          </div>
        </div>
      </div>
    );
  }

  const results = job.checkpoint?.results || [];
  // Ensure selectedImageIndex is within bounds
  const validImageIndex = selectedImageIndex >= 0 && selectedImageIndex < results.length
    ? selectedImageIndex
    : 0;
  const selectedResult = results[validImageIndex];
  const progress = job.progress || {};

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate(-1)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft size={20} className="text-gray-600" />
            </button>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Chain Processing Results</h1>
              <p className="text-gray-600">Job {jobId?.slice(0, 8)}...</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {job.status === 'processing' && (
              <button
                onClick={() => loadJobData()}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <RefreshCw size={20} className="text-gray-600" />
              </button>
            )}
            <button
              onClick={handleExport}
              disabled={exporting || job.status !== 'completed'}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg transition-colors font-medium"
            >
              {exporting ? (
                <>
                  <Loader size={18} className="animate-spin" />
                  Exporting...
                </>
              ) : (
                <>
                  <Download size={18} />
                  Export Results
                </>
              )}
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-gray-900">Processing Progress</span>
            <span className="text-lg font-bold text-gray-900">
              {progress.percentage || 0}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="bg-blue-600 h-3 rounded-full transition-all duration-300"
              style={{ width: `${progress.percentage || 0}%` }}
            ></div>
          </div>
          <div className="flex items-center justify-between mt-2 text-sm text-gray-600">
            <span>
              {progress.current || 0} / {progress.total || 0} files processed
            </span>
            <span className="capitalize">{job.status}</span>
          </div>
        </div>

        {/* Results Display */}
        {job.status === 'completed' && results.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Image List */}
            <div className="bg-white rounded-lg border border-gray-200 p-4 max-h-96 overflow-y-auto">
              <h2 className="font-semibold text-gray-900 mb-3">Processed Files</h2>
              <div className="space-y-2">
                {results.map((result, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedImageIndex(idx)}
                    className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                      validImageIndex === idx
                        ? 'bg-blue-100 border border-blue-300'
                        : 'border border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {result.status === 'success' ? (
                        <CheckCircle size={16} className="text-green-500 flex-shrink-0" />
                      ) : (
                        <AlertCircle size={16} className="text-red-500 flex-shrink-0" />
                      )}
                      <span className="font-sm font-medium truncate">{result.file}</span>
                    </div>
                    <div className="text-xs text-gray-500">{result.file_path}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Details */}
            <div className="lg:col-span-2 space-y-6">
              {selectedResult && (
                <>
                  {/* Chain Timeline */}
                  {selectedResult.chain_steps && (
                    <div className="bg-white rounded-lg border border-gray-200 p-6">
                      <ChainTimeline
                        steps={selectedResult.chain_steps.map((s: any) => ({
                          step_number: s.step_number,
                          provider: s.provider,
                          input_source: s.input_source,
                          output_preview: s.output?.text?.substring(0, 100) || '',
                          processing_time_ms: s.metadata?.processing_time_ms || 0,
                          confidence: s.output?.confidence || 0,
                          success: !s.error,
                          error: s.error,
                          timestamp: s.metadata?.timestamp,
                        }))}
                        totalTimeMs={selectedResult.metadata?.total_chain_time_ms || 0}
                      />
                    </div>
                  )}

                  {/* Final Output */}
                  <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <h3 className="font-semibold text-gray-900 mb-3">Final Output</h3>
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 max-h-64 overflow-y-auto">
                      <p className="text-gray-700 whitespace-pre-wrap">{selectedResult.text}</p>
                    </div>
                    <div className="mt-3 flex items-center justify-between text-sm text-gray-600">
                      <span>{selectedResult.text.length} characters</span>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(selectedResult.text);
                        }}
                        className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                      >
                        Copy
                      </button>
                    </div>
                  </div>

                  {/* Metadata */}
                  {selectedResult.metadata && (
                    <div className="bg-white rounded-lg border border-gray-200 p-6">
                      <h3 className="font-semibold text-gray-900 mb-3">Metadata</h3>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-600">Processing Time</span>
                          <span className="font-medium text-gray-900">
                            {selectedResult.metadata.processing_time?.toFixed(2)}s
                          </span>
                        </div>
                        {selectedResult.metadata.total_chain_time_ms && (
                          <div className="flex justify-between">
                            <span className="text-gray-600">Total Chain Time</span>
                            <span className="font-medium text-gray-900">
                              {(selectedResult.metadata.total_chain_time_ms / 1000).toFixed(2)}s
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}

        {/* Empty State */}
        {job.status === 'processing' && results.length === 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <Loader size={32} className="animate-spin text-blue-500 mx-auto mb-4" />
            <p className="text-gray-600">Processing files... ({progress.current || 0}/{progress.total || 0})</p>
            {progress.filename && <p className="text-sm text-gray-500 mt-2">{progress.filename}</p>}
          </div>
        )}
      </div>
  );
}
