import React, { useState, useEffect } from "react";
import { 
  Layers, Trash2, RefreshCw
} from "lucide-react";
import { api } from "../services/api";
import type { CacheEntry, CacheStats } from "../services/api";

export const CacheExplorer: React.FC = () => {
  const [entries, setEntries] = useState<CacheEntry[]>([]);
  const [stats, setStats] = useState<CacheStats | null>(null);
  const [selectedTier, setSelectedTier] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const fetchCacheData = async () => {
    try {
      setLoading(true);
      const [entriesData, statsData] = await Promise.all([
        api.listCacheEntries(),
        api.getCacheStats()
      ]);
      setEntries(entriesData);
      setStats(statsData);
    } catch (err) {
      console.error("Cache fetch failed:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCacheData();
  }, []);

  const handleFlushAll = async () => {
    if (!window.confirm("Flush all cache tiers globally? This will clear all exact, semantic, and retrieval entries.")) return;
    try {
      await api.flushAllCaches();
      setActionMsg("All multi-layer cache entries purged.");
      await fetchCacheData();
    } catch (err) {
      console.error(err);
    }
  };

  const filteredEntries = entries.filter((e) => {
    if (selectedTier === "ALL") return true;
    if (selectedTier === "L1" && e.tier.includes("Exact")) return true;
    if (selectedTier === "L2" && e.tier.includes("Semantic")) return true;
    if (selectedTier === "L4" && e.tier.includes("Retrieval")) return true;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Multi-Tier Cache Explorer & Inspector
          </h1>
          <p className="text-sm text-slate-400">
            Inspect live memory keys, TTL expirations, hit frequencies, and trigger deterministic namespace invalidation.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchCacheData}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-surface border border-surfaceBorder hover:border-slate-600 text-xs text-slate-300 transition-all font-medium"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleFlushAll}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-rose-500/10 border border-rose-500/30 hover:bg-rose-500/20 text-xs text-rose-400 font-medium transition-all"
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span>Flush All Caches</span>
          </button>
        </div>
      </div>

      {actionMsg && (
        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-400 flex items-center justify-between">
          <span>{actionMsg}</span>
          <button onClick={() => setActionMsg(null)}>✕</button>
        </div>
      )}

      {/* Tier Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div 
          onClick={() => setSelectedTier("L1")}
          className={`p-4 rounded-2xl border cursor-pointer transition-all ${
            selectedTier === "L1" ? "bg-primary/10 border-primary/50" : "bg-surface border-surfaceBorder hover:border-slate-700"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium uppercase">L1 Exact Cache</span>
            <span className="h-2 w-2 rounded-full bg-primary" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-white">
            {stats?.exact_cache_size ?? 0} <span className="text-xs font-normal text-slate-400">keys</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">SHA-256 normalized hash • &lt; 1ms latency</p>
        </div>

        <div 
          onClick={() => setSelectedTier("L2")}
          className={`p-4 rounded-2xl border cursor-pointer transition-all ${
            selectedTier === "L2" ? "bg-accent/10 border-accent/50" : "bg-surface border-surfaceBorder hover:border-slate-700"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium uppercase">L2 Semantic Cache</span>
            <span className="h-2 w-2 rounded-full bg-accent" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-white">
            {stats?.semantic_cache_size ?? 0} <span className="text-xs font-normal text-slate-400">vectors</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">FAISS Cosine Sim (≥0.88) + Entity Guardrail</p>
        </div>

        <div 
          onClick={() => setSelectedTier("L4")}
          className={`p-4 rounded-2xl border cursor-pointer transition-all ${
            selectedTier === "L4" ? "bg-emerald-500/10 border-emerald-500/50" : "bg-surface border-surfaceBorder hover:border-slate-700"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-medium uppercase">L4 Retrieval Cache</span>
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-white">
            {stats?.retrieval_cache_size ?? 0} <span className="text-xs font-normal text-slate-400">query pools</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Chunk score pools cached per KB version</p>
        </div>
      </div>

      {/* Filter Tabs & Entries Table */}
      <div className="p-5 rounded-2xl bg-surface border border-surfaceBorder space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-surfaceBorder">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold text-white">Cached Key Registry</h3>
          </div>
          <div className="flex items-center gap-1 text-xs">
            {["ALL", "L1", "L2", "L4"].map((t) => (
              <button
                key={t}
                onClick={() => setSelectedTier(t)}
                className={`px-2.5 py-1 rounded-lg transition-all font-mono font-medium ${
                  selectedTier === t ? "bg-primary text-white" : "bg-background text-slate-400 hover:text-white"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-surfaceBorder text-slate-400">
                <th className="pb-2 font-medium">Tier</th>
                <th className="pb-2 font-medium">Cache Key</th>
                <th className="pb-2 font-medium">Cached Snippet</th>
                <th className="pb-2 font-medium">Created At</th>
                <th className="pb-2 font-medium">TTL Remaining</th>
                <th className="pb-2 font-medium">Hit Count</th>
                <th className="pb-2 font-medium">Size</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surfaceBorder/40">
              {filteredEntries.map((e, idx) => (
                <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-800 text-slate-300 border border-slate-700">
                      {e.tier}
                    </span>
                  </td>
                  <td className="py-3 font-mono text-primary-light">{e.key}</td>
                  <td className="py-3 text-slate-300 max-w-sm truncate">{e.query_snippet}</td>
                  <td className="py-3 text-slate-400">{e.created_at}</td>
                  <td className="py-3 font-mono text-amber-400">{e.ttl_remaining_seconds}s</td>
                  <td className="py-3 font-mono text-emerald-400">⚡ {e.hit_count}</td>
                  <td className="py-3 font-mono text-slate-400">{e.size_bytes} B</td>
                </tr>
              ))}
              {filteredEntries.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-500">
                    No cache entries found. Execute queries in the Playground to generate cache keys.
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
