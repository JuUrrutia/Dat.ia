/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
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
    },
  },
  plugins: [],
};
