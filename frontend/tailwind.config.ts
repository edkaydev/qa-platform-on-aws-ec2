import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#2C085E",
          50: "#F5F1FB",
          100: "#E9E0F6",
          200: "#D3C1EC",
          300: "#B79ADE",
          400: "#8F66C8",
          500: "#6E43AD",
          600: "#57348C",
          700: "#452A6F",
          800: "#351F56",
          900: "#2C085E",
          950: "#1B043A",
        },
        ember: {
          DEFAULT: "#FD6500",
          50: "#FFF3EA",
          100: "#FFE2CC",
          200: "#FFC299",
          300: "#FF9C5C",
          400: "#FE7E2B",
          500: "#FD6500",
          600: "#D95200",
          700: "#B04300",
          800: "#8A3500",
          900: "#6B2A00",
        },
        parchment: "#FAF7FF",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      boxShadow: {
        soft: "0 1px 2px rgba(16,24,40,0.04), 0 10px 30px rgba(44,8,94,0.07)",
        lift: "0 2px 6px rgba(16,24,40,0.06), 0 18px 40px rgba(44,8,94,0.10)",
      },
      borderRadius: {
        xl: "0.9rem",
        "2xl": "1.25rem",
        "3xl": "1.75rem",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseDot: {
          "0%, 80%, 100%": { opacity: "0.25", transform: "scale(0.8)" },
          "40%": { opacity: "1", transform: "scale(1)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.35s ease-out both",
        "pulse-dot": "pulseDot 1.2s infinite ease-in-out",
      },
    },
  },
  plugins: [],
};

export default config;
