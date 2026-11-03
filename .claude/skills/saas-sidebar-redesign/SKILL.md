---
name: saas-sidebar-redesign
description: Redesign a Vue 3 app's shell from a top nav bar into a modern SaaS-style layout with a vertical left sidebar (collapsible on desktop, drawer on mobile), consistent spacing scale, and a polished professional look. Use when the user asks to restyle the layout, move navigation to a sidebar, or make the UI look like a modern SaaS dashboard.
---

# SaaS Sidebar Redesign (Vue 3)

Converts the app shell from a top `<header class="top-nav">` with inline `<router-link>` tabs into:

- a vertical left sidebar with the same navigation items,
- a content area with a consistent spacing scale and page header pattern,
- a responsive behaviour: collapsible on desktop, off-canvas drawer on mobile.

This skill changes shared layout code. Work in small verified steps and keep every route working.

## Project facts to respect

- Entry shell: `client/src/App.vue`. Navigation items are `<router-link>` elements with `:class="{ active: $route.path === '...' }"` and `t('nav.*')` labels. One item (Reports) has a hard-coded label.
- The header also hosts `LanguageSwitcher`, `ProfileMenu`, and `FilterBar` (rendered globally after the header). Keep all three working; move them into the sidebar footer or the content top bar, do not delete them.
- Global design tokens and shared classes live unscoped in `App.vue` `<style>`: `.card`, `.card-header`, `.stat-card`, `.table-container`, `.badge` variants, `.page-header`, `.loading`, `.error`. Do not rename them; other views depend on them.
- Palette: slate neutrals (`#0f172a`, `#64748b`, `#e2e8f0`), primary blue `#2563eb` (hover `#1d4ed8`), status green/blue/yellow/red. No emojis in the UI (see root `CLAUDE.md`).
- i18n keys live in `client/src/locales/en.js` and `ja.js`. Every label must exist in both files.
- Any `.vue` file that is created or significantly changed must be delegated to the **vue-expert** subagent (root `CLAUDE.md`). Do the planning and verification yourself; hand the component edits to vue-expert with a precise brief.

## Workflow

### 1. Inventory the current shell
Read `client/src/App.vue` (template, script, and style), `client/src/main.js` (routes), and `client/src/components/FilterBar.vue`. List:
- every nav item (path, i18n key, label),
- every element in the header and where it is used,
- the global classes that depend on the top-nav layout (`.top-nav`, `.nav-container`, `.nav-tabs`, `.main-content` widths).

Record this list in your reply before changing anything.

### 2. Define design tokens once
Add CSS custom properties on `:root` in `App.vue` and reuse them everywhere. Do not hard-code new spacing values.

```css
:root {
  --sidebar-width: 240px;
  --sidebar-width-collapsed: 72px;
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-border: #e2e8f0;
  --color-text: #0f172a;
  --color-text-muted: #64748b;
  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  --space-1: 0.25rem;  /* 4px */
  --space-2: 0.5rem;   /* 8px */
  --space-3: 0.75rem;  /* 12px */
  --space-4: 1rem;     /* 16px */
  --space-6: 1.5rem;   /* 24px */
  --space-8: 2rem;     /* 32px */
  --radius: 8px;
}
```

Also define dark-mode overrides under `@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])`, and under `:root[data-theme="dark"]`, if the app already supports dark mode. Check first with a grep for `prefers-color-scheme` and `data-theme`. If the app has no dark mode, do not add one.

### 3. Build the sidebar layout
Use a CSS grid shell:

```css
.app-shell {
  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr;
  min-height: 100vh;
  background: var(--color-bg);
}
.app-shell.is-collapsed { grid-template-columns: var(--sidebar-width-collapsed) 1fr; }
```

Sidebar rules:
- `position: sticky; top: 0; height: 100vh;` on desktop.
- Logo and company name at the top (`t('nav.companyName')`, `t('nav.subtitle')`). Show only the logo mark when collapsed.
- Nav items as a vertical list. Each item: icon (inline SVG, no icon font, no emojis), label, and an active state using `$route.path`. Use `aria-current="page"` on the active link.
- Footer: `LanguageSwitcher` and `ProfileMenu`.
- Collapse toggle button with `aria-expanded` and an `aria-label`. Persist the collapsed state only if the app already uses localStorage for UI prefs; otherwise keep it in component state.

Content area:
- A top bar in the main column that holds `FilterBar`. Keep it sticky if the page scrolls.
- `main.main-content` gets `max-width` (for example `1280px`), `margin: 0 auto`, and `padding: var(--space-6)`.

### 4. Responsive behaviour
- Below `768px`: the sidebar is hidden and becomes an off-canvas drawer opened by a menu button in the top bar. The drawer closes on route change, on Escape, and on backdrop click.
- Set `document.body` scroll lock while the drawer is open, and restore it on close.
- The collapse toggle is hidden on mobile.
- Verify there is no horizontal scroll at 390px wide. Tables in `.table-container` keep their own horizontal scroll.

### 5. Consistent page pattern
Standardise `.page-header` (title, subtitle, actions) and `.card` spacing using the tokens. Keep the existing class names so the views keep working. Do not restyle individual views beyond what the shared classes change; this skill is about the shell and shared tokens.

### 6. Accessibility
- Landmark elements: `<aside>` for the sidebar with `aria-label`, `<nav>` inside it, `<main>` for content.
- A skip link to `#main-content` as the first focusable element.
- Visible focus rings (`:focus-visible`) on all links and buttons.
- Colour contrast for muted text stays at least 4.5:1 on the surface.

### 7. Delegate the component edits
Give vue-expert a brief that contains:
- the file list (`App.vue`, plus any new `client/src/components/AppSidebar.vue`),
- the nav item list from step 1,
- the token block from step 2,
- the responsive rules from step 4,
- the requirement to keep every existing route and i18n key working.

Ask it to report back the diff summary and the build result.

### 8. Verify
1. `cd client && npm run build` must pass with no errors.
2. Start the dev server (`npm run dev`, port 3000) if it is not running. Do not change the API server.
3. Browser check, only if Playwright MCP tools are available in the session. If they are not, say so and do not claim the layout was verified visually.
   - Each nav item navigates and shows the active state.
   - Collapse toggles the width and the labels hide.
   - At 390px the drawer opens, closes on route change and Escape, and the page does not scroll horizontally.
   - `LanguageSwitcher` changes labels in both locales.
   - `FilterBar` still filters the Orders page.
4. Run `/review` or the `code-reviewer` subagent on the changed files before reporting done.

## Report format

Finish with:
- files changed,
- the nav items and where they now live,
- build result,
- what was verified in a browser and what was not,
- any view that looked wrong at 390px or 1280px.

## Do not

- Rename or remove shared global classes used by other views.
- Remove `LanguageSwitcher`, `ProfileMenu`, or `FilterBar`.
- Add a new UI library, icon font, or dependency without asking.
- Add emojis or gradients that break the slate and blue palette.
- Commit or push unless the user asks.
