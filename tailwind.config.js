/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          50: '#f0f6ff',
          100: '#e0edff',
          200: '#bae0ff',
          300: '#7cc7ff',
          400: '#36a9ff',
          500: '#0c8aff',
          600: '#006ee6',
          700: '#0058be',
          800: '#00499b',
          900: '#063d7d',
          950: '#042754',
        },
        dark: {
          base: '#0B0F19',
          surface: '#111827',
          card: '#1F2937',
          border: '#374151',
          hover: '#4B5563',
        },
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'scale(0.98)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        fadeIn: 'fadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        slideUp: 'slideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards',
      },
    },
  },
  plugins: [],
};
