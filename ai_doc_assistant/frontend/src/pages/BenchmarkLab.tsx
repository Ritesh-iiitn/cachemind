import React, { useState, useEffect } from "react";
import { 
  Play, Zap, TrendingDown, Database, RefreshCw 
} from "lucide-react";
import { 
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, 
  Tooltip, Legend, CartesianGrid 
} from "recharts";
import { api } from "../services/api";
import type { KnowledgeBase, BenchmarkReport } from "../services/api";

export const BenchmarkLab: React.FC = () => {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [selectedKbId, setSelectedKbId] = useState<string>("");
  const [queriesCount] = useState<number>(8);
  const [workloadType] = useState<string>("mixed");
  const [running, setRunning] = useState(false);
  const [currentReport, setCurrentReport] = useState<BenchmarkReport | null>(null);

  useEffect(() => {
    api.listKnowledgeBases().then((data) => {
      setKbs(data);
      if (data.length > 0) setSelectedKbId(data[0].id);
    });
    api.listBenchmarkHistory().then((data) => {
      if (data.length > 0) setCurrentReport(data[0]);
    });
  }, []);

  const handleRunBenchmark = async () => {
    if (!selectedKbId) return;
    try {
      setRunning(true);
      const report = await api.runBenchmark(selectedKbId, queriesCount, workloadType);
      setCurrentReport(report);
    } catch (err) {
      console.error("Benchmark failed:", err);
    } finally {
      setRunning(false);
    }
  };

  const chartData = currentReport?.detailed_results.map((item, idx) => ({
    name: `Q${idx + 1}`,
    Baseline: item.baseline_latency_ms,
    CacheMind: item.optimized_latency_ms,
    tier: item.cache_tier
  })) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Rigorous Benchmarking & Evaluation Lab
          </h1>
          <p className="text-sm text-slate-400">
            Execute side-by-side workloads comparing Standard Naive RAG vs CacheMind's Adaptive Cache Engine.
          </p>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-surface p-1.5 rounded-xl border border-surfaceBorder">
            <Database className="h-4 w-4 text-primary ml-2" />
            <select
              value={selectedKbId}
              onChange={(e) => setSelectedKbId(e.target.value)}
              className="bg-transparent text-xs text-white border-none focus:outline-none pr-2 font-medium"
            >
              {kbs.map((kb) => (
                <option key={kb.id} value={kb.id} className="bg-surface text-white">
                  {kb.name}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleRunBenchmark}
            disabled={running || !selectedKbId}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover disabled:opacity-50 text-white text-xs font-semibold transition-all shadow-md shadow-primary/20"
          >
            {running ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                <span>Benchmarking Workload...</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                <span>Run Side-by-Side Test</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Benchmark Summary Metrics */}
      {currentReport && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-2xl bg-surface border border-surfaceBorder">
            <span className="text-xs font-medium text-slate-400 uppercase">Latency Reduction (Avg)</span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-bold font-mono text-emerald-400">
                {currentReport.compute_saved_pct}%
              </span>
              <TrendingDown className="h-4 w-4 text-emerald-400" />
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Baseline: {currentReport.baseline_avg_ms}ms → CacheMind: {currentReport.optimized_avg_ms}ms
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-surface border border-surfaceBorder">
            <span className="text-xs font-medium text-slate-400 uppercase">Cache Hit Rate</span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-bold font-mono text-primary-light">
                {currentReport.cache_hit_rate}%
              </span>
              <Zap className="h-4 w-4 text-primary" />
            </div>
            <p className="text-xs text-slate-500 mt-1">Workload: {currentReport.workload_type}</p>
          </div>

          <div className="p-4 rounded-2xl bg-surface border border-surfaceBorder">
            <span className="text-xs font-medium text-slate-400 uppercase">P50 Latency Speedup</span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-bold font-mono text-accent">
                {(currentReport.baseline_p50_ms / Math.max(1, currentReport.optimized_p50_ms)).toFixed(1)}x
              </span>
              <span className="text-xs text-slate-400">speedup</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              {currentReport.baseline_p50_ms}ms vs {currentReport.optimized_p50_ms}ms
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-surface border border-surfaceBorder">
            <span className="text-xs font-medium text-slate-400 uppercase">P95 Tail Latency</span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-bold font-mono text-amber-400">
                {currentReport.optimized_p95_ms}
              </span>
              <span className="text-xs text-amber-400 font-mono">ms</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">Baseline P95: {currentReport.baseline_p95_ms}ms</p>
          </div>
        </div>
      )}

      {/* Latency Comparison Chart */}
      <div className="p-5 rounded-2xl bg-surface border border-surfaceBorder space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">Query Latency Comparison (ms)</h3>
          <span className="text-xs text-slate-400 font-mono">Baseline RAG vs CacheMind</span>
        </div>

        <div className="h-72">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} unit="ms" />
                <Tooltip 
                  contentStyle={{ backgroundColor: "#111827", borderColor: "#1f2937", borderRadius: "8px", fontSize: "12px" }} 
                />
                <Legend wrapperStyle={{ fontSize: "12px" }} />
                <Bar dataKey="Baseline" fill="#ef4444" radius={[4, 4, 0, 0]} name="Baseline (Naive RAG)" />
                <Bar dataKey="CacheMind" fill="#3b82f6" radius={[4, 4, 0, 0]} name="CacheMind (Adaptive Engine)" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-500">
              Click "Run Side-by-Side Test" above to execute real benchmark queries.
            </div>
          )}
        </div>
      </div>

      {/* Detailed Query Breakdown Table */}
      {currentReport && (
        <div className="p-5 rounded-2xl bg-surface border border-surfaceBorder space-y-3">
          <h3 className="text-sm font-semibold text-white">Per-Query Benchmark Telemetry</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-surfaceBorder text-slate-400">
                  <th className="pb-2 font-medium">Query</th>
                  <th className="pb-2 font-medium">Cache Tier</th>
                  <th className="pb-2 font-medium">Baseline (ms)</th>
                  <th className="pb-2 font-medium">CacheMind (ms)</th>
                  <th className="pb-2 font-medium">Latency Saved</th>
                  <th className="pb-2 font-medium">Tokens Saved</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surfaceBorder/40">
                {currentReport.detailed_results.map((r, i) => (
                  <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 text-slate-200 max-w-md truncate">{r.query}</td>
                    <td className="py-3 font-mono font-medium text-primary-light">{r.cache_tier}</td>
                    <td className="py-3 font-mono text-rose-400">{r.baseline_latency_ms} ms</td>
                    <td className="py-3 font-mono text-primary-light">{r.optimized_latency_ms} ms</td>
                    <td className="py-3 font-mono text-emerald-400">+{r.latency_reduction_pct}%</td>
                    <td className="py-3 font-mono text-emerald-400">+{r.tokens_saved}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
