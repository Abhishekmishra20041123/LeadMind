"use client";
import { useState, useEffect, useCallback } from "react";
import DashboardLayout from "../../components/DashboardLayout";

const API = "http://localhost:8000/api";
const token = () => (typeof window !== "undefined" ? localStorage.getItem("access_token") : "");
const hdrs = () => {
    const t = token();
    return {
        "Content-Type": "application/json",
        ...(t ? { "Authorization": "Bearer " + t } : {})
    };
};

const PRIORITY_COLOR = { high: "bg-red-500", medium: "bg-amber-400", low: "bg-emerald-500" };
const PRIORITY_TEXT  = { high: "text-red-600", medium: "text-amber-600", low: "text-emerald-600" };

export default function TasksPage() {
    const [tasks, setTasks]         = useState([]);
    const [loading, setLoading]     = useState(true);
    const [filter, setFilter]       = useState("all"); // all | pending | done | overdue
    const [creating, setCreating]   = useState(false);
    const [suggesting, setSuggesting] = useState(false);
    const [suggestions, setSuggestions] = useState([]);
    const [toast, setToast]         = useState(null);
    const [fetchError, setFetchError] = useState(null);

    const [form, setForm] = useState({
        title: "", lead_id: "", priority: "medium",
        assigned_to: "", due_date: "", source: "manual"
    });

    const showToast = (msg, err = false) => {
        setToast({ msg, err });
        setTimeout(() => setToast(null), 3000);
    };

    const loadTasks = useCallback(async () => {
        setLoading(true);
        setFetchError(null);
        try {
            console.log("Fetching tasks from:", API + "/tasks/my-tasks");
            const r = await fetch(API + "/tasks/my-tasks", { headers: hdrs() });
            console.log("Fetch response status:", r.status);
            if (r.ok) {
                const data = await r.json();
                setTasks(data.tasks);
            } else {
                setFetchError(`Fetch failed with status ${r.status}`);
            }
        } catch (err) {
            setFetchError(`Critical fetch error: ${err.message}`);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { loadTasks(); }, [loadTasks]);

    const handleComplete = async (task) => {
        await fetch(API + "/tasks/" + task.task_id, {
            method: "PATCH", headers: hdrs(),
            body: JSON.stringify({ status: task.status === "done" ? "pending" : "done" })
        });
        loadTasks();
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        setCreating(true);
        try {
            const r = await fetch(API + "/tasks/create", {
                method: "POST", headers: hdrs(), body: JSON.stringify(form)
            });
            if (r.ok) {
                showToast("Task created successfully.");
                setForm({ title: "", lead_id: "", priority: "medium", assigned_to: "", due_date: "", source: "manual" });
                loadTasks();
            } else { showToast("Failed to create task.", true); }
        } finally { setCreating(false); }
    };

    const handleAiSuggest = async () => {
        setSuggesting(true);
        setSuggestions([]);
        try {
            const r = await fetch(API + "/tasks/ai-suggest", { method: "POST", headers: hdrs() });
            if (r.ok) setSuggestions((await r.json()).tasks || []);
            else showToast("AI suggestion failed.", true);
        } finally { setSuggesting(false); }
    };

    const acceptSuggestion = async (s) => {
        const due = s.due_days_from_now
            ? new Date(Date.now() + s.due_days_from_now * 86400000).toISOString()
            : "";
        await fetch(API + "/tasks/create", {
            method: "POST", headers: hdrs(),
            body: JSON.stringify({
                title: s.title, lead_id: s.lead_id || "",
                priority: s.priority, due_date: due, source: "ai"
            })
        });
        showToast("AI task enqueued.");
        loadTasks();
    };

    const now = Date.now();
    const filtered = tasks.filter(t => {
        if (filter === "pending")  return t.status === "pending";
        if (filter === "done")     return t.status === "done";
        if (filter === "overdue")  return t.status === "pending" && t.due_date && new Date(t.due_date).getTime() < now;
        return true;
    });

    const overdue   = tasks.filter(t => t.status === "pending" && t.due_date && new Date(t.due_date).getTime() < now);
    const pendingCt = tasks.filter(t => t.status === "pending").length;
    const doneCt    = tasks.filter(t => t.status === "done").length;

    return (
        <DashboardLayout>
            <div className="font-mono text-ink max-w-7xl mx-auto py-8 px-4 sm:px-8">

                {/* Toast */}
                {toast && (
                    <div className={"fixed top-4 right-4 z-50 px-6 py-4 border-2 shadow-[6px_6px_0_0_rgba(10,10,10,1)] font-mono text-xs font-bold uppercase tracking-widest flex items-center gap-3 " + (toast.err ? "border-red-500 bg-red-50 text-red-600" : "border-ink bg-primary text-ink")}>
                        <span className="material-symbols-outlined text-sm">{toast.err ? "error" : "task_alt"}</span>
                        {toast.msg}
                    </div>
                )}

                {/* Header */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end mb-10 border-b-4 border-ink pb-6 gap-4">
                    <div>
                        <h1 className="text-4xl font-black uppercase tracking-tighter">Task Board</h1>
                        <p className="text-sm uppercase tracking-widest text-ink/60 mt-2 font-bold">Follow-ups & Team Actions</p>
                    </div>
                    <button
                        onClick={handleAiSuggest}
                        disabled={suggesting}
                        className="px-6 py-3 border-2 border-ink bg-paper font-bold uppercase tracking-widest text-xs hover:bg-primary hover:text-ink transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                        <span className="material-symbols-outlined text-sm">auto_awesome</span>
                        {suggesting ? "Thinking..." : "AI Suggest Tasks"}
                    </button>
                </div>

                {/* Error Banner */}
                {fetchError && (
                    <div className="mb-10 p-6 border-4 border-red-500 bg-red-50 text-red-600 font-mono text-sm font-bold uppercase tracking-widest flex items-center gap-4 animate-bounce">
                        <span className="material-symbols-outlined text-2xl">error</span>
                        <div className="flex-1">
                            <div>System Fault: {fetchError}</div>
                            <div className="text-[10px] mt-1 opacity-70 italic">Verify API connection & CORS settings</div>
                        </div>
                        <button onClick={() => loadTasks()} className="px-4 py-2 bg-red-600 text-white hover:bg-red-700 transition-colors">Retry</button>
                    </div>
                )}

                {/* Stats row */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
                    {[
                        { label: "Total",   val: tasks.length,   icon: "checklist" },
                        { label: "Pending", val: pendingCt,      icon: "pending" },
                        { label: "Done",    val: doneCt,         icon: "check_circle" },
                        { label: "Overdue", val: overdue.length, icon: "alarm", danger: true },
                    ].map(stat => (
                        <div key={stat.label} className={"border-2 border-ink p-5 flex flex-col gap-1 " + (stat.danger && overdue.length > 0 ? "bg-red-50 border-red-500" : "bg-paper")}>
                            <span className={"material-symbols-outlined text-2xl " + (stat.danger && overdue.length > 0 ? "text-red-500" : "text-ink/50")}>{stat.icon}</span>
                            <div className={"text-3xl font-black " + (stat.danger && overdue.length > 0 ? "text-red-600" : "")}>{stat.val}</div>
                            <div className="text-[10px] uppercase tracking-widest text-ink/60">{stat.label}</div>
                        </div>
                    ))}
                </div>

                {/* AI Suggestions */}
                {suggestions.length > 0 && (
                    <div className="border-2 border-primary bg-primary/5 p-6 mb-10">
                        <h3 className="text-xs font-bold uppercase tracking-widest mb-4 flex items-center gap-2 text-ink">
                            <span className="material-symbols-outlined text-sm">auto_awesome</span>
                            AI-Suggested Tasks — Click to Accept
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {suggestions.map((s, i) => (
                                <button
                                    key={i}
                                    onClick={() => acceptSuggestion(s)}
                                    className="text-left p-4 border-2 border-ink bg-paper hover:bg-primary hover:text-ink transition-colors group"
                                >
                                    <div className={"inline-block px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest rounded mb-2 " + (PRIORITY_COLOR[s.priority] || "bg-mute") + " text-paper"}>{s.priority}</div>
                                    <p className="text-xs font-bold uppercase">{s.title}</p>
                                    {s.due_days_from_now && (
                                        <p className="text-[10px] text-ink/50 mt-1">Due in {s.due_days_from_now} days</p>
                                    )}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                    {/* Create Task Form */}
                    <div className="border-2 border-ink p-6 bg-paper h-fit">
                        <h3 className="text-xs font-bold uppercase tracking-widest mb-6 flex items-center gap-2">
                            <span className="material-symbols-outlined text-sm">add_task</span>
                            New Task
                        </h3>
                        <form onSubmit={handleCreate} className="space-y-4">
                            {[
                                { label: "Task Title *", key: "title", type: "text", placeholder: "e.g. Follow up on proposal" },
                                { label: "Lead ID (optional)", key: "lead_id", type: "text", placeholder: "e.g. L_ABC123" },
                                { label: "Assign To (email)", key: "assigned_to", type: "email", placeholder: "rep@company.com" },
                                { label: "Due Date", key: "due_date", type: "datetime-local", placeholder: "" },
                            ].map(f => (
                                <div key={f.key} className="flex flex-col gap-1">
                                    <label className="text-[10px] font-bold uppercase tracking-widest text-ink/60">{f.label}</label>
                                    <input
                                        type={f.type}
                                        required={f.key === "title"}
                                        value={form[f.key]}
                                        onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                                        placeholder={f.placeholder}
                                        className="px-3 py-2 border-2 border-ink bg-mute/30 text-xs font-mono focus:outline-none focus:border-primary"
                                    />
                                </div>
                            ))}

                            <div className="flex flex-col gap-1">
                                <label className="text-[10px] font-bold uppercase tracking-widest text-ink/60">Priority</label>
                                <select
                                    value={form.priority}
                                    onChange={e => setForm(prev => ({ ...prev, priority: e.target.value }))}
                                    className="px-3 py-2 border-2 border-ink bg-mute/30 text-xs font-mono focus:outline-none focus:border-primary"
                                >
                                    <option value="high">High</option>
                                    <option value="medium">Medium</option>
                                    <option value="low">Low</option>
                                </select>
                            </div>

                            <button type="submit" disabled={creating || !form.title}
                                className="w-full py-3 bg-ink text-paper font-bold uppercase tracking-widest text-xs hover:bg-primary hover:text-ink transition-colors disabled:opacity-50"
                            >
                                {creating ? "Creating..." : "Create Task"}
                            </button>
                        </form>
                    </div>

                    {/* Task List */}
                    <div className="lg:col-span-2">
                        {/* Filter tabs */}
                        <div className="flex border-b-2 border-ink mb-6 overflow-x-auto">
                            {["all", "pending", "done", "overdue"].map(f => (
                                <button
                                    key={f}
                                    onClick={() => setFilter(f)}
                                    className={"px-6 py-3 text-[11px] font-bold uppercase tracking-widest border-b-4 transition-colors whitespace-nowrap " + (filter === f ? "border-ink text-ink" : "border-transparent text-ink/40 hover:text-ink/70")}
                                >
                                    {f} {f === "overdue" && overdue.length > 0 && <span className="ml-1 px-1.5 py-0.5 bg-red-500 text-paper text-[9px] rounded">{overdue.length}</span>}
                                </button>
                            ))}
                        </div>

                        {loading ? (
                            <div className="text-center py-16 text-xs uppercase tracking-widest text-ink/40 animate-pulse">Loading tasks...</div>
                        ) : filtered.length === 0 ? (
                            <div className="text-center py-16 border-2 border-dashed border-ink/20">
                                <span className="material-symbols-outlined text-4xl text-ink/20">task_alt</span>
                                <p className="text-xs uppercase tracking-widest text-ink/40 mt-3">No tasks in this category</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {filtered.map(task => {
                                    const isOverdue = task.status === "pending" && task.due_date && new Date(task.due_date).getTime() < now;
                                    return (
                                        <div key={task.id || task.task_id}
                                            className={"border-2 p-4 flex items-start gap-4 transition-all " + (task.status === "done" ? "border-ink/20 bg-mute/20 opacity-60" : isOverdue ? "border-red-500 bg-red-50" : "border-ink bg-paper hover:shadow-[4px_4px_0_0_rgba(10,10,10,1)]")}
                                        >
                                            <button
                                                onClick={() => handleComplete(task)}
                                                className={"mt-0.5 w-5 h-5 border-2 flex items-center justify-center shrink-0 transition-colors " + (task.status === "done" ? "border-emerald-500 bg-emerald-500" : "border-ink hover:border-primary")}
                                            >
                                                {task.status === "done" && <span className="material-symbols-outlined text-paper text-[12px]">check</span>}
                                            </button>

                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className={"font-bold text-sm uppercase " + (task.status === "done" ? "line-through text-ink/40" : "")}>{task.title}</span>
                                                    <span className={"px-2 py-0.5 text-[9px] font-bold uppercase text-paper rounded " + (PRIORITY_COLOR[task.priority] || "bg-mute")}>{task.priority}</span>
                                                    {task.source === "ai" && <span className="px-2 py-0.5 text-[9px] font-bold uppercase bg-primary/20 text-ink border border-primary/30">AI</span>}
                                                    {isOverdue && <span className="px-2 py-0.5 text-[9px] font-bold uppercase bg-red-500 text-paper">OVERDUE</span>}
                                                </div>
                                                <div className="flex items-center gap-4 mt-2 flex-wrap">
                                                    {task.lead_id && <span className="text-[10px] text-ink/50 font-mono">{task.lead_id}</span>}
                                                    {task.assigned_to && <span className="text-[10px] text-ink/50">{task.assigned_to}</span>}
                                                    {task.due_date && (
                                                        <span className={"text-[10px] font-bold " + (isOverdue ? "text-red-600" : "text-ink/50")}>
                                                            Due: {new Date(task.due_date).toLocaleDateString()}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </DashboardLayout>
    );
}
