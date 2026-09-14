import React from "react";
import { Clock, Loader2, CheckCircle2, XCircle, Cpu, Timer } from "lucide-react";
import type { QueueStats } from "../services/api";


interface QueueStatsCardsProps {
  stats: QueueStats | null;
  loading?: boolean;
}

export const QueueStatsCards: React.FC<QueueStatsCardsProps> = ({ stats, loading }) => {
  const cards = [
    {
      title: "Queued Tasks",
      value: stats?.queued ?? 0,
      icon: Clock,
      color: "text-slate-300",
      bgColor: "bg-slate-800/60",
      borderColor: "border-slate-700/60",
      detail: `${stats?.queue_depth ?? 0} total in backlog`
    },
    {
      title: "Processing",
      value: stats?.processing ?? 0,
      icon: Loader2,
      color: "text-sky-400",
      bgColor: "bg-sky-500/10",
      borderColor: "border-sky-500/25",
      isSpinning: true,
      detail: `${stats?.worker_utilization_pct ?? 0}% worker load`
    },
    {
      title: "Completed Today",
      value: stats?.completed_today ?? 0,
      icon: CheckCircle2,
      color: "text-emerald-400",
      bgColor: "bg-emerald-500/10",
      borderColor: "border-emerald-500/25",
      detail: `${stats?.success_rate_pct ?? 100}% success rate`
    },
    {
      title: "Failed Tasks",
      value: stats?.failed_today ?? 0,
      icon: XCircle,
      color: "text-rose-400",
      bgColor: "bg-rose-500/10",
      borderColor: "border-rose-500/25",
      detail: `${stats?.retry_rate_pct ?? 0}% retry rate`
    },
    {
      title: "Active Workers",
      value: stats?.active_workers ?? 1,
      icon: Cpu,
      color: "text-purple-400",
      bgColor: "bg-purple-500/10",
      borderColor: "border-purple-500/25",
      detail: "Cluster nodes active"
    },
    {
      title: "Avg Wait Time",
      value: `${Math.round(stats?.average_wait_time_ms ?? 0)} ms`,
      icon: Timer,
      color: "text-amber-400",
      bgColor: "bg-amber-500/10",
      borderColor: "border-amber-500/25",
      detail: `Avg Proc: ${((stats?.average_processing_time_ms ?? 0) / 1000).toFixed(1)}s`
    }
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className={`p-4 rounded-xl border ${card.borderColor} ${card.bgColor} backdrop-blur-sm transition-all hover:translate-y-[-2px] hover:shadow-lg`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">{card.title}</span>
              <Icon className={`h-4 w-4 ${card.color} ${card.isSpinning && (stats?.processing ?? 0) > 0 ? "animate-spin" : ""}`} />
            </div>
            <div className="mt-2.5 flex items-baseline justify-between">
              <span className="text-2xl font-bold tracking-tight text-white font-mono">
                {loading ? "..." : card.value}
              </span>
            </div>
            <p className="mt-1 text-[11px] text-slate-500 truncate">{card.detail}</p>
          </div>
        );
      })}
    </div>
  );
};
