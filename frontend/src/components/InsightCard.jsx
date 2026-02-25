/**
 * InsightCard.jsx — Displays a single AI-generated insight
 */

import { Lightbulb } from 'lucide-react';

function InsightCard({ title, content, type = 'info' }) {
    const colorMap = {
        info: 'bg-blue-50 border-blue-200 text-blue-800',
        warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
        success: 'bg-green-50 border-green-200 text-green-800',
        danger: 'bg-red-50 border-red-200 text-red-800',
    };

    return (
        <div className={`rounded-lg border p-4 ${colorMap[type]}`}>
            <div className="flex items-start gap-3">
                <Lightbulb className="h-5 w-5 mt-0.5 flex-shrink-0" />
                <div>
                    {title && <h4 className="font-semibold mb-1">{title}</h4>}
                    <p className="text-sm">{content}</p>
                </div>
            </div>
        </div>
    );
}

export default InsightCard;
