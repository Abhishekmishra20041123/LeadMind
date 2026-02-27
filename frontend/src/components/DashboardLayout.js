"use client";
import Sidebar from "./Sidebar";
import Header from "./Header";

export default function DashboardLayout({ children }) {
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