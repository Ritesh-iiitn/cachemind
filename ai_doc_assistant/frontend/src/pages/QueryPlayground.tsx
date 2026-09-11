import React, { useState, useEffect } from "react";
import { 
  Send, Sparkles, Zap, Clock, 
  Cpu, Database, CheckCircle2,
  RotateCcw
} from "lucide-react";
import { api } from "../services/api";
import type { KnowledgeBase, QueryResponse } from "../services/api";

export const QueryPlayground: React.FC = () => {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [selectedKbId, setSelectedKbId] = useState<string>("");
  const [query, setQuery] = useState("");
  const [forceNoCache, setForceNoCache] = useState(false);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<QueryResponse | null>(null);

  useEffect(() => {
    api.listKnowledgeBases().then((data) => {
      setKbs(data);
      if (data.length > 0) setSelectedKbId(data[0].id);
    });
  }, []);

  const handleExecute = async (overrideQuery?: string) => {
    const q = overrideQuery || query;
    if (!q.trim() || !selectedKbId) return;

    try {
      setLoading(true);
      const res = await api.executeQuery(selectedKbId, q, forceNoCache);
      setResponse(res);
    } catch (err) {
      console.error("Query failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const sampleScenarios = [
    {
      label: "1. Initial Conceptual Query (Cache MISS)",
      query: "What is the high-level architecture and caching hierarchy in CacheMind?",
    },
    {
      label: "2. Semantic Paraphrase (L2 Semantic Cache HIT)",
      query: "Can you explain the system architecture and multi-tier cache layers?",
    },
    {
      label: "3. Complex Multi-Hop Comparison (Agentic Routing)",
      query: "Compare the scalability and memory bandwidth tradeoffs between Naive Attention and KV Cache decoding.",
    }
  ];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Adaptive Query Playground & Execution Tracer
          </h1>
          <p className="text-sm text-slate-400">
            Submit queries to test real-time cache planning, semantic similarity matching, adaptive model routing, and verification loops.
          </p>
        </div>

        {/* KB Selector */}
        <div className="flex items-center gap-2 bg-surface p-1.5 rounded-xl border border-surfaceBorder">
          <Database className="h-4 w-4 text-primary ml-2" />
          <select
            value={selectedKbId}
            onChange={(e) => setSelectedKbId(e.target.value)}
            className="bg-transparent text-xs text-white border-none focus:outline-none pr-2 font-medium"
          >
            {kbs.map((kb) => (
              <option key={kb.id} value={kb.id} className="bg-surface text-white">
                {kb.name} (v{kb.version})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Demo Scenario Shortcuts */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-slate-400 flex items-center gap-1 mr-1">
          <Sparkles className="h-3.5 w-3.5 text-accent" /> Demo Flows:
        </span>
        {sampleScenarios.map((sc, i) => (
          <button
            key={i}
            onClick={() => {
              setQuery(sc.query);
              handleExecute(sc.query);
            }}
            className="px-3 py-1.5 rounded-xl bg-surface hover:bg-slate-800 border border-surfaceBorder hover:border-slate-600 text-xs text-slate-300 transition-all font-medium"
          >
            {sc.label}
          </button>
        ))}
      </div>

      {/* Query Input Box */}
      <div className="p-4 rounded-2xl bg-surface border border-surfaceBorder space-y-3 shadow-lg">
        <div className="relative">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleExecute();
              }
            }}
            rows={3}
            placeholder="Ask a factual question, comparison, or technical query..."
            className="w-full p-3 rounded-xl bg-background border border-surfaceBorder text-sm text-white placeholder-slate-500 focus:outline-none focus:border-primary resize-none font-sans"
          />
        </div>

        <div className="flex items-center justify-between">
          <label className="flex items-center space-x-2 text-xs text-slate-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={forceNoCache}
              onChange={(e) => setForceNoCache(e.target.checked)}
              className="rounded bg-background border-surfaceBorder text-primary focus:ring-0"
            />
            <span>Bypass Cache (Force Cold Execution)</span>
          </label>

          <button
            onClick={() => handleExecute()}
            disabled={loading || !query.trim()}
            className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover disabled:opacity-50 text-white text-xs font-semibold transition-all shadow-md shadow-primary/20"
          >
            {loading ? (
              <>
                <RotateCcw className="h-4 w-4 animate-spin" />
                <span>Executing Plan...</span>
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                <span>Run Execution</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Execution Results View */}
      {response && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fadeIn">
          {/* Main Answer & Citations Column */}
          <div className="lg:col-span-2 space-y-5">
            {/* Answer Card */}
            <div className="p-5 rounded-2xl bg-surface border border-surfaceBorder space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-surfaceBorder">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-accent" />
                  <h3 className="text-sm font-semibold text-white">Synthesized Response</h3>
                </div>
                {/* Cache Badge */}
                <div className="flex items-center gap-2">
                  {response.cache_status.exact_cache_hit && (
                    <span className="px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-primary/20 text-primary-light border border-primary/40 flex items-center gap-1.5">
                      <Zap className="h-3.5 w-3.5" /> L1 EXACT CACHE HIT (0ms LLM)
                    </span>
                  )}
                  {response.cache_status.semantic_cache_hit && (
                    <span className="px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-accent/20 text-accent border border-accent/40 flex items-center gap-1.5">
                      <Zap className="h-3.5 w-3.5" /> L2 SEMANTIC CACHE HIT (Sim: {((response.cache_status.similarity_score || 0.92) * 100).toFixed(1)}%)
                    </span>
                  )}
                  {!response.cache_status.exact_cache_hit && !response.cache_status.semantic_cache_hit && (
                    <span className="px-2.5 py-1 rounded-full text-xs font-mono font-medium bg-slate-800 text-slate-300 border border-slate-700">
                      COLD EXECUTION (Cache MISS)
                    </span>
                  )}
                </div>
              </div>

              <div className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap font-sans">
                {response.answer}
              </div>

              {/* Citations List */}
              {response.citations.length > 0 && (
                <div className="pt-4 border-t border-surfaceBorder space-y-3">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                    <span>Verified Knowledge Citations ({response.citations.length})</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {response.citations.map((cit, idx) => (
                      <div key={idx} className="p-3 rounded-xl bg-background/50 border border-surfaceBorder space-y-1">
                        <div className="flex items-center justify-between text-[11px] font-medium text-primary-light">
                          <span>{cit.filename} (Page {cit.page_number || 1})</span>
                          <span className="font-mono text-[10px] text-slate-500">{cit.chunk_id}</span>
                        </div>
                        <p className="text-xs text-slate-400 line-clamp-3">{cit.snippet}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Execution Plan & Observability Trace */}
          <div className="space-y-5">
            {/* Plan Summary Card */}
            <div className="p-5 rounded-2xl bg-surface border border-surfaceBorder space-y-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Cpu className="h-4 w-4 text-primary" />
                <span>Execution Plan & Routing</span>
              </h3>

              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between py-1 border-b border-surfaceBorder/50">
                  <span className="text-slate-400">Plan ID</span>
                  <span className="font-mono text-slate-200">{response.execution_plan.plan_id}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-surfaceBorder/50">
                  <span className="text-slate-400">Query Complexity</span>
                  <span className="font-mono uppercase text-accent font-medium">{response.execution_plan.query_complexity}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-surfaceBorder/50">
                  <span className="text-slate-400">Retrieval Strategy</span>
                  <span className="font-mono uppercase text-emerald-400 font-medium">{response.execution_plan.retrieval_strategy}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-surfaceBorder/50">
                  <span className="text-slate-400">Model Assigned</span>
                  <span className="font-mono text-slate-200">{response.model_used}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-surfaceBorder/50">
                  <span className="text-slate-400">Total Latency</span>
                  <span className="font-mono text-primary-light font-bold">{response.total_latency_ms} ms</span>
                </div>
                <div className="flex justify-between py-1 border-b border-surfaceBorder/50">
                  <span className="text-slate-400">Tokens Saved</span>
                  <span className="font-mono text-emerald-400 font-bold">+{response.tokens_saved}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-400">Verification</span>
                  <span className="font-mono text-emerald-400 font-bold">{response.verification_status}</span>
                </div>
              </div>
            </div>

            {/* Execution Trace Timeline */}
            <div className="p-5 rounded-2xl bg-surface border border-surfaceBorder space-y-3">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Clock className="h-4 w-4 text-amber-400" />
                <span>Micro-Step Trace</span>
              </h3>

              <div className="space-y-2 text-xs">
                {response.steps_executed.map((step, idx) => (
                  <div key={idx} className="flex items-center gap-2 p-2 rounded-lg bg-background/40 border border-surfaceBorder/60">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                    <span className="font-mono text-slate-300 flex-1">{step}</span>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {response.latency_breakdown_ms[step] !== undefined ? `${response.latency_breakdown_ms[step]} ms` : "done"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
