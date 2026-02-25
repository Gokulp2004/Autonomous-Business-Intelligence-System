/**
 * CleaningReport.jsx — Visual display of the automated cleaning pipeline results.
 *
 * Shows:
 *   - Before/After summary cards
 *   - Step-by-step actions with severity badges
 *   - Expandable details per step
 */
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Info,
  Sparkles,
  XCircle,
} from "lucide-react";
import { useState } from "react";

const severityConfig = {
  success: {
    icon: CheckCircle2,
    bg: "bg-green-50",
    border: "border-green-200",
    badge: "bg-green-100 text-green-700",
    text: "text-green-700",
  },
  info: {
    icon: Info,
    bg: "bg-blue-50",
    border: "border-blue-200",
    badge: "bg-blue-100 text-blue-700",
    text: "text-blue-700",
  },
  warning: {
    icon: AlertTriangle,
    bg: "bg-yellow-50",
    border: "border-yellow-200",
    badge: "bg-yellow-100 text-yellow-700",
    text: "text-yellow-700",
  },
  danger: {
    icon: XCircle,
    bg: "bg-red-50",
    border: "border-red-200",
    badge: "bg-red-100 text-red-700",
    text: "text-red-700",
  },
};

function SummaryCard({ label, before, after, improved }) {
  return (
    <div className="bg-white rounded-lg border p-4 text-center">
      <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</p>
      <div className="flex items-center justify-center gap-2">
        <span className="text-lg font-mono text-gray-400">{before}</span>
        <ArrowRight className="w-4 h-4 text-gray-400" />
        <span className={`text-lg font-bold ${improved ? "text-green-600" : "text-gray-900"}`}>
          {after}
        </span>
      </div>
    </div>
  );
}

function ActionRow({ action, index }) {
  const [expanded, setExpanded] = useState(false);
  const config = severityConfig[action.severity] || severityConfig.info;
  const Icon = config.icon;
  const hasDetails = action.details && action.details.length > 0;

  return (
    <div className={`${config.bg} ${config.border} border rounded-lg mb-2 overflow-hidden`}>
      <button
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:opacity-90 transition"
        onClick={() => hasDetails && setExpanded(!expanded)}
      >
        <span className="text-xs font-bold text-gray-400 w-5">{index + 1}</span>
        <Icon className={`w-4 h-4 flex-shrink-0 ${config.text}`} />
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium text-gray-900">{action.step}</span>
          <span className="block text-xs text-gray-600 mt-0.5 truncate-2">
            {action.detail}
          </span>
        </div>
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${config.badge} flex-shrink-0`}
        >
          {action.affected > 0 ? `${action.affected} changed` : "OK"}
        </span>
        {hasDetails && (
          expanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
          )
        )}
      </button>

      {expanded && hasDetails && (
        <div className="px-4 pb-3 border-t border-gray-200/50">
          <table className="w-full text-xs mt-2">
            <thead>
              <tr className="text-gray-500 uppercase tracking-wide">
                <th className="text-left py-1">Column</th>
                {action.details[0].outlier_count !== undefined ? (
                  <>
                    <th className="text-right py-1">Outliers</th>
                    <th className="text-right py-1">%</th>
                    <th className="text-right py-1">Lower</th>
                    <th className="text-right py-1">Upper</th>
                  </>
                ) : (
                  <>
                    <th className="text-right py-1">Missing</th>
                    <th className="text-right py-1">%</th>
                    <th className="text-left py-1">Strategy</th>
                    <th className="text-left py-1">Fill Value</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {action.details.map((d, i) => (
                <tr key={i} className="border-t border-gray-200/30">
                  <td className="py-1 font-mono">{d.column}</td>
                  {d.outlier_count !== undefined ? (
                    <>
                      <td className="text-right py-1">{d.outlier_count}</td>
                      <td className="text-right py-1">{d.pct}%</td>
                      <td className="text-right py-1 font-mono">{d.lower_bound}</td>
                      <td className="text-right py-1 font-mono">{d.upper_bound}</td>
                    </>
                  ) : (
                    <>
                      <td className="text-right py-1">{d.missing}</td>
                      <td className="text-right py-1">{d.pct}%</td>
                      <td className="py-1">{d.strategy}</td>
                      <td className="py-1 font-mono">{d.fill_value ?? "—"}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function CleaningReport({ cleaning }) {
  if (!cleaning) return null;

  const { actions, summary } = cleaning;
  const b = summary.before;
  const a = summary.after;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Sparkles className="w-5 h-5 text-indigo-500" />
        <h2 className="text-lg font-bold text-gray-900">Data Cleaning Report</h2>
        <span className="ml-auto text-xs text-gray-500">
          {summary.total_actions} action(s) applied
        </span>
      </div>

      {/* Before / After Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <SummaryCard
          label="Rows"
          before={b.rows.toLocaleString()}
          after={a.rows.toLocaleString()}
          improved={summary.rows_removed > 0}
        />
        <SummaryCard
          label="Columns"
          before={b.columns}
          after={a.columns}
          improved={summary.columns_removed > 0}
        />
        <SummaryCard
          label="Missing Values"
          before={b.missing_values.toLocaleString()}
          after={a.missing_values.toLocaleString()}
          improved={summary.missing_fixed > 0}
        />
        <SummaryCard
          label="Issues Fixed"
          before="—"
          after={summary.total_actions}
          improved={summary.total_actions > 0}
        />
      </div>

      {/* Step-by-step actions */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Pipeline Steps</h3>
        {actions.map((action, i) => (
          <ActionRow key={i} action={action} index={i} />
        ))}
      </div>
    </div>
  );
}
