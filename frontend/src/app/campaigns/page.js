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
    active:    "bg-data-green text-paper",
    paused:    "bg-yellow-500 text-paper",
    completed: "bg-ink text-paper",
  };
  return (
    <span className={`font-mono text-[10px] font-bold uppercase px-2 py-0.5 tracking-widest ${map[status] || map.active}`}>
      {status}
    </span>
  );
}

// ── Step Editor ───────────────────────────────────────────────────────────────

const BLANK_STEP = {
  step_id: "", day_offset: 0, channel: "email",
  subject: "", content: "", conditions: { proceed_if: "always" },
};

function StepEditor({ steps, setSteps }) {
  const addStep = () =>
    setSteps([...steps, { ...BLANK_STEP, step_id: `s${steps.length + 1}` }]);
  const removeStep = (i) => setSteps(steps.filter((_, idx) => idx !== i));
  const update = (i, field, value) => {
    const next = [...steps];
    if (field === "proceed_if") {
      next[i] = { ...next[i], conditions: { proceed_if: value } };
    } else {
      next[i] = { ...next[i], [field]: field === "day_offset" ? parseInt(value, 10) || 0 : value };
    }
    setSteps(next);
  };

  return (
    <div className="flex flex-col gap-3">
      {steps.map((step, i) => (
        <div key={i} className="border border-ink bg-mute p-4">
          <div className="flex justify-between items-center mb-3">
            <span className="font-mono text-[10px] font-bold uppercase text-ink/60">Step {i + 1}</span>
            {steps.length > 1 && (
              <button onClick={() => removeStep(i)}
                className="font-mono text-[10px] uppercase border border-ink px-2 py-0.5 hover:bg-primary hover:text-paper hover:border-primary transition-colors">
                Remove
              </button>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="font-mono text-[10px] uppercase text-ink/60 block mb-1">Step ID</label>
              <input value={step.step_id} onChange={e => update(i, "step_id", e.target.value)}
                className="w-full border border-ink bg-paper px-3 py-2 font-mono text-xs focus:outline-none focus:border-primary"
                placeholder="s1" />
            </div>
            <div>
              <label className="font-mono text-[10px] uppercase text-ink/60 block mb-1">Send After (days)</label>
              <input type="number" min={0} value={step.day_offset} onChange={e => update(i, "day_offset", e.target.value)}
                className="w-full border border-ink bg-paper px-3 py-2 font-mono text-xs focus:outline-none focus:border-primary" />
            </div>
          </div>
          <div className="mb-3">
            <label className="font-mono text-[10px] uppercase text-ink/60 block mb-1">Subject Line</label>
            <input value={step.subject} onChange={e => update(i, "subject", e.target.value)}
              className="w-full border border-ink bg-paper px-3 py-2 font-mono text-xs focus:outline-none focus:border-primary"
              placeholder="Your subject line..." />
          </div>
          <div className="mb-3">
            <label className="font-mono text-[10px] uppercase text-ink/60 block mb-1">Email Content</label>
            <textarea value={step.content} onChange={e => update(i, "content", e.target.value)} rows={3}
              className="w-full border border-ink bg-paper px-3 py-2 font-mono text-xs focus:outline-none focus:border-primary resize-none"
              placeholder="Hi {{name}}, ..." />
          </div>
          <div>
            <label className="font-mono text-[10px] uppercase text-ink/60 block mb-1">Proceed Condition</label>
            <select value={step.conditions?.proceed_if || "always"} onChange={e => update(i, "proceed_if", e.target.value)}
              className="w-full border border-ink bg-paper px-3 py-2 font-mono text-xs focus:outline-none focus:border-primary">
              <option value="always">Always Send</option>
              <option value="opened_previous">Only if Opened Previous</option>
              <option value="clicked_previous">Only if Clicked Previous</option>
            </select>
          </div>
        </div>
      ))}
      <button onClick={addStep}
        className="border border-dashed border-ink px-4 py-3 font-mono text-xs uppercase text-ink/50 hover:border-primary hover:text-primary transition-colors text-center">
        + Add Step
      </button>
    </div>
  );
}

// ── Create Campaign Modal ─────────────────────────────────────────────────────

function CreateCampaignModal({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [steps, setSteps] = useState([{ ...BLANK_STEP, step_id: "s1" }]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    if (!name.trim()) return setError("Campaign name is required");
    if (steps.some(s => !s.step_id || !s.subject)) return setError("All steps need a Step ID and Subject");
    setLoading(true); setError("");
    try {
      const res = await fetch(`${API}/api/campaigns/create`, {
        method: "POST", headers: getAuth(), body: JSON.stringify({ name, steps }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed");
      onCreated(); onClose();
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 bg-ink/70 flex items-center justify-center z-50 p-4">
      <div className="bg-paper border border-ink w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-premium flex flex-col">
        {/* Modal Header */}
        <div className="h-14 border-b border-ink flex items-center justify-between px-6 shrink-0 bg-ink text-paper">
          <span className="font-display font-bold uppercase tracking-tight">New Drip Campaign</span>
          <button onClick={onClose} className="font-mono text-xs uppercase border border-paper/30 px-3 py-1 hover:bg-paper hover:text-ink transition-colors">
            Close
          </button>
        </div>
        <div className="p-6 flex flex-col gap-4">
          <div>
            <label className="font-mono text-[10px] uppercase text-ink/60 block mb-1">Campaign Name</label>
            <input value={name} onChange={e => setName(e.target.value)}
              className="w-full border border-ink bg-paper px-3 py-2 font-mono text-sm focus:outline-none focus:border-primary"
              placeholder="e.g. Welcome Sequence" />
          </div>
          <div>
            <p className="font-mono text-[10px] uppercase text-ink/60 mb-3">Email Steps</p>
            <StepEditor steps={steps} setSteps={setSteps} />
          </div>
          {error && <p className="font-mono text-xs text-primary uppercase">{error}</p>}
          <div className="flex gap-3 justify-end pt-2 border-t border-ink">
            <button onClick={onClose}
              className="border border-ink px-5 py-2 font-mono text-xs uppercase hover:bg-mute transition-colors">
              Cancel
            </button>
            <button onClick={submit} disabled={loading}
              className="bg-ink text-paper border border-ink px-5 py-2 font-mono text-xs uppercase hover:bg-primary hover:border-primary transition-colors disabled:opacity-50">
              {loading ? "Creating..." : "Create Campaign"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Enroll Modal ──────────────────────────────────────────────────────────────

function EnrollModal({ campaign, onClose, onEnrolled }) {
  const [leadIds, setLeadIds] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    const ids = leadIds.split(/[\n,]+/).map(s => s.trim()).filter(Boolean);
    if (!ids.length) return setError("Enter at least one Lead ID");
    setLoading(true); setError("");
    try {
      const res = await fetch(`${API}/api/campaigns/${campaign.campaign_id}/enroll`, {
        method: "POST", headers: getAuth(), body: JSON.stringify({ lead_ids: ids }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed");
      onEnrolled(data); onClose();
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 bg-ink/70 flex items-center justify-center z-50 p-4">
      <div className="bg-paper border border-ink w-full max-w-md shadow-premium">
        <div className="h-14 border-b border-ink flex items-center justify-between px-6 bg-ink text-paper shrink-0">
          <span className="font-display font-bold uppercase tracking-tight text-sm truncate">{campaign.name} — Enroll Leads</span>
          <button onClick={onClose} className="font-mono text-xs uppercase border border-paper/30 px-3 py-1 hover:bg-paper hover:text-ink transition-colors shrink-0">Close</button>
        </div>
        <div className="p-6 flex flex-col gap-4">
          <div>
            <label className="font-mono text-[10px] uppercase text-ink/60 block mb-1">Lead IDs (one per line or comma-separated)</label>
            <textarea value={leadIds} onChange={e => setLeadIds(e.target.value)} rows={5}
              className="w-full border border-ink bg-mute px-3 py-2 font-mono text-xs focus:outline-none focus:border-primary resize-none"
              placeholder={"L_001\nL_002\nL_003"} />
          </div>
          {error && <p className="font-mono text-xs text-primary uppercase">{error}</p>}
          <div className="flex gap-3 justify-end border-t border-ink pt-4">
            <button onClick={onClose} className="border border-ink px-5 py-2 font-mono text-xs uppercase hover:bg-mute transition-colors">Cancel</button>
            <button onClick={submit} disabled={loading}
              className="bg-ink text-paper border border-ink px-5 py-2 font-mono text-xs uppercase hover:bg-primary hover:border-primary transition-colors disabled:opacity-50">
              {loading ? "Enrolling..." : "Enroll Leads"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Campaign Detail Drawer ────────────────────────────────────────────────────

function CampaignDetail({ campaign, onClose }) {
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    fetch(`${API}/api/campaigns/${campaign.campaign_id}`, { headers: getAuth() })
      .then(r => r.json()).then(setDetail);
  }, [campaign.campaign_id]);

  return (
    <div className="fixed inset-0 bg-ink/40 z-40 flex justify-end">
      <div className="w-full max-w-sm bg-paper border-l border-ink flex flex-col h-full overflow-y-auto">
        <div className="h-14 border-b border-ink flex items-center justify-between px-5 bg-ink text-paper shrink-0">
          <span className="font-display font-bold uppercase tracking-tight text-sm truncate">{campaign.name}</span>
          <button onClick={onClose} className="font-mono text-xs uppercase border border-paper/30 px-3 py-1 hover:bg-paper hover:text-ink transition-colors shrink-0">Close</button>
        </div>

        {!detail ? (
          <div className="flex-1 flex items-center justify-center font-mono text-xs uppercase text-ink/40 animate-pulse">Loading...</div>
        ) : (
          <div className="p-5 flex flex-col gap-5">
            {/* Enrollment Stats */}
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: "Total Enrolled", value: detail.total_enrolled ?? 0 },
                { label: "Active",         value: detail.active ?? 0 },
                { label: "Completed",      value: detail.completed ?? 0 },
                { label: "Dropped",        value: detail.dropped ?? 0 },
              ].map(s => (
                <div key={s.label} className="border border-ink p-4 bg-mute">
                  <p className="font-mono text-[10px] uppercase text-ink/60 mb-1">{s.label}</p>
                  <p className="font-display text-3xl font-bold">{s.value}</p>
                </div>
              ))}
            </div>

            {/* Steps */}
            <div>
              <p className="font-mono text-[10px] uppercase text-ink/60 mb-3">Steps ({detail.steps?.length})</p>
              <div className="flex flex-col gap-2">
                {detail.steps?.map((step, i) => (
                  <div key={step.step_id} className="border-l-4 border-primary pl-4 py-2 border-y border-r border-ink bg-mute">
                    <div className="flex justify-between mb-1">
                      <span className="font-mono text-[10px] uppercase font-bold text-primary">Step {i + 1} — Day {step.day_offset}</span>
                      <span className="font-mono text-[10px] text-ink/40">{detail.step_stats?.[step.step_id] ?? 0} active</span>
                    </div>
                    <p className="font-display text-sm font-bold mb-0.5">{step.subject}</p>
                    <p className="font-mono text-[10px] text-ink/50 uppercase">
                      Condition: {step.conditions?.proceed_if || "always"}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [enrollTarget, setEnrollTarget] = useState(null);
  const [detailTarget, setDetailTarget] = useState(null);
  const [toast, setToast] = useState("");

  const fetchCampaigns = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/campaigns/list`, { headers: getAuth() });
      const data = await res.json();
      setCampaigns(data.campaigns || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchCampaigns(); }, [fetchCampaigns]);

  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(""), 3000); };

  const togglePause = async (c) => {
    await fetch(`${API}/api/campaigns/${c.campaign_id}/pause`, { method: "PATCH", headers: getAuth() });
    showToast(`Campaign ${c.status === "active" ? "paused" : "resumed"}`);
    fetchCampaigns();
  };

  const deleteCampaign = async (c) => {
    if (!confirm(`Delete "${c.name}" and all enrollments?`)) return;
    await fetch(`${API}/api/campaigns/${c.campaign_id}`, { method: "DELETE", headers: getAuth() });
    showToast("Campaign deleted");
    fetchCampaigns();
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full bg-paper bg-grid-pattern overflow-hidden">

        {/* Page Header */}
        <header className="h-16 shrink-0 border-b border-ink flex items-center justify-between px-8 bg-paper z-10">
          <div className="flex flex-col justify-center">
            <span className="font-mono text-[10px] text-ink/60 uppercase">Outreach Automation</span>
            <h2 className="font-display font-bold text-xl tracking-tight leading-none mt-0.5">Drip Campaigns</h2>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={fetchCampaigns}
              className="h-9 px-4 border border-ink bg-paper hover:bg-mute font-mono text-[10px] uppercase flex items-center gap-2 transition-colors">
              <span className="material-symbols-outlined text-[14px]">refresh</span>
              Refresh
            </button>
            <button onClick={() => setShowCreate(true)}
              className="h-9 px-4 bg-ink text-paper border border-ink hover:bg-primary hover:border-primary font-mono text-[10px] uppercase flex items-center gap-2 transition-colors">
              <span className="material-symbols-outlined text-[14px]">add</span>
              New Campaign
            </button>
          </div>
        </header>

        {/* Stats Row */}
        <div className="border-b border-ink shrink-0 flex divide-x divide-ink">
          {[
            { label: "Total Campaigns",  value: campaigns.length,                                       icon: "campaign" },
            { label: "Active",           value: campaigns.filter(c => c.status === "active").length,    icon: "play_circle" },
            { label: "Total Enrolled",   value: campaigns.reduce((a, c) => a + (c.enrolled_count || 0), 0), icon: "group" },
            { label: "Completed Runs",   value: campaigns.reduce((a, c) => a + (c.completed_count || 0), 0), icon: "check_circle" },
          ].map(s => (
            <div key={s.label} className="flex-1 px-8 py-4 flex items-center gap-4 bg-paper hover:bg-mute transition-colors">
              <span className="material-symbols-outlined text-[24px] text-ink/30">{s.icon}</span>
              <div>
                <p className="font-mono text-[10px] uppercase text-ink/50">{s.label}</p>
                <p className="font-display text-3xl font-bold leading-none mt-0.5">{s.value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Table */}
        <div className="flex-1 overflow-y-auto">
          <table className="w-full border-collapse">
            <thead className="sticky top-0 z-10">
              <tr className="bg-ink text-paper">
                {["Campaign", "Status", "Steps", "Enrolled", "Completed", "Actions"].map(h => (
                  <th key={h} className="text-left px-6 py-3 font-mono text-[10px] uppercase tracking-widest font-bold">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-16 text-center font-mono text-xs uppercase text-ink/40 animate-pulse">
                    Loading campaigns...
                  </td>
                </tr>
              ) : campaigns.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-24 text-center">
                    <span className="material-symbols-outlined text-[48px] text-ink/20 block mb-3">campaign</span>
                    <p className="font-mono text-xs uppercase text-ink/40">No campaigns yet</p>
                    <p className="font-mono text-[10px] text-ink/30 mt-1">Create your first drip sequence above</p>
                  </td>
                </tr>
              ) : campaigns.map((c, i) => (
                <tr key={c.campaign_id}
                  className={`border-b border-ink hover:bg-mute transition-colors group ${i % 2 === 0 ? "bg-paper" : "bg-paper"}`}>
                  <td className="px-6 py-4">
                    <button onClick={() => setDetailTarget(c)} className="text-left group-hover:text-primary transition-colors">
                      <p className="font-display font-bold text-sm">{c.name}</p>
                      <p className="font-mono text-[10px] text-ink/40 uppercase mt-0.5">{c.campaign_id}</p>
                    </button>
                  </td>
                  <td className="px-6 py-4"><StatusBadge status={c.status} /></td>
                  <td className="px-6 py-4">
                    <span className="font-display font-bold text-lg">{c.steps?.length ?? 0}</span>
                    <span className="font-mono text-[10px] text-ink/40 ml-1 uppercase">steps</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="font-display font-bold text-lg">{c.enrolled_count ?? 0}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="font-display font-bold text-lg text-data-green">{c.completed_count ?? 0}</span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      <button onClick={() => setEnrollTarget(c)}
                        className="border border-ink px-3 py-1 font-mono text-[10px] uppercase hover:bg-ink hover:text-paper transition-colors">
                        Enroll
                      </button>
                      <button onClick={() => togglePause(c)}
                        className="border border-ink px-3 py-1 font-mono text-[10px] uppercase hover:bg-mute transition-colors">
                        {c.status === "active" ? "Pause" : "Resume"}
                      </button>
                      <button onClick={() => deleteCampaign(c)}
                        className="border border-primary px-3 py-1 font-mono text-[10px] uppercase text-primary hover:bg-primary hover:text-paper transition-colors">
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modals */}
      {showCreate && (
        <CreateCampaignModal
          onClose={() => setShowCreate(false)}
          onCreated={() => { fetchCampaigns(); showToast("Campaign created!"); }}
        />
      )}
      {enrollTarget && (
        <EnrollModal
          campaign={enrollTarget}
          onClose={() => setEnrollTarget(null)}
          onEnrolled={(d) => { showToast(`Enrolled ${d.enrolled} leads`); fetchCampaigns(); }}
        />
      )}
      {detailTarget && (
        <CampaignDetail campaign={detailTarget} onClose={() => setDetailTarget(null)} />
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
