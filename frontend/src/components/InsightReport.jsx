/**
 * InsightReport.jsx - AI-Generated Insight Display Component
 *
 * Renders the Gemini-generated markdown insights in a beautiful UI.
 * Supports loading state, error handling, and section-based layout.
 */

import { useState } from "react";
import { Sparkles, Loader2, AlertTriangle, ChevronDown, ChevronRight, RefreshCw } from "lucide-react";

function MarkdownSection({ content }) {
  /* Simple markdown-to-JSX renderer for our structured content */
  if (!content) return null;
  const lines = content.split("\n");
  const elements = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.startsWith("- **") && line.includes("**")) {
      /* Bold list item: - **Key**: Value */
      const match = line.match(/^- \*\*(.+?)\*\*:?\s*(.*)/);
      if (match) {
        elements.push(
          <li key={i} className="flex gap-1 mb-1">
            <span className="font-semibold text-gray-800">{match[1]}:</span>
            <span className="text-gray-600">{match[2]}</span>
          </li>
        );
        continue;
      }
    }

    if (line.startsWith("- ")) {
      elements.push(
        <li key={i} className="text-gray-600 mb-1 ml-1">
          {line.slice(2)}
        </li>
      );
      continue;
    }

    if (line.startsWith("### ")) {
      elements.push(
        <h4 key={i} className="text-sm font-semibold text-gray-800 mt-3 mb-1">
          {line.slice(4)}
        </h4>
      );
      continue;
    }

    if (line.trim() === "") {
      elements.push(<div key={i} className="h-2" />);
      continue;
    }

    /* Bold text within a paragraph */
    const parts = line.split(/\*\*(.+?)\*\*/g);
    if (parts.length > 1) {
      elements.push(
        <p key={i} className="text-gray-600 text-sm mb-1">
          {parts.map((part, j) =>
            j % 2 === 1 ? (
              <strong key={j} className="text-gray-800">{part}</strong>
            ) : (
              <span key={j}>{part}</span>
            )
          )}
        </p>
      );
      continue;
    }

    elements.push(
      <p key={i} className="text-gray-600 text-sm mb-1">
        {line}
      </p>
    );
  }

  return <div>{elements}</div>;
}

function InsightSection({ title, content, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition text-left"
      >
        <span className="text-sm font-semibold text-gray-700">{title}</span>
        {open ? (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400" />
        )}
      </button>
      {open && (
        <div className="px-4 py-3 bg-white">
          <MarkdownSection content={content} />
        </div>
      )}
    </div>
  );
}

export default function InsightReport({ insights, loading, error, onRegenerate }) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <div className="relative">
          <Sparkles className="w-8 h-8 text-indigo-400 animate-pulse" />
          <Loader2 className="w-6 h-6 text-indigo-600 animate-spin absolute -top-1 -right-2" />
        </div>
        <p className="text-gray-600 font-medium mt-4">Generating AI Insights...</p>
        <p className="text-gray-400 text-sm mt-1">Gemini is analyzing your data</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <h3 className="text-sm font-medium text-red-700">Insight Generation Failed</h3>
        <p className="text-red-600 text-xs mt-1 max-w-md mx-auto">{error}</p>
        {onRegenerate && (
          <button
            onClick={onRegenerate}
            className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700 transition text-xs"
          >
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        )}
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="bg-white rounded-xl border p-8 text-center">
        <Sparkles className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <h3 className="text-sm font-medium text-gray-500">No Insights Generated Yet</h3>
        <p className="text-xs text-gray-400 mt-1">Click the button below to generate AI insights.</p>
        {onRegenerate && (
          <button
            onClick={onRegenerate}
            className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition text-sm"
          >
            <Sparkles className="w-4 h-4" /> Generate Insights
          </button>
        )}
      </div>
    );
  }

  /* Parse sections from the response */
  const sections = insights.sections || {};
  const sectionOrder = [
    { key: "executive_summary", title: "Executive Summary" },
    { key: "key_findings", title: "Key Findings" },
    { key: "trends_and_patterns", title: "Trends & Patterns" },
    { key: "anomalies_and_concerns", title: "Anomalies & Concerns" },
    { key: "correlations_and_relationships", title: "Correlations & Relationships" },
    { key: "predictions_and_forecasts", title: "Predictions & Forecasts" },
    { key: "actionable_recommendations", title: "Actionable Recommendations" },
    { key: "questions_for_further_analysis", title: "Questions for Further Analysis" },
  ];

  const hasSections = sectionOrder.some((s) => sections[s.key]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-indigo-500" />
          <h3 className="text-lg font-semibold text-gray-900">AI-Powered Insights</h3>
          <span className="text-xs bg-indigo-100 text-indigo-600 px-2 py-0.5 rounded-full">Gemini</span>
        </div>
        {onRegenerate && (
          <button
            onClick={onRegenerate}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 border rounded-lg text-xs text-gray-600 hover:bg-gray-50 transition"
          >
            <RefreshCw className="w-3 h-3" /> Regenerate
          </button>
        )}
      </div>

      {/* Structured sections */}
      {hasSections ? (
        <div className="space-y-2">
          {sectionOrder.map((s, i) =>
            sections[s.key] ? (
              <InsightSection
                key={s.key}
                title={s.title}
                content={sections[s.key]}
                defaultOpen={i < 3}
              />
            ) : null
          )}
        </div>
      ) : (
        /* Fallback: render raw insights markdown */
        <div className="bg-white rounded-xl border p-5">
          <MarkdownSection content={insights.insights} />
        </div>
      )}
    </div>
  );
}
