/**
 * AnalysisPage.jsx - Full analysis results page
 *
 * Tabs: Cleaning | Statistics | Anomalies | Forecasts | Data Preview
 */

import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  Clock,
  FileDown,
  Hash,
  Layers,
  Loader2,
  MessageSquare,
  Percent,
  ShieldAlert,
  Sparkles,
  Table2,
  TrendingUp,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import AnomalyReport from "../components/AnomalyReport";
import CleaningReport from "../components/CleaningReport";
import ForecastView from "../components/ForecastView";
import InsightReport from "../components/InsightReport";
import { generateInsights, generateReport, getDownloadUrl, runAnalysis } from "../services/api";

/* ── Reusable sub-components ─────────────────────────────── */

function StatCard({ label, value, sub, icon: Icon }) {
  return (
    <div className="bg-white rounded-lg border p-4">
      <div className="flex items-center gap-2 mb-1">
        {Icon && <Icon className="w-4 h-4 text-indigo-400" />}
        <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function DescriptiveStatsTable({ stats }) {
  if (!stats || Object.keys(stats).length === 0) return null;
  const columns = Object.keys(stats);
  const metrics = ["count", "mean", "std", "min", "q1", "median", "q3", "max", "range", "iqr", "cv"];
  const metricLabels = {
    count: "Count", mean: "Mean", std: "Std Dev", min: "Min",
    q1: "Q1 (25%)", median: "Median", q3: "Q3 (75%)", max: "Max",
    range: "Range", iqr: "IQR", cv: "CV",
  };

  return (
    <div className="bg-white rounded-xl border p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Descriptive Statistics</h3>
      <div className="overflow-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50">
              <th className="py-2 px-3 text-left text-gray-500 uppercase">Metric</th>
              {columns.map((col) => (
                <th key={col} className="py-2 px-3 text-right text-gray-500 uppercase font-mono whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metrics.map((m) => (
              <tr key={m} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="py-1.5 px-3 text-gray-600 font-medium">{metricLabels[m]}</td>
                {columns.map((col) => (
                  <td key={col} className="py-1.5 px-3 text-right font-mono text-gray-900">
                    {stats[col][m] !== null && stats[col][m] !== undefined
                      ? typeof stats[col][m] === "number"
                        ? stats[col][m].toLocaleString(undefined, { maximumFractionDigits: 4 })
                        : stats[col][m]
                      : "\u2014"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CorrelationTable({ correlations }) {
  if (!correlations || correlations.length === 0) return null;
  return (
    <div className="bg-white rounded-xl border p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Strong Correlations (|r| &gt; 0.7)</h3>
      <div className="overflow-auto max-h-64">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-xs uppercase border-b">
              <th className="text-left py-2">Column A</th>
              <th className="text-left py-2">Column B</th>
              <th className="text-right py-2">r</th>
              <th className="text-left py-2 pl-3">Strength</th>
              <th className="text-left py-2 pl-3">Direction</th>
            </tr>
          </thead>
          <tbody>
            {correlations.map((c, i) => (
              <tr key={i} className="border-b border-gray-100">
                <td className="py-1.5 font-mono text-xs">{c.col_a}</td>
                <td className="py-1.5 font-mono text-xs">{c.col_b}</td>
                <td className="py-1.5 text-right font-mono">
                  {typeof c.correlation === "number" ? c.correlation.toFixed(4) : c.correlation}
                </td>
                <td className="py-1.5 pl-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${c.strength === "very_strong" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"
                    }`}>
                    {c.strength}
                  </span>
                </td>
                <td className="py-1.5 pl-3 text-xs text-gray-600">{c.direction}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DistributionTable({ distributions }) {
  if (!distributions || Object.keys(distributions).length === 0) return null;
  return (
    <div className="bg-white rounded-xl border p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Distribution Analysis</h3>
      <div className="overflow-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 uppercase border-b">
              <th className="text-left py-2">Column</th>
              <th className="text-right py-2">Skewness</th>
              <th className="text-right py-2">Kurtosis</th>
              <th className="text-left py-2 pl-3">Shape</th>
              <th className="text-left py-2 pl-3">Normal?</th>
              <th className="text-right py-2">p-value</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(distributions).map(([col, d]) => (
              <tr key={col} className="border-b border-gray-100">
                <td className="py-1.5 font-mono">{col}</td>
                <td className="py-1.5 text-right font-mono">{d.skewness}</td>
                <td className="py-1.5 text-right font-mono">{d.kurtosis}</td>
                <td className="py-1.5 pl-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${d.shape === "symmetric" ? "bg-green-100 text-green-700" :
                      d.shape === "right_skewed" ? "bg-orange-100 text-orange-700" :
                        "bg-blue-100 text-blue-700"
                    }`}>
                    {d.shape?.replace("_", " ")}
                  </span>
                </td>
                <td className="py-1.5 pl-3">
                  {d.is_normal ? (
                    <span className="text-green-600 font-medium">Yes</span>
                  ) : (
                    <span className="text-red-500">No</span>
                  )}
                </td>
                <td className="py-1.5 text-right font-mono text-gray-500">
                  {d.shapiro_p !== null ? d.shapiro_p?.toFixed(4) : "\u2014"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FeatureImportance({ features }) {
  if (!features || features.length === 0) return null;
  const maxScore = Math.max(...features.map((f) => f.importance));

  return (
    <div className="bg-white rounded-xl border p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-1">Feature Importance</h3>
      <p className="text-xs text-gray-400 mb-3">
        Mutual information score (target: <span className="font-mono">{features[0]?.target}</span>)
      </p>
      <div className="space-y-2">
        {features.map((f, i) => (
          <div key={i} className="flex items-center gap-3">
            <span className="text-xs font-mono text-gray-600 w-32 truncate">{f.feature}</span>
            <div className="flex-1 bg-gray-100 rounded-full h-3 overflow-hidden">
              <div
                className="bg-indigo-500 h-full rounded-full transition-all"
                style={{ width: `${maxScore > 0 ? (f.importance / maxScore) * 100 : 0}%` }}
              />
            </div>
            <span className="text-xs font-mono text-gray-500 w-12 text-right">{f.importance}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SegmentView({ segments }) {
  if (!segments || Object.keys(segments).length === 0) return null;
  const [activeSeg, setActiveSeg] = useState(Object.keys(segments)[0]);
  const seg = segments[activeSeg] || {};

  return (
    <div className="bg-white rounded-xl border p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Segment Analysis (Group-By)</h3>
      {/* Category selector */}
      <div className="flex gap-1 mb-4 flex-wrap">
        {Object.keys(segments).map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveSeg(cat)}
            className={`text-xs px-3 py-1 rounded-full transition ${activeSeg === cat ? "bg-indigo-100 text-indigo-700 font-medium" : "bg-gray-100 text-gray-500 hover:bg-gray-200"
              }`}
          >
            {cat}
          </button>
        ))}
      </div>
      {/* Segment tables */}
      {Object.entries(seg).map(([numCol, groups]) => (
        <div key={numCol} className="mb-4">
          <p className="text-xs font-semibold text-gray-500 mb-1 uppercase">{numCol}</p>
          <div className="overflow-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-400 uppercase border-b">
                  <th className="text-left py-1">{activeSeg}</th>
                  <th className="text-right py-1">Mean</th>
                  <th className="text-right py-1">Median</th>
                  <th className="text-right py-1">Std</th>
                  <th className="text-right py-1">Count</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(groups).map(([grp, vals]) => (
                  <tr key={grp} className="border-t border-gray-100">
                    <td className="py-1 font-medium">{grp}</td>
                    <td className="text-right font-mono">{vals.mean}</td>
                    <td className="text-right font-mono">{vals.median}</td>
                    <td className="text-right font-mono">{vals.std}</td>
                    <td className="text-right">{vals.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}

function TrendTable({ trends }) {
  if (!trends || Object.keys(trends).length === 0) return null;
  return (
    <div className="bg-white rounded-xl border p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Trend Detection</h3>
      <div className="overflow-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 uppercase border-b">
              <th className="text-left py-2">Column</th>
              <th className="text-left py-2">Direction</th>
              <th className="text-right py-2">Slope</th>
              <th className="text-right py-2">R&sup2;</th>
              <th className="text-right py-2">p-value</th>
              <th className="text-left py-2 pl-3">Significant?</th>
              <th className="text-right py-2">% Change</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(trends).map(([col, t]) => (
              <tr key={col} className="border-b border-gray-100">
                <td className="py-1.5 font-mono">{col}</td>
                <td className="py-1.5">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${t.direction === "increasing" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                    }`}>
                    {t.direction}
                  </span>
                </td>
                <td className="py-1.5 text-right font-mono">{t.slope}</td>
                <td className="py-1.5 text-right font-mono">{t.r_squared}</td>
                <td className="py-1.5 text-right font-mono">{t.p_value}</td>
                <td className="py-1.5 pl-3">
                  {t.significant ? (
                    <span className="text-green-600 font-medium">Yes</span>
                  ) : (
                    <span className="text-gray-400">No</span>
                  )}
                </td>
                <td className="py-1.5 text-right font-mono">
                  {t.pct_change !== null && t.pct_change !== undefined ? `${t.pct_change}%` : "\u2014"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CategoricalSummary({ catSummary }) {
  if (!catSummary || Object.keys(catSummary).length === 0) return null;
  return (
    <div className="bg-white rounded-xl border p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">Categorical Columns</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {Object.entries(catSummary).map(([col, info]) => (
          <div key={col} className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs font-semibold text-gray-700 mb-1 font-mono">{col}</p>
            <p className="text-xs text-gray-500 mb-2">
              {info.unique_count} unique | top: <span className="font-medium">{info.top_value}</span>{" "}
              ({info.top_pct}%)
            </p>
            <div className="space-y-1">
              {Object.entries(info.top_values || {}).slice(0, 5).map(([val, count]) => (
                <div key={val} className="flex items-center gap-2">
                  <span className="text-xs text-gray-600 w-24 truncate">{val}</span>
                  <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-indigo-400 h-full rounded-full"
                      style={{ width: `${(count / info.top_freq) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-400 w-8 text-right">{count}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DataPreviewTable({ preview }) {
  if (!preview || preview.length === 0) return null;
  const columns = Object.keys(preview[0]);
  return (
    <div className="bg-white rounded-xl border p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
        <Table2 className="w-4 h-4" />
        Cleaned Data Preview (first 15 rows)
      </h3>
      <div className="overflow-auto max-h-[500px]">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-gray-50">
            <tr>
              <th className="py-2 px-2 text-gray-400 text-left">#</th>
              {columns.map((col) => (
                <th key={col} className="py-2 px-2 text-gray-600 text-left font-mono whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {preview.map((row, i) => (
              <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="py-1.5 px-2 text-gray-300">{i + 1}</td>
                {columns.map((col) => (
                  <td key={col} className="py-1.5 px-2 text-gray-900 whitespace-nowrap max-w-[200px] truncate">
                    {row[col] !== null && row[col] !== undefined ? String(row[col]) : "\u2014"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ── Main Page ───────────────────────────────────────────── */

function AnalysisPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const fileId = searchParams.get("file_id");

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("cleaning");
  const [insights, setInsights] = useState(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [insightsError, setInsightsError] = useState(null);
  const [reportLoading, setReportLoading] = useState(null); // "pdf" | "pptx" | null

  useEffect(() => {
    if (!fileId) return;
    setLoading(true);
    setError(null);
    runAnalysis(fileId)
      .then((res) => setResult(res))
      .catch((err) => {
        console.error(err);
        setError(err.response?.data?.detail || err.message || "Analysis failed.");
      })
      .finally(() => setLoading(false));
  }, [fileId]);

  const fetchInsights = async () => {
    if (!fileId) return;
    setInsightsLoading(true);
    setInsightsError(null);
    try {
      const res = await generateInsights(fileId);
      setInsights(res);
    } catch (err) {
      console.error(err);
      setInsightsError(err.response?.data?.detail || err.message || "Insight generation failed.");
    } finally {
      setInsightsLoading(false);
    }
  };

  const handleReport = async (format) => {
    if (!fileId || reportLoading) return;
    setReportLoading(format);
    try {
      const res = await generateReport(fileId, format);
      // Open the full download URL in a new tab
      const url = getDownloadUrl(res.download_url);
      window.open(url, "_blank");
    } catch (err) {
      console.error(err);
      alert(`Report generation failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setReportLoading(null);
    }
  };

  if (!fileId) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-gray-900">Analysis Dashboard</h2>
        <div className="bg-white rounded-xl shadow-sm border p-12 text-center">
          <BarChart3 className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-500">No Analysis Yet</h3>
          <p className="text-gray-400 mt-2">Upload a file and run analysis to see results.</p>
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

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <Loader2 className="w-10 h-10 text-indigo-500 animate-spin mb-4" />
        <p className="text-gray-600 font-medium">Running full analysis pipeline...</p>
        <p className="text-gray-400 text-sm mt-1">
          Cleaning \u2192 Statistics \u2192 Correlations \u2192 Anomalies \u2192 Forecasts
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-8 text-center">
        <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
        <h3 className="text-lg font-medium text-red-700">Analysis Failed</h3>
        <p className="text-red-600 text-sm mt-2 max-w-md mx-auto">{error}</p>
        <button
          onClick={() => navigate("/")}
          className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition text-sm"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Upload
        </button>
      </div>
    );
  }

  if (!result) return null;

  const analysis = result.analysis || {};
  const tabs = [
    { key: "cleaning", label: "Cleaning", icon: Layers },
    { key: "statistics", label: "Statistics", icon: Hash },
    { key: "anomalies", label: "Anomalies", icon: ShieldAlert },
    { key: "forecasts", label: "Forecasts", icon: Clock },
    { key: "insights", label: "AI Insights", icon: Sparkles },
    { key: "preview", label: "Data", icon: Table2 },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Analysis Results</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            File: {result.file_id} | {analysis.summary?.total_rows} rows \u00d7{" "}
            {analysis.summary?.total_columns} columns
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleReport("pdf")}
            disabled={!!reportLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 transition disabled:opacity-50"
          >
            {reportLoading === "pdf" ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileDown className="w-4 h-4" />}
            PDF
          </button>
          <button
            onClick={() => handleReport("pptx")}
            disabled={!!reportLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-orange-500 text-white rounded-lg text-sm hover:bg-orange-600 transition disabled:opacity-50"
          >
            {reportLoading === "pptx" ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileDown className="w-4 h-4" />}
            PPT
          </button>
          <button
            onClick={() => navigate(`/dashboard?file_id=${fileId}`)}
            className="inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 transition"
          >
            <BarChart3 className="w-4 h-4" /> Dashboard
          </button>
          <button
            onClick={() => navigate(`/chat?file_id=${fileId}`)}
            className="inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-sm hover:bg-emerald-700 transition"
          >
            <MessageSquare className="w-4 h-4" /> Chat
          </button>
          <button
            onClick={() => navigate("/")}
            className="inline-flex items-center gap-2 px-3 py-1.5 border rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition"
          >
            <ArrowLeft className="w-4 h-4" /> Upload New
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg overflow-x-auto">
        {tabs.map((tab) => {
          const TabIcon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-md transition whitespace-nowrap ${activeTab === tab.key
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
                }`}
            >
              <TabIcon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {activeTab === "cleaning" && <CleaningReport cleaning={result.cleaning} />}

      {activeTab === "statistics" && (
        <div className="space-y-4">
          {/* Quick stat cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatCard icon={Hash} label="Numeric Columns" value={analysis.summary?.numeric_columns || 0} />
            <StatCard
              icon={Percent}
              label="Correlations"
              value={analysis.strong_correlations?.length ?? 0}
              sub="with |r| > 0.7"
            />
            <StatCard
              icon={TrendingUp}
              label="Trends"
              value={analysis.trends ? Object.keys(analysis.trends).length : 0}
            />
            <StatCard
              icon={Activity}
              label="Normal Dist."
              value={analysis.summary?.normal_distributions ?? 0}
              sub="(Shapiro p > 0.05)"
            />
          </div>

          <DescriptiveStatsTable stats={analysis.descriptive_stats} />
          <CorrelationTable correlations={analysis.strong_correlations} />
          <DistributionTable distributions={analysis.distributions} />
          <TrendTable trends={analysis.trends} />
          <FeatureImportance features={analysis.feature_importance} />
          <CategoricalSummary catSummary={analysis.categorical_summary} />
          <SegmentView segments={analysis.segments} />
        </div>
      )}

      {activeTab === "anomalies" && <AnomalyReport anomalies={result.anomalies} />}

      {activeTab === "forecasts" && <ForecastView forecasts={result.forecasts} />}

      {activeTab === "insights" && (
        <InsightReport
          insights={insights}
          loading={insightsLoading}
          error={insightsError}
          onRegenerate={fetchInsights}
        />
      )}

      {activeTab === "preview" && <DataPreviewTable preview={result.preview} />}
    </div>
  );
}

export default AnalysisPage;
