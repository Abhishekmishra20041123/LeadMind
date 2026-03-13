import { LedgerRow } from "./LedgerRow";

export function LedgerTable({ leads, analyzing, runAgent, deleteLead, loading }) {
    if (loading) {
        return (
            <div className="flex-1 overflow-auto bg-paper">
                <table className="w-full border-collapse">
                    <thead className="bg-ink text-paper sticky top-0 z-10">
                        <tr>
                            <th className="h-12 px-6 text-left font-mono text-xs font-normal uppercase tracking-wider border-r border-white/20 w-[100px]">ID_REF</th>
                            <th className="h-12 px-6 text-left font-mono text-xs font-normal uppercase tracking-wider border-r border-white/20 w-[25%]">Lead Entity</th>
                            <th className="h-12 px-6 text-left font-mono text-xs font-normal uppercase tracking-wider border-r border-white/20 w-[20%]">Organization</th>
                            <th className="h-12 px-6 text-left font-mono text-xs font-normal uppercase tracking-wider border-r border-white/20 w-[20%]">Title</th>
                            <th className="h-12 px-6 text-left font-mono text-xs font-normal uppercase tracking-wider border-r border-white/20 w-[15%]">Intent Score</th>
                            <th className="h-12 px-6 text-left font-mono text-xs font-normal uppercase tracking-wider border-r border-white/20 w-[10%]">Status</th>
                            <th className="h-12 px-6 text-right font-mono text-xs font-normal uppercase tracking-wider w-[100px]">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-ink">
                        <tr>
                            <td colSpan={7} className="px-6 py-12 text-center text-ink/50 font-mono">
                                <div className="flex items-center justify-center gap-2">
                                    <span className="material-symbols-outlined animate-spin text-xl">sync</span>
                                    LOADING DATABASE...
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-auto bg-paper">
            <table className="w-full border-collapse">
                <thead className="bg-ink text-paper sticky top-0 z-10">
                    <tr>
                        <th className="h-12 px-6 text-left font-mono text-xs font-normal uppercase tracking-wider border-r border-white/20 w-[100px]">ID_REF</th>
                        <th className="h-12 px-6 text-left font-mono text-xs font-normal uppercase tracking-wider border-r border-white/20 w-[25%]">Lead Entity</th>
                        <th className="h-12 px-6 text-left font-mono text-xs font-normal uppercase tracking-wider border-r border-white/20 w-[20%]">Organization</th>
                        <th className="h-12 px-6 text-left font-mono text-xs font-normal uppercase tracking-wider border-r border-white/20 w-[20%]">Title</th>
                        <th className="h-12 px-6 text-left font-mono text-xs font-normal uppercase tracking-wider border-r border-white/20 w-[15%]">Intent Score</th>
                        <th className="h-12 px-6 text-left font-mono text-xs font-normal uppercase tracking-wider border-r border-white/20 w-[10%]">Status</th>
                        <th className="h-12 px-6 text-right font-mono text-xs font-normal uppercase tracking-wider w-[100px]">Actions</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-ink">
                    {leads.map((lead, i) => (
                        <LedgerRow
                            key={`${lead.lead_id || lead.id || 'L'}-${i}`}
                            lead={{ ...lead, _index: i }}
                            analyzing={analyzing}
                            runAgent={runAgent}
                            deleteLead={deleteLead}
                        />
                    ))}
                </tbody>
            </table>
        </div>
    );
}
