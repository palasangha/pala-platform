import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { projectAPI } from '@/services/api';
import type { Project, Image } from '@/types';
import { ArrowLeft, Upload, Image as ImageIcon, Trash2, Download, FileJson, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

export const ProjectDetail: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [project, setProject] = useState<Project | null>(null);
  const [images, setImages] = useState<Image[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const [bulkResults, setBulkResults] = useState<any>(null);
  const [showResults, setShowResults] = useState(false);

  useEffect(() => {
    if (projectId) {
      loadProjectData();
    }
  }, [projectId]);

  const loadProjectData = async () => {
    if (!projectId) return;

    try {
      const [projectData, imagesData] = await Promise.all([
        projectAPI.getProject(projectId),
        projectAPI.getProjectImages(projectId),
      ]);
      setProject(projectData.project);
      setImages(imagesData.images);

      // Try to load bulk results
      await loadBulkResults();
    } catch (err) {
      setError('Failed to load project data');
    } finally {
      setLoading(false);
    }
  };

  const loadBulkResults = async () => {
    if (!projectId) return;

    try {
      const token = localStorage.getItem('access_token');

      // Try to fetch result.json from project folder
      const response = await fetch(`/api/projects/${projectId}/results.json`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setBulkResults(data);
      }
    } catch (err) {
      // Silently fail if no bulk results exist
      console.log('No bulk results found for this project');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !projectId) return;

    setUploading(true);
    const files = Array.from(e.target.files);

    try {
      for (const file of files) {
        await projectAPI.uploadImage(projectId, file);
      }
      loadProjectData();
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to upload images');
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteImage = async (imageId: string) => {
    if (!projectId || !window.confirm('Delete this image?')) return;

    try {
      await projectAPI.deleteImage(projectId, imageId);
      setImages(images.filter((img) => img.id !== imageId));
    } catch (err) {
      setError('Failed to delete image');
    }
  };

  const handleExportCorrected = async () => {
    if (!projectId) return;

    setExporting(true);
    setError('');

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/projects/${projectId}/export-corrected`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to export results');
      }

      // Download the ZIP file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${project?.name}_corrected_results.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      setError(err.message || 'Failed to export corrected results');
    } finally {
      setExporting(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center">
            <button
              onClick={() => navigate('/projects')}
              className="mr-4 text-gray-600 hover:text-gray-900"
            >
              <ArrowLeft className="w-6 h-6" />
            </button>
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900">{project?.name}</h1>
              <p className="text-sm text-gray-600">{project?.description}</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-4 rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Upload Section */}
        <div className="mb-6 flex gap-4">
          <label className="flex items-center justify-center px-4 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 cursor-pointer">
            <Upload className="w-5 h-5 mr-2" />
            {uploading ? 'Uploading...' : 'Upload Images'}
            <input
              type="file"
              multiple
              accept="image/*,.pdf"
              onChange={handleFileUpload}
              className="hidden"
              disabled={uploading}
            />
          </label>
          {images.length > 0 && (
            <button
              onClick={handleExportCorrected}
              disabled={exporting}
              className="flex items-center justify-center px-4 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Download className="w-5 h-5 mr-2" />
              {exporting ? 'Exporting...' : 'Export Corrected Results'}
            </button>
          )}
          {bulkResults && (
            <button
              onClick={() => setShowResults(!showResults)}
              className="flex items-center justify-center px-4 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
            >
              <FileJson className="w-5 h-5 mr-2" />
              {showResults ? 'Hide Results' : 'View All Results'}
              {showResults ? <ChevronUp className="w-4 h-4 ml-2" /> : <ChevronDown className="w-4 h-4 ml-2" />}
            </button>
          )}
        </div>

        {/* Bulk Results Section */}
        {showResults && bulkResults && (
          <div className="mb-8 bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">All Bulk Processing Results</h2>

            {/* Summary */}
            {bulkResults.summary && (
              <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                <h3 className="font-semibold text-gray-900 mb-3">Summary</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-gray-600">Total Files</p>
                    <p className="text-lg font-bold text-gray-900">{bulkResults.summary.total_files}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Successful</p>
                    <p className="text-lg font-bold text-green-600">{bulkResults.summary.successful}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Failed</p>
                    <p className="text-lg font-bold text-red-600">{bulkResults.summary.failed}</p>
                  </div>
                  <div>
                    <p className="text-gray-600">Avg Confidence</p>
                    <p className="text-lg font-bold text-blue-600">
                      {bulkResults.summary.statistics?.average_confidence?.toFixed(2) || 'N/A'}%
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Successful Results Table */}
            {bulkResults.results_preview?.successful_samples?.length > 0 && (
              <div className="mb-6">
                <h3 className="font-semibold text-gray-900 mb-3 text-green-700">
                  ✓ Successful Results ({bulkResults.results_preview.successful_samples.length})
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-green-50 border-b">
                      <tr>
                        <th className="px-4 py-2 text-left">File</th>
                        <th className="px-4 py-2 text-left">Confidence</th>
                        <th className="px-4 py-2 text-left">Words</th>
                        <th className="px-4 py-2 text-left">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bulkResults.results_preview.successful_samples.map((result: any, idx: number) => (
                        <tr key={idx} className="border-b hover:bg-gray-50">
                          <td className="px-4 py-2">
                            <div className="flex items-center gap-2">
                              <span className="text-gray-900 font-medium">{result.file}</span>
                            </div>
                          </td>
                          <td className="px-4 py-2">
                            <span className="inline-block px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
                              {(result.confidence * 100).toFixed(1)}%
                            </span>
                          </td>
                          <td className="px-4 py-2 text-gray-600">
                            {result.text?.split(' ').length || 0}
                          </td>
                          <td className="px-4 py-2">
                            <button
                              onClick={() => {
                                const imageId = images.find(
                                  (img) => img.original_filename === result.file
                                )?.id;
                                if (imageId) {
                                  navigate(`/projects/${projectId}/images/${imageId}`);
                                }
                              }}
                              className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800"
                            >
                              <ExternalLink className="w-4 h-4" />
                              View
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Failed Results Table */}
            {bulkResults.results_preview?.failed_samples?.length > 0 && (
              <div>
                <h3 className="font-semibold text-gray-900 mb-3 text-red-700">
                  ✗ Failed Results ({bulkResults.results_preview.failed_samples.length})
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-red-50 border-b">
                      <tr>
                        <th className="px-4 py-2 text-left">File</th>
                        <th className="px-4 py-2 text-left">Error</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bulkResults.results_preview.failed_samples.map((result: any, idx: number) => (
                        <tr key={idx} className="border-b hover:bg-gray-50">
                          <td className="px-4 py-2 text-gray-900 font-medium">{result.file}</td>
                          <td className="px-4 py-2 text-red-600">{result.error}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Images Grid */}
        {images.length === 0 ? (
          <div className="text-center py-12">
            <ImageIcon className="w-16 h-16 mx-auto text-gray-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900">No images yet</h3>
            <p className="mt-2 text-sm text-gray-500">Upload images to start OCR processing</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {images.map((image) => (
              <div
                key={image.id}
                className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow"
              >
                <div
                  onClick={() => navigate(`/projects/${projectId}/images/${image.id}`)}
                  className="cursor-pointer p-4"
                >
                  <div className="aspect-square bg-gray-100 rounded-md mb-3 flex items-center justify-center overflow-hidden">
                    <ImageIcon className="w-16 h-16 text-gray-400" />
                  </div>
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {image.original_filename}
                  </p>
                  <div className="mt-2">
                    <span
                      className={`inline-block px-2 py-1 text-xs rounded ${getStatusColor(
                        image.ocr_status
                      )}`}
                    >
                      {image.ocr_status}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">
                    {new Date(image.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="border-t px-4 py-2 flex justify-end">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteImage(image.id);
                    }}
                    className="text-red-600 hover:text-red-800"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};
