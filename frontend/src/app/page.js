"use client";
import DashboardLayout from "../components/DashboardLayout";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

const API = "http://localhost:8000/api";

export default function MissionControl() {
    const router = useRouter();
    const [stats, setStats] = useState(null);
    const [targets, setTargets] = useState([]);
    const [activities, setActivities] = useState([]);
    const [pipeline, setPipeline] = useState([]);

    useEffect(() => {
        const token = localStorage.getItem("access_token");
        const headers = token ? { "Authorization": `Bearer ${token}` } : {};

        fetch(`${API}/dashboard/stats`, { headers }).then(r => r.json()).then(setStats).catch(() => { });
        fetch(`${API}/dashboard/priority-targets`, { headers }).then(r => r.json()).then(d => setTargets(d.targets || [])).catch(() => { });
        fetch(`${API}/dashboard/activity`, { headers }).then(r => r.json()).then(d => setActivities(d.activities || [])).catch(() => { });
        fetch(`${API}/dashboard/pipeline`, { headers }).then(r => r.json()).then(d => setPipeline(d.stages || [])).catch(() => { });
    }, []);

    function formatPipelineValue(val) {
        if (!val) return "₹0";
        if (val >= 1e6) return `₹${(val / 1e6).toFixed(1)}M`;
        if (val >= 1e3) return `₹${(val / 1e3).toFixed(1)}K`;
        return `₹${val.toLocaleString()}`;
    }

    const kpis = [
        { label: "Total Leads", value: stats?.total_leads?.toLocaleString() || "0", icon: "groups", trend: "0%", trendUp: true, subtext: "vs last week", color: "text-ink/60", valueColor: "text-ink" },
        { label: "Live Visitors", value: stats?.live_visitors?.toLocaleString() || "0", icon: "sensors", trend: "Active", trendUp: true, subtext: "last 30m", color: "text-blue-600", valueColor: "text-ink" },
        { label: "High Intent", value: stats?.high_intent || "0", icon: "local_fire_department", trend: "0 new", trendUp: true, subtext: "since login", color: "text-primary", valueColor: "text-primary" },
        { label: "Pipeline Value", value: stats ? formatPipelineValue(stats.pipeline_value) : "₹0", icon: "monetization_on", trend: null, subtext: "Projected Q4", color: "text-ink/60", valueColor: "text-ink" },
    ];

    function timeAgo(ts) {
        if (!ts) return "";
        const diff = (Date.now() - new Date(ts).getTime()) / 1000;
        if (diff < 60) return `${Math.floor(diff)}s ago`;
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return `${Math.floor(diff / 86400)}d ago`;
    }



    return (
        <DashboardLayout>
            {/* Page Header */}
            <div className="bg-paper border-b border-ink px-8 py-6 flex flex-col sm:flex-row justify-between sm:items-end gap-4 shrink-0">
                <div>
                    <h2 className="font-display text-4xl font-bold uppercase tracking-tighter leading-none mb-1">Dashboard</h2>
                    {/* <p className="font-mono text-sm text-ink/60">Global Overview // <span id="current-date">{new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }).toUpperCase()}</span></p> */}
                </div>
                <div className="flex gap-4">
                    <button className="h-10 px-6 border border-ink bg-paper hover:bg-mute font-mono text-xs uppercase flex items-center gap-2 transition-colors">
                        <span className="material-symbols-outlined text-[16px]">refresh</span>
                        Refresh Data
                    </button>
                    <button onClick={() => router.push('/upload')} className="h-10 px-6 bg-primary text-white font-mono text-xs uppercase font-bold hover:bg-ink transition-colors flex items-center gap-2">
                        <span className="material-symbols-outlined text-[16px]">add</span>
                        New Leads
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
                            {targets.map((t, i) => (
                                <div key={i} className="bg-paper border border-ink p-0 flex flex-col sm:flex-row group hover:shadow-[4px_4px_0px_0px_rgba(10,10,10,1)] transition-all cursor-pointer">
                                    {/* Accent bar with initials badge — replaces empty avatar placeholder */}
                                    <div className="w-2 sm:w-3 bg-ink shrink-0 relative flex items-center justify-center">
                                        <div className="absolute -right-5 w-10 h-10 bg-primary text-white flex items-center justify-center font-display font-bold text-sm shadow-[2px_2px_0px_0px_rgba(10,10,10,1)] z-10">
                                            {t.name ? t.name.split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase() : "—"}
                                        </div>
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
                                            <a href={`/intel/${t.id}`} className="px-6 py-2 border border-ink font-mono text-xs uppercase font-bold hover:bg-ink hover:text-white transition-colors flex items-center justify-center gap-2 shrink-0">
                                                Review Intel <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                                            </a>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Active Agents (Right 4 Cols) */}
                    <div className="col-span-12 lg:col-span-4 flex flex-col h-full">
                        <div className="flex justify-between items-end border-b-3 border-ink pb-2 mb-6">
                            <h3 className="font-display text-2xl font-bold uppercase">Active Agents</h3>
                            <div className="flex items-center gap-2">
                                <span className="w-2 h-2 bg-data-green animate-pulse"></span>
                                <span className="font-mono text-xs uppercase">Online</span>
                            </div>
                        </div>

                        <div className="flex flex-col gap-4">
                            {[
                                { name: "Web Researcher", icon: "travel_explore", desc: "Scrapes SEC filings, news, and LinkedIn for deep company intel.", color: "text-blue-600" },
                                { name: "Intent Qualifier", icon: "target", desc: "Analyzes digital footprint to compute a 1-100 buying intent score.", color: "text-primary" },
                                { name: "Email Strategist", icon: "mail", desc: "Drafts hyper-personalized outreach based on exact pain points.", color: "text-purple-600" },
                                { name: "Timing Optimizer", icon: "schedule", desc: "Predicts the highest-probability day & time for response.", color: "text-orange-500" },
                                { name: "CRM Logger", icon: "database", desc: "Serializes LangGraph context into structured JSON for MongoDB.", color: "text-data-green" }
                            ].map((agent, i) => (
                                <div key={i} className="bg-paper border border-ink p-4 flex gap-4 group hover:bg-mute transition-all hover:shadow-[4px_4px_0px_0px_rgba(10,10,10,1)] hover:-translate-y-1">
                                    <div className="w-12 h-12 bg-ink text-paper flex items-center justify-center shrink-0">
                                        <span className={`material-symbols-outlined text-[24px]`}>{agent.icon}</span>
                                    </div>
                                    <div className="flex flex-col justify-center">
                                        <div className="flex items-center gap-2 mb-1">
                                            <h4 className="font-display font-bold text-lg leading-none">{agent.name}</h4>
                                            <span className={`material-symbols-outlined text-[14px] ${agent.color}`}>verified</span>
                                        </div>
                                        <p className="font-mono text-xs text-ink/70 leading-snug">{agent.desc}</p>
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
