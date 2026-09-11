/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0b0f19",
        surface: "#111827",
        surfaceBorder: "#1f2937",
        primary: {
          DEFAULT: "#3b82f6",
          hover: "#2563eb",
          light: "#60a5fa",
        },
        accent: {
          DEFAULT: "#8b5cf6",
          emerald: "#10b981",
          amber: "#f59e0b",
          rose: "#f43f5e",
        }
      }
    },
  },
  plugins: [],
}
