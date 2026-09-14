import React, { useState } from "react";
import { X, RefreshCw, Ban, ShieldAlert } from "lucide-react";
import { TaskStatusBadge } from "./TaskStatusBadge";

import { TaskProgressBar } from "./TaskProgressBar";
import { api } from "../services/api";
import type { IngestionJob } from "../services/api";

interface TaskDetailsDrawerProps {
  job: IngestionJob | null;
  isOpen: boolean;
  onClose: () => void;
  onJobUpdated?: () => void;
}

const PIPELINE_STAGES = [
  { id: "accepted", label: "Accepted", threshold: 0 },
  { id: "queued", label: "Queued", threshold: 5 },
  { id: "parsing", label: "Parsing", threshold: 10 },
  { id: "cleaning", label: "Cleaning", threshold: 25 },
  { id: "chunking", label: "Chunking", threshold: 40 },
  { id: "generating_embeddings", label: "Embedding", threshold: 70 },
  { id: "indexing", label: "Indexing", threshold: 85 },
  { id: "invalidating_cache", label: "Cache Invalidation", threshold: 95 },
  { id: "completed", label: "Completed", threshold: 100 }
];

export const TaskDetailsDrawer: React.FC<TaskDetailsDrawerProps> = ({
  job,
  isOpen,
  onClose,
  onJobUpdated
}) => {
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  if (!isOpen || !job) return null;

  const handleRetry = async () => {
    try {
      setActionLoading(true);
      setActionMessage(null);
      await api.retryJob(job.job_id);
      setActionMessage("Job re-queued successfully.");
      onJobUpdated?.();
    } catch (err: any) {
      setActionMessage(`Retry failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!window.confirm(`Cancel task ${job.job_id}?`)) return;
    try {
      setActionLoading(true);
      setActionMessage(null);
      await api.cancelJob(job.job_id);
      setActionMessage("Job cancelled.");
      onJobUpdated?.();
    } catch (err: any) {
      setActionMessage(`Cancel failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const formatTime = (iso?: string | null) => {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return iso;
    }
  };

  const canRetry = job.status === "FAILED" || job.status === "CANCELLED" || job.status === "RETRYING";
  const canCancel = job.status === "QUEUED" || job.status === "PROCESSING";

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end animate-fadeIn">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Drawer Panel */}
      <div className="relative w-full max-w-xl bg-surface border-l border-surfaceBorder h-full flex flex-col shadow-2xl z-10 overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-surfaceBorder flex items-center justify-between sticky top-0 bg-surface/95 backdrop-blur z-20">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-white tracking-tight">Task Details</h2>
              <TaskStatusBadge status={job.status} size="sm" />
            </div>
            <p className="text-xs font-mono text-slate-400 mt-1">{job.job_id}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Action feedback */}
        {actionMessage && (
          <div className="mx-6 mt-4 p-3 rounded-lg bg-primary/10 border border-primary/20 text-xs text-primary-light flex items-center justify-between">
            <span>{actionMessage}</span>
            <button onClick={() => setActionMessage(null)} className="text-slate-400 hover:text-white">✕</button>
          </div>
        )}

        <div className="p-6 space-y-6 flex-1">
          {/* Progress Bar & Stage */}
          <div className="p-4 rounded-xl bg-background/60 border border-surfaceBorder/80 space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Current Progress</span>
              <span className="font-mono text-white font-semibold">{job.progress}%</span>
            </div>
            <TaskProgressBar progress={job.progress} stage={job.current_stage} status={job.status} showLabel={false} />
            <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
              <span>Stage: <span className="text-slate-200 font-medium">{job.current_stage}</span></span>
              <span>Attempts: <span className="font-mono text-slate-200">{job.attempt_count} / {job.max_attempts}</span></span>
            </div>
          </div>

          {/* Visual Pipeline Stepper */}
          <div className="p-4 rounded-xl bg-background/60 border border-surfaceBorder/80 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Execution Pipeline</h3>
            <div className="space-y-2 pt-1">
              {PIPELINE_STAGES.map((step, idx) => {
                const isPassed = job.progress > step.threshold || job.status === "COMPLETED";
                const isCurrent = job.status === "PROCESSING" && job.progress >= step.threshold && (idx === PIPELINE_STAGES.length - 1 || job.progress < PIPELINE_STAGES[idx + 1].threshold);
                const isFailed = job.status === "FAILED" && isCurrent;

                return (
                  <div key={step.id} className="flex items-center gap-3 text-xs">
                    <div className="w-5 flex justify-center">
                      {isPassed ? (
                        <div className="h-4 w-4 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center justify-center text-[10px]">
                          ✓
                        </div>
                      ) : isFailed ? (
                        <div className="h-4 w-4 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/40 flex items-center justify-center text-[10px]">
                          ✕
                        </div>
                      ) : isCurrent ? (
                        <div className="h-4 w-4 rounded-full bg-sky-500/20 text-sky-400 border border-sky-500/40 flex items-center justify-center animate-pulse text-[10px]">
                          ●
                        </div>
                      ) : (
                        <div className="h-3 w-3 rounded-full border border-slate-700 bg-slate-800" />
                      )}
                    </div>
                    <span className={`font-medium ${isCurrent ? "text-sky-400 font-bold" : isPassed ? "text-slate-300" : "text-slate-500"}`}>
                      {step.label}
                    </span>
                    {isCurrent && (
                      <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20 ml-auto">
                        In Progress
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Core Metadata */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Metadata</h3>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-background/40 border border-surfaceBorder/60">
                <span className="text-slate-500 block">Document</span>
                <span className="font-medium text-slate-200 truncate block mt-0.5">{job.document_name || job.document_id || "—"}</span>
              </div>
              <div className="p-3 rounded-lg bg-background/40 border border-surfaceBorder/60">
                <span className="text-slate-500 block">Knowledge Base</span>
                <span className="font-medium text-slate-200 truncate block mt-0.5">{job.knowledge_base_id || "—"}</span>
              </div>
              <div className="p-3 rounded-lg bg-background/40 border border-surfaceBorder/60">
                <span className="text-slate-500 block">Task Type</span>
                <span className="font-medium text-slate-200 block mt-0.5">{job.task_type}</span>
              </div>
              <div className="p-3 rounded-lg bg-background/40 border border-surfaceBorder/60">
                <span className="text-slate-500 block">Worker ID</span>
                <span className="font-mono text-slate-300 block mt-0.5 truncate">{job.worker_id || "Assigned on dequeue"}</span>
              </div>
            </div>
          </div>

          {/* Timings & Durations */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Timings & Latency</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs font-mono">
              <div className="p-3 rounded-lg bg-background/40 border border-surfaceBorder/60">
                <span className="text-slate-500 text-[11px] block font-sans">Created</span>
                <span className="text-slate-200 mt-0.5 block">{formatTime(job.created_at)}</span>
              </div>
              <div className="p-3 rounded-lg bg-background/40 border border-surfaceBorder/60">
                <span className="text-slate-500 text-[11px] block font-sans">Started</span>
                <span className="text-slate-200 mt-0.5 block">{formatTime(job.started_at)}</span>
              </div>
              <div className="p-3 rounded-lg bg-background/40 border border-surfaceBorder/60">
                <span className="text-slate-500 text-[11px] block font-sans">Completed</span>
                <span className="text-slate-200 mt-0.5 block">{formatTime(job.completed_at)}</span>
              </div>
              <div className="p-3 rounded-lg bg-background/40 border border-surfaceBorder/60">
                <span className="text-slate-500 text-[11px] block font-sans">Queue Wait</span>
                <span className="text-amber-400 mt-0.5 block">
                  {job.queue_wait_time_ms ? `${Math.round(job.queue_wait_time_ms)} ms` : "—"}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-background/40 border border-surfaceBorder/60">
                <span className="text-slate-500 text-[11px] block font-sans">Processing Time</span>
                <span className="text-sky-400 mt-0.5 block">
                  {job.processing_time_ms ? `${(job.processing_time_ms / 1000).toFixed(2)}s` : "—"}
                </span>
              </div>
              <div className="p-3 rounded-lg bg-background/40 border border-surfaceBorder/60">
                <span className="text-slate-500 text-[11px] block font-sans">Queue Pos / Est Wait</span>
                <span className="text-slate-300 mt-0.5 block">
                  {job.queue_position ? `#${job.queue_position} (~${((job.estimated_wait_time_ms || 0)/1000).toFixed(1)}s)` : "—"}
                </span>
              </div>
            </div>
          </div>

          {/* Error Details (if any) */}
          {job.error_message && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 space-y-1.5">
              <div className="flex items-center gap-2 text-rose-400 text-xs font-semibold">
                <ShieldAlert className="h-4 w-4" />
                <span>Error Code: {job.error_code || "EXECUTION_ERROR"}</span>
              </div>
              <p className="text-xs font-mono text-rose-300 break-words leading-relaxed">
                {job.error_message}
              </p>
            </div>
          )}

          {/* Retry History */}
          {job.retry_history && job.retry_history.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Retry History</h3>
              <div className="space-y-2">
                {job.retry_history.map((rh, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-background/50 border border-surfaceBorder text-xs space-y-1 font-mono">
                    <div className="flex items-center justify-between text-slate-300">
                      <span>Attempt #{rh.attempt}</span>
                      <span className="text-[11px] text-slate-500">{formatTime(rh.timestamp)}</span>
                    </div>
                    <div className="text-[11px] text-amber-400">
                      Delay: {rh.delay_seconds}s • Code: {rh.error_code || "TRANSIENT"}
                    </div>
                    {rh.error_message && (
                      <div className="text-[11px] text-slate-400 truncate">{rh.error_message}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-6 border-t border-surfaceBorder bg-surface/95 backdrop-blur flex items-center justify-between sticky bottom-0 z-20">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
          >
            Close
          </button>

          <div className="flex items-center gap-2">
            {canCancel && (
              <button
                onClick={handleCancel}
                disabled={actionLoading}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 text-xs font-semibold transition-all disabled:opacity-50"
              >
                <Ban className="h-3.5 w-3.5" />
                <span>Cancel Task</span>
              </button>
            )}

            {canRetry && (
              <button
                onClick={handleRetry}
                disabled={actionLoading}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-primary hover:bg-primary-hover text-white text-xs font-semibold shadow-lg shadow-primary/25 transition-all disabled:opacity-50"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${actionLoading ? "animate-spin" : ""}`} />
                <span>Retry Job</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
