"use client";
import { useState, useEffect, useCallback } from "react";
import DashboardLayout from "../../components/DashboardLayout";

const API = "http://localhost:8000/api";
const FALLBACK_PHONE = "+917777039470";
const token = () => (typeof window !== "undefined" ? localStorage.getItem("access_token") : "");
const hdrs = () => ({ "Content-Type": "application/json", Authorization: "Bearer " + token() });

const CHANNELS = [
    {
        id: "sms",
        label: "SMS",
        icon: "sms",
        color: "#10B981",
        bgClass: "bg-emerald-50",
        borderClass: "border-emerald-500",
        textClass: "text-emerald-700",
        badgeClass: "bg-emerald-100 text-emerald-700",
        desc: "160-char personalized SMS per lead",
        limitNote: "Max 160 chars",
    },
    {
        id: "whatsapp",
        label: "WhatsApp",
        icon: "chat",
        color: "#22C55E",
        bgClass: "bg-teal-50",
        borderClass: "border-teal-500",
        textClass: "text-teal-700",
        badgeClass: "bg-teal-100 text-teal-700",
        desc: "Rich conversational WhatsApp message",
        limitNote: "Conversational tone",
    },
    {
        id: "voice",
        label: "AI Voice Call",
        icon: "record_voice_over",
        color: "#3B82F6",
        bgClass: "bg-blue-50",
        borderClass: "border-blue-500",
        textClass: "text-blue-700",
        badgeClass: "bg-blue-100 text-blue-700",
        desc: "30-sec Twilio voice script, read by AI",
        limitNote: "~30 seconds",
    },
];

export default function ChannelsPage() {
    const [activeChannel, setActiveChannel] = useState("sms");
    const [queue, setQueue]         = useState([]);
    const [logs, setLogs]           = useState([]);
    const [loading, setLoading]     = useState(false);
    const [generating, setGenerating] = useState(false);
    const [approving, setApproving] = useState(false);
    const [selected, setSelected]   = useState(new Set());
    const [editingId, setEditingId] = useState(null);
    const [editText, setEditText]   = useState("");
    const [templateHint, setTemplateHint] = useState("");
    const [activeView, setActiveView] = useState("queue"); // queue | logs | settings
    const [toast, setToast]         = useState(null);
    const [twilioOk, setTwilioOk]   = useState(false);
    const [settings, setSettings]   = useState({
        twilio_account_sid: "", twilio_auth_token: "",
        twilio_phone_number: "", twilio_whatsapp_number: ""
    });
    const [savingSettings, setSavingSettings] = useState(false);

    const ch = CHANNELS.find(c => c.id === activeChannel);

    const showToast = (msg, err = false) => {
        setToast({ msg, err });
        setTimeout(() => setToast(null), 4000);
    };

    // ── Load queue ────────────────────────────────────────────────────────────
    const loadQueue = useCallback(async () => {
        setLoading(true);
        setSelected(new Set());
        try {
            const r = await fetch(API + "/channels/queue?channel=" + activeChannel + "&status=pending", { headers: hdrs() });
            if (r.ok) setQueue((await r.json()).items || []);
        } finally { setLoading(false); }
    }, [activeChannel]);

    const loadLogs = useCallback(async () => {
        try {
            const r = await fetch(API + "/channels/logs?channel=" + activeChannel, { headers: hdrs() });
            if (r.ok) setLogs((await r.json()).logs || []);
        } catch (e) { console.error(e); }
    }, [activeChannel]);

    const checkSettings = useCallback(async () => {
        try {
            const r = await fetch(API + "/channels/settings", { headers: hdrs() });
            if (r.ok) {
                const d = await r.json();
                setTwilioOk(d.configured);
                if (d.configured && d.settings) setSettings(s => ({ ...s, ...d.settings }));
            }
        } catch (e) { console.error(e); }
    }, []);

    useEffect(() => {
        loadQueue();
        loadLogs();
        checkSettings();
    }, [loadQueue, loadLogs, checkSettings]);

    // ── Generate AI queue ─────────────────────────────────────────────────────
    const handleGenerate = async () => {
        setGenerating(true);
        try {
            const r = await fetch(API + "/channels/generate-queue", {
                method: "POST", headers: hdrs(),
                body: JSON.stringify({ channel: activeChannel, template_hint: templateHint })
            });
            if (r.ok) {
                const d = await r.json();
                showToast("AI generated " + d.generated + " drafts for " + activeChannel.toUpperCase());
                loadQueue();
            } else {
                showToast("Generation failed — check backend logs.", true);
            }
        } finally { setGenerating(false); }
    };

    // ── Selection ──────────────────────────────────────────────────────────────
    const toggleItem = (id) => {
        setSelected(prev => {
            const next = new Set(prev);
            next.has(id) ? next.delete(id) : next.add(id);
            return next;
        });
    };
    const toggleAll = () => {
        if (selected.size === queue.length) setSelected(new Set());
        else setSelected(new Set(queue.map(i => i.id)));
    };

    // ── Bulk approve ──────────────────────────────────────────────────────────
    const handleApprove = async () => {
        if (selected.size === 0) return;
        setApproving(true);
        try {
            const r = await fetch(API + "/channels/approve", {
                method: "POST", headers: hdrs(),
                body: JSON.stringify({ item_ids: [...selected] })
            });
            if (r.ok) {
                const d = await r.json();
                showToast(d.sent + " message(s) sent!" + (d.failed > 0 ? (" " + d.failed + " failed.") : ""), d.failed > 0);
                loadQueue();
                loadLogs();
            } else {
                showToast("Approval failed.", true);
            }
        } finally { setApproving(false); }
    };

    // ── Discard draft ─────────────────────────────────────────────────────────
    const handleDiscard = async (id) => {
        await fetch(API + "/channels/queue/" + id, { method: "DELETE", headers: hdrs() });
        setQueue(prev => prev.filter(i => i.id !== id));
        showToast("Draft discarded.");
    };

    // ── Edit draft ────────────────────────────────────────────────────────────
    const startEdit = (item) => { setEditingId(item.id); setEditText(item.draft); };
    const saveEdit = async () => {
        await fetch(API + "/channels/queue/" + editingId + "/edit", {
            method: "PATCH", headers: hdrs(), body: JSON.stringify({ draft: editText })
        });
        setQueue(prev => prev.map(i => i.id === editingId ? { ...i, draft: editText, edited: true } : i));
        setEditingId(null);
    };

    // ── Save Twilio settings ──────────────────────────────────────────────────
    const saveSettings = async (e) => {
        e.preventDefault();
        setSavingSettings(true);
        try {
            const r = await fetch(API + "/channels/settings", {
                method: "POST", headers: hdrs(), body: JSON.stringify(settings)
            });
            if (r.ok) { setTwilioOk(true); showToast("Twilio settings saved."); }
        } finally { setSavingSettings(false); }
    };

    const pendingCount = queue.length;

    return (
        <DashboardLayout>
            <div className="font-mono text-ink max-w-7xl mx-auto py-8 px-4 sm:px-8">

                {/* Toast */}
                {toast && (
                    <div
                        className={"fixed top-6 right-6 z-50 px-5 py-3 border-2 border-ink font-mono text-xs uppercase flex flex-col gap-2 shadow-[6px_6px_0px_0px_rgba(10,10,10,1)] transition-all animate-in slide-in-from-top-2 "
                            + (toast.err ? "bg-red-50 text-red-700" : "bg-[#f93706] text-black")}
                    >
                        <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-sm">{toast.err ? "error" : "check_circle"}</span>
                            <span className="font-bold">{toast.msg}</span>
                        </div>
                        <div className="h-1 bg-black/20 w-full overflow-hidden">
                            <div className="h-full bg-black animate-progress-shrink" />
                        </div>
                    </div>
                )}

                {/* ── Header ─────────────────────────────────────────────────── */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end mb-10 border-b-4 border-ink pb-6 gap-4">
                    <div>
                        <h1 className="text-4xl font-black uppercase tracking-tighter">Outreach Queue</h1>
                        <p className="text-sm uppercase tracking-widest text-ink/60 mt-2 font-bold">AI-drafted SMS · WhatsApp · Voice — Review & Approve</p>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className={"flex items-center gap-2 px-4 py-2 border-2 text-xs font-bold uppercase tracking-widest " + (twilioOk ? "border-emerald-500 text-emerald-700 bg-emerald-50" : "border-red-500 text-red-600 bg-red-50")}>
                            <span className={"w-2 h-2 rounded-full " + (twilioOk ? "bg-emerald-500" : "bg-red-500 animate-pulse")}></span>
                            {twilioOk ? "Twilio Connected" : "Twilio Not Set"}
                        </div>
                        <button onClick={() => setActiveView(v => v === "settings" ? "queue" : "settings")}
                            className="px-4 py-2 border-2 border-ink bg-mute/30 text-xs font-bold uppercase tracking-widest hover:bg-ink hover:text-paper transition-colors flex items-center gap-1.5"
                        >
                            <span className="material-symbols-outlined text-sm">settings</span>
                            Settings
                        </button>
                    </div>
                </div>

                {/* ── Settings Panel ──────────────────────────────────────────── */}
                {activeView === "settings" && (
                    <div className="border-2 border-ink bg-paper p-8 mb-10 shadow-[8px_8px_0_0_rgba(10,10,10,1)] animate-in slide-in-from-top-2 duration-300">
                        <div className="flex items-center gap-3 mb-8">
                            <div className="w-8 h-8 bg-red-500 flex items-center justify-center">
                                <span className="material-symbols-outlined text-paper text-sm">phone</span>
                            </div>
                            <div>
                                <h2 className="font-bold text-lg uppercase tracking-widest">Twilio API Configuration</h2>
                                <p className="text-xs text-ink/50 uppercase tracking-widest">Required for sending SMS, WhatsApp & Voice</p>
                            </div>
                        </div>
                        <div className="p-4 border-2 border-amber-400 bg-amber-50 mb-8">
                            <p className="text-xs text-amber-800 uppercase tracking-wide">
                                Get your credentials from{" "}
                                <a href="https://console.twilio.com" target="_blank" rel="noopener noreferrer" className="underline font-bold">console.twilio.com</a>{" "}
                                → Account Info. For WhatsApp: enable Twilio Sandbox or submit for Business approval.
                            </p>
                        </div>
                        <form onSubmit={saveSettings} className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {[
                                { label: "Account SID", key: "twilio_account_sid", type: "text", ph: "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" },
                                { label: "Auth Token", key: "twilio_auth_token", type: "password", ph: "Your Auth Token" },
                                { label: "Phone Number (E.164)", key: "twilio_phone_number", type: "text", ph: "+15551234567" },
                                { label: "WhatsApp Sender", key: "twilio_whatsapp_number", type: "text", ph: "whatsapp:+14155238886" },
                            ].map(f => (
                                <div key={f.key}>
                                    <label className="text-[10px] font-bold uppercase tracking-widest text-ink/60 block mb-1.5">{f.label}</label>
                                    <input type={f.type} value={settings[f.key]} placeholder={f.ph}
                                        onChange={e => setSettings(s => ({ ...s, [f.key]: e.target.value }))}
                                        className="w-full px-3 py-2.5 border-2 border-ink bg-mute/30 text-sm font-mono focus:outline-none focus:border-primary"
                                    />
                                </div>
                            ))}
                            <div className="md:col-span-2 flex justify-end gap-3">
                                <button type="button" onClick={() => setActiveView("queue")}
                                    className="px-5 py-2.5 border-2 border-ink text-xs font-bold uppercase tracking-widest hover:bg-mute/40 transition-colors">Cancel</button>
                                <button type="submit" disabled={savingSettings}
                                    className="px-6 py-2.5 bg-ink text-paper text-xs font-bold uppercase tracking-widest hover:bg-primary hover:text-ink transition-colors disabled:opacity-50">
                                    {savingSettings ? "Saving..." : "Save Twilio Settings"}
                                </button>
                            </div>
                        </form>
                    </div>
                )}

                {/* ── Channel Tabs ──────────────────────────────────────────── */}
                <div className="flex border-b-2 border-ink mb-8">
                    {CHANNELS.map(c => (
                        <button key={c.id} onClick={() => setActiveChannel(c.id)}
                            className={"px-6 py-4 text-xs font-bold uppercase tracking-widest border-b-4 transition-colors flex items-center gap-2.5 " + (activeChannel === c.id ? "border-ink text-ink bg-mute/20" : "border-transparent text-ink/40 hover:text-ink/70")}
                        >
                            <span className="material-symbols-outlined text-lg">{c.icon}</span>
                            {c.label}
                            {activeChannel === c.id && pendingCount > 0 && (
                                <span className="ml-1 px-2 py-0.5 bg-primary text-ink text-[9px] font-bold border border-ink">{pendingCount}</span>
                            )}
                        </button>
                    ))}
                    <div className="ml-auto flex items-center gap-3 pr-2">
                        {["queue", "logs"].map(v => (
                            <button key={v} onClick={() => setActiveView(v)}
                                className={"px-4 py-2 text-[10px] font-bold uppercase tracking-widest border-2 transition-colors " + (activeView === v ? "border-ink bg-ink text-paper" : "border-ink/30 text-ink/50 hover:border-ink hover:text-ink")}
                            >
                                {v === "queue" ? "Pending Queue" : "Sent Log"}
                            </button>
                        ))}
                    </div>
                </div>

                {activeView !== "settings" && (
                    <>
                        {/* ── Channel description + Generate bar ─────────────── */}
                        <div className={"border-2 p-6 mb-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 " + ch.borderClass + " " + ch.bgClass}>
                            <div className="flex items-start gap-4">
                                <span className={"material-symbols-outlined text-3xl " + ch.textClass}>{ch.icon}</span>
                                <div>
                                    <h3 className={"text-sm font-black uppercase tracking-widest " + ch.textClass}>{ch.label} Outreach</h3>
                                    <p className="text-xs text-ink/60 mt-1">{ch.desc} · <span className="font-bold">{ch.limitNote}</span></p>
                                    <p className="text-[10px] text-ink/40 mt-1 uppercase tracking-widest">AI personalizes each message using lead intent score, pages visited & behavioral signals</p>
                                </div>
                            </div>
                            <div className="flex flex-col gap-3 w-full md:w-auto md:min-w-[320px]">
                                <div>
                                    <label className="text-[10px] font-bold uppercase tracking-widest text-ink/60 block mb-1">Template Hint (optional)</label>
                                    <input value={templateHint} onChange={e => setTemplateHint(e.target.value)}
                                        placeholder={activeChannel === "sms" ? "e.g. Mention pricing page visit" : activeChannel === "whatsapp" ? "e.g. Offer free trial call" : "e.g. Intro call about automation ROI"}
                                        className="w-full px-3 py-2 border-2 border-ink/30 bg-white/70 text-xs font-mono focus:outline-none focus:border-ink"
                                    />
                                </div>
                                <button onClick={handleGenerate} disabled={generating}
                                    className="w-full py-3 bg-ink text-paper font-bold uppercase tracking-widest text-xs hover:bg-primary hover:text-ink transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                                >
                                    <span className="material-symbols-outlined text-sm">{generating ? "hourglass_top" : "auto_awesome"}</span>
                                    {generating ? "AI Drafting Personalized Messages..." : "Generate AI Drafts for All Leads"}
                                </button>
                            </div>
                        </div>

                        {/* ── PENDING QUEUE VIEW ────────────────────────────── */}
                        {activeView === "queue" && (
                            <>
                                {/* Bulk action bar */}
                                {queue.length > 0 && (
                                    <div className="flex items-center justify-between mb-4 bg-mute/30 border-2 border-ink px-5 py-3">
                                        <div className="flex items-center gap-4">
                                            <input type="checkbox" checked={selected.size === queue.length && queue.length > 0}
                                                onChange={toggleAll}
                                                className="w-4 h-4 accent-black cursor-pointer"
                                            />
                                            <span className="text-xs font-bold uppercase tracking-widest">
                                                {selected.size > 0 ? selected.size + " selected" : "Select all " + queue.length + " drafts"}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            {selected.size > 0 && (
                                                <button onClick={handleApprove} disabled={approving}
                                                    className={"px-6 py-2.5 font-black uppercase tracking-widest text-xs border-2 border-ink transition-all flex items-center gap-2 shadow-[4px_4px_0_0_rgba(10,10,10,1)] hover:shadow-none hover:translate-x-1 hover:translate-y-1 " + ch.bgClass + " " + ch.textClass + " disabled:opacity-50"}
                                                >
                                                    <span className="material-symbols-outlined text-sm">{activeChannel === "voice" ? "call" : "send"}</span>
                                                    {approving ? "Sending..." : "Approve & Send " + selected.size + " " + ch.label}
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                )}

                                {/* Queue items */}
                                {loading ? (
                                    <div className="text-center py-16 text-xs uppercase tracking-widest text-ink/40 animate-pulse">Loading queue...</div>
                                ) : queue.length === 0 ? (
                                    <div className="border-2 border-dashed border-ink/20 py-20 text-center">
                                        <span className="material-symbols-outlined text-5xl text-ink/20">{ch.icon}</span>
                                        <p className="text-sm font-bold uppercase tracking-widest text-ink/40 mt-4">No pending {ch.label} drafts</p>
                                        <p className="text-xs text-ink/30 mt-2">Click "Generate AI Drafts for All Leads" to create personalized messages</p>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        {queue.map(item => (
                                            <div key={item.id}
                                                className={"border-2 p-5 transition-all " + (selected.has(item.id) ? "border-ink bg-primary/5 shadow-[4px_4px_0_0_rgba(10,10,10,1)]" : "border-ink/40 bg-paper hover:border-ink")}
                                            >
                                                {editingId === item.id ? (
                                                    /* ── Edit mode ── */
                                                    <div className="space-y-3">
                                                        <div className="flex items-center gap-3 mb-3">
                                                            <span className="font-bold text-sm uppercase">{item.lead_name}</span>
                                                            <span className="text-xs text-ink/50">{item.lead_company}</span>
                                                            <span className="text-xs text-ink/40">{item.lead_phone}</span>
                                                        </div>
                                                        <textarea value={editText} onChange={e => setEditText(e.target.value)} rows={4}
                                                            className="w-full px-3 py-2.5 border-2 border-ink bg-mute/20 text-sm font-mono focus:outline-none focus:border-primary resize-none"
                                                        />
                                                        {activeChannel === "sms" && (
                                                            <p className={"text-right text-[10px] font-bold " + (editText.length > 160 ? "text-red-500" : "text-ink/40")}>{editText.length}/160</p>
                                                        )}
                                                        <div className="flex gap-3">
                                                            <button onClick={saveEdit} className="px-4 py-2 bg-ink text-paper text-xs font-bold uppercase tracking-widest hover:bg-primary hover:text-ink transition-colors">Save Edit</button>
                                                            <button onClick={() => setEditingId(null)} className="px-4 py-2 border-2 border-ink text-xs font-bold uppercase tracking-widest hover:bg-mute/40 transition-colors">Cancel</button>
                                                        </div>
                                                    </div>
                                                ) : (
                                                    /* ── Normal mode ── */
                                                    <div className="flex items-start gap-4">
                                                        <input type="checkbox" checked={selected.has(item.id)} onChange={() => toggleItem(item.id)}
                                                            className="mt-1 w-4 h-4 accent-black cursor-pointer shrink-0"
                                                        />
                                                        <div className="flex-1 min-w-0">
                                                            {/* Lead info */}
                                                            <div className="flex items-center gap-3 flex-wrap mb-3">
                                                                <div className="w-8 h-8 bg-ink flex items-center justify-center text-paper text-xs font-black shrink-0">
                                                                    {item.lead_name ? item.lead_name[0].toUpperCase() : "?"}
                                                                </div>
                                                                <div>
                                                                    <span className="font-bold text-sm uppercase">{item.lead_name}</span>
                                                                    <span className="text-xs text-ink/50 ml-2">{item.lead_company}</span>
                                                                </div>
                                                                <span className="text-[10px] font-mono text-ink/50 bg-mute/40 px-2 py-0.5">
                                                                    {item.lead_phone}
                                                                </span>
                                                                <div className={"px-2 py-0.5 text-[9px] font-bold uppercase border " + (item.intent_score >= 70 ? "border-emerald-400 bg-emerald-50 text-emerald-700" : item.intent_score >= 40 ? "border-amber-400 bg-amber-50 text-amber-700" : "border-ink/20 text-ink/50")}>
                                                                    Score {item.intent_score}
                                                                </div>
                                                                {item.source && <span className="px-2 py-0.5 text-[9px] font-bold uppercase bg-mute/30 text-ink/50 border border-ink/10">{item.source}</span>}
                                                                {item.edited && <span className="px-2 py-0.5 text-[9px] font-bold uppercase bg-amber-100 text-amber-700 border border-amber-300">EDITED</span>}
                                                            </div>

                                                            {/* Draft message */}
                                                            <div className={"px-4 py-3 border-l-4 bg-mute/20 text-sm leading-relaxed font-mono " + ch.borderClass}>
                                                                {item.draft}
                                                            </div>
                                                            {activeChannel === "sms" && (
                                                                <p className={"text-[10px] mt-1 text-right " + (item.draft?.length > 160 ? "text-red-500 font-bold" : "text-ink/30")}>
                                                                    {item.draft?.length || 0}/160 chars
                                                                </p>
                                                            )}
                                                        </div>

                                                        {/* Action buttons */}
                                                        <div className="flex flex-col gap-2 shrink-0">
                                                            <button onClick={() => startEdit(item)}
                                                                className="px-3 py-1.5 border-2 border-ink/40 text-[10px] font-bold uppercase tracking-widest hover:border-ink hover:bg-mute/30 transition-colors flex items-center gap-1"
                                                            >
                                                                <span className="material-symbols-outlined text-sm">edit</span>
                                                                Edit
                                                            </button>
                                                            <button onClick={() => handleDiscard(item.id)}
                                                                className="px-3 py-1.5 border-2 border-red-200 text-red-500 text-[10px] font-bold uppercase tracking-widest hover:border-red-500 hover:bg-red-50 transition-colors flex items-center gap-1"
                                                            >
                                                                <span className="material-symbols-outlined text-sm">delete_outline</span>
                                                                Discard
                                                            </button>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {/* Bottom sticky approve bar */}
                                {selected.size > 0 && (
                                    <div className="fixed bottom-0 left-0 right-0 z-40 bg-ink text-paper px-8 py-4 flex items-center justify-between shadow-2xl">
                                        <div className="flex items-center gap-4">
                                            <span className="material-symbols-outlined text-primary text-xl">{ch.icon}</span>
                                            <span className="font-bold uppercase tracking-widest text-sm">{selected.size} {ch.label} message{selected.size !== 1 ? "s" : ""} ready to send</span>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <button onClick={() => setSelected(new Set())} className="text-paper/60 text-xs uppercase tracking-widest hover:text-paper transition-colors">
                                                Clear Selection
                                            </button>
                                            <button onClick={handleApprove} disabled={approving}
                                                className="px-8 py-3 bg-primary text-ink font-black uppercase tracking-widest text-sm hover:bg-white hover:text-ink transition-colors disabled:opacity-50 flex items-center gap-2"
                                            >
                                                <span className="material-symbols-outlined text-base">{activeChannel === "voice" ? "call" : "send"}</span>
                                                {approving ? "Sending..." : "Approve & Send All " + selected.size}
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </>
                        )}

                        {/* ── LOGS VIEW ─────────────────────────────────────── */}
                        {activeView === "logs" && (
                            <div className="border-2 border-ink overflow-hidden">
                                <div className="border-b-2 border-ink bg-mute/20 p-4">
                                    <h3 className="text-xs font-bold uppercase tracking-widest flex items-center gap-2">
                                        <span className="material-symbols-outlined text-sm">history</span>
                                        Sent {ch.label} History
                                    </h3>
                                </div>
                                {logs.length === 0 ? (
                                    <div className="py-16 text-center">
                                        <span className="material-symbols-outlined text-4xl text-ink/20">history</span>
                                        <p className="text-xs uppercase tracking-widest text-ink/40 mt-3">No {ch.label} messages sent yet</p>
                                    </div>
                                ) : (
                                    <div className="divide-y divide-ink/10">
                                        {logs.map(log => (
                                            <div key={log.id} className="p-5 flex items-start gap-4 hover:bg-mute/20 transition-colors">
                                                <span className={"material-symbols-outlined text-xl " + ch.textClass}>{ch.icon}</span>
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-xs font-bold uppercase tracking-widest">{log.lead_id}</p>
                                                    <p className="text-sm text-ink/70 mt-1 leading-relaxed">{log.summary}</p>
                                                    <p className="text-[10px] text-ink/40 mt-1.5">{log.timestamp ? new Date(log.timestamp).toLocaleString() : ""}</p>
                                                </div>
                                                <span className="px-2 py-1 text-[9px] font-bold uppercase border border-emerald-400 bg-emerald-50 text-emerald-700 shrink-0">SENT</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </>
                )}

                {/* Bottom padding for sticky bar */}
                {selected.size > 0 && <div className="h-20" />}
            </div>
        </DashboardLayout>
    );
}
