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
    const [isSending, setIsSending] = useState(false);
    const [isRegenerating, setIsRegenerating] = useState(false);
    const [engagement, setEngagement] = useState(null);
    const [templates, setTemplates] = useState([]);
    const [selectedTemplate, setSelectedTemplate] = useState("");

    // Live Preview State
    const [rawEditorContent, setRawEditorContent] = useState("");
    const [previewHtml, setPreviewHtml] = useState(null);
    const [isLoadingPreview, setIsLoadingPreview] = useState(false);

    const handleRegenerate = async () => {
        if (!target) return;
        setIsRegenerating(true);
        try {
            const res = await fetch(`${API}/agents/regenerate/${id}/email_strategy`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${localStorage.getItem("access_token")}`
                }
            });
            if (!res.ok) throw new Error("Failed to regenerate email strategy");

            // Quick reload to show the new draft and updated CRM logs
            window.location.reload();

        } catch (e) {
            console.error("Regeneration failed", e);
            alert("Regeneration failed: " + e.message);
        } finally {
            setIsRegenerating(false);
        }
    };

    const fetchPreview = async (templateId, contentToPreview) => {
        if (!templateId) {
            setPreviewHtml(null);
            return;
        }
        setIsLoadingPreview(true);
        try {
            const token = localStorage.getItem("access_token");
            const res = await fetch(`${API}/leads/${id}/preview-template`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ template_id: templateId, content: contentToPreview })
            });
            const data = await res.json();
            setPreviewHtml(data.html);
        } catch (e) {
            console.error("Preview fetch failed:", e);
        } finally {
            setIsLoadingPreview(false);
        }
    };

    const handleTemplateChange = (e) => {
        const newTemplateId = e.target.value;
        const currentContent = document.getElementById("email-editor")?.innerHTML || rawEditorContent;
        if (currentContent !== rawEditorContent) {
            setRawEditorContent(currentContent);
        }
        setSelectedTemplate(newTemplateId);
        fetchPreview(newTemplateId, currentContent);
    };

    const handleApproveEmail = async () => {
        if (!target) return;
        if (target.emailSent) {
            alert("Email was already sent to this lead. Use force send if you need to re-send.");
            return;
        }
        setIsSending(true);
        try {
            let contentBody = "";
            let finalTemplateId = selectedTemplate || null;

            if (previewHtml) {
                const iframeDoc = document.getElementById("email-preview-iframe")?.contentDocument;
                if (iframeDoc && iframeDoc.body.innerHTML.trim() !== "") {
                    contentBody = iframeDoc.documentElement.outerHTML;
                    finalTemplateId = null; // HTML is already wrapped
                } else {
                    contentBody = rawEditorContent || target.draft.map(d => d.content).join("");
                }
            } else {
                contentBody = document.getElementById("email-editor")?.innerHTML || rawEditorContent || target.draft.map(d => d.content).join("");
            }

            const res = await fetch(`${API}/leads/${id}/approve-email`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${localStorage.getItem("access_token")}`
                },
                body: JSON.stringify({
                    subject: target.subject,
                    content: contentBody,
                    to_email: target.email || "mishraabhishek1703@gmail.com",
                    template_id: finalTemplateId
                })
            });
            if (res.status === 409) {
                const err = await res.json();
                const sentDate = err.detail?.sent_at ? new Date(err.detail.sent_at).toLocaleString() : "earlier";
                alert(`This email was already sent on ${sentDate}. No duplicate sent.`);
                window.location.reload();
                return;
            }
            if (!res.ok) throw new Error("Failed to dispatch email");
            alert("Email dispatched successfully and logged to CRM!");
            window.location.reload();
        } catch (e) {
            console.error("Email dispatch failed", e);
            alert("Delivery failed: " + e.message);
        } finally {
            setIsSending(false);
        }
    };

    const handleDeleteLead = async () => {
        if (!confirm(`Are you sure you want to delete lead ${target?.name}? This action cannot be undone.`)) return;
        try {
            const res = await fetch(`${API}/leads/${id}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` }
            });
            if (!res.ok) throw new Error("Delete failed");
            alert("Lead deleted successfully.");
            window.location.href = "/ledger";
        } catch (e) {
            console.error(e);
            alert("Failed to delete lead: " + e.message);
        }
    };

    useEffect(() => {
        const queryParams = batchId ? `?batch_id=${batchId}` : '';
        const token = localStorage.getItem("access_token");
        const headers = { "Authorization": `Bearer ${token}` };

        // Fetch lead details
        fetch(`${API}/leads/${id}${queryParams}`, { headers })
            .then(res => {
                if (!res.ok) throw new Error("Lead not found");
                return res.json();
            })
            .then(data => {
                // Map the new structured backend JSON to the expected visual template
                const fullData = {
                    id: data.lead_id,
                    email: data.email || "",
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
                        events: data.agents?.timing?.events || [],
                        targetTime: data.agents?.timing?.targetTime || "Unknown"
                    },
                    draft: Array.isArray(data.agents?.message?.draft) ? data.agents.message.draft : [
                        { type: 'text', content: data.agents?.message?.draft || "Compiling draft..." }
                    ],
                    subject: data.agents?.message?.subject || "No Subject",
                    personalizationFactors: data.agents?.message?.personalization_factors || [],
                    logs: data.agents?.crm?.logs || [],
                    emailSent: data.email_sent || false,
                    lastSentAt: data.last_sent_at || null,
                };
                setTarget(fullData);
                setLoading(false);

                // Initialize raw editor content
                if (!rawEditorContent) {
                    let html = fullData.draft.map((line) => {
                        if (line.type === 'br') return '<br/>';
                        // type='html' means the backend sent a full HTML block (e.g. email with product cards).
                        // Render it as-is WITHOUT any fading or select-none classes.
                        if (line.type === 'html') return line.content;
                        return `<p>${line.content}</p>`;
                    }).join("");
                    setRawEditorContent(html);
                }

            })
            .catch(err => {
                console.error("Failed to fetch lead data:", err);
                setLoading(false);
            });

        // Fetch email engagement stats
        fetch(`${API}/leads/${id}/email-engagement`, { headers })
            .then(res => res.json())
            .then(data => setEngagement(data))
            .catch(err => console.error("Failed to fetch engagement:", err));

        // Fetch available templates
        fetch(`${API}/templates/`, { headers })
            .then(res => res.json())
            .then(data => {
                const fetchedTemplates = data.templates || [];
                setTemplates(fetchedTemplates);
                if (fetchedTemplates.length > 0 && !selectedTemplate) {
                    const defaultTemplate = fetchedTemplates[0]._id;
                    setSelectedTemplate(defaultTemplate);
                    // fetchPreview will be triggered by a separate useEffect so it gets the initialized rawEditorContent
                }
            })
            .catch(err => console.error("Failed to fetch templates:", err));

        // Auto-refresh engagement stats every 5 seconds for a "live" feel
        const interval = setInterval(() => {
            fetch(`${API}/leads/${id}/email-engagement`, { headers })
                .then(res => res.json())
                .then(data => setEngagement(data))
                .catch(() => { });
        }, 5000);

        return () => clearInterval(interval);
    }, [id, batchId]);

    // Setup initial preview once templates and content are fetched
    useEffect(() => {
        if (selectedTemplate && rawEditorContent && !previewHtml && !isLoadingPreview) {
            fetchPreview(selectedTemplate, rawEditorContent);
        }
    }, [selectedTemplate, rawEditorContent]);

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
                <header className="h-16 border-b border-ink glass-effect flex items-center justify-between px-8 shrink-0 sticky top-0 z-50 transition-premium shadow-sm">
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
                            <div className="col-span-12 lg:col-span-8 bg-paper border border-ink p-8 flex flex-col justify-center shadow-premium hover:shadow-premium-hover transition-premium relative group">
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
                            <div className="col-span-12 lg:col-span-4 bg-paper border border-ink p-6 flex flex-col relative overflow-hidden shadow-premium hover:shadow-premium-hover transition-premium">
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

                        {/* Middle Section: Email Engagement Tracker (Always visible if email sent) */}
                        {engagement && engagement.email_sent && (
                            <section className="glass-effect border border-ink p-6 relative shadow-premium hover:shadow-premium-hover transition-premium">
                                <div className="absolute top-0 right-0 bg-primary/10 text-primary px-3 py-1 font-mono text-xs uppercase tracking-widest border-b border-l border-primary/20">
                                    LIVE TRACKING
                                </div>
                                <div className="flex items-center gap-2 mb-6">
                                    <span className="material-symbols-outlined text-ink">query_stats</span>
                                    <h3 className="font-display font-bold text-lg uppercase tracking-wide">Email Engagement (Live)</h3>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 divide-y md:divide-y-0 md:divide-x divide-ink/20 font-mono">
                                    <div className="flex flex-col gap-1 pr-4">
                                        <span className="text-xs text-ink/50 uppercase">Open Rate</span>
                                        <div className="flex items-baseline gap-2">
                                            <span className={`text-3xl font-bold ${engagement.open_count > 0 ? "text-primary" : "text-ink"}`}>
                                                {engagement.open_count > 0 ? "100%" : "0%"}
                                            </span>
                                            <span className="text-sm text-ink/50">({engagement.open_count} opens)</span>
                                        </div>
                                    </div>
                                    <div className="flex flex-col gap-1 md:pl-6 pr-4">
                                        <span className="text-xs text-ink/50 uppercase">Click Rate</span>
                                        <div className="flex items-baseline gap-2">
                                            <span className={`text-3xl font-bold ${engagement.click_count > 0 ? "text-data-green" : "text-ink"}`}>
                                                {engagement.click_count > 0 ? "100%" : "0%"}
                                            </span>
                                            <span className="text-sm text-ink/50">({engagement.click_count} clicks)</span>
                                        </div>
                                    </div>
                                    <div className="flex flex-col gap-1 md:pl-6 pr-4">
                                        <span className="text-xs text-ink/50 uppercase">First Activity</span>
                                        <span className="text-sm font-bold text-ink">
                                            {engagement.first_opened_at || engagement.first_clicked_at 
                                                ? new Date(engagement.first_opened_at || engagement.first_clicked_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) 
                                                : "—"}
                                        </span>
                                    </div>
                                    <div className="flex flex-col gap-1 md:pl-6">
                                        <span className="text-xs text-ink/50 uppercase">Last Activity</span>
                                        <span className="text-sm font-bold text-ink">
                                            {engagement.last_opened_at || engagement.last_clicked_at 
                                                ? new Date(engagement.last_opened_at || engagement.last_clicked_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) 
                                                : "—"}
                                        </span>
                                    </div>
                                </div>
                            </section>
                        )}

                        {/* Main Grid: 3 Columns */}
                        <section className="grid grid-cols-12 gap-6 min-h-[600px]">
                            {/* Column 1: Research (Agent 1) */}
                            <div className="col-span-12 lg:col-span-3 flex flex-col gap-6">
                                <div className="bg-paper border border-ink h-full flex flex-col shadow-premium hover:shadow-premium-hover transition-premium">
                                    <div className="p-4 border-b border-ink bg-mute flex justify-between items-center">
                                        <h3 className="font-display font-bold text-sm tracking-wide">AGENT_01: RESEARCH</h3>
                                        <span className="material-symbols-outlined text-ink text-sm">person_search</span>
                                    </div>
                                    <div className="p-6 flex flex-col gap-6 flex-1">
                                        {/* Identity Card — replaces empty avatar box */}
                                        <div className="w-full border border-ink bg-ink text-paper p-5 flex flex-col gap-4 relative overflow-hidden">
                                            {/* Decorative grid lines */}
                                            <div className="absolute inset-0 opacity-5" style={{ backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 24px, #fff 24px, #fff 25px), repeating-linear-gradient(90deg, transparent, transparent 24px, #fff 24px, #fff 25px)' }} />
                                            {/* Initials badge */}
                                            <div className="relative flex items-center gap-4">
                                                <div className="w-16 h-16 bg-primary flex items-center justify-center shrink-0 shadow-[4px_4px_0px_0px_rgba(255,255,255,0.2)]">
                                                    <span className="font-display font-bold text-3xl text-white leading-none">
                                                        {target?.name ? target.name.split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase() : "—"}
                                                    </span>
                                                </div>
                                                <div className="flex flex-col gap-0.5 min-w-0">
                                                    <span className="font-mono text-[9px] uppercase tracking-widest text-paper/40">Subject</span>
                                                    <span className="font-display font-bold text-lg leading-tight text-paper truncate">{target.name}</span>
                                                    <span className="font-mono text-[10px] text-paper/60 truncate">{target.title}</span>
                                                </div>
                                            </div>
                                            {/* Key data rows */}
                                            <div className="relative flex flex-col gap-2 pt-3 border-t border-paper/10 font-mono text-[10px]">
                                                <div className="flex justify-between items-center">
                                                    <span className="text-paper/40 uppercase tracking-wider">Company</span>
                                                    <span className="text-paper font-bold uppercase">{target.company}</span>
                                                </div>
                                                {target.email && (
                                                    <div className="flex justify-between items-center">
                                                        <span className="text-paper/40 uppercase tracking-wider">Email</span>
                                                        <span className="text-paper truncate max-w-[140px]">{target.email}</span>
                                                    </div>
                                                )}
                                                <div className="flex justify-between items-center">
                                                    <span className="text-paper/40 uppercase tracking-wider">Status</span>
                                                    <span className="text-primary font-bold">{target.status || "Active"}</span>
                                                </div>
                                            </div>
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
                                <div className="bg-paper border border-ink h-full flex flex-col shadow-premium hover:shadow-premium-hover transition-premium">
                                    <div className="p-4 border-b border-ink bg-mute flex justify-between items-center">
                                        <h3 className="font-display font-bold text-sm tracking-wide">AGENT_04: TIMING</h3>
                                        <span className="material-symbols-outlined text-ink text-sm">schedule</span>
                                    </div>
                                    <div className="p-6 relative flex-1 flex flex-col">
                                        <div className="flex-1 relative">
                                            {/* Vertical Line */}
                                            <div className="absolute left-4 top-0 bottom-0 w-px bg-ink/10"></div>
                                            <div className="flex flex-col gap-8 relative z-10 pl-0">
                                                {/* Item 1: Active */}
                                                <div className="flex items-start gap-4">
                                                    <div className="w-8 h-8 rounded-none border border-ink bg-primary flex items-center justify-center shrink-0 shadow-[2px_2px_0px_0px_rgba(10,10,10,1)] hover:shadow-glow-primary transition-premium">
                                                        <span className="material-symbols-outlined text-white text-[18px]">bolt</span>
                                                    </div>
                                                    <div className="flex flex-col pt-0.5 mt-[-2px]">
                                                        <span className="font-mono text-xs font-bold text-primary uppercase tracking-wider mb-1">RECOMMENDED WINDOW</span>
                                                        <span className="font-display font-bold text-lg leading-tight">{target.timing.optimalTimeWindow}</span>
                                                        <span className="font-mono text-xs text-ink/70 mt-1">Send at: {target.timing.recommended}</span>
                                                        <p className="text-xs text-ink/50 mt-1 italic leading-relaxed">{target.timing.recommendedReason}</p>
                                                    </div>
                                                </div>
                                                {/* Item 2: Approach Type */}
                                                <div className="flex items-start gap-4 opacity-90">
                                                    <div className="w-8 h-8 rounded-none border border-ink bg-white flex items-center justify-center shrink-0 shadow-[2px_2px_0px_0px_rgba(10,10,10,0.2)]">
                                                        <div className={`w-2.5 h-2.5 bg-ink`}></div>
                                                    </div>
                                                    <div className="flex flex-col pt-0.5 mt-[-2px] w-full">
                                                        <span className="font-mono text-xs font-bold text-ink/50 uppercase tracking-wider mb-1">APPROACH STRATEGY</span>
                                                        <span className="font-body font-bold text-sm text-primary">{target.timing.approach?.type || "Standard"} <span className="text-ink/40 font-mono text-[10px]">(Urgency: {target.timing.approach?.urgency || 0})</span></span>
                                                        <ul className="text-[11px] text-ink/60 mt-2 space-y-1 pl-0">
                                                            {target.timing.approach?.content_suggestions?.map((s, idx) => (
                                                                <li key={idx} className="flex gap-2 items-start">
                                                                    <span className="text-primary mt-1">›</span>
                                                                    <span>{s}</span>
                                                                </li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                </div>
                                                {/* Item 3: Predictive */}
                                                <div className="flex items-start gap-4 opacity-80">
                                                    <div className="w-8 h-8 rounded-none border border-ink bg-white flex items-center justify-center shrink-0 shadow-[2px_2px_0px_0px_rgba(10,10,10,0.1)]">
                                                        <div className={`w-2.5 h-2.5 bg-ink/30`}></div>
                                                    </div>
                                                    <div className="flex flex-col pt-0.5 mt-[-2px] w-full">
                                                        <span className="font-mono text-xs font-bold text-ink/50 uppercase tracking-wider mb-1">PREDICTION MODEL</span>
                                                        <div className="grid grid-cols-2 gap-4 mt-1">
                                                            <div className="flex flex-col">
                                                                <span className="text-[10px] text-ink/40 uppercase">Resp. Prob</span>
                                                                <span className="font-mono text-sm">{(target.timing.engagementPrediction?.response_probability * 100 || 0).toFixed(0)}%</span>
                                                            </div>
                                                            <div className="flex flex-col">
                                                                <span className="text-[10px] text-ink/40 uppercase">Est. Delay</span>
                                                                <span className="font-mono text-sm">{target.timing.engagementPrediction?.expected_delay || 0} hrs</span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Timeline Logs Widget - Moved into the flex flow */}
                                        {(() => {
                                            const executedLog = target.logs?.find(l =>
                                                l.agent === "SCHEDULER" && l.action?.includes("Executed")
                                            );
                                            const dispatched = !!executedLog;
                                            return (
                                                <div className={`mt-8 border p-4 transition-premium shadow-sm ${dispatched ? "border-data-green bg-data-green/5" : "border-ink/20 bg-mute/30"
                                                    }`}>
                                                    <div className="flex justify-between items-center mb-3">
                                                        <span className="font-mono text-[10px] uppercase font-bold tracking-widest text-ink/50">
                                                            {dispatched ? "Status: Dispatched" : "System Feed"}
                                                        </span>
                                                        {dispatched
                                                            ? <span className="material-symbols-outlined text-data-green text-lg animate-pulse">check_circle</span>
                                                            : <span className="w-2 h-2 bg-data-green rounded-full animate-pulse shadow-glow-blue"></span>
                                                        }
                                                    </div>
                                                    {dispatched ? (
                                                        <div className="font-mono text-[11px] leading-relaxed">
                                                            <span className="text-data-green font-bold uppercase tracking-wider block mb-1">FOLLOW-UP EXECUTED ✓</span>
                                                            <span className="text-ink/60">{executedLog.time} — {executedLog.action?.replace("Executed scheduled follow-up: ", "")}</span>
                                                        </div>
                                                    ) : (
                                                        <div className="font-mono text-[11px] text-ink/60 space-y-1">
                                                            <div className="flex justify-between border-b border-ink/5 pb-1">
                                                                <span>INIT</span>
                                                                <span className="text-ink font-medium">{target.timing.timeline?.first_contact ? new Date(target.timing.timeline.first_contact).toLocaleDateString() : "N/A"}</span>
                                                            </div>
                                                            <div className="flex justify-between pt-1">
                                                                <span>NEXT</span>
                                                                <span className="text-primary font-bold">
                                                                    {target.status === "Email Dispatched"
                                                                        ? target.timing.timeline?.next_followup
                                                                            ? new Date(target.timing.timeline.next_followup).toLocaleString([], { weekday: 'short', day: 'numeric', month: 'short' })
                                                                            : "N/A"
                                                                        : "Awaiting Dispatch"}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })()}
                                    </div>
                                </div>
                            </div>

                            {/* Column 3: Strategy (Agent 3) - Takes up remaining space */}
                            <div className="col-span-12 lg:col-span-6 flex flex-col gap-6">
                                <div className="bg-paper border border-ink h-full flex flex-col shadow-premium hover:shadow-premium-hover transition-premium relative overflow-hidden">
                                    <div className="p-4 border-b border-ink glass-effect text-ink flex justify-between items-center">
                                        <div className="flex items-center gap-2">
                                            <span className="material-symbols-outlined text-sm font-bold">terminal</span>
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
                                                <span className="cursor-pointer hover:text-ink text-primary">ai_model: minimax-m2.5:cloud</span>
                                            </div>
                                            <button className="text-xs font-mono border-b border-ink hover:text-primary transition-colors">
                                                Clear Buffer
                                            </button>
                                        </div>
                                        {/* Content Editable Area OR Preview */}
                                        {isLoadingPreview ? (
                                            <div className="flex-1 p-6 flex flex-col items-center justify-center font-mono text-sm text-ink/60 bg-mute/20">
                                                <span className="material-symbols-outlined text-4xl animate-spin mb-4">refresh</span>
                                                GENERATING PREVIEW...
                                            </div>
                                        ) : previewHtml ? (
                                            <div className="flex-1 bg-white relative flex flex-col">
                                                <div className="absolute top-0 right-0 bg-primary text-white px-3 py-1 font-mono text-[10px] z-10 uppercase tracking-widest font-bold">
                                                    Template Preview (Editable)
                                                </div>
                                                <iframe
                                                    id="email-preview-iframe"
                                                    srcDoc={previewHtml}
                                                    className="w-full h-full border-none flex-1"
                                                    title="Email Preview"
                                                    onLoad={(e) => {
                                                        if (e.target.contentDocument) {
                                                            const editable = e.target.contentDocument.getElementById('ai-email-body-editable');
                                                            if (editable) {
                                                                editable.setAttribute('contenteditable', 'true');
                                                            }
                                                            const style = e.target.contentDocument.createElement('style');
                                                            style.innerHTML = 'body { outline: none; } [contenteditable="true"] { outline: none; cursor: text; min-height: 50px; } [contenteditable="true"]:hover { outline: 1px dashed #ccc; } [contenteditable="true"]:focus { outline: 1px dashed #667eea; background: rgba(102, 126, 234, 0.05); }';
                                                            e.target.contentDocument.head.appendChild(style);
                                                        }
                                                    }}
                                                />
                                            </div>
                                        ) : (
                                            <div className="flex flex-col flex-1 bg-white">
                                                <div className="px-6 py-4 text-sm font-bold text-ink border-b border-ink/10 bg-mute/10">
                                                    Subject: {target.subject}
                                                </div>
                                                <div id="email-editor"
                                                    className="flex-1 p-6 font-mono text-sm leading-relaxed text-ink/80 focus:outline-none overflow-y-auto"
                                                    contentEditable
                                                    suppressContentEditableWarning
                                                    dangerouslySetInnerHTML={{ __html: rawEditorContent }}
                                                    onClick={(e) => {
                                                        // contentEditable blocks link clicks — intercept and open manually
                                                        const anchor = e.target.closest('a');
                                                        if (anchor && anchor.href) {
                                                            e.preventDefault();
                                                            let targetUrl = anchor.href;
                                                            // If this is a tracking redirect (e.g. /api/track/click?...&url=REAL_URL),
                                                            // extract the real destination URL so the preview works correctly.
                                                            // Tracking in actual SENT emails is handled by EmailService at send time.
                                                            try {
                                                                const parsed = new URL(targetUrl);
                                                                const realUrl = parsed.searchParams.get('url');
                                                                if (realUrl) targetUrl = realUrl;
                                                            } catch (_) {}
                                                            window.open(targetUrl, '_blank', 'noopener,noreferrer');
                                                        }
                                                    }}
                                                />
                                            </div>
                                        )}

                                        {/* Template Disclaimer */}
                                        <div className="px-4 py-2 border-t border-ink/10 bg-mute/30 font-mono text-[10px] text-ink/50 text-center animate-pulse">
                                            {previewHtml
                                                ? "EDIT MODE: You can click directly inside the template above to edit the final email layout and text."
                                                : "EDIT MODE: The text above is the raw AI body. It will be wrapped inside the selected HTML template upon dispatch."}
                                        </div>
                                        {/* Actions Footer */}
                                        <div className="p-4 border-t border-ink bg-paper flex flex-wrap justify-between items-center gap-4">
                                            <button
                                                onClick={handleRegenerate}
                                                disabled={isRegenerating}
                                                className="flex items-center gap-2 px-4 py-2 border border-ink bg-paper hover:bg-mute hover:shadow-premium transition-premium font-display font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed shadow-[2px_2px_0px_0px_rgba(10,10,10,1)]">
                                                <span className={`material-symbols-outlined text-lg ${isRegenerating ? 'animate-spin' : ''}`}>autorenew</span>
                                                {isRegenerating ? 'WORKING...' : 'REGENERATE'}
                                            </button>
                                            <div className="flex flex-wrap items-center gap-2">
                                                {/* Email-sent badge + re-send option */}
                                                {target.emailSent && (
                                                    <div className="flex items-center gap-2">
                                                        <div className="flex items-center gap-1.5 px-3 py-1.5 border border-data-green/40 bg-data-green/10">
                                                            <span className="material-symbols-outlined text-data-green text-sm">mark_email_read</span>
                                                            <div className="font-mono text-[10px] leading-tight">
                                                                <div className="text-data-green font-bold uppercase tracking-wider">Email Sent</div>
                                                                {target.lastSentAt && (
                                                                    <div className="text-ink/40">{new Date(target.lastSentAt).toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</div>
                                                                )}
                                                            </div>
                                                        </div>
                                                        <button
                                                            onClick={async () => {
                                                                if (!confirm("This lead has already received an email. Send again anyway?")) return;
                                                                setIsSending(true);
                                                                try {
                                                                    let contentBody = "";
                                                                    let finalTemplateId = selectedTemplate || null;
                                                                    if (previewHtml) {
                                                                        const iframeDoc = document.getElementById("email-preview-iframe")?.contentDocument;
                                                                        if (iframeDoc && iframeDoc.body.innerHTML.trim() !== "") {
                                                                            contentBody = iframeDoc.documentElement.outerHTML;
                                                                            finalTemplateId = null;
                                                                        } else {
                                                                            contentBody = rawEditorContent || target.draft.map(d => d.content).join("");
                                                                        }
                                                                    } else {
                                                                        contentBody = document.getElementById("email-editor")?.innerHTML || rawEditorContent || target.draft.map(d => d.content).join("");
                                                                    }

                                                                    const res = await fetch(`${API}/leads/${id}/approve-email`, {
                                                                        method: "POST",
                                                                        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${localStorage.getItem("access_token")}` },
                                                                        body: JSON.stringify({ subject: target.subject, content: contentBody, to_email: target.email || "mishraabhishek1703@gmail.com", force: true, template_id: finalTemplateId })
                                                                    });
                                                                    if (!res.ok) throw new Error("Failed");
                                                                    alert("Email re-sent successfully.");
                                                                    window.location.reload();
                                                                } catch (e) { alert("Re-send failed: " + e.message); }
                                                                finally { setIsSending(false); }
                                                            }}
                                                            disabled={isSending}
                                                            title="Force re-send (bypasses duplicate guard)"
                                                            className="flex items-center gap-2 px-4 py-2 border border-amber-500 bg-amber-50 text-amber-700 hover:bg-amber-500 hover:text-white font-display font-medium text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                                                        >
                                                            <span className="material-symbols-outlined text-lg">refresh</span>
                                                            RE-SEND
                                                        </button>
                                                    </div>
                                                )}
                                                <div className="flex items-center gap-2 px-3 py-1 border border-ink bg-paper focus-within:ring-2 focus-within:ring-primary focus-within:border-primary transition-all">
                                                    <span className="material-symbols-outlined text-ink/50 text-[18px]">view_quilt</span>
                                                    <select
                                                        value={selectedTemplate}
                                                        onChange={handleTemplateChange}
                                                        className="font-mono text-xs bg-transparent outline-none py-1.5 cursor-pointer text-ink appearance-none pr-4"
                                                        style={{ backgroundImage: 'url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%231a1a1a%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E")', backgroundRepeat: 'no-repeat', backgroundPosition: 'right center', backgroundSize: '8px auto' }}
                                                    >
                                                        <option value="">Raw AI Source</option>
                                                        {templates.map(t => (
                                                            <option key={t._id} value={t._id}>{t.name}</option>
                                                        ))}
                                                    </select>
                                                </div>
                                                <button className="flex items-center gap-2 px-4 py-2 border border-ink hover:bg-mute transition-colors font-display font-medium text-sm">
                                                    <span className="material-symbols-outlined text-lg">content_copy</span>
                                                    COPY
                                                </button>
                                                <button
                                                    onClick={handleDeleteLead}
                                                    className="flex items-center gap-2 px-4 py-2 border border-ink bg-paper hover:bg-red-50 text-red-600 hover:text-red-700 font-display font-medium text-sm transition-colors"
                                                    title="Delete Lead Permanentely"
                                                >
                                                    <span className="material-symbols-outlined text-lg">delete</span>
                                                    DELETE
                                                </button>
                                                <button
                                                    onClick={handleApproveEmail}
                                                    disabled={isSending || target.emailSent}
                                                    title={target.emailSent ? "Email already sent to this lead" : "Approve and send email"}
                                                    className={`flex items-center gap-2 px-6 py-2 border border-ink font-display font-bold text-sm transition-premium ${target.emailSent
                                                        ? 'bg-mute text-ink/40 cursor-not-allowed'
                                                        : 'bg-primary text-white hover:bg-ink shadow-premium hover:shadow-premium-hover hover:glow-primary hover:translate-x-[-1px] hover:translate-y-[-1px] active:translate-x-[2px] active:translate-y-[2px] active:shadow-none'
                                                        } disabled:opacity-50 disabled:cursor-not-allowed`}>
                                                    <span className="material-symbols-outlined text-lg">{isSending ? 'hourglass_empty' : target.emailSent ? 'done_all' : 'send'}</span>
                                                    {isSending ? 'DISPATCHING...' : target.emailSent ? 'ALREADY SENT' : 'APPROVE & LOG'}
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Footer: Audit Trail (Agent 5) */}
                        <section className="border border-ink bg-paper mt-8 shadow-premium hover:shadow-premium-hover transition-premium overflow-hidden mb-12">
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
