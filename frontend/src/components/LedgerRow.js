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
    const isSDK = lead.source === "sdk" || lead.sdk_source;
    const engScore = lead.engagement_score;

    const openReport = () => {
        const batch = searchParams.get('batch');
        const query = batch ? `?batch=${batch}` : '';
        router.push(`/intel/${leadId}${query}`);
    };

    return (
        <tr onClick={openReport} className="h-[64px] group hover:bg-ink hover:text-paper cursor-pointer transition-colors relative border-b border-ink">
            {/* ID + Source */}
            <td className="px-6 py-3 font-mono text-[10px] uppercase border-r border-ink group-hover:border-paper min-w-[120px]">
                <div className="flex flex-col gap-1">
                    <span className="font-bold whitespace-nowrap">{leadId}</span>
                    <span className={`inline-flex self-start border px-1 ${
                        isSDK
                            ? 'bg-blue-50 text-blue-600 border-blue-200 group-hover:bg-blue-900 group-hover:text-blue-200 group-hover:border-blue-700'
                            : 'bg-mute text-ink border-ink group-hover:bg-ink group-hover:text-paper group-hover:border-paper'
                    }`}>
                        {isSDK ? '⚡ SDK' : '📄 CSV'}
                    </span>
                </div>
            </td>

            {/* Lead Entity */}
            <td className="px-6 py-3 border-r border-ink group-hover:border-paper">
                <div className="flex flex-col gap-0.5">
                    <span className="font-display font-bold text-lg leading-tight">{lead.name || "Unknown"}</span>
                    {isSDK ? (
                        /* SDK behavioral mini-bar */
                        <div className="flex items-center gap-1.5 flex-wrap">
                            {/* Engagement bar */}
                            {engScore != null && (
                                <div className="flex items-center gap-1">
                                    <div className="w-12 h-1.5 bg-ink/10 group-hover:bg-white/20 rounded-full overflow-hidden">
                                        <div
                                            className={`h-full rounded-full ${engScore >= 70 ? 'bg-green-500' : engScore >= 40 ? 'bg-yellow-400' : 'bg-red-400'}`}
                                            style={{ width: `${engScore}%` }}
                                        />
                                    </div>
                                    <span className="font-mono text-[9px] opacity-60">{engScore}</span>
                                </div>
                            )}
                            {lead.cart_added && (
                                <span className="text-[9px] px-1 bg-orange-100 text-orange-700 border border-orange-300 group-hover:bg-orange-900 group-hover:text-orange-200 group-hover:border-orange-700 rounded font-bold">🛒</span>
                            )}
                            {lead.checkout_started && (
                                <span className="text-[9px] px-1 bg-red-100 text-red-700 border border-red-300 group-hover:bg-red-900 group-hover:text-red-200 group-hover:border-red-700 rounded font-bold">💳</span>
                            )}
                            {lead.purchase_made && (
                                <span className="text-[9px] px-1 bg-green-100 text-green-700 border border-green-300 group-hover:bg-green-900 group-hover:text-green-200 group-hover:border-green-700 rounded font-bold">🎉</span>
                            )}
                            {lead.utm_source && (
                                <span className="text-[9px] px-1 bg-purple-50 text-purple-700 border border-purple-200 group-hover:bg-purple-900 group-hover:text-purple-200 group-hover:border-purple-700 rounded font-mono">
                                    via {lead.utm_source}
                                </span>
                            )}
                        </div>
                    ) : (
                        <span className="font-mono text-[10px] opacity-60">
                            Last active: {lead.lastActive || lead.last_active || "—"}
                        </span>
                    )}

                </div>
            </td>

            <td className="px-6 py-3 font-body text-sm border-r border-ink group-hover:border-paper">{lead.company || lead.organization || "Unknown"}</td>
            <td className="px-6 py-3 font-body text-sm border-r border-ink group-hover:border-paper">
                <div className="flex flex-col gap-0.5">
                    <span>{lead.title || "Customer"}</span>
                    {isSDK && lead.device_type && (
                        <span className="font-mono text-[9px] opacity-50">
                            {lead.device_type === "mobile" ? "📱" : lead.device_type === "tablet" ? "📲" : "🖥"} {lead.device_type}
                        </span>
                    )}
                </div>
            </td>

            {/* Intent Score */}
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
                            onClick={(e) => { e.preventDefault(); e.stopPropagation(); runAgent(lead.lead_id || lead._index); }}
                            className="w-8 h-8 flex items-center justify-center border border-ink bg-paper hover:bg-primary hover:text-white transition-colors"
                            title="Run LangGraph Agent Analysis"
                        >
                            <span className="material-symbols-outlined text-[16px]">bolt</span>
                        </button>
                    )}
                    <button
                        onClick={(e) => { e.preventDefault(); e.stopPropagation(); if (window.confirm(`Delete lead ${lead.name || leadId}?`)) deleteLead(leadId); }}
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
            {/* Hover border indicator */}
            <td className="absolute left-0 top-0 bottom-0 w-1 bg-primary opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></td>
        </tr>
    );
}
