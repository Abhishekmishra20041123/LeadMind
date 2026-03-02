"use client";
import DashboardLayout from "../../components/DashboardLayout";
import { useState, useEffect, Suspense } from "react";
import { fetchLeads } from "../../api/leads";
import { LedgerTable } from "../../components/LedgerTable";
import { useBatchProgress } from "../../hooks/useBatchProgress";
import { useSearchParams } from "next/navigation";

function LedgerView() {
    const [leads, setLeads] = useState([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(true);
    const [analyzing, setAnalyzing] = useState(null); // tracking ID of actively analyzing lead
    const [searchQuery, setSearchQuery] = useState("");
    const [minScore, setMinScore] = useState("");
    const [maxScore, setMaxScore] = useState("");

    // Hooks for parsing URL params
    const searchParams = useSearchParams();
    const batchId = searchParams.get('batch');

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

    // Initial load and pagination changes
    useEffect(() => {
        load(page, batchId, searchQuery, minScore, maxScore);
    }, [page, batchId]);

    // Fast-refresh when progress ticks
    useEffect(() => {
        if (progress && (progress.status === 'processing' || progress.status === 'completed')) {
            load(page, batchId, searchQuery, minScore, maxScore);
        }
    }, [progress?.percent, progress?.status]);

    const handleApplyFilters = () => {
        setPage(1); // Reset to page 1 on new filter
        load(1, batchId, searchQuery, minScore, maxScore);
    };

    const handleClearFilters = () => {
        setSearchQuery("");
        setMinScore("");
        setMaxScore("");
        setPage(1);
        load(1, batchId, "", "", "");
    };

    // Mock analysis function specifically tied to row UI update logic
    const handleRunAgent = async (leadId) => {
        if (analyzing) return;
        setAnalyzing(leadId);

        try {
            const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
            // Hit backend agent to trigger LangGraph on this single row
            const res = await fetch(`${API}/agents/trigger`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${localStorage.getItem("access_token")}`
                },
                body: JSON.stringify({ lead_id: leadId })
            });
            if (!res.ok) throw new Error("Agent failed");

            // Reload table upon completion to see new score/status
            await load(page, batchId, searchQuery, minScore, maxScore);
        } catch (e) {
            console.error(e);
        } finally {
            setAnalyzing(null);
        }
    };

    const totalPages = Math.ceil(total / 25);

    return (
        <div className="flex flex-col h-full bg-paper relative">
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
                    <span className="font-mono text-xs text-ink/60 mr-4">
                        Page {page} of {totalPages}
                    </span>
                    <div className="flex gap-2">
                        <button
                            disabled={page === 1}
                            onClick={() => setPage(page - 1)}
                            className="size-8 flex items-center justify-center border border-ink bg-paper hover:bg-mute disabled:opacity-30 disabled:hover:bg-paper"
                        >
                            <span className="material-symbols-outlined text-[14px]">arrow_back</span>
                        </button>
                        <button
                            disabled={page >= totalPages}
                            onClick={() => setPage(page + 1)}
                            className="size-8 flex items-center justify-center border border-ink bg-paper hover:bg-mute disabled:opacity-30 disabled:hover:bg-paper"
                        >
                            <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                        </button>
                    </div>
                </div>
            </header>

            {/* Filters Toolbar */}
            <div className="bg-mute border-b border-ink px-8 py-3 flex flex-wrap items-center gap-4 z-0">
                <div className="flex items-center border border-ink bg-paper px-3 h-8 w-64 focus-within:ring-1 focus-within:ring-primary">
                    <span className="material-symbols-outlined text-[16px] text-ink/50 mr-2">search</span>
                    <input
                        type="text"
                        placeholder="Search Name, Company, Title, or Score..."
                        className="bg-transparent outline-none w-full font-mono text-[10px] uppercase"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleApplyFilters()}
                    />
                </div>

                <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] uppercase text-ink/60">Intent Range:</span>
                    <select
                        className="h-8 border border-ink bg-paper px-2 font-mono text-[10px] uppercase outline-none focus:ring-1 focus:ring-primary"
                        value={minScore}
                        onChange={(e) => setMinScore(e.target.value)}
                    >
                        <option value="">Min</option>
                        <option value="0">0+</option>
                        <option value="20">20+</option>
                        <option value="40">40+</option>
                        <option value="60">60+</option>
                        <option value="80">80+</option>
                    </select>
                    <span className="text-ink/60">-</span>
                    <select
                        className="h-8 border border-ink bg-paper px-2 font-mono text-[10px] uppercase outline-none focus:ring-1 focus:ring-primary"
                        value={maxScore}
                        onChange={(e) => setMaxScore(e.target.value)}
                    >
                        <option value="">Max</option>
                        <option value="40">Under 40</option>
                        <option value="60">Under 60</option>
                        <option value="80">Under 80</option>
                        <option value="100">Under 100</option>
                    </select>
                </div>

                <div className="flex items-center gap-2 ml-auto">
                    {(searchQuery || minScore || maxScore) && (
                        <button
                            onClick={handleClearFilters}
                            className="h-8 px-4 font-mono text-[10px] uppercase text-ink/60 hover:text-ink hover:underline"
                        >
                            Reset
                        </button>
                    )}
                    <button
                        onClick={handleApplyFilters}
                        className="h-8 px-4 border border-ink bg-primary text-white font-mono text-[10px] uppercase font-bold hover:bg-ink transition-colors"
                    >
                        Apply Filters
                    </button>
                </div>
            </div>

            <main className="flex-1 overflow-x-auto relative">
                <LedgerTable
                    leads={leads}
                    loading={loading}
                    analyzing={analyzing}
                    runAgent={handleRunAgent}
                />
            </main>
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
