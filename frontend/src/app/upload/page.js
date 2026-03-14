"use client";
import DashboardLayout from "../../components/DashboardLayout";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { uploadBatch } from "../../api/batch";
import { BatchFileInput } from "../../components/BatchFileInput";
import { useBatchProgress } from "../../hooks/useBatchProgress";
import { SmartUploadWizard } from "../../components/SmartUploadWizard";

export default function DataUploadPage() {
    const [isLegacyMode, setIsLegacyMode] = useState(false);
    
    // Legacy State
    const [files, setFiles] = useState({});
    const [uploadStatus, setUploadStatus] = useState("idle");
    const [uploadResult, setUploadResult] = useState(null);
    const [startIndex, setStartIndex] = useState("");
    const [endIndex, setEndIndex] = useState("");
    
    const router = useRouter();
    const progress = useBatchProgress(uploadResult?.batch_id);

    const ready =
        files.agentMapping &&
        files.crmPipeline &&
        files.emailLogs &&
        files.leadsData &&
        files.salesPipeline;

    const handleLegacyUpload = async () => {
        if (!ready) return;
        setUploadStatus("uploading");

        try {
            const result = await uploadBatch(files, startIndex, endIndex);
            setUploadResult(result);
            setUploadStatus("success");

            setTimeout(() => {
                router.push(`/agents?batch=${result.batch_id}`);
            }, 1800);
        } catch (err) {
            console.error(err);
            setUploadStatus("error");
        }
    };

    const handleSmartUploadSuccess = (batch_id) => {
        setTimeout(() => {
            router.push(`/agents?batch=${batch_id}`);
        }, 1800);
    }

    return (
        <DashboardLayout>
            <div className="flex flex-col h-full bg-paper relative bg-grid-pattern overflow-hidden">
                <header className="flex items-center justify-between whitespace-nowrap border-b border-ink bg-paper px-6 py-4 z-20 shrink-0">
                    <div className="flex items-center gap-4">
                        <div className="size-6 bg-ink text-paper flex items-center justify-center">
                            <span className="material-symbols-outlined text-sm">grid_view</span>
                        </div>
                        <h2 className="text-ink text-xl font-display font-bold leading-none tracking-[-0.02em] uppercase">LEADMIND // TERMINAL</h2>
                    </div>
                </header>

                <main className="flex-1 relative w-full h-full flex items-center justify-center p-4 md:p-8 overflow-y-auto">
                    <div className="relative z-30 w-full max-w-[800px] max-h-[90vh] bg-paper border-[3px] border-ink shadow-[8px_8px_0px_0px_rgba(10,10,10,1)] flex flex-col">

                        <div className="flex items-center justify-between border-b border-ink p-6 bg-ink text-paper shrink-0">
                            <div className="flex flex-col gap-1">
                                <h1 className="font-display text-3xl font-bold tracking-tight uppercase leading-none">Data Upload // V.4.0</h1>
                                <p className="font-mono text-xs text-paper/70 uppercase tracking-widest">Enterprise Atomic Ingestion Interface</p>
                            </div>
                            <div className="flex items-center gap-4">
                                <button 
                                    onClick={() => setIsLegacyMode(!isLegacyMode)}
                                    className="font-mono text-xs uppercase tracking-widest border border-paper/30 hover:border-paper hover:bg-paper/10 px-3 py-1 transition-colors"
                                >
                                    {isLegacyMode ? "Switch to Smart AI Upload" : "Switch to Legacy Upload"}
                                </button>
                                <button className="hover:bg-primary/20 p-2 transition-colors border border-transparent hover:border-paper/50 group">
                                    <span className="material-symbols-outlined text-paper group-hover:text-primary transition-colors">close</span>
                                </button>
                            </div>
                        </div>

                        {!isLegacyMode ? (
                            <div className="p-6 overflow-y-auto">
                                <SmartUploadWizard onUploadSuccess={handleSmartUploadSuccess} />
                            </div>
                        ) : (
                            // Legacy Upload UI
                            <>
                                <div className="overflow-y-auto p-6 flex flex-col gap-6 flex-1">
                                    <div className="flex flex-col gap-4">
                                        <div className="mb-2">
                                            <h3 className="font-mono text-sm font-bold uppercase tracking-wider text-ink border-l-4 border-primary pl-3">Required Payloads (Legacy)</h3>
                                            <p className="font-mono text-xs text-ink/60 mt-2">All 5 structural schemas must be provided for the pipeline execution to unlock.</p>
                                        </div>
                                        <BatchFileInput label="Agent Mappings" fileKey="agentMapping" files={files} setFiles={setFiles} />
                                        <BatchFileInput label="CRM Pipeline" fileKey="crmPipeline" files={files} setFiles={setFiles} />
                                        <BatchFileInput label="Email Logs" fileKey="emailLogs" files={files} setFiles={setFiles} />
                                        <BatchFileInput label="Leads Data" fileKey="leadsData" files={files} setFiles={setFiles} />
                                        <BatchFileInput label="Sales Pipeline" fileKey="salesPipeline" files={files} setFiles={setFiles} />
                                    </div>

                                    <div className="flex flex-col gap-4">
                                        <div className="mb-2">
                                            <h3 className="font-mono text-sm font-bold uppercase tracking-wider text-ink border-l-4 border-primary pl-3">Optional Range Limits</h3>
                                        </div>
                                        <div className="flex items-center gap-4 w-full">
                                            <div className="flex flex-col gap-1 w-1/2">
                                                <label className="font-mono text-[10px] uppercase font-bold text-ink/60">Start Lead Row</label>
                                                <input
                                                    type="number"
                                                    className="w-full bg-paper border-[2px] border-ink p-2 font-mono text-sm outline-none focus:border-primary transition-colors disabled:opacity-50"
                                                    value={startIndex}
                                                    onChange={(e) => setStartIndex(e.target.value)}
                                                    disabled={uploadStatus === 'uploading' || uploadStatus === 'success'}
                                                />
                                            </div>
                                            <div className="flex flex-col gap-1 w-1/2">
                                                <label className="font-mono text-[10px] uppercase font-bold text-ink/60">End Lead Row</label>
                                                <input
                                                    type="number"
                                                    className="w-full bg-paper border-[2px] border-ink p-2 font-mono text-sm outline-none focus:border-primary transition-colors disabled:opacity-50"
                                                    value={endIndex}
                                                    onChange={(e) => setEndIndex(e.target.value)}
                                                    disabled={uploadStatus === 'uploading' || uploadStatus === 'success'}
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    <div className="bg-ink text-paper p-4 font-mono text-xs leading-relaxed border-t-2 border-primary">
                                        <div className="flex gap-2">
                                            <span className="text-primary">&gt;&gt;&gt;</span>
                                            <span className={ready ? 'text-data-green' : 'text-paper'}>
                                                {ready ? 'ALL REQUIREMENTS MET. PIPELINE UNLOCKED.' : 'AWAITING PAYLOADS...'}
                                            </span>
                                        </div>
                                        {uploadStatus === 'uploading' && <div className="flex gap-2 text-primary"><span className="text-primary">&gt;&gt;&gt;</span><span className="animate-pulse">TRANSFERRING...</span></div>}
                                        {uploadStatus === 'success' && uploadResult && <div className="flex gap-2 text-data-green"><span className="text-data-green">&gt;&gt;&gt;</span><span>BATCH ID [{uploadResult.batch_id}] GENERATED.</span></div>}
                                    </div>
                                </div>

                                <div className="p-6 border-t border-ink bg-paper flex items-center justify-between gap-6 shrink-0 z-20">
                                    <div className="flex gap-4 w-full justify-end">
                                        <button
                                            onClick={handleLegacyUpload}
                                            disabled={!ready || uploadStatus === 'uploading'}
                                            className={`px-8 py-3 font-display font-bold uppercase text-sm flex items-center justify-center gap-2 transition-all ${
                                                !ready || uploadStatus === 'uploading'
                                                    ? 'bg-mute text-ink/40 border-[2px] border-ink/20 cursor-not-allowed'
                                                    : uploadStatus === 'success'
                                                        ? 'bg-data-green text-white border-[2px] border-data-green'
                                                        : 'bg-primary text-white border-[2px] border-ink hover:bg-ink'
                                            }`}
                                        >
                                            {uploadStatus === 'uploading' ? 'PROCESSING...' : uploadStatus === 'success' ? 'COMPLETE' : 'EXECUTE LEGACY BATCH RUN'}
                                        </button>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </main>
            </div>
        </DashboardLayout>
    );
}
