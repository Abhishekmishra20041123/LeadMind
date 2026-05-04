"use client";
import { useState, useEffect } from "react";
import DashboardLayout from "../../components/DashboardLayout";
import EmbedSnippet from "../../components/EmbedSnippet";
import LiveVisitorFeed from "../../components/LiveVisitorFeed";
import {
  Plus, X, Key, Calendar, Trash2,
  Users, Activity, TrendingUp, ShoppingCart,
  Target, Zap, Copy, Check, Globe, ChevronDown, ChevronUp
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Stat Card ──────────────────────────────────────────────────────────────
function StatCard({ icon: Icon, label, value, sub, accent = "bg-ink" }) {
  return (
    <div className="bg-paper border-4 border-ink shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] p-4 flex items-start gap-3 hover:shadow-[6px_6px_0px_0px_rgba(0,0,0,1)] hover:-translate-y-0.5 transition-all">
      <div className={`p-2 border-2 border-ink ${accent}`}>
        <Icon className="w-5 h-5 text-paper" />
      </div>
      <div>
        <p className="text-2xl font-display font-black text-ink leading-none">{value ?? "—"}</p>
        <p className="text-xs font-mono text-ink/60 mt-0.5">{label}</p>
        {sub && <p className="text-[10px] font-mono text-ink/40 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

// ── Pipeline step ─────────────────────────────────────────────────────────
function PipelineStep({ n, icon, title, desc, last }) {
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className="w-7 h-7 border-2 border-ink bg-ink text-paper flex items-center justify-center text-xs font-black font-mono shrink-0">
          {n}
        </div>
        {!last && <div className="w-0.5 flex-1 bg-ink/20 mt-1 min-h-[16px]" />}
      </div>
      <div className={`pb-4 ${last ? "" : ""}`}>
        <p className="text-sm font-display font-bold text-ink flex items-center gap-1.5">{icon} {title}</p>
        <p className="text-[11px] font-mono text-ink/50 mt-0.5 leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────
export default function TrackingPage() {
  const [keys,            setKeys]            = useState([]);
  const [stats,           setStats]           = useState(null);
  const [loading,         setLoading]         = useState(true);
  const [statsLoading,    setStatsLoading]    = useState(true);
  const [error,           setError]           = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKeyName,      setNewKeyName]      = useState("");
  const [creating,        setCreating]        = useState(false);
  const [copiedKeyId,     setCopiedKeyId]     = useState(null);
  const [snippetOpen,     setSnippetOpen]     = useState(false);
  const [toast,           setToast]           = useState(null);

  const showToast = (msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => { fetchKeys(); fetchStats(); }, []);

  const getToken = () => localStorage.getItem("access_token");

  const fetchKeys = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API}/api/api-keys/list`, {
        headers: { Authorization: `Bearer ${getToken()}` }
      });
      if (!res.ok) throw new Error("Failed to load API keys.");
      const data = await res.json();
      setKeys(data.keys.filter(k => k.is_active) || []);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  const fetchStats = async () => {
    try {
      setStatsLoading(true);
      const res = await fetch(`${API}/api/api-keys/stats`, {
        headers: { Authorization: `Bearer ${getToken()}` }
      });
      if (res.ok) setStats(await res.json());
    } catch (_) {}
    finally { setStatsLoading(false); }
  };

  const handleCreateKey = async (e) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    setCreating(true);
    try {
      const res = await fetch(`${API}/api/api-keys/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ name: newKeyName })
      });
      if (!res.ok) throw new Error("Failed to create key");
      await fetchKeys();
      setShowCreateModal(false);
      setNewKeyName("");
      setSnippetOpen(true);
    } catch (err) { showToast(err.message, "error"); }
    finally { setCreating(false); }
  };

  const handleRevoke = async (keyId) => {
    if (!confirm("Revoke this key? All sites using it will stop tracking immediately.")) return;
    try {
      await fetch(`${API}/api/api-keys/${keyId}`, {
        method: "DELETE", headers: { Authorization: `Bearer ${getToken()}` }
      });
      await fetchKeys();
    } catch (err) { showToast(err.message, "error"); }
  };

  const copyKey = (key, id) => {
    navigator.clipboard.writeText(key);
    setCopiedKeyId(id);
    setTimeout(() => setCopiedKeyId(null), 2000);
  };

  const activeKey = keys.length > 0 ? keys[0].key : null;

  return (
    <DashboardLayout>
      <div className="p-6 max-w-screen-2xl mx-auto space-y-6">

        {/* ── Page Header ── */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 border-b-4 border-ink pb-6">
          <div>
            <h1 className="text-4xl font-display font-black text-ink uppercase tracking-tight flex items-center gap-3">
              <span className="w-3 h-3 bg-data-green rounded-full animate-pulse inline-block" />
              Live Tracking
            </h1>
            <p className="text-sm font-mono text-ink/50 mt-1 max-w-xl">
              Behavioral SDK — tracks page views, scroll depth, UTMs, key actions &amp; auto-promotes hot visitors to leads.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {keys.length > 0 && (
              <button
                onClick={() => setSnippetOpen(s => !s)}
                className="flex items-center gap-2 px-4 py-2.5 border-4 border-ink bg-paper text-ink font-bold text-sm shadow-[3px_3px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-y-0.5 transition-all"
              >
                <Globe className="w-4 h-4" />
                {snippetOpen ? "Hide SDK" : "Install SDK"}
                {snippetOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
            )}
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2.5 bg-ink text-paper border-4 border-ink font-bold text-sm shadow-[4px_4px_0px_0px_rgba(0,0,0,0.3)] hover:shadow-none hover:translate-y-0.5 transition-all"
            >
              <Plus className="w-4 h-4" /> New API Key
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border-4 border-red-500 text-red-700 font-mono text-sm">
            ⚠️ {error}
          </div>
        )}

        {/* ── Stats Row ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Users}    label="Total Visitors"    accent="bg-blue-500"
            value={stats?.total_visitors ?? (statsLoading ? "…" : 0)}
            sub={`${stats?.active_24h ?? 0} active today`} />
          <StatCard icon={Target}   label="SDK Leads"         accent="bg-data-green"
            value={stats?.total_leads_sdk ?? (statsLoading ? "…" : 0)}
            sub={`${stats?.identified ?? 0} identified`} />
          <StatCard icon={TrendingUp} label="Avg Engagement"  accent="bg-purple-500"
            value={stats ? `${stats.avg_engagement}/100` : (statsLoading ? "…" : "—")}
            sub={`${stats?.events_7d ?? 0} events this week`} />
          <StatCard icon={Zap} label="High Intent"   accent="bg-orange-500"
            value={stats ? ((stats.cart_visitors || 0) + (stats.checkout_visitors || 0)) : (statsLoading ? "…" : 0)}
            sub={`${stats?.cart_visitors ?? 0} actions · ${stats?.checkout_visitors ?? 0} goals`} />
        </div>

        {/* ── SDK Snippet (collapsible) ── */}
        {snippetOpen && activeKey && (
          <div className="bg-paper border-4 border-ink shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] p-6">
            <h3 className="font-display font-black text-base uppercase mb-4 flex items-center gap-2">
              <Globe className="w-4 h-4" /> Install SDK on Your Website
            </h3>
            <EmbedSnippet apiKey={activeKey} />
          </div>
        )}

        {/* ── Main 2-col Grid ── */}
        <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">

          {/* Left 3/5: Live Feed */}
          <div className="xl:col-span-3">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xl font-display font-black uppercase tracking-tight flex items-center gap-2">
                <span className="w-2 h-2 bg-data-green rounded-full animate-pulse" />
                Live Feed
              </h2>
            </div>
            <LiveVisitorFeed />
          </div>

          {/* Right 2/5: Keys + How It Works */}
          <div className="xl:col-span-2 space-y-6">

            {/* ── API Keys ── */}
            <div className="bg-paper border-4 border-ink shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] overflow-hidden">
              <div className="border-b-4 border-ink px-4 py-3 bg-mute flex items-center justify-between">
                <h2 className="font-display font-black text-base uppercase tracking-tight flex items-center gap-2">
                  <Key className="w-4 h-4" /> API Keys
                </h2>
                <span className="text-xs font-mono text-ink/50">{keys.length} active</span>
              </div>

              {loading ? (
                <div className="p-8 text-center font-mono text-sm text-ink/30 animate-pulse">Loading…</div>
              ) : keys.length === 0 ? (
                <div className="p-8 text-center space-y-3">
                  <p className="font-mono text-sm text-ink/40 italic">No API keys yet.</p>
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="px-4 py-2 bg-ink text-paper font-bold text-sm border-2 border-ink hover:bg-ink/80 transition-colors"
                  >
                    Create First Key
                  </button>
                </div>
              ) : (
                <table className="w-full font-mono text-sm">
                  <thead className="bg-mute border-b-2 border-ink/20 text-xs text-ink/50 uppercase">
                    <tr>
                      <th className="p-3 text-left">Name</th>
                      <th className="p-3 text-left">Key</th>
                      <th className="p-3 text-left hidden sm:table-cell">Events</th>
                      <th className="p-3 text-right">Del</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-ink/10">
                    {keys.map(k => (
                      <tr key={k._id} className="hover:bg-mute/30 transition-colors">
                        <td className="p-3 font-bold text-sm truncate max-w-[100px]">{k.name}</td>
                        <td className="p-3">
                          <button
                            onClick={() => copyKey(k.key, k._id)}
                            className="flex items-center gap-1.5 bg-ink/5 hover:bg-ink/10 px-2 py-1 border border-ink/20 hover:border-ink transition-colors text-xs"
                          >
                            {copiedKeyId === k._id
                              ? <><Check className="w-3 h-3 text-data-green" /><span className="text-data-green font-bold">Copied!</span></>
                              : <><Copy className="w-3 h-3 text-ink/40" /><span className="text-ink/60">{k.key_preview || k.key?.slice(0, 16) + "…"}</span></>
                            }
                          </button>
                        </td>
                        <td className="p-3 text-ink/40 text-xs hidden sm:table-cell">
                          {(k.event_count || 0).toLocaleString()}
                        </td>
                        <td className="p-3 text-right">
                          <button
                            onClick={() => handleRevoke(k._id)}
                            className="p-1.5 text-ink/30 hover:text-red-500 hover:bg-red-50 border border-transparent hover:border-red-300 transition-colors"
                            title="Revoke"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* ── How It Works ── */}
            <div className="bg-paper border-4 border-ink shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] p-5">
              <h3 className="font-display font-black text-base uppercase tracking-tight mb-4 flex items-center gap-2">
                <Activity className="w-4 h-4" /> How It Works
              </h3>
              <div>
                <PipelineStep n="01" icon="📋" title="Install SDK" last={false}
                  desc="Paste one script tag. Auto-tracks page views, scroll, clicks, key actions & UTMs." />
                <PipelineStep n="02" icon="📊" title="Events Captured" last={false}
                  desc="Every visitor action scores in real-time — key actions, goal completions, time on site." />
                <PipelineStep n="03" icon="🎯" title="Threshold Met" last={false}
                  desc="Engagement ≥ 50 or key action taken → visitor auto-promotes to a full pipeline lead." />
                <PipelineStep n="04" icon="🤖" title="AI Pipeline Runs" last={true}
                  desc="5-agent AI: research, intent score, email draft, timing, CRM log — fires instantly." />
              </div>

              {/* Intent legend */}
              <div className="mt-4 pt-4 border-t-2 border-ink/10">
                <p className="text-[10px] font-mono font-bold text-ink/30 uppercase tracking-widest mb-2">Intent Levels</p>
                <div className="space-y-1.5">
                  {[
                    { color: "bg-red-500",    label: "GOAL",     desc: "Primary goal reached" },
                    { color: "bg-orange-400", label: "ACTION",   desc: "High interest action" },
                    { color: "bg-yellow-400", label: "HOT",      desc: "Engagement ≥ 60" },
                    { color: "bg-blue-400",   label: "BROWSING", desc: "Exploring site" },
                  ].map(({ color, label, desc }) => (
                    <div key={label} className="flex items-center gap-2 text-[11px] font-mono">
                      <span className={`w-2.5 h-2.5 border border-ink/20 shrink-0 ${color}`} />
                      <span className="font-black text-ink w-20">{label}</span>
                      <span className="text-ink/40">{desc}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>

      {/* ── Create Key Modal ── */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 backdrop-blur-sm p-4">
          <div className="bg-paper border-4 border-ink shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-8 max-w-sm w-full relative">
            <button
              onClick={() => setShowCreateModal(false)}
              className="absolute top-4 right-4 p-1 hover:bg-mute transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2 mb-1">
              <Key className="w-5 h-5" />
              <h2 className="text-2xl font-display font-black uppercase">Create API Key</h2>
            </div>
            <p className="text-xs font-mono text-ink/40 mb-6">
              Give it a name so you know which site it belongs to.
            </p>
            <form onSubmit={handleCreateKey} className="space-y-5">
              <div>
                <label className="block font-mono text-xs font-bold mb-2 uppercase text-ink/60">Key Name</label>
                <input
                  type="text" required
                  value={newKeyName}
                  onChange={e => setNewKeyName(e.target.value)}
                  className="w-full p-3 bg-mute border-2 border-ink font-mono text-sm focus:outline-none focus:border-primary"
                  placeholder="e.g. Production Website"
                  autoFocus
                />
              </div>
              <button
                type="submit" disabled={creating}
                className="w-full py-3 bg-ink text-paper border-2 border-ink font-bold font-mono hover:bg-ink/80 disabled:opacity-50 transition-colors shadow-[3px_3px_0px_0px_rgba(0,0,0,0.3)] hover:shadow-none"
              >
                {creating ? "Generating…" : "Generate Key"}
              </button>
            </form>
          </div>
        </div>
      )}
      {toast && (
        <div
          className={`fixed top-6 right-6 z-50 px-5 py-3 border-2 border-ink font-mono text-xs uppercase
                    flex flex-col gap-2 shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]
                    transition-all animate-in slide-in-from-top-2
                    ${toast.type === "error"
                      ? "bg-red-50 text-red-700"
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
