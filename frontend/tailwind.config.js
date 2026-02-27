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
            }
        },
    },
    plugins: [],
};
