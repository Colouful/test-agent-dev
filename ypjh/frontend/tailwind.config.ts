import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#e3f2fd', 100: '#bbdefb', 200: '#90caf9',
          300: '#64b5f6', 400: '#42a5f5', 500: '#1976d2',
          600: '#1565c0', 700: '#0d47a1', 800: '#0a3880',
          900: '#071e56',
        },
      },
      fontFamily: {
        serif: ['"Noto Serif SC"', '"Source Han Serif"', 'SimSun', 'serif'],
        sans:  ['"Noto Sans SC"', '"PingFang SC"', 'sans-serif'],
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
} satisfies Config
