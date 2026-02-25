/**
 * ReportDownload.jsx — Report download buttons (placeholder)
 * Will be built in Step 8.
 */

import { FileDown } from 'lucide-react';

function ReportDownload({ fileId }) {
    // TODO: Implement in Step 8
    return (
        <div className="flex gap-3">
            <button
                disabled
                className="flex items-center gap-2 bg-gray-200 text-gray-500 px-4 py-2 rounded-lg cursor-not-allowed"
            >
                <FileDown className="h-4 w-4" />
                Download PDF
            </button>
            <button
                disabled
                className="flex items-center gap-2 bg-gray-200 text-gray-500 px-4 py-2 rounded-lg cursor-not-allowed"
            >
                <FileDown className="h-4 w-4" />
                Download PPT
            </button>
        </div>
    );
}

export default ReportDownload;
