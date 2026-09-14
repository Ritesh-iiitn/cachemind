import React from "react";
import type { JobStatus } from "../services/api";

interface TaskProgressBarProps {
  progress: number;
  stage?: string;
  status: JobStatus;
  showLabel?: boolean;
}

const formatStageLabel = (stage?: string): string => {
  if (!stage) return "Pending";
  return stage
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
};

export const TaskProgressBar: React.FC<TaskProgressBarProps> = ({
  progress,
  stage,
  status,
  showLabel = true
}) => {
  const clamped = Math.max(0, Math.min(100, progress));

  let barColor = "bg-primary";
  if (status === "FAILED") barColor = "bg-rose-500";
  else if (status === "CANCELLED") barColor = "bg-slate-600";
  else if (status === "RETRYING") barColor = "bg-amber-500";
  else if (status === "COMPLETED") barColor = "bg-emerald-500";
  else if (status === "PROCESSING") barColor = "bg-gradient-to-r from-sky-500 to-primary";

  return (
    <div className="w-full space-y-1.5">
      {showLabel && (
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span className="font-medium text-slate-300 truncate max-w-[180px]">
            {formatStageLabel(stage)}
          </span>
          <span className="font-mono text-slate-400 font-semibold">{clamped}%</span>
        </div>
      )}
      <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden border border-slate-700/50">
        <div
          className={`h-full transition-all duration-500 ease-out rounded-full ${barColor}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
};
