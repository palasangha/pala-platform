import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { Download, BarChart3, FolderOpen, Zap, LogOut, History, Activity, Server } from 'lucide-react';
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
  const [isUploadingToArchipelago, setIsUploadingToArchipelago] = useState<boolean>(false);
  const [, setArchipelagoResult] = useState<{
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

  // Folder browser functions - to be used in modal implementation
  // const handleNavigateFolder = async (path: string) => {
  //   setBrowserState({ ...browserState, isLoading: true });
  //   try {
  //     const response = await authenticatedFetch('/api/bulk/browse-folders', {
  //       method: 'POST',
  //       headers: { 'Content-Type': 'application/json' },
  //       body: JSON.stringify({ path }),
  //     });
  //     if (!response.ok) throw new Error('Failed to load folder');
  //     const data = await response.json();
  //     setBrowserState({
  //       ...browserState,
  //       isLoading: false,
  //       currentPath: data.current_path,
  //       folders: data.folders || [],
  //       files: data.files || [],
  //       parentPath: data.parent_path,
  //       error: null,
  //     });
  //   } catch (err) {
  //     setBrowserState({
  //       ...browserState,
  //       isLoading: false,
  //       error: err instanceof Error ? err.message : 'Failed to load folder',
  //     });
  //   }
  // };

  // const handleSelectFolder = (path: string) => {
  //   setState({ ...state, folderPath: path, error: null });
  //   setBrowserState({ ...browserState, isOpen: false });
  // };

  // const handleCloseBrowser = () => {
  //   setBrowserState({ ...browserState, isOpen: false });
  // };

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

  const handleCancelProcessing = async () => {
    if (!currentJobId) return;

    if (!confirm('Are you sure you want to cancel the ongoing processing? Progress will be lost.')) {
      return;
    }

    try {
      const response = await authenticatedFetch(`/api/bulk/stop/${currentJobId}`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to cancel job');
      }

      alert('Job cancellation request sent successfully');
      // The polling will pick up the 'cancelled' status eventually,
      // but we can also stop it manually here if we want.
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to cancel job');
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

            {/* Start Button */}
            <div className="mb-6 flex gap-3">
              <button
                onClick={handleProcessing}
                disabled={state.isProcessing}
                className="flex-1 px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors flex items-center justify-center gap-2"
              >
                <Zap className="w-5 h-5" />
                Start Processing
              </button>
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

                {/* Cancel Button */}
                <div className="mt-4 flex gap-2">
                  <button
                    onClick={handleDownloadSampleResults}
                    className="flex-1 px-4 py-2 bg-orange-500 text-white font-semibold rounded-lg hover:bg-orange-600 transition-colors flex items-center justify-center gap-2"
                  >
                    <Download className="w-5 h-5" />
                    Download Samples ({state.progress.current})
                  </button>
                  <button
                    onClick={handleCancelProcessing}
                    className="flex-1 px-4 py-2 bg-red-500 text-white font-semibold rounded-lg hover:bg-red-600 transition-colors flex items-center justify-center gap-2"
                  >
                    <LogOut className="w-5 h-5 rotate-180" />
                    Cancel Job
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-2 text-center">
                  💡 Download steps so far to verify quality, or cancel if something is wrong
                </p>
              </div>
            )}

            {/* Results Display */}
            {state.results && !state.isProcessing && (
              <div className="mb-6 bg-green-50 p-6 rounded-lg border border-green-200">
                <h3 className="text-lg font-semibold text-green-900 mb-4 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5" />
                  Processing Complete
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                  <div className="bg-white p-4 rounded-lg border border-green-100">
                    <p className="text-sm text-gray-600">Total Files</p>
                    <p className="text-2xl font-bold text-green-600">{state.results.summary.total_files}</p>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-green-100">
                    <p className="text-sm text-gray-600">Successful</p>
                    <p className="text-2xl font-bold text-green-600">{state.results.summary.successful}</p>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-green-100">
                    <p className="text-sm text-gray-600">Failed</p>
                    <p className="text-2xl font-bold text-red-600">{state.results.summary.failed}</p>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-green-100">
                    <p className="text-sm text-gray-600">Avg Confidence</p>
                    <p className="text-2xl font-bold text-blue-600">{state.results.summary.statistics.average_confidence.toFixed(2)}%</p>
                  </div>
                </div>

                <div className="flex gap-2 flex-wrap">
                  <button
                    onClick={handleDownload}
                    className="px-4 py-2 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
                  >
                    <Download className="w-5 h-5" />
                    Download Results
                  </button>
                  <button
                    onClick={handleCreateProject}
                    disabled={state.isCreatingProject}
                    className="px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors flex items-center gap-2"
                  >
                    <FolderOpen className="w-5 h-5" />
                    Create Project
                  </button>
                  {currentJobId && (
                    <button
                      onClick={() => handleUploadToArchipelago(currentJobId!)}
                      disabled={isUploadingToArchipelago}
                      className="px-4 py-2 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 disabled:bg-gray-400 transition-colors flex items-center gap-2"
                    >
                      <Server className="w-5 h-5" />
                      Upload to Archipelago
                    </button>
                  )}
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
