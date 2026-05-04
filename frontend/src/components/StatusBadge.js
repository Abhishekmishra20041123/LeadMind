export function StatusBadge({ status, analyzing = false }) {
    if (analyzing || status === "Processing") {
        return (
            <span className="inline-flex items-center px-2 py-1 border border-ink group-hover:border-paper group-hover:bg-paper group-hover:text-ink bg-white font-mono text-[10px] font-bold uppercase tracking-wide text-primary">
                Processing<span className="animate-pulse">_</span>
            </span>
        );
    }

    if (status === "Ready") {
        return (
            <span className="inline-flex items-center px-2 py-1 border border-ink group-hover:border-paper group-hover:bg-paper group-hover:text-ink bg-white font-mono text-[10px] font-bold uppercase tracking-wide">
                <span className="w-2 h-2 rounded-full bg-[#10b981] mr-2 border border-black group-hover:border-ink"></span>
                Ready
            </span>
        );
    }

    if (status === "Analysis") {
        return (
            <span className="inline-flex items-center px-2 py-1 border border-ink group-hover:border-paper group-hover:bg-paper group-hover:text-ink bg-white font-mono text-[10px] font-bold uppercase tracking-wide">
                <span className="w-2 h-2 rounded-full bg-[#eab308] mr-2 border border-black group-hover:border-ink"></span>
                Analysis
            </span>
        );
    }

    if (status === "Email Dispatched") {
        return (
            <span className="inline-flex items-center px-2 py-1 border border-ink group-hover:border-paper group-hover:bg-paper group-hover:text-ink bg-white font-mono text-[10px] font-bold uppercase tracking-wide">
                <span className="w-2 h-2 rounded-full bg-[#3b82f6] mr-2 border border-black group-hover:border-ink"></span>
                Dispatched
            </span>
        );
    }

    if (status === "Contacted") {
        return (
            <span className="inline-flex items-center px-2 py-1 border border-ink group-hover:border-paper group-hover:bg-paper group-hover:text-ink bg-white font-mono text-[10px] font-bold uppercase tracking-wide">
                <span className="w-2 h-2 rounded-full bg-[#8b5cf6] mr-2 border border-black group-hover:border-ink"></span>
                Contacted
            </span>
        );
    }

    if (status === "New Lead") {
        return (
            <span className="inline-flex items-center px-2 py-1 border border-ink group-hover:border-paper group-hover:bg-paper group-hover:text-ink bg-white font-mono text-[10px] font-bold uppercase tracking-wide">
                <span className="w-2 h-2 rounded-full bg-[#f97316] mr-2 border border-black group-hover:border-ink"></span>
                New Lead
            </span>
        );
    }

    if (status === "Converted") {
        return (
            <span className="inline-flex items-center px-2 py-1 border border-ink group-hover:border-paper group-hover:bg-paper group-hover:text-ink bg-white font-mono text-[10px] font-bold uppercase tracking-wide">
                <span className="w-2 h-2 rounded-full bg-[#10b981] mr-2 border border-black group-hover:border-ink"></span>
                Converted
            </span>
        );
    }

    // Fallback for truly unknown / missing status
    return (
        <span className="inline-flex items-center px-2 py-1 border border-ink group-hover:border-paper group-hover:bg-paper group-hover:text-ink bg-white font-mono text-[10px] font-bold uppercase tracking-wide text-ink/50 group-hover:text-ink">
            <span className="w-2 h-2 rounded-full bg-[#9ca3af] mr-2 border border-black group-hover:border-ink"></span>
            {status || "Unknown"}
        </span>
    );
}
