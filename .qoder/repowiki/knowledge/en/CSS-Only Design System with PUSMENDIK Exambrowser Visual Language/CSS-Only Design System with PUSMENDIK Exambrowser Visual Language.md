---
kind: frontend_style
name: CSS-Only Design System with PUSMENDIK Exambrowser Visual Language
category: frontend_style
scope:
    - '**'
source_files:
    - web/src/styles.css
    - web/package.json
    - web/src/components/AppShell.tsx
    - web/src/components/DaftarSoal.tsx
    - web/src/components/Modal.tsx
    - exambrowser-ui/README.md
---

## What system/approach is used

The frontend styling is a **single-file, CSS-only design system** built on native CSS custom properties (variables) and BEM-style class names. There is no CSS-in-JS library, no Tailwind, no SCSS preprocessor, and no component library — just one global stylesheet at `web/src/styles.css` (~2900 lines) imported by the React/Vite app. The visual language is explicitly derived from the government **PUSMENDIK CBT "exambrowser-ui"** reference implementation, as declared in the file's opening comment.

## Key files and packages

- `web/src/styles.css` — the single source of truth for all UI styles: tokens, layout, components, responsive breakpoints, and print media rules.
- `web/package.json` — confirms zero styling dependencies beyond React/Vite; no `tailwind`, `sass`, `postcss`, or UI kit.
- `exambrowser-ui/` — contains only screenshots and a README; the actual exambrowser styles live elsewhere and are referenced as the visual source of truth.
- Component `.tsx` files under `web/src/components/` and pages under `web/src/pages/` compose the UI using plain `className` strings that map directly to classes in `styles.css`.

## Architecture and conventions

### Design tokens via `:root` variables
All colors, spacing, and shared values are centralized in `:root`:
- Palette: `--navy-900/700/600`, `--cyan/cyan-dark`, `--red/red-dark`, `--orange/orange-dark`, `--green/green-dark`, `--ink/ink-soft/ink-faint`, `--line`, `--page-bg`.
- Spacing/shapes: `--card-radius: 14px`, `--shadow-card`, `--font-scale` (used to scale question text).
This makes theming and consistency trivial — every component references these tokens rather than hard-coded hex values.

### BEM-like naming without a framework
Classes follow a flat, descriptive convention: `.btn`, `.btn-navy`, `.btn-ghost`, `.package-card`, `.passage-table`, `.review-option`, `.modal-backdrop`. Modifier suffixes (`-navy`, `-ghost`, `-lg`, `-sm`, `-block`) and state classes (`.active`, `.selected`, `.answered`, `.doubt`, `.current`, `.urgent`) are appended directly to base classes. No CSS modules, no scoped styles.

### Desktop-first responsive strategy
Breakpoints are defined inline in `styles.css`:
- `@media (max-width: 1023px)` — tablet padding adjustments.
- `@media (max-width: 767px)` — full mobile reflow: sticky exam header/action bar, collapsible nav menu, stacked footer grid, reduced font sizes, touch-friendly tap targets (≥44px), and iOS-safe-area insets via `env(safe-area-inset-*)`.
- `@media print` — dedicated A4 print stylesheet that hides chrome and renders a clean review document with `break-inside: avoid` and `print-color-adjust: exact`.

### Component patterns in CSS
- **Cards**: `.card` with `border-radius: var(--card-radius)` and `box-shadow: var(--shadow-card)`.
- **Buttons**: Base `.btn` plus color variants (`.btn-red`, `.btn-orange`, `.btn-green`, `.btn-cyan`, `.btn-navy`, `.btn-ghost`) and size modifiers (`.btn-lg`, `.btn-sm`, `.btn-block`).
- **Exam UI**: Dedicated sections for `.exam-head`, `.timer-box` (with urgent pulse animation), `.question-frame`, `.passage`, `.passage-table` (sticky first column, horizontal scroll), `.option`, `.action-bar`, and `.daftar-grid` (question navigator).
- **Feedback/Status**: `.notice.warn|error|ok`, `.toast`, `.pill.active|finished`, tag variants (`.tag.correct|wrong|blank|doubt|revision|reported`).
- **Modals & Popovers**: `.modal-backdrop`, `.modal`, `.info-tooltip-content`, `.package-statistics-popover`.

### Accessibility and UX conventions
- Focus states use explicit `outline` + `outline-offset` on interactive elements (`.app-nav button:focus-visible`, `.scroll-to-top:focus-visible`, textarea focus ring).
- Touch optimization: `touch-action: manipulation`, `-webkit-tap-highlight-color: transparent`, minimum 44px tap targets on mobile.
- Safe area insets (`env(safe-area-inset-top/bottom/left/right)`) for notched devices.
- Semantic HTML paired with styled classes (e.g., `<details>`/`<summary>` for FAQ, `<meter>`-style progress bars via `.meter`).

### Print output
A complete `@media print` block strips navigation, filters, and controls, then reveals `.print-header` and `.print-body` (rendered by ReviewPage) to produce an A4-formatted attempt report with preserved color via `print-color-adjust: exact`.

## Conventions and constraints

- **Single stylesheet rule**: All styles live in `web/src/styles.css`; there are no per-component CSS files, CSS modules, or style imports beyond the root entry.
- **No external styling dependencies**: The dependency list has no CSS frameworks or preprocessors — everything is vanilla CSS.
- **Token-driven colors**: New UI elements should consume `--navy-*`, `--ink-*`, `--red`, `--green`, `--orange`, `--cyan`, `--line`, etc., rather than introducing new hardcoded colors.
- **BEM-style class composition**: Use a base class plus modifier/state suffixes (e.g., `.package-badge.difficulty-easy|medium|hard`, `.daftar-item.answered|doubt|current`).
- **Desktop-first breakpoints**: Add mobile overrides inside existing `@media (max-width: 767px)` blocks rather than creating new breakpoint layers.
- **Exambrowser visual alignment**: The project explicitly inherits its visual language from the PUSMENDIK exambrowser reference; new UI should match that aesthetic (navy gradient masthead, card shadows, rounded corners, muted ink tones).
- **Print-safe design**: Any visible element must consider whether it should be hidden in print (via the existing `@media print` rules) or exposed through `.print-header`/`.print-body`.