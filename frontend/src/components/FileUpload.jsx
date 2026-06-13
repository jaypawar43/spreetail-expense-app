import { useState, useCallback, useRef } from 'react';
import { uploadCSV } from '../api/client';

/**
 * FileUpload — Drag-and-drop CSV upload component.
 */
export default function FileUpload({ onUploadComplete }) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.csv')) {
      setSelectedFile(file);
      setError(null);
    } else {
      setError('Please upload a CSV file.');
    }
  }, []);

  const handleFileSelect = useCallback((e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
    }
  }, []);

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setProgress(0);
    setError(null);

    // Simulate progress while upload happens
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90;
        }
        return prev + Math.random() * 15;
      });
    }, 200);

    try {
      const session = await uploadCSV(selectedFile);
      clearInterval(progressInterval);
      setProgress(100);

      // Brief delay to show 100% before transitioning
      setTimeout(() => {
        onUploadComplete(session);
      }, 500);

    } catch (err) {
      clearInterval(progressInterval);
      setProgress(0);
      setError(
        err.response?.data?.error ||
        'Failed to upload file. Is the backend running on port 8000?'
      );
      setUploading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="max-w-2xl mx-auto animate-slide-up">
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold mb-2">
          <span className="gradient-text">Upload Expenses</span>
        </h2>
        <p className="text-white/40 text-sm">
          Upload your CSV file to analyze and split shared expenses
        </p>
      </div>

      {/* Drop Zone */}
      <div
        className={`dropzone mb-6 ${isDragging ? 'active' : ''} ${selectedFile ? 'border-brand-500/30' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
        id="csv-dropzone"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileSelect}
          className="hidden"
          id="csv-file-input"
        />

        {!selectedFile ? (
          <>
            <div className="text-5xl mb-4 opacity-60">📄</div>
            <p className="text-white/60 text-lg font-medium mb-2">
              Drag & drop your CSV file here
            </p>
            <p className="text-white/30 text-sm">
              or click to browse • Supports <span className="font-mono text-brand-400">.csv</span> files
            </p>
          </>
        ) : (
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl flex items-center justify-center text-2xl"
              style={{ background: 'rgba(76, 110, 245, 0.1)' }}>
              📊
            </div>
            <div className="text-left">
              <p className="text-white font-semibold">{selectedFile.name}</p>
              <p className="text-white/40 text-sm">{formatFileSize(selectedFile.size)}</p>
            </div>
            {!uploading && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                }}
                className="ml-auto text-white/30 hover:text-red-400 transition-colors p-2"
                id="remove-file-btn"
              >
                ✕
              </button>
            )}
          </div>
        )}
      </div>

      {/* Progress Bar */}
      {uploading && (
        <div className="mb-6 animate-fade-in">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-white/50">
              {progress < 100 ? 'Analyzing expenses & detecting anomalies...' : 'Complete!'}
            </span>
            <span className="text-brand-400 font-mono">{Math.round(progress)}%</span>
          </div>
          <div className="w-full h-2 rounded-full overflow-hidden"
            style={{ background: 'rgba(255, 255, 255, 0.06)' }}>
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${progress}%`,
                background: progress >= 100
                  ? 'var(--gradient-success)'
                  : 'var(--gradient-brand)',
              }}
            />
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-6 p-4 rounded-xl border border-red-500/20 bg-red-500/[0.06] animate-fade-in"
          id="upload-error">
          <p className="text-red-400 text-sm flex items-center gap-2">
            <span>⚠️</span> {error}
          </p>
        </div>
      )}

      {/* Upload Button */}
      {selectedFile && !uploading && (
        <button
          onClick={handleUpload}
          className="btn-primary w-full text-center animate-slide-up"
          id="upload-btn"
        >
          🚀 Upload & Analyze
        </button>
      )}

      {/* Expected Format */}
      <div className="mt-8 glass-card p-5">
        <h3 className="text-sm font-semibold text-white/60 mb-3">Expected CSV Format</h3>
        <div className="overflow-x-auto">
          <code className="text-xs font-mono text-brand-300 block whitespace-nowrap">
            date, description, paid_by, amount, currency, split_type, split_with, split_details, notes
          </code>
        </div>
        <div className="mt-3 flex gap-2 flex-wrap">
          {['Equal', 'Unequal', 'Percentage', 'Share'].map(type => (
            <span key={type} className="badge-blue text-[10px]">{type} splits</span>
          ))}
          <span className="badge-purple text-[10px]">Multi-currency</span>
          <span className="badge-yellow text-[10px]">Settlements</span>
        </div>
      </div>
    </div>
  );
}
