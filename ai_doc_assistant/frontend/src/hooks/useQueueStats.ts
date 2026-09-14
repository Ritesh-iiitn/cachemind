import { useState, useEffect, useCallback } from "react";
import { api } from "../services/api";
import type { QueueStats } from "../services/api";

export const useQueueStats = (refreshIntervalMs: number = 4000) => {
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      const data = await api.getQueueStats();
      setStats(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load queue stats");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, refreshIntervalMs);
    return () => clearInterval(interval);
  }, [fetchStats, refreshIntervalMs]);

  return { stats, loading, error, refresh: fetchStats };
};
