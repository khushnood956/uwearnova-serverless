import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        obsidian: {
          DEFAULT: "#14120F",
          50: "#f6f5f4",
          100: "#e8e6e3",
          200: "#d3cfca",
          300: "#b5afa7",
          400: "#91897f",
          500: "#746c62",
          600: "#5b544b",
          700: "#474139",
          800: "#2a2723",
          900: "#1a1815",
          950: "#14120F",
        },
        ivory: {
          DEFAULT: "#FAF7F2",
          light: "#FFFDF9",
          dark: "#EFE8DC",
          sand: "#EFE8DC",
        },
        champagne: {
          DEFAULT: "#B08D57",
          light: "#D4B98A",
          dark: "#8C6E3F",
        },
        sale: {
          DEFAULT: "#B5472F",
          terracotta: "#B5472F",
        },
        success: {
          DEFAULT: "#3F6B4F",
        },
        danger: {
          DEFAULT: "#A33A2C",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["var(--font-serif)", "Cormorant Garamond", "Playfair Display", "ui-serif", "serif"],
      },
      fontSize: {
        display: ["clamp(2.5rem, 6vw, 5rem)", { lineHeight: "1.08", letterSpacing: "-0.025em" }],
        h2: ["clamp(1.875rem, 3.5vw, 3rem)", { lineHeight: "1.15", letterSpacing: "-0.02em" }],
        h3: ["clamp(1.25rem, 2vw, 1.75rem)", { lineHeight: "1.25", letterSpacing: "-0.015em" }],
        eyebrow: ["0.75rem", { lineHeight: "1rem", letterSpacing: "0.18em" }],
      },
      borderRadius: {
        card: "12px",
        image: "4px",
        button: "9999px",
        section: "0px",
      },
      boxShadow: {
        subtle: "0 1px 3px rgba(20, 18, 15, 0.04), 0 4px 12px rgba(20, 18, 15, 0.02)",
        card: "0 2px 8px rgba(20, 18, 15, 0.04), 0 12px 28px -4px rgba(20, 18, 15, 0.05)",
        "card-hover": "0 8px 24px -4px rgba(20, 18, 15, 0.08), 0 20px 40px -8px rgba(20, 18, 15, 0.06)",
        lift: "0 16px 36px -6px rgba(20, 18, 15, 0.12)",
      },
      transitionDuration: {
        fast: "150ms",
        base: "280ms",
        slow: "600ms",
      },
      transitionTimingFunction: {
        out: "cubic-bezier(0.22, 1, 0.36, 1)",
        "in-out": "cubic-bezier(0.65, 0, 0.35, 1)",
        smooth: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
