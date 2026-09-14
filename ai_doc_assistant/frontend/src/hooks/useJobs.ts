import { useState, useEffect, useCallback } from "react";
import { api } from "../services/api";
import type { IngestionJob, JobListResponse } from "../services/api";

interface UseJobsOptions {
  status?: string;
  kbId?: string;
  pageSize?: number;
  autoRefreshIntervalMs?: number;
}

export const useJobs = (options: UseJobsOptions = {}) => {
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(options.pageSize || 15);
  const [statusFilter, setStatusFilter] = useState<string>(options.status || "ALL");
  const [kbFilter, setKbFilter] = useState<string>(options.kbId || "ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params: any = {
        page,
        page_size: pageSize
      };
      if (statusFilter && statusFilter !== "ALL") {
        params.status = statusFilter;
      }
      if (kbFilter && kbFilter !== "ALL") {
        params.knowledge_base_id = kbFilter;
      }

      const res: JobListResponse = await api.listJobs(params);
      setJobs(res.jobs || []);
      setTotal(res.total || 0);
    } catch (err: any) {
      console.error("Failed to fetch jobs:", err);
      setError(err.message || "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, statusFilter, kbFilter]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  // Periodic auto-refresh
  useEffect(() => {
    const interval = options.autoRefreshIntervalMs || 3500;
    const timer = setInterval(() => {
      fetchJobs();
    }, interval);
    return () => clearInterval(timer);
  }, [fetchJobs, options.autoRefreshIntervalMs]);

  // Client-side search query filtering by filename or job_id
  const filteredJobs = jobs.filter((j) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    const nameMatch = j.document_name?.toLowerCase().includes(q);
    const idMatch = j.job_id.toLowerCase().includes(q) || j.id.toLowerCase().includes(q);
    const stageMatch = j.current_stage.toLowerCase().includes(q);
    return nameMatch || idMatch || stageMatch;
  });

  return {
    jobs: filteredJobs,
    rawJobs: jobs,
    total,
    page,
    setPage,
    pageSize,
    setPageSize,
    statusFilter,
    setStatusFilter,
    kbFilter,
    setKbFilter,
    searchQuery,
    setSearchQuery,
    loading,
    error,
    refresh: fetchJobs
  };
};
