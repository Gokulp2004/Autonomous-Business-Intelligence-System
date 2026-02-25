/**
 * AnomalyReport.jsx - Displays anomaly detection results
 *
 * Shows:
 *   - Summary cards (total anomalies, columns affected)
 *   - Per-column anomaly breakdown (Z-score + IQR)
 *   - Isolation Forest multi-variate results
 */
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Search,
  ShieldAlert,
} from "lucide-react";
import { useState } from "react";

function AnomalyColumnCard({ col, data }) {
  const [expanded, setExpanded] = useState(false);
  const total = data.total_anomalies || 0;

  return (
    <div className="bg-white rounded-lg border mb-2 overflow-hidden">
      <button
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition"
        onClick={() => setExpanded(!expanded)}
      >
        {total > 0 ? (
          <AlertTriangle className="w-4 h-4 text-yellow-500 flex-shrink-0" />
        ) : (
          <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
        )}
        <span className="text-sm font-medium text-gray-900 flex-1">{col}</span>
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${total > 0
              ? "bg-yellow-100 text-yellow-700"
              : "bg-green-100 text-green-700"
            }`}
        >
          {total > 0 ? `${total} anomalies` : "Clean"}
        </span>
        {total > 0 &&
          (expanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400" />
          ))}
      </button>

      {expanded && total > 0 && (
        <div className="px-4 pb-4 space-y-3 border-t">
          {/* Z-score results */}
          {data.zscore && data.zscore.count > 0 && (
            <div className="mt-3">
              <p className="text-xs font-semibold text-gray-500 uppercase mb-1">
                Z-Score (|z| &gt; {data.zscore.threshold})
              </p>
              <p className="text-xs text-gray-600 mb-2">
                {data.zscore.count} outliers ({data.zscore.pct}% of data)
              </p>
              {data.zscore.anomalies && data.zscore.anomalies.length > 0 && (
                <div className="overflow-auto max-h-40">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-gray-400 uppercase">
                        <th className="text-left py-1">Row</th>
                        <th className="text-right py-1">Value</th>
                        <th className="text-right py-1">Z-Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.zscore.anomalies.slice(0, 10).map((a, i) => (
                        <tr key={i} className="border-t border-gray-100">
                          <td className="py-1">{a.index}</td>
                          <td className="text-right font-mono">{a.value}</td>
                          <td className="text-right font-mono text-red-600">
                            {a.z_score}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* IQR results */}
          {data.iqr && data.iqr.count > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-1">
                IQR Method
              </p>
              <p className="text-xs text-gray-600 mb-1">
                {data.iqr.count} outliers ({data.iqr.pct}%) — bounds: [
                {data.iqr.lower_bound}, {data.iqr.upper_bound}]
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AnomalyReport({ anomalies }) {
  if (!anomalies || anomalies.status === "no_numeric_columns") {
    return (
      <div className="bg-gray-50 rounded-xl border p-8 text-center">
        <Search className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <p className="text-gray-500">No numeric columns to analyze for anomalies.</p>
      </div>
    );
  }

  const summary = anomalies.summary || {};
  const perColumn = anomalies.per_column || {};
  const isoForest = anomalies.isolation_forest;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <ShieldAlert className="w-5 h-5 text-yellow-500" />
        <h2 className="text-lg font-bold text-gray-900">Anomaly Detection</h2>
        <span className="ml-auto text-xs text-gray-500">
          {summary.total_anomalies_found || 0} anomalies in{" "}
          {summary.columns_with_anomalies || 0}/{summary.columns_analyzed || 0} columns
        </span>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-white rounded-lg border p-4 text-center">
          <p className="text-xs text-gray-500 uppercase">Total Anomalies</p>
          <p className="text-2xl font-bold text-yellow-600">
            {summary.total_anomalies_found || 0}
          </p>
        </div>
        <div className="bg-white rounded-lg border p-4 text-center">
          <p className="text-xs text-gray-500 uppercase">Columns Affected</p>
          <p className="text-2xl font-bold text-gray-900">
            {summary.columns_with_anomalies || 0}
          </p>
        </div>
        <div className="bg-white rounded-lg border p-4 text-center">
          <p className="text-xs text-gray-500 uppercase">Columns Analyzed</p>
          <p className="text-2xl font-bold text-gray-900">
            {summary.columns_analyzed || 0}
          </p>
        </div>
        <div className="bg-white rounded-lg border p-4 text-center">
          <p className="text-xs text-gray-500 uppercase">Method</p>
          <p className="text-sm font-bold text-gray-900 mt-1">
            Z-Score + IQR + IF
          </p>
        </div>
      </div>

      {/* Per-column Results */}
      {Object.keys(perColumn).length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            Per-Column Analysis
          </h3>
          {Object.entries(perColumn).map(([col, data]) => (
            <AnomalyColumnCard key={col} col={col} data={data} />
          ))}
        </div>
      )}

      {/* Isolation Forest */}
      {isoForest && (
        <div className="bg-white rounded-xl border p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">
            Isolation Forest (Multi-variate)
          </h3>
          <p className="text-xs text-gray-600 mb-3">
            Detected <strong>{isoForest.anomaly_count}</strong> anomalous rows (
            {isoForest.anomaly_pct}%) across all numeric features simultaneously.
          </p>
          {isoForest.top_anomalies && isoForest.top_anomalies.length > 0 && (
            <div className="overflow-auto max-h-64">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-500 uppercase border-b">
                    <th className="text-left py-2">Row</th>
                    <th className="text-right py-2">Score</th>
                    <th className="text-left py-2 pl-3">Values</th>
                  </tr>
                </thead>
                <tbody>
                  {isoForest.top_anomalies.slice(0, 10).map((a, i) => (
                    <tr key={i} className="border-b border-gray-100">
                      <td className="py-1.5">{a.row_index}</td>
                      <td className="text-right font-mono text-red-600">
                        {a.anomaly_score}
                      </td>
                      <td className="py-1.5 pl-3 font-mono text-gray-600">
                        {Object.entries(a.values || {})
                          .map(([k, v]) => `${k}=${v}`)
                          .join(", ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
