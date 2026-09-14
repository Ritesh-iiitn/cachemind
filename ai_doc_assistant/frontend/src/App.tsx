import React, { useState } from "react";
import { Navbar } from "./components/Navbar";
import { Dashboard } from "./pages/Dashboard";
import { KnowledgeBase } from "./pages/KnowledgeBase";
import { QueryPlayground } from "./pages/QueryPlayground";
import { CacheExplorer } from "./pages/CacheExplorer";
import { BenchmarkLab } from "./pages/BenchmarkLab";
import { InferenceLab } from "./pages/InferenceLab";
import { TaskQueue } from "./pages/TaskQueue";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>("dashboard");

  return (
    <div className="min-h-screen bg-background text-slate-100 flex flex-col font-sans">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />
      
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 animate-fadeIn">
        {activeTab === "dashboard" && <Dashboard />}
        {activeTab === "knowledge" && <KnowledgeBase />}
        {activeTab === "queue" && <TaskQueue />}
        {activeTab === "playground" && <QueryPlayground />}
        {activeTab === "cache" && <CacheExplorer />}
        {activeTab === "benchmarks" && <BenchmarkLab />}
        {activeTab === "inference" && <InferenceLab />}
      </main>


      <footer className="border-t border-surfaceBorder/80 py-4 px-6 text-center text-xs text-slate-500 bg-surface/30">
        <p>CacheMind • Adaptive Agentic RAG & LLM Inference Optimization Gateway • Open Source</p>
      </footer>
    </div>
  );
};

export default App;
