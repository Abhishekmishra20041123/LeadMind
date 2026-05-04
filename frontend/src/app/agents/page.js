"use client";
import DashboardLayout from "../../components/DashboardLayout";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useBatchProgress } from "../../hooks/useBatchProgress";

function AgentMonitorView() {
    const searchParams = useSearchParams();
    const batchId = searchParams.get('batch');
    const [activeBatchId, setActiveBatchId] = useState(batchId);
    const [fetchingLatest, setFetchingLatest] = useState(!batchId);

    useEffect(() => {
        if (!batchId) {
            const token = localStorage.getItem("access_token");
            fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api"}/batch/list`, {
                headers: { "Authorization": `Bearer ${token}` }
            })
                .then(res => res.json())
                .then(data => {
                    if (data.batches && data.batches.length > 0) {
                        setActiveBatchId(data.batches[0].batch_id);
                    }
                })
                .catch(console.error)
                .finally(() => setFetchingLatest(false));
        } else {
            setActiveBatchId(batchId);
            setFetchingLatest(false);
        }
    }, [batchId]);

    const progress = useBatchProgress(activeBatchId);

    // Fallback UI if not provided and not fetching
    if (fetchingLatest) {
        return (
            <div className="flex flex-col items-center justify-center p-24 font-mono animate-pulse text-ink/50 uppercase">
                Locating active stream...
            </div>
        );
    }

    if (!activeBatchId) {
        return (
            <div className="flex flex-col items-center justify-center p-24 font-mono text-ink/50 uppercase">
                Awaiting active batch allocation_
            </div>
        );
    }

    if (!progress) {
        return (
            <div className="flex flex-col items-center justify-center p-24 font-mono animate-pulse text-primary uppercase font-bold">
                Connecting Pipeline Stream...
            </div>
        );
    }

    const isCompleted = progress.status === 'completed';
    const isFailed    = progress.status === 'failed' || progress.status === 'error';

    const isProcessing = progress.status === 'processing';

    // UI-only status override: Show all as running if processing, all as completed if done.
    // This provides a non-sequential, "all-at-once" pipeline visibility.
    const getDisplayStatus = (id) => {
        if (isCompleted) return 'completed';
        if (isProcessing) return 'running';
        if (isFailed) return progress.agents?.[id] || 'error';
        return 'pending';
    };

    const agentList = [
        { id: 'research', name: 'Research Agent',      status: getDisplayStatus('research') },
        { id: 'intent',   name: 'Intent Scoring',      status: getDisplayStatus('intent') },
        { id: 'timing',   name: 'Timing Engine',       status: getDisplayStatus('timing') },
        { id: 'logger',   name: 'CRM Logger',          status: getDisplayStatus('logger') },
        { id: 'outreach', name: 'Multi-Channel Drafter', status: getDisplayStatus('message') }, 
    ];

    const processedCount = progress.processed_count || 0;
    const totalCount     = progress.total_count     || 0;

    return (
        <div className="flex flex-col h-full bg-paper relative bg-grid-pattern overflow-hidden">
            {/* HEADER BLOCK */}
            <header className="h-16 shrink-0 border-b border-ink flex items-center justify-between px-8 bg-paper z-10">
                <div className="flex items-center gap-6">
                    <div className="flex flex-col justify-center">
                        <span className="font-mono text-[10px] text-ink/60 uppercase">Active Process Tracker</span>
                        <h2 className="font-display font-bold text-xl tracking-tight leading-none mt-0.5">{activeBatchId}</h2>
                    </div>
                    <div className="h-6 w-px bg-ink/20"></div>
                    <div className="relative flex items-center gap-2 px-3 py-1.5 border border-ink overflow-hidden">
                        {progress.status === 'processing' ? (
                            <div className="absolute top-0 left-0 h-full bg-primary/20 transition-all duration-500" style={{ width: `${progress.percent}%` }}></div>
                        ) : null}
                        <div className={`relative z-10 flex items-center gap-2 ${isCompleted ? 'text-green-600' : isFailed ? 'text-red-500' : 'text-primary'}`}>
                            <span className={`material-symbols-outlined text-[14px] ${progress.status === 'processing' ? 'animate-[spin_3s_linear_infinite]' : ''}`}>
                                {isCompleted ? 'check_circle' : isFailed ? 'error' : 'sync'}
                            </span>
                            <span className="font-mono text-xs font-bold uppercase">
                                {progress.percent}% &bull; {progress.status}
                                {totalCount > 0 ? ` — ${processedCount}/${totalCount} leads` : ''}
                            </span>
                        </div>
                    </div>
                </div>
                {/* VIEW LEADS CTA — appears only after batch completes */}
                {isCompleted && (
                    <a
                        href="/ledger"
                        className="h-9 px-5 bg-ink text-paper hover:bg-primary font-mono text-xs font-bold uppercase transition-colors flex items-center gap-2 border border-ink"
                    >
                        <span className="material-symbols-outlined text-[14px]">open_in_new</span>
                        VIEW LEADS
                    </a>
                )}
            </header>

            {/* PIPELINE VISUALIZATION (SWIM LANES) */}
            <div className="flex-1 flex flex-col justify-center px-12 overflow-x-auto relative z-10 min-h-[350px]">
                <div className="flex items-start gap-0 w-full min-w-[1000px]">
                    {agentList.map((agent, index) => {
                        const isLast = index === agentList.length - 1;
                        const isCompleted = agent.status === 'completed';
                        const isRunning = agent.status === 'running';
                        const isPending = agent.status === 'pending' || agent.status === 'idle';
                        const isError = agent.status === 'error';

                        let shortName = agent.name;
                        let abbr = `AGN_${shortName.substring(0, 3).toUpperCase()}`;

                        return (
                            <div key={agent.id} className="flex contents w-full h-full group">
                                <div className={`flex-1 flex flex-col gap-4 ${isPending ? 'opacity-50' : ''}`}>
                                    <div className={`relative h-48 p-6 flex flex-col justify-between transition-all duration-500 ${isRunning
                                        ? 'border-3 border-primary bg-paper shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] transform -translate-y-2'
                                        : isCompleted
                                            ? 'border border-ink bg-ink'
                                            : isError
                                                ? 'border-2 border-red-500 bg-red-500/10'
                                                : 'border border-ink bg-mute'
                                        }`}>

                                        {isRunning && (
                                            <div className="absolute -top-3 left-4 bg-primary text-paper px-2 py-0.5 text-[10px] font-mono font-bold tracking-widest uppercase animate-pulse">
                                                EXECUTING
                                            </div>
                                        )}
                                        {isError && (
                                            <div className="absolute -top-3 left-4 bg-red-500 text-paper px-2 py-0.5 text-[10px] font-mono font-bold tracking-widest uppercase">
                                                FAILED
                                            </div>
                                        )}

                                        <div className="flex justify-between items-start">
                                            <span className={`font-mono text-xs ${isRunning ? 'text-primary font-bold' : isCompleted ? 'text-paper/60' : isError ? 'text-red-500 font-bold' : 'text-ink/60'}`}>
                                                0{index + 1} // {abbr}
                                            </span>
                                            <span className={`material-symbols-outlined ${isRunning ? 'text-primary animate-[spin_3s_linear_infinite]' : isCompleted ? 'text-data-green' : isError ? 'text-red-500' : 'text-ink/40'}`}>
                                                {isRunning ? 'sync' : isCompleted ? 'check_circle' : isError ? 'error' : 'hourglass_empty'}
                                            </span>
                                        </div>
                                        <div>
                                            <h3 className={`font-display text-2xl font-bold mb-1 ${isRunning ? 'text-ink' : isCompleted ? 'text-paper' : isError ? 'text-red-500' : 'text-ink'}`}>
                                                {shortName}
                                            </h3>
                                            <p className={`font-mono text-xs uppercase ${isRunning ? 'text-ink font-bold' : isCompleted ? 'text-paper/80' : isError ? 'text-red-500' : 'text-ink/60'}`}>
                                                {agent.status}
                                            </p>
                                        </div>
                                        <div className={`w-full h-1 mt-4 relative overflow-hidden ${isRunning ? 'bg-mute' : isCompleted ? 'bg-paper/20' : isError ? 'bg-red-500/20' : 'bg-ink/10'}`}>
                                            {isRunning && (
                                                <div className="w-2/3 bg-primary h-full relative overflow-hidden transition-all duration-300">
                                                    <div className="absolute inset-0 bg-white/30 skew-x-12 -translate-x-full animate-[shimmer_1.5s_infinite]"></div>
                                                </div>
                                            )}
                                            {isCompleted && (
                                                <div className="w-full bg-data-green h-full"></div>
                                            )}
                                            {isError && (
                                                <div className="w-full bg-red-500 h-full"></div>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* CONNECTOR */}
                                {!isLast && (
                                    <div className={`w-12 h-48 flex items-center justify-center relative ${isPending ? 'opacity-50' : ''}`}>
                                        <div className={`w-full h-px border-t ${isCompleted ? 'bg-ink border-transparent' : 'bg-ink/30 border-dashed border-ink'}`}></div>
                                        {isCompleted && (
                                            <span className="material-symbols-outlined absolute text-ink bg-paper p-0.5 z-10 text-[14px]">arrow_forward</span>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* TERMINAL LOG OUTPUT */}
            <div className="h-[30%] min-h-[200px] border-t-3 border-ink bg-ink text-paper flex flex-col z-20 shadow-[0_-10px_40px_-15px_rgba(0,0,0,0.3)] shrink-0">
                <div className="h-10 border-b border-white/20 flex items-center justify-between px-4 bg-[#1a1a1a] shrink-0">
                    <div className="flex items-center gap-4">
                        <span className="font-mono text-xs text-primary font-bold flex items-center gap-2">
                            <span className={`w-2 h-2 ${progress.status === 'processing' ? 'bg-primary animate-pulse' : 'bg-data-green'} rounded-full`}></span>
                            {progress.status === 'processing' ? 'LIVE STREAM' : 'PIPELINE LOG TRACE'}
                        </span>
                    </div>
                </div>
                <div className="flex-1 p-6 font-mono text-xs overflow-y-auto space-y-2 flex flex-col">
                    {progress.logs && progress.logs.map((log, index) => {
                        const isError = log.includes("ERROR");
                        const isSuccess = log.includes("SUCCESS");
                        return (
                            <div key={index} className="flex gap-4 opacity-80">
                                <span className="text-white/40 w-16 shrink-0">SYS_OUT</span>
                                <span className={`${isError ? 'text-red-500' : isSuccess ? 'text-data-green' : 'text-primary'} shrink-0 min-w-[60px]`}>
                                    [SYSTEM]
                                </span>
                                <span className={isError ? 'text-red-400' : 'text-paper/90'}>{log}</span>
                            </div>
                        )
                    })}
                    {progress.status !== 'completed' && (
                        <div className="flex gap-4 opacity-50">
                            <span className="text-white/40 w-16 shrink-0">SYS_OUT</span>
                            <span className="text-data-green shrink-0 min-w-[60px]">[SYSTEM]</span>
                            <span className="animate-pulse">STREAMING RAW PIPELINE LOGS...</span>
                        </div>
                    )}
                    {progress.status === 'completed' && (
                        <div className="flex gap-4">
                            <span className="text-white/40 w-16 shrink-0">SYS_OUT</span>
                            <span className="text-data-green shrink-0 min-w-[60px]">[SYSTEM]</span>
                            <span className="text-data-green font-bold">BATCH RUN SUCCESSFULLY FINALIZED</span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default function AgentMonitorPage() {
    return (
        <DashboardLayout>
            <Suspense fallback={<div className="p-12 font-mono">Initializing Neural Agent Board...</div>}>
                <AgentMonitorView />
            </Suspense>
        </DashboardLayout>
    );
}
