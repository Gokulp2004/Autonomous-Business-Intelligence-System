/**
 * DashboardPage.jsx - Interactive Visualization Dashboard
 *
 * Fetches Plotly chart configs from the backend and renders them
 * using react-plotly.js. Includes KPI summary cards and chart grid.
 */

import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  Columns,
  Database,
  GitBranch,
  Loader2,
  Maximize2,
  MessageSquare,
  Minimize2,
  RefreshCw,
  ShieldCheck,
  TrendingDown,
  TrendingUp
} from "lucide-react";
import { useEffect, useState } from "react";
import Plot from "react-plotly.js";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getCharts, getDashboardSummary } from "../services/api";

/* ── KPI Card ────────────────────────────────────────────── */

function KpiCard({ label, value, sub, icon: Icon, color = "indigo" }) {
  const colors = {
    indigo: "bg-indigo-50 text-indigo-600",
    green: "bg-green-50 text-green-600",
    red: "bg-red-50 text-red-600",
    amber: "bg-amber-50 text-amber-600",
    blue: "bg-blue-50 text-blue-600",
    cyan: "bg-cyan-50 text-cyan-600",
  };
  const iconClass = colors[color] || colors.indigo;

  return (
    <div className="bg-white rounded-xl border p-4 flex items-start gap-3 hover:shadow-md transition">
      <div className={`p-2 rounded-lg ${iconClass}`}>
        {Icon && <Icon className="w-5 h-5" />}
      </div>
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-bold text-gray-900 mt-0.5">{value}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

/* ── Chart Card ──────────────────────────────────────────── */

function ChartCard({ chart }) {
  const [expanded, setExpanded] = useState(false);

  if (!chart || !chart.data) return null;

  const containerClass = expanded
    ? "fixed inset-4 z-50 bg-white rounded-2xl shadow-2xl border p-4 flex flex-col"
    : "bg-white rounded-xl border p-4 hover:shadow-md transition";

  return (
    <>
      {expanded && (
        <div
          className="fixed inset-0 bg-black/30 z-40"
          onClick={() => setExpanded(false)}
        />
      )}
      <div className={containerClass}>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-700 truncate">
            {chart.title}
          </h3>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-gray-400 hover:text-gray-600 transition p-1"
            title={expanded ? "Minimize" : "Expand"}
          >
            {expanded ? (
              <Minimize2 className="w-4 h-4" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </button>
        </div>
        <div className={expanded ? "flex-1" : ""}>
          <Plot
            data={chart.data}
            layout={{
              ...chart.layout,
              autosize: true,
              height: expanded ? undefined : chart.layout?.height || 340,
              paper_bgcolor: "transparent",
              plot_bgcolor: "#fafafa",
              font: { family: "Inter, sans-serif", size: 11 },
            }}
            config={{
              responsive: true,
              displayModeBar: expanded,
              displaylogo: false,
              modeBarButtonsToRemove: ["lasso2d", "select2d"],
            }}
            useResizeHandler
            style={{ width: "100%", height: expanded ? "100%" : "auto" }}
          />
        </div>
      </div>
    </>
  );
}

/* ── Filter Chip ─────────────────────────────────────────── */

function FilterChip({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 text-xs font-medium rounded-full transition ${active
          ? "bg-indigo-100 text-indigo-700 ring-1 ring-indigo-300"
          : "bg-gray-100 text-gray-500 hover:bg-gray-200"
        }`}
    >
      {label}
    </button>
  );
}

/* ── Main Dashboard Page ─────────────────────────────────── */

export default function DashboardPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const fileId = searchParams.get("file_id");

  const [summary, setSummary] = useState(null);
  const [charts, setCharts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filterType, setFilterType] = useState("all");

  useEffect(() => {
    if (!fileId) return;
    loadDashboard();
  }, [fileId]);

  async function loadDashboard() {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, chartsRes] = await Promise.all([
        getDashboardSummary(fileId),
        getCharts(fileId),
      ]);
      setSummary(summaryRes);
      setCharts(chartsRes.charts || []);
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail || err.message || "Failed to load dashboard."
      );
    } finally {
      setLoading(false);
    }
  }

  /* No file_id — prompt user */
  if (!fileId) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-gray-900">
          Visualization Dashboard
        </h2>
        <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
          <BarChart3 className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-500">No Data Loaded</h3>
          <p className="text-gray-400 mt-2">
            Upload a file and run analysis first to see the dashboard.
          </p>
          <button
            onClick={() => navigate("/")}
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition text-sm"
          >
            <ArrowLeft className="w-4 h-4" /> Go to Upload
          </button>
        </div>
      </div>
    );
  }

  /* Loading */
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <Loader2 className="w-10 h-10 text-indigo-500 animate-spin mb-4" />
        <p className="text-gray-600 font-medium">Building your dashboard...</p>
        <p className="text-gray-400 text-sm mt-1">
          Generating charts and computing KPIs
        </p>
      </div>
    );
  }

  /* Error */
  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-8 text-center">
        <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
        <h3 className="text-lg font-medium text-red-700">Dashboard Error</h3>
        <p className="text-red-600 text-sm mt-2 max-w-md mx-auto">{error}</p>
        <div className="mt-4 flex gap-3 justify-center">
          <button
            onClick={loadDashboard}
            className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition text-sm"
          >
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
          <button
            onClick={() => navigate("/")}
            className="inline-flex items-center gap-2 px-4 py-2 border rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition"
          >
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
        </div>
      </div>
    );
  }

  /* Chart type filter */
  const chartTypes = ["all", ...new Set(charts.map((c) => c.type))];
  const filteredCharts =
    filterType === "all"
      ? charts
      : charts.filter((c) => c.type === filterType);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {fileId} &mdash; {charts.length} charts generated
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadDashboard}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 border rounded-lg text-xs text-gray-600 hover:bg-gray-50 transition"
          >
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
          <button
            onClick={() => navigate(`/analysis?file_id=${fileId}`)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 border rounded-lg text-xs text-gray-600 hover:bg-gray-50 transition"
          >
            <BarChart3 className="w-3 h-3" /> Analysis
          </button>
          <button
            onClick={() => navigate(`/chat?file_id=${fileId}`)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs hover:bg-emerald-700 transition"
          >
            <MessageSquare className="w-3 h-3" /> Chat
          </button>
          <button
            onClick={() => navigate("/")}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 border rounded-lg text-xs text-gray-600 hover:bg-gray-50 transition"
          >
            <ArrowLeft className="w-3 h-3" /> Upload
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <KpiCard
            icon={Database}
            label="Rows"
            value={summary.total_rows?.toLocaleString()}
            color="indigo"
          />
          <KpiCard
            icon={Columns}
            label="Columns"
            value={summary.total_columns}
            sub={`${summary.numeric_columns} numeric, ${summary.categorical_columns} categorical`}
            color="blue"
          />
          <KpiCard
            icon={ShieldCheck}
            label="Data Quality"
            value={`${summary.data_quality_score}%`}
            sub={`${summary.missing_cells} missing cells`}
            color={summary.data_quality_score >= 95 ? "green" : "amber"}
          />
          <KpiCard
            icon={AlertCircle}
            label="Anomalies"
            value={summary.anomaly_count}
            color={summary.anomaly_count > 0 ? "red" : "green"}
          />
          <KpiCard
            icon={GitBranch}
            label="Correlations"
            value={summary.correlation_count}
            sub="|r| > 0.7"
            color="cyan"
          />
          <KpiCard
            icon={summary.trends_increasing >= summary.trends_decreasing ? TrendingUp : TrendingDown}
            label="Trends"
            value={`${summary.trends_increasing}\u2191 ${summary.trends_decreasing}\u2193`}
            color={summary.trends_increasing > 0 ? "green" : "amber"}
          />
        </div>
      )}

      {/* Chart Type Filters */}
      {charts.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {chartTypes.map((t) => (
            <FilterChip
              key={t}
              label={t === "all" ? `All (${charts.length})` : `${t} (${charts.filter((c) => c.type === t).length})`}
              active={filterType === t}
              onClick={() => setFilterType(t)}
            />
          ))}
        </div>
      )}

      {/* Chart Grid */}
      {filteredCharts.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {filteredCharts.map((chart) => (
            <ChartCard key={chart.id} chart={chart} />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl border p-12 text-center">
          <BarChart3 className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No charts to display.</p>
        </div>
      )}
    </div>
  );
}
