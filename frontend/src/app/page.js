"use client";
import DashboardLayout from "../components/DashboardLayout";
import { useState, useEffect } from "react";

const API = "http://localhost:8000/api";

export default function MissionControl() {
    const [stats, setStats] = useState(null);
    const [targets, setTargets] = useState([]);
    const [activities, setActivities] = useState([]);
    const [pipeline, setPipeline] = useState([]);

    useEffect(() => {
        fetch(`${API}/dashboard/stats`).then(r => r.json()).then(setStats).catch(() => { });
        fetch(`${API}/dashboard/priority-targets`).then(r => r.json()).then(d => setTargets(d.targets || [])).catch(() => { });
        fetch(`${API}/dashboard/activity`).then(r => r.json()).then(d => setActivities(d.activities || [])).catch(() => { });
        fetch(`${API}/dashboard/pipeline`).then(r => r.json()).then(d => setPipeline(d.stages || [])).catch(() => { });
    }, []);

    const kpis = [
        { label: "Total Leads", value: stats?.total_leads?.toLocaleString() || "1,248", icon: "groups", trend: "12%", trendUp: true, subtext: "vs last week", color: "text-ink/60", valueColor: "text-ink" },
        { label: "High Intent", value: "14", icon: "local_fire_department", trend: "4 new", trendUp: true, subtext: "since login", color: "text-primary", valueColor: "text-primary" },
        { label: "Pipeline Value", value: stats ? `$${(stats.pipeline_value / 1e6).toFixed(1)}M` : "$4.2M", icon: "monetization_on", trend: null, subtext: "Projected Q4", color: "text-ink/60", valueColor: "text-ink" },
        { label: "Avg Score", value: "78%", icon: "analytics", bar: 78, color: "text-ink/60", valueColor: "text-ink" },
    ];

    function timeAgo(ts) {
        if (!ts) return "";
        const diff = (Date.now() - new Date(ts).getTime()) / 1000;
        if (diff < 60) return `${Math.floor(diff)}s ago`;
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return `${Math.floor(diff / 86400)}d ago`;
    }

    // Use dummy data if api fails to load targets for visual presentation based on design
    const displayTargets = targets.length > 0 ? targets : [
        { name: "Marcus Thorne", title: "CTO", company: "Nexus Dynamics", score: 92, signal: "Viewed pricing page 4x in last 24h", tags: ["Enterprise", "Decision Maker"], type: "Hot Lead" },
        { name: "Elena Rodriguez", title: "VP Sales", company: "Global Logistics", score: 88, signal: "Downloaded Q3 whitepaper", tags: ["Mid-Market"] },
        { name: "David Chen", title: "Director", company: "FinTech Sol.", score: 85, signal: "LinkedIn connection accepted", tags: ["Rapid Growth"] }
    ];

    // Convert activities to match the design's structured format if we have API data, else use mock
    const displayActivities = activities.length > 0 ? activities : [
        { agent: "RESEARCH_AGENT", time: "10:42:01", text: "Completed deep dive for Nexus Dynamics. Found 3 new news articles regarding Series B funding.", status: "success" },
        { agent: "INTENT_AGENT", time: "10:38:45", text: "High intent signal detected for Marcus Thorne. Intent score spiked +15 pts.", status: "warning" },
        { agent: "EMAIL_STRATEGY", time: "10:35:12", text: "Drafted outreach sequence for Global Logistics based on recent earnings report.", status: "success" },
        { agent: "SYSTEM", time: "10:30:00", text: "Batch upload processed. 15 new leads added to The Ledger.", status: "neutral" },
        { agent: "TIMING_AGENT", time: "10:15:22", text: "Scheduled follow-up for David Chen. Optimal window: Tuesday 14:00.", status: "success" },
    ];

    return (
        <DashboardLayout>
            {/* Page Header */}
            <div className="bg-paper border-b border-ink px-8 py-6 flex flex-col sm:flex-row justify-between sm:items-end gap-4 shrink-0">
                <div>
                    <h2 className="font-display text-4xl font-bold uppercase tracking-tighter leading-none mb-1">Command Center</h2>
                    <p className="font-mono text-sm text-ink/60">Global Overview // <span id="current-date">{new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }).toUpperCase()}</span></p>
                </div>
                <div className="flex gap-4">
                    <button className="h-10 px-6 border border-ink bg-paper hover:bg-mute font-mono text-xs uppercase flex items-center gap-2 transition-colors">
                        <span className="material-symbols-outlined text-[16px]">refresh</span>
                        Refresh Data
                    </button>
                    <button className="h-10 px-6 bg-primary text-white font-mono text-xs uppercase font-bold hover:bg-ink transition-colors flex items-center gap-2">
                        <span className="material-symbols-outlined text-[16px]">add</span>
                        New Campaign
                    </button>
                </div>
            </div>

            <div className="p-8 flex flex-col gap-8 max-w-[1600px] w-full mx-auto">
                {/* Metrics Tickers */}
                <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-0 border border-ink bg-paper divide-y md:divide-y-0 md:divide-x divide-ink">
                    {kpis.map((kpi, i) => (
                        <div key={i} className="p-6 relative group hover:bg-mute transition-colors">
                            <div className="flex justify-between items-start mb-4">
                                <span className={`font-mono text-xs uppercase ${kpi.color} ${kpi.label === 'High Intent' ? 'font-bold' : ''}`}>{kpi.label}</span>
                                <span className={`material-symbols-outlined ${kpi.color} text-[20px]`}>{kpi.icon}</span>
                            </div>
                            <div className={`font-display text-4xl font-bold mb-2 ${kpi.valueColor}`}>{kpi.value}</div>

                            {kpi.bar ? (
                                <div className="w-full h-1 bg-mute mt-4 relative overflow-hidden">
                                    <div className="bg-ink h-full" style={{ width: `${kpi.bar}%` }}></div>
                                </div>
                            ) : (
                                <div className="flex items-center gap-2 font-mono text-xs">
                                    {kpi.trend && (
                                        <span className="text-data-green flex items-center">
                                            <span className="material-symbols-outlined text-[14px]">
                                                {kpi.trendUp ? 'arrow_upward' : 'arrow_downward'}
                                            </span> {kpi.trend}
                                        </span>
                                    )}
                                    <span className="text-ink/40">{kpi.subtext}</span>
                                </div>
                            )}
                            <div className={`absolute bottom-0 left-0 w-full h-1 transition-colors ${kpi.label === 'High Intent' ? 'bg-primary' : 'bg-ink/10 group-hover:bg-primary'}`}></div>
                        </div>
                    ))}
                </section>

                <div className="grid grid-cols-12 gap-8 h-full min-h-[500px]">
                    {/* Priority Targets (Left 8 Cols) */}
                    <div className="col-span-12 lg:col-span-8 flex flex-col gap-6">
                        <div className="flex justify-between items-end border-b-3 border-ink pb-2">
                            <h3 className="font-display text-2xl font-bold uppercase">Priority Targets</h3>
                            <a className="font-mono text-xs uppercase underline hover:text-primary" href="/ledger">View Full Ledger</a>
                        </div>
                        <div className="flex flex-col gap-4">
                            {displayTargets.map((t, i) => (
                                <div key={i} className="bg-paper border border-ink p-0 flex flex-col sm:flex-row group hover:shadow-[4px_4px_0px_0px_rgba(10,10,10,1)] transition-all cursor-pointer">
                                    <div className="w-full sm:w-48 h-48 sm:h-auto border-b sm:border-b-0 sm:border-r border-ink relative overflow-hidden shrink-0 bg-mute flex text-ink/30 items-center justify-center">
                                        <span className="material-symbols-outlined text-[64px] group-hover:scale-110 transition-transform">person</span>
                                        {t.type && (
                                            <div className="absolute top-2 left-2 bg-primary text-white font-mono text-[10px] px-2 py-0.5 font-bold uppercase">{t.type}</div>
                                        )}
                                    </div>
                                    <div className="p-6 flex-1 flex flex-col justify-between">
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <h4 className="font-display text-2xl font-bold">{t.name}</h4>
                                                <p className="font-mono text-sm text-ink/60 mb-1">{t.title} @ {t.company}</p>
                                                <div className="flex flex-wrap gap-2 mt-3">
                                                    {t.tags?.map(tag => (
                                                        <span key={tag} className="px-2 py-1 border border-ink text-[10px] font-mono uppercase bg-mute">{tag}</span>
                                                    ))}
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <div className="font-mono text-xs text-ink/60 uppercase mb-1">Intent Score</div>
                                                <div className={`font-display text-5xl font-bold leading-none ${(t.score || t._score) >= 90 ? 'text-primary' : ''}`}>{t.score || t._score || '--'}</div>
                                            </div>
                                        </div>
                                        <div className="mt-6 flex flex-col xl:flex-row xl:items-center justify-between gap-4 pt-4 border-t border-dashed border-ink/30">
                                            <p className="text-sm font-medium">Recent Signal: <span className="font-normal text-ink/70">{t.signal}</span></p>
                                            <a href={`/intel/${t.index}`} className="px-6 py-2 border border-ink font-mono text-xs uppercase font-bold hover:bg-ink hover:text-white transition-colors flex items-center justify-center gap-2 shrink-0">
                                                Review Intel <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                                            </a>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* The Feed (Right 4 Cols) */}
                    <div className="col-span-12 lg:col-span-4 flex flex-col h-full">
                        <div className="flex justify-between items-end border-b-3 border-ink pb-2 mb-6">
                            <h3 className="font-display text-2xl font-bold uppercase">Agent Activity</h3>
                            <div className="flex items-center gap-2">
                                <span className="w-2 h-2 bg-primary rounded-full animate-pulse"></span>
                                <span className="font-mono text-xs uppercase">Live</span>
                            </div>
                        </div>
                        <div className="bg-ink text-paper p-4 font-mono text-xs uppercase border-b border-white/20">
                            Log Stream // ID: 8821-X
                        </div>
                        <div className="bg-paper border-l border-r border-b border-ink flex-1 overflow-y-auto max-h-[600px] shadow-[4px_4px_0px_0px_rgba(10,10,10,0.1)]">
                            {displayActivities.map((a, i) => (
                                <div key={i} className="p-4 border-b border-ink/10 flex gap-3 hover:bg-mute transition-colors">
                                    <div className="mt-1">
                                        {a.color ? (
                                            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: a.color }}></div>
                                        ) : (
                                            <div className={`w-2 h-2 rounded-full ${a.status === 'success' ? 'bg-data-green' : a.status === 'warning' ? 'bg-primary animate-pulse' : 'bg-ink/30'}`}></div>
                                        )}
                                    </div>
                                    <div className="flex-1">
                                        <div className="flex justify-between mb-1">
                                            <span className="font-bold text-ink">{a.agent}</span>
                                            <span className="text-ink/50">{a.time || timeAgo(a.timestamp)}</span>
                                        </div>
                                        <p className="text-sm normal-case font-body text-ink/80">{a.text || a.action}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </DashboardLayout>
    );
}
