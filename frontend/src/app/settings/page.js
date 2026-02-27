"use client";
import DashboardLayout from "../../components/DashboardLayout";

export default function SettingsPage() {
    return (
        <DashboardLayout>
            <div className="animate-in fade-in zoom-in duration-500 max-w-5xl mx-auto">
                {/* Header */}
                <div className="mb-8 flex items-end justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Settings</h1>
                        <p className="font-mono text-xs text-[var(--text-muted)] tracking-widest uppercase">
                            System Configuration // v2.4.0
                        </p>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* API Config */}
                    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl overflow-hidden shadow-sm hover:border-[var(--border-accent)] transition-colors">
                        <div className="px-6 py-4 border-b border-[var(--border)] bg-[var(--bg-surface)]">
                            <h2 className="text-sm font-semibold text-white tracking-wide">API CONFIGURATION</h2>
                        </div>
                        <div className="p-6 space-y-6">
                            <div>
                                <label className="block text-xs font-bold text-[var(--text-muted)] uppercase tracking-wider mb-2">
                                    Backend URL
                                </label>
                                <div className="relative">
                                    <input
                                        className="w-full bg-[var(--bg-base)] border border-[var(--border)] rounded-lg px-4 py-3 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:border-transparent transition-all font-mono"
                                        defaultValue="http://localhost:8000"
                                        readOnly
                                    />
                                    <span className="material-icons-outlined absolute right-3 top-3 text-[var(--green)] text-lg">check_circle</span>
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-[var(--text-muted)] uppercase tracking-wider mb-2">
                                    Gemini API Key
                                </label>
                                <div className="relative">
                                    <input
                                        className="w-full bg-[var(--bg-base)] border border-[var(--border)] rounded-lg px-4 py-3 text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:border-transparent transition-all font-mono tracking-widest"
                                        type="password"
                                        defaultValue="sk-••••••••••••••••••••••••••"
                                        readOnly
                                    />
                                    <div className="absolute right-3 top-2.5 px-2 py-0.5 bg-[var(--bg-elevated)] rounded text-[10px] text-[var(--text-muted)] border border-[var(--border)]">
                                        HIDDEN
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* System Info */}
                    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl overflow-hidden shadow-sm hover:border-[var(--border-accent)] transition-colors">
                        <div className="px-6 py-4 border-b border-[var(--border)] bg-[var(--bg-surface)]">
                            <h2 className="text-sm font-semibold text-white tracking-wide">SYSTEM INFO</h2>
                        </div>
                        <div className="divide-y divide-[var(--border-subtle)]">
                            {[
                                { label: "Version", value: "v2.4.0 [STABLE]" },
                                { label: "Agents Online", value: "5 Workers", color: "text-[var(--green)]" },
                                { label: "LLM Provider", value: "Google Gemini 1.5 Pro" },
                                { label: "Orchestration", value: "LangGraph" },
                                { label: "Frontend Build", value: "Next.js 15 (Turbopack)" },
                            ].map((item, i) => (
                                <div key={i} className="flex justify-between items-center px-6 py-4 hover:bg-[var(--bg-hover)] transition-colors">
                                    <span className="text-sm text-[var(--text-secondary)] font-medium">{item.label}</span>
                                    <span className={`font-mono text-xs ${item.color || "text-[var(--text-primary)]"}`}>{item.value}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Data Sources */}
                    <div className="lg:col-span-2 bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl overflow-hidden shadow-sm hover:border-[var(--border-accent)] transition-colors">
                        <div className="px-6 py-4 border-b border-[var(--border)] bg-[var(--bg-surface)] flex justify-between items-center">
                            <h2 className="text-sm font-semibold text-white tracking-wide">DATA SOURCES</h2>
                            <span className="text-xs text-[var(--text-muted)] bg-[var(--bg-base)] px-2 py-1 rounded border border-[var(--border)]">
                                AUTO-SYNC ON
                            </span>
                        </div>
                        <div className="divide-y divide-[var(--border-subtle)]">
                            {[
                                { file: "Leads_Data.csv", desc: "Primary lead database", size: "2.4 MB", updated: "2h ago" },
                                { file: "Sales_Pipeline.csv", desc: "Sales pipeline deals", size: "1.1 MB", updated: "5m ago" },
                                { file: "Email_Logs.csv", desc: "Historical email interactions", size: "15.8 MB", updated: "1d ago" },
                                { file: "CRM_Pipeline.csv", desc: "CRM pipeline data", size: "890 KB", updated: "12m ago" },
                                { file: "Agent_Mapping.csv", desc: "Sales agent assignments", size: "12 KB", updated: "3d ago" },
                            ].map((ds, i) => (
                                <div key={i} className="flex items-center gap-4 px-6 py-4 hover:bg-[var(--bg-hover)] transition-colors group">
                                    <div className="w-10 h-10 rounded-full bg-[var(--green-soft)] flex items-center justify-center shrink-0">
                                        <span className="material-icons-outlined text-lg text-[var(--green)]">table_chart</span>
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <div className="font-mono text-sm font-semibold text-[var(--text-primary)] truncate">{ds.file}</div>
                                            <span className="material-icons-outlined text-[14px] text-[var(--green)]">verified</span>
                                        </div>
                                        <div className="text-xs text-[var(--text-muted)] truncate">{ds.desc}</div>
                                    </div>
                                    <div className="text-right hidden sm:block">
                                        <div className="font-mono text-xs text-[var(--text-secondary)]">{ds.size}</div>
                                        <div className="text-[10px] text-[var(--text-muted)]">Synced {ds.updated}</div>
                                    </div>
                                    <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button className="p-2 hover:bg-[var(--bg-elevated)] rounded-full text-[var(--text-muted)] hover:text-white transition-colors">
                                            <span className="material-icons-outlined text-lg">more_vert</span>
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                        <div className="p-4 bg-[var(--bg-surface)] border-t border-[var(--border)] text-center">
                            <button className="text-xs font-medium text-[var(--accent)] hover:text-white transition-colors flex items-center justify-center gap-2 w-full">
                                <span className="material-icons-outlined text-sm">add_circle</span>
                                CONNECT NEW DATA SOURCE
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </DashboardLayout>
    );
}
