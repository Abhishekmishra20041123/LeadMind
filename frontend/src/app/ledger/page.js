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

    // Hooks for parsing URL params
    const searchParams = useSearchParams();
    const batchId = searchParams.get('batch');

    const progress = useBatchProgress(batchId);

    async function load(p, batchStr) {
        setLoading(true);
        try {
            const data = await fetchLeads(p, 25, batchStr);
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
        load(page, batchId);
    }, [page, batchId]);

    // Fast-refresh when progress ticks
    useEffect(() => {
        if (progress && (progress.status === 'processing' || progress.status === 'completed')) {
            load(page, batchId);
        }
    }, [progress?.percent, progress?.status]);

    // Mock analysis function specifically tied to row UI update logic
    const handleRunAgent = async (leadId) => {
        if (analyzing) return;
        setAnalyzing(leadId);

        try {
            const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
            // Hit backend agent to trigger LangGraph on this single row
            const res = await fetch(`${API}/agents/trigger`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ lead_id: leadId })
            });
            if (!res.ok) throw new Error("Agent failed");

            // Reload table upon completion to see new score/status
            await load(page, batchId);
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
