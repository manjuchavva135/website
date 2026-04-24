import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        tide: "#0ea5a4",
        sand: "#fff7ed"
      }
    }
  },
  plugins: []
};

export default config;
