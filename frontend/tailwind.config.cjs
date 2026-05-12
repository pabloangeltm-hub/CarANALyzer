/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
      colors: {
        background:   'hsl(var(--background))',
        foreground:   'hsl(var(--foreground))',
        surface: {
          DEFAULT:  'hsl(var(--surface))',
          elevated: 'hsl(var(--surface-elevated))',
        },
        card: {
          DEFAULT:    'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT:    'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        primary: {
          DEFAULT:    'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT:    'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT:    'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT:    'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        warning: {
          DEFAULT:    'hsl(var(--warning))',
          foreground: 'hsl(var(--warning-foreground))',
        },
        destructive: {
          DEFAULT:    'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        border:   'hsl(var(--border))',
        input:    'hsl(var(--input))',
        ring:     'hsl(var(--ring))',
      },
      keyframes: {
        shimmer: {
          to: { transform: 'translateX(100%)' },
        },
        'page-in': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-down': {
          from: { opacity: '0', transform: 'translateY(-8px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        'collapsible-open': {
          from: { width: '64px' },
          to:   { width: '240px' },
        },
        'collapsible-close': {
          from: { width: '240px' },
          to:   { width: '64px' },
        },
      },
      animation: {
        shimmer:           'shimmer 1.5s infinite',
        'page-in':         'page-in 0.2s ease-out both',
        'fade-in':         'fade-in 0.15s ease-out both',
        'slide-up':        'slide-up 0.2s ease-out both',
        'slide-down':      'slide-down 0.2s ease-out both',
      },
      boxShadow: {
        'glow-primary': '0 0 0 1px hsl(var(--primary) / 0.4), 0 4px 20px hsl(var(--primary) / 0.15)',
        'glow-accent':  '0 0 0 1px hsl(var(--accent) / 0.4), 0 4px 20px hsl(var(--accent) / 0.12)',
        'card':         '0 1px 3px hsl(0 0% 0% / 0.4), 0 1px 2px hsl(0 0% 0% / 0.25)',
        'card-hover':   '0 4px 16px hsl(0 0% 0% / 0.5), 0 1px 4px hsl(0 0% 0% / 0.3)',
        'modal':        '0 20px 60px hsl(0 0% 0% / 0.6), 0 8px 24px hsl(0 0% 0% / 0.4)',
      },
      transitionDuration: {
        '150': '150ms',
        '250': '250ms',
      },
    },
  },
  plugins: [],
}
