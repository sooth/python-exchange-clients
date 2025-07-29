/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'media', // Always use dark mode
  theme: {
    extend: {
      colors: {
        // FTX exact color scheme from screenshot
        background: {
          primary: '#000000', // Pure black background
          secondary: '#141823', // Dark blue-gray for panels
          tertiary: '#1b2332', // Lighter panels/cards
          hover: '#262d3d', // Hover states
          input: '#202533', // Input backgrounds
        },
        text: {
          primary: '#ffffff', // Primary text
          secondary: '#848e9c', // Secondary gray text
          muted: '#5a6374', // Muted text
          label: '#848e9c', // Form labels
        },
        accent: {
          primary: '#5fcade', // FTX signature light blue
          hover: '#4db8cf', // Darker blue for hover
        },
        success: '#0ecb81', // Bright green
        error: '#f6465d', // Bright red
        warning: '#ffb800', // Orange warning
        border: {
          primary: '#2a3343', // Main borders
          secondary: '#1f2531', // Subtle borders
          input: '#373f51', // Input borders
        },
      },
      spacing: {
        '0.5': '0.125rem',
        '1.5': '0.375rem',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      fontSize: {
        '2xs': '0.625rem',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [],
}