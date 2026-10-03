import { useState, useRef } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export default function PdfScanner() {
  const [file, setFile] = useState<File | null>(null)
  const [scanning, setScanning] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0])
      setResult(null)
      setError('')
    }
  }

  const handleScan = async () => {
    if (!file) return

    setScanning(true)
    setError('')
    setResult(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`${API_BASE_URL}/api/scan`, {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || data.message || 'An error occurred during scanning.')
      }

      setResult(data)
    } catch (err: any) {
      setError(err.message || 'Failed to connect to the scanner service.')
    } finally {
      setScanning(false)
      // reset file input so the same file can be uploaded again if needed
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      setFile(null)
    }
  }

  return (
    <section className="pdf-scanner-wrap" aria-labelledby="scanner-heading">
      <h2 id="scanner-heading">Local PDF Safety Scanner</h2>
      <p>Select a local PDF to check its structure and scan for embedded threats.</p>
      
      <div className="scanner-controls">
        <label htmlFor="pdf-upload" className="sr-only">Upload PDF</label>
        <input 
          id="pdf-upload"
          type="file" 
          accept="application/pdf,.pdf" 
          onChange={handleFileChange}
          ref={fileInputRef}
          disabled={scanning}
        />
        <button 
          onClick={handleScan} 
          disabled={!file || scanning}
          className="primary-action"
        >
          {scanning ? 'Scanning...' : 'Scan PDF'}
        </button>
      </div>

      {error && <p className="status-message error">{error}</p>}

      {result && (
        <div className={`scan-result status-${result.status.toLowerCase()}`}>
          <h3>Scan Status: {result.status.replace(/_/g, ' ')}</h3>
          <p>{result.message}</p>
          
          {result.indicators && result.indicators.length > 0 && (
            <div className="indicators">
              <h4>Suspicious Indicators Found:</h4>
              <ul>
                {result.indicators.map((ind: string, idx: number) => (
                  <li key={idx}>{ind}</li>
                ))}
              </ul>
            </div>
          )}
          
          {result.sha256 && (
            <p className="hash">
              <small>SHA-256: {result.sha256}</small>
            </p>
          )}
          
          {result.status === 'NO_THREATS_DETECTED' && (
            <p className="disclaimer">
              <small><strong>Note:</strong> No automated scan can guarantee a file is 100% safe.</small>
            </p>
          )}
        </div>
      )}
    </section>
  )
}
