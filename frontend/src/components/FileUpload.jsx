/**
 * FileUpload.jsx — Drag-and-drop file upload component
 *
 * Uses react-dropzone for a smooth drag-and-drop experience.
 * Shows file info, upload progress, and error messages.
 */

import { AlertCircle, CheckCircle, Loader2, Upload, X } from 'lucide-react';
import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadFile } from '../services/api';

function FileUpload({ onUploadComplete }) {
  const [status, setStatus] = useState('idle'); // idle | selected | uploading | success | error
  const [error, setError] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [progress, setProgress] = useState(0);

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const getFileIcon = (filename) => {
    const ext = filename?.split('.').pop()?.toLowerCase();
    if (ext === 'csv') return '📄';
    if (['xlsx', 'xls'].includes(ext)) return '📊';
    return '📁';
  };

  const handleUpload = async (file) => {
    setStatus('uploading');
    setProgress(0);
    setError('');

    try {
      // Simulate progress (real progress needs XMLHttpRequest or fetch with streams)
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) { clearInterval(progressInterval); return 90; }
          return prev + Math.random() * 15;
        });
      }, 200);

      const result = await uploadFile(file);

      clearInterval(progressInterval);
      setProgress(100);
      setStatus('success');
      onUploadComplete(result);
    } catch (err) {
      setStatus('error');
      setError(err.response?.data?.detail || 'Upload failed. Please try again.');
    }
  };

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;
    const file = acceptedFiles[0];
    setSelectedFile(file);
    setStatus('selected');
    // Auto-upload immediately
    await handleUpload(file);
  }, [onUploadComplete]);

  const reset = () => {
    setStatus('idle');
    setSelectedFile(null);
    setError('');
    setProgress(0);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
    disabled: status === 'uploading',
  });

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={`
          relative border-2 border-dashed rounded-xl text-center cursor-pointer
          transition-all duration-200
          ${status === 'uploading' ? 'pointer-events-none' : ''}
          ${isDragActive
            ? 'border-blue-500 bg-blue-50 scale-[1.01]'
            : 'border-gray-300 bg-white hover:border-blue-400 hover:bg-blue-50/30'}
          ${status === 'success' ? 'border-green-400 bg-green-50' : ''}
          ${status === 'error' ? 'border-red-400 bg-red-50' : ''}
          ${selectedFile ? 'p-6' : 'p-12'}
        `}
      >
        <input {...getInputProps()} />

        {/* Idle state — no file selected */}
        {(status === 'idle') && (
          <div>
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Upload className="h-8 w-8 text-blue-600" />
            </div>
            <p className="text-lg font-medium text-gray-700">
              {isDragActive ? 'Drop your file here...' : 'Drag & drop your Excel or CSV file'}
            </p>
            <p className="text-sm text-gray-500 mt-2">
              Supports .csv, .xlsx, .xls — Max 50 MB
            </p>
            <div className="flex items-center justify-center gap-4 mt-4">
              <span className="inline-flex items-center gap-1 text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">
                📄 CSV
              </span>
              <span className="inline-flex items-center gap-1 text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">
                📊 XLSX
              </span>
              <span className="inline-flex items-center gap-1 text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">
                📊 XLS
              </span>
            </div>
          </div>
        )}

        {/* Uploading state */}
        {status === 'uploading' && selectedFile && (
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <span className="text-lg">{getFileIcon(selectedFile.name)}</span>
              </div>
              <div className="flex-1 text-left min-w-0">
                <p className="font-medium text-gray-800 truncate">{selectedFile.name}</p>
                <p className="text-xs text-gray-500">{formatFileSize(selectedFile.size)}</p>
              </div>
              <Loader2 className="h-5 w-5 text-blue-500 animate-spin flex-shrink-0" />
            </div>
            {/* Progress bar */}
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${Math.min(progress, 100)}%` }}
              />
            </div>
            <p className="text-sm text-blue-600">
              Uploading & analyzing your data... {Math.round(progress)}%
            </p>
          </div>
        )}

        {/* Success state */}
        {status === 'success' && selectedFile && (
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <CheckCircle className="h-5 w-5 text-green-600" />
            </div>
            <div className="flex-1 text-left min-w-0">
              <p className="font-medium text-gray-800 truncate">{selectedFile.name}</p>
              <p className="text-xs text-green-600">Uploaded successfully — preview below</p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); reset(); }}
              className="p-1 hover:bg-green-200 rounded transition-colors flex-shrink-0"
              title="Upload a different file"
            >
              <X className="h-4 w-4 text-gray-500" />
            </button>
          </div>
        )}

        {/* Error state */}
        {status === 'error' && (
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <AlertCircle className="h-5 w-5 text-red-600" />
              </div>
              <div className="flex-1 text-left min-w-0">
                <p className="font-medium text-red-700">Upload failed</p>
                <p className="text-xs text-red-500">{error}</p>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); reset(); }}
                className="p-1 hover:bg-red-200 rounded transition-colors flex-shrink-0"
                title="Try again"
              >
                <X className="h-4 w-4 text-gray-500" />
              </button>
            </div>
            <p className="text-sm text-gray-500">Click or drop a file to try again</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default FileUpload;
