/**
 * ForecastView.jsx - Displays time-series forecast results
 *
 * Shows:
 *   - Forecast summary per column
 *   - Historical vs predicted values table
 *   - Confidence intervals
 */
import {
  BarChart3,
  ChevronDown,
  ChevronRight,
  Clock,
  TrendingUp,
} from "lucide-react";
import { useState } from "react";

function ForecastCard({ col, data }) {
  const [expanded, setExpanded] = useState(false);

  if (data.status === "insufficient_data") {
    return null;
  }

  const forecast = data.forecast || [];
  const lastForecast = forecast.length > 0 ? forecast[forecast.length - 1] : null;
  const firstForecast = forecast.length > 0 ? forecast[0] : null;

  return (
    <div className="bg-white rounded-lg border mb-3 overflow-hidden">
      <button
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition"
        onClick={() => setExpanded(!expanded)}
      >
        <TrendingUp className="w-4 h-4 text-indigo-500 flex-shrink-0" />
        <div className="flex-1">
          <span className="text-sm font-medium text-gray-900">{col}</span>
          <span className="block text-xs text-gray-500 mt-0.5">
            {data.method === "prophet" ? "Prophet" : "Linear"} | {data.periods} periods |{" "}
            {data.frequency}
            {data.r_squared !== undefined && ` | R²=${data.r_squared}`}
          </span>
        </div>
        {firstForecast && lastForecast && (
          <span className="text-xs text-gray-600 flex-shrink-0">
            {firstForecast.yhat} → {lastForecast.yhat}
          </span>
        )}
        {expanded ? (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t">
          {/* Method info */}
          <div className="grid grid-cols-3 gap-2 mt-3 mb-4">
            <div className="bg-gray-50 rounded p-2 text-center">
              <p className="text-[10px] text-gray-400 uppercase">Method</p>
              <p className="text-xs font-semibold text-gray-700">
                {data.method === "prophet" ? "Prophet" : "Linear Regression"}
              </p>
            </div>
            <div className="bg-gray-50 rounded p-2 text-center">
              <p className="text-[10px] text-gray-400 uppercase">Periods</p>
              <p className="text-xs font-semibold text-gray-700">{data.periods}</p>
            </div>
            <div className="bg-gray-50 rounded p-2 text-center">
              <p className="text-[10px] text-gray-400 uppercase">Frequency</p>
              <p className="text-xs font-semibold text-gray-700">{data.frequency}</p>
            </div>
          </div>

          {/* Forecast Table */}
          {forecast.length > 0 && (
            <div className="overflow-auto max-h-64">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-400 uppercase border-b">
                    <th className="text-left py-1.5">Date</th>
                    <th className="text-right py-1.5">Predicted</th>
                    <th className="text-right py-1.5">Lower</th>
                    <th className="text-right py-1.5">Upper</th>
                  </tr>
                </thead>
                <tbody>
                  {forecast.map((f, i) => (
                    <tr key={i} className="border-b border-gray-100">
                      <td className="py-1.5 font-mono">
                        {f.ds ? f.ds.split("T")[0] : f.ds}
                      </td>
                      <td className="text-right font-mono font-medium text-indigo-600">
                        {f.yhat}
                      </td>
                      <td className="text-right font-mono text-gray-400">
                        {f.yhat_lower}
                      </td>
                      <td className="text-right font-mono text-gray-400">
                        {f.yhat_upper}
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

export default function ForecastView({ forecasts }) {
  if (!forecasts || Object.keys(forecasts).length === 0) {
    return (
      <div className="bg-gray-50 rounded-xl border p-8 text-center">
        <Clock className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <h3 className="text-lg font-medium text-gray-500">No Forecasts Available</h3>
        <p className="text-gray-400 mt-2 text-sm">
          Forecasting requires time-series data (a datetime column + numeric columns).
        </p>
      </div>
    );
  }

  const cols = Object.keys(forecasts);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-indigo-500" />
        <h2 className="text-lg font-bold text-gray-900">Time-Series Forecasts</h2>
        <span className="ml-auto text-xs text-gray-500">
          {cols.length} column(s) forecasted
        </span>
      </div>

      {/* Forecast Cards */}
      {cols.map((col) => (
        <ForecastCard key={col} col={col} data={forecasts[col]} />
      ))}
    </div>
  );
}
