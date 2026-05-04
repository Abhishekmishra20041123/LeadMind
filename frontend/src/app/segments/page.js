"use client";
import { useState, useEffect } from "react";
import DashboardLayout from "../../components/DashboardLayout";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const FIELD_OPTIONS = [
    { value: "intel.intent_score", label: "Intent Score" },
    { value: "pipeline_stage", label: "Pipeline Stage" },
    { value: "profile.title", label: "Job Title" },
    { value: "status", label: "Status" },
    { value: "source", label: "Source (sdk/csv)" },
    { value: "email_opens.open_count", label: "Email Open Count" }
];

const OPERATOR_OPTIONS = [
    { value: "eq", label: "Equals" },
    { value: "neq", label: "Not Equals" },
    { value: "gt", label: "Greater Than" },
    { value: "gte", label: "Greater or Equal" },
    { value: "lt", label: "Less Than" },
    { value: "lte", label: "Less or Equal" },
    { value: "contains", label: "Contains" }
];

export default function SegmentsPage() {
    const [segments, setSegments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showCreate, setShowCreate] = useState(false);
    const [toastMessage, setToastMessage] = useState(null);
    const [aiSuggesting, setAiSuggesting] = useState(false);

    // New segment state
    const [name, setName] = useState("");
    const [logic, setLogic] = useState("AND");
    const [rules, setRules] = useState([{ field: "intel.intent_score", operator: "gte", value: "80" }]);

    useEffect(() => {
        fetchSegments();
    }, []);

    const fetchSegments = async () => {
        try {
            const res = await fetch(`${API}/segments/list`, {
                headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` }
            });
            if (res.ok) {
                const data = await res.json();
                setSegments(data.segments);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const showToast = (msg, isError = false) => {
        setToastMessage({ msg, isError });
        setTimeout(() => setToastMessage(null), 3000);
    };

    const handleCreate = async () => {
        if (!name.trim()) return showToast("Name is required", true);
        try {
            const res = await fetch(`${API}/segments/create`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${localStorage.getItem("access_token")}`
                },
                body: JSON.stringify({
                    name, logic, rules: rules.map(r => ({
                        field: r.field,
                        operator: r.operator,
                        value: isNaN(r.value) ? r.value : Number(r.value)
                    }))
                })
            });
            if (res.ok) {
                showToast("SEGMENT CREATED");
                setShowCreate(false);
                setName("");
                setRules([{ field: "intel.intent_score", operator: "gte", value: "80" }]);
                fetchSegments();
            } else {
                showToast("FAILED TO CREATE", true);
            }
        } catch (e) {
            showToast("ERROR", true);
        }
    };

    const handleDelete = async (id) => {
        try {
            await fetch(`${API}/segments/${id}`, {
                method: "DELETE",
                headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` }
            });
            setSegments(prev => prev.filter(s => s._id !== id));
            showToast("SEGMENT DELETED");
        } catch (e) {
            console.error(e);
        }
    };

    const handleAiSuggest = async () => {
        setAiSuggesting(true);
        try {
            const res = await fetch(`${API}/segments/ai-suggest`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` }
            });
            if (res.ok) {
                const data = await res.json();
                const sug = data.suggestions[0];
                if (sug) {
                    setName(sug.name);
                    setLogic(sug.logic);
                    setRules(sug.rules);
                    setShowCreate(true);
                    showToast("AI SUGGESTED A SEGMENT!");
                }
            }
        } catch (e) {
            showToast("AI FAILED TO SUGGEST", true);
        } finally {
            setAiSuggesting(false);
        }
    };

    return (
        <DashboardLayout>
            <div className="font-mono text-ink max-w-5xl mx-auto py-8 px-4 sm:px-8">
                <div className="flex justify-between items-end mb-12 border-b-4 border-ink pb-6 relative">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-primary/20 rounded-full blur-3xl -z-10 animate-pulse" />
                    <div>
                        <h1 className="text-4xl font-black uppercase tracking-tighter">Segments</h1>
                        <p className="text-sm uppercase tracking-widest text-ink/60 mt-2 font-bold">Smart Audience Grouping</p>
                    </div>
                    <div className="flex gap-4">
                        <button onClick={handleAiSuggest} disabled={aiSuggesting} className="px-6 py-3 bg-data-purple text-paper font-bold uppercase tracking-widest text-xs hover:bg-ink transition duration-300 disabled:opacity-50 flex items-center gap-2">
                            <span className="material-symbols-outlined text-sm">psychology</span>
                            {aiSuggesting ? "Analyzing..." : "AI Suggest"}
                        </button>
                        <button onClick={() => setShowCreate(!showCreate)} className="px-8 py-3 bg-primary text-ink font-bold uppercase tracking-widest text-xs border-2 border-ink shadow-[4px_4px_0px_0px_rgba(10,10,10,1)] hover:translate-y-[2px] hover:shadow-[2px_2px_0px_0px_rgba(10,10,10,1)] active:translate-y-[4px] active:shadow-none transition-all">
                            {showCreate ? "Cancel" : "+ New Segment"}
                        </button>
                    </div>
                </div>

                {toastMessage && (
                    <div className={`fixed top-4 right-4 z-50 p-4 border-2 shadow-[4px_4px_0px_0px_rgba(10,10,10,1)] font-mono text-xs uppercase font-bold tracking-widest ${toastMessage.isError ? 'bg-red-500 text-white border-ink' : 'bg-green-400 text-ink border-ink'}`}>
                        {toastMessage.msg}
                    </div>
                )}

                {showCreate && (
                    <div className="mb-12 border-2 border-ink p-6 bg-mute/20 relative shadow-[6px_6px_0px_0px_rgba(10,10,10,1)] flex flex-col gap-6">
                        <div className="flex flex-col gap-2">
                            <label className="text-xs uppercase font-bold tracking-widest text-ink/70">Segment Name</label>
                            <input type="text" value={name} onChange={e => setName(e.target.value)} className="w-full bg-paper border-2 border-ink p-3 text-sm focus:outline-none focus:bg-primary/10 transition-colors" placeholder="e.g. Hot SQL Leads" />
                        </div>

                        <div className="border-t-2 border-ink/10 pt-6 flex flex-col gap-4">
                            <div className="flex justify-between items-center">
                                <label className="text-xs uppercase font-bold tracking-widest text-ink/70">Matching Rules</label>
                                <select value={logic} onChange={e => setLogic(e.target.value)} className="bg-paper border-2 border-ink p-1 text-xs font-bold uppercase focus:outline-none focus:bg-primary/10">
                                    <option value="AND">Match ALL (AND)</option>
                                    <option value="OR">Match ANY (OR)</option>
                                </select>
                            </div>
                            
                            {rules.map((rule, idx) => (
                                <div key={idx} className="flex gap-2 items-center bg-paper border-2 border-ink p-2">
                                    <span className="text-ink/30 px-2">#{idx+1}</span>
                                    <select value={rule.field} onChange={e => { const r = [...rules]; r[idx].field = e.target.value; setRules(r); }} className="flex-1 bg-transparent border-0 text-xs uppercase focus:outline-none">
                                        {FIELD_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                                    </select>
                                    <select value={rule.operator} onChange={e => { const r = [...rules]; r[idx].operator = e.target.value; setRules(r); }} className="w-32 bg-transparent border-l-2 border-ink/20 pl-2 text-xs uppercase focus:outline-none">
                                        {OPERATOR_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                                    </select>
                                    <input type="text" value={rule.value} onChange={e => { const r = [...rules]; r[idx].value = e.target.value; setRules(r); }} className="flex-1 bg-transparent border-l-2 border-ink/20 pl-2 text-xs focus:outline-none" placeholder="Value..." />
                                    <button onClick={() => setRules(rules.filter((_, i) => i !== idx))} className="px-3 hover:text-red-500">×</button>
                                </div>
                            ))}
                            <button onClick={() => setRules([...rules, {field: "intel.intent_score", operator: "gte", value: "80"}])} className="text-xs uppercase tracking-widest text-primary font-bold self-start hover:underline">
                                + ADD CONDITION
                            </button>
                        </div>
                        
                        <div className="mt-4 flex justify-end">
                            <button onClick={handleCreate} className="px-8 py-3 bg-ink text-primary font-bold uppercase tracking-widest text-xs hover:bg-[#222]">
                                SAVE SEGMENT
                            </button>
                        </div>
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {loading ? (
                        [...Array(3)].map((_, idx) => <div key={idx} className="h-48 bg-mute/20 border-2 border-ink animate-pulse" />)
                    ) : segments.map(seg => (
                        <div key={seg._id} className="group border-2 border-ink flex flex-col bg-paper hover:-translate-y-1 transition duration-300">
                            <div className="p-6 border-b-2 border-ink bg-mute/10 flex justify-between items-start">
                                <div>
                                    <h3 className="font-bold uppercase tracking-tight text-lg leading-none">{seg.name}</h3>
                                    <p className="text-[10px] text-ink/50 tracking-widest mt-2">{seg.rules.length} RULES ({seg.logic})</p>
                                </div>
                                <button onClick={() => handleDelete(seg._id)} className="text-ink/30 hover:text-red-500 transition-colors">
                                    <span className="material-symbols-outlined text-sm">delete</span>
                                </button>
                            </div>
                            <div className="p-6 flex-1 flex flex-col justify-end">
                                <div className="flex items-end gap-3">
                                    <span className="text-4xl font-black text-ink">{seg.member_count}</span>
                                    <span className="text-xs font-bold uppercase tracking-widest text-ink/40 mb-1">MEMBERS</span>
                                </div>
                            </div>
                            <div className="border-t-2 border-ink p-3 bg-ink text-paper text-[10px] font-bold uppercase tracking-widest text-center cursor-pointer hover:bg-primary hover:text-ink transition-colors">
                                VIEW MEMBERS →
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </DashboardLayout>
    );
}
