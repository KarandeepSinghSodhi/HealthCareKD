/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        accent: {
          DEFAULT: 'var(--accent-500)',
          light: 'var(--accent-400)',
          dark: 'var(--accent-600)',
        },
      },
      backgroundColor: {
        'white/8': 'rgba(255,255,255,0.08)',
        'white/6': 'rgba(255,255,255,0.06)',
        'white/5': 'rgba(255,255,255,0.05)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
      },
    },
  },
  plugins: [],
}
