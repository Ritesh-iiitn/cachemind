import React from "react";
import { 
  Zap, Database, Compass, Layers, 
  BarChart3, Cpu, Activity, Clock
} from "lucide-react";

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: Activity },
    { id: "knowledge", label: "Knowledge Base", icon: Database },
    { id: "queue", label: "Task Queue", icon: Clock },
    { id: "playground", label: "Query Playground", icon: Compass },
    { id: "cache", label: "Cache Explorer", icon: Layers },
    { id: "benchmarks", label: "Benchmark Lab", icon: BarChart3 },
    { id: "inference", label: "Inference Lab", icon: Cpu },
  ];


  return (
    <header className="sticky top-0 z-50 bg-surface/90 backdrop-blur-md border-b border-surfaceBorder px-6 py-3.5 flex items-center justify-between">
      <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab("dashboard")}>
        <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-primary to-accent flex items-center justify-center shadow-lg shadow-primary/20">
          <Zap className="h-5 w-5 text-white animate-pulse" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              CacheMind
            </span>
            <span className="text-[10px] uppercase font-mono tracking-wider px-1.5 py-0.5 rounded bg-primary/20 text-primary-light border border-primary/30">
              v1.0 Local Engine
            </span>
          </div>
          <p className="text-xs text-slate-400 hidden sm:block">Adaptive Agentic RAG & Inference Gateway</p>
        </div>
      </div>

      <nav className="flex items-center space-x-1 sm:space-x-2 bg-background/60 p-1 rounded-xl border border-surfaceBorder/80">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? "bg-primary text-white shadow-md shadow-primary/25"
                  : "text-slate-400 hover:text-slate-200 hover:bg-surface"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              <span className="hidden md:inline">{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="flex items-center space-x-3 text-xs">
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
          <span className="font-mono font-medium">Gateway Active</span>
        </div>
      </div>
    </header>
  );
};
