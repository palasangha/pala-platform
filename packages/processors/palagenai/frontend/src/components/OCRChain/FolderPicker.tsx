import { useState, useEffect } from 'react';
import { ChevronUp, Folder, AlertCircle, Loader, Check } from 'lucide-react';
import { chainAPI } from '@/services/api';

interface Folder {
  name: string;
  path: string;
  is_readable: boolean;
}

interface FolderPickerProps {
  onSelect: (path: string) => void;
  onClose: () => void;
}

export default function FolderPicker({ onSelect, onClose }: FolderPickerProps) {
  const [currentPath, setCurrentPath] = useState('/');
  const [folders, setFolders] = useState<Folder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [customPath, setCustomPath] = useState('');

  // Load folders when path changes
  useEffect(() => {
    loadFolders(currentPath);
  }, [currentPath]);

  const loadFolders = async (path: string) => {
    try {
      setLoading(true);
      setError(null);
      const result = await chainAPI.listFolders(path);
      setFolders(result.folders);
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || err.message || 'Failed to load folders';
      setError(errorMsg);
      setFolders([]);
    } finally {
      setLoading(false);
    }
  };

  const handleFolderClick = (folder: Folder) => {
    if (folder.is_readable) {
      setCurrentPath(folder.path);
    }
  };

  const handleParentClick = () => {
    const parent = currentPath.substring(0, currentPath.lastIndexOf('/')) || '/';
    setCurrentPath(parent);
  };

  const handleSelectCurrent = () => {
    onSelect(currentPath);
  };

  const handleCustomPath = (path: string) => {
    setCustomPath(path);
  };

  const handleApplyCustomPath = () => {
    if (customPath.trim()) {
      setCurrentPath(customPath.trim());
      setCustomPath('');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <h2 className="text-xl font-bold text-gray-900 mb-4">Browse Folders</h2>

        {/* Current Path */}
        <div className="mb-4 p-3 bg-gray-100 rounded-lg">
          <p className="text-sm text-gray-600 mb-1">Current Path:</p>
          <p className="text-sm font-mono text-gray-900 break-all">{currentPath}</p>
        </div>

        {/* Custom Path Input */}
        <div className="mb-4 flex gap-2">
          <input
            type="text"
            value={customPath}
            onChange={(e) => handleCustomPath(e.target.value)}
            placeholder="Or paste path here..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleApplyCustomPath();
              }
            }}
          />
          <button
            onClick={handleApplyCustomPath}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors font-medium"
          >
            Go
          </button>
        </div>

        {/* Folders List */}
        <div className="flex-1 overflow-y-auto border border-gray-300 rounded-lg mb-4">
          {loading ? (
            <div className="flex items-center justify-center h-40">
              <Loader size={24} className="animate-spin text-gray-400" />
            </div>
          ) : error ? (
            <div className="p-4 flex items-start gap-3 text-red-800 bg-red-50">
              <AlertCircle size={20} className="flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Error loading folders</p>
                <p className="text-sm mt-1">{error}</p>
              </div>
            </div>
          ) : (
            <div className="divide-y">
              {/* Parent Folder */}
              {currentPath !== '/' && (
                <button
                  onClick={handleParentClick}
                  className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors flex items-center gap-3"
                >
                  <ChevronUp size={18} className="text-gray-500 flex-shrink-0" />
                  <span className="text-gray-700 font-medium">..</span>
                </button>
              )}

              {/* Folders */}
              {folders.length > 0 ? (
                folders.map((folder) => (
                  <button
                    key={folder.path}
                    onClick={() => handleFolderClick(folder)}
                    disabled={!folder.is_readable}
                    className={`w-full text-left px-4 py-3 transition-colors flex items-center gap-3 ${
                      folder.is_readable
                        ? 'hover:bg-gray-50 cursor-pointer'
                        : 'bg-gray-50 cursor-not-allowed opacity-60'
                    }`}
                  >
                    <Folder size={18} className={folder.is_readable ? 'text-blue-500' : 'text-gray-400'} />
                    <div className="flex-1 min-w-0">
                      <p className="text-gray-900 truncate">{folder.name}</p>
                      {!folder.is_readable && (
                        <p className="text-xs text-gray-500">Permission denied</p>
                      )}
                    </div>
                  </button>
                ))
              ) : (
                <div className="p-4 text-center text-gray-500">
                  <p>No folders found</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors font-medium text-gray-700"
          >
            Cancel
          </button>
          <button
            onClick={handleSelectCurrent}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium flex items-center gap-2"
          >
            <Check size={18} />
            Select Folder
          </button>
        </div>
      </div>
    </div>
  );
}
