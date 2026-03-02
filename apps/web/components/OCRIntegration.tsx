'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

interface OCRJob {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  files_total: number;
  files_processed: number;
  current_file?: string;
  results: Array<{
    file_name: string;
    text: string;
    provider: string;
    confidence: number;
    timestamp: string;
    error?: string;
  }>;
  errors: Array<{
    file: string;
    error: string;
  }>;
}

interface OCRIntegrationProps {
  onJobComplete?: (job: OCRJob) => void;
}

export default function OCRIntegration({ onJobComplete }: OCRIntegrationProps) {
  const { ws } = useWebSocket();
  const [folderPath, setFolderPath] = useState('');
  const [provider, setProvider] = useState('tesseract');
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<OCRJob | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusPollingInterval, setStatusPollingInterval] = useState<NodeJS.Timeout | null>(null);

  // Poll for job status every 2 seconds
  useEffect(() => {
    if (!jobId || !ws) return;

    const pollStatus = async () => {
      try {
        const response = await new Promise((resolve) => {
          const msgId = `status-${Date.now()}`;
          
          const handleMessage = (event: Event) => {
            const message = JSON.parse((event as MessageEvent).data);
            if (message.id === msgId && message.result) {
              resolve(message.result);
              ws.removeEventListener('message', handleMessage);
            }
          };

          ws.addEventListener('message', handleMessage);

          ws.send(
            JSON.stringify({
              jsonrpc: '2.0',
              method: 'tools/invoke',
              params: {
                toolName: 'get_ocr_status',
                arguments: { job_id: jobId }
              },
              id: msgId
            })
          );
        });

        const jobData = response as OCRJob;
        setJob(jobData);

        if (jobData.status === 'completed' || jobData.status === 'failed') {
          setIsProcessing(false);
          if (statusPollingInterval) {
            clearInterval(statusPollingInterval);
            setStatusPollingInterval(null);
          }
          if (onJobComplete) {
            onJobComplete(jobData);
          }
        }
      } catch (error) {
        console.error('Error polling OCR status:', error);
      }
    };

    // Start polling
    const interval = setInterval(pollStatus, 2000);
    setStatusPollingInterval(interval);
    pollStatus(); // Call immediately

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [jobId, ws, onJobComplete]);

  const startProcessing = useCallback(async () => {
    if (!ws || !folderPath) {
      alert('Please enter a folder path');
      return;
    }

    setIsProcessing(true);

    try {
      const response = await new Promise((resolve) => {
        const msgId = `process-${Date.now()}`;

        const handleMessage = (event: Event) => {
          const message = JSON.parse((event as MessageEvent).data);
          if (message.id === msgId) {
            resolve(message.result || message.error);
            ws.removeEventListener('message', handleMessage);
          }
        };

        ws.addEventListener('message', handleMessage);

        ws.send(
          JSON.stringify({
            jsonrpc: '2.0',
            method: 'tools/invoke',
            params: {
              toolName: 'process_folder',
              arguments: {
                folder_path: folderPath,
                provider: provider,
                language: 'eng',
                file_pattern: '*.*'
              }
            },
            id: msgId
          })
        );
      });

      const result = response as any;
      if (result.job_id) {
        setJobId(result.job_id);
      } else if (result.message) {
        alert(`Error: ${result.message}`);
        setIsProcessing(false);
      }
    } catch (error) {
      console.error('Error starting OCR processing:', error);
      alert(`Error: ${error}`);
      setIsProcessing(false);
    }
  }, [ws, folderPath, provider]);

  const getProgressPercentage = () => {
    if (!job || job.files_total === 0) return 0;
    return (job.files_processed / job.files_total) * 100;
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 max-w-4xl">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">OCR Processing</h2>

      {!jobId ? (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Folder Path
            </label>
            <input
              type="text"
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              placeholder="/path/to/images"
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isProcessing}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              OCR Provider
            </label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isProcessing}
            >
              <option value="tesseract">Tesseract (Local)</option>
              <option value="ollama">Ollama (Local Vision Model)</option>
              <option value="lmstudio">LM Studio (Local Vision Model)</option>
            </select>
          </div>

          <button
            onClick={startProcessing}
            disabled={isProcessing}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-bold py-2 px-4 rounded-md transition-colors"
          >
            {isProcessing ? 'Processing...' : 'Start Processing'}
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-gray-50 p-4 rounded-md">
            <h3 className="font-semibold text-gray-700 mb-2">Job ID: {jobId}</h3>
            <p className="text-sm text-gray-600 mb-2">
              Status: <span className="font-semibold capitalize">{job?.status || 'pending'}</span>
            </p>

            {job && (
              <>
                <div className="mb-4">
                  <div className="flex justify-between text-sm text-gray-600 mb-2">
                    <span>Progress</span>
                    <span>{job.files_processed}/{job.files_total} files</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${getProgressPercentage()}%` }}
                    />
                  </div>
                </div>

                {job.current_file && (
                  <p className="text-sm text-gray-600 mb-4">
                    Currently processing: <span className="font-mono">{job.current_file}</span>
                  </p>
                )}

                {job.results.length > 0 && (
                  <div className="mt-4">
                    <h4 className="font-semibold text-gray-700 mb-2">Results ({job.results.length})</h4>
                    <div className="max-h-96 overflow-y-auto space-y-2">
                      {job.results.map((result, idx) => (
                        <div key={idx} className="bg-white border border-gray-200 p-3 rounded text-sm">
                          <div className="flex justify-between items-start mb-1">
                            <span className="font-mono text-blue-600">{result.file_name}</span>
                            <span className="text-gray-500 text-xs">{(result.confidence * 100).toFixed(1)}%</span>
                          </div>
                          <p className="text-gray-700 line-clamp-2">{result.text}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {job.errors.length > 0 && (
                  <div className="mt-4 bg-red-50 border border-red-200 p-3 rounded">
                    <h4 className="font-semibold text-red-700 mb-2">Errors ({job.errors.length})</h4>
                    <div className="max-h-48 overflow-y-auto space-y-1">
                      {job.errors.map((error, idx) => (
                        <div key={idx} className="text-sm text-red-600">
                          <span className="font-mono">{error.file}:</span> {error.error}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          {job?.status === 'completed' || job?.status === 'failed' ? (
            <button
              onClick={() => {
                setJobId(null);
                setJob(null);
                setFolderPath('');
              }}
              className="w-full bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded-md transition-colors"
            >
              Process Another Folder
            </button>
          ) : null}
        </div>
      )}
    </div>
  );
}
