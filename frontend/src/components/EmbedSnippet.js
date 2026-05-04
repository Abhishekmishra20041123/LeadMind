"use client";
import { useState } from "react";
import { Check, Copy, Code2, Info } from "lucide-react";

export default function EmbedSnippet({ apiKey }) {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState("html");

  const apiHostUrl =
    typeof window !== "undefined" && window.location.hostname !== "localhost"
      ? process.env.NEXT_PUBLIC_API_URL || window.location.origin
      : "http://localhost:8000";

  const scriptTag = `src="${apiHostUrl}/public/sdk/leadmind-tracker.js"\n    data-api-key="${apiKey}"\n    data-api-host="${apiHostUrl}"`;

  const snippets = {
    html: {
      label: "HTML / WordPress",
      icon: "🌐",
      file: "index.html  (every page, or shared header)",
      position: "Paste just before </head> on every page. For WordPress, add to your theme's header.php or via a plugin like Insert Headers and Footers.",
      code:
`<!-- LeadMind Tracking — paste before </head> -->
<script
  ${scriptTag}
  async>
</script>`,
    },

    react: {
      label: "React (CRA)",
      icon: "⚛️",
      file: "public/index.html",
      position: 'Paste inside <head> of public/index.html — the single HTML shell that wraps all React routes. This runs once on every page.',
      code:
`<!-- File: public/index.html -->
<!-- Paste inside <head>, before </head> -->
<script
  ${scriptTag}
  async>
</script>`,
    },

    vite: {
      label: "Vite",
      icon: "⚡",
      file: "index.html  (project root — NOT inside /public)",
      position: "In Vite, the shell HTML lives at the project ROOT, not inside /public. Paste inside <head> of that root index.html.",
      code:
`<!-- File: index.html  (Vite project root) -->
<!-- Paste inside <head>, before </head> -->
<script
  ${scriptTag}
  async>
</script>`,
    },

    nextjs: {
      label: "Next.js App Router",
      icon: "▲",
      file: "app/layout.tsx  (or app/layout.js)",
      position: 'Use the built-in <Script> component with strategy="afterInteractive". This loads after hydration so it never blocks React.',
      code:
`// File: app/layout.tsx
import Script from "next/script";

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head />
      <body>
        <Script
          id="leadmind-tracker"
          ${scriptTag}
          strategy="afterInteractive"
        />
        {children}
      </body>
    </html>
  );
}`,
    },

    nextjs_pages: {
      label: "Next.js Pages Router",
      icon: "📄",
      file: "pages/_document.tsx  (or pages/_document.js)",
      position: "Place inside the <Head> component in _document — this runs on every page in the Pages Router.",
      code:
`// File: pages/_document.tsx
import { Html, Head, Main, NextScript } from "next/document";

export default function Document() {
  return (
    <Html lang="en">
      <Head>
        <script
          ${scriptTag}
          async
        />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}`,
    },
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(snippets[activeTab].code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!apiKey) {
    return (
      <div className="p-6 bg-yellow-500/10 border-2 border-yellow-500 text-yellow-700 text-sm font-mono flex items-center gap-3">
        <Info className="w-5 h-5 flex-shrink-0" />
        Generate an API key above to view your personalised tracking snippet.
      </div>
    );
  }

  const tab = snippets[activeTab];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h3 className="text-xl font-display font-black text-ink uppercase tracking-tight flex items-center gap-2">
          <Code2 className="w-5 h-5" /> Install Tracking SDK
        </h3>
        <p className="text-sm font-mono text-ink/60 mt-1">
          Select your framework — SDK auto-tracks page views, scroll depth, clicks, UTM params, device info, cart &amp; checkout events.
        </p>
      </div>

      {/* Framework Tabs */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(snippets).map(([key, data]) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`px-3 py-1.5 font-mono text-xs font-bold border-2 transition-all flex items-center gap-1.5 ${
              activeTab === key
                ? "border-ink bg-ink text-paper shadow-[2px_2px_0px_0px_rgba(0,0,0,1)]"
                : "border-ink/20 text-ink/60 hover:border-ink hover:text-ink bg-paper"
            }`}
          >
            <span>{data.icon}</span> {data.label}
          </button>
        ))}
      </div>

      {/* Placement hint */}
      <div className="bg-blue-50 border-2 border-blue-300 p-3 flex gap-3">
        <Info className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-mono text-[11px] font-bold text-blue-700 uppercase tracking-wider mb-0.5">
            File: <span className="text-blue-900">{tab.file}</span>
          </p>
          <p className="text-xs text-blue-800">{tab.position}</p>
        </div>
      </div>

      {/* Code block */}
      <div className="relative group">
        <button
          onClick={copyToClipboard}
          className="absolute top-3 right-3 z-10 flex items-center gap-2 px-3 py-1.5 bg-white/10 hover:bg-white/20 border border-white/20 text-white font-mono text-xs uppercase tracking-wider backdrop-blur-sm transition-all"
        >
          {copied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
          {copied ? "Copied!" : "Copy"}
        </button>
        <div className="bg-[#0f1115] text-[#e2e8f0] p-5 pt-10 overflow-x-auto font-mono text-xs leading-relaxed border-4 border-ink shadow-[6px_6px_0px_0px_rgba(0,0,0,1)]">
          <pre><code>{tab.code}</code></pre>
        </div>
      </div>

      {/* Usage hints */}
      <div className="bg-mute border-2 border-ink/20 p-4 space-y-2">
        <p className="font-mono text-[10px] uppercase font-bold text-ink/50 tracking-widest">After install — optional API</p>
        <div className="grid grid-cols-1 gap-2 font-mono text-xs text-ink/80">
          <div className="bg-paper border border-ink/10 px-3 py-2 rounded">
            <span className="text-purple-600 font-bold">LeadMind.identify</span>
            {"({ email: \"user@co.com\", name: \"Jane\" })"}
            <span className="ml-2 text-ink/40">// after login / form submit</span>
          </div>
          <div className="bg-paper border border-ink/10 px-3 py-2 rounded">
            <span className="text-blue-600 font-bold">LeadMind.track</span>
            {"(\"demo_requested\", { plan: \"pro\" })"}
            <span className="ml-2 text-ink/40">// custom events</span>
          </div>
        </div>
      </div>
    </div>
  );
}
