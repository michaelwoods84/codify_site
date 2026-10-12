// tailwind.config.js — codifyit.co.uk brand theme.
//
// The site is static HTML with no build step on deploy, so the compiled
// output (assets/brand.css) is committed. After adding or changing any
// Tailwind classes in the HTML, rebuild it with:
//
//   npx tailwindcss@3 -i assets/brand.src.css -o assets/brand.css --minify
//
module.exports = {
  content: {
    files: [
      './index.html',
      './excel-to-python/**/*.html',
      './parents-guide/**/*.html',
      './financial-products/**/*.html',
      './privacy/**/*.html',
      './money-risk-numbers/**/*.html',
      './build-it-together/**/*.html',
      './ai-for-parents/**/*.html',
      './feedback/**/*.html',
    ],
    // Only read class="…" attributes, so ordinary words in the page copy
    // ("fixed", "table", "hidden") don't turn into stray utilities.
    extract: {
      html: (content) =>
        [...content.matchAll(/class="([^"]*)"/g)].flatMap((m) => m[1].split(/\s+/)),
    },
  },
  // Pages keep their own hand-written layout CSS, so skip Tailwind's reset.
  corePlugins: { preflight: false },
  theme: {
    extend: {
      colors: {
        brand: {
          bg: '#f8f9fa',          // Stark, premium light gray
          text: '#0f172a',        // Ink Navy
          muted: '#475569',       // Slate gray for body text
          primary: '#0a369d',     // Trustworthy Royal Blue
          cta: '#ff6b35',         // High-contrast Coral/Amber for action buttons
          border: '#e2e8f0',      // Technical border line gray
          codebg: '#1e293b',      // Dark slate background to make syntax highlighting pop
        }
      },
      borderRadius: {
        // Enforce technical precision over friendly bubbles
        'sm': '2px',
        'md': '4px',
        'lg': '6px',
        'xl': '8px',
      }
    }
  }
}
