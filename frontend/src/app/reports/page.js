"use client";
import { useState, useEffect } from "react";
import DashboardLayout from "../../components/DashboardLayout";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, Cell } from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export default function ReportsPage() {
    const [loading, setLoading] = useState(true);
    const [emailData, setEmailData] = useState([]);
    const [funnelData, setFunnelData] = useState([]);
    const [agentData, setAgentData] = useState([]);
    const [revenueData, setRevenueData] = useState({ actual: 0, forecast: 0 });
    const [campaigns, setCampaigns] = useState([]);
    const [days, setDays] = useState(30);

    useEffect(() => {
        fetchReports();
    }, [days]);

    const fetchReports = async () => {
        setLoading(true);
        const headers = { "Authorization": `Bearer ${localStorage.getItem("access_token")}` };
        try {
            const [emailsRes, funnelRes, agentRes, revRes, campRes] = await Promise.all([
                fetch(`${API}/reports/email-performance?days=${days}`, { headers }),
                fetch(`${API}/reports/conversion-funnel`, { headers }),
                fetch(`${API}/reports/agent-performance`, { headers }),
                fetch(`${API}/reports/revenue-forecast`, { headers }),
                fetch(`${API}/reports/campaign-comparison`, { headers })
            ]);

            if (emailsRes.ok) setEmailData((await emailsRes.json()).data);
            if (funnelRes.ok) setFunnelData((await funnelRes.json()).funnel);
            if (agentRes.ok) setAgentData((await agentRes.json()).data);
            if (revRes.ok) {
                const r = await revRes.json();
                setRevenueData({ actual: r.pipeline_total, forecast: r.weighted_forecast });
            }
            if (campRes.ok) setCampaigns((await campRes.json()).data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleExport = async () => {
        try {
            const res = await fetch(`${API}/reports/export`, {
                headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` }
            });
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "leadmind_export.csv";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } catch (e) {
            console.error("Export failed", e);
        }
    };

    const formatCurrency = (val) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);

    return (
        <DashboardLayout>
            <div className="font-mono text-ink max-w-7xl mx-auto py-8 px-4 sm:px-8">
                {/* Header */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end mb-12 border-b-4 border-ink pb-6 gap-6 relative">
                    <div className="absolute top-0 right-1/4 w-32 h-32 bg-data-orange/20 rounded-full blur-3xl -z-10" />
                    <div>
                        <h1 className="text-4xl font-black uppercase tracking-tighter">Analytics</h1>
                        <p className="text-sm uppercase tracking-widest text-ink/60 mt-2 font-bold">Reporting & Export</p>
                    </div>
                    <div className="flex items-center gap-4">
                        <select 
                            value={days} 
                            onChange={(e) => setDays(Number(e.target.value))}
                            className="bg-paper border-2 border-ink px-4 py-3 text-xs font-bold uppercase tracking-widest focus:outline-none cursor-pointer hover:bg-mute/20 transition-colors">
                            <option value={7}>Last 7 Days</option>
                            <option value={30}>Last 30 Days</option>
                            <option value={90}>Last 90 Days</option>
                        </select>
                        <button onClick={handleExport} className="px-6 py-3 bg-ink text-paper font-bold uppercase tracking-widest text-xs hover:bg-primary hover:text-ink transition-colors flex items-center gap-2">
                            <span className="material-symbols-outlined text-sm">download</span>
                            Export CSV
                        </button>
                    </div>
                </div>

                {loading ? (
                    <div className="flex h-64 items-center justify-center font-bold tracking-widest uppercase animate-pulse">Loading Reports...</div>
                ) : (
                    <div className="space-y-12">
                        {/* Top: Revenue & Funnel */}
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                            
                            {/* Revenue Forecast Card */}
                            <div className="border-2 border-ink bg-primary text-ink p-8 flex flex-col justify-center relative overflow-hidden shadow-[6px_6px_0px_0px_rgba(10,10,10,1)] hover:-translate-y-1 transition duration-300">
                                <div className="absolute -right-12 -top-12 text-[150px] opacity-10 font-black rotate-12 select-none">$</div>
                                <h3 className="text-sm font-bold uppercase tracking-widest mb-6 border-b-2 border-ink/20 pb-4 inline-block">Revenue Forecast</h3>
                                
                                <div className="space-y-6">
                                    <div>
                                        <p className="text-[10px] uppercase tracking-widest font-bold opacity-60 mb-1">Weighted Pipeline</p>
                                        <div className="text-4xl font-black">{formatCurrency(revenueData.forecast)}</div>
                                    </div>
                                    <div>
                                        <p className="text-[10px] uppercase tracking-widest font-bold opacity-60 mb-1">Total Deal Value</p>
                                        <div className="text-xl font-bold">{formatCurrency(revenueData.actual)}</div>
                                    </div>
                                </div>
                            </div>

                            {/* Conversion Funnel */}
                            <div className="lg:col-span-2 border-2 border-ink bg-paper p-6 relative">
                                <h3 className="text-xs font-bold uppercase tracking-widest mb-6 text-ink/70 flex items-center gap-2">
                                    <span className="material-symbols-outlined text-sm">filter_alt</span>
                                    Conversion Funnel
                                </h3>
                                <div className="h-64">
                                    {funnelData.length === 0 ? (
                                        <div className="h-full flex items-center justify-center text-xs tracking-widest text-ink/40">NO PIPELINE DATA</div>
                                    ) : (
                                        <ResponsiveContainer width="100%" height="100%">
                                            <BarChart data={funnelData} layout="vertical" margin={{ top: 0, right: 30, left: 20, bottom: 0 }}>
                                                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E5E7EB" />
                                                <XAxis type="number" hide />
                                                <YAxis dataKey="label" type="category" width={100} tick={{ fontSize: 10, fontFamily: 'monospace', fontWeight: 'bold' }} axisLine={false} tickLine={false} />
                                                <Tooltip 
                                                    cursor={{fill: '#f4f4f5'}}
                                                    contentStyle={{ backgroundColor: '#0a0a0a', border: 'none', borderRadius: '0', color: '#fff' }}
                                                    itemStyle={{ color: '#fff', fontSize: '12px' }}
                                                    labelStyle={{ color: '#aaa', fontSize: '10px', marginBottom: '8px', textTransform: 'uppercase' }}
                                                />
                                                <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={24}>
                                                    {funnelData.map((entry, index) => (
                                                        <Cell key={"cell-" + index} fill={entry.color} />
                                                    ))}
                                                </Bar>
                                            </BarChart>
                                        </ResponsiveContainer>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Middle: Email Performance Chart */}
                        <div className="border-2 border-ink overflow-hidden bg-paper">
                            <div className="border-b-2 border-ink bg-mute/20 p-4">
                                <h3 className="text-xs font-bold uppercase tracking-widest text-ink/70 flex items-center gap-2">
                                    <span className="material-symbols-outlined text-sm">mail</span>
                                    Email Performance ({days} Days)
                                </h3>
                            </div>
                            <div className="p-6 h-80">
                                {emailData.length === 0 ? (
                                     <div className="h-full flex items-center justify-center text-xs tracking-widest text-ink/40">NO EMAIL DATA</div>
                                ) : (
                                    <ResponsiveContainer width="100%" height="100%">
                                        <LineChart data={emailData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                                            <XAxis dataKey="date" tick={{ fontSize: 10, fontFamily: 'monospace' }} axisLine={false} tickLine={false} dy={10} />
                                            <YAxis tick={{ fontSize: 10, fontFamily: 'monospace' }} axisLine={false} tickLine={false} dx={-10} />
                                            <Tooltip 
                                                contentStyle={{ backgroundColor: '#0a0a0a', border: '2px solid #111', color: '#fefefe' }}
                                                itemStyle={{ fontSize: '12px', fontWeight: 'bold', fontFamily: 'monospace' }}
                                                labelStyle={{ color: '#aaa', fontSize: '10px', marginBottom: '8px', textTransform: 'uppercase', fontFamily: 'monospace' }}
                                            />
                                            <Legend wrapperStyle={{ fontSize: '10px', fontFamily: 'monospace', paddingTop: '20px' }} />
                                            <Line type="monotone" dataKey="sends" name="Sends" stroke="#3B82F6" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
                                            <Line type="monotone" dataKey="opens" name="Opens" stroke="#10B981" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
                                            <Line type="monotone" dataKey="clicks" name="Clicks" stroke="#F59E0B" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
                                        </LineChart>
                                    </ResponsiveContainer>
                                )}
                            </div>
                        </div>

                        {/* Bottom: Agent Performance & Campaigns */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                            
                            {/* Agent Success Rate */}
                            <div className="border-2 border-ink p-6 bg-paper">
                                <h3 className="text-xs font-bold uppercase tracking-widest mb-6 text-ink/70 flex items-center gap-2">
                                    <span className="material-symbols-outlined text-sm">smart_toy</span>
                                    Agent Success Rates
                                </h3>
                                {agentData.length === 0 ? (
                                    <div className="h-40 flex items-center justify-center text-xs tracking-widest text-ink/40">NO AGENT DATA</div>
                                ) : (
                                    <div className="space-y-6">
                                        {agentData.map(agent => (
                                            <div key={agent.agent}>
                                                <div className="flex justify-between text-xs font-bold uppercase tracking-widest mb-2">
                                                    <span>{agent.agent}</span>
                                                    <span>{agent.success_rate}%</span>
                                                </div>
                                                <div className="h-2 w-full bg-mute/30 overflow-hidden border border-ink/10">
                                                    <div className="h-full bg-data-purple transition-all duration-1000" style={{ width: agent.success_rate + "%" }} />
                                                </div>
                                                <p className="text-[10px] text-ink/50 mt-1 uppercase tracking-widest">{agent.calls} TOTAL INVOCATIONS</p>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/* Campaign Comparison */}
                            <div className="border-2 border-ink bg-paper flex flex-col">
                                <div className="border-b-2 border-ink bg-mute/20 p-4">
                                    <h3 className="text-xs font-bold uppercase tracking-widest text-ink/70 flex items-center gap-2">
                                        <span className="material-symbols-outlined text-sm">campaign</span>
                                        Campaigns
                                    </h3>
                                </div>
                                <div className="p-0 overflow-x-auto flex-1">
                                    {campaigns.length === 0 ? (
                                        <div className="h-40 flex items-center justify-center text-xs tracking-widest text-ink/40">NO CAMPAIGNS</div>
                                    ) : (
                                        <table className="w-full text-left text-sm whitespace-nowrap">
                                            <thead>
                                                <tr className="bg-mute/10 text-[10px] uppercase tracking-widest text-ink/50 border-b-2 border-ink">
                                                    <th className="px-6 py-4 font-bold">Campaign Name</th>
                                                    <th className="px-6 py-4 font-bold">Enrolled</th>
                                                    <th className="px-6 py-4 font-bold">Completed</th>
                                                    <th className="px-6 py-4 font-bold">Status</th>
                                                </tr>
                                            </thead>
                                            <tbody className="font-medium text-xs">
                                                {campaigns.map(c => (
                                                    <tr key={c.name} className="border-b border-ink/10 last:border-0 hover:bg-primary/5 transition-colors">
                                                        <td className="px-6 py-4 uppercase font-bold text-ink">{c.name}</td>
                                                        <td className="px-6 py-4 text-ink/70">{c.enrolled}</td>
                                                        <td className="px-6 py-4 text-ink/70">{c.completed}</td>
                                                        <td className="px-6 py-4">
                                                            <span className={"px-2 py-1 text-[9px] font-bold uppercase tracking-widest " + (c.status === 'active' ? 'bg-data-green/20 text-data-green' : 'bg-ink/10 text-ink/50')}>
                                                                {c.status}
                                                            </span>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    )}
                                </div>
                            </div>
                        </div>
                        
                    </div>
                )}
            </div>
        </DashboardLayout>
    );
}
