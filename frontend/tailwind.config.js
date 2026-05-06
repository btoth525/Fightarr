/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Radarr-inspired dark palette
        // Sampled from Radarr's actual UI to feel familiar to *arr users
        bg: {
          DEFAULT: "#202020",  // app background
          panel: "#262626",    // cards, sidebar items
          elevated: "#2a2a2a", // hovered/raised
          input: "#1a1a1a",    // form inputs
        },
        border: {
          DEFAULT: "#333333",
          strong: "#444444",
        },
        text: {
          DEFAULT: "#cccccc",
          muted: "#888888",
          dim: "#666666",
          bright: "#ffffff",
        },
        // Status colors — match Radarr conventions
        accent: {
          DEFAULT: "#f5a623",  // Radarr orange — the marker
          hover: "#ffb84d",
        },
        status: {
          monitored: "#5cb85c",   // green
          unmonitored: "#888",
          missing: "#d9534f",     // red
          downloaded: "#5bc0de",  // blue
          announced: "#7e7e7e",   // gray
          upcoming: "#f0ad4e",    // amber
        },
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "sans-serif",
        ],
        mono: ["SF Mono", "Menlo", "Consolas", "monospace"],
      },
      borderRadius: {
        DEFAULT: "3px",  // Radarr uses small radii
        md: "4px",
      },
    },
  },
  plugins: [],
};
