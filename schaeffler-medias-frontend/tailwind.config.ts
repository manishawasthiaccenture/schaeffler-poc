import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        schaeffler: {
          green: "#00893D",
          greenDark: "#00672E",
          greenLight: "#E6F3EC",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
