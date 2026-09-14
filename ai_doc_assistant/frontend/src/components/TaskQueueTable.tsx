import React from "react";
import { FileText, RefreshCw, Ban, Clock, ChevronRight } from "lucide-react";
import { TaskStatusBadge } from "./TaskStatusBadge";

import { TaskProgressBar } from "./TaskProgressBar";
import type { IngestionJob } from "../services/api";

interface TaskQueueTableProps {
  jobs: IngestionJob[];
  loading?: boolean;
  onSelectJob: (job: IngestionJob) => void;
  onRetryJob?: (jobId: string) => void;
  onCancelJob?: (jobId: string) => void;
}

export const TaskQueueTable: React.FC<TaskQueueTableProps> = ({
  jobs,
  loading,
  onSelectJob,
  onRetryJob,
  onCancelJob
}) => {
  const formatTime = (iso?: string | null) => {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return iso;
    }
  };

  const formatDuration = (job: IngestionJob) => {
    if (job.processing_time_ms) {
      return `${(job.processing_time_ms / 1000).toFixed(1)}s`;
    }
    if (job.started_at && job.status === "PROCESSING") {
      const diffMs = Date.now() - new Date(job.started_at).getTime();
      return `${Math.max(1, Math.round(diffMs / 1000))}s`;
    }
    return "—";
  };

  if (loading && jobs.length === 0) {
    return (
      <div className="py-20 text-center text-slate-500 text-sm animate-pulse">
        Loading task queue records...
      </div>
    );
  }

  if (!loading && jobs.length === 0) {
    return (
      <div className="py-20 px-6 text-center space-y-3 bg-surface/30 rounded-2xl border border-surfaceBorder/80">
        <div className="mx-auto w-12 h-12 rounded-2xl bg-slate-800/80 border border-slate-700/80 flex items-center justify-center text-slate-400">
          <Clock className="h-6 w-6" />
        </div>
        <h3 className="text-sm font-semibold text-slate-200">No Ingestion Tasks Found</h3>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          Upload documents via the Knowledge Base tab to dispatch asynchronous background ingestion tasks.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-surfaceBorder bg-surface/40 backdrop-blur-sm shadow-xl">
      <table className="w-full text-left text-xs">
        <thead className="bg-surface/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-surfaceBorder">
          <tr>
            <th className="py-3.5 px-4">Task ID</th>
            <th className="py-3.5 px-4">Document</th>
            <th className="py-3.5 px-4">Status</th>
            <th className="py-3.5 px-4 min-w-[160px]">Progress</th>
            <th className="py-3.5 px-4">Stage</th>
            <th className="py-3.5 px-4 text-center">Attempts</th>
            <th className="py-3.5 px-4">Created</th>
            <th className="py-3.5 px-4">Duration</th>
            <th className="py-3.5 px-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-surfaceBorder/60">
          {jobs.map((job) => {
            const canRetry = job.status === "FAILED" || job.status === "CANCELLED";
            const canCancel = job.status === "QUEUED" || job.status === "PROCESSING";

            return (
              <tr
                key={job.job_id}
                onClick={() => onSelectJob(job)}
                className="hover:bg-slate-800/40 cursor-pointer transition-colors group"
              >
                {/* Task ID */}
                <td className="py-3.5 px-4 font-mono font-medium text-slate-300">
                  <span className="text-primary-light group-hover:text-primary transition-colors">
                    {job.job_id}
                  </span>
                </td>

                {/* Document */}
                <td className="py-3.5 px-4">
                  <div className="flex items-center gap-2 max-w-[200px]">
                    <FileText className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                    <span className="truncate text-slate-200 font-medium" title={job.document_name || job.document_id}>
                      {job.document_name || job.document_id || "Document"}
                    </span>
                  </div>
                </td>

                {/* Status */}
                <td className="py-3.5 px-4">
                  <TaskStatusBadge status={job.status} size="sm" />
                </td>

                {/* Progress */}
                <td className="py-3.5 px-4">
                  <div className="max-w-[160px]">
                    <TaskProgressBar
                      progress={job.progress}
                      stage={job.current_stage}
                      status={job.status}
                      showLabel={true}
                    />
                  </div>
                </td>

                {/* Stage */}
                <td className="py-3.5 px-4 text-slate-300 capitalize">
                  {job.current_stage.replace(/_/g, " ")}
                </td>

                {/* Attempts */}
                <td className="py-3.5 px-4 text-center font-mono text-slate-400">
                  <span className={job.attempt_count > 1 ? "text-amber-400 font-bold" : ""}>
                    {job.attempt_count}/{job.max_attempts}
                  </span>
                </td>

                {/* Created At */}
                <td className="py-3.5 px-4 text-slate-400 font-mono whitespace-nowrap">
                  {formatTime(job.created_at)}
                </td>

                {/* Duration */}
                <td className="py-3.5 px-4 text-slate-400 font-mono whitespace-nowrap">
                  {formatDuration(job)}
                </td>

                {/* Actions */}
                <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center justify-end gap-1">
                    {canCancel && onCancelJob && (
                      <button
                        title="Cancel Task"
                        onClick={() => onCancelJob(job.job_id)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors"
                      >
                        <Ban className="h-3.5 w-3.5" />
                      </button>
                    )}

                    {canRetry && onRetryJob && (
                      <button
                        title="Retry Task"
                        onClick={() => onRetryJob(job.job_id)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-primary transition-colors hover:bg-slate-800"
                      >
                        <RefreshCw className="h-3.5 w-3.5" />
                      </button>
                    )}

                    <button
                      title="View Details"
                      onClick={() => onSelectJob(job)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
