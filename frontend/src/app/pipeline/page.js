"use client";
import { useState, useEffect, useRef } from "react";
import DashboardLayout from "../../components/DashboardLayout";
import { useRouter } from "next/navigation";

const API = "http://localhost:8000/api";

function getAuthHeaders() {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return token ? { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
}

function formatValue(val) {
  if (!val || val === 0) return null;
  if (val >= 1e7) return `₹${(val / 1e7).toFixed(1)}Cr`;
  if (val >= 1e5) return `₹${(val / 1e5).toFixed(1)}L`;
  if (val >= 1e3) return `₹${(val / 1e3).toFixed(1)}K`;
  return `₹${val}`;
}

// ── Kanban Card ──────────────────────────────────────────────────────────────

function KanbanCard({ lead, onDragStart, stageColor }) {
  const score = lead.intent_score || 0;
  const scoreColor = score >= 80 ? "#f93706" : score >= 60 ? "#F59E0B" : "#10B981";
  const val = formatValue(lead.deal_value);

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, lead.lead_id)}
      className="bg-paper border border-ink p-4 cursor-grab active:cursor-grabbing
                 hover:shadow-[4px_4px_0px_0px_rgba(10,10,10,1)] hover:-translate-y-0.5
                 transition-all select-none group"
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex-1 min-w-0">
          <p className="font-display font-bold text-sm leading-tight truncate">{lead.name}</p>
          <p className="font-mono text-[10px] text-ink/50 uppercase truncate">{lead.company}</p>
        </div>
        {/* Intent score badge */}
        <div
          className="shrink-0 w-9 h-9 flex items-center justify-center font-display font-bold text-sm border-2 text-white"
          style={{ backgroundColor: scoreColor, borderColor: scoreColor }}
        >
          {score}
        </div>
      </div>

      {/* Meta row */}
      <div className="flex items-center gap-2 flex-wrap mb-3">
        {val && (
          <span className="font-mono text-[10px] bg-mute border border-ink px-1.5 py-0.5 uppercase">
            {val}
          </span>
        )}
        {lead.days_in_stage > 0 && (
          <span className="font-mono text-[10px] text-ink/40 uppercase">
            {lead.days_in_stage}d in stage
          </span>
        )}
        {lead.source === "sdk" && (
          <span className="font-mono text-[10px] bg-blue-50 border border-blue-300 text-blue-600 px-1.5 py-0.5 uppercase">
            SDK
          </span>
        )}
        {lead.email_sent && (
          <span className="font-mono text-[10px] text-ink/40 flex items-center gap-1">
            <span className="material-symbols-outlined text-[10px]">mark_email_read</span>
            Sent
          </span>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-dashed border-ink/20">
        <p className="font-mono text-[10px] text-ink/40 uppercase truncate max-w-[120px]">{lead.title || "—"}</p>
        <a
          href={`/intel/${lead.lead_id}`}
          onClick={(e) => e.stopPropagation()}
          className="font-mono text-[10px] uppercase border border-ink px-2 py-0.5
                     hover:bg-ink hover:text-paper transition-colors opacity-0 group-hover:opacity-100"
        >
          View →
        </a>
      </div>
    </div>
  );
}

// ── Kanban Column ────────────────────────────────────────────────────────────

function KanbanColumn({ col, onDragStart, onDragOver, onDrop, isDragOver }) {
  const val = formatValue(col.value);
  return (
    <div
      className={`flex flex-col min-w-[260px] max-w-[280px] shrink-0 transition-all h-full
                  ${isDragOver ? "ring-2 ring-primary ring-offset-2" : ""}`}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      {/* Column header */}
      <div
        className="px-4 py-3 border border-ink mb-0 flex items-center justify-between"
        style={{ backgroundColor: col.color, borderBottomColor: col.color }}
      >
        <div>
          <p className="font-display font-bold text-sm uppercase text-white tracking-wide leading-none">
            {col.stage}
          </p>
          {val && (
            <p className="font-mono text-[10px] text-white/70 mt-0.5">{val}</p>
          )}
        </div>
        <div className="w-7 h-7 bg-white/20 flex items-center justify-center font-display font-bold text-sm text-white">
          {col.count}
        </div>
      </div>

      {/* Cards area */}
      <div
        className={`flex-1 border border-t-0 border-ink bg-mute/40 p-2 flex flex-col gap-2
                    min-h-[200px] overflow-y-auto transition-colors
                    ${isDragOver ? "bg-primary/5" : ""}`}
      >
        {col.leads.length === 0 && (
          <div className="flex-1 flex items-center justify-center">
            <p className="font-mono text-[10px] uppercase text-ink/30">Empty</p>
          </div>
        )}
        {col.leads.map((lead, index) => (
          <KanbanCard
            key={`${lead.lead_id}-${index}`}
            lead={lead}
            stageColor={col.color}
            onDragStart={onDragStart}
          />
        ))}
      </div>
    </div>
  );
}

// ── Forecast Bar ─────────────────────────────────────────────────────────────

function ForecastBar({ forecast }) {
  if (!forecast || !forecast.forecast?.length) return null;
  const { total_raw, total_weighted, forecast: rows } = forecast;

  return (
    <div className="bg-paper border border-ink p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="font-display font-bold uppercase tracking-tight">Revenue Forecast</h3>
        <div className="flex gap-6">
          <div className="text-right">
            <p className="font-mono text-[10px] text-ink/50 uppercase">Pipeline Value</p>
            <p className="font-display font-bold text-xl">{formatValue(total_raw) || "₹0"}</p>
          </div>
          <div className="text-right">
            <p className="font-mono text-[10px] text-primary uppercase">Weighted Forecast</p>
            <p className="font-display font-bold text-xl text-primary">{formatValue(total_weighted) || "₹0"}</p>
          </div>
        </div>
      </div>

      {/* Stage breakdown bar */}
      <div className="space-y-1.5">
        {rows.filter(r => r.raw_value > 0 && r.stage !== "Lost").map((row) => {
          const pct = total_raw > 0 ? (row.raw_value / total_raw) * 100 : 0;
          const pctFormatted = Math.round(row.probability * 100);
          return (
            <div key={row.stage} className="flex items-center gap-3">
              <p className="font-mono text-[10px] uppercase w-28 shrink-0 text-ink/60">{row.stage}</p>
              <div className="flex-1 h-2 bg-mute border border-ink/20 overflow-hidden">
                <div
                  className="h-full bg-ink transition-all"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <p className="font-mono text-[10px] text-ink/50 w-16 text-right shrink-0">
                {formatValue(row.weighted_value) || "₹0"} ({pctFormatted}%)
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function PipelinePage() {
  const router = useRouter();
  const [board, setBoard]       = useState([]);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading]   = useState(true);
  const [toast, setToast]       = useState(null);
  const [dragOverStage, setDragOverStage] = useState(null);
  const dragLeadId = useRef(null);

  // Fetch board + forecast
  const loadData = async () => {
    setLoading(true);
    try {
      const [boardRes, forecastRes] = await Promise.all([
        fetch(`${API}/pipeline/board`, { headers: getAuthHeaders() }),
        fetch(`${API}/pipeline/forecast`, { headers: getAuthHeaders() }),
      ]);
      if (boardRes.status === 401) { router.push("/login"); return; }
      const boardData    = await boardRes.json();
      const forecastData = await forecastRes.json();
      setBoard(boardData.columns || []);
      setForecast(forecastData);
    } catch (e) {
      showToast("Failed to load pipeline data", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const showToast = (msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  // Drag handlers
  const handleDragStart = (e, leadId) => {
    dragLeadId.current = leadId;
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e, stage) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDragOverStage(stage);
  };

  const handleDrop = async (e, targetStage) => {
    e.preventDefault();
    setDragOverStage(null);
    const leadId = dragLeadId.current;
    if (!leadId) return;

    // Optimistic UI: move card immediately
    setBoard(prev => {
      const lead = prev.flatMap(c => c.leads).find(l => l.lead_id === leadId);
      if (!lead || Object.is(lead.pipeline_stage, targetStage)) return prev;

      return prev.map(col => {
        if (col.stage === lead.pipeline_stage) {
          return { ...col, leads: col.leads.filter(l => l.lead_id !== leadId), count: col.count - 1 };
        }
        if (col.stage === targetStage) {
          return { ...col, leads: [...col.leads, { ...lead, pipeline_stage: targetStage }], count: col.count + 1 };
        }
        return col;
      });
    });

    // Persist to backend
    try {
      const res = await fetch(`${API}/pipeline/move`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ lead_id: leadId, new_stage: targetStage }),
      });
      if (!res.ok) throw new Error("Move failed");
      showToast(`Moved to "${targetStage}"`);
      // Reload forecast silently
      fetch(`${API}/pipeline/forecast`, { headers: getAuthHeaders() })
        .then(r => r.json()).then(setForecast);
    } catch {
      showToast("Failed to move lead — try again", "error");
      loadData(); // revert
    }
    dragLeadId.current = null;
  };

  const handleDragLeave = () => setDragOverStage(null);

  const totalLeads = board.reduce((s, c) => s + c.count, 0);

  return (
    <DashboardLayout>
      {/* Page header */}
      <div className="bg-paper border-b border-ink px-8 py-6 flex flex-col sm:flex-row justify-between sm:items-end gap-4 shrink-0">
        <div>
          <h2 className="font-display text-4xl font-bold uppercase tracking-tighter leading-none mb-1">
            Pipeline
          </h2>
          <p className="font-mono text-xs text-ink/50 uppercase">
            {totalLeads} leads across {board.length} stages
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={loadData}
            className="h-10 px-5 border border-ink bg-paper hover:bg-mute font-mono text-xs uppercase
                       flex items-center gap-2 transition-colors"
          >
            <span className="material-symbols-outlined text-[16px]">refresh</span>
            Refresh
          </button>
          <button
            onClick={() => router.push("/ledger")}
            className="h-10 px-5 bg-ink text-paper hover:bg-primary font-mono text-xs uppercase
                       flex items-center gap-2 transition-colors"
          >
            <span className="material-symbols-outlined text-[16px]">table_chart</span>
            All Leads
          </button>
        </div>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="flex flex-col items-center gap-4">
              <span className="material-symbols-outlined text-[48px] text-ink/20 animate-spin">refresh</span>
              <p className="font-mono text-xs uppercase text-ink/40">Loading Pipeline...</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col flex-1 overflow-hidden gap-0">
            {/* Forecast bar */}
            <div className="px-8 pt-6 pb-4 shrink-0">
              <ForecastBar forecast={forecast} />
            </div>

            {/* Kanban board — horizontal scroll */}
            <div className="flex-1 overflow-x-auto overflow-y-hidden px-8 pb-6">
              <div className="flex gap-4 h-full items-stretch min-h-[400px]" onDragLeave={handleDragLeave}>
                {board.map((col) => (
                  <KanbanColumn
                    key={col.stage}
                    col={col}
                    isDragOver={dragOverStage === col.stage}
                    onDragStart={handleDragStart}
                    onDragOver={(e) => handleDragOver(e, col.stage)}
                    onDrop={(e) => handleDrop(e, col.stage)}
                  />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Toast notification */}
      {toast && (
        <div
          className={`fixed top-6 right-6 z-50 px-5 py-3 border-2 border-ink font-mono text-xs uppercase
                      flex flex-col gap-2 shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]
                      transition-all animate-in slide-in-from-top-2
                      ${toast.type === "error"
                        ? "bg-red-50 border-red-500 text-red-700"
                        : "bg-[#f93706] text-black"}`}
        >
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[16px]">
              {toast.type === "error" ? "error" : "check_circle"}
            </span>
            <span className="font-bold">{toast.msg}</span>
          </div>
          <div className="h-1 bg-black/20 w-full overflow-hidden">
            <div className="h-full bg-black animate-progress-shrink" />
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
