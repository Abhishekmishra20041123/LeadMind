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

    const userDisplay = user?.company_name || user?.email || "CMD_ALEX_R";

    return (
        <header className="bg-ink text-paper h-12 flex items-center justify-between px-6 border-b border-ink shrink-0 z-50">
            <div className="flex items-center gap-4">
                <span className="material-symbols-outlined text-[20px]">grid_view</span>
                <h1 className="font-display font-bold text-lg tracking-tight">STRATEGIC GRID <span className="text-primary text-xs align-top ml-1">v2.4.0</span></h1>
            </div>

            <div className="flex items-center gap-6 font-mono text-sm">
                <div className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-data-green rounded-full animate-pulse"></span>
                    <span>SYSTEM ONLINE</span>
                </div>
                <div className="border-l border-white/20 pl-6">
                    <span className="uppercase">USER: {userDisplay}</span>
                </div>
            </div>
        </header>
    );
}
