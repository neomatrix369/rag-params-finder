/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        frame: 'var(--color-frame)',
        'frame-muted': 'var(--color-frame-muted)',
        canvas: 'var(--color-canvas)',
        paper: 'var(--color-paper)',
        ink: 'var(--color-ink)',
        muted: 'var(--color-muted)',
        line: 'var(--color-line)',
        accent: {
          DEFAULT: 'var(--color-accent)',
          strong: 'var(--color-accent-strong)',
          soft: 'var(--color-accent-soft)',
        },
        cobalt: 'var(--color-cobalt)',
      },
      fontFamily: {
        sans: ['var(--font-body)'],
        display: ['var(--font-display)'],
        mono: ['var(--font-mono)'],
      },
      borderRadius: {
        panel: '1rem',
      },
      boxShadow: {
        panel: '0 16px 40px -28px rgb(11 31 42 / 0.55)',
        lift: '0 22px 50px -28px rgb(11 31 42 / 0.7)',
      },
    },
  },
  plugins: [],
}
