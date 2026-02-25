/**
 * DataPreview.jsx — Rich data preview after file upload
 *
 * Displays:
 *   1. Summary stats (rows, columns, memory, duplicates)
 *   2. Column profiles with type badges, missing % bars, stats
 *   3. Scrollable data table with the first 10 rows
 *
 * This gives the user confidence that their data was parsed correctly
 * BEFORE they run expensive analysis.
 */

import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Calendar,
  ChevronDown,
  ChevronUp,
  Columns3,
  Database,
  Hash,
  Table2,
  Type,
} from 'lucide-react';
import { useState } from 'react';

// ── Type badge colors ────────────────────────────────────────
const typeBadge = {
  numeric: { bg: 'bg-blue-100', text: 'text-blue-700', icon: Hash, label: 'Numeric' },
  text: { bg: 'bg-purple-100', text: 'text-purple-700', icon: Type, label: 'Text' },
  datetime: { bg: 'bg-amber-100', text: 'text-amber-700', icon: Calendar, label: 'Date' },
};

function DataPreview({ data, onAnalyze }) {
  const [activeTab, setActiveTab] = useState('profile'); // profile | table
  const [expandedCol, setExpandedCol] = useState(null);

  if (!data) return null;

  const { file_id, filename, file_size_mb, profile, preview, sheets } = data;
  const { row_count, column_count, columns, memory_usage_mb, duplicate_rows } = profile;

  return (
    <div className="space-y-4">
      {/* ── Summary Cards ────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <SummaryCard
          icon={<Database className="h-5 w-5 text-blue-600" />}
          label="Rows"
          value={row_count.toLocaleString()}
        />
        <SummaryCard
          icon={<Columns3 className="h-5 w-5 text-green-600" />}
          label="Columns"
          value={column_count}
        />
        <SummaryCard
          icon={<BarChart3 className="h-5 w-5 text-purple-600" />}
          label="Memory"
          value={`${memory_usage_mb} MB`}
        />
        <SummaryCard
          icon={<AlertTriangle className="h-5 w-5 text-amber-600" />}
          label="Duplicates"
          value={duplicate_rows}
          warn={duplicate_rows > 0}
        />
      </div>

      {/* ── Sheet info (Excel only) ────────────────────────── */}
      {sheets && sheets.length > 1 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-2 text-sm text-amber-700">
          <strong>Multi-sheet file detected:</strong> {sheets.join(', ')} — Currently showing the first sheet.
        </div>
      )}

      {/* ── Tab Switcher ─────────────────────────────────────── */}
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <div className="flex border-b">
          <TabButton
            active={activeTab === 'profile'}
            onClick={() => setActiveTab('profile')}
            icon={<BarChart3 className="h-4 w-4" />}
            label="Column Profile"
          />
          <TabButton
            active={activeTab === 'table'}
            onClick={() => setActiveTab('table')}
            icon={<Table2 className="h-4 w-4" />}
            label={`Data Preview (${preview.length} rows)`}
          />
        </div>

        {/* ── Column Profile Tab ──────────────────────────── */}
        {activeTab === 'profile' && (
          <div className="divide-y">
            {columns.map((col, idx) => {
              const badge = typeBadge[col.category] || typeBadge.text;
              const BadgeIcon = badge.icon;
              const isExpanded = expandedCol === idx;

              return (
                <div key={col.name} className="hover:bg-gray-50 transition-colors">
                  {/* Column header row */}
                  <button
                    onClick={() => setExpandedCol(isExpanded ? null : idx)}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left"
                  >
                    {/* Column name + type badge */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-800 truncate">
                          {col.name}
                        </span>
                        <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full ${badge.bg} ${badge.text}`}>
                          <BadgeIcon className="h-3 w-3" />
                          {badge.label}
                        </span>
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {col.unique_count} unique · {col.dtype}
                      </p>
                    </div>

                    {/* Missing values bar */}
                    <div className="w-32 flex-shrink-0">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className={col.missing_pct > 0 ? 'text-amber-600' : 'text-green-600'}>
                          {col.missing_pct > 0 ? `${col.missing_pct}% missing` : 'Complete'}
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-1.5">
                        <div
                          className={`h-1.5 rounded-full ${col.missing_pct > 30 ? 'bg-red-400' : col.missing_pct > 0 ? 'bg-amber-400' : 'bg-green-400'}`}
                          style={{ width: `${100 - col.missing_pct}%` }}
                        />
                      </div>
                    </div>

                    {/* Expand arrow */}
                    <div className="flex-shrink-0 text-gray-400">
                      {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </div>
                  </button>

                  {/* Expanded details */}
                  {isExpanded && (
                    <div className="px-4 pb-3 grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                      {col.category === 'numeric' && (
                        <>
                          <StatItem label="Min" value={col.min} />
                          <StatItem label="Max" value={col.max} />
                          <StatItem label="Mean" value={col.mean} />
                          <StatItem label="Median" value={col.median} />
                          <StatItem label="Std Dev" value={col.std} />
                          <StatItem label="Missing" value={col.missing_count} />
                          <StatItem label="Unique" value={col.unique_count} />
                        </>
                      )}
                      {col.category === 'datetime' && (
                        <>
                          <StatItem label="Earliest" value={col.min} />
                          <StatItem label="Latest" value={col.max} />
                          <StatItem label="Missing" value={col.missing_count} />
                          <StatItem label="Unique" value={col.unique_count} />
                        </>
                      )}
                      {col.category === 'text' && (
                        <>
                          <StatItem label="Missing" value={col.missing_count} />
                          <StatItem label="Unique" value={col.unique_count} />
                          {col.top_values && (
                            <div className="col-span-2">
                              <p className="text-xs text-gray-500 mb-1">Top values</p>
                              <div className="flex flex-wrap gap-1">
                                {Object.entries(col.top_values).slice(0, 5).map(([val, count]) => (
                                  <span key={val} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                                    {val} ({count})
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </>
                      )}
                      {col.sample_values && col.sample_values.length > 0 && (
                        <div className="col-span-full">
                          <p className="text-xs text-gray-500 mb-1">Sample values</p>
                          <p className="text-xs text-gray-600 bg-gray-50 rounded px-2 py-1 font-mono">
                            {col.sample_values.join(' · ')}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* ── Data Table Tab ──────────────────────────────── */}
        {activeTab === 'table' && (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b">
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 w-10">#</th>
                  {columns.map((col) => {
                    const badge = typeBadge[col.category] || typeBadge.text;
                    return (
                      <th key={col.name} className="px-3 py-2 text-left">
                        <span className="font-medium text-gray-700 text-xs">{col.name}</span>
                        <span className={`ml-1 text-[10px] px-1 py-0.5 rounded ${badge.bg} ${badge.text}`}>
                          {badge.label.charAt(0)}
                        </span>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {preview.map((row, rowIdx) => (
                  <tr key={rowIdx} className="hover:bg-gray-50">
                    <td className="px-3 py-2 text-xs text-gray-400">{rowIdx + 1}</td>
                    {columns.map((col) => (
                      <td key={col.name} className="px-3 py-2 text-gray-600 max-w-[200px] truncate">
                        {row[col.name] != null ? String(row[col.name]) : (
                          <span className="text-gray-300 italic">null</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {row_count > preview.length && (
              <div className="text-center py-3 text-sm text-gray-400 border-t">
                Showing {preview.length} of {row_count.toLocaleString()} rows
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Analyze Button ────────────────────────────────── */}
      <div className="flex justify-end">
        <button
          onClick={() => onAnalyze?.(file_id)}
          className="flex items-center gap-2 bg-blue-600 text-white px-8 py-3 rounded-lg
                     hover:bg-blue-700 transition-colors shadow-sm font-medium text-lg"
        >
          Run Analysis
          <ArrowRight className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}

/* ── Helper Components ──────────────────────────────────────── */

function SummaryCard({ icon, label, value, warn = false }) {
  return (
    <div className={`flex items-center gap-3 rounded-lg border px-4 py-3 ${warn ? 'bg-amber-50 border-amber-200' : 'bg-white'}`}>
      {icon}
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className={`text-lg font-semibold ${warn ? 'text-amber-700' : 'text-gray-800'}`}>{value}</p>
      </div>
    </div>
  );
}

function TabButton({ active, onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors
        ${active
          ? 'border-blue-600 text-blue-600'
          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
        }`}
    >
      {icon}
      {label}
    </button>
  );
}

function StatItem({ label, value }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="font-medium text-gray-800">{value != null ? String(value) : '—'}</p>
    </div>
  );
}

export default DataPreview;
