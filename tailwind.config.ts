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
        primary: {
          DEFAULT: "#4F46E5",
          dark: "#4338CA",
          light: "#6366F1",
        },
        success: "#10B981",
        warning: "#F59E0B",
        danger: "#EF4444",
        info: "#3B82F6",
        indigo: {
          50: "#EEF2FF",
          600: "#5B4FE5",
          700: "#4A3FCC",
        },
        teal: {
          50: "#F0FDFA",
          300: "#5EEAD4",
          600: "#0D9488",
          700: "#0F766E",
        },
        orange: {
          50: "#FFF7ED",
          300: "#FDBA74",
          600: "#EA580C",
          700: "#C2410C",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      animation: {
        bounce: "bounce 1s infinite",
      },
    },
  },
  plugins: [],
};

export default config;
