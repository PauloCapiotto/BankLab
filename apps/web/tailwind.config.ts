import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#fff8f1",
        surface: "#ffffff",
        "surface-warm": "#fff4ec",
        primary: { DEFAULT: "#ef6a3a", dark: "#b94f2d" },
        copper: "#74311f",
        brown: "#4a2117",
        success: { DEFAULT: "#237a4b", soft: "#dcfce7" },
        danger: { DEFAULT: "#b94122", soft: "#ffdfd2" },
        ink: "#22130f",
        muted: "#7f6a60",
        "border-warm": "#f1d8c8",
      },
      fontFamily: {
        display: ["var(--font-bricolage)", "sans-serif"],
        sans: ["var(--font-jakarta)", "sans-serif"],
      },
      borderRadius: {
        card: "1.25rem",
      },
    },
  },
  plugins: [],
};

export default config;
