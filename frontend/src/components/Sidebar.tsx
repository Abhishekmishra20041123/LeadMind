import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Sidebar() {
    const pathname = usePathname();

    const navItems = [
        { name: "Mission Control", path: "/", icon: "dashboard" },
        { name: "Sales Pipeline", path: "/ledger", icon: "table_chart" },
        { name: "Data Upload", path: "/upload", icon: "cloud_upload" },
        { name: "Email Designer", path: "/email-designer", icon: "draw" },
        { name: "Agent Monitor", path: "/agents", icon: "memory", badge: "RUNNING" },
        { name: "Settings", path: "/settings", icon: "settings" },
    ];

    return (
        <aside className="w-[250px] bg-paper border-r border-ink flex flex-col shrink-0 overflow-y-auto hidden md:flex">
            <nav className="flex flex-col w-full">
                {navItems.map((item) => {
                    const isActive = pathname === item.path;
                    return (
                        <Link
                            key={item.path}
                            href={item.path}
                            className={`group flex items-center gap-3 px-6 py-4 border-b border-ink transition-colors ${isActive ? 'bg-ink text-paper hover:bg-ink' : 'hover:bg-mute'}`}
                        >
                            <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
                            <span className={`font-display text-sm tracking-wide uppercase transition-colors ${isActive ? 'font-bold' : 'font-medium group-hover:text-primary'}`}>
                                {item.name}
                            </span>

                            {item.badge && !isActive && (
                                <span className="ml-auto font-mono text-xs bg-mute px-1 border border-ink text-ink">
                                    {item.badge}
                                </span>
                            )}

                            {isActive && (
                                <span className="ml-auto w-1.5 h-1.5 bg-primary"></span>
                            )}
                        </Link>
                    )
                })}
            </nav>


        </aside>
    );
}
