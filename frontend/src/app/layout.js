import "./globals.css";

export const metadata = {
    title: "LeadMind // Dashboard",
    description: "LeadMind Sales Dashboard",
};

export default function RootLayout({ children }) {
    return (
        <html lang="en">
            <head>
                <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300..700&family=Inter+Tight:wght@100..900&family=JetBrains+Mono:wght@100..800&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet" />
            </head>
            <body className="bg-mute text-ink font-body h-screen overflow-hidden flex flex-col" suppressHydrationWarning>{children}</body>
        </html>
    );
}
