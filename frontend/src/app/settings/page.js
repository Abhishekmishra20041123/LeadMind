"use client";
import DashboardLayout from "../../components/DashboardLayout";
import { useState, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export default function SettingsPage() {
    const [profile, setProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [activeTab, setActiveTab] = useState("PROFILE");
    const [toastMessage, setToastMessage] = useState(null);

    // Auth Modal State
    const [isUnlocked, setIsUnlocked] = useState(false);
    const [unlockPassword, setUnlockPassword] = useState("");
    const [unlocking, setUnlocking] = useState(false);
    const [unlockError, setUnlockError] = useState("");

    // Form inputs state
    const [formData, setFormData] = useState({
        company_name: "",
        company_website_url: "",
        country: "",
        business_type: "",
        company_description: "",
        contact_person_name: "",
        email: "",
        phone_number: "",
        password: "",
        confirm_password: "",
        api_key: "",
        settings: {
            smtp_user: "",
            smtp_pass: ""
        }
    });

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const res = await fetch(`${API}/auth/me`, {
                    headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` }
                });
                if (res.ok) {
                    const data = await res.json();
                    setProfile(data);
                    setFormData({
                        company_name: data.company_name || "",
                        company_website_url: data.company_website_url || "",
                        country: data.country || "",
                        business_type: data.business_type || "",
                        company_description: data.company_description || "",
                        contact_person_name: data.contact_person_name || "",
                        email: data.email || "",
                        phone_number: data.phone_number || "",
                        password: "",
                        confirm_password: "",
                        api_key: data.api_key || "",
                        settings: {
                            smtp_user: data.settings?.smtp_user || "",
                            smtp_pass: data.settings?.smtp_pass || ""
                        }
                    });
                }
            } catch (e) {
                console.error("Failed to load profile", e);
            } finally {
                setLoading(false);
            }
        };
        fetchProfile();
    }, []);

    const showToast = (message, isError = false) => {
        setToastMessage({ text: message, isError });
        setTimeout(() => setToastMessage(null), 3000);
    };

    const handleSave = async (e) => {
        e.preventDefault();
        if (formData.password || formData.confirm_password) {
            if (formData.password !== formData.confirm_password) {
                showToast("ERROR: SECURITY KEYS DO NOT MATCH.", true);
                return;
            }
        }
        setSaving(true);
        try {
            const payload = {
                company_name: formData.company_name,
                company_website_url: formData.company_website_url,
                country: formData.country,
                business_type: formData.business_type,
                company_description: formData.company_description,
                contact_person_name: formData.contact_person_name,
                email: formData.email,
                phone_number: formData.phone_number,
                api_key: formData.api_key,
                settings: formData.settings
            };
            if (formData.password) payload.password = formData.password;

            const res = await fetch(`${API}/auth/settings`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${localStorage.getItem("access_token")}`
                },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                showToast("CONFIGURATION SAVED SUCCESSFULLY.");
                setFormData(prev => ({ ...prev, password: "", confirm_password: "" }));
            } else {
                showToast("SAVE FAILED. CHECK SYSTEM LOGS.", true);
            }
        } catch (error) {
            showToast(`ERROR: ${error.message}`, true);
        } finally {
            setSaving(false);
        }
    };

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        if (name.startsWith("settings.")) {
            const field = name.split(".")[1];
            setFormData(prev => ({ ...prev, settings: { ...prev.settings, [field]: value } }));
        } else {
            setFormData(prev => ({ ...prev, [name]: value }));
        }
    };

    if (loading) return (
        <DashboardLayout>
            <div className="flex h-full items-center justify-center bg-paper text-ink font-mono uppercase tracking-widest animate-pulse">
                INITIALIZING SYSTEM SETTINGS...
            </div>
        </DashboardLayout>
    );

    const handleUnlock = async (e) => {
        e.preventDefault();
        setUnlocking(true);
        setUnlockError("");
        try {
            const res = await fetch(`${API}/auth/signin`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email: profile.email, password: unlockPassword })
            });
            if (res.ok) {
                setIsUnlocked(true);
            } else {
                setUnlockError("INVALID SECURITY KEY.");
            }
        } catch (error) {
            setUnlockError("AUTHENTICATION FAILED.");
        } finally {
            setUnlocking(false);
            setUnlockPassword("");
        }
    };

    if (!isUnlocked && profile) {
        return (
            <DashboardLayout>
                <div className="flex h-full items-center justify-center bg-grid-pattern relative p-8" style={{ backgroundColor: "#F9F9F9" }}>
                    <div className="w-full max-w-md bg-paper border-2 border-ink shadow-[8px_8px_0px_0px_rgba(10,10,10,1)] p-8 animate-in zoom-in-95 duration-500">
                        <div className="flex flex-col items-center text-center space-y-4 mb-8">
                            <div className="w-16 h-16 bg-primary flex items-center justify-center border-2 border-ink shadow-[4px_4px_0px_0px_rgba(10,10,10,1)]">
                                <span className="material-symbols-outlined text-paper text-3xl">lock</span>
                            </div>
                            <div>
                                <h1 className="font-display font-bold text-2xl text-ink uppercase tracking-tight">System Locked</h1>
                                <p className="font-mono text-xs text-ink/60 uppercase mt-2 tracking-widest leading-relaxed">
                                    Authentication required to access and modify system configuration parameters.
                                </p>
                            </div>
                        </div>
                        <form onSubmit={handleUnlock} className="space-y-6">
                            {unlockError && (
                                <div className="p-3 bg-red-50 border-2 border-red-500 text-red-500 font-mono text-xs font-bold uppercase tracking-widest text-center">
                                    {unlockError}
                                </div>
                            )}
                            <div className="flex flex-col gap-2">
                                <label className="text-xs font-mono font-bold uppercase text-ink/80 tracking-widest">Operator Security Key</label>
                                <input
                                    type="password"
                                    value={unlockPassword}
                                    onChange={(e) => setUnlockPassword(e.target.value)}
                                    placeholder="Enter your login password"
                                    className="w-full px-4 py-3 border-2 border-ink bg-mute text-ink font-mono text-sm focus:outline-none focus:border-primary focus:bg-white transition-colors"
                                    autoFocus
                                />
                            </div>
                            <button
                                type="submit"
                                disabled={unlocking || !unlockPassword}
                                className="w-full py-4 bg-primary text-paper font-bold font-mono text-sm uppercase tracking-widest border-2 border-ink shadow-[4px_4px_0px_0px_rgba(10,10,10,1)] hover:shadow-none hover:translate-x-[4px] hover:translate-y-[4px] transition-all disabled:opacity-50 disabled:cursor-wait">
                                {unlocking ? 'AUTHENTICATING...' : 'AUTHORIZE ACCESS'}
                            </button>
                        </form>
                    </div>
                </div>
            </DashboardLayout>
        );
    }

    const getInitials = (name) => {
        if (!name) return "XX";
        return name.substring(0, 2).toUpperCase();
    };

    const tabs = ["PROFILE", "CONTACTS", "SECURITY", "INTEGRATIONS"];

    const InputField = ({ label, name, type = "text", value, placeholder, isReadOnly = false }) => (
        <div className="flex flex-col gap-2">
            <label className="text-xs font-mono font-bold uppercase text-ink/80 tracking-widest">{label}</label>
            <input
                type={type}
                name={name}
                value={value}
                onChange={handleInputChange}
                readOnly={isReadOnly}
                placeholder={placeholder}
                className={`w-full px-4 py-3 border-2 border-ink bg-mute text-ink font-mono text-sm focus:outline-none focus:border-primary focus:bg-white transition-colors ${isReadOnly ? 'opacity-70 cursor-not-allowed' : ''}`}
            />
        </div>
    );

    const smtpProviders = [
        {
            name: "Gmail",
            color: "#EA4335",
            steps: ["Enable 2-Step Verification", "Go to Google Account → Security", "Search 'App Passwords'", "Select App: Mail → Other", "Copy the 16-char password"],
            url: "https://myaccount.google.com/apppasswords",
            label: "Open Google"
        },
        {
            name: "Outlook / Hotmail",
            color: "#0078D4",
            steps: ["Sign in to Microsoft account", "Go to Security → Advanced", "Enable two-step verification", "App Passwords → Create new", "Copy the generated password"],
            url: "https://account.live.com/proofs/AppPassword",
            label: "Open Microsoft"
        },
        {
            name: "Yahoo Mail",
            color: "#6001D2",
            steps: ["Sign in to Yahoo Security", "Enable two-step verification", "Click 'Generate app password'", "Name it and click Generate", "Copy the 16-char password"],
            url: "https://login.yahoo.com/account/security/app-passwords/list",
            label: "Open Yahoo"
        }
    ];

    return (
        <DashboardLayout>
            <div className="flex flex-col h-full relative bg-grid-pattern overflow-x-hidden p-8" style={{ backgroundColor: "#F9F9F9" }}>
                {/* TOAST */}
                {toastMessage && (
                    <div className={`fixed top-4 right-4 z-50 px-6 py-4 border-2 ${toastMessage.isError ? 'border-red-500 bg-red-50' : 'border-ink bg-primary text-white'} shadow-[8px_8px_0px_0px_rgba(10,10,10,1)] flex items-center gap-3 animate-in slide-in-from-top-4 fade-in`}>
                        <span className="material-symbols-outlined text-xl">{toastMessage.isError ? 'error' : 'task_alt'}</span>
                        <span className="font-mono text-xs font-bold uppercase tracking-widest">{toastMessage.text}</span>
                    </div>
                )}

                <div className="max-w-5xl mx-auto w-full bg-paper border-2 border-ink shadow-[12px_12px_0px_0px_rgba(10,10,10,1)]">
                    {/* HEADER */}
                    <header className="px-8 py-8 border-b-2 border-ink bg-paper z-10">
                        <div className="flex flex-col gap-2">
                            <span className="font-mono text-[10px] text-ink/60 uppercase tracking-widest">System Configuration // v2.4.0</span>
                            <h1 className="font-display font-bold text-4xl tracking-tight text-ink uppercase">Settings</h1>
                        </div>
                    </header>

                    <div className="flex-1 overflow-visible px-8 py-8">
                        <div>
                            {/* TABS */}
                            <div className="flex border-b-2 border-ink/20 mb-10 overflow-x-auto scroller-hide">
                                {tabs.map(tab => (
                                    <button
                                        key={tab}
                                        type="button"
                                        onClick={() => setActiveTab(tab)}
                                        className={`px-8 py-4 font-mono text-sm font-bold tracking-widest transition-all whitespace-nowrap border-b-4 ${activeTab === tab ? 'border-primary text-primary' : 'border-transparent text-ink/40 hover:text-ink/80 hover:bg-mute/50'}`}
                                    >
                                        {tab}
                                    </button>
                                ))}
                            </div>

                            {/* CONTENT */}
                            <form onSubmit={handleSave} className="animate-in fade-in slide-in-from-bottom-4 duration-500">

                                {/* ── PROFILE ── */}
                                {activeTab === "PROFILE" && (
                                    <div className="space-y-10">
                                        <div className="flex items-center gap-6 pb-8 border-b-2 border-ink/10">
                                            <div className="w-24 h-24 bg-ink flex items-center justify-center text-paper font-display text-4xl font-bold border-2 border-ink">
                                                {getInitials(formData.company_name)}
                                            </div>
                                            <div>
                                                <h2 className="font-display font-bold text-2xl text-ink uppercase">{formData.company_name || 'UNDEFINED PROTOCOL'}</h2>
                                                <p className="font-mono text-xs text-ink/60 uppercase mt-1 tracking-widest">Primary Operational Entity</p>
                                            </div>
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                            <InputField label="Company Name" name="company_name" value={formData.company_name} placeholder="Acme Corp" />
                                            <InputField label="Company Website URL" name="company_website_url" value={formData.company_website_url} placeholder="https://acme.com" />
                                            <InputField label="Region / Country" name="country" value={formData.country} placeholder="United States" />
                                            <div className="flex flex-col gap-2">
                                                <label className="text-xs font-mono font-bold uppercase text-ink/80 tracking-widest">Business Type</label>
                                                <div className="relative">
                                                    <select
                                                        name="business_type"
                                                        value={formData.business_type}
                                                        onChange={handleInputChange}
                                                        className="w-full px-4 py-3 border-2 border-ink bg-mute text-ink font-mono text-sm focus:outline-none focus:border-primary focus:bg-white transition-colors appearance-none cursor-pointer"
                                                    >
                                                        <option value="">— Select Type —</option>
                                                        <option value="SaaS">SaaS</option>
                                                        <option value="E-Commerce">E-Commerce</option>
                                                        <option value="Agency">Agency</option>
                                                        <option value="Finance">Finance</option>
                                                        <option value="Healthcare">Healthcare</option>
                                                        <option value="Manufacturing">Manufacturing</option>
                                                        <option value="Other">Other</option>
                                                    </select>
                                                    <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none">
                                                        <span className="material-symbols-outlined text-ink/60 text-base">expand_more</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex flex-col gap-2">
                                            <label className="text-xs font-mono font-bold uppercase text-ink/80 tracking-widest">Company Description</label>
                                            <textarea
                                                name="company_description"
                                                value={formData.company_description}
                                                onChange={handleInputChange}
                                                placeholder="Briefly describe what your company does..."
                                                rows={3}
                                                className="w-full px-4 py-3 border-2 border-ink bg-mute text-ink font-mono text-sm focus:outline-none focus:border-primary focus:bg-white transition-colors resize-none"
                                            />
                                        </div>
                                    </div>
                                )}

                                {/* ── CONTACTS ── */}
                                {activeTab === "CONTACTS" && (
                                    <div className="space-y-10">
                                        <h2 className="font-mono font-bold text-xl uppercase tracking-widest mb-6 border-l-4 border-primary pl-4 text-ink">Primary Operator Details</h2>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                            <InputField label="Contact Person Name" name="contact_person_name" value={formData.contact_person_name} placeholder="Jane Doe" />
                                            <InputField label="Email Address" name="email" value={formData.email} placeholder="jane@acme.com" />
                                            <InputField label="Phone Number" name="phone_number" value={formData.phone_number} placeholder="+1 (555) 012-3456" />
                                        </div>
                                    </div>
                                )}

                                {/* ── SECURITY ── */}
                                {activeTab === "SECURITY" && (
                                    <div className="space-y-10">
                                        <h2 className="font-mono font-bold text-xl uppercase tracking-widest mb-6 border-l-4 border-red-500 pl-4 text-ink">Access Credentials</h2>
                                        <div className="p-6 border-2 border-ink bg-mute/50 mb-8 max-w-lg">
                                            <p className="font-mono text-xs text-ink/80 leading-relaxed uppercase">
                                                UPDATING YOUR SECURITY KEY WILL TERMINATE ALL ACTIVE SESSIONS. YOU WILL BE REQUIRED TO RE-AUTHENTICATE ON YOUR NEXT LOGIN.
                                            </p>
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                            <InputField type="password" label="New Security Key" name="password" value={formData.password} placeholder="Leave blank to keep unchanged" />
                                            <InputField type="password" label="Confirm Security Key" name="confirm_password" value={formData.confirm_password} placeholder="Re-enter new security key" />
                                        </div>
                                    </div>
                                )}

                                {/* ── INTEGRATIONS ── */}
                                {activeTab === "INTEGRATIONS" && (
                                    <div className="space-y-12">
                                        {/* SMTP Gateway */}
                                        <div className="pt-8 border-t-2 border-ink/10">
                                            {/* Section header */}
                                            <div className="flex items-center justify-between mb-8">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 bg-ink flex items-center justify-center">
                                                        <span className="material-symbols-outlined text-paper text-sm">send</span>
                                                    </div>
                                                    <div>
                                                        <h2 className="font-mono font-bold text-xl uppercase tracking-widest text-ink">SMTP Gateway</h2>
                                                        <p className="font-mono text-[10px] text-ink/50 uppercase tracking-widest mt-0.5">Outbound email delivery configuration</p>
                                                    </div>
                                                </div>
                                                <span className="flex items-center gap-2 px-3 py-1.5 border-2 border-data-green/40 bg-data-green/10 font-mono text-[10px] font-bold uppercase tracking-widest text-data-green">
                                                    <span className="w-1.5 h-1.5 rounded-full bg-data-green animate-pulse"></span>
                                                    Auto-Detected
                                                </span>
                                            </div>

                                            {/* Input fields — only email + app password */}
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
                                                <div className="flex flex-col gap-2">
                                                    <label className="flex items-center gap-2 text-xs font-mono font-bold uppercase text-ink/70 tracking-widest">
                                                        <span className="material-symbols-outlined text-sm text-ink/40">person</span>
                                                        SMTP Username (Your Email)
                                                    </label>
                                                    <input type="text" name="settings.smtp_user" value={formData.settings.smtp_user} onChange={handleInputChange} placeholder="user@gmail.com"
                                                        className="w-full px-4 py-3 border-2 border-ink bg-mute text-ink font-mono text-sm focus:outline-none focus:border-primary focus:bg-white transition-colors" />
                                                    <p className="font-mono text-[10px] text-ink/40 uppercase tracking-wide">SMTP host &amp; port are auto-detected from your email domain</p>
                                                </div>
                                                <div className="flex flex-col gap-2">
                                                    <label className="flex items-center gap-2 text-xs font-mono font-bold uppercase text-ink/70 tracking-widest">
                                                        <span className="material-symbols-outlined text-sm text-ink/40">lock</span>
                                                        SMTP App Password
                                                    </label>
                                                    <input type="password" name="settings.smtp_pass" value={formData.settings.smtp_pass} onChange={handleInputChange} placeholder="Paste App Password here"
                                                        className="w-full px-4 py-3 border-2 border-ink bg-mute text-ink font-mono text-sm focus:outline-none focus:border-primary focus:bg-white transition-colors" />
                                                </div>
                                            </div>

                                            {/* App Password Guide — dark card */}
                                            <div className="border-2 border-ink overflow-hidden shadow-[6px_6px_0px_0px_rgba(10,10,10,1)]">
                                                {/* Header bar */}
                                                <div className="bg-ink px-6 py-4 flex items-center justify-between">
                                                    <div className="flex items-center gap-3">
                                                        <span className="material-symbols-outlined text-primary text-lg">key</span>
                                                        <span className="font-mono text-sm font-bold uppercase tracking-widest text-paper">How to Get Your App Password</span>
                                                    </div>
                                                    <span className="px-3 py-1 bg-primary/20 border border-primary/40 font-mono text-[10px] font-bold uppercase tracking-widest text-primary">Required Step</span>
                                                </div>

                                                {/* Body */}
                                                <div className="p-6 bg-[#111] text-paper">
                                                    <p className="font-mono text-xs text-paper/60 uppercase tracking-wide leading-relaxed mb-6">
                                                        Your email provider requires a dedicated <span className="text-primary font-bold">App Password</span> — not your regular login password — to allow secure third-party email sending.
                                                    </p>

                                                    {/* Provider cards */}
                                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                                                        {smtpProviders.map((provider) => (
                                                            <div key={provider.name} className="border border-paper/10 bg-paper/5 hover:bg-paper/10 transition-all group">
                                                                <div className="flex items-center gap-3 px-4 py-3 border-b border-paper/10" style={{ borderLeftWidth: '3px', borderLeftColor: provider.color }}>
                                                                    <span className="font-mono text-xs font-bold uppercase tracking-widest text-paper">{provider.name}</span>
                                                                </div>
                                                                <div className="px-4 py-4 space-y-2.5">
                                                                    {provider.steps.map((step, i) => (
                                                                        <div key={i} className="flex items-start gap-3">
                                                                            <span className="shrink-0 w-5 h-5 bg-primary/20 border border-primary/40 flex items-center justify-center font-mono text-[9px] font-bold text-primary">{i + 1}</span>
                                                                            <span className="font-mono text-[10px] text-paper/60 uppercase tracking-wide leading-tight">{step}</span>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                                <div className="px-4 pb-4">
                                                                    <a href={provider.url} target="_blank" rel="noopener noreferrer"
                                                                        className="flex items-center justify-between w-full px-3 py-2 border border-paper/20 bg-paper/5 hover:bg-primary hover:border-primary hover:text-ink transition-all font-mono text-[10px] font-bold uppercase tracking-widest text-paper/60">
                                                                        <span>{provider.label}</span>
                                                                        <span className="material-symbols-outlined text-sm">arrow_outward</span>
                                                                    </a>
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>


                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* GLOBAL SAVE BAR */}
                                <div className="mt-12 pt-8 border-t-2 border-ink flex justify-end">
                                    <button
                                        type="submit"
                                        disabled={saving}
                                        className="px-8 py-4 bg-primary text-paper font-bold font-mono text-sm uppercase tracking-widest border-2 border-ink shadow-[4px_4px_0px_0px_rgba(10,10,10,1)] hover:shadow-none hover:translate-x-[4px] hover:translate-y-[4px] transition-all disabled:opacity-50 disabled:cursor-wait">
                                        {saving ? 'UPDATING SYSTEMS...' : 'SAVE CONFIGURATION'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </DashboardLayout>
    );
}
