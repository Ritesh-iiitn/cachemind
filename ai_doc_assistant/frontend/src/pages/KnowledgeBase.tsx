import React, { useState, useEffect } from "react";
import { 
  Database, Upload, Plus, Trash2, FileText, 
  CheckCircle2, AlertCircle, RefreshCw, Eye, Ban
} from "lucide-react";
import { api } from "../services/api";
import type { KnowledgeBase as KBType, DocumentItem } from "../services/api";
import { useJobStatus } from "../hooks/useJobStatus";
import { TaskStatusBadge } from "../components/TaskStatusBadge";
import { TaskProgressBar } from "../components/TaskProgressBar";
import { TaskDetailsDrawer } from "../components/TaskDetailsDrawer";


export const KnowledgeBase: React.FC = () => {
  const [kbs, setKbs] = useState<KBType[]>([]);
  const [selectedKb, setSelectedKb] = useState<KBType | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [newKbName, setNewKbName] = useState("");
  const [newKbDesc, setNewKbDesc] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeJobFilename, setActiveJobFilename] = useState<string>("");
  const [drawerOpen, setDrawerOpen] = useState(false);

  const { job: activeJob, refresh: refreshActiveJob } = useJobStatus(activeJobId);

  const fetchKbs = async () => {
    try {
      setLoading(true);
      const data = await api.listKnowledgeBases();
      setKbs(data);
      if (data.length > 0 && !selectedKb) {
        setSelectedKb(data[0]);
      }
    } catch (e) {
      console.error("Failed to fetch KBs:", e);
    } finally {
      setLoading(false);
    }
  };

  const fetchDocuments = async (kbId: string) => {
    try {
      const docs = await api.listDocuments(kbId);
      setDocuments(docs);
    } catch (e) {
      console.error("Failed to fetch docs:", e);
    }
  };

  useEffect(() => {
    fetchKbs();
  }, []);

  useEffect(() => {
    if (selectedKb) {
      fetchDocuments(selectedKb.id);
    }
  }, [selectedKb]);

  // When active job completes or changes, refresh documents & KB
  useEffect(() => {
    if (activeJob && selectedKb) {
      if (activeJob.status === "COMPLETED") {
        fetchDocuments(selectedKb.id);
        fetchKbs();
      }
    }
  }, [activeJob?.status]);

  const handleCreateKb = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKbName.trim()) return;
    try {
      const created = await api.createKnowledgeBase(newKbName, newKbDesc);
      setNewKbName("");
      setNewKbDesc("");
      await fetchKbs();
      setSelectedKb(created);
      setMessage(`Knowledge Base "${created.name}" created successfully.`);
    } catch (err) {
      console.error(err);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!selectedKb || !e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    try {
      setUploading(true);
      setActiveJobFilename(file.name);
      setMessage(`Enqueuing "${file.name}" into ${selectedKb.name}...`);
      const res = await api.uploadDocumentAsync(selectedKb.id, file);
      setActiveJobId(res.job_id);
      setMessage(`"${file.name}" accepted for background processing (Job ID: ${res.job_id}).`);
      await fetchDocuments(selectedKb.id);
    } catch (err: any) {
      setMessage(`Upload failed: ${err.message || "Unknown error"}`);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };


  const handleDeleteKb = async (kbId: string, kbName: string) => {
    if (!window.confirm(`Delete Knowledge Base "${kbName}"? This will permanently delete all indexed documents, vector indices, and purge associated cache entries.`)) return;
    try {
      await api.deleteKnowledgeBase(kbId);
      setMessage(`Knowledge Base "${kbName}" deleted successfully.`);
      const remainingKbs = await api.listKnowledgeBases();
      setKbs(remainingKbs);
      if (selectedKb?.id === kbId) {
        if (remainingKbs.length > 0) {
          setSelectedKb(remainingKbs[0]);
        } else {
          setSelectedKb(null);
          setDocuments([]);
        }
      }
    } catch (err: any) {
      console.error(err);
      setMessage(`Failed to delete Knowledge Base: ${err.message || "Unknown error"}`);
    }
  };

  const handleDeleteDoc = async (docId: string, filename: string) => {
    if (!selectedKb) return;
    if (!window.confirm(`Delete "${filename}"? This will bump the KB version and invalidate cached entries.`)) return;
    try {
      await api.deleteDocument(selectedKb.id, docId);
      await fetchDocuments(selectedKb.id);
      await fetchKbs();
      setMessage(`Deleted "${filename}". Multi-tier cache entries purged.`);
    } catch (err) {
      console.error(err);
    }
  };


  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Knowledge Base & Document Indexing
          </h1>
          <p className="text-sm text-slate-400">
            Upload PDF, Markdown, and TXT corpora. Every document mutation automatically updates the index version and purges stale caches.
          </p>
        </div>
      </div>

      {message && (
        <div className="p-3 rounded-xl bg-primary/10 border border-primary/20 text-xs text-primary-light flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-primary" />
            <span>{message}</span>
          </div>
          <button onClick={() => setMessage(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Main Grid: KB List + Active KB Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Knowledge Bases */}
        <div className="p-5 rounded-2xl bg-surface border border-surfaceBorder space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Database className="h-4 w-4 text-primary" />
              <span>Knowledge Bases</span>
            </h3>
            <span className="text-xs font-mono text-slate-400">{kbs.length} Total</span>
          </div>

          {/* Create KB Form */}
          <form onSubmit={handleCreateKb} className="space-y-3 pt-2 border-t border-surfaceBorder">
            <div>
              <label className="text-xs text-slate-400">New Knowledge Base Name</label>
              <input
                type="text"
                value={newKbName}
                onChange={(e) => setNewKbName(e.target.value)}
                placeholder="e.g. Distributed Systems Spec"
                className="w-full mt-1 px-3 py-1.5 rounded-lg bg-background border border-surfaceBorder text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Description (Optional)</label>
              <input
                type="text"
                value={newKbDesc}
                onChange={(e) => setNewKbDesc(e.target.value)}
                placeholder="Brief summary of domain corpus"
                className="w-full mt-1 px-3 py-1.5 rounded-lg bg-background border border-surfaceBorder text-xs text-white placeholder-slate-500 focus:outline-none focus:border-primary"
              />
            </div>
            <button
              type="submit"
              className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg bg-primary hover:bg-primary-hover text-white text-xs font-medium transition-all shadow-md shadow-primary/20"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Create Knowledge Base</span>
            </button>
          </form>

          {/* KB Selection List */}
          <div className="space-y-2 pt-2 border-t border-surfaceBorder max-h-72 overflow-y-auto">
            {kbs.map((kb) => {
              const isSelected = selectedKb?.id === kb.id;
              return (
                <div
                  key={kb.id}
                  onClick={() => setSelectedKb(kb)}
                  className={`p-3 rounded-xl border cursor-pointer transition-all ${
                    isSelected
                      ? "bg-primary/10 border-primary/40 text-white"
                      : "bg-background/40 border-surfaceBorder hover:border-slate-600 text-slate-300"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium truncate">{kb.name}</span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-primary-light border border-slate-700">
                        v{kb.version}
                      </span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteKb(kb.id, kb.name);
                        }}
                        className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-slate-800 transition-colors"
                        title={`Delete "${kb.name}"`}
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
                    <span>{kb.document_count ?? 0} docs • {kb.chunk_count ?? 0} chunks</span>
                    <span className="font-mono text-[10px]">{kb.id.slice(0, 8)}</span>
                  </div>
                </div>
              );
            })}
            {kbs.length === 0 && !loading && (
              <p className="text-xs text-center text-slate-500 py-4">No knowledge bases yet. Create one above!</p>
            )}
          </div>
        </div>

        {/* Right Column: Selected KB Document Details */}
        <div className="lg:col-span-2 p-5 rounded-2xl bg-surface border border-surfaceBorder space-y-5">
          {selectedKb ? (
            <>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-surfaceBorder">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-white">{selectedKb.name}</h2>
                    <span className="px-2 py-0.5 rounded-full text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Version v{selectedKb.version}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    {selectedKb.description || "No description provided."} • ID: <span className="font-mono">{selectedKb.id}</span>
                  </p>
                </div>

                {/* Actions: Delete KB and Upload Document */}
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleDeleteKb(selectedKb.id, selectedKb.name)}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800/90 hover:bg-rose-950/50 text-slate-400 hover:text-rose-300 border border-slate-700 hover:border-rose-500/40 text-xs font-medium transition-all"
                    title="Delete this Knowledge Base and all its documents"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    <span className="hidden sm:inline">Delete KB</span>
                  </button>

                  <label className="flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-primary hover:bg-primary-hover text-white text-xs font-medium cursor-pointer transition-all shadow-md shadow-primary/20">
                    <Upload className="h-4 w-4" />
                    <span>{uploading ? "Enqueueing..." : "Upload & Index Document"}</span>
                    <input
                      type="file"
                      accept=".pdf,.txt,.md,.markdown,.docx"
                      onChange={handleFileUpload}
                      disabled={uploading}
                      className="hidden"
                    />
                  </label>
                </div>
              </div>

              {/* Active Background Ingestion Task Card */}
              {activeJob && (
                <div className="p-4 rounded-2xl bg-surface/90 border border-primary/30 shadow-lg space-y-3 animate-fadeIn">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-primary" />
                      <span className="text-xs font-semibold text-white truncate max-w-xs">
                        {activeJob.document_name || activeJobFilename || activeJob.job_id}
                      </span>
                      <TaskStatusBadge status={activeJob.status} size="sm" />
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setDrawerOpen(true)}
                        className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface border border-surfaceBorder hover:bg-slate-800 text-[11px] font-medium text-slate-300 hover:text-white transition-all"
                      >
                        <Eye className="h-3 w-3" />
                        <span>View Task</span>
                      </button>
                      {activeJob.status === "FAILED" && (
                        <button
                          onClick={async () => {
                            await api.retryJob(activeJob.job_id);
                            refreshActiveJob();
                          }}
                          className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-primary hover:bg-primary-hover text-white text-[11px] font-medium transition-all"
                        >
                          <RefreshCw className="h-3 w-3" />
                          <span>Retry Job</span>
                        </button>
                      )}
                      {(activeJob.status === "QUEUED" || activeJob.status === "PROCESSING") && (
                        <button
                          onClick={async () => {
                            await api.cancelJob(activeJob.job_id);
                            refreshActiveJob();
                          }}
                          className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-rose-950/40 text-slate-400 hover:text-rose-400 border border-slate-700 text-[11px] font-medium transition-all"
                        >
                          <Ban className="h-3 w-3" />
                          <span>Cancel</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Status Detail Content */}
                  {activeJob.status === "PROCESSING" || activeJob.status === "QUEUED" || activeJob.status === "RETRYING" ? (
                    <div className="space-y-2 pt-1">
                      <TaskProgressBar
                        progress={activeJob.progress}
                        stage={activeJob.current_stage}
                        status={activeJob.status}
                        showLabel={true}
                      />
                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span>Job ID: <span className="font-mono text-slate-300">{activeJob.job_id}</span></span>
                        {activeJob.queue_position ? (
                          <span>Queue Position: <strong className="text-amber-400">#{activeJob.queue_position}</strong></span>
                        ) : null}
                      </div>
                    </div>
                  ) : activeJob.status === "COMPLETED" ? (
                    <div className="flex flex-wrap items-center justify-between text-xs text-emerald-400 bg-emerald-500/10 p-2.5 rounded-xl border border-emerald-500/20">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                        <span className="font-medium">Indexed successfully</span>
                      </div>
                      <div className="flex items-center gap-3 font-mono text-[11px] text-slate-300">
                        <span>Chunks: <strong className="text-white">{activeJob.total_items || activeJob.metadata?.total_chunks || "—"}</strong></span>
                        <span>Time: <strong className="text-sky-400">{activeJob.processing_time_ms ? `${(activeJob.processing_time_ms/1000).toFixed(1)}s` : "—"}</strong></span>
                        <span>KB Version: <strong className="text-emerald-400">v{activeJob.metadata?.kb_version || selectedKb.version}</strong></span>
                      </div>
                    </div>
                  ) : activeJob.status === "FAILED" ? (
                    <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 space-y-1">
                      <div className="flex items-center gap-1.5 font-semibold text-rose-400">
                        <AlertCircle className="h-4 w-4" />
                        <span>Processing failed: {activeJob.error_code || "ERROR"}</span>
                      </div>
                      <p className="text-[11px] font-mono text-rose-200 truncate">{activeJob.error_message}</p>
                    </div>
                  ) : null}
                </div>
              )}

              {/* Document List Table */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Indexed Documents ({documents.length})
                  </h3>
                  <span className="text-xs text-slate-500">FAISS + BM25 Multi-Index</span>
                </div>


                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-surfaceBorder text-slate-400">
                        <th className="pb-2 font-medium">Filename</th>
                        <th className="pb-2 font-medium">Format</th>
                        <th className="pb-2 font-medium">Size</th>
                        <th className="pb-2 font-medium">Chunks</th>
                        <th className="pb-2 font-medium">Version</th>
                        <th className="pb-2 font-medium">Status</th>
                        <th className="pb-2 font-medium text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surfaceBorder/40">
                      {documents.map((doc) => (
                        <tr key={doc.id} className="hover:bg-slate-800/30 transition-colors">
                          <td className="py-3 font-medium text-white flex items-center gap-2">
                            <FileText className="h-3.5 w-3.5 text-primary-light" />
                            <span className="truncate max-w-xs">{doc.filename}</span>
                          </td>
                          <td className="py-3 uppercase font-mono text-[10px] text-slate-400">{doc.file_type}</td>
                          <td className="py-3 font-mono text-slate-400">{(doc.file_size / 1024).toFixed(1)} KB</td>
                          <td className="py-3 font-mono text-emerald-400">{doc.chunk_count}</td>
                          <td className="py-3 font-mono text-slate-300">v{doc.version}</td>
                          <td className="py-3">
                            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              {doc.status}
                            </span>
                          </td>
                          <td className="py-3 text-right">
                            <button
                              onClick={() => handleDeleteDoc(doc.id, doc.filename)}
                              className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                              title="Delete document"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                      {documents.length === 0 && (
                        <tr>
                          <td colSpan={7} className="py-10 text-center text-slate-500">
                            No documents uploaded yet. Click "Upload & Index Document" above (supports PDF, TXT, Markdown).
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="py-16 px-6 flex flex-col items-center justify-center text-center space-y-4">
              <div className="p-4 rounded-2xl bg-primary/10 border border-primary/20 text-primary-light">
                <FileText className="h-8 w-8" />
              </div>
              <div className="max-w-md space-y-1.5">
                <h3 className="text-base font-semibold text-white">Create a Knowledge Base to Start Uploading</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Documents (PDF, TXT, Markdown, DOCX) must belong to a Knowledge Base so that multi-tier cache keys and FAISS vector indices are versioned and partitioned.
                </p>
              </div>
              <div className="pt-2">
                <button
                  onClick={async () => {
                    try {
                      const created = await api.createKnowledgeBase("My Documents", "Primary knowledge base for document Q&A and semantic search");
                      await fetchKbs();
                      setSelectedKb(created);
                      setMessage(`Knowledge Base "${created.name}" created! You can now upload PDF/text documents.`);
                    } catch (err) {
                      console.error("Failed to auto-create KB:", err);
                    }
                  }}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white text-xs font-semibold shadow-lg shadow-primary/25 transition-all"
                >
                  <Plus className="h-4 w-4" />
                  <span>Create Default Knowledge Base & Unlock Upload</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Task Details Drawer */}
      <TaskDetailsDrawer
        job={activeJob}
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onJobUpdated={() => {
          refreshActiveJob();
          if (selectedKb) {
            fetchDocuments(selectedKb.id);
            fetchKbs();
          }
        }}
      />
    </div>
  );
};
