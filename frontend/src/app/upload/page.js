"use client";
import DashboardLayout from "../../components/DashboardLayout";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { uploadBatch } from "../../api/batch";
import { MultiUploadDropZone } from "../../components/UploadDropZone";
import { useBatchProgress } from "../../hooks/useBatchProgress";

export default function UploadProtocolPage() {
    const [files, setFiles] = useState([]);
    const [uploadStatus, setUploadStatus] = useState("idle"); // idle, uploading, success, error
    const [uploadResult, setUploadResult] = useState(null);
    const [startIndex, setStartIndex] = useState("");
    const [endIndex, setEndIndex] = useState("");
    const router = useRouter();

    const progress = useBatchProgress(uploadResult?.batch_id);

    // The form is ready to upload when at least 1 file is selected
    const ready = files.length > 0;

    const handleUpload = async () => {
        if (!ready) return;
        setUploadStatus("uploading");

        try {
            const result = await uploadBatch(files, startIndex, endIndex);
            setUploadResult(result);
            setUploadStatus("success");

            // Redirect smoothly to the Agent Monitor so they can watch the pipeline
            setTimeout(() => {
                router.push(`/agents?batch=${result.batch_id}`);
            }, 1800);
        } catch (err) {
            console.error(err);
            setUploadStatus("error");
        }
    };

    return (
        <DashboardLayout>
            <div className="flex flex-col h-full bg-paper relative bg-grid-pattern overflow-hidden">
                {/* Top Navigation */}
                <header className="flex items-center justify-between whitespace-nowrap border-b border-ink bg-paper px-6 py-4 z-20 shrink-0">
                    <div className="flex items-center gap-4">
                        <div className="size-6 bg-ink text-paper flex items-center justify-center">
                            <span className="material-symbols-outlined text-sm">grid_view</span>
                        </div>
                        <h2 className="text-ink text-xl font-display font-bold leading-none tracking-[-0.02em] uppercase">STRATEGIC GRID // TERMINAL</h2>
                    </div>
                </header>

                {/* Main Content Area */}
                <main className="flex-1 relative w-full h-full flex items-center justify-center p-4 md:p-8 overflow-y-auto">
                    {/* Modal Overlay Container */}
                    <div className="relative z-30 w-full max-w-[800px] max-h-[90vh] bg-paper border-[3px] border-ink shadow-[8px_8px_0px_0px_rgba(10,10,10,1)] flex flex-col">

                        {/* Modal Header */}
                        <div className="flex items-center justify-between border-b border-ink p-6 bg-ink text-paper shrink-0">
                            <div className="flex flex-col gap-1">
                                <h1 className="font-display text-3xl font-bold tracking-tight uppercase leading-none">Batch Run Protocol // V.3.0</h1>
                                <p className="font-mono text-xs text-paper/70 uppercase tracking-widest">Enterprise Atomic Ingestion Interface</p>
                            </div>
                            <button className="hover:bg-primary/20 p-2 transition-colors border border-transparent hover:border-paper/50 group">
                                <span className="material-symbols-outlined text-paper group-hover:text-primary transition-colors">close</span>
                            </button>
                        </div>

                        {/* Modal Body: Scrollable */}
                        <div className="overflow-y-auto p-6 flex flex-col gap-6 flex-1">
                            {/* File Inputs List */}
                            <div className="flex flex-col gap-4">
                                <div className="mb-2 border-l-4 border-primary pl-3 bg-mute/20 p-2">
                                    <h3 className="font-mono text-sm font-bold uppercase tracking-wider text-ink">Universal Payloads</h3>
                                    <p className="font-mono text-xs text-ink/80 mt-1 leading-relaxed">
                                        Drop any customer data CSVs here. The AI Data Discovery Agent will automatically parse headers, determine semantics, and map structure to the execution core.
                                    </p>
                                </div>
                                <MultiUploadDropZone files={files} setFiles={setFiles} />
                            </div>

                            {/* Range Selection Inputs */}
                            <div className="flex flex-col gap-4">
                                <div className="mb-2">
                                    <h3 className="font-mono text-sm font-bold uppercase tracking-wider text-ink border-l-4 border-primary pl-3">Optional Range Limits</h3>
                                    <p className="font-mono text-xs text-ink/60 mt-2">Limit execution to a subset of the leads database.</p>
                                </div>
                                <div className="flex items-center gap-4 w-full">
                                    <div className="flex flex-col gap-1 w-1/2">
                                        <label className="font-mono text-[10px] uppercase font-bold text-ink/60" htmlFor="start-index">Start Lead Row</label>
                                        <input
                                            id="start-index"
                                            type="number"
                                            min="0"
                                            className="w-full bg-paper border-[2px] border-ink p-2 font-mono text-sm outline-none focus:border-primary transition-colors disabled:opacity-50"
                                            placeholder="e.g. 0"
                                            value={startIndex}
                                            onChange={(e) => setStartIndex(e.target.value)}
                                            disabled={uploadStatus === 'uploading' || uploadStatus === 'success'}
                                        />
                                    </div>
                                    <div className="flex flex-col gap-1 w-1/2">
                                        <label className="font-mono text-[10px] uppercase font-bold text-ink/60" htmlFor="end-index">End Lead Row</label>
                                        <input
                                            id="end-index"
                                            type="number"
                                            min="1"
                                            className="w-full bg-paper border-[2px] border-ink p-2 font-mono text-sm outline-none focus:border-primary transition-colors disabled:opacity-50"
                                            placeholder="e.g. 10"
                                            value={endIndex}
                                            onChange={(e) => setEndIndex(e.target.value)}
                                            disabled={uploadStatus === 'uploading' || uploadStatus === 'success'}
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* Helper / Log Output */}
                            <div className="bg-ink text-paper p-4 font-mono text-xs leading-relaxed border-t-2 border-primary">
                                <div className="flex gap-2">
                                    <span className="text-primary">&gt;&gt;&gt;</span>
                                    <span className={ready ? 'text-data-green' : 'text-paper'}>
                                        {ready ? 'ALL REQUIREMENTS MET. PIPELINE UNLOCKED.' : 'AWAITING PAYLOADS...'}
                                    </span>
                                </div>
                                {uploadStatus === 'uploading' && (
                                    <div className="flex gap-2 text-primary">
                                        <span className="text-primary">&gt;&gt;&gt;</span>
                                        <span className="animate-pulse">TRANSFERRING TO BACKEND CLUSTER...</span>
                                    </div>
                                )}
                                {uploadStatus === 'success' && uploadResult && (
                                    <div className="flex gap-2 text-data-green">
                                        <span className="text-data-green">&gt;&gt;&gt;</span>
                                        <span>INITIALIZED: BATCH ID [{uploadResult.batch_id}] GENERATED.</span>
                                    </div>
                                )}
                                {progress && (
                                    <div className="flex gap-2 text-primary mt-2">
                                        <span className="text-primary">&gt;&gt;&gt;</span>
                                        <span className="animate-pulse">STATUS: {progress.status.toUpperCase()} ({progress.percent}%)</span>
                                    </div>
                                )}
                                {uploadStatus === 'success' && (
                                    <div className="flex gap-2 text-white/50 mt-2">
                                        <span className="text-white/50">&gt;&gt;&gt;</span>
                                        <span>HANDING OFF TO AGENT MONITOR STREAM...</span>
                                    </div>
                                )}
                                {uploadStatus === 'error' && (
                                    <div className="flex gap-2 text-red-500">
                                        <span className="text-red-500">&gt;&gt;&gt;</span>
                                        <span>ERROR: TRANSMISSION REJECTED. CHECK SYSTEM LOGS.</span>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Modal Footer: Actions */}
                        <div className="p-6 border-t border-ink bg-paper flex items-center justify-between gap-6 shrink-0 z-20">
                            <div className="flex flex-col gap-1">
                                <span className="font-mono text-[10px] text-ink/50 uppercase tracking-widest">Execution Status</span>
                                <div className="flex items-center gap-2">
                                    <div className={`size-2 rounded-full ${uploadStatus === 'success' ? 'bg-data-green' : uploadStatus === 'uploading' ? 'bg-primary' : ready ? 'bg-data-green animate-pulse' : 'bg-ink/40'}`}></div>
                                    <span className={`font-display font-bold text-sm uppercase ${uploadStatus === 'success' ? 'text-data-green' : uploadStatus === 'uploading' ? 'text-primary' : 'text-ink/60'}`}>
                                        {uploadStatus === 'success' ? 'Batch Stored Successfully' : uploadStatus === 'uploading' ? 'Processing...' : ready ? 'Ready for Execution' : 'Requirements Pending'}
                                    </span>
                                </div>
                            </div>
                            <div className="flex gap-4 w-full max-w-md justify-end">
                                <button
                                    onClick={() => {
                                        setFiles([]);
                                        setUploadStatus("idle");
                                    }}
                                    className="px-6 py-3 border border-ink text-ink font-display font-bold uppercase text-sm hover:bg-mute transition-colors"
                                >
                                    Reset
                                </button>
                                {/* Form Submit Button */}
                                <button
                                    onClick={handleUpload}
                                    disabled={!ready || uploadStatus === 'uploading'}
                                    className={`flex-1 px-8 py-3 font-display font-bold uppercase text-sm flex items-center justify-center gap-2 transition-all ${!ready || uploadStatus === 'uploading'
                                        ? 'bg-mute text-ink/40 border-ink/20 cursor-not-allowed'
                                        : uploadStatus === 'success'
                                            ? 'bg-data-green text-white border-data-green shadow-[4px_4px_0px_0px_rgba(10,10,10,1)]'
                                            : 'bg-primary text-white border-ink hover:bg-ink hover:shadow-[4px_4px_0px_0px_rgba(10,10,10,1)]'
                                        }`}
                                >
                                    <span>
                                        {uploadStatus === 'uploading' ? 'PROCESSING...'
                                            : uploadStatus === 'success' ? 'EXECUTION COMPLETE'
                                                : 'EXECUTE BATCH RUN'}
                                    </span>
                                    <span className="material-symbols-outlined text-base">
                                        {!ready ? 'lock' : uploadStatus === 'success' ? 'check_circle' : uploadStatus === 'uploading' ? 'sync' : 'rocket_launch'}
                                    </span>
                                </button>
                            </div>
                        </div>

                    </div>
                </main>
            </div>
        </DashboardLayout>
    );
}
