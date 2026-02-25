/**
 * HomePage.jsx — Landing page with file upload and data preview
 *
 * This is the first page users see. The flow:
 *   1. Drag-and-drop or browse to upload a file
 *   2. See a rich data preview with column profiles
 *   3. Click "Run Analysis" to start the pipeline
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import DataPreview from '../components/DataPreview';
import FileUpload from '../components/FileUpload';

function HomePage() {
  const [uploadResult, setUploadResult] = useState(null);
  const navigate = useNavigate();

  const handleAnalyze = (fileId) => {
    // Navigate to analysis page (wired up in Step 5)
    navigate(`/analysis?file_id=${fileId}`);
  };

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold text-gray-900">
          Autonomous Business Intelligence
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Upload your data. Get instant insights, visualizations, and
          AI-powered business recommendations — automatically.
        </p>
      </div>

      {/* Upload Section */}
      <FileUpload onUploadComplete={setUploadResult} />

      {/* Data Preview Section — appears after successful upload */}
      {uploadResult && (
        <DataPreview data={uploadResult} onAnalyze={handleAnalyze} />
      )}
    </div>
  );
}

export default HomePage;
