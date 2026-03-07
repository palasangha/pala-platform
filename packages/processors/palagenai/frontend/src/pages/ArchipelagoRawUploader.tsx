import React, { useState } from 'react';
import api from '@/services/api';
import { Save, FileJson, FileText, FileUp } from 'lucide-react';

const ArchipelagoRawUploader: React.FC = () => {
  const [jsonInput, setJsonInput] = useState<string>(JSON.stringify({
    "label": "Test Document",
    "type": "Document",
    "language": "en",
    "description": "Test document for Archipelago",
    "creator": "Test User",
    "note": "This is a test document with OCR text",
    "documents": [],
    "as:document": {}
  }, null, 2));

  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string>('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);

    try {
      // Validate JSON
      const metadata = JSON.parse(jsonInput);

      // Send to backend
      const response = await api.post(
        `/archipelago/push-raw-metadata`,
        { metadata }
      );

      setResult(response.data);
    } catch (err: any) {
      if (err instanceof SyntaxError) {
        setError('Invalid JSON format: ' + err.message);
      } else if (err.response) {
        setError(err.response.data?.error || 'Failed to push metadata to Archipelago');
      } else {
        setError('Network error: ' + err.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const formatJson = () => {
    try {
      const parsed = JSON.parse(jsonInput);
      setJsonInput(JSON.stringify(parsed, null, 2));
      setError('');
    } catch (err: any) {
      setError('Invalid JSON: ' + err.message);
    }
  };

  const loadSample = (type: string) => {
    const samples: { [key: string]: any } = {
      'minimal': {
        "label": "Minimal Test Document",
        "type": "Document",
        "language": "en",
        "description": "Minimal metadata test",
        "documents": []
      },
      'withText': {
        "label": "Document with OCR Text",
        "type": "Document",
        "language": "en",
        "description": "Document with OCR content",
        "note": "This is the extracted OCR text from the document.\n\nIt can span multiple lines and paragraphs.",
        "creator": "OCR Service",
        "documents": []
      },
      'withFile': {
        "label": "Document with MinIO File",
        "type": "Document",
        "language": "en",
        "description": "Document with file reference",
        "note": "OCR extracted text here",
        "documents": [],
        "as:document": {
          "urn:uuid:test-uuid-here": {
            "url": "http://localhost:9000/archipelago/test-file.pdf",
            "name": "test-file.pdf",
            "type": "Document",
            "dr:for": "documents",
            "dr:uuid": "test-uuid-here",
            "dr:filesize": 1024,
            "dr:mimetype": "application/pdf"
          }
        }
      }
    };

    setJsonInput(JSON.stringify(samples[type], null, 2));
    setError('');
  };
  
  return (
    <div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="md:col-span-2">
            <div className="bg-white rounded-lg shadow">
              <div className="p-4 border-b flex justify-between items-center">
                <h3 className="font-bold">Raw Metadata (JSON)</h3>
                <div className="flex gap-2">
                  <button onClick={formatJson} className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-md flex items-center gap-1"><FileJson className="w-3 h-3" /> Format</button>
                  <button onClick={() => loadSample('minimal')} className="px-3 py-1 text-sm bg-blue-100 hover:bg-blue-200 rounded-md flex items-center gap-1"><FileText className="w-3 h-3" /> Minimal</button>
                  <button onClick={() => loadSample('withText')} className="px-3 py-1 text-sm bg-blue-100 hover:bg-blue-200 rounded-md flex items-center gap-1"><FileText className="w-3 h-3" /> With Text</button>
                  <button onClick={() => loadSample('withFile')} className="px-3 py-1 text-sm bg-blue-100 hover:bg-blue-200 rounded-md flex items-center gap-1"><FileUp className="w-3 h-3" /> With File</button>
                </div>
              </div>
              <div className="p-4">
                <form onSubmit={handleSubmit}>
                  <div className="mb-4">
                    <textarea
                      rows={20}
                      value={jsonInput}
                      onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setJsonInput(e.target.value)}
                      className="w-full p-2 border rounded-md font-mono text-xs"
                      placeholder="Enter Archipelago metadata JSON..."
                    />
                  </div>

                  {error && (
                    <div className="p-3 mb-4 bg-red-100 text-red-700 rounded-md">
                      {error}
                      <button onClick={() => setError('')} className="ml-4 font-bold">X</button>
                    </div>
                  )}

                  <div className="flex justify-between">
                    <button type="submit" disabled={loading} className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-300 flex items-center gap-2">
                      {loading ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          Pushing...
                        </>
                      ) : (
                        <><Save className="w-4 h-4" /> Push to Archipelago</>
                      )}
                    </button>
                    <button type="button" onClick={() => setResult(null)} className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200">
                      Clear Result
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="bg-white rounded-lg shadow">
              <div className="p-4 border-b"><h3 className="font-bold">Result</h3></div>
              <div className="p-4">
                {result ? (
                  <div>
                    <div className={`p-3 mb-4 rounded-md ${result.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {result.success ? '✓ Success' : '✗ Failed'}
                    </div>

                    {result.node_id && (
                      <div className="mb-3">
                        <strong>Node ID:</strong> {result.node_id}
                      </div>
                    )}

                    {result.node_url && (
                      <div className="mb-3">
                        <strong>URL:</strong>{' '}
                        <a href={result.node_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                          View in Archipelago
                        </a>
                      </div>
                    )}

                    {result.message && (
                      <div className="mb-3">
                        <strong>Message:</strong> {result.message}
                      </div>
                    )}

                    <details>
                      <summary className="text-gray-500 cursor-pointer">Full Response</summary>
                      <pre className="text-xs mt-2 p-2 bg-gray-50 rounded overflow-auto max-h-60">
                        {JSON.stringify(result, null, 2)}
                      </pre>
                    </details>
                  </div>
                ) : (
                  <p className="text-gray-500">No result yet. Submit the form to push metadata to Archipelago.</p>
                )}
              </div>
            </div>
            <div className="bg-white rounded-lg shadow">
              <div className="p-4 border-b"><h3 className="font-bold">Help</h3></div>
              <div className="p-4 text-sm">
                <h6 className="font-bold">Required Fields:</h6>
                <ul className="list-disc list-inside">
                  <li><code>label</code> - Document title</li>
                  <li><code>type</code> - Content type (e.g., "Document")</li>
                </ul>

                <h6 className="font-bold mt-4">Common Fields:</h6>
                <ul className="list-disc list-inside">
                  <li><code>description</code> - Brief description</li>
                  <li><code>note</code> - OCR text or notes</li>
                  <li><code>language</code> - Language code (e.g., "en")</li>
                  <li><code>creator</code> - Creator name</li>
                  <li><code>documents</code> - Array of file IDs</li>
                  <li><code>as:document</code> - File metadata</li>
                </ul>

                <p className="text-gray-500 mt-3">
                  Use the sample buttons above to load pre-configured templates.
                </p>
              </div>
            </div>
          </div>
        </div>
    </div>
  );
};

export default ArchipelagoRawUploader;
