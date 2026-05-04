"use client";
import { useState, useEffect, useCallback } from "react";
import DashboardLayout from "../../components/DashboardLayout";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const token = () => (typeof window !== "undefined" ? localStorage.getItem("access_token") : "");
const hdrs = () => ({ "Content-Type": "application/json", Authorization: "Bearer " + token() });

export default function ChatbotPage() {
    const [sessions, setSessions]   = useState([]);
    const [loading, setLoading]     = useState(true);
    const [selected, setSelected]   = useState(null); // session object
    const [history, setHistory]     = useState([]);
    const [histLoading, setHistLoading] = useState(false);
    const [apiKeys, setApiKeys]     = useState([]);
    const [activeTab, setActiveTab] = useState("sessions"); // sessions | embed
    const [copied, setCopied]       = useState(false);

    const loadSessions = useCallback(async () => {
        setLoading(true);
        try {
            const r = await fetch(API + "/chat/sessions", { headers: hdrs() });
            if (r.ok) setSessions((await r.json()).sessions || []);
        } finally { setLoading(false); }
    }, []);

    const loadApiKeys = useCallback(async () => {
        try {
            const r = await fetch(API + "/api-keys/list", { headers: hdrs() });
            if (r.ok) setApiKeys((await r.json()).keys || []);
        } catch (e) { console.error(e); }
    }, []);

    useEffect(() => {
        loadSessions();
        loadApiKeys();
    }, [loadSessions, loadApiKeys]);

    const loadHistory = async (session) => {
        setSelected(session);
        setHistLoading(true);
        try {
            const r = await fetch(API + "/chat/history/" + session.session_id, { headers: hdrs() });
            if (r.ok) setHistory((await r.json()).messages || []);
        } finally { setHistLoading(false); }
    };

    const firstKey = apiKeys[0];
    const apiHost  = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").replace("/api", "");

    const embedSnippet = firstKey
        ? `<script\n  src="${apiHost}/public/sdk/chatbot-widget.js"\n  data-api-key="${firstKey.key}"\n  data-api-host="${apiHost}"\n  data-title="Chat with us"\n  data-color="#7C3AED"\n  async>\n</script>`
        : "// Generate an API key in Settings → Integrations first";

    const copyEmbed = () => {
        navigator.clipboard.writeText(embedSnippet);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const leadsViaChat = sessions.filter(s => s.lead_created).length;
    const totalMsgs    = sessions.reduce((acc, s) => acc + (s.message_count || 0), 0);

    return (
        <DashboardLayout>
            <div className="font-mono text-ink max-w-7xl mx-auto py-8 px-4 sm:px-8">

                {/* Header */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end mb-10 border-b-4 border-ink pb-6 gap-4">
                    <div>
                        <h1 className="text-4xl font-black uppercase tracking-tighter">AI Chatbot</h1>
                        <p className="text-sm uppercase tracking-widest text-ink/60 mt-2 font-bold">Visitor Conversations & Lead Capture</p>
                    </div>
                    <div className="flex gap-3">
                        {["sessions", "embed"].map(t => (
                            <button key={t} onClick={() => setActiveTab(t)}
                                className={"px-5 py-2.5 border-2 border-ink text-xs font-bold uppercase tracking-widest transition-colors " + (activeTab === t ? "bg-ink text-paper" : "bg-paper hover:bg-mute/40")}
                            >
                                {t === "sessions" ? "Chat Sessions" : "Embed Code"}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-10">
                    {[
                        { label: "Total Sessions",  val: sessions.length,  icon: "forum" },
                        { label: "Leads Captured",  val: leadsViaChat,     icon: "person_add", accent: true },
                        { label: "Total Messages",  val: totalMsgs,        icon: "chat" },
                    ].map(s => (
                        <div key={s.label} className={"border-2 border-ink p-5 flex flex-col gap-1 " + (s.accent && leadsViaChat > 0 ? "bg-primary/10 border-primary" : "bg-paper")}>
                            <span className={"material-symbols-outlined text-2xl " + (s.accent && leadsViaChat > 0 ? "text-primary" : "text-ink/40")}>{s.icon}</span>
                            <div className="text-3xl font-black">{s.val}</div>
                            <div className="text-[10px] uppercase tracking-widest text-ink/60">{s.label}</div>
                        </div>
                    ))}
                </div>

                {/* ── Embed Code Tab ── */}
                {activeTab === "embed" && (
                    <div className="border-2 border-ink overflow-hidden shadow-[8px_8px_0_0_rgba(10,10,10,1)]">
                        <div className="bg-ink px-6 py-4 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <span className="material-symbols-outlined text-primary text-lg">integration_instructions</span>
                                <span className="font-bold text-sm uppercase tracking-widest text-paper">Chatbot Widget Installation</span>
                            </div>
                            <button onClick={copyEmbed}
                                className="px-4 py-1.5 border border-primary/40 bg-primary/20 text-primary font-mono text-[10px] font-bold uppercase tracking-widest hover:bg-primary hover:text-ink transition-colors flex items-center gap-2"
                            >
                                <span className="material-symbols-outlined text-sm">{copied ? "check" : "content_copy"}</span>
                                {copied ? "Copied!" : "Copy"}
                            </button>
                        </div>
                        <div className="p-8 bg-[#111]">
                            <p className="font-mono text-xs text-paper/60 uppercase tracking-wide mb-6 leading-relaxed">
                                Paste this snippet in the <span className="text-primary font-bold">&lt;body&gt;</span> tag of your website. The chatbot bubble will appear automatically and begin capturing visitor conversations.
                            </p>

                            {/* Visual preview */}
                            <div className="mb-8 p-6 border border-paper/10 bg-[#1a1a2e] relative overflow-hidden">
                                <p className="font-mono text-[10px] text-paper/40 uppercase tracking-widest mb-4">Widget Preview</p>
                                <div className="flex items-end justify-end">
                                    <div className="w-14 h-14 rounded-full bg-[#7C3AED] flex items-center justify-center shadow-xl border-2 border-white/20 cursor-pointer hover:scale-105 transition-transform">
                                        <svg viewBox="0 0 24 24" className="w-7 h-7 fill-white">
                                            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
                                        </svg>
                                    </div>
                                </div>
                                <p className="font-mono text-[10px] text-paper/30 mt-3 text-right uppercase tracking-widest">Chat with us · Powered by LeadMind AI</p>
                            </div>

                            <pre className="p-5 bg-[#0a0a0a] border-l-4 border-primary overflow-x-auto text-xs font-mono text-emerald-400 leading-relaxed select-all">
                                {embedSnippet}
                            </pre>

                            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
                                {[
                                    { icon: "chat_bubble", title: "Multi-turn AI", desc: "Full conversation context maintained across the session." },
                                    { icon: "person_add", title: "Auto Lead Capture", desc: "Automatically creates a lead when email is collected." },
                                    { icon: "devices", title: "Any Platform", desc: "Works on HTML, WordPress, Shopify, Webflow, and more." },
                                ].map(f => (
                                    <div key={f.title} className="p-4 border border-paper/10 bg-paper/5">
                                        <span className="material-symbols-outlined text-primary text-lg mb-2 block">{f.icon}</span>
                                        <p className="font-mono text-xs font-bold uppercase text-paper mb-1">{f.title}</p>
                                        <p className="font-mono text-[10px] text-paper/50 leading-relaxed">{f.desc}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {/* ── Sessions Tab ── */}
                {activeTab === "sessions" && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                        {/* Sessions list */}
                        <div className="border-2 border-ink overflow-hidden">
                            <div className="border-b-2 border-ink bg-mute/20 p-4">
                                <h3 className="text-xs font-bold uppercase tracking-widest flex items-center gap-2">
                                    <span className="material-symbols-outlined text-sm">forum</span>
                                    Chat Sessions
                                </h3>
                            </div>
                            {loading ? (
                                <div className="p-8 text-center text-xs uppercase tracking-widest text-ink/40 animate-pulse">Loading sessions...</div>
                            ) : sessions.length === 0 ? (
                                <div className="p-8 text-center">
                                    <span className="material-symbols-outlined text-4xl text-ink/20">chat_bubble_outline</span>
                                    <p className="text-xs uppercase tracking-widest text-ink/40 mt-3">No conversations yet.<br/>Install the widget to start capturing leads.</p>
                                </div>
                            ) : (
                                <div className="divide-y divide-ink/10 max-h-[600px] overflow-y-auto">
                                    {sessions.map(s => (
                                        <button key={s.session_id} onClick={() => loadHistory(s)}
                                            className={"w-full text-left p-4 hover:bg-mute/30 transition-colors flex items-start gap-3 " + (selected?.session_id === s.session_id ? "bg-primary/10 border-l-4 border-primary" : "")}
                                        >
                                            <div className={"w-9 h-9 shrink-0 flex items-center justify-center border-2 border-ink font-bold text-sm " + (s.lead_created ? "bg-primary text-ink" : "bg-mute text-ink/60")}>
                                                {s.captured_name ? s.captured_name[0].toUpperCase() : "?"}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-bold text-xs uppercase">{s.captured_name || "Anonymous Visitor"}</span>
                                                    {s.lead_created && <span className="px-1.5 py-0.5 bg-primary/20 text-ink text-[9px] font-bold uppercase border border-primary/30">LEAD</span>}
                                                </div>
                                                <p className="text-[10px] text-ink/50 mt-0.5 truncate">{s.captured_email || s.session_id}</p>
                                                <p className="text-[10px] text-ink/40">{s.created_at ? new Date(s.created_at).toLocaleDateString() : ""}</p>
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Message history */}
                        <div className="border-2 border-ink overflow-hidden flex flex-col">
                            <div className="border-b-2 border-ink bg-mute/20 p-4 flex justify-between items-center">
                                <h3 className="text-xs font-bold uppercase tracking-widest flex items-center gap-2">
                                    <span className="material-symbols-outlined text-sm">chat</span>
                                    {selected ? (selected.captured_name || "Anonymous") + " — Conversation" : "Select a session"}
                                </h3>
                                {selected?.lead_created && (
                                    <span className="px-3 py-1 bg-primary/20 border border-primary/30 font-mono text-[10px] font-bold uppercase tracking-widest text-ink">Lead Captured</span>
                                )}
                            </div>
                            <div className="flex-1 p-4 overflow-y-auto max-h-[500px] space-y-3 bg-[#f8f8ff]">
                                {!selected && (
                                    <div className="h-full flex items-center justify-center">
                                        <p className="text-xs uppercase tracking-widest text-ink/30">Select a session on the left</p>
                                    </div>
                                )}
                                {histLoading && (
                                    <div className="text-center text-xs uppercase tracking-widest text-ink/40 animate-pulse pt-8">Loading messages...</div>
                                )}
                                {!histLoading && history.map((m, i) => (
                                    <div key={i} className={"flex " + (m.role === "user" ? "justify-end" : "justify-start")}>
                                        <div className={"max-w-[80%] px-4 py-2.5 text-[13px] leading-relaxed " + (m.role === "user"
                                            ? "bg-[#7C3AED] text-white rounded-xl rounded-br-sm"
                                            : "bg-white border border-gray-200 text-gray-800 rounded-xl rounded-bl-sm shadow-sm"
                                        )}>
                                            {m.content}
                                            <p className={"text-[10px] mt-1 " + (m.role === "user" ? "text-white/60" : "text-gray-400")}>
                                                {m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : ""}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </DashboardLayout>
    );
}
