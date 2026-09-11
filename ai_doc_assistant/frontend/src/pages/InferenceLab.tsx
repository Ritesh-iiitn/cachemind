import React, { useState, useEffect } from "react";
import { 
  Layers, Activity, Play, 
  MemoryStick, Sliders 
} from "lucide-react";
import { 
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, 
  Tooltip, Legend, CartesianGrid 
} from "recharts";
import { api } from "../services/api";

export const InferenceLab: React.FC = () => {
  const [promptTokens, setPromptTokens] = useState<number>(1024);
  const [genTokens, setGenTokens] = useState<number>(256);
  const [hiddenDim, setHiddenDim] = useState<number>(4096);
  const [numHeads, setNumHeads] = useState<number>(32);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const runBenchmark = async () => {
    try {
      setLoading(true);
      const data = await api.runKVBenchmark(promptTokens, genTokens, hiddenDim, numHeads);
      setResult(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runBenchmark();
  }, []);

  const comparisonData = result ? [
    {
      metric: "Prefill Latency (ms)",
      Naive: result.naive_attention.prefill_latency_ms,
      KVCached: result.kv_cached_attention.prefill_latency_ms
    },
    {
      metric: "Decode Latency (ms)",
      Naive: result.naive_attention.decode_latency_ms,
      KVCached: result.kv_cached_attention.decode_latency_ms
    },
    {
      metric: "Total Latency (ms)",
      Naive: result.naive_attention.total_latency_ms,
      KVCached: result.kv_cached_attention.total_latency_ms
    },
    {
      metric: "Time To First Token (ms)",
      Naive: result.naive_attention.ttft_ms,
      KVCached: result.kv_cached_attention.ttft_ms
    }
  ] : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Inference Lab & KV-Cache Systems Profiler
          </h1>
          <p className="text-sm text-slate-400">
            Low-level transformer attention profiling: Mathematical and computational proof of O(N²) Naive Attention vs O(1) Stateful KV Cache.
          </p>
        </div>
      </div>

      {/* Conceptual Callout: Semantic Cache != KV Cache */}
      <div className="p-4 rounded-2xl bg-primary/10 border border-primary/20 text-xs space-y-1">
        <div className="flex items-center gap-2 font-semibold text-primary-light">
          <Layers className="h-4 w-4" />
          <span>Architectural Distinction: Application Semantic Caching vs. Inference KV Caching</span>
        </div>
        <p className="text-slate-300 leading-relaxed">
          <b>Semantic Response Cache (L2)</b> caches finalized natural language text based on prompt vector similarity (≥ 0.88). 
          <b>KV Cache (Layer 6)</b> operates at the deep learning runtime layer inside transformer self-attention (Q · K^T), storing key/value tensor matrices in VRAM/RAM to eliminate redundant matrix operations during autoregressive decoding.
        </p>
      </div>

      {/* Interactive Controls & Parameter Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Controls Card */}
        <div className="p-5 rounded-2xl bg-surface border border-surfaceBorder space-y-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Sliders className="h-4 w-4 text-primary" />
            <span>Attention Parameters</span>
          </h3>

          <div className="space-y-3 text-xs">
            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Prompt Length (Tokens)</span>
                <span className="font-mono text-primary-light font-bold">{promptTokens}</span>
              </div>
              <input
                type="range"
                min="128"
                max="4096"
                step="128"
                value={promptTokens}
                onChange={(e) => setPromptTokens(Number(e.target.value))}
                className="w-full accent-primary"
              />
            </div>

            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Generated Length (Tokens)</span>
                <span className="font-mono text-primary-light font-bold">{genTokens}</span>
              </div>
              <input
                type="range"
                min="32"
                max="512"
                step="32"
                value={genTokens}
                onChange={(e) => setGenTokens(Number(e.target.value))}
                className="w-full accent-primary"
              />
            </div>

            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Hidden Dimension (d_model)</span>
                <span className="font-mono text-primary-light font-bold">{hiddenDim}</span>
              </div>
              <select
                value={hiddenDim}
                onChange={(e) => setHiddenDim(Number(e.target.value))}
                className="w-full p-2 rounded-lg bg-background border border-surfaceBorder text-white text-xs"
              >
                <option value={1024}>1024 (Small - 0.5B)</option>
                <option value={2048}>2048 (Medium - 3B)</option>
                <option value={4096}>4096 (Large - 7B/8B)</option>
              </select>
            </div>

            <div>
              <div className="flex justify-between text-slate-300 mb-1">
                <span>Attention Heads (h)</span>
                <span className="font-mono text-primary-light font-bold">{numHeads}</span>
              </div>
              <select
                value={numHeads}
                onChange={(e) => setNumHeads(Number(e.target.value))}
                className="w-full p-2 rounded-lg bg-background border border-surfaceBorder text-white text-xs"
              >
                <option value={8}>8 Heads</option>
                <option value={16}>16 Heads</option>
                <option value={32}>32 Heads</option>
              </select>
            </div>

            <button
              onClick={runBenchmark}
              disabled={loading}
              className="w-full py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white font-medium transition-all shadow-md shadow-primary/20 flex items-center justify-center gap-1.5"
            >
              <Play className="h-3.5 w-3.5" />
              <span>Simulate Attention Profile</span>
            </button>
          </div>
        </div>

        {/* Results Analytics Grid */}
        <div className="lg:col-span-3 space-y-6">
          {/* Key Stat Cards */}
          {result && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded-2xl bg-surface border border-surfaceBorder">
                <span className="text-xs font-medium text-slate-400 uppercase">Decode Speedup</span>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="text-3xl font-bold font-mono text-emerald-400">
                    {result.comparison.decode_speedup_factor}x
                  </span>
                  <span className="text-xs text-emerald-400 font-medium">faster</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Naive: {result.naive_attention.tokens_per_second} t/s → KV: {result.kv_cached_attention.tokens_per_second} t/s
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-surface border border-surfaceBorder">
                <span className="text-xs font-medium text-slate-400 uppercase">Memory Bandwidth Saved</span>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="text-3xl font-bold font-mono text-primary-light">
                    {result.comparison.memory_bandwidth_saved_pct}%
                  </span>
                  <MemoryStick className="h-4 w-4 text-primary" />
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  {result.naive_attention.total_memory_traffic_mb} MB vs {result.kv_cached_attention.total_memory_traffic_mb} MB
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-surface border border-surfaceBorder">
                <span className="text-xs font-medium text-slate-400 uppercase">Throughput Gain</span>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="text-3xl font-bold font-mono text-accent">
                    {(result.kv_cached_attention.tokens_per_second / Math.max(1, result.naive_attention.tokens_per_second)).toFixed(1)}x
                  </span>
                  <Activity className="h-4 w-4 text-accent" />
                </div>
                <p className="text-xs text-slate-500 mt-1">Token generation efficiency</p>
              </div>
            </div>
          )}

          {/* Latency Comparison Graph */}
          <div className="p-5 rounded-2xl bg-surface border border-surfaceBorder space-y-4">
            <h3 className="text-sm font-semibold text-white">Attention Latency Matrix (ms)</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={comparisonData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                  <XAxis dataKey="metric" stroke="#64748b" fontSize={11} />
                  <YAxis stroke="#64748b" fontSize={11} unit="ms" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: "#111827", borderColor: "#1f2937", borderRadius: "8px", fontSize: "12px" }} 
                  />
                  <Legend wrapperStyle={{ fontSize: "12px" }} />
                  <Bar dataKey="Naive" fill="#ef4444" radius={[4, 4, 0, 0]} name="Naive Attention O(N²)" />
                  <Bar dataKey="KVCached" fill="#10b981" radius={[4, 4, 0, 0]} name="KV-Cached Attention O(1)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
