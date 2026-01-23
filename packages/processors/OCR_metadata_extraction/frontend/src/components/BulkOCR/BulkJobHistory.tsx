import React, { useState, useEffect } from 'react';
import { Download, Eye, Trash2, Clock, CheckCircle, XCircle, RefreshCw, ChevronLeft, ChevronRight, FileText, AlertCircle, TrendingUp, Languages, FolderOpen, Calendar, Upload, FolderPlus } from 'lucide-react';

interface BulkJob {
  id: string;
  job_id: string;
  folder_path: string;
  provider: string;
  languages: string[];
  handwriting: boolean;
  recursive: boolean;
  status: 'processing' | 'completed' | 'error';
  progress: {
    current: number;
    total: number;
    percentage: number;
    filename: string;
  };
  created_at: string;
  completed_at: string | null;
  results?: {
    summary: {
      total_files: number;
      successful: number;
      failed: number;
      statistics: {
        total_characters: number;
        average_confidence: number;
      };
    };
    results_preview?: {
      successful_samples?: any[];
      error_samples?: any[];
    };
    download_url: string;
  };
  error?: string;
}

const BulkJobHistory: React.FC = () => {
  const [jobs, setJobs] = useState<BulkJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<BulkJob | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [archipelagoEnabled, setArchipelagoEnabled] = useState(false);
  const [isPushingToArchipelago, setIsPushingToArchipelago] = useState(false);
  const [showArchipelagoModal, setShowArchipelagoModal] = useState(false);
  const [isUploadingAMI, setIsUploadingAMI] = useState(false);
  const [amiUploadResult, setAmiUploadResult] = useState<any>(null);
  const [archipelagoFormData, setArchipelagoFormData] = useState({
    collectionTitle: '',
    collectionDescription: '',
    tags: ''
  });
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const limit = 10;

  const fetchJobHistory = async (pageNum: number = 1, silent: boolean = false) => {
    try {
      // Only show loading spinner on initial load or manual refresh
      if (!silent) {
        setIsLoading(true);
      }

      const token = localStorage.getItem('access_token');

      const response = await fetch(`/api/bulk/history?page=${pageNum}&limit=${limit}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch job history');
      }

      const data = await response.json();
      setJobs(data.jobs);
      setTotalPages(data.pagination.pages);
      setLastRefresh(new Date());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load job history');
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  };

  const handleDeleteJob = async (jobId: string) => {
    if (!confirm('Are you sure you want to delete this job?')) {
      return;
    }

    try {
      const token = localStorage.getItem('access_token');

      const response = await fetch(`/api/bulk/job/${jobId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to delete job');
      }

      // Refresh the list
      fetchJobHistory(page);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete job');
    }
  };

  const handleCancelJob = async (jobId: string) => {
    if (!confirm('Are you sure you want to cancel this job?')) {
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/bulk/stop/${jobId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to cancel job');
      }

      // Refresh the list
      fetchJobHistory(page);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to cancel job');
    }
  };

  const handleDownloadReport = async (job: BulkJob) => {
    try {
      const token = localStorage.getItem('access_token');
      const downloadUrl = job.results?.download_url;

      if (!downloadUrl) {
        alert('Download URL not available for this job. Reports may still be generating.');
        return;
      }

      if (job.status !== 'completed') {
        alert(`Cannot download: Job is ${job.status}. Wait for processing to complete.`);
        return;
      }

      const response = await fetch(downloadUrl, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const contentType = response.headers.get('content-type');
        let errorMessage = 'Failed to download report';

        if (contentType && contentType.includes('application/json')) {
          try {
            const error = await response.json();
            errorMessage = error.error || errorMessage;
          } catch (e) {
            errorMessage = `HTTP ${response.status}: ${response.statusText}`;
          }
        } else {
          errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        }

        throw new Error(errorMessage);
      }

      const blob = await response.blob();
      if (blob.size === 0) {
        throw new Error('Downloaded file is empty. Reports may not have been generated correctly.');
      }

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ocr_reports_${job.job_id}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to download report';
      alert(errorMessage);
    }
  };

  const checkArchipelagoConnection = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/archipelago/check-connection', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setArchipelagoEnabled(data.enabled === true && data.success === true);
      }
    } catch (err) {
      console.error('Error checking Archipelago connection:', err);
      setArchipelagoEnabled(false);
    }
  };

  const handlePushToArchipelago = async (job: BulkJob) => {
    setSelectedJob(job);
    setArchipelagoFormData({
      collectionTitle: `Bulk OCR - ${job.folder_path.split('/').pop()}`,
      collectionDescription: `Bulk OCR processing results from ${job.folder_path}`,
      tags: `ocr,bulk-processing,${job.provider}`
    });
    setShowArchipelagoModal(true);
  };

  const submitToArchipelago = async () => {
    if (!selectedJob) return;

    try {
      setIsPushingToArchipelago(true);
      const token = localStorage.getItem('access_token');

      const response = await fetch('/api/archipelago/push-bulk-job', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          job_id: selectedJob.job_id,
          collection_title: archipelagoFormData.collectionTitle,
          collection_description: archipelagoFormData.collectionDescription,
          tags: archipelagoFormData.tags.split(',').map(t => t.trim()).filter(t => t),
          include_failed: false
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to push to Archipelago');
      }

      const data = await response.json();
      alert(`Successfully created collection in Archipelago!\n\nCollection ID: ${data.collection_id}\nDocuments created: ${data.created_documents}/${data.total_documents}\n\nURL: ${data.collection_url}`);
      setShowArchipelagoModal(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to push to Archipelago');
    } finally {
      setIsPushingToArchipelago(false);
    }
  };

  const handleUploadToAMISets = async (job: BulkJob) => {
    if (!job.results) {
      alert('No results available for this job');
      return;
    }

    setIsUploadingAMI(true);
    setAmiUploadResult(null);

    try {
      const token = localStorage.getItem('access_token');
      const folderName = job.folder_path ? job.folder_path.split('/').pop() || 'OCR Batch' : 'OCR Batch';
      const collectionTitle = `${folderName} - ${new Date().toLocaleDateString()}`;

      const response = await fetch('/api/archipelago/push-bulk-ami', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          job_id: job.job_id,
          collection_title: collectionTitle,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setAmiUploadResult({
          success: true,
          ami_set_id: data.ami_set_id,
          ami_set_name: data.ami_set_name,
          message: data.message,
          total_documents: data.total_documents,
        });

        // Extract processing URL
        const processingUrl = data.message ? data.message.split('Process it at: ')[1] : null;
        if (processingUrl && confirm('✅ AMI Set created successfully!\n\nOpen Archipelago processing page?')) {
          window.open(processingUrl, '_blank');
        }
      } else {
        throw new Error(data.error || 'Failed to create AMI Set');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to upload to AMI Sets';
      setAmiUploadResult({
        success: false,
        error: errorMessage,
      });
      alert(errorMessage);
    } finally {
      setIsUploadingAMI(false);
    }
  };

  const handleCreateProjectFromJob = async (job: BulkJob) => {
    if (!job.results) {
      alert('No results available for this job');
      return;
    }

    const samples = (job.results.results_preview?.successful_samples || []) as any[];
    if (samples.length === 0) {
      alert('No processed images available for this job');
      return;
    }

    // Create project name with current date and time
    const now = new Date();
    const dateTime = now.toLocaleString('en-US', { 
      year: 'numeric', 
      month: '2-digit', 
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
    const projectName = `New Project ${dateTime}`;
    const zipFileName = job.folder_path ? job.folder_path.split('/').pop() || 'Unknown' : 'Unknown';
    const projectDescription = `Project created from bulk OCR job\nZip File: ${zipFileName}\nFolder: ${job.folder_path}\nProvider: ${job.provider}\nProcessed: ${job.results.summary.successful} files`;

    try {
      setIsCreatingProject(true);
      const token = localStorage.getItem('access_token');

      // Step 1: Create project
      const projectResponse = await fetch('/api/projects', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: projectName,
          description: projectDescription,
        }),
      });

      if (!projectResponse.ok) {
        const errorData = await projectResponse.json();
        throw new Error(errorData.error || 'Failed to create project');
      }

      const projectData = await projectResponse.json();
      const projectId = projectData.project.id;

      // Step 2: Add all processed images to the project
      const imagesAdded: string[] = [];
      let failedImages = 0;

      for (const sample of samples) {
        try {
          const imageResponse = await fetch('/api/ocr/add-to-project', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              project_id: projectId,
              filename: sample.file,
              file_path: sample.file_path,
              ocr_text: sample.text,
              confidence: sample.confidence,
              language: sample.language,
              provider: sample.provider,
            }),
          });

          if (imageResponse.ok) {
            imagesAdded.push(sample.file);
          } else {
            failedImages++;
          }
        } catch (err) {
          failedImages++;
        }
      }

      alert(`✅ Project created successfully!\n\nProject: ${projectData.project.name}\nID: ${projectId}\n\nImages added: ${imagesAdded.length}/${samples.length}`);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create project';
      alert(errorMessage);
    } finally {
      setIsCreatingProject(false);
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'processing':
        return <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'cancelled':
        return <XCircle className="w-5 h-5 text-gray-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const baseClasses = "px-3 py-1 rounded-full text-xs font-semibold";
    switch (status) {
      case 'completed':
        return <span className={`${baseClasses} bg-green-100 text-green-800`}>Completed</span>;
      case 'error':
        return <span className={`${baseClasses} bg-red-100 text-red-800`}>Failed</span>;
      case 'processing':
        return <span className={`${baseClasses} bg-blue-100 text-blue-800`}>Processing</span>;
      case 'cancelled':
        return <span className={`${baseClasses} bg-gray-100 text-gray-800`}>Cancelled</span>;
      default:
        return <span className={`${baseClasses} bg-gray-100 text-gray-800`}>Unknown</span>;
    }
  };

  useEffect(() => {
    fetchJobHistory(page);
    checkArchipelagoConnection();

    // Auto-refresh every 5 seconds to show real-time updates
    if (autoRefresh) {
      const intervalId = setInterval(() => {
        // Silent refresh to avoid flickering
        fetchJobHistory(page, true);
      }, 5000);

      // Cleanup interval on unmount or when autoRefresh changes
      return () => clearInterval(intervalId);
    }
  }, [page, autoRefresh]);

  if (isLoading && jobs.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6">
      <div className="bg-white rounded-lg shadow-lg">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-2xl font-bold text-gray-800">Bulk Processing History</h2>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                  autoRefresh
                    ? 'bg-green-100 text-green-700 hover:bg-green-200'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                title={autoRefresh ? 'Auto-refresh enabled' : 'Auto-refresh disabled'}
              >
                <RefreshCw className={`w-4 h-4 ${autoRefresh ? 'animate-spin' : ''}`} />
                {autoRefresh ? 'Auto' : 'Manual'}
              </button>
              <button
                onClick={() => fetchJobHistory(page)}
                className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh Now
              </button>
            </div>
          </div>
          <div className="text-sm text-gray-500">
            Last updated: {lastRefresh.toLocaleTimeString()}
            {autoRefresh && <span className="ml-2">(updates every 5 seconds)</span>}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mx-6 mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
            {error}
          </div>
        )}

        {/* Job List */}
        <div className="divide-y divide-gray-200">
          {jobs.length === 0 ? (
            <div className="px-6 py-12 text-center text-gray-500">
              No bulk processing jobs found. Start a new bulk OCR process to see it here!
            </div>
          ) : (
            jobs.map((job) => (
              <div key={job.id} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between">
                  {/* Job Info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      {getStatusIcon(job.status)}
                      <h3 className="font-semibold text-gray-800 truncate max-w-md">
                        {job.folder_path}
                      </h3>
                      {getStatusBadge(job.status)}
                    </div>

                    <div className="ml-8 space-y-1 text-sm text-gray-600">
                      <div className="flex gap-4">
                        <span><strong>Provider:</strong> {job.provider}</span>
                        <span><strong>Languages:</strong> {job.languages.join(', ')}</span>
                      </div>
                      <div>
                        <strong>Created:</strong> {formatDate(job.created_at)}
                      </div>
                      {job.completed_at && (
                        <div>
                          <strong>Completed:</strong> {formatDate(job.completed_at)}
                        </div>
                      )}

                      {/* Progress Bar for Processing Jobs */}
                      {job.status === 'processing' && (
                        <div className="mt-2">
                          <div className="flex justify-between text-xs mb-1">
                            <span>{job.progress.filename}</span>
                            <span>{job.progress.percentage}%</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${job.progress.percentage}%` }}
                            />
                          </div>
                        </div>
                      )}

                      {/* Summary for Completed Jobs */}
                      {job.status === 'completed' && job.results && (
                        <div className="mt-2 flex gap-4 text-xs">
                          <span className="text-green-600">
                            <strong>Success:</strong> {job.results.summary.successful}/{job.results.summary.total_files}
                          </span>
                          {job.results.summary.failed > 0 && (
                            <span className="text-red-600">
                              <strong>Failed:</strong> {job.results.summary.failed}
                            </span>
                          )}
                          <span>
                            <strong>Avg Confidence:</strong> {(job.results.summary.statistics.average_confidence * 100).toFixed(1)}%
                          </span>
                        </div>
                      )}

                      {/* Error Message */}
                      {job.status === 'error' && job.error && (
                        <div className="mt-2 text-red-600 text-xs">
                          <strong>Error:</strong> {job.error}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 ml-4">
                    {job.status === 'completed' && job.results && (
                      <>
                        <button
                          onClick={() => setSelectedJob(job)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="View Details"
                        >
                          <Eye className="w-5 h-5" />
                        </button>
                        <button
                          onClick={() => handleDownloadReport(job)}
                          className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                          title="Download Report"
                        >
                          <Download className="w-5 h-5" />
                        </button>
                        {archipelagoEnabled && (
                          <>
                            <button
                              onClick={() => handlePushToArchipelago(job)}
                              className="p-2 text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                              title="Push to Archipelago Commons"
                            >
                              <Upload className="w-5 h-5" />
                            </button>
                            <button
                              onClick={() => handleUploadToAMISets(job)}
                              disabled={isUploadingAMI}
                              className="p-2 text-indigo-600 hover:bg-indigo-50 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
                              title="Upload to Archipelago (AMI Sets)"
                            >
                              <Upload className="w-5 h-5" />
                            </button>
                          </>
                        )}
                        <button
                          onClick={() => handleCreateProjectFromJob(job)}
                          disabled={isCreatingProject || !job.results?.results_preview?.successful_samples || job.results.results_preview.successful_samples.length === 0}
                          className="p-2 text-orange-600 hover:bg-orange-50 disabled:text-gray-400 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
                          title={!job.results?.results_preview?.successful_samples || job.results.results_preview.successful_samples.length === 0 ? "No processed images available" : "Create Project from Job"}
                        >
                          <FolderPlus className="w-5 h-5" />
                        </button>
                      </>
                    )}
                    {job.status === 'processing' && (
                      <button
                        onClick={() => handleCancelJob(job.job_id)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Cancel Job"
                      >
                        <XCircle className="w-5 h-5" />
                      </button>
                    )}
                    <button
                      onClick={() => handleDeleteJob(job.job_id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete Job"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
            <div className="text-sm text-gray-600">
              Page {page} of {totalPages}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-2 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* AMI Upload Result Notification */}
      {amiUploadResult && (
        <div className={`fixed top-4 right-4 p-4 rounded-lg shadow-lg max-w-sm z-40 ${
          amiUploadResult.success
            ? 'bg-green-50 border border-green-200'
            : 'bg-red-50 border border-red-200'
        }`}>
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1">
              {amiUploadResult.success ? (
                <>
                  <h3 className="font-semibold text-green-900">AMI Set Created</h3>
                  <p className="text-sm text-green-800 mt-1">
                    <strong>Name:</strong> {amiUploadResult.ami_set_name}
                  </p>
                  <p className="text-sm text-green-800">
                    <strong>ID:</strong> {amiUploadResult.ami_set_id}
                  </p>
                  <p className="text-sm text-green-800">
                    <strong>Documents:</strong> {amiUploadResult.total_documents}
                  </p>
                </>
              ) : (
                <>
                  <h3 className="font-semibold text-red-900">Upload Failed</h3>
                  <p className="text-sm text-red-800 mt-1">{amiUploadResult.error}</p>
                </>
              )}
            </div>
            <button
              onClick={() => setAmiUploadResult(null)}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Job Details Modal */}
      {selectedJob && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full my-8">
            {/* Header */}
            <div className="px-6 py-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white flex items-center justify-between rounded-t-lg">
              <div className="flex items-center gap-3">
                {getStatusIcon(selectedJob.status)}
                <div>
                  <h3 className="text-xl font-bold">Job Details</h3>
                  <p className="text-sm text-blue-100">Job ID: {selectedJob.job_id}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedJob(null)}
                className="text-white hover:bg-blue-800 p-2 rounded-lg transition-colors"
                title="Close"
              >
                ✕
              </button>
            </div>

            <div className="px-6 py-6 max-h-[calc(100vh-250px)] overflow-y-auto">
              {/* Status Badge */}
              <div className="mb-6">
                {getStatusBadge(selectedJob.status)}
              </div>

              {/* Basic Information */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <div className="flex items-center gap-2 mb-3">
                    <FolderOpen className="w-5 h-5 text-blue-600" />
                    <h4 className="font-semibold text-gray-800">Source Information</h4>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="text-gray-600">Folder Path:</span>
                      <p className="font-mono text-xs bg-white p-2 rounded mt-1 break-all">{selectedJob.folder_path}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-gray-600">Recursive:</span>
                      <span className="font-semibold">{selectedJob.recursive ? 'Yes' : 'No'}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <div className="flex items-center gap-2 mb-3">
                    <Languages className="w-5 h-5 text-green-600" />
                    <h4 className="font-semibold text-gray-800">OCR Configuration</h4>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="text-gray-600">Provider:</span>
                      <span className="ml-2 font-semibold capitalize">{selectedJob.provider}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Languages:</span>
                      <span className="ml-2 font-semibold">{selectedJob.languages.join(', ')}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Handwriting:</span>
                      <span className="ml-2 font-semibold">{selectedJob.handwriting ? 'Enabled' : 'Disabled'}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Timestamps */}
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 mb-6">
                <div className="flex items-center gap-2 mb-3">
                  <Calendar className="w-5 h-5 text-purple-600" />
                  <h4 className="font-semibold text-gray-800">Timeline</h4>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Created:</span>
                    <p className="font-semibold mt-1">{formatDate(selectedJob.created_at)}</p>
                  </div>
                  {selectedJob.completed_at && (
                    <>
                      <div>
                        <span className="text-gray-600">Completed:</span>
                        <p className="font-semibold mt-1">{formatDate(selectedJob.completed_at)}</p>
                      </div>
                      <div>
                        <span className="text-gray-600">Duration:</span>
                        <p className="font-semibold mt-1">
                          {(() => {
                            const start = new Date(selectedJob.created_at);
                            const end = new Date(selectedJob.completed_at);
                            const diffMs = end.getTime() - start.getTime();
                            const diffMins = Math.floor(diffMs / 60000);
                            const diffSecs = Math.floor((diffMs % 60000) / 1000);
                            return diffMins > 0 ? `${diffMins}m ${diffSecs}s` : `${diffSecs}s`;
                          })()}
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Processing Progress */}
              {selectedJob.status === 'processing' && (
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200 mb-6">
                  <div className="flex items-center gap-2 mb-3">
                    <RefreshCw className="w-5 h-5 text-blue-600 animate-spin" />
                    <h4 className="font-semibold text-gray-800">Processing Progress</h4>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-700">{selectedJob.progress.filename}</span>
                      <span className="font-semibold">{selectedJob.progress.current} / {selectedJob.progress.total}</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div
                        className="bg-blue-600 h-3 rounded-full transition-all duration-300 flex items-center justify-end pr-2"
                        style={{ width: `${selectedJob.progress.percentage}%` }}
                      >
                        <span className="text-xs text-white font-semibold">{selectedJob.progress.percentage}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Error Information */}
              {selectedJob.status === 'error' && selectedJob.error && (
                <div className="bg-red-50 p-4 rounded-lg border border-red-200 mb-6">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertCircle className="w-5 h-5 text-red-600" />
                    <h4 className="font-semibold text-red-800">Error Details</h4>
                  </div>
                  <p className="text-sm text-red-700 font-mono bg-red-100 p-3 rounded">{selectedJob.error}</p>
                </div>
              )}

              {/* Results Summary */}
              {selectedJob.status === 'completed' && selectedJob.results && (
                <>
                  <div className="bg-green-50 p-4 rounded-lg border border-green-200 mb-6">
                    <div className="flex items-center gap-2 mb-4">
                      <TrendingUp className="w-5 h-5 text-green-600" />
                      <h4 className="font-semibold text-gray-800">Processing Summary</h4>
                    </div>

                    {/* Statistics Cards */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                      <div className="bg-white p-4 rounded-lg text-center">
                        <div className="text-3xl font-bold text-blue-600">{selectedJob.results.summary.total_files}</div>
                        <div className="text-xs text-gray-600 mt-1">Total Files</div>
                      </div>
                      <div className="bg-white p-4 rounded-lg text-center">
                        <div className="text-3xl font-bold text-green-600">{selectedJob.results.summary.successful}</div>
                        <div className="text-xs text-gray-600 mt-1">Successful</div>
                      </div>
                      <div className="bg-white p-4 rounded-lg text-center">
                        <div className="text-3xl font-bold text-red-600">{selectedJob.results.summary.failed}</div>
                        <div className="text-xs text-gray-600 mt-1">Failed</div>
                      </div>
                      <div className="bg-white p-4 rounded-lg text-center">
                        <div className="text-3xl font-bold text-purple-600">
                          {((selectedJob.results.summary.successful / selectedJob.results.summary.total_files) * 100).toFixed(0)}%
                        </div>
                        <div className="text-xs text-gray-600 mt-1">Success Rate</div>
                      </div>
                    </div>

                    {/* Detailed Statistics */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="bg-white p-3 rounded-lg">
                        <div className="text-sm text-gray-600">Total Characters Extracted</div>
                        <div className="text-2xl font-bold text-gray-800">
                          {selectedJob.results.summary.statistics.total_characters.toLocaleString()}
                        </div>
                      </div>
                      <div className="bg-white p-3 rounded-lg">
                        <div className="text-sm text-gray-600">Average Confidence</div>
                        <div className="text-2xl font-bold text-gray-800">
                          {(selectedJob.results.summary.statistics.average_confidence * 100).toFixed(1)}%
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Sample Results */}
                  {selectedJob.results.results_preview && (
                    <div className="space-y-4">
                      {/* Successful Samples */}
                      {selectedJob.results.results_preview.successful_samples && selectedJob.results.results_preview.successful_samples.length > 0 && (
                        <div className="bg-white border border-gray-200 rounded-lg">
                          <div className="px-4 py-3 bg-green-50 border-b border-green-200 rounded-t-lg">
                            <div className="flex items-center gap-2">
                              <CheckCircle className="w-5 h-5 text-green-600" />
                              <h4 className="font-semibold text-gray-800">
                                Successful Files ({selectedJob.results.results_preview.successful_samples.length})
                              </h4>
                            </div>
                          </div>
                          <div className="max-h-96 overflow-y-auto">
                            {selectedJob.results.results_preview.successful_samples.slice(0, 10).map((result: any, idx: number) => (
                              <div key={idx} className="p-4 border-b border-gray-100 hover:bg-gray-50">
                                <div className="flex items-start justify-between mb-2">
                                  <div className="flex items-center gap-2">
                                    <FileText className="w-4 h-4 text-blue-600" />
                                    <span className="font-semibold text-sm text-gray-800">{result.file}</span>
                                  </div>
                                  <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                                    {(result.confidence * 100).toFixed(1)}% confidence
                                  </span>
                                </div>
                                <div className="text-xs text-gray-600 mb-2">
                                  <span className="mr-3">Language: {result.language}</span>
                                  <span className="mr-3">Provider: {result.provider}</span>
                                  <span>Length: {result.text_length} chars</span>
                                </div>
                                {result.text && (
                                  <div className="bg-gray-50 p-2 rounded text-xs font-mono max-h-20 overflow-y-auto">
                                    {result.text.substring(0, 200)}{result.text.length > 200 ? '...' : ''}
                                  </div>
                                )}
                              </div>
                            ))}
                            {selectedJob.results.results_preview.successful_samples.length > 10 && (
                              <div className="p-3 text-center text-sm text-gray-600 bg-gray-50">
                                ... and {selectedJob.results.results_preview.successful_samples.length - 10} more files
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Error Samples */}
                      {selectedJob.results.results_preview.error_samples && selectedJob.results.results_preview.error_samples.length > 0 && (
                        <div className="bg-white border border-gray-200 rounded-lg">
                          <div className="px-4 py-3 bg-red-50 border-b border-red-200 rounded-t-lg">
                            <div className="flex items-center gap-2">
                              <XCircle className="w-5 h-5 text-red-600" />
                              <h4 className="font-semibold text-gray-800">
                                Failed Files ({selectedJob.results.results_preview.error_samples.length})
                              </h4>
                            </div>
                          </div>
                          <div className="max-h-64 overflow-y-auto">
                            {selectedJob.results.results_preview.error_samples.slice(0, 10).map((error: any, idx: number) => (
                              <div key={idx} className="p-4 border-b border-gray-100 hover:bg-gray-50">
                                <div className="flex items-center gap-2 mb-2">
                                  <AlertCircle className="w-4 h-4 text-red-600" />
                                  <span className="font-semibold text-sm text-gray-800">{error.file}</span>
                                </div>
                                <div className="text-xs text-red-600 bg-red-50 p-2 rounded font-mono">
                                  {error.error}
                                </div>
                              </div>
                            ))}
                            {selectedJob.results.results_preview.error_samples.length > 10 && (
                              <div className="p-3 text-center text-sm text-gray-600 bg-gray-50">
                                ... and {selectedJob.results.results_preview.error_samples.length - 10} more errors
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end gap-2 rounded-b-lg">
              {selectedJob.status === 'completed' && selectedJob.results && (
                <button
                  onClick={() => handleDownloadReport(selectedJob)}
                  className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 flex items-center gap-2 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Download Full Report
                </button>
              )}
              <button
                onClick={() => setSelectedJob(null)}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Archipelago Push Modal */}
      {showArchipelagoModal && selectedJob && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full">
            {/* Header */}
            <div className="px-6 py-4 bg-purple-600 text-white flex items-center justify-between rounded-t-lg">
              <div className="flex items-center gap-3">
                <Upload className="w-6 h-6" />
                <h3 className="text-xl font-bold">Push to Archipelago Commons</h3>
              </div>
              <button
                onClick={() => setShowArchipelagoModal(false)}
                className="text-white hover:bg-purple-700 p-2 rounded-lg transition-colors"
                disabled={isPushingToArchipelago}
              >
                ✕
              </button>
            </div>

            {/* Content */}
            <div className="px-6 py-6">
              <p className="text-gray-600 mb-6">
                Create a collection in Archipelago Commons with all successfully processed documents from this bulk job.
              </p>

              {/* Form */}
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Collection Title *
                  </label>
                  <input
                    type="text"
                    value={archipelagoFormData.collectionTitle}
                    onChange={(e) => setArchipelagoFormData({ ...archipelagoFormData, collectionTitle: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="Enter collection title"
                    disabled={isPushingToArchipelago}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description
                  </label>
                  <textarea
                    value={archipelagoFormData.collectionDescription}
                    onChange={(e) => setArchipelagoFormData({ ...archipelagoFormData, collectionDescription: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    rows={3}
                    placeholder="Enter collection description"
                    disabled={isPushingToArchipelago}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tags (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={archipelagoFormData.tags}
                    onChange={(e) => setArchipelagoFormData({ ...archipelagoFormData, tags: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="e.g., ocr, documents, archive"
                    disabled={isPushingToArchipelago}
                  />
                </div>

                {/* Job Info */}
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <h4 className="font-semibold text-gray-800 mb-2">Job Information</h4>
                  <div className="space-y-1 text-sm text-gray-600">
                    <div><strong>Folder:</strong> {selectedJob.folder_path}</div>
                    <div><strong>Provider:</strong> {selectedJob.provider}</div>
                    {selectedJob.results && (
                      <>
                        <div><strong>Total Files:</strong> {selectedJob.results.summary.total_files}</div>
                        <div><strong>Successful:</strong> {selectedJob.results.summary.successful}</div>
                        <div><strong>Failed:</strong> {selectedJob.results.summary.failed}</div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end gap-3 rounded-b-lg">
              <button
                onClick={() => setShowArchipelagoModal(false)}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
                disabled={isPushingToArchipelago}
              >
                Cancel
              </button>
              <button
                onClick={submitToArchipelago}
                disabled={!archipelagoFormData.collectionTitle || isPushingToArchipelago}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                {isPushingToArchipelago ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Pushing...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    Push to Archipelago
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BulkJobHistory;
