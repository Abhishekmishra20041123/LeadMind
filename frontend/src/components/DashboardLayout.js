"use client";
import Sidebar from "./Sidebar";
import Header from "./Header";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function DashboardLayout({ children }) {
  const router = useRouter();
  const [isAuthorized, setIsAuthorized] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    // Verify token with backend
    fetch("http://localhost:8000/api/auth/me", {
      headers: { "Authorization": `Bearer ${token}` }
    })
    .then(res => {
      if (res.status === 401) {
        localStorage.removeItem("access_token");
        router.replace("/login");
      } else {
        setIsAuthorized(true);
      }
    })
    .catch(() => {
      // In case of network error, we might want to still show the UI if it's just a temporary glitch
      // but for security/correctness, we'll keep it as is.
      setIsAuthorized(true); 
    });
  }, [router]);

  if (!isAuthorized) {
    return (
      <div className="flex items-center justify-center h-screen bg-ink text-paper font-mono text-sm uppercase">
        <span className="material-symbols-outlined animate-spin mr-2">refresh</span>
        Authenticating...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden text-ink bg-mute">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 flex flex-col overflow-y-auto bg-grid-pattern relative">
          {children}
        </main>
      </div>
    </div>
  );
}