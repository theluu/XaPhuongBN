/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        nen: "var(--nen)",
        "be-mat": "var(--be-mat)",
        "be-mat-2": "var(--be-mat-2)",
        muc: "var(--muc)",
        "muc-nhat": "var(--muc-nhat)",
        vien: "var(--vien)",
        "xac-nhan": "var(--xac-nhan)",
        "tam-thoi": "var(--tam-thoi)",
        son: "var(--son)",
        thieu: "var(--thieu)",
      },
      fontFamily: {
        sans: ['"Be Vietnam Pro"', "system-ui", "sans-serif"],
        so: ['"Barlow Semi Condensed"', '"Be Vietnam Pro"', "sans-serif"],
      },
    },
  },
  plugins: [],
};
