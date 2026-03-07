import React, { useState } from 'react';
import { archipelagoAPI } from '@/services/archipelagoService';

export const ArchipelagoMetadataUpdater: React.FC = () => {

  const [nodeUuid, setNodeUuid] = useState('');
  const [metadata, setMetadata] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      await archipelagoAPI.updateMetadata(nodeUuid, metadata);
      setSuccess('Successfully updated metadata!');
      setNodeUuid('');
      setMetadata('');
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to update metadata');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
        <div className="bg-white p-8 rounded-lg shadow">
          <h2 className="text-xl font-bold mb-4">Update Archipelago Metadata</h2>
          <form onSubmit={handleUpdate}>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Node UUID
              </label>
              <input
                type="text"
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                value={nodeUuid}
                onChange={(e) => setNodeUuid(e.target.value)}
                placeholder="Enter the node UUID to update"
              />
            </div>
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Raw Metadata
              </label>
              <textarea
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 font-mono"
                rows={15}
                value={metadata}
                onChange={(e) => setMetadata(e.target.value)}
                placeholder='Paste the raw JSON metadata here, e.g., {"label": "New Title", ...}'
              />
            </div>

            {error && (
              <div className="mb-4 rounded-md bg-red-50 p-4">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}
            {success && (
              <div className="mb-4 rounded-md bg-green-50 p-4">
                <p className="text-sm text-green-800">{success}</p>
              </div>
            )}

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-300"
              >
                {loading ? 'Updating...' : 'Update Metadata'}
              </button>
            </div>
          </form>
        </div>
    </div>
  );
};
