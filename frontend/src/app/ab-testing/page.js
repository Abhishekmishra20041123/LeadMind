"use client";
import { useState, useEffect, useCallback } from "react";
import DashboardLayout from "../../components/DashboardLayout";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getAuth() {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  return { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}

// ── Status Badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }) {
  const map = {
    running:   "bg-primary text-paper",
    completed: "bg-ink text-paper",
  };
  return (
    <span className={`font-mono text-[10px] font-bold uppercase px-2 py-0.5 tracking-widest ${map[status] || map.running}`}>
      {status}
    </span>
  );
}

// ── Variant Bar ───────────────────────────────────────────────────────────────

function VariantBar({ variant, isWinner }) {
  const openRate  = variant.sent > 0 ? ((variant.opens  || 0) / variant.sent * 100).toFixed(1) : "0.0";
  const clickRate = variant.sent > 0 ? ((variant.clicks || 0) / variant.sent * 100).toFixed(1) : "0.0";

  return (
    <div className={`border ${isWinner ? "border-data-green bg-data-green/5" : "border-ink bg-mute"} p-4 relative`}>
      {isWinner && (
        <div className="absolute -top-px left-0 right-0 h-0.5 bg-data-green" />
      )}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[10px] font-bold uppercase text-ink/60">Variant {variant.id}</span>
          {isWinner && (
            <span className="font-mono text-[9px] font-bold uppercase bg-data-green text-paper px-2 py-0.5 tracking-widest">
              Winner
            </span>
          )}
        </div>
        <span className="font-mono text-[10px] text-ink/40 uppercase">{variant.sent} sent</span>
      </div>

      <p className="font-display font-bold text-sm mb-3 leading-snug">{variant.subject || "—"}</p>

      {/* Open Rate */}
      <div className="mb-2">
        <div className="flex justify-between mb-1">
          <span className="font-mono text-[10px] uppercase text-ink/50">Open Rate</span>
          <span className="font-mono text-[10px] font-bold">{openRate}%</span>
        </div>
        <div className="h-1.5 bg-paper border border-ink">
          <div
            className="h-full bg-ink transition-all duration-700"
            style={{ width: `${Math.min(openRate, 100)}%` }}
          />
        </div>
      </div>

      {/* Click Rate */}
      <div>
        <div className="flex justify-between mb-1">
          <span className="font-mono text-[10px] uppercase text-ink/50">Click Rate</span>
          <span className="font-mono text-[10px] font-bold text-primary">{clickRate}%</span>
        </div>
        <div className="h-1.5 bg-paper border border-ink">
          <div
            className="h-full bg-primary transition-all duration-700"
            style={{ width: `${Math.min(clickRate, 100)}%` }}
          />
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className="border border-ink px-2 py-1.5 bg-paper text-center">
          <p className="font-mono text-[9px] uppercase text-ink/40">Opens</p>
          <p className="font-display font-bold text-lg leading-none mt-0.5">{variant.opens || 0}</p>
        </div>
        <div className="border border-ink px-2 py-1.5 bg-paper text-center">
          <p className="font-mono text-[9px] uppercase text-ink/40">Clicks</p>
          <p className="font-display font-bold text-lg leading-none mt-0.5">{variant.clicks || 0}</p>
        </div>
      </div>
    </div>
  );
}

// ── Significance Block ────────────────────────────────────────────────────────

function SignificanceBlock({ sig }) {
  if (!sig) return null;
  return (
    <div className={`border ${sig.is_significant ? "border-data-green bg-data-green/5" : "border-ink bg-mute"} p-4 flex items-center gap-4 mb-4`}>
      <span className={`material-symbols-outlined text-[24px] ${sig.is_significant ? "text-data-green" : "text-ink/30"}`}>
        {sig.is_significant ? "verified" : "hourglass_empty"}
      </span>
      <div>
        <p className={`font-display font-bold text-sm ${sig.is_significant ? "text-data-green" : "text-ink"}`}>
          {sig.is_significant
            ? "Statistically significant at 95% confidence"
            : "Not yet significant — need more data"}
        </p>
        <p className="font-mono text-[10px] uppercase text-ink/50 mt-0.5">
          Z-score: <strong>{sig.z_score}</strong> &nbsp;·&nbsp; Threshold: 1.96
        </p>
      </div>
    </div>
  );
}

// ── Test Detail Modal ─────────────────────────────────────────────────────────

function TestDetailModal({ test, onClose, onRefresh }) {
  const [detail, setDetail] = useState(null);
  const [declareId, setDeclareId] = useState("");
  const [declaring, setDeclaring] = useState(false);

  useEffect(() => {
    fetch(`${API}/api/ab/${test.test_id}`, { headers: getAuth() })
      .then(r => r.json()).then(setDetail);
  }, [test.test_id]);

  const declareWinner = async () => {
    if (!declareId) return;
    setDeclaring(true);
    await fetch(`${API}/api/ab/${test.test_id}/declare-winner`, {
      method: "POST", headers: getAuth(),
      body: JSON.stringify({ winner_variant_id: declareId }),
    });
    setDeclaring(false);
    onRefresh(); onClose();
  };

  return (
    <div className="fixed inset-0 bg-ink/70 flex items-center justify-center z-50 p-4">
      <div className="bg-paper border border-ink w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-premium flex flex-col">
        <div className="h-14 border-b border-ink flex items-center justify-between px-6 bg-ink text-paper shrink-0">
          <span className="font-display font-bold uppercase tracking-tight truncate">{test.name}</span>
          <button onClick={onClose}
            className="font-mono text-xs uppercase border border-paper/30 px-3 py-1 hover:bg-paper hover:text-ink transition-colors shrink-0">
            Close
          </button>
        </div>

        <div className="p-6">
          {!detail ? (
            <p className="font-mono text-xs uppercase text-ink/40 animate-pulse py-8 text-center">Loading results...</p>
          ) : (
            <>
              <div className="flex items-center gap-4 mb-5">
                <StatusBadge status={detail.status} />
                <span className="font-mono text-[10px] uppercase text-ink/50">
                  {detail.sample_size} leads · {detail.variants?.length} variants
                  {detail.winner && ` · Winner: Variant ${detail.winner}`}
                </span>
              </div>

              <SignificanceBlock sig={detail.significance} />

              <div className="grid grid-cols-2 gap-4 mb-5">
                {(detail.variants || []).map(v => (
                  <VariantBar key={v.id} variant={v} isWinner={detail.winner === v.id} />
                ))}
              </div>

              {detail.status === "running" && (
                <div className="border border-ink bg-mute p-4">
                  <p className="font-mono text-[10px] uppercase text-ink/60 mb-3">Declare Winner Manually</p>
                  <div className="flex gap-3">
                    <select value={declareId} onChange={e => setDeclareId(e.target.value)}
                      className="flex-1 border border-ink bg-paper px-3 py-2 font-mono text-xs focus:outline-none focus:border-primary">
                      <option value="">Select variant...</option>
                      {(detail.variants || []).map(v => (
                        <option key={v.id} value={v.id}>Variant {v.id} — {v.subject}</option>
                      ))}
                    </select>
                    <button onClick={declareWinner} disabled={!declareId || declaring}
                      className="bg-ink text-paper border border-ink px-5 py-2 font-mono text-xs uppercase hover:bg-primary hover:border-primary transition-colors disabled:opacity-50 whitespace-nowrap">
                      {declaring ? "Declaring..." : "Declare Winner"}
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Create Test Modal ─────────────────────────────────────────────────────────

function CreateTestModal({ onClose, onCreated }) {
  const [name, setName]     = useState("");
  const [leadIds, setLeadIds] = useState("");
  const [varA, setVarA]     = useState({ id: "A", subject: "", content: "" });
  const [varB, setVarB]     = useState({ id: "B", subject: "", content: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");

  const autoGenerateB = () => {
    if (!varA.subject) return setError("Enter Variant A subject first");
    const prefixes = ["Boost your", "10x your", "Scale your", "Transform your"];
    const words = varA.subject.split(" ").slice(-2).join(" ");
    const pick = prefixes[Math.floor(Math.random() * prefixes.length)];
    setVarB({ id: "B", subject: `${pick} ${words}`, content: varB.content || varA.content });
    setError("");
  };

  const submit = async () => {
    const ids = leadIds.split(/[\n,]+/).map(s => s.trim()).filter(Boolean);
    if (!name || !ids.length || !varA.subject || !varB.subject)
      return setError("Name, lead IDs, and both variant subjects are required");
    setLoading(true); setError("");
    try {
      const res = await fetch(`${API}/api/ab/create`, {
        method: "POST", headers: getAuth(),
        body: JSON.stringify({ name, lead_ids: ids, variants: [varA, varB] }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed");
      onCreated(); onClose();
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const varBlock = (v, setV, label) => (
    <div className="border border-ink bg-mute p-4">
      <p className="font-mono text-[10px] font-bold uppercase text-ink/60 mb-3">Variant {label}</p>
      <div className="mb-3">
        <label className="font-mono text-[10px] uppercase text-ink/50 block mb-1">Subject</label>
        <input value={v.subject} onChange={e => setV({ ...v, subject: e.target.value })}
          className="w-full border border-ink bg-paper px-3 py-2 font-mono text-xs focus:outline-none focus:border-primary"
          placeholder={`Subject for variant ${label}...`} />
      </div>
      <div>
        <label className="font-mono text-[10px] uppercase text-ink/50 block mb-1">Content (optional)</label>
        <textarea value={v.content} onChange={e => setV({ ...v, content: e.target.value })} rows={2}
          className="w-full border border-ink bg-paper px-3 py-2 font-mono text-xs focus:outline-none focus:border-primary resize-none"
          placeholder="Opening paragraph..." />
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 bg-ink/70 flex items-center justify-center z-50 p-4">
      <div className="bg-paper border border-ink w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-premium">
        <div className="h-14 border-b border-ink flex items-center justify-between px-6 bg-ink text-paper shrink-0">
          <span className="font-display font-bold uppercase tracking-tight">New A/B Test</span>
          <button onClick={onClose}
            className="font-mono text-xs uppercase border border-paper/30 px-3 py-1 hover:bg-paper hover:text-ink transition-colors">
            Close
          </button>
        </div>
        <div className="p-6 flex flex-col gap-4">
          <div>
            <label className="font-mono text-[10px] uppercase text-ink/60 block mb-1">Test Name</label>
            <input value={name} onChange={e => setName(e.target.value)}
              className="w-full border border-ink bg-paper px-3 py-2 font-mono text-xs focus:outline-none focus:border-primary"
              placeholder="e.g. Subject Line Test — Q2" />
          </div>
          <div>
            <label className="font-mono text-[10px] uppercase text-ink/60 block mb-1">Lead IDs (comma or newline)</label>
            <textarea value={leadIds} onChange={e => setLeadIds(e.target.value)} rows={4}
              className="w-full border border-ink bg-mute px-3 py-2 font-mono text-xs focus:outline-none focus:border-primary resize-none"
              placeholder={"L_001, L_002, L_003..."} />
          </div>
          {varBlock(varA, setVarA, "A")}
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-ink/20" />
            <button onClick={autoGenerateB}
              className="border border-ink px-4 py-1.5 font-mono text-[10px] uppercase hover:bg-ink hover:text-paper transition-colors flex items-center gap-2">
              <span className="material-symbols-outlined text-[12px]">auto_awesome</span>
              Auto-Generate B
            </button>
            <div className="flex-1 h-px bg-ink/20" />
          </div>
          {varBlock(varB, setVarB, "B")}
          {error && <p className="font-mono text-xs text-primary uppercase">{error}</p>}
          <div className="flex gap-3 justify-end border-t border-ink pt-4">
            <button onClick={onClose} className="border border-ink px-5 py-2 font-mono text-xs uppercase hover:bg-mute transition-colors">Cancel</button>
            <button onClick={submit} disabled={loading}
              className="bg-ink text-paper border border-ink px-5 py-2 font-mono text-xs uppercase hover:bg-primary hover:border-primary transition-colors disabled:opacity-50">
              {loading ? "Launching..." : "Launch A/B Test"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function ABTestingPage() {
  const [tests, setTests]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState(null);
  const [toast, setToast]       = useState("");

  const fetchTests = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/ab/list`, { headers: getAuth() });
      const data = await res.json();
      setTests(data.tests || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchTests(); }, [fetchTests]);

  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(""), 3000); };

  const running   = tests.filter(t => t.status === "running").length;
  const completed = tests.filter(t => t.status === "completed").length;
  const winners   = tests.filter(t => t.winner).length;

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full bg-paper bg-grid-pattern overflow-hidden">

        {/* Page Header */}
        <header className="h-16 shrink-0 border-b border-ink flex items-center justify-between px-8 bg-paper z-10">
          <div className="flex flex-col justify-center">
            <span className="font-mono text-[10px] text-ink/60 uppercase">Email Optimization</span>
            <h2 className="font-display font-bold text-xl tracking-tight leading-none mt-0.5">A/B Testing</h2>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={fetchTests}
              className="h-9 px-4 border border-ink bg-paper hover:bg-mute font-mono text-[10px] uppercase flex items-center gap-2 transition-colors">
              <span className="material-symbols-outlined text-[14px]">refresh</span>
              Refresh
            </button>
            <button onClick={() => setShowCreate(true)}
              className="h-9 px-4 bg-ink text-paper border border-ink hover:bg-primary hover:border-primary font-mono text-[10px] uppercase flex items-center gap-2 transition-colors">
              <span className="material-symbols-outlined text-[14px]">science</span>
              New A/B Test
            </button>
          </div>
        </header>

        {/* Stats Row */}
        <div className="border-b border-ink shrink-0 flex divide-x divide-ink">
          {[
            { label: "Running Tests", value: running,   icon: "play_circle",   highlight: running > 0 },
            { label: "Completed",     value: completed, icon: "check_circle",  highlight: false },
            { label: "Winners Found", value: winners,   icon: "emoji_events",  highlight: false },
            { label: "Total Tests",   value: tests.length, icon: "science",    highlight: false },
          ].map(s => (
            <div key={s.label} className="flex-1 px-8 py-4 flex items-center gap-4 bg-paper hover:bg-mute transition-colors">
              <span className={`material-symbols-outlined text-[24px] ${s.highlight ? "text-primary" : "text-ink/30"}`}>{s.icon}</span>
              <div>
                <p className="font-mono text-[10px] uppercase text-ink/50">{s.label}</p>
                <p className={`font-display text-3xl font-bold leading-none mt-0.5 ${s.highlight ? "text-primary" : ""}`}>{s.value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Tests Grid */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <span className="material-symbols-outlined text-[48px] text-ink/20 animate-pulse block mb-3">science</span>
                <p className="font-mono text-xs uppercase text-ink/40">Loading tests...</p>
              </div>
            </div>
          ) : tests.length === 0 ? (
            <div className="border border-dashed border-ink flex flex-col items-center justify-center py-24">
              <span className="material-symbols-outlined text-[48px] text-ink/20 mb-4">science</span>
              <p className="font-mono text-xs uppercase text-ink/40">No A/B tests yet</p>
              <p className="font-mono text-[10px] text-ink/30 mt-1">Create your first test to compare email variants</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              {tests.map(t => {
                const variants = t.variants || [];
                return (
                  <button
                    key={t.test_id}
                    onClick={() => setSelected(t)}
                    className={`text-left bg-paper border ${t.winner ? "border-data-green" : "border-ink"} p-5 hover:shadow-premium transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 group`}
                  >
                    {/* Card Header */}
                    <div className="flex items-start justify-between mb-3">
                      <p className="font-display font-bold text-sm leading-snug group-hover:text-primary transition-colors">{t.name}</p>
                      <StatusBadge status={t.status} />
                    </div>

                    <p className="font-mono text-[10px] uppercase text-ink/40 mb-4">
                      {t.sample_size} leads · {variants.length} variants
                      {t.winner && <span className="text-data-green font-bold"> · Winner: {t.winner}</span>}
                    </p>

                    {/* Mini Variant Bars */}
                    <div className="flex flex-col gap-2">
                      {variants.slice(0, 2).map(v => {
                        const rate = v.sent > 0 ? ((v.opens || 0) / v.sent * 100).toFixed(1) : "0.0";
                        return (
                          <div key={v.id}>
                            <div className="flex justify-between mb-1">
                              <span className="font-mono text-[9px] uppercase text-ink/50">Variant {v.id}</span>
                              <span className="font-mono text-[9px] font-bold">{rate}% opens</span>
                            </div>
                            <div className="h-1 bg-mute border border-ink/20">
                              <div
                                className={`h-full transition-all duration-700 ${t.winner === v.id ? "bg-data-green" : "bg-ink"}`}
                                style={{ width: `${Math.min(parseFloat(rate), 100)}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    <p className="font-mono text-[9px] uppercase text-ink/30 mt-3 text-right group-hover:text-primary transition-colors">
                      View full results →
                    </p>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      {showCreate && (
        <CreateTestModal
          onClose={() => setShowCreate(false)}
          onCreated={() => { fetchTests(); showToast("A/B test launched!"); }}
        />
      )}
      {selected && (
        <TestDetailModal
          test={selected}
          onClose={() => setSelected(null)}
          onRefresh={() => { fetchTests(); showToast("Winner declared!"); }}
        />
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 bg-ink text-paper px-5 py-3 border border-ink font-mono text-xs uppercase flex items-center gap-2 shadow-premium animate-in slide-in-from-bottom-2">
          <span className="material-symbols-outlined text-[14px] text-data-green">check_circle</span>
          {toast}
        </div>
      )}
    </DashboardLayout>
  );
}
