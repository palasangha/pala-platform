"""
Phase 5: React Frontend Components
===================================
React components for document upload, processing, and QA interface.
Written as Python strings for easy deployment.

Author: ICR Integration Team
Date: 2026-01-23
"""

# React Component Templates

DOCUMENT_UPLOAD_COMPONENT = '''
import React, { useState } from 'react';
import axios from 'axios';

const DocumentUpload = ({ onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError(null);
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(
        'http://localhost:8000/api/documents/upload',
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );

      if (response.data.success) {
        onUploadSuccess(response.data);
        setFile(null);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="document-upload">
      <h2>Upload Document</h2>
      
      <div className="upload-form">
        <input
          type="file"
          onChange={handleFileChange}
          accept=".pdf,.png,.jpg,.jpeg"
          disabled={uploading}
        />
        
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="btn-primary"
        >
          {uploading ? 'Uploading...' : 'Upload & Process'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}
      
      {file && (
        <div className="file-info">
          Selected: {file.name} ({(file.size / 1024).toFixed(2)} KB)
        </div>
      )}
    </div>
  );
};

export default DocumentUpload;
'''

DOCUMENT_VIEWER_COMPONENT = '''
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const DocumentViewer = ({ documentId }) => {
  const [document, setDocument] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (documentId) {
      loadDocument();
      const interval = setInterval(loadDocument, 2000); // Poll every 2s
      return () => clearInterval(interval);
    }
  }, [documentId]);

  const loadDocument = async () => {
    try {
      const response = await axios.get(
        `http://localhost:8000/api/documents/${documentId}`
      );
      
      if (response.data.success) {
        setDocument(response.data.document);
        setError(null);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load document');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading document...</div>;
  if (error) return <div className="error">{error}</div>;
  if (!document) return null;

  return (
    <div className="document-viewer">
      <h3>Document: {document.filename}</h3>
      
      <div className="document-status">
        <span className={`status-badge ${document.status}`}>
          {document.status}
        </span>
        {document.processed && <span className="processed">✓ Processed</span>}
      </div>

      {document.text && (
        <div className="document-text">
          <h4>Extracted Text</h4>
          <pre>{document.text.substring(0, 500)}...</pre>
        </div>
      )}

      {document.markdown && (
        <div className="document-markdown">
          <h4>Structured Content</h4>
          <pre>{document.markdown.substring(0, 500)}...</pre>
        </div>
      )}

      {document.extraction && (
        <div className="document-extraction">
          <h4>Extracted Fields</h4>
          <pre>{JSON.stringify(document.extraction, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};

export default DocumentViewer;
'''

QA_INTERFACE_COMPONENT = '''
import React, { useState } from 'react';
import axios from 'axios';

const QAInterface = ({ documentId }) => {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAsk = async () => {
    if (!question.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(
        'http://localhost:8000/api/qa/ask',
        {
          question: question,
          document_id: documentId || null,
          n_results: 5
        }
      );

      if (response.data.success) {
        setAnswer(response.data);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Question failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="qa-interface">
      <h3>Ask Questions</h3>
      
      <div className="qa-input">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about the document..."
          onKeyPress={(e) => e.key === 'Enter' && handleAsk()}
          disabled={loading}
        />
        
        <button
          onClick={handleAsk}
          disabled={!question.trim() || loading}
          className="btn-primary"
        >
          {loading ? 'Asking...' : 'Ask'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {answer && (
        <div className="qa-answer">
          <div className="answer-text">
            <strong>Answer:</strong>
            <p>{answer.answer}</p>
            <span className="confidence">
              Confidence: {(answer.confidence * 100).toFixed(0)}%
            </span>
          </div>

          {answer.sources && answer.sources.length > 0 && (
            <div className="answer-sources">
              <strong>Sources:</strong>
              {answer.sources.map((source, idx) => (
                <div key={idx} className="source">
                  <span className="source-number">[{idx + 1}]</span>
                  <span className="source-text">
                    {source.text.substring(0, 150)}...
                  </span>
                  <span className="source-score">
                    {(source.score * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default QAInterface;
'''

APP_COMPONENT = '''
import React, { useState } from 'react';
import DocumentUpload from './DocumentUpload';
import DocumentViewer from './DocumentViewer';
import QAInterface from './QAInterface';
import './App.css';

function App() {
  const [currentDocumentId, setCurrentDocumentId] = useState(null);
  const [documents, setDocuments] = useState([]);

  const handleUploadSuccess = (data) => {
    setCurrentDocumentId(data.document_id);
    setDocuments([...documents, data]);
    
    // Auto-process the document
    processDocument(data.document_id);
  };

  const processDocument = async (docId) => {
    try {
      await axios.post(
        `http://localhost:8000/api/documents/${docId}/process`
      );
    } catch (err) {
      console.error('Process failed:', err);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🚀 Intelligent Content Recognition</h1>
        <p>Upload, Process, Extract, and Query Documents</p>
      </header>

      <div className="container">
        <div className="left-panel">
          <DocumentUpload onUploadSuccess={handleUploadSuccess} />
          
          {currentDocumentId && (
            <DocumentViewer documentId={currentDocumentId} />
          )}
        </div>

        <div className="right-panel">
          {currentDocumentId && (
            <QAInterface documentId={currentDocumentId} />
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
'''

CSS_STYLES = '''
.App {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.App-header {
  padding: 2rem;
  text-align: center;
  color: white;
}

.App-header h1 {
  margin: 0;
  font-size: 2.5rem;
}

.container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.left-panel, .right-panel {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 10px 40px rgba(0,0,0,0.1);
}

.document-upload h2 {
  margin-top: 0;
  color: #333;
}

.upload-form {
  display: flex;
  gap: 1rem;
  margin: 1rem 0;
}

.btn-primary {
  background: #667eea;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.3s;
}

.btn-primary:hover:not(:disabled) {
  background: #5568d3;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  background: #fee;
  border: 1px solid #fcc;
  color: #c33;
  padding: 0.75rem;
  border-radius: 6px;
  margin: 1rem 0;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.uploaded {
  background: #e3f2fd;
  color: #1976d2;
}

.status-badge.processing {
  background: #fff3e0;
  color: #f57c00;
}

.status-badge.completed {
  background: #e8f5e9;
  color: #388e3c;
}

.status-badge.failed {
  background: #ffebee;
  color: #d32f2f;
}

.qa-input {
  display: flex;
  gap: 1rem;
  margin: 1rem 0;
}

.qa-input input {
  flex: 1;
  padding: 0.75rem;
  border: 2px solid #ddd;
  border-radius: 6px;
  font-size: 1rem;
}

.qa-answer {
  margin-top: 2rem;
  padding: 1.5rem;
  background: #f8f9fa;
  border-radius: 8px;
}

.answer-text {
  margin-bottom: 1.5rem;
}

.confidence {
  display: inline-block;
  margin-left: 1rem;
  padding: 0.25rem 0.5rem;
  background: #667eea;
  color: white;
  border-radius: 4px;
  font-size: 0.85rem;
}

.answer-sources {
  border-top: 1px solid #ddd;
  padding-top: 1rem;
}

.source {
  display: flex;
  gap: 0.5rem;
  padding: 0.5rem;
  margin: 0.5rem 0;
  background: white;
  border-radius: 4px;
  font-size: 0.9rem;
}

.source-number {
  font-weight: 600;
  color: #667eea;
}

.source-score {
  margin-left: auto;
  color: #666;
}
'''


def save_react_components(output_dir: str = "./frontend"):
    """Save React components to files."""
    from pathlib import Path
    
    output_path = Path(output_dir) / "src"
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save components
    components = {
        'DocumentUpload.jsx': DOCUMENT_UPLOAD_COMPONENT,
        'DocumentViewer.jsx': DOCUMENT_VIEWER_COMPONENT,
        'QAInterface.jsx': QA_INTERFACE_COMPONENT,
        'App.jsx': APP_COMPONENT,
        'App.css': CSS_STYLES
    }
    
    for filename, content in components.items():
        file_path = output_path / filename
        with open(file_path, 'w') as f:
            f.write(content.strip())
        print(f"✓ Created: {file_path}")
    
    # Create package.json
    package_json = '''{
  "name": "icr-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build"
  }
}'''
    
    with open(output_path.parent / 'package.json', 'w') as f:
        f.write(package_json)
    print(f"✓ Created: {output_path.parent / 'package.json'}")
    
    print("\nTo run the frontend:")
    print(f"  cd {output_dir}")
    print("  npm install")
    print("  npm start")


if __name__ == '__main__':
    print("React Component Templates for ICR Frontend")
    print("=" * 60)
    print("\nComponents available:")
    print("  - DocumentUpload: File upload interface")
    print("  - DocumentViewer: Document status and results")
    print("  - QAInterface: Question answering interface")
    print("  - App: Main application")
    print("  - App.css: Styling")
    print("\nUse save_react_components() to export files")
