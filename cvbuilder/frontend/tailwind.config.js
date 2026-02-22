/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#f0f4ff",
          100: "#e0eaff",
          500: "#3b6fd4",
          600: "#2e5bbf",
          700: "#2449a8",
          800: "#1a3a8c",
          900: "#0f2766",
        },
      },
    },
  },
  plugins: [],
}

