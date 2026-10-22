# Dashboard design system

The dashboard (`web/`) is a static, dependency-free front end (ES modules, no build step) served by `src/graphpulse/server.py`. Every number it shows comes from the engine API (`docs/API.md`); nothing is hard-coded (`tests/test_docs_lint.py` forbids percentages and counts in `web/`).

## Direction

* **Landing page:** the *one-motif* direction. The single shape is a route that survives a closed road (a blue route, a closed segment, an ink detour). It appears as the hero, in the loader, and as the brand mark. Sections are separated by tone steps, not rules or cards; no gradients, glass, or icon-topped feature cards. The page shows real interface fragments driven by the live engine, plus a "Run a sample scenario" button that uses the public API.
* **Application:** the *achromatic ledger* style: ink-first chrome, one data hue (blue) on the main data element, flat surfaces, no shadow on anything at rest (floating menus, dialogs and toasts only), a tabular-figure type scale. The skill's default shell is "no sidebar"; the requirement for a collapsible, independently scrolling sidebar led to the **open-plane** shell instead (labelled sidebar on the page ground, neutral grey active pill, settings / theme / account pinned at the bottom).
* **Face:** a blue-grey ground (`#f2f4f7`), taken from the product's world (a ledger / meter ground); true neutral darks for the dark theme (`#0a0a0a`, `#141414`).
* **Type:** the system UI stack (Segoe UI Variable, system-ui). No web font is loaded, so there are no external requests and the page works offline.

The design guidance came from the `design-taste-frontend` skill (installed with `npx skills add Leonxlnx/taste-skill`; its files are git-ignored). Its lint and browser inspector were used as the objective gate: **0 FAIL** on all app screens and on the landing page at 1440, 768 and 390 pixels. Remaining notes: the landing page has no photographs or video (a software product; real interface fragments are used instead), and a tablet-width "ragged row" warning on Network that is a false positive (everything is a single column at that width).

## Tokens (`web/css/tokens.css`)

Light and dark define the same names: `--ground --surface --raised --active --border --rule --control --text --muted --primary --on-primary --data --positive --negative` and the canvas palette `--cv-*` that the graph renderer reads. Density (`compact`) and reduced motion are attributes on `<html>`; the theme is applied before first paint to avoid a flash.

## Structure

| Piece | File | Notes |
|---|---|---|
| Loader, landing, shell | `index.html`, `css/landing.css`, `js/main.js` | loader about one second; landing is instantiated from a `<template>` only on the landing route |
| Sidebar | `css/app.css`, `js/main.js` | collapse button top-left, rail mode with floating tooltips, scrollable nav, bottom group (Settings, theme control, account menu), off-canvas drawer on phones |
| Pages | `js/pages/*.js` | Overview, Network, Routing, Activity, Verification, State inspector, Guide, Glossary, Settings (Appearance, Workspace, Engine, Data) |
| Graph map | `js/graph_view.js` | on-demand canvas, device-pixel-ratio aware, pan / pinch / Ctrl+wheel zoom, keyboard pan and zoom, theme-aware, tour overlay |
| Charts | `js/charts.js` | straight-segment line chart with a real y-scale, thin bar list |
| States | `js/ui.js` | loading skeletons, empty states, inline error notices with Retry, toasts, confirm dialogs, drawer |

## Accessibility and behaviour

Skip link, landmarks, visible focus rings, `aria-current` on navigation, `aria-expanded` on the sidebar toggle, accessible names on every icon button, dialogs with focus return and Escape, `prefers-reduced-motion` and an explicit "Reduce motion" setting, colour pairs chosen for 4.5:1 text contrast, tables that become two-line lists on phones.

## Regression test

`tests/ui/smoke.js` drives the real UI in a browser (forms and inline errors, decisions, tour, verification, inspector, activity drawer, settings including the engine budget, sidebar collapse, account menu, landing scenario) and renders every page in **both themes**, checking for an h1, no sideways scroll and no error notice. See the header of that file for how to run it. `tests/test_web_assets.py` guards the shell contract (every imported module exists, tokens match across themes, no external requests).
