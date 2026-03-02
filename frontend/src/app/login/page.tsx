'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function LoginPage() {
    const router = useRouter();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const response = await fetch('http://localhost:8000/api/auth/signin', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Login failed');
            }

            localStorage.setItem('access_token', data.access_token);
            router.push('/');
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-background-light dark:bg-background-dark font-body antialiased">
            <div className="relative flex h-screen w-full flex-col lg:flex-row overflow-hidden">
                {/* Left Side: Military Grid Aesthetic */}
                <div className="relative hidden lg:flex w-1/2 flex-col justify-between bg-[#0a0a0a] p-12 border-r border-primary/20 overflow-hidden">
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

                {/* Decorative corner elements */}
                <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-primary/30"></div>
                <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-primary/30"></div>
                <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-primary/30"></div>
                <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-primary/30"></div>

                {/* Right Side: Sign-In Form (Mobile view defaults here) */}
                <div className="flex flex-1 flex-col justify-center bg-background-light dark:bg-slate-50 px-6 py-8 sm:px-12 lg:px-20 h-full overflow-y-auto">
                    {/* Mobile Header Only */}
                    <div className="lg:hidden mb-8 flex items-center justify-between border-b border-slate-200 pb-4 shrink-0">
                        <div className="flex flex-col">
                            <span className="font-mono text-[10px] text-primary font-bold tracking-widest">SYSTEM V4.0.1</span>
                            <h2 className="font-display text-xl font-bold text-slate-900 uppercase">Strategic Grid</h2>
                        </div>
                        <span className="material-symbols-outlined text-slate-900">shield</span>
                    </div>

                    <div className="mx-auto w-full max-w-sm">
                        <div className="mb-10">
                            <h3 className="font-display text-4xl font-bold tracking-tight text-slate-900">Welcome Back</h3>
                            <p className="mt-2 text-sm text-slate-500 font-mono">Secure Terminal Access Required</p>
                        </div>

                        {error && (
                            <div className="mb-6 p-4 border border-primary bg-primary/5 text-primary font-mono text-xs uppercase tracking-wide">
                                [ERROR] {error}
                            </div>
                        )}

                        <form className="space-y-6" onSubmit={handleSubmit}>
                            <div>
                                <label htmlFor="email" className="block font-mono text-[11px] font-bold uppercase tracking-wider text-slate-900 mb-1">
                                    Official Business Email
                                </label>
                                <div className="relative">
                                    <input id="email" name="email" type="email" autoComplete="email" required
                                        value={email} onChange={(e) => setEmail(e.target.value)}
                                        className="block w-full border border-slate-900 bg-transparent px-4 py-4 text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-primary focus:border-primary rounded-none font-body transition-all"
                                        placeholder="name@company.gov" />
                                </div>
                            </div>

                            <div>
                                <div className="flex items-center justify-between mb-1">
                                    <label htmlFor="password" className="block font-mono text-[11px] font-bold uppercase tracking-wider text-slate-900">
                                        Password
                                    </label>
                                </div>
                                <div className="relative">
                                    <input id="password" name="password" type="password" autoComplete="current-password" required
                                        value={password} onChange={(e) => setPassword(e.target.value)}
                                        className="block w-full border border-slate-900 bg-transparent px-4 py-4 text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-primary focus:border-primary rounded-none font-body transition-all"
                                        placeholder="••••••••" />
                                </div>
                            </div>

                            <div className="flex items-center justify-between">
                                <div className="flex items-center">
                                    <input id="remember-me" name="remember-me" type="checkbox"
                                        className="h-4 w-4 border-slate-900 text-primary focus:ring-primary rounded-none" />
                                    <label htmlFor="remember-me" className="ml-2 block text-xs font-mono text-slate-700">Remember Station</label>
                                </div>
                                <Link href="#" className="font-mono text-xs font-bold text-primary hover:underline underline-offset-4">Forgot Password?</Link>
                            </div>

                            <div>
                                <button type="submit" disabled={loading}
                                    className="flex w-full justify-center bg-primary px-4 py-5 text-sm font-bold uppercase tracking-widest text-white hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded-none transition-colors disabled:opacity-50">
                                    {loading ? 'Authenticating...' : 'Sign In'}
                                </button>
                            </div>
                        </form>

                        <div className="mt-12 text-center border-t border-slate-200 pt-8">
                            <p className="font-mono text-xs text-slate-500">
                                Don't have an account?{' '}
                                <Link href="/signup" className="font-bold text-slate-900 hover:text-primary transition-colors">Sign up</Link>
                            </p>
                        </div>

                        {/* Technical Footer for Form */}
                        <div className="mt-12 flex flex-col items-center gap-2 opacity-30 shrink-0">
                            <div className="h-px w-full bg-slate-200"></div>
                            <div className="flex w-full justify-between font-mono text-[9px] text-slate-400 uppercase tracking-tighter">
                                <span>12</span>
                                <span>34</span>
                                <span>56</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
