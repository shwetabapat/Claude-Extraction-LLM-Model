import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { RotatingLines } from 'react-loader-spinner';
import './App.css';

interface AnalysisResponse {
  insights: string;
  files_processed: string[];
  pages_sent?: number;
}

interface CombinedDocument {
  filename: string;
  base64_content: string;
}

function App() {
  const [files, setFiles] = useState<File[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState<string[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [combinedDoc, setCombinedDoc] = useState<CombinedDocument | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(prev => [...prev, ...acceptedFiles]);
    setError(null);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    }
  });

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const analyzeDocuments = async () => {
    if (files.length < 1) {
      setError('Please upload at least 1 document');
      return;
    }

    setIsAnalyzing(true);
    setProgress([]);
    setAnalysis(null);
    setError(null);

    try {
      // Step 1: Combine documents
      setProgress(prev => [...prev, "Combining documents..."]);
      const formData = new FormData();
      files.forEach(file => {
        formData.append('files', file);
      });

      const combineResponse = await fetch('http://localhost:8000/api/combine-documents', {
        method: 'POST',
        body: formData,
      });

      if (!combineResponse.ok) {
        const errorData = await combineResponse.json();
        throw new Error(errorData.detail || `Error combining documents: ${combineResponse.status}`);
      }

      const combinedDoc = await combineResponse.json();
      setCombinedDoc(combinedDoc);
      setProgress(prev => [...prev, "Documents combined successfully"]);

      // Step 2: Analyze the combined document
      setProgress(prev => [...prev, "Analyzing combined document..."]);
      const analyzeFormData = new FormData();
      
      // Convert base64 to Blob
      const byteCharacters = atob(combinedDoc.base64_content);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: 'application/pdf' });
      const combinedFile = new File([blob], combinedDoc.filename, { type: 'application/pdf' });
      
      analyzeFormData.append('files', combinedFile);

      const analyzeResponse = await fetch('http://localhost:8000/api/analyze-documents', {
        method: 'POST',
        body: analyzeFormData,
      });

      if (!analyzeResponse.ok) {
        const errorData = await analyzeResponse.json();
        throw new Error(errorData.detail || `Error analyzing documents: ${analyzeResponse.status}`);
      }

      const result = await analyzeResponse.json();
      setProgress(prev => [...prev, "Analysis complete"]);
      setAnalysis(result);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error processing documents');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const downloadCombinedDocument = () => {
    if (!combinedDoc) return;
    
    const byteCharacters = atob(combinedDoc.base64_content);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = combinedDoc.filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  return (
    <div className="App">
      {isAnalyzing && (
        <div className="loader-overlay">
          <RotatingLines
            strokeColor="#0666eb"
            strokeWidth="5"
            animationDuration="0.75"
            width="80"
            visible={true}
          />
        </div>
      )}
      <header className="App-header">
        <h1>Document Analysis</h1>
        <p>Upload your trade documents and get instant insights powered by AI</p>
      </header>
      <main>
        <div className="upload-section">
          <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
            <input {...getInputProps()} />
            {isDragActive ? (
              <p>Drop your documents here</p>
            ) : (
              <p>Drag and drop your documents here, or click to browse</p>
            )}
          </div>
          
          {files.length > 0 && (
            <div className="file-list">
              <h3>Selected Documents ({files.length})</h3>
              <ul>
                {files.map((file, index) => (
                  <li key={index}>
                    <span>{file.name}</span>
                    <button 
                      onClick={() => removeFile(index)}
                      className="remove-button"
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
              <button 
                onClick={analyzeDocuments} 
                disabled={isAnalyzing || files.length < 1}
                className="analyze-button"
              >
                <span>
                  {isAnalyzing ? 'Processing documents...' : 'Analyze Documents'}
                </span>
              </button>
            </div>
          )}
        </div>

        {error && (
          <div className="error-message">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            {error}
          </div>
        )}

        {progress.length > 0 && (
          <div className="progress-section">
            <h3>Processing Status</h3>
            <ul>
              {progress.map((message, index) => (
                <li key={index}>{message}</li>
              ))}
            </ul>
            {combinedDoc && (
              <button 
                onClick={downloadCombinedDocument}
                className="download-button"
              >
                <span>Download Combined Document</span>
              </button>
            )}
          </div>
        )}

        {analysis && (
          <div className="analysis-section">
            <h3>Analysis Results</h3>
            <div className="analysis-content">
              <h4>Key Insights</h4>
              <p>{analysis.insights}</p>
              
              <h4>Processed Documents</h4>
              <ul>
                {analysis.files_processed.map((filename, index) => (
                  <li key={index}>{filename}</li>
                ))}
              </ul>
              {analysis.pages_sent && (
                <p className="pages-info">
                  Pages analyzed: {analysis.pages_sent}
                </p>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App; 