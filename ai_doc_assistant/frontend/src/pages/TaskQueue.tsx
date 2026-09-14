import React, { useState } from "react";
import { 
  ListFilter, Search, RefreshCw, AlertCircle, 
  CheckCircle2, ChevronLeft, ChevronRight 
} from "lucide-react";

import { QueueStatsCards } from "../components/QueueStatsCards";
import { TaskQueueTable } from "../components/TaskQueueTable";
import { TaskDetailsDrawer } from "../components/TaskDetailsDrawer";
import { useJobs } from "../hooks/useJobs";
import { useQueueStats } from "../hooks/useQueueStats";
import { api } from "../services/api";
import type { IngestionJob } from "../services/api";

export const TaskQueue: React.FC = () => {
  const [selectedJob, setSelectedJob] = useState<IngestionJob | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [notification, setNotification] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const {
    jobs,
    total,
    page,
    setPage,
    pageSize,
    statusFilter,
    setStatusFilter,
    searchQuery,
    setSearchQuery,
    loading: jobsLoading,
    refresh: refreshJobs
  } = useJobs({ autoRefreshIntervalMs: 3500 });

  const { stats, loading: statsLoading, refresh: refreshStats } = useQueueStats(4000);

  const handleSelectJob = (job: IngestionJob) => {
    setSelectedJob(job);
    setDrawerOpen(true);
  };

  const handleRetryJob = async (jobId: string) => {
    try {
      await api.retryJob(jobId);
      setNotification({ message: `Job ${jobId} re-enqueued for execution.`, type: "success" });
      refreshJobs();
      refreshStats();
    } catch (err: any) {
      setNotification({ message: `Failed to retry job: ${err.message}`, type: "error" });
    }
  };

  const handleCancelJob = async (jobId: string) => {
    if (!window.confirm(`Cancel background task ${jobId}?`)) return;
    try {
      await api.cancelJob(jobId);
      setNotification({ message: `Job ${jobId} cancelled.`, type: "success" });
      refreshJobs();
      refreshStats();
    } catch (err: any) {
      setNotification({ message: `Failed to cancel job: ${err.message}`, type: "error" });
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            Distributed Task Queue & Ingestion Pipeline
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time monitoring of Redis-backed asynchronous document ingestion, background workers, and cache invalidation jobs.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              refreshJobs();
              refreshStats();
            }}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-surface border border-surfaceBorder hover:bg-slate-800 text-xs font-semibold text-slate-300 hover:text-white transition-all shadow-sm"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${jobsLoading || statsLoading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Alert Notification */}
      {notification && (
        <div
          className={`p-3 rounded-xl border text-xs flex items-center justify-between ${
            notification.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
              : "bg-rose-500/10 border-rose-500/20 text-rose-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === "success" ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            ) : (
              <AlertCircle className="h-4 w-4 text-rose-400" />
            )}
            <span>{notification.message}</span>
          </div>
          <button onClick={() => setNotification(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Real-time Queue Stats Cards */}
      <QueueStatsCards stats={stats} loading={statsLoading} />

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-2xl bg-surface/60 border border-surfaceBorder flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-md">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 bg-background/80 border border-surfaceBorder rounded-xl px-3 py-1.5 text-xs text-slate-300">
            <ListFilter className="h-3.5 w-3.5 text-slate-400" />
            <span className="text-slate-500 mr-1">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="bg-transparent text-white focus:outline-none cursor-pointer font-medium"
            >
              <option value="ALL" className="bg-slate-900">All Statuses</option>
              <option value="QUEUED" className="bg-slate-900">Queued</option>
              <option value="PROCESSING" className="bg-slate-900">Processing</option>
              <option value="RETRYING" className="bg-slate-900">Retrying</option>
              <option value="COMPLETED" className="bg-slate-900">Completed</option>
              <option value="FAILED" className="bg-slate-900">Failed</option>
              <option value="CANCELLED" className="bg-slate-900">Cancelled</option>
            </select>
          </div>

          <div className="relative flex-1 sm:w-64">
            <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search filename or Job ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-background/80 border border-surfaceBorder rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary/50 transition-colors"
            />
          </div>
        </div>

        <div className="text-xs text-slate-400 flex items-center justify-between sm:justify-end gap-3">
          <span>
            Showing <strong className="text-white">{jobs.length}</strong> of <strong className="text-white">{total}</strong> tasks
          </span>
        </div>
      </div>

      {/* Task Queue Table */}
      <TaskQueueTable
        jobs={jobs}
        loading={jobsLoading}
        onSelectJob={handleSelectJob}
        onRetryJob={handleRetryJob}
        onCancelJob={handleCancelJob}
      />

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-slate-400 pt-2 px-1">
          <span>Page {page} of {totalPages}</span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1.5 rounded-lg border border-surfaceBorder bg-surface hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-slate-300"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-1.5 rounded-lg border border-surfaceBorder bg-surface hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-slate-300"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Slide-over Task Details Drawer */}
      <TaskDetailsDrawer
        job={selectedJob}
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onJobUpdated={() => {
          refreshJobs();
          refreshStats();
          if (selectedJob) {
            api.getJob(selectedJob.job_id).then((j) => setSelectedJob(j)).catch(() => {});
          }
        }}
      />
    </div>
  );
};
