'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function SignupPage() {
    const router = useRouter();
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const [formData, setFormData] = useState({
        companyName: '',
        companyWebsiteUrl: '',
        country: '',
        contactPersonName: '',
        email: '',
        phoneNumber: '',
        password: '',
        confirmPassword: ''
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
        setError('');
    };

    const handleNextStage = (e: React.FormEvent) => {
        e.preventDefault();
        setStep(step + 1);
    };

    const handlePrevStage = () => {
        setStep(step - 1);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (formData.password !== formData.confirmPassword) {
            setError("Passwords do not match");
            return;
        }

        setLoading(true);
        setError('');

        try {
            // Map camelCase to backend snake_case
            const payload = {
                company_name: formData.companyName,
                company_website_url: formData.companyWebsiteUrl,
                country: formData.country,
                contact_person_name: formData.contactPersonName,
                email: formData.email,
                phone_number: formData.phoneNumber,
                password: formData.password
            };

            const response = await fetch('http://localhost:8000/api/auth/signup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            const data = await response.json();

            if (!response.ok) {
                if (Array.isArray(data.detail)) {
                    const messages = data.detail.map((err: any) => err.msg).join('; ');
                    throw new Error(messages);
                }
                throw new Error(data.detail || 'Signup failed');
            }

            localStorage.setItem('access_token', data.access_token);
            router.push('/');

        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (step === 1) {
        return (
            <div className="flex h-screen w-full flex-col lg:flex-row bg-background-dark font-display antialiased overflow-hidden">
                {/* Left Side: Pitch Black Military Aesthetic */}
                <div className="hidden lg:flex w-1/3 bg-[#0a0a0a] relative border-r border-primary/20 overflow-hidden flex-col justify-between p-12">
                    <div className="bg-military-grid absolute inset-0 z-0"></div>
                    <div className="relative z-10">
                        <div className="flex items-center gap-4">
                            <div className="w-8 h-[2px] bg-primary"></div>
                            <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-primary font-bold">System Auth v4.0.1</p>
                        </div>
                    </div>
                    <div className="relative z-10 flex-1 flex flex-col items-start justify-center py-10 overflow-hidden">
                        <h1 className="vertical-text text-[8vh] max-h-full font-bold tracking-tighter text-slate-100 uppercase leading-none select-none whitespace-nowrap">
                            STRATEGIC <span className="text-primary">GRID</span>
                        </h1>
                    </div>
                    <div className="relative z-10 flex flex-col gap-6">
                        <p className="font-mono text-[10px] text-slate-500 uppercase leading-relaxed max-w-[200px] tracking-widest font-bold">
                            Standard protocol for high-density infrastructure verification.
                        </p>
                        <div className="h-[2px] w-full bg-primary/80"></div>
                    </div>
                </div>

                {/* Right Side: Clean White Signup Form */}
                <div className="flex-1 bg-background-light dark:bg-background-light h-full overflow-y-auto flex flex-col relative w-full lg:w-2/3">
                    {/* Mobile Navigation Header */}
                    <div className="flex items-center justify-between p-6 border-b border-slate-200">
                        <div className="flex items-center gap-4">
                            <span className="material-symbols-outlined text-slate-900">arrow_back</span>
                            <h2 className="text-slate-900 text-xl font-bold uppercase tracking-tight">Signup Stage 1</h2>
                        </div>
                        <div className="flex flex-col items-end">
                            <span className="font-mono text-[10px] text-slate-500 uppercase tracking-widest font-bold">Protocol</span>
                            <span className="font-mono text-[12px] text-primary font-bold">1 of 3</span>
                        </div>
                    </div>
                    {/* Progress Bar */}
                    <div className="w-full h-1 bg-slate-100">
                        <div className="h-full bg-primary" style={{ width: '33.33%' }}></div>
                    </div>

                    <div className="flex-1 flex flex-col p-6 lg:px-12 lg:py-8 max-w-2xl mx-auto w-full justify-center">
                        <div className="mb-8">
                            <h3 className="text-4xl font-bold text-slate-900 uppercase tracking-tight mb-2">Company Details</h3>
                            <p className="font-sans text-slate-500 text-lg">Initialize your organizational profile for system integration.</p>
                        </div>

                        <form className="space-y-6" onSubmit={handleNextStage}>
                            <div className="relative group">
                                <label className="absolute -top-3 left-4 bg-white px-2 font-mono text-[11px] font-bold text-slate-900 uppercase tracking-widest z-10 transition-all group-focus-within:text-primary">
                                    Company Name
                                </label>
                                <input name="companyName" value={formData.companyName} onChange={handleChange} required
                                    className="w-full h-16 border-2 border-slate-900 rounded-none px-6 font-mono text-sm tracking-tight focus:ring-0 focus:border-primary placeholder:text-slate-300 text-slate-900 bg-transparent uppercase"
                                    placeholder="ENTER LEGAL ENTITY NAME" type="text" />
                            </div>

                            <div className="relative group">
                                <label className="absolute -top-3 left-4 bg-white px-2 font-mono text-[11px] font-bold text-slate-900 uppercase tracking-widest z-10 transition-all group-focus-within:text-primary">
                                    Company Website URL
                                </label>
                                <input name="companyWebsiteUrl" value={formData.companyWebsiteUrl} onChange={handleChange} required
                                    className="w-full h-16 border-2 border-slate-900 rounded-none px-6 font-mono text-sm tracking-tight focus:ring-0 focus:border-primary placeholder:text-slate-300 text-slate-900 bg-transparent uppercase"
                                    placeholder="HTTPS://ORGANIZATION.DOMAIN" type="url" />
                            </div>

                            <div className="relative group">
                                <label className="absolute -top-3 left-4 bg-white px-2 font-mono text-[11px] font-bold text-slate-900 uppercase tracking-widest z-10 transition-all group-focus-within:text-primary">
                                    Operating Region / Country
                                </label>
                                <div className="relative">
                                    <select name="country" value={formData.country} onChange={handleChange} required
                                        className="w-full h-16 border-2 border-slate-900 rounded-none px-6 font-mono text-sm tracking-tight focus:ring-0 focus:border-primary text-slate-900 bg-transparent appearance-none uppercase cursor-pointer">
                                        <option disabled value="">SELECT REGION</option>
                                        <option value="United States">UNITED STATES</option>
                                        <option value="United Kingdom">UNITED KINGDOM</option>
                                        <option value="European Union">EUROPEAN UNION</option>
                                        <option value="Asia Pacific">ASIA PACIFIC</option>
                                    </select>
                                    <div className="absolute inset-y-0 right-0 flex items-center pr-4 pointer-events-none">
                                        <span className="material-symbols-outlined text-slate-900">expand_more</span>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-slate-50 border-l-4 border-primary p-4 flex gap-4">
                                <span className="material-symbols-outlined text-primary">info</span>
                                <p className="font-mono text-[10px] text-slate-600 leading-tight uppercase">Ensure legal entity name matches official registration for smooth verification.</p>
                            </div>

                            <div className="pt-4 flex flex-col gap-4">
                                <button type="submit"
                                    className="w-full h-14 bg-primary text-white font-mono font-bold text-lg uppercase tracking-[0.2em] flex items-center justify-center gap-3 transition-transform active:scale-[0.98] border-2 border-primary">
                                    Continue to step 2
                                    <span className="material-symbols-outlined">arrow_forward</span>
                                </button>
                                <div className="flex justify-between items-center px-2">
                                    <p className="font-mono text-[10px] text-slate-400 uppercase">Status: Session Active</p>
                                    <p className="font-mono text-[10px] text-slate-400 uppercase">
                                        <Link href="/login" className="hover:text-primary">Already have an account?</Link>
                                    </p>
                                </div>
                            </div>
                        </form>
                    </div>

                    {/* Footer for visual balance */}
                    <div className="p-4 border-t border-slate-100 flex justify-between items-center shrink-0">
                        <img alt="Security Partner Logo" className="h-6 opacity-30 grayscale" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAV1MCjGHqGVuhCiWfdShFzfHAJHmkF0BpWbt7oxCqJB7vM3Q-uRPbN-zfzkYcuYMIJAkEPUERMclwcQxSG4RI43odfoOPDQNbGxPSb7Wyww5A0EZL7j_o12FY3Fkg5JdmACbf2mqSwDh3li-eSVKf0tixugzPxHxu_V1fdTuK8B_z1xWSJDznFJDRgjkVw0s-HpilpAz2cQsFzlxn1QYFKzg09vJWxCSLHiYwggmeMBpFt0I2LtTfThgNnnTWElgreDqPU0ioUjNQt" />
                        <span className="font-mono text-[10px] text-slate-400 uppercase tracking-widest">Proprietary Military Grade Infrastructure</span>
                    </div>
                </div>
            </div>
        );
    }

    if (step === 2) {
        return (
            <div className="flex flex-col md:flex-row h-screen w-full bg-background-dark font-sans antialiased overflow-hidden">
                <div className="hidden md:flex md:w-1/3 bg-[#0a0a0a] relative flex-col justify-between p-12 border-r border-primary/20 overflow-hidden">
                    <div className="bg-military-grid absolute inset-0 z-0"></div>
                    <div className="relative z-10">
                        <div className="flex items-center gap-4">
                            <div className="w-8 h-[2px] bg-primary"></div>
                            <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-primary font-bold">System Auth v4.0.1</p>
                        </div>
                    </div>
                    <div className="relative z-10 flex-1 flex flex-col items-start justify-center py-10 overflow-hidden">
                        <h1 className="vertical-text text-[8vh] max-h-full font-bold tracking-tighter text-slate-100 uppercase leading-none select-none whitespace-nowrap">
                            STRATEGIC <span className="text-primary">GRID</span>
                        </h1>
                    </div>
                    <div className="relative z-10 flex flex-col gap-6">
                        <p className="font-mono text-[10px] text-slate-500 uppercase leading-relaxed max-w-[200px] tracking-widest font-bold">
                            Standard protocol for high-density infrastructure verification.
                        </p>
                        <div className="h-[2px] w-full bg-primary/80"></div>
                    </div>
                </div>

                <div className="flex-1 bg-background-light dark:bg-background-light h-full overflow-y-auto flex flex-col relative w-full lg:w-2/3">
                    <div className="md:hidden flex items-center justify-between px-6 py-6 border-b border-black shrink-0">
                        <div className="flex items-center gap-3" onClick={handlePrevStage}>
                            <span className="material-symbols-outlined text-black text-xl cursor-pointer">arrow_back_ios</span>
                            <span className="font-display font-bold text-sm tracking-tight uppercase">Stage 2</span>
                        </div>
                        <div className="font-mono text-[10px] font-bold text-black/40 tracking-widest">STEP 02/03</div>
                    </div>

                    <div className="flex-1 flex flex-col p-6 md:px-12 md:py-8 max-w-xl mx-auto w-full justify-center">
                        <header className="mb-8">
                            <h2 className="text-4xl md:text-5xl font-bold text-black tracking-tighter uppercase mb-4 font-display leading-none">
                                Contact Details
                            </h2>
                            <p className="font-mono text-[11px] text-black tracking-wider uppercase">
                                Verification of operational leadership required.
                            </p>
                        </header>

                        <form className="space-y-6" onSubmit={handleNextStage}>
                            <div className="relative group">
                                <label className="absolute -top-2.5 left-4 bg-white px-2 font-mono text-[10px] font-bold text-black z-10 uppercase tracking-widest">
                                    Contact Person Name
                                </label>
                                <input name="contactPersonName" value={formData.contactPersonName} onChange={handleChange} required
                                    className="w-full bg-transparent border border-black px-4 py-5 font-mono text-sm text-black placeholder:text-black/10 rounded-none focus:ring-0 focus:border-primary transition-all uppercase"
                                    placeholder="Enter Full Name" type="text" />
                            </div>

                            <div className="relative group">
                                <label className="absolute -top-2.5 left-4 bg-white px-2 font-mono text-[10px] font-bold text-black z-10 uppercase tracking-widest">
                                    Official Business Email
                                </label>
                                <input name="email" value={formData.email} onChange={handleChange} required
                                    className="w-full bg-transparent border border-black px-4 py-5 font-mono text-sm text-black placeholder:text-black/10 rounded-none focus:ring-0 focus:border-primary transition-all"
                                    placeholder="name@organization.gov" type="email" />
                                <p className="mt-2 font-mono text-[9px] text-black/50 uppercase tracking-tight">Security check: Public domains are automatically rejected.</p>
                            </div>

                            <div className="relative group">
                                <label className="absolute -top-2.5 left-4 bg-white px-2 font-mono text-[10px] font-bold text-black z-10 uppercase tracking-widest">
                                    Phone Number
                                </label>
                                <div className="flex">
                                    <div className="flex items-center justify-center border border-black border-r-0 px-4 font-mono text-sm text-black bg-white">
                                        +1
                                    </div>
                                    <input name="phoneNumber" value={formData.phoneNumber} onChange={handleChange} required
                                        className="w-full bg-transparent border border-black px-4 py-5 font-mono text-sm text-black placeholder:text-black/10 rounded-none focus:ring-0 focus:border-primary transition-all"
                                        placeholder="000-000-0000" type="tel" />
                                </div>
                            </div>

                            <div className="flex flex-col gap-4 pt-4">
                                <button type="submit"
                                    className="w-full py-4 bg-primary border border-black font-mono text-xs font-bold uppercase tracking-[0.2em] text-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] active:translate-x-[2px] active:translate-y-[2px] active:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all">
                                    Continue Execution
                                </button>
                                <button type="button" onClick={handlePrevStage}
                                    className="w-full py-4 border border-black font-mono text-xs font-bold uppercase tracking-[0.2em] text-black hover:bg-black hover:text-white transition-all">
                                    [ Back ]
                                </button>
                            </div>
                        </form>

                        <div className="mt-8 pt-6 flex flex-col md:flex-row justify-between items-start md:items-end gap-6 border-t border-black/10 shrink-0">
                            <div className="flex flex-col gap-1">
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 bg-primary rounded-full"></div>
                                    <span className="font-mono text-[9px] text-black/40 uppercase tracking-widest leading-none">Operational Security Level 4</span>
                                </div>
                                <span className="font-mono text-[9px] text-black/40 uppercase tracking-widest leading-none ml-4">Strategic Grid Access Control</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="md:hidden fixed bottom-6 left-2 pointer-events-none z-20">
                    <p className="font-mono text-[8px] text-black/20 vertical-text uppercase tracking-[0.3em] font-bold">
                        STRATEGIC GRID // SYSTEM V4.0.1
                    </p>
                </div>
                <div className="hidden md:block fixed bottom-12 left-12 pointer-events-none">
                    <div className="flex flex-col gap-1">
                        <p className="font-mono text-[9px] text-white/40 uppercase tracking-widest">Lat: 38.8977° N</p>
                        <p className="font-mono text-[9px] text-white/40 uppercase tracking-widest">Lon: 77.0365° W</p>
                    </div>
                </div>
            </div>
        );
    }

    if (step === 3) {
        return (
            <div className="flex flex-col md:flex-row h-screen w-full bg-background-dark font-display antialiased overflow-hidden">
                <div className="hidden md:flex w-1/3 bg-[#0a0a0a] border-r border-primary/20 relative overflow-hidden flex-col justify-between p-12">
                    <div className="bg-military-grid absolute inset-0 z-0"></div>
                    <div className="relative z-10">
                        <div className="flex items-center gap-4">
                            <div className="w-8 h-[2px] bg-primary"></div>
                            <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-primary font-bold">System Auth v4.0.1</p>
                        </div>
                    </div>
                    <div className="relative z-10 flex-1 flex flex-col items-start justify-center py-10 overflow-hidden">
                        <h1 className="vertical-text text-[8vh] max-h-full font-bold tracking-tighter text-slate-100 uppercase leading-none select-none whitespace-nowrap">
                            STRATEGIC <span className="text-primary">GRID</span>
                        </h1>
                    </div>
                    <div className="relative z-10 flex flex-col gap-6">
                        <p className="font-mono text-[10px] text-slate-500 uppercase leading-relaxed max-w-[200px] tracking-widest font-bold">
                            Standard protocol for high-density infrastructure verification.
                        </p>
                        <div className="h-[2px] w-full bg-primary/80"></div>
                    </div>
                </div>

                <div className="flex-1 bg-white dark:bg-white h-full overflow-y-auto flex flex-col relative w-full lg:w-2/3">
                    <div className="flex items-center justify-between p-6 border-b border-black md:hidden shrink-0">
                        <span className="material-symbols-outlined text-black cursor-pointer" onClick={handlePrevStage}>arrow_back</span>
                        <span className="font-mono text-xs font-bold text-black tracking-widest uppercase">Stage 3 of 3</span>
                        <span className="material-symbols-outlined text-black opacity-0">close</span>
                    </div>

                    <div className="flex-1 flex flex-col justify-center max-w-md mx-auto w-full px-6 py-8">
                        {error && (
                            <div className="mb-6 p-4 border-2 border-primary bg-primary/10 text-primary font-mono text-sm uppercase tracking-wide">
                                [ERROR] {error}
                            </div>
                        )}

                        <div className="hidden md:flex items-center gap-4 mb-8">
                            <span className="font-mono text-xs font-bold text-black bg-black/5 px-2 py-1">STEP 03</span>
                            <div className="flex-1 h-[1px] bg-black/10"></div>
                            <span className="font-mono text-xs text-black/40">SECURITY CONFIG</span>
                        </div>

                        <div className="mb-8">
                            <h2 className="text-black text-4xl font-bold leading-none tracking-tight mb-2">Signup Stage 3</h2>
                            <p className="text-black/60 text-lg font-medium">Security protocol activation</p>
                        </div>

                        <form className="space-y-6" onSubmit={handleSubmit}>
                            <div className="relative group">
                                <label className="absolute -top-3 left-4 bg-white px-2 font-mono text-[10px] uppercase font-bold text-black z-10">
                                    Access Password
                                </label>
                                <div className="relative">
                                    <input name="password" value={formData.password} onChange={handleChange} required
                                        className="w-full border-black border-2 bg-transparent px-4 py-5 font-mono text-black focus:ring-0 focus:border-primary placeholder:text-black/10 rounded-none transition-colors"
                                        placeholder="••••••••" type="password" />
                                    <span className="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-black/40 cursor-pointer hover:text-black">visibility</span>
                                </div>
                            </div>

                            <div className="relative group">
                                <label className="absolute -top-3 left-4 bg-white px-2 font-mono text-[10px] uppercase font-bold text-black z-10">
                                    Confirm Identity Key
                                </label>
                                <div className="relative">
                                    <input name="confirmPassword" value={formData.confirmPassword} onChange={handleChange} required
                                        className="w-full border-black border-2 bg-transparent px-4 py-5 font-mono text-black focus:ring-0 focus:border-primary placeholder:text-black/10 rounded-none transition-colors"
                                        placeholder="••••••••" type="password" />
                                    <span className="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-black/40 cursor-pointer hover:text-black">lock</span>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-2">
                                <div className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 bg-primary"></div>
                                    <span className="font-mono text-[9px] uppercase text-black/60">Min 12 Chars</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 bg-black/20"></div>
                                    <span className="font-mono text-[9px] uppercase text-black/60">Special Symbol</span>
                                </div>
                            </div>

                            <div className="pt-4 flex flex-col gap-4">
                                <button type="submit" disabled={loading}
                                    className="w-full bg-primary text-white font-bold py-4 px-8 uppercase tracking-widest text-sm hover:brightness-110 active:scale-[0.98] transition-all flex items-center justify-between disabled:opacity-50">
                                    <span>{loading ? 'Creating...' : 'Create Account'}</span>
                                    <span className="material-symbols-outlined">terminal</span>
                                </button>
                                <button type="button" onClick={handlePrevStage}
                                    className="w-full border border-black/10 text-black/40 font-mono text-xs uppercase py-3 hover:bg-black/5 transition-colors">
                                    Return to Previous Stage
                                </button>
                            </div>
                        </form>
                    </div>

                    <div className="md:hidden border-t border-black/5 bg-white p-4 shrink-0">
                        <div className="flex justify-between items-center px-4">
                            <a className="text-primary flex flex-col items-center gap-1" href="#">
                                <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>shield</span>
                                <span className="font-mono text-[8px] font-bold">SECURE</span>
                            </a>
                            <a className="text-black/20 flex flex-col items-center gap-1" href="#">
                                <span className="material-symbols-outlined">dataset</span>
                                <span className="font-mono text-[8px] font-bold">GRID</span>
                            </a>
                            <a className="text-black/20 flex flex-col items-center gap-1" href="#">
                                <span className="material-symbols-outlined">account_circle</span>
                                <span className="font-mono text-[8px] font-bold">USER</span>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return null;
}
