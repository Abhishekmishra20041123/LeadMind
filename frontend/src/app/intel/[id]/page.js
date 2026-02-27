"use client";
import DashboardLayout from "../../../components/DashboardLayout";
import { useState, useEffect, use } from "react";
// Since this is a detail page, it requires the dynamic ID from the URL.

import { useSearchParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export default function IntelPage({ params }) {
    const unwrappedParams = use(params);
    const id = unwrappedParams.id;
    const searchParams = useSearchParams();
    const batchId = searchParams.get('batch');

    const [target, setTarget] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const queryParams = batchId ? `?batch_id=${batchId}` : '';
        fetch(`${API}/leads/${id}${queryParams}`)
            .then(res => {
                if (!res.ok) throw new Error("Lead not found");
                return res.json();
            })
            .then(data => {
                // Map the new structured backend JSON to the expected visual template
                const fullData = {
                    id: data.lead_id,
                    name: data.profile?.name || "Unknown",
                    title: data.profile?.title || "Unknown",
                    company: data.profile?.company || "Unknown",
                    linkedin: data.profile?.linkedin || "",
                    website: data.profile?.website || "",
                    bio: data.profile?.bio || "",
                    intent: data.agents?.intent?.score || 0,
                    status: data.status || "Ready State",
                    signal: data.agents?.intent?.reasoning || "Pending Analysis",
                    intentRecommendation: data.agents?.intent?.recommendation || {},
                    news: data.agents?.research?.signals || [],
                    timing: {
                        recommended: data.agents?.timing?.recommended || "N/A",
                        recommendedReason: data.agents?.timing?.recommendedReason || "",
                        optimalTimeWindow: data.agents?.timing?.optimal_time_window || "N/A",
                        approach: data.agents?.timing?.approach || {},
                        engagementPrediction: data.agents?.timing?.engagement_prediction || {},
                        timeline: data.agents?.timing?.timeline || {},
                        localTime: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                        events: [
                            { label: "TRIGGER EVENT", desc: "Pipeline Initialized", time: "Just Now", type: "white" }
                        ],
                        targetTime: "11:32 AM (PST)"
                    },
                    draft: Array.isArray(data.agents?.message?.draft) ? data.agents.message.draft : [
                        { type: 'text', content: data.agents?.message?.draft || "Compiling draft..." }
                    ],
                    subject: data.agents?.message?.subject || "No Subject",
                    personalizationFactors: data.agents?.message?.personalization_factors || [],
                    logs: data.agents?.crm?.logs || [
                        { time: "10:41:00", agent: "RESEARCH", action: "Scraped web endpoints.", status: "SUCCESS" },
                        { time: "10:41:12", agent: "INTENT", action: "Calculated Intent Score: 12.0", status: "SUCCESS" },
                        { time: "10:41:55", agent: "STRATEGY", action: "Draft generated via GPT-4", status: "SUCCESS" },
                        { time: "10:42:01", agent: "TIMING", action: "Analyzed 45 historical signals.", status: "SUCCESS" },
                        { time: "10:42:05", agent: "SYSTEM", action: "Graph sequence processing finished.", status: "SUCCESS" }
                    ]
                };
                setTarget(fullData);
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to fetch lead data:", err);
                setLoading(false);
            });
    }, [id, batchId]);

    if (loading || !target) {
        return (
            <DashboardLayout>
                <div className="flex items-center justify-center h-full bg-mute text-ink font-mono animate-pulse">
                    LOADING INTELLIGENCE...
                </div>
            </DashboardLayout>
        );
    }

    return (
        <DashboardLayout>
            <div className="flex flex-col h-full bg-mute">
                {/* Breadcrumbs / Top Bar */}
                <header className="h-16 border-b border-ink bg-white flex items-center justify-between px-8 shrink-0">
                    <div className="flex items-center gap-2 font-mono text-sm">
                        <span className="text-ink/40">MISSION CONTROL</span>
                        <span className="text-ink/30">/</span>
                        <span className="text-ink/40">THE LEDGER</span>
                        <span className="text-ink/30">/</span>
                        <span className="text-primary font-bold">INTELLIGENCE REPORT</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 px-3 py-1 bg-mute border border-ink">
                            <span className="w-2 h-2 rounded-full bg-data-green animate-pulse"></span>
                            <span className="font-mono text-xs font-bold tracking-tight">SYSTEM ONLINE</span>
                        </div>
                        <button className="p-2 hover:bg-mute border border-transparent hover:border-ink transition-colors">
                            <span className="material-symbols-outlined text-xl">notifications</span>
                        </button>
                    </div>
                </header>

                {/* Scrollable Content */}
                <div className="flex-1 overflow-y-auto p-8 relative">
                    <div className="max-w-[1600px] mx-auto flex flex-col gap-6">
                        {/* Header Section: Identity & Intent */}
                        <section className="grid grid-cols-12 gap-6 items-stretch">
                            {/* Identity Block */}
                            <div className="col-span-12 lg:col-span-8 bg-paper border border-ink p-8 flex flex-col justify-center shadow-sm relative group">
                                <div className="absolute top-0 right-0 bg-ink text-paper px-3 py-1 font-mono text-xs uppercase tracking-widest">Target Acquired</div>
                                <div className="flex items-start justify-between">
                                    <div className="flex flex-col gap-1">
                                        <h1 className="font-display font-bold text-5xl uppercase tracking-tighter text-ink">{target.name}</h1>
                                        <div className="flex items-center gap-3 mt-2">
                                            <span className="font-mono text-lg bg-mute px-2 py-1 border border-ink">{target.title}</span>
                                            <span className="text-ink/40 font-light text-2xl">@</span>
                                            <span className="font-display font-bold text-2xl text-ink">{target.company}</span>
                                        </div>
                                        <div className="flex gap-4 mt-6">
                                            <a className="flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors border-b border-ink/20 hover:border-primary pb-0.5" href="#">
                                                <span className="material-symbols-outlined text-lg">link</span>
                                                {target.linkedin}
                                            </a>
                                            <span className="text-ink/30">|</span>
                                            <a className="flex items-center gap-2 text-sm font-medium hover:text-primary transition-colors border-b border-ink/20 hover:border-primary pb-0.5" href="#">
                                                <span className="material-symbols-outlined text-lg">language</span>
                                                {target.website}
                                            </a>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            {/* Intent Gauge (Agent 2) */}
                            <div className="col-span-12 lg:col-span-4 bg-paper border border-ink p-6 flex flex-col relative overflow-hidden">
                                <div className="flex justify-between items-start mb-2">
                                    <h2 className="font-display font-bold text-lg text-ink">AGENT_02: INTENT</h2>
                                    <span className="material-symbols-outlined text-primary animate-spin" style={{ animationDuration: '3s' }}>settings</span>
                                </div>
                                <div className="flex-1 flex flex-col items-center justify-center relative mt-4">
                                    {/* Gauge SVG equivalent using Tailwind */}
                                    <div className="relative w-48 h-24 overflow-hidden">
                                        <div className="absolute w-48 h-48 rounded-full border-[12px] border-mute top-0 left-0"></div>
                                        <div className="absolute w-48 h-48 rounded-full border-[12px] border-primary top-0 left-0 border-b-0 border-l-0 border-r-transparent origin-center" style={{ clipPath: 'polygon(0 0, 100% 0, 100% 50%, 0 50%)', transform: 'rotate(158deg)' }}></div>
                                    </div>
                                    <div className="absolute bottom-0 flex flex-col items-center">
                                        <span className="font-mono text-6xl font-bold text-ink leading-none">{target.intent}</span>
                                        <span className="font-mono text-xs text-primary uppercase tracking-widest mt-1">{target.status}</span>
                                    </div>
                                </div>
                                <div className="mt-4 pt-4 border-t border-dashed border-ink/30 flex flex-col gap-3 font-mono text-xs">
                                    <div className="flex justify-between items-start gap-2">
                                        <span className="text-ink/50 w-24 shrink-0">SIGNALS</span>
                                        <span className="text-ink font-bold text-right leading-tight max-h-[80px] overflow-y-auto">{target.signal}</span>
                                    </div>
                                    <div className="flex justify-between items-start gap-2">
                                        <span className="text-ink/50 w-24 shrink-0">ACTION</span>
                                        <div className="flex flex-col items-end gap-1">
                                            <span className="text-ink font-bold text-right leading-tight text-primary text-[11px]">{target.intentRecommendation.next_best_action || "Awaiting strategy"}</span>
                                            <span className="bg-mute px-1.5 py-0.5 border border-ink/20 inline-block text-[10px]">URGENCY: {target.intentRecommendation.urgency || "Unknown"}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Main Grid: 3 Columns */}
                        <section className="grid grid-cols-12 gap-6 min-h-[600px]">
                            {/* Column 1: Research (Agent 1) */}
                            <div className="col-span-12 lg:col-span-3 flex flex-col gap-6">
                                <div className="bg-paper border border-ink h-full flex flex-col">
                                    <div className="p-4 border-b border-ink bg-mute flex justify-between items-center">
                                        <h3 className="font-display font-bold text-sm tracking-wide">AGENT_01: RESEARCH</h3>
                                        <span className="material-symbols-outlined text-ink text-sm">person_search</span>
                                    </div>
                                    <div className="p-6 flex flex-col gap-6 flex-1">
                                        {/* Photo - using a solid color as placeholder for the external image */}
                                        <div className="w-full aspect-square bg-mute border border-ink relative overflow-hidden group transition-all duration-500 flex items-center justify-center text-ink/20">
                                            <span className="material-symbols-outlined text-6xl">person</span>
                                            <div className="absolute bottom-0 left-0 bg-ink text-paper px-2 py-1 font-mono text-xs">IMG_REF_001</div>
                                        </div>
                                        {/* Bio */}
                                        <div className="flex flex-col gap-2">
                                            <h4 className="font-mono text-xs text-ink/40 uppercase">Subject Bio</h4>
                                            <p className="text-sm leading-relaxed text-ink/80">{target.bio}</p>
                                        </div>
                                        {/* News Hits */}
                                        <div className="flex flex-col gap-3">
                                            <h4 className="font-mono text-xs text-ink/40 uppercase">Intelligence Hits</h4>
                                            <ul className="flex flex-col gap-2">
                                                {target.news.map((item, i) => (
                                                    <li key={i} className="flex gap-2 items-start text-sm group cursor-pointer">
                                                        <span className="text-primary mt-1">●</span>
                                                        <span className="group-hover:underline decoration-primary underline-offset-4">{item}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Column 2: Timing (Agent 4) */}
                            <div className="col-span-12 lg:col-span-3 flex flex-col gap-6">
                                <div className="bg-paper border border-ink h-full flex flex-col">
                                    <div className="p-4 border-b border-ink bg-mute flex justify-between items-center">
                                        <h3 className="font-display font-bold text-sm tracking-wide">AGENT_04: TIMING</h3>
                                        <span className="material-symbols-outlined text-ink text-sm">schedule</span>
                                    </div>
                                    <div className="p-6 relative flex-1">
                                        {/* Vertical Line */}
                                        <div className="absolute left-10 top-6 bottom-6 w-px bg-ink"></div>
                                        <div className="flex flex-col gap-8 relative z-10 pl-2">
                                            {/* Item 1: Active */}
                                            <div className="flex items-start gap-4">
                                                <div className="w-6 h-6 rounded-none border border-ink bg-primary flex items-center justify-center shrink-0 shadow-[2px_2px_0px_0px_rgba(10,10,10,1)]">
                                                    <span className="material-symbols-outlined text-white text-[16px]">bolt</span>
                                                </div>
                                                <div className="flex flex-col pt-0.5 mt-[-2px]">
                                                    <span className="font-mono text-xs font-bold text-primary uppercase tracking-wider mb-1">RECOMMENDED WINDOW</span>
                                                    <span className="font-display font-bold text-lg leading-tight">{target.timing.optimalTimeWindow}</span>
                                                    <span className="font-mono text-xs text-ink/70 mt-1">Send at: {target.timing.recommended}</span>
                                                    <p className="text-xs text-ink/50 mt-1">{target.timing.recommendedReason}</p>
                                                </div>
                                            </div>
                                            {/* Item 2: Approach Type */}
                                            <div className="flex items-start gap-4 opacity-80 mt-2">
                                                <div className="w-6 h-6 rounded-none border border-ink bg-paper flex items-center justify-center shrink-0">
                                                    <div className={`w-2 h-2 bg-ink`}></div>
                                                </div>
                                                <div className="flex flex-col pt-0.5 mt-[-2px] w-full">
                                                    <span className="font-mono text-xs font-bold text-ink/50 uppercase tracking-wider mb-1">APPROACH STRATEGY</span>
                                                    <span className="font-body font-medium text-sm text-primary">{target.timing.approach?.type || "Standard"} (Urgency: {target.timing.approach?.urgency || 0})</span>
                                                    <ul className="text-xs text-ink/60 mt-1 list-disc pl-4">
                                                        {target.timing.approach?.content_suggestions?.map((s, idx) => (
                                                            <li key={idx}>{s}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            </div>
                                            {/* Item 3: Predictive */}
                                            <div className="flex items-start gap-4 opacity-60">
                                                <div className="w-6 h-6 rounded-none border border-ink bg-paper flex items-center justify-center shrink-0">
                                                    <div className={`w-2 h-2 bg-ink/40`}></div>
                                                </div>
                                                <div className="flex flex-col pt-0.5 mt-[-2px] w-full">
                                                    <span className="font-mono text-xs font-bold text-ink/50 uppercase tracking-wider mb-1">PREDICTION MODEL</span>
                                                    <div className="flex justify-between items-center text-xs mt-1">
                                                        <span className="font-medium text-ink/80">Resp. Prob:</span>
                                                        <span className="font-mono ml-2">{(target.timing.engagementPrediction?.response_probability * 100 || 0).toFixed(0)}%</span>
                                                    </div>
                                                    <div className="flex justify-between items-center text-xs">
                                                        <span className="font-medium text-ink/80">Est. Delay:</span>
                                                        <span className="font-mono ml-2">{target.timing.engagementPrediction?.expected_delay || 0} hrs</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        {/* Windows Widget Style at bottom */}
                                        <div className="absolute bottom-6 left-6 right-6 border border-ink p-3 bg-mute/50">
                                            <div className="flex justify-between items-center mb-2">
                                                <span className="font-mono text-[10px] uppercase">Timeline Logs</span>
                                                <span className="w-2 h-2 bg-data-green rounded-full animate-pulse"></span>
                                            </div>
                                            <div className="font-mono text-xs text-ink/60">
                                                Init: {target.timing.timeline?.first_contact ? new Date(target.timing.timeline.first_contact).toLocaleDateString() : "N/A"}<br />
                                                Next: {target.timing.timeline?.next_followup || "N/A"}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Column 3: Strategy (Agent 3) - Takes up remaining space */}
                            <div className="col-span-12 lg:col-span-6 flex flex-col gap-6">
                                <div className="bg-paper border border-ink h-full flex flex-col shadow-lg relative">
                                    <div className="p-4 border-b border-ink bg-ink text-paper flex justify-between items-center">
                                        <div className="flex items-center gap-2">
                                            <span className="material-symbols-outlined text-sm">terminal</span>
                                            <h3 className="font-display font-bold text-sm tracking-wide">AGENT_03: STRATEGY_TERMINAL</h3>
                                        </div>
                                        <div className="flex gap-2">
                                            <div className="w-3 h-3 rounded-full bg-primary border border-white"></div>
                                            <div className="w-3 h-3 rounded-full bg-yellow-500 border border-white"></div>
                                            <div className="w-3 h-3 rounded-full bg-data-green border border-white"></div>
                                        </div>
                                    </div>
                                    <div className="flex flex-col flex-1 relative bg-mute/20">
                                        {/* Toolbar */}
                                        <div className="flex items-center justify-between px-4 py-2 border-b border-ink/20 bg-paper">
                                            <div className="flex gap-4 font-mono text-xs text-ink/50">
                                                <span className="cursor-pointer hover:text-ink">mode: edit</span>
                                                <span className="cursor-pointer hover:text-ink">encoding: utf-8</span>
                                                <span className="cursor-pointer hover:text-ink text-primary">ai_model: gpt-4-turbo</span>
                                            </div>
                                            <button className="text-xs font-mono border-b border-ink hover:text-primary transition-colors">
                                                Clear Buffer
                                            </button>
                                        </div>
                                        {/* Content Editable Area */}
                                        <div className="flex-1 p-6 font-mono text-sm leading-relaxed text-ink/80 focus:outline-none overflow-y-auto" contentEditable suppressContentEditableWarning>
                                            <div className="mb-4 pb-2 border-b border-ink/20 font-bold">
                                                Subject: {target.subject}
                                            </div>
                                            {target.draft.map((line, i) => {
                                                if (line.type === 'br') return <br key={i} />;
                                                if (line.type === 'html') return <div key={i} className="mb-4 text-ink/50 select-none" dangerouslySetInnerHTML={{ __html: line.content }} />;
                                                return <p key={i} dangerouslySetInnerHTML={{ __html: line.content }}></p>;
                                            })}
                                        </div>
                                        {/* Actions Footer */}
                                        <div className="p-4 border-t border-ink bg-paper flex justify-between items-center gap-4">
                                            <button className="flex items-center gap-2 px-4 py-2 border border-ink hover:bg-mute transition-colors font-display font-medium text-sm">
                                                <span className="material-symbols-outlined text-lg">autorenew</span>
                                                REGENERATE
                                            </button>
                                            <div className="flex gap-2">
                                                <button className="flex items-center gap-2 px-4 py-2 border border-ink hover:bg-mute transition-colors font-display font-medium text-sm">
                                                    <span className="material-symbols-outlined text-lg">content_copy</span>
                                                    COPY
                                                </button>
                                                <button className="flex items-center gap-2 px-6 py-2 bg-primary text-white border border-ink hover:bg-ink transition-colors font-display font-bold text-sm shadow-[4px_4px_0px_0px_rgba(10,10,10,1)] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]">
                                                    <span className="material-symbols-outlined text-lg">send</span>
                                                    APPROVE & LOG
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Footer: Audit Trail (Agent 5) */}
                        <section className="border border-ink bg-paper mt-4">
                            <details className="group" open>
                                <summary className="flex items-center justify-between p-4 cursor-pointer bg-mute hover:bg-mute/80 transition-colors list-none select-none">
                                    <div className="flex items-center gap-3">
                                        <span className="material-symbols-outlined text-ink group-open:rotate-180 transition-transform">expand_more</span>
                                        <h3 className="font-display font-bold text-sm tracking-wide uppercase">AGENT_05: AUDIT TRAIL & CRM LOGS</h3>
                                    </div>
                                    <div className="flex gap-4 font-mono text-xs text-ink/50">
                                        <span>SYNCED: JUST NOW</span>
                                        <span>SOURCE: SALESFORCE</span>
                                    </div>
                                </summary>
                                <div className="p-0 border-t border-ink">
                                    <table className="w-full text-left font-mono text-xs">
                                        <thead className="bg-mute/40 text-ink/50 border-b border-ink/20">
                                            <tr>
                                                <th className="p-3 font-medium w-32">TIMESTAMP</th>
                                                <th className="p-3 font-medium w-32">AGENT</th>
                                                <th className="p-3 font-medium">ACTION</th>
                                                <th className="p-3 font-medium w-32">STATUS</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-ink/10">
                                            {target.logs.map((log, i) => (
                                                <tr key={i} className="hover:bg-mute/50 transition-colors">
                                                    <td className="p-3 text-ink/40">{log.time}</td>
                                                    <td className={`p-3 font-bold ${log.agent === 'STRATEGY' ? 'text-primary' : 'text-ink'}`}>{log.agent}</td>
                                                    <td className="p-3">{log.action}</td>
                                                    <td className="p-3">
                                                        {log.status === 'SUCCESS' ? (
                                                            <span className="bg-data-green/10 text-data-green px-1.5 py-0.5 border border-data-green/20">{log.status}</span>
                                                        ) : (
                                                            <span className="bg-mute text-ink/60 px-1.5 py-0.5 border border-ink/20">{log.status}</span>
                                                        )}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </details>
                        </section>
                    </div>
                </div>
            </div>
        </DashboardLayout>
    );
}
