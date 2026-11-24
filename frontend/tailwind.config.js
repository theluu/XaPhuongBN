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
        "dieu-huong": "var(--dieu-huong)",
        "dieu-huong-2": "var(--dieu-huong-2)",
        "nhan-dien": "var(--nhan-dien)",
        chinh: "var(--chinh)",
      },
      borderRadius: { the: "var(--bo-goc)" },
      boxShadow: { the: "var(--bong)", nho: "var(--bong-nho)" },
      fontFamily: {
        sans: ['"Be Vietnam Pro"', "Inter", "system-ui", "sans-serif"],
        so: ['"Be Vietnam Pro"', "Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
};
