"use client";
import DashboardLayout from "../../components/DashboardLayout";
import { useState, useEffect, useRef, Suspense } from "react";
import { fetchLeads } from "../../api/leads";
import { LedgerTable } from "../../components/LedgerTable";
import { useBatchProgress } from "../../hooks/useBatchProgress";
import { useSearchParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// ── Live Bulk Progress Modal ───────────────────────────────────────────────────
// All state lives in the PARENT (LedgerView) to avoid React 18 Strict Mode
// double-invoking useEffect. The modal is display-only.
function BulkProgressModal({ total, results, currentLead, done, onClose }) {
    const logRef = useRef(null);

    // Auto-scroll log to bottom on new results
    useEffect(() => {
        if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
    }, [results.length]);

    const sent = results.filter(r => r.result === "sent").length;
    const skipped = results.filter(r => r.result === "skipped").length;
    const failed = results.filter(r => r.result === "failed").length;
    const progress = total > 0 ? Math.round((results.length / total) * 100) : 0;

    const resultIcon = (r) => {
        if (r === "sent") return <span className="text-data-green font-bold">✓ SENT</span>;
        if (r === "skipped") return <span className="text-amber-500 font-bold">⏭ SKIPPED</span>;
        return <span className="text-red-500 font-bold">✕ FAILED</span>;
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-ink/70 backdrop-blur-sm" />

            {/* Modal */}
            <div className="relative z-10 w-full max-w-xl bg-paper border-2 border-ink shadow-[8px_8px_0px_0px_rgba(10,10,10,1)] mx-4">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 bg-ink text-paper">
                    <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-primary text-xl">send</span>
                        <div>
                            <h2 className="font-mono font-bold text-sm uppercase tracking-widest">Multi-Channel Dispatch</h2>
                            <p className="font-mono text-[10px] text-paper/50 mt-0.5">{total} leads queued</p>
                        </div>
            </div>
                    {/* Always-visible close button */}
                    <button
                        onClick={onClose}
                        className="font-mono text-[10px] uppercase border border-paper/30 px-3 py-1 hover:bg-paper/10 transition-colors flex items-center gap-1.5"
                    >
                        <span className="material-symbols-outlined text-[12px]">close</span>
                        {done ? "Close" : "Hide"}
                    </button>
                </div>

                {/* Progress bar */}
                <div className="h-1.5 bg-mute w-full overflow-hidden">
                    <div className="h-full bg-primary transition-all duration-300" style={{ width: `${progress}%` }} />
                </div>

                {/* Currently processing banner */}
                <div className="px-6 py-3 border-b border-ink/20 bg-mute min-h-[52px] flex items-center gap-3">
                    {!done && currentLead ? (
                        <>
                            <span className="w-2 h-2 rounded-full bg-primary animate-pulse shrink-0" />
                            <div className="font-mono text-xs min-w-0">
                                <span className="text-ink/50 uppercase tracking-wide">Sending → </span>
                                <span className="font-bold text-ink">{currentLead.name}</span>
                                <span className="text-ink/40"> @ {currentLead.company}</span>
                            </div>
                            <span className="ml-auto font-mono text-[10px] text-ink/40 shrink-0">
                                {results.length + 1} / {total}
                            </span>
                        </>
                    ) : done ? (
                        <div className="flex items-center gap-3 w-full font-mono text-xs">
                            <span className="material-symbols-outlined text-data-green text-base">check_circle</span>
                            <span className="font-bold text-data-green uppercase">Complete</span>
                            <span className="ml-auto text-ink/50">{sent} sent · {skipped} skipped · {failed} failed</span>
                        </div>
                    ) : (
                        <span className="font-mono text-xs text-ink/40 animate-pulse">Initialising...</span>
                    )}
                </div>

                {/* Per-lead log */}
                <div ref={logRef} className="overflow-y-auto max-h-72 divide-y divide-ink/10">
                    {results.map((r, i) => (
                        <div key={i} className="flex items-center gap-3 px-6 py-2.5 hover:bg-mute/50 transition-colors">
                            <div className="font-mono text-xs min-w-0 flex-1">
                                <span className="font-bold text-ink">{r.name}</span>
                                <span className="text-ink/40 ml-1.5">@ {r.company}</span>
                                {r.reason && <span className="block text-[10px] text-ink/40 mt-0.5">{r.reason}</span>}
                            </div>
                            <div className="font-mono text-[10px] shrink-0">{resultIcon(r.result)}</div>
                        </div>
                    ))}

                    {/* Ghost row for currently-processing lead */}
                    {!done && currentLead && (
                        <div className="flex items-center gap-3 px-6 py-2.5 bg-primary/5 animate-pulse">
                            <div className="font-mono text-xs flex-1">
                                <span className="font-bold text-ink">{currentLead.name}</span>
                                <span className="text-ink/40 ml-1.5">@ {currentLead.company}</span>
                            </div>
                            <span className="font-mono text-[10px] text-primary">SENDING...</span>
                        </div>
                    )}
                </div>

                {/* Footer summary */}
                {done && (
                    <div className="px-6 py-4 border-t border-ink bg-mute flex justify-between font-mono text-[11px]">
                        <span className="text-data-green font-bold">✓ {sent} Sent</span>
                        <span className="text-amber-500 font-bold">⏭ {skipped} Skipped</span>
                        <span className="text-red-500 font-bold">✕ {failed} Failed</span>
                    </div>
                )}
            </div>
        </div>
    );
}


// ── Ledger View ────────────────────────────────────────────────────────────────
function LedgerView() {
    const [leads, setLeads] = useState([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(true);
    const [analyzing, setAnalyzing] = useState(null);
    const [searchQuery, setSearchQuery] = useState("");
    const [minScore, setMinScore] = useState("");
    const [maxScore, setMaxScore] = useState("");

    // Bulk send state (all here — NOT inside modal, avoids React 18 double-fire)
    const [showBulkModal, setShowBulkModal] = useState(false);
    const [bulkResults, setBulkResults] = useState([]);
    const [bulkCurrentLead, setBulkCurrentLead] = useState(null);
    const [bulkDone, setBulkDone] = useState(false);
    const [bulkTotal, setBulkTotal] = useState(0);
    const bulkRunning = useRef(false);
    const [toast, setToast] = useState(null);

    const showToast = (msg, type = "success") => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 3000);
    };

    // Templates state
    const [templates, setTemplates] = useState([]);
    const [selectedTemplate, setSelectedTemplate] = useState("");

    // Channel Selection state
    const [selectedChannels, setSelectedChannels] = useState(['email']);
    const channelOptions = [
        { id: 'email', label: 'Email', icon: 'mail' },
        { id: 'sms', label: 'SMS', icon: 'sms' },
        { id: 'whatsapp', label: 'WhatsApp', icon: 'chat' },
    ];

    const searchParams = useSearchParams();
    const batchId = searchParams.get("batch");
    const progress = useBatchProgress(batchId);

    async function load(p, bId, search, min, max) {
        setLoading(true);
        try {
            const data = await fetchLeads(p, 25, {
                batchId: bId,
                search: search || undefined,
                minScore: min || undefined,
                maxScore: max || undefined
            });
            setLeads(data.data);
            setTotal(data.total);
            setPage(data.page);
        } catch (e) {
            console.error(e);
            setLeads([]);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => { load(page, batchId, searchQuery, minScore, maxScore); }, [page, batchId]);

    useEffect(() => {
        // Fetch available templates for bulk send
        const token = localStorage.getItem("access_token");
        fetch(`${API}/templates/`, { headers: { "Authorization": `Bearer ${token}` } })
            .then(res => res.json())
            .then(data => {
                const fetchedTemplates = data.templates || [];
                setTemplates(fetchedTemplates);
                if (fetchedTemplates.length > 0) {
                    setSelectedTemplate(fetchedTemplates[0]._id);
                }
            })
            .catch(err => console.error("Failed to fetch templates:", err));
    }, []);

    useEffect(() => {
        if (progress && (progress.status === "processing" || progress.status === "completed")) {
            load(page, batchId, searchQuery, minScore, maxScore);
        }
    }, [progress?.percent, progress?.status]);

    const handleApplyFilters = () => { setPage(1); load(1, batchId, searchQuery, minScore, maxScore); };
    const handleClearFilters = () => {
        setSearchQuery(""); setMinScore(""); setMaxScore(""); setPage(1);
        load(1, batchId, "", "", "");
    };

    const handleRunAgent = async (leadId) => {
        if (analyzing) return;
        setAnalyzing(leadId);
        try {
            const res = await fetch(`${API}/agents/trigger`, {
                method: "POST",
                headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("access_token")}` },
                body: JSON.stringify({ lead_id: leadId })
            });
            if (!res.ok) throw new Error("Agent failed");
            await load(page, batchId, searchQuery, minScore, maxScore);
        } catch (e) { 
            console.error(e); 
        } finally {
            setAnalyzing(null);
        }
    };

    const handleDeleteLead = async (leadId) => {
        try {
            const res = await fetch(`${API}/leads/${leadId}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` }
            });
            if (!res.ok) throw new Error("Delete failed");
            // Optimistic update
            setLeads(prev => prev.filter(l => (l.lead_id || l.id) !== leadId));
            setTotal(prev => prev - 1);
        } catch (e) {
            console.error(e);
            showToast("Failed to delete lead", "error");
        }
    };

    // ── Bulk send — runs in the click handler, NOT in useEffect ───────────────
    const handleBulkSend = async () => {
        if (bulkRunning.current) return; // prevent double-click
        bulkRunning.current = true;

        // Deduplicate by name+company
        const seen = new Set();
        const uniqueLeads = leads.filter(l => {
            const key = `${(l.name || "").toLowerCase().trim()}|${(l.company || "").toLowerCase().trim()}`;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });

        setBulkResults([]);
        setBulkCurrentLead(null);
        setBulkDone(false);
        setBulkTotal(uniqueLeads.length);
        setShowBulkModal(true);

        const token = localStorage.getItem("access_token");

        for (const lead of uniqueLeads) {
            setBulkCurrentLead(lead);
            await new Promise(r => setTimeout(r, 80)); // let UI render

            const leadId = lead.lead_id || lead.record_id;

            try {
                const res = await fetch(`${API}/leads/bulk-approve`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                    body: JSON.stringify({
                        lead_ids: [leadId],
                        template_id: selectedTemplate || null,
                        channels: selectedChannels
                    })
                });

                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    setBulkResults(prev => [...prev, { ...lead, result: "failed", reason: err.detail || "Delivery failed" }]);
                } else {
                    const data = await res.json();
                    const r = data.results?.[0];
                    if (r?.result === "skipped") {
                        setBulkResults(prev => [...prev, { ...lead, result: "skipped", reason: r.reason || "Already sent" }]);
                    } else if (r?.result === "failed") {
                        setBulkResults(prev => [...prev, { ...lead, result: "failed", reason: r.reason || "Delivery failed" }]);
                    } else {
                        setBulkResults(prev => [...prev, { ...lead, result: "sent" }]);
                    }
                }
            } catch (e) {
                setBulkResults(prev => [...prev, { ...lead, result: "failed", reason: e.message }]);
            }
        }

        setBulkCurrentLead(null);
        setBulkDone(true);
        bulkRunning.current = false;
    };

    const handleBulkClose = async () => {
        // Just hides the modal — send continues in background
        setShowBulkModal(false);
        // If fully done, reload the table
        if (bulkDone) {
            setBulkTotal(0);
            setBulkResults([]);
            setBulkDone(false);
            await load(page, batchId, searchQuery, minScore, maxScore);
        }
    };

    const totalPages = Math.ceil(total / 25);

    return (
        <div className="flex flex-col h-full bg-paper relative">
            {/* Bulk Modal — display-only, all logic in parent */}
            {showBulkModal && (
                <BulkProgressModal
                    total={bulkTotal}
                    results={bulkResults}
                    currentLead={bulkCurrentLead}
                    done={bulkDone}
                    onClose={handleBulkClose}
                />
            )}

            <header className="h-16 shrink-0 border-b border-ink flex items-center justify-between px-8 bg-paper z-10 sticky top-0">
                <div className="flex items-center gap-6">
                    <div className="flex flex-col justify-center">
                        <span className="font-mono text-[10px] text-ink/60 uppercase">Data Streamer</span>
                        <h2 className="font-display font-bold text-xl tracking-tight leading-none mt-0.5">
                            {batchId ? `BATCH [${batchId}]` : "GLOBAL LEDGER"}
                        </h2>
                    </div>
                </div>

                {/* Pagination Controls */}
                <div className="flex items-center gap-4">
                    <span className="font-mono text-xs text-ink/60 mr-4">Page {page} of {totalPages}</span>
                    <div className="flex gap-2">
                        <button disabled={page === 1} onClick={() => setPage(page - 1)} className="size-8 flex items-center justify-center border border-ink bg-paper hover:bg-mute disabled:opacity-30">
                            <span className="material-symbols-outlined text-[14px]">arrow_back</span>
                        </button>
                        <button disabled={page >= totalPages} onClick={() => setPage(page + 1)} className="size-8 flex items-center justify-center border border-ink bg-paper hover:bg-mute disabled:opacity-30">
                            <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                        </button>
                    </div>
                </div>
            </header>

            {/* Filters Toolbar */}
            <div className="bg-mute border-b border-ink px-8 py-3 flex flex-wrap items-center gap-4 z-20 relative">
                <div className="flex items-center border border-ink bg-paper px-3 h-8 w-64 focus-within:ring-1 focus-within:ring-primary">
                    <span className="material-symbols-outlined text-[16px] text-ink/50 mr-2">search</span>
                    <input
                        type="text"
                        placeholder="Search Name, Company, Title, or Score..."
                        className="bg-transparent outline-none w-full font-mono text-[10px] uppercase"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleApplyFilters()}
                    />
                </div>

                <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] uppercase text-ink/60">Intent Range:</span>
                    <select className="h-8 border border-ink bg-paper px-2 font-mono text-[10px] uppercase outline-none focus:ring-1 focus:ring-primary" value={minScore} onChange={(e) => setMinScore(e.target.value)}>
                        <option value="">Min</option>
                        <option value="0">0+</option>
                        <option value="20">20+</option>
                        <option value="40">40+</option>
                        <option value="60">60+</option>
                        <option value="80">80+</option>
                    </select>
                    <span className="text-ink/60">-</span>
                    <select className="h-8 border border-ink bg-paper px-2 font-mono text-[10px] uppercase outline-none focus:ring-1 focus:ring-primary" value={maxScore} onChange={(e) => setMaxScore(e.target.value)}>
                        <option value="">Max</option>
                        <option value="40">Under 40</option>
                        <option value="60">Under 60</option>
                        <option value="80">Under 80</option>
                        <option value="100">Under 100</option>
                    </select>
                </div>

                <div className="flex items-center gap-2 ml-auto">
                    {(searchQuery || minScore || maxScore) && (
                        <button onClick={handleClearFilters} className="h-8 px-4 font-mono text-[10px] uppercase text-ink/60 hover:text-ink hover:underline">
                            Reset
                        </button>
                    )}
                    <button onClick={handleApplyFilters} className="h-8 px-4 border border-ink bg-paper text-ink font-mono text-[10px] uppercase font-bold hover:bg-mute transition-colors">
                        Apply Filters
                    </button>

                    {/* Live bulk status pill — shown while sending or after done */}
                    {bulkTotal > 0 && !showBulkModal && (
                        <button
                            onClick={() => setShowBulkModal(true)}
                            className={`h-8 px-3 border font-mono text-[10px] uppercase font-bold flex items-center gap-1.5 transition-colors ${bulkDone
                                ? 'border-data-green/40 bg-data-green/10 text-data-green hover:bg-data-green/20'
                                : 'border-primary/40 bg-primary/10 text-primary animate-pulse hover:bg-primary/20'
                                }`}
                        >
                            <span className="material-symbols-outlined text-[13px]">
                                {bulkDone ? 'check_circle' : 'send'}
                            </span>
                            {bulkDone
                                ? `✓ Done — ${bulkResults.filter(r => r.result === 'sent').length} sent`
                                : `Sending ${bulkResults.length + 1}/${bulkTotal}...`
                            }
                        </button>
                    )}

                    {/* Channel Selector */}
                    <div className="relative group flex items-center gap-2 px-3 h-8 border border-ink bg-paper focus-within:ring-1 focus-within:ring-primary focus-within:border-primary transition-all cursor-pointer">
                        <span className="material-symbols-outlined text-ink/50 text-[14px]">cell_tower</span>
                        <span className="font-mono text-[9px] uppercase text-ink/40 font-bold">Outreach:</span>
                        <div className="flex items-center gap-1 overflow-hidden max-w-[100px]">
                            {selectedChannels.length === 0 ? (
                                <span className="font-mono text-[9px] uppercase text-red-500 font-bold">No Channels</span>
                            ) : (
                                selectedChannels.map(c => (
                                    <span key={c} className="font-mono text-[8px] uppercase font-bold bg-ink text-paper px-1 rounded-[2px] shrink-0">
                                        {c.substring(0, 1)}
                                    </span>
                                ))
                            )}
                        </div>
                        <span className="material-symbols-outlined text-ink/40 text-[12px] ml-auto">expand_more</span>
                        
                        {/* Dropdown Menu */}
                        <div className="absolute top-full right-0 mt-1 w-40 bg-paper border-2 border-ink shadow-[4px_4px_0px_0px_rgba(10,10,10,1)] z-[100] hidden group-hover:block py-1">
                            <div className="px-3 py-1.5 border-b border-ink/10 bg-mute">
                                <span className="font-mono text-[8px] uppercase font-bold text-ink/50 tracking-tighter">Select Channels</span>
                            </div>
                            {channelOptions.map(chan => (
                                <label key={chan.id} className="flex items-center gap-3 px-3 py-2 hover:bg-mute cursor-pointer transition-colors">
                                    <input 
                                        type="checkbox"
                                        checked={selectedChannels.includes(chan.id)}
                                        onChange={(e) => {
                                            if (e.target.checked) {
                                                setSelectedChannels([...selectedChannels, chan.id]);
                                            } else {
                                                setSelectedChannels(selectedChannels.filter(c => c !== chan.id));
                                            }
                                        }}
                                        className="w-3 h-3 accent-primary cursor-pointer border-2 border-ink"
                                    />
                                    <span className="material-symbols-outlined text-sm text-ink/60">{chan.icon}</span>
                                    <span className="font-mono text-[10px] uppercase font-bold text-ink">{chan.label}</span>
                                </label>
                            ))}
                        </div>
                    </div>

                    {/* Template Dropdown */}
                    <div className="flex items-center gap-2 px-3 h-8 border border-ink bg-paper focus-within:ring-1 focus-within:ring-primary focus-within:border-primary transition-all">
                        <span className="material-symbols-outlined text-ink/50 text-[14px]">view_quilt</span>
                        <select
                            value={selectedTemplate}
                            onChange={e => setSelectedTemplate(e.target.value)}
                            className="font-mono text-[10px] uppercase bg-transparent outline-none py-1 cursor-pointer text-ink appearance-none pr-4"
                            style={{ backgroundImage: 'url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%231a1a1a%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E")', backgroundRepeat: 'no-repeat', backgroundPosition: 'right center', backgroundSize: '8px auto' }}
                        >
                            <option value="">Raw AI Source</option>
                            {templates.map(t => (
                                <option key={t._id} value={t._id}>{t.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Bulk Approve button */}
                    <button
                        onClick={handleBulkSend}
                        disabled={leads.length === 0 || loading || (bulkTotal > 0 && !bulkDone)}
                        className="h-8 px-4 border border-ink bg-primary text-white font-mono text-[10px] uppercase font-bold hover:bg-ink transition-colors shadow-[3px_3px_0px_0px_rgba(10,10,10,1)] hover:shadow-none hover:translate-x-[1px] hover:translate-y-[1px] flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
                    >
                        <span className="material-symbols-outlined text-[14px]">send</span>
                        Bulk Approve &amp; Send ({leads.length})
                    </button>
                </div>
            </div>

            <main className="flex-1 overflow-x-auto relative">
                <LedgerTable 
                    leads={leads} 
                    loading={loading} 
                    analyzing={analyzing} 
                    runAgent={handleRunAgent} 
                    deleteLead={handleDeleteLead}
                />
            </main>
            {toast && (
                <div
                    className={`fixed top-6 right-6 z-[100] px-5 py-3 border-2 border-ink font-mono text-xs uppercase
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
                    {/* Progress Bar */}
                    <div className="h-1 bg-black/20 w-full overflow-hidden">
                        <div className="h-full bg-black animate-progress-shrink origin-left" />
                    </div>
                </div>
            )}
        </div>
    );
}

export default function LedgerPage() {
    return (
        <DashboardLayout>
            <Suspense fallback={<div className="p-8 font-mono text-sm">System connecting to ledger stream...</div>}>
                <LedgerView />
            </Suspense>
        </DashboardLayout>
    );
}
