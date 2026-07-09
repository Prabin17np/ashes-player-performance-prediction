import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          50: "#EEF2F8",
          100: "#DAE3F0",
          200: "#AFC1DD",
          300: "#7C97C1",
          400: "#3F5D8E",
          500: "#16335C", // primary navy
          600: "#102A4E",
          700: "#0B1F3A", // ink navy
          800: "#08162A",
          900: "#050E1B",
        },
        gold: {
          50: "#FBF5E7",
          100: "#F4E5BE",
          200: "#EAD190",
          300: "#DDBB68",
          400: "#D2A94B",
          500: "#C79A3C", // primary gold (Ashes urn)
          600: "#A87E2C",
          700: "#846222",
        },
        paper: "#F1F3F6", // light gray
        slate: {
          450: "#5B6472",
        },
      },
      fontFamily: {
        display: ["Fraunces", "ui-serif", "Georgia", "serif"],
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(11,31,58,0.04), 0 8px 24px -8px rgba(11,31,58,0.10)",
        "card-hover": "0 2px 4px rgba(11,31,58,0.06), 0 16px 32px -12px rgba(11,31,58,0.16)",
      },
      borderRadius: {
        xl2: "1.25rem",
      },
      backgroundImage: {
        "seam": "repeating-linear-gradient(90deg, transparent 0, transparent 6px, rgba(199,154,60,0.55) 6px, rgba(199,154,60,0.55) 8px)",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.4s ease-out both",
      },
    },
  },
  plugins: [],
} satisfies Config;
