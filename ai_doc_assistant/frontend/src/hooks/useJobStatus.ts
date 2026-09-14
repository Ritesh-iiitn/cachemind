import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "../services/api";
import type { IngestionJob } from "../services/api";

export const useJobStatus = (jobId: string | null) => {
  const [job, setJob] = useState<IngestionJob | null>(null);
  const [loading, setLoading] = useState<boolean>(Boolean(jobId));
  const [error, setError] = useState<string | null>(null);
  const [isConnectedWs, setIsConnectedWs] = useState<boolean>(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pollTimerRef = useRef<any>(null);

  const fetchJob = useCallback(async (id: string) => {
    try {
      const data = await api.getJob(id);
      setJob(data);
      return data;
    } catch (err: any) {
      setError(err.message || "Failed to fetch job details");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch when jobId changes
  useEffect(() => {
    if (!jobId) {
      setJob(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    fetchJob(jobId);

    // Setup WebSocket connection
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.port === "5173" || window.location.port === "3000"
      ? "localhost:8000"
      : window.location.host;
    const wsUrl = `${protocol}//${host}/api/v1/ws/jobs?job_id=${encodeURIComponent(jobId)}`;

    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnectedWs(true);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.job_id === jobId || payload.data?.job_id === jobId) {
            // Re-fetch or update state directly
            if (payload.event_type === "job_progress") {
              setJob((prev) => {
                if (!prev) return prev;
                return {
                  ...prev,
                  progress: payload.data?.progress ?? prev.progress,
                  current_stage: payload.data?.stage ?? prev.current_stage,
                  processed_items: payload.data?.processed_items ?? prev.processed_items,
                  total_items: payload.data?.total_items ?? prev.total_items
                };
              });
            } else {
              // Status transition or milestone
              fetchJob(jobId);
            }
          }
        } catch (e) {
          console.debug("WS parse error:", e);
        }
      };

      ws.onerror = () => {
        setIsConnectedWs(false);
      };

      ws.onclose = () => {
        setIsConnectedWs(false);
      };
    } catch (e) {
      setIsConnectedWs(false);
    }

    // Fallback polling every 2.5s if WebSocket is inactive or while job is active
    pollTimerRef.current = setInterval(async () => {
      if (jobId) {
        const latest = await fetchJob(jobId);
        if (latest && (latest.status === "COMPLETED" || latest.status === "FAILED" || latest.status === "CANCELLED")) {
          clearInterval(pollTimerRef.current);
        }
      }
    }, 2500);

    return () => {
      if (ws) {
        ws.close();
      }
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, [jobId, fetchJob]);

  return {
    job,
    loading,
    error,
    isConnectedWs,
    refresh: () => jobId && fetchJob(jobId)
  };
};
