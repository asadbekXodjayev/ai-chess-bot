/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'chess-dark': '#161512',
        'chess-dark-square': '#769656',
        'chess-light-square': '#eeeed2',
        'chess-accent': '#81b64c',
      },
      fontFamily: {
        'mono': ['ui-monospace', 'SFMono-Regular', 'SF Mono', 'Menlo', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}