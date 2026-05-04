"use client";
import { useEffect, useState } from "react";

export default function Header() {
    const [user, setUser] = useState(null);

    useEffect(() => {
        const token = localStorage.getItem("access_token");
        if (token) {
            fetch("http://localhost:8000/api/auth/me", {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            })
                .then(res => res.json())
                .then(data => setUser(data))
                .catch(console.error);
        }
    }, []);

    const userDisplay = user?.company_name || user?.email || "";
    // On the client, check if we have a token loosely to know if we should show logout
    const [isLoggedIn, setIsLoggedIn] = useState(false);

    useEffect(() => {
        setIsLoggedIn(!!localStorage.getItem("access_token"));
    }, []);

    const handleLogout = () => {
        localStorage.removeItem("access_token");
        window.location.href = "/login";
    };

    return (
        <header className="bg-ink text-paper h-12 flex items-center justify-between px-6 border-b border-ink shrink-0 z-50">
            <div className="flex items-center gap-3">
                <div className="w-8 h-8 flex items-center justify-center">
                    <img src="/logo.png" alt="LeadMind" className="w-full h-full object-contain" />
                </div>
                <a href="/" className="font-display font-bold text-xl tracking-tight hover:text-primary transition-colors">
                    LeadMind
                </a>
            </div>

            <div className="flex items-center gap-6 font-mono text-sm">
                <div className="flex items-center gap-2 hidden md:flex">
                    <span className="w-2 h-2 bg-data-green rounded-full animate-pulse"></span>
                    <span>SYSTEM ONLINE</span>
                </div>

                <div className="border-l border-white/20 pl-6 flex items-center gap-4">
                    {isLoggedIn ? (
                        <>
                            <span className="uppercase text-paper/70 hidden sm:inline-block">COMPANY NAME: <span className="text-paper font-bold">{userDisplay || "Loading..."}</span></span>
                            <button
                                onClick={handleLogout}
                                className="px-3 py-1 text-xs border border-paper/30 hover:bg-paper hover:text-ink transition-colors uppercase font-bold"
                            >
                                Logout
                            </button>
                        </>
                    ) : (
                        <div className="flex gap-3">
                            <a href="/login" className="px-4 py-1.5 text-xs hover:text-primary transition-colors uppercase font-bold">
                                Sign In
                            </a>
                            <a href="/signup" className="px-4 py-1.5 text-xs bg-primary text-white hover:bg-white hover:text-ink transition-colors uppercase font-bold">
                                Sign Up
                            </a>
                        </div>
                    )}
                </div>
            </div>
        </header>
    );
}
