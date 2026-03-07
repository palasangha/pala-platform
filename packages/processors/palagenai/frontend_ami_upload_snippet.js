/**
 * AMI Sets Upload Component
 * Add this to your bulk processing results page
 */

// Add this button to your bulk results UI
const AMIUploadButton = ({ jobId, authToken }) => {
  const [uploading, setUploading] = React.useState(false);
  const [result, setResult] = React.useState(null);
  const [error, setError] = React.useState(null);

  const handleUploadViaAMI = async () => {
    setUploading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('/api/archipelago/push-bulk-ami', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          job_id: jobId,
          collection_title: 'Bhushanji Documents Collection',
          // collection_id: 123  // Optional: specify existing collection
        })
      });

      const data = await response.json();

      if (data.success) {
        setResult(data);

        // Show success message
        console.log('AMI Set Created:', data);

        // Optionally auto-open processing URL
        const processingUrl = data.message.split('Process it at: ')[1];
        if (processingUrl && confirm('AMI Set created! Open processing page?')) {
          window.open(processingUrl, '_blank');
        }
      } else {
        setError(data.error || 'Upload failed');
      }
    } catch (err) {
      console.error('AMI upload error:', err);
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="ami-upload-section">
      <h3>Upload to Archipelago via AMI Sets</h3>

      <button
        onClick={handleUploadViaAMI}
        disabled={uploading}
        className="btn btn-primary"
      >
        {uploading ? (
          <>
            <span className="spinner"></span>
            Creating AMI Set...
          </>
        ) : (
          'Upload to Archipelago (AMI)'
        )}
      </button>

      {result && (
        <div className="alert alert-success mt-3">
          <h4>✅ AMI Set Created Successfully!</h4>
          <dl>
            <dt>AMI Set ID:</dt>
            <dd>{result.ami_set_id}</dd>

            <dt>Name:</dt>
            <dd>{result.ami_set_name}</dd>

            <dt>Documents:</dt>
            <dd>{result.total_documents}</dd>

            <dt>CSV File ID:</dt>
            <dd>{result.csv_fid}</dd>

            <dt>ZIP File ID:</dt>
            <dd>{result.zip_fid}</dd>
          </dl>

          <div className="next-steps">
            <h5>Next Steps:</h5>
            <ol>
              <li>
                <a
                  href={result.message.split('Process it at: ')[1]}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-link"
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
        </div>
      )}

      {error && (
        <div className="alert alert-danger mt-3">
          <h4>❌ Upload Failed</h4>
          <p>{error}</p>
        </div>
      )}

      <div className="info-box mt-3">
        <h5>About AMI Sets Upload</h5>
        <p>
          This new upload method provides:
        </p>
        <ul>
          <li>✅ Real Drupal file entities (no fake IDs)</li>
          <li>✅ Automatic thumbnail generation</li>
          <li>✅ Full PDF metadata extraction</li>
          <li>✅ No duplicate documents</li>
          <li>✅ Complete Archipelago integration</li>
        </ul>
      </div>
    </div>
  );
};

// Plain HTML/JavaScript version (no React)
function createAMIUploadUI(containerId, jobId, authToken) {
  const container = document.getElementById(containerId);

  container.innerHTML = `
    <div class="ami-upload-section">
      <h3>Upload to Archipelago via AMI Sets</h3>

      <button id="ami-upload-btn" class="btn btn-primary">
        Upload to Archipelago (AMI)
      </button>

      <div id="ami-result" class="mt-3" style="display: none;"></div>
      <div id="ami-error" class="alert alert-danger mt-3" style="display: none;"></div>

      <div class="info-box mt-3">
        <h5>About AMI Sets Upload</h5>
        <p>This new upload method provides:</p>
        <ul>
          <li>✅ Real Drupal file entities (no fake IDs)</li>
          <li>✅ Automatic thumbnail generation</li>
          <li>✅ Full PDF metadata extraction</li>
          <li>✅ No duplicate documents</li>
          <li>✅ Complete Archipelago integration</li>
        </ul>
      </div>
    </div>
  `;

  document.getElementById('ami-upload-btn').addEventListener('click', async () => {
    const btn = document.getElementById('ami-upload-btn');
    const resultDiv = document.getElementById('ami-result');
    const errorDiv = document.getElementById('ami-error');

    btn.disabled = true;
    btn.textContent = 'Creating AMI Set...';
    resultDiv.style.display = 'none';
    errorDiv.style.display = 'none';

    try {
      const response = await fetch('/api/archipelago/push-bulk-ami', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          job_id: jobId,
          collection_title: 'Bhushanji Documents Collection'
        })
      });

      const data = await response.json();

      if (data.success) {
        const processingUrl = data.message.split('Process it at: ')[1];

        resultDiv.innerHTML = `
          <div class="alert alert-success">
            <h4>✅ AMI Set Created Successfully!</h4>
            <dl>
              <dt>AMI Set ID:</dt>
              <dd>${data.ami_set_id}</dd>
              <dt>Name:</dt>
              <dd>${data.ami_set_name}</dd>
              <dt>Documents:</dt>
              <dd>${data.total_documents}</dd>
            </dl>
            <a href="${processingUrl}" target="_blank" class="btn btn-primary">
              Open Processing Page →
            </a>
          </div>
        `;
        resultDiv.style.display = 'block';

        if (confirm('AMI Set created! Open processing page?')) {
          window.open(processingUrl, '_blank');
        }
      } else {
        errorDiv.textContent = data.error || 'Upload failed';
        errorDiv.style.display = 'block';
      }
    } catch (err) {
      errorDiv.textContent = 'Error: ' + err.message;
      errorDiv.style.display = 'block';
    } finally {
      btn.disabled = false;
      btn.textContent = 'Upload to Archipelago (AMI)';
    }
  });
}

// Usage example:
// createAMIUploadUI('ami-container', 'bulk_job_12345', 'your-jwt-token');

export { AMIUploadButton, createAMIUploadUI };
