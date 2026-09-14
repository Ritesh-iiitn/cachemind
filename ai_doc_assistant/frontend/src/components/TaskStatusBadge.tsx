import React from "react";
import { Clock, Loader2, RefreshCw, CheckCircle2, XCircle, Ban } from "lucide-react";
import type { JobStatus } from "../services/api";

interface TaskStatusBadgeProps {
  status: JobStatus;
  size?: "sm" | "md";
}

export const TaskStatusBadge: React.FC<TaskStatusBadgeProps> = ({ status, size = "md" }) => {
  const isSm = size === "sm";
  const paddingClass = isSm ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs";
  const iconSize = isSm ? "h-3 w-3" : "h-3.5 w-3.5";

  switch (status) {
    case "QUEUED":
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-slate-800/80 text-slate-300 border border-slate-700 ${paddingClass}`}
        >
          <Clock className={`${iconSize} text-slate-400`} />
          <span>Queued</span>
        </span>
      );

    case "PROCESSING":
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-sky-500/10 text-sky-400 border border-sky-500/30 shadow-sm shadow-sky-500/10 ${paddingClass}`}
        >
          <Loader2 className={`${iconSize} text-sky-400 animate-spin`} />
          <span className="animate-pulse">Processing</span>
        </span>
      );

    case "RETRYING":
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30 ${paddingClass}`}
        >
          <RefreshCw className={`${iconSize} text-amber-400 animate-spin`} />
          <span>Retrying</span>
        </span>
      );

    case "COMPLETED":
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 ${paddingClass}`}
        >
          <CheckCircle2 className={`${iconSize} text-emerald-400`} />
          <span>Completed</span>
        </span>
      );

    case "FAILED":
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-rose-500/10 text-rose-400 border border-rose-500/30 ${paddingClass}`}
        >
          <XCircle className={`${iconSize} text-rose-400`} />
          <span>Failed</span>
        </span>
      );

    case "CANCELLED":
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full font-medium bg-slate-800/50 text-slate-500 border border-slate-700/50 ${paddingClass}`}
        >
          <Ban className={`${iconSize} text-slate-500`} />
          <span>Cancelled</span>
        </span>
      );

    default:
      return (
        <span className={`inline-flex items-center rounded-full font-medium bg-slate-800 text-slate-400 ${paddingClass}`}>
          {status}
        </span>
      );
  }
};
