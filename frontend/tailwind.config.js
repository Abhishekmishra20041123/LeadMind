/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    darkMode: "class",
    theme: {
        extend: {
            colors: {
                "background": "var(--background)",
                "foreground": "var(--foreground)",
                "primary": "#f93706", // International Orange
                "ink": "#0A0A0A", // Primary Black
                "paper": "#FFFFFF", // Paper White
                "mute": "#F0F0F0", // Concrete Grey
                "data-green": "#00CC66", // Data Green
                "background-light": "#ffffff",
                "background-dark": "#0a0a0a",
                "neon-blue": "#00F3FF",
                "soft-indigo": "#6366F1",
            },
            fontFamily: {
                "display": ["Space Grotesk", "sans-serif"],
                "body": ["Inter Tight", "sans-serif"],
                "sans": ["Inter Tight", "sans-serif"],
                "mono": ["JetBrains Mono", "monospace"],
            },
            borderRadius: {
                "DEFAULT": "0px", // Strict grid, no rounded corners as per design direction
                "sm": "0px",
                "md": "0px",
                "lg": "0px",
                "xl": "0px",
            },
            borderWidth: {
                DEFAULT: '1px',
                '3': '3px',
            },
            boxShadow: {
                'premium': '8px 8px 0px 0px rgba(10, 10, 10, 1)',
                'premium-hover': '12px 12px 0px 0px rgba(10, 10, 10, 0.8)',
                'glow-primary': '0 0 15px rgba(249, 55, 6, 0.3)',
                'glow-blue': '0 0 15px rgba(0, 243, 255, 0.3)',
            }
        },
    },
    plugins: [],
};
