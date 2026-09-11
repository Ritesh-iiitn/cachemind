import React, { useEffect, useState } from "react";
import { 
  Zap, Clock, ShieldCheck, 
  ArrowUpRight, Server, RefreshCw
} from "lucide-react";
import { 
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, 
  Cell, AreaChart, Area 
} from "recharts";
import { api } from "../services/api";
import type { CacheStats } from "../services/api";

export const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<CacheStats | null>(null);
  const [traces, setTraces] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [cacheData, tracesData] = await Promise.all([
        api.getCacheStats(),
        api.listTraces()
      ]);
      setStats(cacheData);
      setTraces(tracesData);
    } catch (err) {
      console.error("Dashboard fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const tierChartData = stats ? [
    { name: "L1 Exact Cache", count: stats.total_exact_hits, color: "#3b82f6" },
    { name: "L2 Semantic Cache", count: stats.total_semantic_hits, color: "#8b5cf6" },
    { name: "L4 Retrieval Cache", count: stats.total_retrieval_hits, color: "#10b981" },
    { name: "L5 Prefix Cache", count: stats.total_prefix_hits, color: "#f59e0b" },
    { name: "Cache Misses", count: stats.total_misses, color: "#64748b" },
  ] : [];

  const latencyTrendData = traces.slice(0, 15).reverse().map((t, i) => ({
    name: `Req ${i + 1}`,
    latency: t.latency_ms,
    tokens: t.tokens_generated
  }));

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Inference Observatory & Cache Telemetry
          </h1>
          <p className="text-sm text-slate-400">
            Real-time monitoring of multi-tier caching hit rates, agentic execution latency, and token savings.
          </p>
        </div>
        <button
          onClick={fetchDashboardData}
          className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-surface border border-surfaceBorder hover:border-slate-600 text-xs font-medium text-slate-300 transition-all hover:bg-slate-800/80"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-2xl bg-surface border border-surfaceBorder/80 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Overall Hit Rate</span>
            <div className="p-2 rounded-xl bg-primary/10 text-primary-light">
              <Zap className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-white">
              {stats?.overall_hit_rate ?? 0}%
            </span>
            <span className="text-xs font-medium text-emerald-400 flex items-center">
              <ArrowUpRight className="h-3 w-3" /> multi-layer
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">Across L1, L2, L4 & L5 tiers</p>
        </div>

        <div className="p-4 rounded-2xl bg-surface border border-surfaceBorder/80 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">LLM Calls Avoided</span>
            <div className="p-2 rounded-xl bg-accent/10 text-accent">
              <ShieldCheck className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-white">
              {stats?.llm_calls_avoided ?? 0}
            </span>
            <span className="text-xs text-slate-400">requests</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">Zero-cost sub-10ms responses</p>
        </div>

        <div className="p-4 rounded-2xl bg-surface border border-surfaceBorder/80 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Tokens Saved</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <Server className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-white">
              {stats?.total_tokens_saved?.toLocaleString() ?? 0}
            </span>
            <span className="text-xs text-emerald-400 font-medium">tokens</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">Prefill & generation compute saved</p>
        </div>

        <div className="p-4 rounded-2xl bg-surface border border-surfaceBorder/80 shadow-sm relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Compute Cost Saved</span>
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold font-mono text-white">
              {stats?.estimated_compute_saved_pct ?? 0}%
            </span>
            <span className="text-xs text-amber-400 font-medium">efficiency gain</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">Relative to unoptimized RAG</p>
        </div>
      </div>

      {/* Analytics Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tier Distribution Chart */}
        <div className="p-5 rounded-2xl bg-surface border border-surfaceBorder/80 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Cache Tier Hit Breakdown</h3>
            <span className="text-xs text-slate-400 font-mono">Live Counters</span>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={tierChartData} layout="vertical">
                <XAxis type="number" stroke="#64748b" fontSize={11} />
                <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={10} width={115} />
                <Tooltip 
                  contentStyle={{ backgroundColor: "#111827", borderColor: "#1f2937", borderRadius: "8px", fontSize: "12px" }} 
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {tierChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-surfaceBorder">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-primary" />
              <span className="text-slate-400">Exact L1: <b className="text-white">{stats?.total_exact_hits ?? 0}</b></span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-accent" />
              <span className="text-slate-400">Semantic L2: <b className="text-white">{stats?.total_semantic_hits ?? 0}</b></span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <span className="text-slate-400">Retrieval L4: <b className="text-white">{stats?.total_retrieval_hits ?? 0}</b></span>
            </div>
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-amber-500" />
              <span className="text-slate-400">Prefix L5: <b className="text-white">{stats?.total_prefix_hits ?? 0}</b></span>
            </div>
          </div>
        </div>

        {/* Latency Trend Area Chart */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-surface border border-surfaceBorder/80 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Execution Latency Trajectory</h3>
            <span className="text-xs text-slate-400 font-mono">Recent Requests (ms)</span>
          </div>
          <div className="h-56">
            {latencyTrendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={latencyTrendData}>
                  <defs>
                    <linearGradient id="latencyGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: "#111827", borderColor: "#1f2937", borderRadius: "8px", fontSize: "12px" }} 
                  />
                  <Area type="monotone" dataKey="latency" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#latencyGradient)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-500">
                Execute queries in the Playground to populate live latency telemetry.
              </div>
            )}
          </div>
          <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-surfaceBorder">
            <span>Sub-10ms responses indicate cache hits (L1/L2)</span>
            <span className="text-primary-light font-mono">P50: ~8ms on warm cache</span>
          </div>
        </div>
      </div>

      {/* Live Recent Execution Traces */}
      <div className="p-5 rounded-2xl bg-surface border border-surfaceBorder/80 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">Recent Agentic Execution Traces</h3>
          <span className="text-xs text-slate-400 font-mono">{traces.length} logged</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-surfaceBorder text-slate-400">
                <th className="pb-2.5 font-medium">Request ID</th>
                <th className="pb-2.5 font-medium">Query</th>
                <th className="pb-2.5 font-medium">Cache Tier</th>
                <th className="pb-2.5 font-medium">Strategy</th>
                <th className="pb-2.5 font-medium">Model</th>
                <th className="pb-2.5 font-medium">Latency</th>
                <th className="pb-2.5 font-medium">Tokens Saved</th>
                <th className="pb-2.5 font-medium">Verification</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surfaceBorder/50">
              {traces.slice(0, 8).map((t) => {
                const tier = t.exact_cache_hit ? "L1 EXACT" : (t.semantic_cache_hit ? "L2 SEMANTIC" : (t.retrieval_cache_hit ? "L4 RETRIEVAL" : "MISS"));
                const tierColor = t.exact_cache_hit ? "bg-primary/20 text-primary-light border-primary/30" : (t.semantic_cache_hit ? "bg-accent/20 text-accent border-accent/30" : (t.retrieval_cache_hit ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" : "bg-slate-800 text-slate-400 border-slate-700"));

                return (
                  <tr key={t.request_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 font-mono text-slate-400">{t.request_id.slice(0, 10)}</td>
                    <td className="py-3 text-slate-200 max-w-xs truncate">{t.query}</td>
                    <td className="py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium border ${tierColor}`}>
                        {tier}
                      </span>
                    </td>
                    <td className="py-3 font-mono text-slate-300">{t.retrieval_strategy}</td>
                    <td className="py-3 text-slate-300">{t.model_used}</td>
                    <td className="py-3 font-mono text-slate-200">{t.latency_ms} ms</td>
                    <td className="py-3 font-mono text-emerald-400">+{t.tokens_saved}</td>
                    <td className="py-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                        t.verification_status === "PASSED" ? "bg-emerald-500/10 text-emerald-400" : (t.verification_status === "SKIPPED" ? "bg-slate-800 text-slate-400" : "bg-amber-500/10 text-amber-400")
                      }`}>
                        {t.verification_status}
                      </span>
                    </td>
                  </tr>
                );
              })}
              {traces.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    No execution traces recorded yet. Run queries in Playground or execute Benchmark Lab.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
