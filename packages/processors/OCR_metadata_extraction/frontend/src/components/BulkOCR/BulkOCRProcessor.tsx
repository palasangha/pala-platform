import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { Play, Download, FileText, BarChart3, FolderOpen, Zap, LogOut, ChevronRight, History, Activity, Server } from 'lucide-react';
import BulkJobHistory from './BulkJobHistory';

interface ProcessingResult {
  file: string;
  file_path: string;
  confidence: number;
  text: string;
  text_length: number;
  language: string;
  provider: string;
}

interface ErrorResult {
  file: string;
  error: string;
}

interface BulkProcessingState {
  folderPath: string;
  provider: string;
  languages: string[];
  handwriting: boolean;
  recursive: boolean;
  exportFormats: string[];
  isProcessing: boolean;
  isCreatingProject: boolean;
  progress: {
    current: number;
    total: number;
    percentage: number;
    filename: string;
  };
  results: {
    summary: {
      total_files: number;
      successful: number;
      failed: number;
      folder_path: string;
      processed_at: string;
      statistics: {
        total_characters: number;
        average_confidence: number;
        average_words: number;
        average_blocks: number;
        languages: string[];
      };
    };
    results_preview: {
      total_results: number;
      successful_samples: ProcessingResult[];
      error_samples: ErrorResult[];
    };
    download_url: string;
    report_files: {
      json: string;
      csv: string;
      text: string;
      zip: string;
    };
  } | null;
  error: string | null;
}

interface FolderBrowserState {
  isOpen: boolean;
  currentPath: string;
  folders: Array<{ name: string; path: string; file_count: number; is_dir: boolean }>;
  files: Array<{ name: string; path: string; size: number; is_dir: boolean }>;
  parentPath: string | null;
  isLoading: boolean;
  error: string | null;
}

const BulkOCRProcessor: React.FC = () => {
  const navigate = useNavigate();
  const updateAccessToken = useAuthStore((state) => state.updateAccessToken);
  const [isUploadingToArchipelago, setIsUploadingToArchipelago] = useState(false);
  const [archipelagoResult, setArchipelagoResult] = useState<{
    success: boolean;
    ami_set_id?: number;
    ami_set_name?: string;
    message?: string;
    total_documents?: number;
    error?: string;
    job_id?: string;
    status?: 'processing' | 'complete';
  } | null>(null);

  // Helper function to refresh token when expired
  const refreshAccessToken = async (): Promise<string | null> => {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        throw new Error('Failed to refresh token');
      }

      const data = await response.json();
      // Update both localStorage and auth store
      updateAccessToken(data.access_token);
      return data.access_token;
    } catch (error) {
      console.error('Token refresh failed:', error);
      // Clear auth on failure
      useAuthStore.getState().clearAuth();
      navigate('/login');
      return null;
    }
  };

  // Helper function to make authenticated fetch with auto token refresh
  const authenticatedFetch = async (url: string, options: RequestInit = {}): Promise<Response> => {
    const token = localStorage.getItem('access_token');

    console.log(`[FETCH] Starting request to: ${url}`);
    console.log(`[FETCH] Method: ${options.method || 'GET'}`);
    console.log(`[FETCH] Has token: ${!!token}`);

    const fetchOptions = {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${token}`,
      },
    };

    try {
      console.log(`[FETCH] Sending request with headers:`, Object.keys(fetchOptions.headers || {}));
      let response = await fetch(url, fetchOptions);

      console.log(`[FETCH] Response status: ${response.status}`);
      console.log(`[FETCH] Response ok: ${response.ok}`);
      console.log(`[FETCH] Response headers:`, {
        'content-type': response.headers.get('content-type'),
        'content-length': response.headers.get('content-length'),
      });

      // If 401, try to refresh token and retry
      if (response.status === 401) {
        console.warn(`[FETCH] Got 401 - attempting token refresh`);
        const newToken = await refreshAccessToken();
        if (newToken) {
          console.log(`[FETCH] Token refreshed, retrying request`);
          fetchOptions.headers = {
            ...fetchOptions.headers,
            Authorization: `Bearer ${newToken}`,
          };
          response = await fetch(url, fetchOptions);
          console.log(`[FETCH] Retry response status: ${response.status}`);
        }
      }

      return response;
    } catch (error) {
      console.error(`[FETCH] Network error for ${url}:`, error);
      console.error(`[FETCH] Error type:`, error instanceof TypeError ? 'TypeError' : typeof error);
      console.error(`[FETCH] Error message:`, (error as Error).message);
      if (error instanceof TypeError) {
        console.error(`[FETCH] This is likely a network/CORS/SSL error`);
      }
      throw error;
    }
  };

  const [showHistory, setShowHistory] = useState(false);

  const [state, setState] = useState<BulkProcessingState>({
    folderPath: '',
    provider: 'chrome_lens',
    languages: ['en'],
    handwriting: false,
    recursive: true,
    exportFormats: ['json', 'csv', 'text'],
    isProcessing: false,
    isCreatingProject: false,
    progress: {
      current: 0,
      total: 0,
      percentage: 0,
      filename: '',
    },
    results: null,
    error: null,
  });

  const [currentJobId, setCurrentJobId] = useState<string | null>(null);

  const [availableProviders, setAvailableProviders] = useState<Array<{
    name: string;
    available: boolean;
    display_name: string;
  }> | null>(null);

  const [browserState, setBrowserState] = useState<FolderBrowserState>({
    isOpen: false,
    currentPath: '',
    folders: [],
    files: [],
    parentPath: null,
    isLoading: false,
    error: null,
  });

  useEffect(() => {
    const loadAvailableProviders = async () => {
      try {
        const response = await authenticatedFetch('/api/ocr/providers');
        if (response.ok) {
          const data = await response.json();
          setAvailableProviders(data.providers || []);
          console.log('[PROVIDERS] Loaded providers:', data.providers);
        } else {
          console.error('[PROVIDERS] Failed to load providers:', response.status);
        }
      } catch (error) {
        console.error('[PROVIDERS] Error loading providers:', error);
      }
    };

    loadAvailableProviders();
  }, []);

  const handleFolderPathChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setState({ ...state, folderPath: e.target.value, error: null });
  };

  const handleProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setState({ ...state, provider: e.target.value });
  };

  const handleLanguageToggle = (lang: string) => {
    const languages = state.languages.includes(lang)
      ? state.languages.filter((l) => l !== lang)
      : [...state.languages, lang];
    setState({ ...state, languages });
  };

  const handleFormatToggle = (format: string) => {
    const formats = state.exportFormats.includes(format)
      ? state.exportFormats.filter((f) => f !== format)
      : [...state.exportFormats, format];
    setState({ ...state, exportFormats: formats });
  };

  const handleOpenBrowser = async () => {
    setBrowserState({
      ...browserState,
      isOpen: true,
      isLoading: true,
      currentPath: '',
      error: null,
    });

    try {
      const response = await authenticatedFetch('/api/bulk/browse-folders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path: '' }),
      });

      if (!response.ok) {
        throw new Error('Failed to load folders');
      }

      const data = await response.json();
      setBrowserState({
        ...browserState,
        isOpen: true,
        isLoading: false,
        currentPath: data.current_path,
        folders: data.folders || [],
        files: data.files || [],
        parentPath: data.parent_path,
        error: null,
      });
    } catch (err) {
      setBrowserState({
        ...browserState,
        isOpen: true,
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to load folders',
      });
    }
  };

  const handleNavigateFolder = async (path: string) => {
    setBrowserState({ ...browserState, isLoading: true });

    try {
      const response = await authenticatedFetch('/api/bulk/browse-folders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path }),
      });

      if (!response.ok) {
        throw new Error('Failed to load folder');
      }

      const data = await response.json();
      setBrowserState({
        ...browserState,
        isLoading: false,
        currentPath: data.current_path,
        folders: data.folders || [],
        files: data.files || [],
        parentPath: data.parent_path,
        error: null,
      });
    } catch (err) {
      setBrowserState({
        ...browserState,
        isLoading: false,
        error: err instanceof Error ? err.message : 'Failed to load folder',
      });
    }
  };

  const handleSelectFolder = (path: string) => {
    setState({ ...state, folderPath: path, error: null });
    setBrowserState({ ...browserState, isOpen: false });
  };

  const handleCloseBrowser = () => {
    setBrowserState({ ...browserState, isOpen: false });
  };

  const pollProgress = async (jobId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await authenticatedFetch(`/api/bulk/progress/${jobId}`);

        if (!response.ok) {
          throw new Error('Failed to fetch progress');
        }

        const data = await response.json();

        // Update progress
        setState((prevState) => ({
          ...prevState,
          progress: data.progress,
        }));

        // Check if completed
        if (data.status === 'completed') {
          clearInterval(pollInterval);
          setState((prevState) => ({
            ...prevState,
            isProcessing: false,
            results: data.results,
            progress: {
              current: data.progress.total,
              total: data.progress.total,
              percentage: 100,
              filename: 'Completed',
            },
          }));
        }

        // Check if error
        if (data.status === 'error') {
          clearInterval(pollInterval);
          setState((prevState) => ({
            ...prevState,
            isProcessing: false,
            error: data.error || 'Processing failed',
          }));
        }
      } catch (err) {
        clearInterval(pollInterval);
        setState((prevState) => ({
          ...prevState,
          isProcessing: false,
          error: err instanceof Error ? err.message : 'Failed to fetch progress',
        }));
      }
    }, 1000); // Poll every 1 second
  };

  const handleProcessing = async () => {
    if (!state.folderPath.trim()) {
      setState({ ...state, error: 'Please enter a folder path' });
      return;
    }

    setState({
      ...state,
      isProcessing: true,
      error: null,
      progress: {
        current: 0,
        total: 0,
        percentage: 0,
        filename: 'Initializing...',
      }
    });

    try {
      const response = await authenticatedFetch('/api/bulk/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          folder_path: state.folderPath,
          recursive: state.recursive,
          provider: state.provider,
          languages: state.languages,
          handwriting: state.handwriting,
          export_formats: state.exportFormats,
        }),
      });

      if (!response.ok) {
        let error;
        try {
          error = await response.json();
        } catch (e) {
          error = { error: `HTTP ${response.status}: ${response.statusText}` };
        }
        throw new Error(error.error || 'Processing failed');
      }

      let data;
      try {
        data = await response.json();
      } catch (e) {
        throw new Error('Invalid response from server');
      }

      // Start polling for progress
      if (data.job_id) {
        setCurrentJobId(data.job_id);
        pollProgress(data.job_id);
      } else {
        throw new Error('No job ID received from server');
      }
    } catch (err) {
      setState({
        ...state,
        isProcessing: false,
        error: err instanceof Error ? err.message : 'Unknown error occurred',
      });
    }
  };

  const handleDownload = async () => {
    if (!state.results) {
      setState({
        ...state,
        error: 'No results available. Please complete the processing first.',
      });
      return;
    }

    if (!state.results.download_url) {
      setState({
        ...state,
        error: 'Download URL not available. Reports may still be generating. Please wait a moment and try again.',
      });
      return;
    }

    try {
      setState({ ...state, error: null });
      const response = await authenticatedFetch(state.results.download_url);

      if (!response.ok) {
        const contentType = response.headers.get('content-type');
        let errorMessage = 'Download failed';

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
      const link = document.createElement('a');
      link.href = url;
      link.download = `ocr_reports_${new Date().getTime()}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Download failed for unknown reason';
      setState({
        ...state,
        error: errorMessage,
      });
    }
  };

  const handleDownloadSampleResults = async () => {
    if (!currentJobId) return;

    try {
      setState({ ...state, error: null });

      const response = await authenticatedFetch(
        `/api/bulk/sample-results/${currentJobId}?sample_size=${state.progress.current}`
      );

      if (!response.ok) {
        const contentType = response.headers.get('content-type');
        let errorMessage = 'Sample results download failed';

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
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `sample_results_${currentJobId}_${new Date().getTime()}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setState({
        ...state,
        error: err instanceof Error ? err.message : 'Sample results download failed',
      });
    }
  };

  const handleUploadToArchipelago = async (jobId: string) => {
    console.log(`[UPLOAD] Starting Archipelago upload for job: ${jobId}`);
    
    if (!state.results || state.results.results_preview.successful_samples.length === 0) {
      console.warn(`[UPLOAD] No successful results found`);
      setState({ ...state, error: 'No successful results to upload' });
      return;
    }

    setIsUploadingToArchipelago(true);
    setArchipelagoResult(null);
    setState({ ...state, error: null });

    try {
      // Validate that results exist before accessing properties
      if (!state.results || !state.results.summary) {
        console.error(`[UPLOAD] Results data missing`);
        setState({ ...state, error: 'Results data missing. Please try again.' });
        setIsUploadingToArchipelago(false);
        return;
      }

      // Generate collection title, with fallback if folder_path is missing
      const folderName = state.results.summary.folder_path
        ? state.results.summary.folder_path.split('/').pop() || 'OCR Batch'
        : 'OCR Batch';
      const collectionTitle = `${folderName} - ${new Date().toLocaleDateString()}`;

      console.log(`[UPLOAD] Collection title: ${collectionTitle}`);
      console.log(`[UPLOAD] Job ID: ${jobId}`);
      console.log(`[UPLOAD] Successful samples: ${state.results.results_preview.successful_samples.length}`);

      console.log(`[UPLOAD] Sending POST request to /api/archipelago/push-bulk-ami`);
      const response = await authenticatedFetch('/api/archipelago/push-bulk-ami', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          job_id: jobId,
          collection_title: collectionTitle,
        }),
      });

      console.log(`[UPLOAD] Response received: ${response.status}`);
      console.log(`[UPLOAD] Response ok: ${response.ok}`);

      const data = await response.json();
      console.log(`[UPLOAD] Response data:`, data);

      if (data.success) {
        console.log(`[UPLOAD] Upload request accepted (202)`);
        // Background task started - show message and polling
        setArchipelagoResult({
          success: true,
          message: 'AMI Set creation started. Processing in background...',
          job_id: data.job_id,
          status: 'processing',
        });

        console.log(`[UPLOAD] Starting polling interval for job ${jobId}`);
        // Poll for completion
        const pollInterval = setInterval(async () => {
          try {
            console.log(`[POLL] Checking status for job ${jobId}`);
            const statusResponse = await authenticatedFetch(`/api/bulk/status/${jobId}`);

            console.log(`[POLL] Status response code: ${statusResponse.status}`);

            if (statusResponse.ok) {
              const statusData = await statusResponse.json();
              console.log(`[POLL] Status data received:`, statusData);
              
              if (statusData.archipelago_result) {
                console.log(`[POLL] ✅ Upload complete!`, statusData.archipelago_result);
                clearInterval(pollInterval);
                setArchipelagoResult({
                  success: true,
                  ami_set_id: statusData.archipelago_result.ami_set_id,
                  ami_set_name: statusData.archipelago_result.name,
                  message: statusData.archipelago_result.message,
                  total_documents: statusData.archipelago_result.total_documents,
                  status: 'complete',
                });

                // Open processing page if available
                const processingUrl = statusData.archipelago_result.message?.split('Process it at: ')[1];
                if (processingUrl && confirm('✅ AMI Set created successfully!\n\nOpen Archipelago processing page?')) {
                  window.open(processingUrl, '_blank');
                }

                setIsUploadingToArchipelago(false);
              } else {
                console.log(`[POLL] Still uploading... status: ${statusData.status}`);
              }
            } else {
              console.error(`[POLL] ❌ Bad response status: ${statusResponse.status}`);
              console.error(`[POLL] Response text:`, await statusResponse.text().catch(() => 'Could not read response'));
            }
          } catch (err) {
            console.error('[POLL] ❌ Error polling for result:', err);
            console.error('[POLL] Error details:', (err as Error).message);
          }
        }, 5000); // Poll every 5 seconds

        console.log(`[UPLOAD] Polling started, will timeout in 30 minutes`);
        // Timeout after 30 minutes
        setTimeout(() => {
          clearInterval(pollInterval);
          console.warn('[UPLOAD] ⏱️ Polling timeout - 30 minutes elapsed');
          setIsUploadingToArchipelago(false);
          setState({
            ...state,
            error: 'Archipelago upload timeout - please check server logs'
          });
        }, 30 * 60 * 1000);

      } else if (data.error) {
        // Immediate error
        console.error(`[UPLOAD] ❌ Error from server:`, data.error);
        setArchipelagoResult({
          success: false,
          error: data.error || 'Upload failed',
        });
        setState({
          ...state,
          error: `Archipelago upload failed: ${data.error || 'Unknown error'}`,
        });
        setIsUploadingToArchipelago(false);
      } else {
        console.error(`[UPLOAD] ❌ Unexpected response format:`, data);
        setArchipelagoResult({
          success: false,
          error: 'Unknown response from server',
        });
        setIsUploadingToArchipelago(false);
      }
    } catch (err) {
      console.error(`[UPLOAD] ❌ CRITICAL ERROR:`, err);
      console.error(`[UPLOAD] Error type:`, err instanceof TypeError ? 'TypeError (Network/Fetch Error)' : typeof err);
      console.error(`[UPLOAD] Error message:`, (err as Error).message);
      console.error(`[UPLOAD] Stack trace:`, (err as Error).stack);
      
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      setArchipelagoResult({
        success: false,
        error: errorMessage,
      });
      setState({
        ...state,
        error: `Archipelago upload error: ${errorMessage}`,
      });
      setIsUploadingToArchipelago(false);
    }
  };

  const handleCreateProject = async () => {
    if (!state.results || state.results.results_preview.successful_samples.length === 0) {
      setState({ ...state, error: 'No successful results to create project from' });
      return;
    }

    setState({ ...state, isCreatingProject: true, error: null });

    try {
      // Create project with a descriptive name
      const projectName = `Bulk OCR - ${new Date().toLocaleString()}`;
      const projectResponse = await authenticatedFetch('/api/projects', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: projectName,
          description: `Bulk processed from ${state.results.summary.folder_path}. ${state.results.summary.successful} files processed successfully.`,
        }),
      });

      if (!projectResponse.ok) {
        throw new Error('Failed to create project');
      }

      const projectData = await projectResponse.json();
      const projectId = projectData.project.id;

      // Upload all successful files to the project
      const uploadPromises = state.results.results_preview.successful_samples.map(async (result) => {
        try {
          // Fetch the original file
          const fileResponse = await authenticatedFetch(
            `/api/bulk/file/${encodeURIComponent(result.file)}?folder=${encodeURIComponent(state.results!.summary.folder_path)}`
          );

          if (!fileResponse.ok) {
            console.error(`Failed to fetch file: ${result.file}`);
            return null;
          }

          const fileBlob = await fileResponse.blob();
          const formData = new FormData();
          formData.append('file', fileBlob, result.file);

          // Include the OCR text from bulk processing
          if (result.text) {
            formData.append('ocr_text', result.text);
          }

          // Upload to project with OCR text
          const uploadResponse = await authenticatedFetch(`/api/projects/${projectId}/images`, {
            method: 'POST',
            body: formData,
          });

          if (!uploadResponse.ok) {
            console.error(`Failed to upload file: ${result.file}`);
            return null;
          }

          return await uploadResponse.json();
        } catch (error) {
          console.error(`Error uploading ${result.file}:`, error);
          return null;
        }
      });

      await Promise.all(uploadPromises);

      // Save bulk processing results to project folder
      try {
        const bulkResultsResponse = await authenticatedFetch(`/api/projects/${projectId}/bulk-results`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(state.results),
        });

        if (!bulkResultsResponse.ok) {
          console.warn('Failed to save bulk results to project folder');
        }
      } catch (error) {
        console.warn('Error saving bulk results:', error);
      }

      // Navigate to the project page
      navigate(`/projects/${projectId}`);
    } catch (err) {
      setState({
        ...state,
        isCreatingProject: false,
        error: err instanceof Error ? err.message : 'Failed to create project',
      });
    }
  };

  const { user, clearAuth } = useAuthStore();

  const handleLogout = () => {
    clearAuth();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-4 flex justify-between items-center border-b border-gray-200">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Doc GEN AI</h1>
              <p className="text-sm text-gray-600">Welcome, {user?.name}</p>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </button>
          </div>
          
          {/* Navigation Menu */}
          <nav className="flex gap-6 py-3">
            <button
              onClick={() => navigate('/projects')}
              className="flex items-center gap-2 px-4 py-2 text-gray-700 font-medium rounded-md hover:bg-gray-100"
            >
              <FolderOpen className="w-4 h-4" />
              Projects
            </button>
            <button
              onClick={() => {
                setShowHistory(false);
                navigate('/bulk');
              }}
              className={`flex items-center gap-2 px-4 py-2 text-gray-700 font-medium rounded-md hover:bg-gray-100 ${!showHistory ? 'border-b-2 border-blue-600' : ''}`}
            >
              <Zap className="w-4 h-4" />
              Bulk Processing
            </button>
            <button
              onClick={() => setShowHistory(true)}
              className={`flex items-center gap-2 px-4 py-2 text-gray-700 font-medium rounded-md hover:bg-gray-100 ${showHistory ? 'border-b-2 border-blue-600' : ''}`}
            >
              <History className="w-4 h-4" />
              Job History
            </button>
            <button
              onClick={() => navigate('/workers')}
              className="flex items-center gap-2 px-4 py-2 text-gray-700 font-medium rounded-md hover:bg-gray-100"
            >
              <Activity className="w-4 h-4" />
              Workers
            </button>
            <button
              onClick={() => navigate('/supervisor')}
              className="flex items-center gap-2 px-4 py-2 text-gray-700 font-medium rounded-md hover:bg-gray-100"
            >
              <Server className="w-4 h-4" />
              Supervisor
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto p-6">
      {showHistory ? (
        <BulkJobHistory />
      ) : (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h2 className="text-3xl font-bold text-gray-800 mb-6 flex items-center gap-2">
          <BarChart3 className="w-8 h-8 text-blue-600" />
          Bulk OCR Processing
        </h2>

      {/* Configuration Panel */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Input Configuration */}
        <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Processing Configuration</h2>

          {/* Folder Path */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Folder Path</label>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="/path/to/folder"
                value={state.folderPath}
                onChange={handleFolderPathChange}
                disabled={state.isProcessing}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleOpenBrowser}
                disabled={state.isProcessing}
                className="px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400 transition-colors flex items-center gap-1"
                title="Browse server folders"
              >
                <FolderOpen className="w-4 h-4" />
                Browse
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              💡 <strong>Note:</strong> Paths are from the server machine/Docker container. Use the "Browse" button to select folders, or enter paths like <code className="bg-gray-100 px-1 rounded">/data/Bhushanji/eng-typed</code>
            </p>
          </div>

          {/* Provider Selection */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">OCR Provider</label>
            <select
              value={state.provider}
              onChange={handleProviderChange}
              disabled={state.isProcessing}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {availableProviders ? (
                availableProviders.map((provider) => (
                  <option key={provider.name} value={provider.name} disabled={!provider.available}>
                    {provider.display_name}{!provider.available ? ' (Disabled)' : ''}
                  </option>
                ))
              ) : (
                <>
                  <option value="tesseract">Tesseract</option>
                  <option value="chrome_lens">Chrome Lens</option>
                  <option value="google_vision">Google Vision</option>
                  <option value="easyocr">EasyOCR</option>
                  <option value="ollama">Ollama</option>
                  <option value="vllm">vLLM</option>
                  <option value="llamacpp">llama.cpp (Local LLM)</option>
                  <option value="claude">Claude AI (Anthropic)</option>
                </>
              )}
            </select>
          </div>

          {/* Recursive Processing */}
          <div className="mb-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={state.recursive}
                onChange={(e) => setState({ ...state, recursive: e.target.checked })}
                disabled={state.isProcessing}
                className="rounded border-gray-300"
              />
              <span className="text-sm font-medium text-gray-700">Process subfolders</span>
            </label>
          </div>

          {/* Handwriting Detection */}
          <div className="mb-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={state.handwriting}
                onChange={(e) => setState({ ...state, handwriting: e.target.checked })}
                disabled={state.isProcessing}
                className="rounded border-gray-300"
              />
              <span className="text-sm font-medium text-gray-700">Detect handwriting</span>
            </label>
          </div>
        </div>

        {/* Advanced Options */}
        <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Advanced Options</h2>

          {/* Languages */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Languages</label>
            <div className="flex flex-wrap gap-2">
              {['en', 'hi', 'es', 'fr', 'de', 'zh', 'ja'].map((lang) => (
                <button
                  key={lang}
                  onClick={() => handleLanguageToggle(lang)}
                  disabled={state.isProcessing}
                  className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                    state.languages.includes(lang)
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-700 border border-gray-300'
                  }`}
                >
                  {lang.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {/* Export Formats */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Export Formats</label>
            <div className="space-y-2">
              {['json', 'csv', 'text'].map((format) => (
                <label key={format} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={state.exportFormats.includes(format)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        handleFormatToggle(format);
                      } else {
                        handleFormatToggle(format);
                      }
                    }}
                    disabled={state.isProcessing}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm font-medium text-gray-700 capitalize">{format}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {state.error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm font-medium text-red-800">{state.error}</p>
        </div>
      )}

      {/* Progress Bar */}
      {state.isProcessing && (
        <div className="mb-6 bg-gray-50 p-4 rounded-lg border border-gray-200">
          <h3 className="text-sm font-semibold text-gray-800 mb-2">Processing Progress</h3>
          <div className="mb-2">
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${state.progress.percentage}%` }}
              ></div>
            </div>
          </div>
          <p className="text-sm text-gray-600">
            {state.progress.current} / {state.progress.total} - {state.progress.filename}
            ({state.progress.percentage}%)
          </p>

          {/* Sample Results Button - Show after some files are processed */}
          {state.progress.current > 0 && currentJobId && (
            <div className="mt-4 pt-4 border-t border-gray-300">
              <button
                onClick={handleDownloadSampleResults}
                className="w-full px-4 py-2 bg-orange-500 text-white font-semibold rounded-lg hover:bg-orange-600 transition-colors flex items-center justify-center gap-2"
              >
                <Download className="w-5 h-5" />
                Download Sample Results ({state.progress.current} files)
              </button>
              <p className="text-xs text-gray-500 mt-2 text-center">
                💡 Download processed results so far to verify OCR quality before completion
              </p>
            </div>
          )}
        </div>
      )}

      {/* Process Button */}
      <div className="mb-6">
        <button
          onClick={handleProcessing}
          disabled={state.isProcessing}
          className="w-full px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors flex items-center justify-center gap-2"
        >
          <Play className="w-5 h-5" />
          {state.isProcessing ? 'Processing...' : 'Start Processing'}
        </button>
      </div>

      {/* Results Panel */}
      {state.results && (
        <div className="bg-blue-50 p-6 rounded-lg border border-blue-200">
          <h2 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-blue-600" />
            Processing Report
          </h2>

          {/* Summary Statistics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <p className="text-sm text-gray-600">Total Files</p>
              <p className="text-2xl font-bold text-gray-800">
                {state.results.summary.total_files}
              </p>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <p className="text-sm text-gray-600">Successful</p>
              <p className="text-2xl font-bold text-green-600">
                {state.results.summary.successful}
              </p>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <p className="text-sm text-gray-600">Failed</p>
              <p className="text-2xl font-bold text-red-600">
                {state.results.summary.failed}
              </p>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <p className="text-sm text-gray-600">Success Rate</p>
              <p className="text-2xl font-bold text-blue-600">
                {state.results.summary.total_files > 0
                  ? ((state.results.summary.successful / state.results.summary.total_files) * 100).toFixed(
                      1,
                    )
                  : '0'}
                %
              </p>
            </div>
          </div>

          {/* Detailed Statistics */}
          <div className="bg-white p-4 rounded-lg border border-gray-200 mb-6">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Detailed Statistics</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-600">Total Characters</p>
                <p className="text-lg font-semibold text-gray-800">
                  {state.results.summary.statistics.total_characters.toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Average Confidence</p>
                <p className="text-lg font-semibold text-gray-800">
                  {(state.results.summary.statistics.average_confidence * 100).toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Avg Words per File</p>
                <p className="text-lg font-semibold text-gray-800">
                  {state.results.summary.statistics.average_words.toFixed(0)}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-600">Languages Detected</p>
                <p className="text-lg font-semibold text-gray-800">
                  {state.results.summary.statistics.languages.join(', ') || 'None'}
                </p>
              </div>
            </div>
          </div>

          {/* Successful Samples */}
          {state.results.results_preview.successful_samples.length > 0 && (
            <div className="bg-white p-4 rounded-lg border border-gray-200 mb-6">
              <h3 className="text-sm font-semibold text-gray-800 mb-3">
                ✅ Successfully Processed Files ({state.results.results_preview.successful_samples.length})
              </h3>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {state.results.results_preview.successful_samples.map((result, idx) => (
                  <div key={idx} className="p-2 bg-green-50 rounded border border-green-200">
                    <p className="text-sm font-medium text-gray-800">
                      {idx + 1}. {result.file}
                    </p>
                    <div className="text-xs text-gray-600 grid grid-cols-3 gap-2 mt-1">
                      <span>Confidence: {(result.confidence * 100).toFixed(1)}%</span>
                      <span>Language: {result.language}</span>
                      <span>Chars: {result.text_length.toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Error Samples */}
          {state.results.results_preview.error_samples.length > 0 && (
            <div className="bg-white p-4 rounded-lg border border-gray-200 mb-6">
              <h3 className="text-sm font-semibold text-gray-800 mb-3">
                ❌ Failed Files ({state.results.results_preview.error_samples.length})
              </h3>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {state.results.results_preview.error_samples.map((error, idx) => (
                  <div key={idx} className="p-2 bg-red-50 rounded border border-red-200">
                    <p className="text-sm font-medium text-red-800">
                      {idx + 1}. {error.file}
                    </p>
                    <p className="text-xs text-red-600 mt-1">{error.error}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Download Section */}
          <div className="bg-white p-4 rounded-lg border border-gray-200">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Available Reports</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
              {Object.entries(state.results.report_files).map(([format, filename]) => (
                <div key={format} className="p-2 bg-gray-50 rounded text-center text-xs">
                  <FileText className="w-4 h-4 inline mb-1" />
                  <p className="font-semibold">{format.toUpperCase()}</p>
                  <p className="text-gray-600">{filename}</p>
                </div>
              ))}
            </div>
            <div className="space-y-2">
              <button
                onClick={handleDownload}
                className="w-full px-4 py-2 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 transition-colors flex items-center justify-center gap-2"
              >
                <Download className="w-5 h-5" />
                Download All Reports (ZIP)
              </button>

              <button
                onClick={handleCreateProject}
                disabled={state.isCreatingProject || state.results.results_preview.successful_samples.length === 0}
                className="w-full px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <FolderOpen className="w-5 h-5" />
                {state.isCreatingProject ? 'Creating Project...' : 'Create Project for Review'}
              </button>

              <button
                onClick={() => currentJobId && handleUploadToArchipelago(currentJobId)}
                disabled={isUploadingToArchipelago || !currentJobId || state.results.results_preview.successful_samples.length === 0}
                className="w-full px-4 py-2 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                {isUploadingToArchipelago ? 'Uploading to Archipelago...' : 'Upload to Archipelago (AMI Sets)'}
              </button>

              {state.results.results_preview.successful_samples.length === 0 && (
                <p className="text-xs text-gray-500 text-center">
                  No successful files to create project from
                </p>
              )}

              {/* AMI Sets Upload Progress - Show BEFORE button when processing */}
              {archipelagoResult && archipelagoResult.status === 'processing' && (
                <div className="p-4 rounded-lg border bg-blue-50 border-blue-200 mb-4">
                  <h4 className="font-semibold text-blue-800 mb-3">⏳ Uploading to Archipelago...</h4>
                  <div className="space-y-3">
                    <div className="w-full">
                      <div className="w-full bg-gray-300 rounded-full h-4 overflow-hidden">
                        <div 
                          className="bg-gradient-to-r from-blue-500 to-blue-600 h-4 rounded-full animate-pulse" 
                          style={{ width: '50%' }}
                        ></div>
                      </div>
                    </div>
                    <p className="text-sm text-blue-700">
                      Processing your bulk OCR results and uploading to Archipelago Commons.
                      This may take 5-30 minutes depending on the file size.
                    </p>
                    <div className="text-xs text-blue-600 space-y-1 bg-blue-100 p-2 rounded">
                      <p className="flex items-center gap-2"><span>✓</span> Files prepared</p>
                      <p className="flex items-center gap-2"><span>✓</span> Uploading to server</p>
                      <p className="flex items-center gap-2"><span>⏳</span> Creating AMI Set...</p>
                    </div>
                  </div>
                </div>
              )}

              <button
                onClick={() => currentJobId && handleUploadToArchipelago(currentJobId)}
                disabled={isUploadingToArchipelago || !currentJobId || state.results.results_preview.successful_samples.length === 0}
                className="w-full px-4 py-2 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                {isUploadingToArchipelago ? 'Uploading to Archipelago...' : 'Upload to Archipelago (AMI Sets)'}
              </button>

              {/* AMI Sets Upload Result - Success or Error messages */}
              {archipelagoResult && archipelagoResult.status !== 'processing' && (
                <div className={`p-4 rounded-lg border ${
                  archipelagoResult.success && archipelagoResult.status === 'complete'
                    ? 'bg-green-50 border-green-200'
                    : 'bg-red-50 border-red-200'
                }`}>
                  {archipelagoResult.success && archipelagoResult.status === 'complete' ? (
                    <>
                      <h4 className="font-semibold text-green-800 mb-2">✅ AMI Set Created Successfully!</h4>
                      <dl className="text-sm space-y-1">
                        <div>
                          <dt className="inline font-medium text-green-700">AMI Set ID:</dt>
                          <dd className="inline ml-2 text-green-900">{archipelagoResult.ami_set_id}</dd>
                        </div>
                        <div>
                          <dt className="inline font-medium text-green-700">Name:</dt>
                          <dd className="inline ml-2 text-green-900">{archipelagoResult.ami_set_name}</dd>
                        </div>
                        <div>
                          <dt className="inline font-medium text-green-700">Documents:</dt>
                          <dd className="inline ml-2 text-green-900">{archipelagoResult.total_documents}</dd>
                        </div>
                      </dl>
                      <div className="mt-3 p-3 bg-white rounded border border-green-200">
                        <h5 className="text-xs font-semibold text-green-800 mb-2">Next Steps:</h5>
                        <ol className="text-xs text-green-700 space-y-1 list-decimal list-inside">
                          <li>
                            <a
                              href={archipelagoResult.message?.split('Process it at: ')[1]}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-purple-600 hover:underline font-medium"
                            >
                              Open AMI Set Processing Page →
                            </a>
                          </li>
                          <li>Review the configuration</li>
                          <li>Click "Process" tab</li>
                          <li>Choose "Process via Queue" or "Process via Batch"</li>
                          <li>Monitor the processing progress</li>
                        </ol>
                      </div>
                      <div className="mt-3 p-2 bg-purple-50 rounded border border-purple-200">
                        <p className="text-xs text-purple-800">
                          <strong>💡 About AMI Sets:</strong> This method creates proper Drupal file entities with thumbnails,
                          full PDF metadata, and complete Archipelago integration. No duplicate documents!
                        </p>
                      </div>
                    </>
                  ) : (
                    <>
                      <h4 className="font-semibold text-red-800 mb-2">❌ Upload Failed</h4>
                      <p className="text-sm text-red-700 mb-2">{archipelagoResult.error}</p>
                      <p className="text-xs text-red-600">
                        💡 <strong>Troubleshooting:</strong> Check that your Archipelago instance is reachable and has sufficient disk space. 
                        Check server logs for more details.
                      </p>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Folder Browser Modal */}
      {browserState.isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="bg-blue-600 text-white p-4 flex justify-between items-center">
              <h3 className="text-lg font-semibold">Browse Server Folders</h3>
              <button
                onClick={handleCloseBrowser}
                className="text-white hover:bg-blue-700 p-1 rounded"
              >
                ✕
              </button>
            </div>

            {/* Info Note */}
            <div className="bg-blue-50 border-b border-blue-200 p-3">
              <p className="text-xs text-blue-700">
                💡 <strong>Note:</strong> These are folders from the server machine/Docker container. Select a folder or navigate to find your data.
              </p>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto p-4">
              {browserState.isLoading ? (
                <div className="flex justify-center items-center h-full">
                  <div className="text-center">
                    <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-2"></div>
                    <p className="text-gray-600">Loading folders...</p>
                  </div>
                </div>
              ) : browserState.error ? (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-800 text-sm">{browserState.error}</p>
                </div>
              ) : (
                <div>
                  {/* Breadcrumb */}
                  <div className="mb-4 p-3 bg-gray-50 rounded border border-gray-200 text-sm text-gray-700 font-mono break-all">
                    {browserState.currentPath || 'Server Root'}
                  </div>

                  {/* Parent Folder Button */}
                  {browserState.parentPath && (
                    <button
                      onClick={() => handleNavigateFolder(browserState.parentPath!)}
                      className="w-full flex items-center gap-2 p-3 hover:bg-gray-50 border border-gray-200 rounded-lg mb-2 text-gray-700 font-medium"
                    >
                      <ChevronRight className="w-4 h-4 rotate-180" />
                      Go to parent folder
                    </button>
                  )}

                  {/* Folders List */}
                  {browserState.folders.length > 0 && (
                    <div className="mb-4">
                      <h4 className="text-sm font-semibold text-gray-700 mb-2">📁 Folders ({browserState.folders.length})</h4>
                      <div className="space-y-2">
                        {browserState.folders.map((folder) => (
                          <div key={folder.path} className="flex gap-2">
                            <button
                              onClick={() => handleNavigateFolder(folder.path)}
                              className="flex-1 text-left p-2 hover:bg-blue-50 border border-gray-300 rounded-lg text-blue-600 font-medium flex items-center gap-2 group"
                            >
                              <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                              {folder.name}
                              <span className="text-xs text-gray-500 ml-auto">({folder.file_count} files)</span>
                            </button>
                            <button
                              onClick={() => handleSelectFolder(folder.path)}
                              className="px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm font-medium"
                              title="Select this folder"
                            >
                              Select
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Files List */}
                  {browserState.files.length > 0 && (
                    <div className="mb-4">
                      <h4 className="text-sm font-semibold text-gray-700 mb-2">📄 Image Files ({browserState.files.length})</h4>
                      <div className="space-y-1 max-h-40 overflow-y-auto">
                        {browserState.files.map((file) => (
                          <div
                            key={file.path}
                            className="p-2 bg-gray-50 rounded text-sm text-gray-600 flex justify-between items-center"
                          >
                            <span className="truncate">{file.name}</span>
                            <span className="text-xs text-gray-400 ml-2">
                              {(file.size / 1024).toFixed(1)}KB
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {browserState.folders.length === 0 && browserState.files.length === 0 && (
                    <div className="p-4 text-center text-gray-500">
                      <p>No folders or files found</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="bg-gray-50 p-4 border-t border-gray-200 flex justify-end gap-2">
              <button
                onClick={handleCloseBrowser}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-100"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
      )}
      </main>
    </div>
  );
};

export default BulkOCRProcessor;
