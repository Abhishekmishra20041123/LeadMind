"use client";
import { useState, useEffect, useCallback } from "react";
import { useBatchProgress } from "../hooks/useBatchProgress";
import {
  Activity, MousePointerClick, FileText, Clock, RefreshCw,
  Users, UserPlus, Zap, ShoppingCart, CreditCard, Target,
  Monitor, Smartphone, Tablet, ArrowRight,
  Search, ChevronDown, ChevronUp, Globe, X, ExternalLink, Mail, Phone, Trash2
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatDuration(sec) {
  if (!sec || sec === 0) return "0s";
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60), s = sec % 60;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}
function timeAgo(iso) {
  if (!iso) return "";
  const d = Math.floor((Date.now() - new Date(iso)) / 1000);
  if (d < 60) return `${d}s ago`;
  if (d < 3600) return `${Math.floor(d / 60)}m ago`;
  if (d < 86400) return `${Math.floor(d / 3600)}h ago`;
  return `${Math.floor(d / 86400)}d ago`;
}
function DeviceIcon({ type }) {
  const t = (type || "").toLowerCase();
  if (t === "mobile") return <Smartphone className="w-3 h-3 text-orange-500" />;
  if (t === "tablet") return <Tablet className="w-3 h-3 text-purple-500" />;
  return <Monitor className="w-3 h-3 text-blue-500" />;
}
function intentBadge(v) {
  if (v.checkout_started) return { label: "GOAL", bar: "bg-red-500", left: "border-l-red-500", bg: "bg-red-500 text-paper" };
  if (v.cart_added) return { label: "ACTION", bar: "bg-orange-400", left: "border-l-orange-400", bg: "bg-orange-400 text-ink" };
  if ((v.engagement_score || 0) >= 60)
    return { label: "HOT", bar: "bg-yellow-400", left: "border-l-yellow-400", bg: "bg-yellow-400 text-ink" };
  return { label: "BROWSING", bar: "bg-blue-400", left: "border-l-transparent", bg: "bg-mute text-ink/60" };
}
function getEventLabel(evt) {
  switch (evt.event_type) {
    case "page_view": return `Viewed: ${evt.title || (evt.url || "").replace(/^https?:\/\/[^/]+/, "") || "page"}`;
    case "click": return `Clicked: ${evt.metadata?.text?.slice(0, 30) || "element"}`;
    case "scroll": return `Scrolled ${evt.metadata?.scroll_depth || 0}%`;
    case "time_spent": return `Spent ${formatDuration(evt.metadata?.duration_s)} on page`;
    case "cart_view": return "High Interest Action ⚡";
    case "checkout_started": return "Primary Goal Reached 🎯";
    case "purchase_complete": return "Completed Success 🎉";
    default: return evt.event_type;
  }
}
function getEventIcon(type) {
  switch (type) {
    case "page_view": return <FileText className="w-3 h-3 text-blue-500" />;
    case "click": return <MousePointerClick className="w-3 h-3 text-purple-500" />;
    case "scroll": return <Activity className="w-3 h-3 text-green-500" />;
    case "time_spent": return <Clock className="w-3 h-3 text-orange-500" />;
    case "cart_view": return <Zap className="w-3 h-3 text-orange-600" />;
    case "checkout_started": return <Target className="w-3 h-3 text-red-500" />;
    case "purchase_complete": return <Zap className="w-3 h-3 text-green-600" />;
    default: return <Activity className="w-3 h-3 text-ink/40" />;
  }
}

// ── Agent Monitor Modal ───────────────────────────────────────────────────────
function AgentMonitorModal({ batchId, onClose }) {
  const progress = useBatchProgress(batchId);

  if (!progress) {
    return (
      <div className="fixed inset-0 z-[100] flex items-center justify-center bg-ink/60 backdrop-blur-md p-4">
        <div className="bg-paper border-4 border-ink p-8 shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] max-w-sm w-full text-center">
          <RefreshCw className="w-12 h-12 text-primary animate-spin mx-auto mb-4" />
          <h3 className="font-display font-black text-xl mb-2">INITIALIZING PIPELINE</h3>
          <p className="font-mono text-xs text-ink/40 uppercase tracking-widest">Connecting to Neural Stream...</p>
        </div>
      </div>
    );
  }

  const isCompleted = progress.status === 'completed';
  const isFailed = progress.status === 'failed' || progress.status === 'error';
  const isProcessing = progress.status === 'processing';

  const getDisplayStatus = (id) => {
    if (isCompleted) return 'completed';
    if (isProcessing) return 'running';
    if (isFailed) return progress.agents?.[id] || 'error';
    return 'pending';
  };

  const agentList = [
    { id: 'research', name: 'Research Agent', status: getDisplayStatus('research') },
    { id: 'intent', name: 'Intent Scoring', status: getDisplayStatus('intent') },
    { id: 'timing', name: 'Timing Engine', status: getDisplayStatus('timing') },
    { id: 'logger', name: 'CRM Logger', status: getDisplayStatus('logger') },
    { id: 'outreach', name: 'Multi-Channel Drafter', status: getDisplayStatus('message') },
  ];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-ink/80 backdrop-blur-md p-4 lg:p-12">
      <div className="bg-paper border-4 border-ink shadow-[16px_16px_0px_0px_rgba(0,0,0,1)] w-full max-w-5xl flex flex-col overflow-hidden max-h-[90vh]">
        {/* Header */}
        <div className="bg-ink text-paper px-6 py-4 flex items-center justify-between border-b-4 border-ink">
          <div className="flex items-center gap-6">
            <div className="flex flex-col">
              <span className="text-[10px] font-mono font-bold text-paper/40 uppercase tracking-widest">Pipeline Monitor</span>
              <h2 className="font-display font-black text-xl tracking-tight leading-none mt-1">{batchId}</h2>
            </div>
            <div className="h-8 w-px bg-paper/20"></div>
            <div className="flex items-center gap-3">
              <div className={`px-3 py-1 border-2 border-paper/30 font-mono text-xs font-bold uppercase flex items-center gap-2 ${isCompleted ? 'text-data-green' : isFailed ? 'text-red-500' : 'text-primary'}`}>
                {isProcessing && <RefreshCw className="w-3 h-3 animate-spin" />}
                {progress.percent}% • {progress.status}
              </div>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-paper/10 transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-8 space-y-12">
          {/* Progress Visualization */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {agentList.map((agent, index) => {
              const isLast = index === agentList.length - 1;
              const isComp = agent.status === 'completed';
              const isRun = agent.status === 'running';
              const isErr = agent.status === 'error';
              const isPend = !isComp && !isRun && !isErr;

              return (
                <div key={agent.id} className="relative group">
                  <div className={`p-5 h-full flex flex-col justify-between border-2 transition-all duration-500 ${isRun ? 'border-primary bg-primary/5 shadow-[6px_6px_0px_0px_rgba(var(--primary-rgb),1)] -translate-y-1' :
                      isComp ? 'border-ink bg-ink text-paper' :
                        isErr ? 'border-red-500 bg-red-50' : 'border-ink/10 bg-mute opacity-60'
                    }`}>
                    <div className="flex justify-between items-start mb-4">
                      <span className="font-mono text-[10px] font-bold opacity-40">0{index + 1}</span>
                      {isRun ? <RefreshCw className="w-4 h-4 text-primary animate-spin" /> :
                        isComp ? <Zap className="w-4 h-4 text-data-green" /> :
                          isErr ? <X className="w-4 h-4 text-red-500" /> :
                            <Clock className="w-4 h-4 opacity-20" />}
                    </div>
                    <div>
                      <h4 className="font-display font-black text-sm mb-1 uppercase tracking-tight">{agent.name}</h4>
                      <p className="font-mono text-[9px] uppercase font-bold opacity-60">{agent.status}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Terminal Logs */}
          <div className="bg-ink text-paper border-2 border-ink p-6 font-mono text-[11px] space-y-1.5 shadow-[inner_0_0_20px_rgba(0,0,0,0.5)] max-h-60 overflow-y-auto custom-scrollbar">
            <div className="flex items-center gap-2 mb-4 border-b border-paper/10 pb-2">
              <div className={`w-2 h-2 rounded-full ${isProcessing ? 'bg-primary animate-pulse' : 'bg-data-green'}`} />
              <span className="text-primary font-bold">RAW PIPELINE TRACE</span>
            </div>
            {progress.logs && progress.logs.map((log, i) => (
              <div key={i} className="flex gap-3 opacity-80">
                <span className="text-paper/30 shrink-0">STDOUT</span>
                <span className={log.includes("ERROR") ? 'text-red-400' : log.includes("SUCCESS") ? 'text-data-green' : 'text-primary'}>
                  {log}
                </span>
              </div>
            ))}
            {isProcessing && (
              <div className="flex gap-3 animate-pulse opacity-40">
                <span className="text-paper/30 shrink-0">STDOUT</span>
                <span className="text-primary">Awaiting next sequence...</span>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="bg-mute border-t-4 border-ink p-6 flex justify-between items-center shrink-0">
          <div className="flex flex-col">
            <p className="font-mono text-[10px] font-bold text-ink/40 uppercase">System Status</p>
            <p className="font-display font-black text-sm">{isCompleted ? "NEURAL PIPELINE SUCCESSFUL" : isProcessing ? "EXECUTING AI SYNC..." : "AWAITING INTERACTION"}</p>
          </div>
          <div className="flex gap-3">
            {isCompleted && (
              <button
                onClick={() => window.location.href = "/ledger"}
                className="px-6 py-2.5 bg-data-green text-ink font-bold text-xs uppercase border-2 border-ink shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all"
              >
                Go to Ledger
              </button>

            )}
            <button
              onClick={onClose}
              className="px-6 py-2.5 bg-ink text-paper font-bold text-xs uppercase border-2 border-ink shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all"
            >
              {isCompleted ? "Dismiss" : "Minimize"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Visitor Detail Drawer ─────────────────────────────────────────────────────
function VisitorDrawer({ v, events, onClose, onPromote, promoting }) {
  if (!v) return null;
  const visitorEvents = events.filter(e => e.visitor_id === v.visitor_id);

  // Calculate time spent per page from time_spent events
  const timePerPage = {};
  visitorEvents.forEach(e => {
    if (e.event_type === "time_spent" && e.metadata?.duration_s) {
      const key = e.url || "unknown";
      timePerPage[key] = (timePerPage[key] || 0) + (e.metadata.duration_s || 0);
    }
  });

  // Unique pages from pages_viewed_list OR events
  const pagesSet = new Set([
    ...(v.pages_viewed_list || []),
    ...visitorEvents.filter(e => e.event_type === "page_view").map(e => e.url).filter(Boolean)
  ]);
  const pages = [...pagesSet];

  const intent = intentBadge(v);
  const initials = v.identified_name
    ? v.identified_name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2)
    : v.identified_email ? v.identified_email[0].toUpperCase()
      : v.visitor_id.slice(0, 2).toUpperCase();

  function Row({ label, value, mono }) {
    if (!value && value !== 0) return null;
    return (
      <div className="flex gap-3 py-1.5 border-b border-ink/5">
        <span className="text-[10px] font-mono text-ink/40 uppercase tracking-wider w-28 shrink-0 pt-0.5">{label}</span>
        <span className={`text-xs text-ink break-all ${mono ? "font-mono" : "font-medium"}`}>{value}</span>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="flex-1 bg-ink/40 backdrop-blur-sm" onClick={onClose} />
      {/* Drawer */}
      <div className="w-full max-w-md bg-paper border-l-4 border-ink shadow-[-8px_0px_0px_0px_rgba(0,0,0,1)] flex flex-col overflow-hidden">
        {/* Drawer header */}
        <div className="bg-ink text-paper px-4 py-3 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 border-2 border-paper/30 flex items-center justify-center text-sm font-black ${v.checkout_started ? "bg-red-500" : v.cart_added ? "bg-orange-400" :
                (v.engagement_score || 0) >= 60 ? "bg-yellow-400 text-ink" : "bg-mute text-ink"
              }`}>{initials}</div>
            <div>
              <p className="font-display font-black text-sm">
                {v.identified_name || v.identified_email || `Visitor ${v.visitor_id.slice(0, 12)}`}
              </p>
              <span className={`text-[9px] font-black px-1.5 py-0.5 ${intent.bg}`}>{intent.label}</span>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-paper/10 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-5">

          {/* Intelligence & Research */}
          {v.is_lead && (
            <section>
              <h3 className="text-[10px] font-mono font-bold text-ink/40 uppercase tracking-widest mb-2">Intelligence</h3>
              <div className="bg-primary/5 border-2 border-primary/20 p-4 space-y-4 shadow-[4px_4px_0px_0px_rgba(var(--primary-rgb),0.1)]">
                {/* Intent Score */}
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[10px] font-mono font-bold text-ink/40 uppercase">AI Intent Score</p>
                    <p className="text-2xl font-black text-primary">{v.intent_score || 0}%</p>
                  </div>
                  <div className="w-16 h-16 rounded-full border-4 border-primary/10 flex items-center justify-center relative">
                    <svg className="w-full h-full -rotate-90">
                      <circle
                        cx="32" cy="32" r="28"
                        fill="none" stroke="currentColor" strokeWidth="4"
                        className="text-primary/10"
                      />
                      <circle
                        cx="32" cy="32" r="28"
                        fill="none" stroke="currentColor" strokeWidth="4"
                        strokeDasharray={175}
                        strokeDashoffset={175 - (175 * (v.intent_score || 0)) / 100}
                        className="text-primary transition-all duration-1000"
                      />
                    </svg>
                    <Zap className="absolute w-5 h-5 text-primary animate-pulse" />
                  </div>
                </div>

                {/* Key Signals */}
                {v.key_signals && v.key_signals.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-[9px] font-mono font-bold text-ink/30 uppercase mb-1">Key Research Signals</p>
                    {v.key_signals.map((sig, i) => (
                      <div key={i} className="flex gap-2 p-1.5 bg-paper border border-primary/10 text-[10px] items-start">
                        <span className="mt-0.5 text-primary">●</span>
                        <span className="font-medium text-ink/80">{sig.signal || sig}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Pipeline Status */}
                <div className="flex items-center gap-2 pt-1">
                  <span className="text-[9px] font-black px-2 py-1 bg-ink text-paper uppercase">Stage: {v.pipeline_stage || "New"}</span>
                  <span className="text-[9px] font-black px-2 py-1 bg-data-green text-ink border border-ink/20 uppercase">{v.lead_status || "Active"}</span>
                </div>
              </div>
            </section>
          )}

          {/* Identity */}
          <section>
            <h3 className="text-[10px] font-mono font-bold text-ink/40 uppercase tracking-widest mb-2">Identity</h3>
            <div className="bg-mute border-2 border-ink/10 p-3 space-y-0.5">
              {/* Profile Header in Section */}
              <div className="flex items-center gap-3 mb-3 pb-3 border-b border-ink/5">
                <img
                  src={`https://ui-avatars.com/api/?name=${encodeURIComponent(v.identified_name || v.identified_email || "V")}&background=random&bold=true&color=fff&size=64`}
                  className="w-12 h-12 border-2 border-ink shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
                  alt="Avatar"
                />
                <div className="min-w-0">
                  <p className="font-display font-black text-base truncate">{v.identified_name || "Visitor"}</p>
                  <p className="text-[10px] font-mono text-ink/40 truncate">{v.identified_title || "Individual"}</p>
                </div>
              </div>

              <Row label="Name" value={v.identified_name} />
              <Row label="Email" value={v.identified_email} mono />
              <Row label="Phone" value={v.identified_phone} mono />
              <Row label="Company" value={v.identified_company} />
              <Row label="Job Title" value={v.identified_title} />
              <Row label="City" value={v.identified_city} />
              <Row label="Country" value={v.identified_country} />

              <div className="flex gap-2 mt-2 pt-2 border-t border-ink/5">
                <a
                  href={`https://www.linkedin.com/search/results/all/?keywords=${encodeURIComponent(`${v.identified_name} ${v.identified_company}`)}`}
                  target="_blank" rel="noopener noreferrer"
                  className="text-[9px] font-bold bg-[#0077b5] text-white px-2 py-1 flex items-center gap-1 hover:opacity-80 transition-opacity"
                >
                  <ExternalLink className="w-2.5 h-2.5" /> LinkedIn Search
                </a>
                <a
                  href={`https://www.google.com/search?q=${encodeURIComponent(`${v.identified_name} ${v.identified_company} email`)}`}
                  target="_blank" rel="noopener noreferrer"
                  className="text-[9px] font-bold bg-ink text-paper px-2 py-1 flex items-center gap-1 hover:opacity-80 transition-opacity"
                >
                  <Search className="w-2.5 h-2.5" /> Google Profile
                </a>
              </div>

              <div className="pt-3 space-y-0.5">
                <Row label="Visitor ID" value={v.visitor_id} mono />
                <Row label="Lead ID" value={v.lead_id} mono />
                <Row label="Source" value={v.lead_source || "Web Tracking"} />
                <Row label="Status" value={v.new_vs_returning} />
              </div>
            </div>
          </section>

          {/* Engagement Stats */}
          <section>
            <h3 className="text-[10px] font-mono font-bold text-ink/40 uppercase tracking-widest mb-2">Engagement</h3>
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: "Pages", value: v.page_views || v.total_page_views || 0 },
                { label: "Time", value: formatDuration(v.total_time_sec) },
                { label: "Scroll", value: `${v.max_scroll || v.max_scroll_depth || 0}%` },
                { label: "Sessions", value: v.sessions_count || 1 },
                { label: "Clicks", value: v.clicks || 0 },
                { label: "Score", value: `${v.engagement_score || 0}/100` },
              ].map(({ label, value }) => (
                <div key={label} className="bg-mute border-2 border-ink/10 p-2 text-center">
                  <p className="text-base font-display font-black text-ink">{value}</p>
                  <p className="text-[9px] font-mono text-ink/40 uppercase">{label}</p>
                </div>
              ))}
            </div>
            {/* Engagement bar */}
            <div className="mt-2 flex items-center gap-2">
              <div className="flex-1 h-2 bg-ink/10 border border-ink/10">
                <div className={`h-full ${intent.bar} transition-all`} style={{ width: `${v.engagement_score || 0}%` }} />
              </div>
              <span className="text-[11px] font-mono font-bold text-ink/60">{v.engagement_score || 0}/100</span>
            </div>
            {/* Flags */}
            <div className="flex gap-2 mt-2 flex-wrap">
              {v.cart_added && <span className="text-[10px] font-bold bg-orange-100 text-orange-700 border border-orange-300 px-2 py-0.5">⚡ Key Action</span>}
              {v.checkout_started && <span className="text-[10px] font-bold bg-red-100 text-red-700 border border-red-300 px-2 py-0.5">🎯 Goal Reached</span>}
              {v.purchase_made && <span className="text-[10px] font-bold bg-green-100 text-green-700 border border-green-300 px-2 py-0.5">🎉 Success Event</span>}
              {v.is_product_visitor && <span className="text-[10px] font-bold bg-blue-100 text-blue-700 border border-blue-300 px-2 py-0.5">📦 Intent Page View</span>}
            </div>
          </section>

          {/* Device & Source */}
          <section>
            <h3 className="text-[10px] font-mono font-bold text-ink/40 uppercase tracking-widest mb-2">Device & Source</h3>
            <div className="bg-mute border-2 border-ink/10 p-3 space-y-0.5">
              <Row label="Device" value={v.device_type} />
              <Row label="Browser" value={v.browser} />
              <Row label="OS" value={v.os} />
              <Row label="UTM Source" value={v.utm_source} mono />
              <Row label="UTM Medium" value={v.utm_medium} mono />
              <Row label="UTM Campaign" value={v.utm_campaign} mono />
              <Row label="Last URL" value={v.last_url} mono />
              <Row label="Page Type" value={v.last_page_type} />
              <Row label="First Seen" value={v.first_seen ? new Date(v.first_seen).toLocaleString() : null} />
              <Row label="Last Seen" value={v.last_seen ? new Date(v.last_seen).toLocaleString() : null} />
            </div>
          </section>

          {/* Pages Visited */}
          {pages.length > 0 && (
            <section>
              <h3 className="text-[10px] font-mono font-bold text-ink/40 uppercase tracking-widest mb-2">
                Pages Visited ({pages.length})
              </h3>
              <div className="border-2 border-ink/10 overflow-hidden">
                {pages.map((url, i) => (
                  <div key={i} className={`flex items-start justify-between gap-2 px-3 py-2 text-[11px] font-mono ${i % 2 === 0 ? "bg-paper" : "bg-mute/50"}`}>
                    <span className="text-ink/70 break-all flex-1 leading-relaxed">
                      {url.replace(/^https?:\/\/[^/]+/, "") || "/"}
                    </span>
                    <div className="flex items-center gap-1.5 shrink-0">
                      {timePerPage[url] && (
                        <span className="text-[9px] bg-blue-50 text-blue-600 border border-blue-200 px-1 py-0.5">
                          ⏱ {formatDuration(timePerPage[url])}
                        </span>
                      )}
                      <a href={url} target="_blank" rel="noopener noreferrer"
                        className="text-ink/30 hover:text-ink transition-colors"
                        onClick={e => e.stopPropagation()}>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Full Event Timeline */}
          {visitorEvents.length > 0 && (
            <section>
              <h3 className="text-[10px] font-mono font-bold text-ink/40 uppercase tracking-widest mb-2">
                Full Event Timeline ({visitorEvents.length})
              </h3>
              <div className="space-y-1">
                {visitorEvents.map((evt, i) => (
                  <div key={evt.id || i} className="flex items-start gap-2 p-2 bg-mute/50 border border-ink/5 hover:bg-mute transition-colors">
                    <span className="mt-0.5 shrink-0">{getEventIcon(evt.event_type)}</span>
                    <div className="flex-1 min-w-0">
                      <span className="text-[11px] font-medium text-ink">{getEventLabel(evt)}</span>
                      {evt.url && (
                        <p className="text-[9px] font-mono text-ink/30 truncate mt-0.5">
                          {evt.url.replace(/^https?:\/\/[^/]+/, "") || "/"}
                        </p>
                      )}
                      {evt.metadata && Object.keys(evt.metadata).length > 0 && (
                        <p className="text-[9px] font-mono text-ink/30 mt-0.5">
                          {Object.entries(evt.metadata).slice(0, 3).map(([k, v]) => `${k}: ${v}`).join(" · ")}
                        </p>
                      )}
                    </div>
                    <span className="text-[9px] font-mono text-ink/30 whitespace-nowrap shrink-0">
                      {timeAgo(evt.timestamp)}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Drawer footer */}
        <div className="border-t-4 border-ink p-4 bg-mute shrink-0 flex gap-2">
          {!v.is_lead ? (
            <button
              onClick={() => { onPromote(v.visitor_id); onClose(); }}
              disabled={promoting}
              className="flex-1 py-2.5 bg-ink text-paper font-bold text-sm border-2 border-ink shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-y-0.5 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <UserPlus className="w-4 h-4" /> Convert to Lead
            </button>
          ) : (
            <div className="flex-1 py-2.5 bg-data-green/20 border-2 border-data-green text-ink font-bold text-sm text-center">
              ✓ Already a Lead
            </div>
          )}
          <button onClick={onClose} className="px-4 py-2.5 border-2 border-ink font-bold text-sm hover:bg-ink/5 transition-colors">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Visitor Card ──────────────────────────────────────────────────────────────
function VisitorCard({ v, events, onPromote, onDelete, promoting, onClick }) {
  const [expanded, setExpanded] = useState(false);
  const intent = intentBadge(v);
  // Events for this visitor (from the events list)
  const visitorEvents = events.filter(e => e.visitor_id === v.visitor_id).slice(0, 8);

  // Avatar initials
  const initials = v.identified_name
    ? v.identified_name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2)
    : v.identified_email
      ? v.identified_email[0].toUpperCase()
      : v.visitor_id.slice(0, 2).toUpperCase();

  return (
    <li className={`border-l-4 ${intent.left} bg-paper hover:bg-mute/40 transition-colors`}>
      {/* Main row — click opens drawer */}
      <div className="p-3 flex items-start gap-3 cursor-pointer" onClick={onClick}>
        {/* Avatar circle */}
        <div className="shrink-0">
          <img
            src={`https://ui-avatars.com/api/?name=${encodeURIComponent(v.identified_name || v.identified_email || "V")}&background=random&bold=true&color=fff&size=64`}
            className={`w-8 h-8 border-2 border-ink shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] ${v.checkout_started ? "ring-2 ring-red-500" :
                v.cart_added ? "ring-2 ring-orange-400" :
                  (v.engagement_score || 0) >= 60 ? "ring-2 ring-yellow-400" : ""
              }`}
            alt="Avatar"
          />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Identity + badges row */}
          <div className="flex items-center gap-1.5 flex-wrap mb-1">
            {v.identified_email ? (
              <span className="font-bold text-xs text-ink border border-ink/20 bg-blue-50 px-1.5 py-0.5 truncate max-w-[160px]" title={v.identified_email}>
                ✓ {v.identified_name || v.identified_email}
              </span>
            ) : (
              <span className="font-mono text-[11px] text-ink/50 bg-mute border border-ink/10 px-1.5 py-0.5">
                Vis·{v.visitor_id.slice(0, 10)}
              </span>
            )}
            <span className={`text-[9px] font-black px-1.5 py-0.5 ${intent.bg}`}>
              {intent.label}
            </span>
            {v.is_lead && (
              <span className="text-[9px] font-black px-1.5 py-0.5 bg-data-green text-ink">LEAD ✓</span>
            )}
            {(v.sessions_count || 0) > 1 && (
              <span className="text-[9px] font-mono text-purple-700 bg-purple-100 px-1 py-0.5">
                🔁 {v.sessions_count}×
              </span>
            )}
          </div>

          {/* Engagement bar */}
          <div className="flex items-center gap-1.5 mb-1">
            <div className="flex-1 h-1 bg-ink/10 overflow-hidden">
              <div
                className={`h-full transition-all ${intent.bar}`}
                style={{ width: `${v.engagement_score || 0}%` }}
              />
            </div>
            <span className="text-[10px] font-bold font-mono text-ink/60">{v.engagement_score || 0}</span>
          </div>

          {/* Stats row */}
          <div className="flex items-center gap-3 text-[10px] font-mono text-ink/60 flex-wrap">
            <span>📄 {v.page_views || v.total_page_views || 0}p</span>
            <span>⏱ {formatDuration(v.total_time_sec)}</span>
            <span>↕ {v.max_scroll || v.max_scroll_depth || 0}%</span>
            {v.cart_added && <span className="text-orange-600 font-bold">⚡ Action</span>}
            {v.checkout_started && <span className="text-red-600 font-bold">🎯 Goal</span>}
            {v.purchase_made && <span className="text-green-600 font-bold">🎉 Bought</span>}
            <span className="flex items-center gap-0.5 text-ink/40">
              <DeviceIcon type={v.device_type} />
              {v.device_type || "Desktop"}
            </span>
            <span className="text-ink/30">{timeAgo(v.last_seen)}</span>
          </div>

          {/* UTM + last URL */}
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            {v.utm_source && (
              <span className="text-[9px] font-mono bg-green-50 text-green-700 border border-green-200 px-1.5 py-0.5">
                via {v.utm_source}{v.utm_campaign ? ` / ${v.utm_campaign}` : ""}
              </span>
            )}
            {v.last_url && (
              <p className="text-[10px] text-ink/30 truncate max-w-[200px]" title={v.last_url}>
                <ArrowRight className="w-2.5 h-2.5 inline mr-0.5" />
                {v.last_url.replace(/^https?:\/\/[^/]+/, "") || "/"}
              </p>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <div className="flex items-center gap-2">
            {!v.is_lead && (
              <button
                onClick={(e) => { e.stopPropagation(); onDelete(v.visitor_id); }}
                className="px-2 py-1 text-ink/40 hover:text-red-500 transition-colors"
                title="Delete Session"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
            {v.is_lead ? (
              <span className="text-[9px] font-bold px-2 py-1 border-2 border-data-green text-data-green">LEAD ✓</span>
            ) : (
              <button
                onClick={(e) => { e.stopPropagation(); onPromote(v.visitor_id); }}
                disabled={promoting}
                className="px-2 py-1 border-2 border-ink bg-ink text-paper text-[10px] font-bold flex items-center gap-1 hover:bg-ink/80 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:shadow-none transition-all disabled:opacity-50"
              >
                <UserPlus className="w-3 h-3" /> Convert
              </button>
            )}
          </div>
          {visitorEvents.length > 0 && (
            <button
              onClick={() => setExpanded(e => !e)}
              className="text-[10px] font-mono text-ink/40 hover:text-ink flex items-center gap-0.5 transition-colors"
            >
              {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              {visitorEvents.length} events
            </button>
          )}
        </div>
      </div>

      {/* Expanded event timeline */}
      {expanded && visitorEvents.length > 0 && (
        <div className="px-3 pb-3 ml-11 border-t border-ink/10">
          <p className="text-[9px] uppercase tracking-widest text-ink/30 font-bold mt-2 mb-1.5">Behavior Timeline</p>
          <div className="space-y-1.5">
            {visitorEvents.map((evt, i) => (
              <div key={evt.id || i} className="flex items-center gap-2 text-[10px] font-mono">
                <span className="shrink-0">{getEventIcon(evt.event_type)}</span>
                <span className="flex-1 text-ink/70 truncate">{getEventLabel(evt)}</span>
                <span className="text-ink/30 whitespace-nowrap shrink-0">{timeAgo(evt.timestamp)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </li>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function LiveVisitorFeed() {
  const [events, setEvents] = useState([]);
  const [visitors, setVisitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("visitors");
  const [promoting, setPromoting] = useState(false);
  const [selectedVisitor, setSelectedVisitor] = useState(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [monitoringBatchId, setMonitoringBatchId] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const token = localStorage.getItem("access_token");
      if (!token) return;
      // Use 720h (30 days) so older visitors aren't missed by the time filter
      const [visRes, evtRes] = await Promise.all([
        fetch(`${API}/api/api-keys/visitors?hours=720&limit=100`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API}/api/api-keys/events?limit=100`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (visRes.ok) setVisitors((await visRes.json()).visitors || []);
      if (evtRes.ok) setEvents((await evtRes.json()).events || []);
    } catch (_) { }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchData();
    const t = setInterval(fetchData, 8000);
    return () => clearInterval(t);
  }, [fetchData]);

  const promoteVisitor = async (vid) => {
    try {
      setPromoting(true);
      // Optimistic update
      setVisitors(prev => prev.map(v => v.visitor_id === vid ? { ...v, is_lead: true } : v));

      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API}/api/api-keys/visitors/promote`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ visitor_ids: [vid] }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.batch_id) {
          setMonitoringBatchId(data.batch_id);
        }
      }
      fetchData();
    } catch (_) { }
    finally { setPromoting(false); }
  };

  const promoteAll = async () => {
    const vids = visitors.filter(v => !v.is_lead).map(v => v.visitor_id);
    if (!vids.length) return;
    try {
      setPromoting(true);
      // Optimistic update
      setVisitors(prev => prev.map(v => vids.includes(v.visitor_id) ? { ...v, is_lead: true } : v));

      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API}/api/api-keys/visitors/promote`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ visitor_ids: vids }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.batch_id) {
          setMonitoringBatchId(data.batch_id);
        }
      }
      fetchData();
    } catch (_) { }
    finally { setPromoting(false); }
  };

  const deleteVisitor = async (vid) => {
    if (!confirm("Are you sure you want to delete this visitor session?")) return;
    try {
      setVisitors(prev => prev.filter(v => v.visitor_id !== vid));
      const token = localStorage.getItem("access_token");
      await fetch(`${API}/api/api-keys/visitors/${vid}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
    } catch (_) { }
  };


  const filtered = visitors.filter(v => {
    const q = search.toLowerCase();
    const matchSearch = !q ||
      v.visitor_id.toLowerCase().includes(q) ||
      (v.identified_email || "").toLowerCase().includes(q) ||
      (v.identified_name || "").toLowerCase().includes(q) ||
      (v.utm_source || "").toLowerCase().includes(q);
    const matchFilter =
      filter === "hot" ? (v.cart_added || v.checkout_started || (v.engagement_score || 0) >= 60)
        : filter === "identified" ? !!v.identified_email
          : filter === "leads" ? v.is_lead
            : true;
    return matchSearch && matchFilter;
  });

  const hotCount = visitors.filter(v => v.cart_added || v.checkout_started || (v.engagement_score || 0) >= 60).length;
  const leadCount = visitors.filter(v => v.is_lead).length;
  const notLead = visitors.filter(v => !v.is_lead).length;

  // Group events by visitor for Events tab
  const eventsByVisitor = events.reduce((acc, e) => {
    if (!acc[e.visitor_id]) acc[e.visitor_id] = [];
    acc[e.visitor_id].push(e);
    return acc;
  }, {});

  return (
    <div className="bg-paper border-4 border-ink shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] flex flex-col" style={{ minHeight: 680 }}>

      {/* Header */}
      <div className="border-b-4 border-ink bg-ink text-paper px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-data-green rounded-full animate-pulse" />
            <span className="font-display font-black text-sm uppercase tracking-tight">Live Feed</span>
          </div>
          {/* Tabs */}
          <div className="flex gap-1">
            {[
              { id: "visitors", label: `Visitors (${visitors.length})` },
              { id: "events", label: `Events (${events.length})` },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1 font-mono text-[11px] font-bold transition-colors ${activeTab === tab.id
                    ? "bg-paper text-ink"
                    : "text-paper/50 hover:text-paper"
                  }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
        {/* Actions */}
        <div className="flex items-center gap-2">
          {notLead > 0 && activeTab === "visitors" && (
            <button
              onClick={promoteAll}
              disabled={promoting}
              className="text-[10px] font-bold px-3 py-1 bg-primary text-paper border-2 border-paper/30 hover:bg-primary/80 disabled:opacity-50 transition-colors flex items-center gap-1"
            >
              <Zap className="w-3 h-3" /> Convert All ({notLead})
            </button>
          )}
          <button onClick={fetchData} className="p-1.5 hover:bg-paper/10 transition-colors">
            <RefreshCw className="w-3.5 h-3.5 text-paper/60" />
          </button>
        </div>
      </div>

      {/* Filter bar — visitors tab only */}
      {activeTab === "visitors" && (
        <div className="px-3 py-2 bg-mute border-b-2 border-ink/20 flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-ink/30" />
            <input
              type="text"
              placeholder="Search visitor, email, UTM…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-7 pr-2 py-1.5 text-[11px] font-mono bg-paper border-2 border-ink/20 focus:outline-none focus:border-ink"
            />
          </div>
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="text-[11px] font-mono border-2 border-ink/20 px-2 py-1.5 bg-paper focus:outline-none focus:border-ink"
          >
            <option value="all">All ({visitors.length})</option>
            <option value="hot">🔥 Hot ({hotCount})</option>
            <option value="identified">✅ Identified</option>
            <option value="leads">⚡ Leads ({leadCount})</option>
          </select>
        </div>
      )}

      {/* Body */}
      <div className="flex-1 overflow-y-auto">
        {loading && visitors.length === 0 ? (
          <div className="p-10 text-center text-ink/30 font-mono text-sm animate-pulse">
            Scanning tracking network…
          </div>

        ) : activeTab === "events" ? (
          /* ── Events tab: grouped by visitor ── */
          Object.keys(eventsByVisitor).length === 0 ? (
            <div className="p-10 text-center text-ink/30 font-mono text-sm">
              No events yet. Install the SDK on your site.
            </div>
          ) : (
            <ul className="divide-y-2 divide-ink/10">
              {Object.entries(eventsByVisitor).map(([vid, evts]) => {
                const sv = visitors.find(v => v.visitor_id === vid);
                return (
                  <li key={vid} className="p-3 hover:bg-mute/30 transition-colors">
                    {/* Visitor header */}
                    <div className="flex items-center gap-2 mb-2">
                      <Globe className="w-3.5 h-3.5 text-ink/40" />
                      <span className="text-[11px] font-bold text-ink font-display">
                        {sv?.identified_name || sv?.identified_email || `Visitor ${vid.slice(0, 10)}`}
                      </span>
                      <span className="text-[9px] font-mono text-ink/30 border border-ink/20 px-1">{evts.length} events</span>
                      {sv?.identified_email && (
                        <span className="text-[9px] font-bold bg-blue-100 text-blue-700 border border-blue-300 px-1">✓ ID</span>
                      )}
                    </div>
                    {/* Event list */}
                    <div className="ml-5 space-y-1.5">
                      {evts.slice(0, 6).map((evt, i) => (
                        <div key={evt.id || i} className="flex items-center gap-2 text-[10px] font-mono">
                          <span className="shrink-0">{getEventIcon(evt.event_type)}</span>
                          <span className="flex-1 text-ink/70 truncate">{getEventLabel(evt)}</span>
                          <span className="text-ink/30 whitespace-nowrap shrink-0">{timeAgo(evt.timestamp)}</span>
                        </div>
                      ))}
                      {evts.length > 6 && (
                        <p className="text-[9px] font-mono text-ink/30">+{evts.length - 6} more</p>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          )

        ) : (
          /* ── Visitors tab ── */
          filtered.length === 0 ? (
            <div className="p-10 text-center text-ink/30 font-mono text-sm">
              {search || filter !== "all"
                ? "No visitors match your filter."
                : "No visitors tracked yet."}
            </div>
          ) : (
            <ul className="divide-y-2 divide-ink/10">
              {filtered.map(v => (
                <VisitorCard
                  key={v.visitor_id}
                  v={v}
                  events={events}
                  onPromote={promoteVisitor}
                  onDelete={deleteVisitor}
                  promoting={promoting}
                  onClick={() => setSelectedVisitor(v)}
                />
              ))}
            </ul>
          )
        )}
      </div>

      {/* Visitor Detail Drawer */}
      {selectedVisitor && (
        <VisitorDrawer
          v={selectedVisitor}
          events={events}
          onClose={() => setSelectedVisitor(null)}
          onPromote={promoteVisitor}
          promoting={promoting}
        />
      )}

      {/* Footer */}
      <div className="border-t-2 border-ink/10 px-4 py-2 bg-mute flex justify-between items-center text-[10px] font-mono text-ink/40">
        <span>{visitors.length} visitors · {hotCount} hot · {leadCount} leads</span>
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-data-green rounded-full animate-pulse" />
          Live · 8s refresh
        </span>
      </div>
      {/* Agent Monitor Modal */}
      {monitoringBatchId && (
        <AgentMonitorModal
          batchId={monitoringBatchId}
          onClose={() => setMonitoringBatchId(null)}
        />
      )}
    </div>
  );
}
