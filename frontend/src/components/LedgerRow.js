import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { StatusBadge } from "./StatusBadge";

export function LedgerRow({ lead, analyzing, runAgent, deleteLead }) {
    const router = useRouter();
    const searchParams = useSearchParams();

    const leadIdField = lead.lead_id || lead._index;
    const isAnalyzing = analyzing === leadIdField;
    const activeStatus = isAnalyzing ? "Processing" : (lead.status || "Ready");
    const score = lead.intent ?? lead.intent_score;
    const opacityClass = score == null ? "opacity-50" : "";
    const leadId = lead.lead_id || lead.id;

    const openReport = () => {
        const batch = searchParams.get('batch');
        const query = batch ? `?batch=${batch}` : '';
        router.push(`/intel/${leadId}${query}`);
    };

    return (
        <tr onClick={openReport} className="h-[64px] group hover:bg-ink hover:text-paper cursor-pointer transition-colors relative border-b border-ink">
            <td className="px-6 py-3 font-mono text-sm border-r border-ink group-hover:border-paper">{leadId}</td>
            <td className="px-6 py-3 border-r border-ink group-hover:border-paper">
                <div className="flex flex-col">
                    <span className="font-display font-bold text-lg leading-tight">{lead.name || "Unknown"}</span>
                    <span className="font-mono text-[10px] opacity-60">Last active: {lead.lastActive || lead.last_active || "Recently"}</span>
                </div>
            </td>
            <td className="px-6 py-3 font-body text-sm border-r border-ink group-hover:border-paper">{lead.company || lead.organization || "Unknown"}</td>
            <td className="px-6 py-3 font-body text-sm border-r border-ink group-hover:border-paper">{lead.title || "Unknown"}</td>
            <td className="px-6 py-3 border-r border-ink group-hover:border-paper">
                <div className="flex items-center gap-3">
                    <span className={`font-mono font-bold text-lg ${opacityClass}`}>{score ?? "--"}</span>
                    <div className="h-3 flex-1 bg-mute group-hover:bg-[#333] border border-ink group-hover:border-paper">
                        {score != null ? (
                            <div className="h-full bg-primary group-hover:bg-primary" style={{ width: `${score}%` }}></div>
                        ) : (
                            <div className="h-full bg-ink w-[45%] opacity-20 animate-pulse"></div>
                        )}
                    </div>
                </div>
            </td>
            <td className="px-6 py-3 border-r border-ink group-hover:border-paper">
                <StatusBadge status={activeStatus} analyzing={isAnalyzing} />
            </td>
            <td className="px-6 py-3 text-right">
                <div className="flex items-center justify-end gap-2">
                    {activeStatus === "Ready" && !isAnalyzing && (
                        <button
                            onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                runAgent(lead.lead_id || lead._index);
                            }}
                            className="w-8 h-8 flex items-center justify-center border border-ink bg-paper hover:bg-primary hover:text-white transition-colors"
                            title="Run LangGraph Agent Analysis"
                        >
                            <span className="material-symbols-outlined text-[16px]">bolt</span>
                        </button>
                    )}
                    <button
                        onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            if (window.confirm(`Are you sure you want to delete lead ${lead.name || leadId}?`)) {
                                deleteLead(leadId);
                            }
                        }}
                        className="w-8 h-8 flex items-center justify-center border border-ink bg-paper hover:bg-red-50 text-ink/40 hover:text-red-600 transition-colors group-hover:text-paper"
                        title="Delete Lead"
                    >
                        <span className="material-symbols-outlined text-[16px]">delete</span>
                    </button>
                    <Link href={`/intel/${leadId}`} className="p-2 hover:text-primary transition-colors inline-block text-ink/40 group-hover:text-paper">
                        <span className="material-symbols-outlined">{isAnalyzing || activeStatus === "Processing" ? "pending" : "arrow_forward"}</span>
                    </Link>
                </div>
            </td>
            {/* Hover active border indicator */}
            <td className="absolute left-0 top-0 bottom-0 w-1 bg-primary opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></td>
        </tr>
    );
}
