# ifleon design system

The shared visual language for the ifleonlabs apps (**vigil**, **askdocs**, **roundup**).
Established with `vigil`; the others inherit these tokens and components so the suite feels like one product. No build step — it's plain CSS variables + a small component set you can drop into a self-contained HTML page.

> Generated from the `ui-ux-pro-max` design intelligence: pattern *Real-Time / Operations*, style *Dark Mode (OLED)*, type *Fira Code / Fira Sans*.

## Principles

- **OLED dark, on purpose.** Deep navy base (`#0F172A`), high contrast, minimal glow. Dark is the only theme — designed, not inverted.
- **Data is monospace.** Numbers, URLs, IDs, and the brand use **Fira Code** with tabular figures so columns don't shift. Prose uses **Fira Sans**.
- **Semantic color, never raw hex in components.** Status = green up / red down / amber changed, each paired with an icon + text label (never color alone).
- **Accessible by default.** Visible focus rings, ≥44px touch targets, `aria-live` for async feedback, `prefers-reduced-motion` honored, 4.5:1+ contrast.

## Tokens (CSS variables)

```css
:root {
  /* surfaces */
  --bg:#0F172A; --surface:#131D31; --surface-2:#1A2640; --input:#0B1424;
  /* text */
  --fg:#F8FAFC; --fg-muted:#94A3B8; --fg-subtle:#64748B;
  /* lines */
  --border:#25324B; --border-strong:#3A4A66;
  /* brand / semantic */
  --primary:#1E293B; --accent:#22C55E; --accent-hover:#16A34A;
  --danger:#EF4444; --warning:#FBBF24; --info:#38BDF8; --ring:#38BDF8;
  /* spacing (4/8 scale) */
  --s1:4px; --s2:8px; --s3:12px; --s4:16px; --s5:24px; --s6:32px; --s7:48px;
  --radius:12px; --radius-sm:8px; --radius-pill:999px;
  --mono:"Fira Code",ui-monospace,monospace;
  --sans:"Fira Sans",-apple-system,"Segoe UI",Roboto,sans-serif;
}
```

Fonts:
```html
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

## Components

The canonical implementation lives in [`src/vigil/templates/dashboard.html`](src/vigil/templates/dashboard.html). Reusable pieces:

| Class | What |
|---|---|
| `.nav` / `.brand` | sticky top bar with glowing brand dot |
| `.card` / `.pad` | base surface; `.pad` adds padding |
| `.btn`, `.btn.ghost`, `.btn.danger`, `.btn.sm` | button variants (green primary, outline, danger) |
| `.field` / `.label` / `.input` / `.hint` / `.err-text` | form field with label, helper, inline error |
| `.badge.up/.down/.changed/.none` | status pill — **icon + text**, semantic color |
| `.stat` (with `.v.up`/`.v.down`) | summary stat tile, mono tabular value |
| `.empty` | empty state with icon + guidance |
| `.skeleton` | shimmer loading placeholder |
| `.toast.error/.ok` | transient feedback (auto-dismiss, `aria-live`) |

## UX rules applied (carry into every app)

- Loading → **skeletons**, not spinners, for list loads.
- Every failed request surfaces a **toast** (no silent failures); 401 → auto sign-out.
- Forms: visible labels, required markers, **inline validation** below the field, disabled + busy state on submit.
- Destructive actions **confirm** first; danger styling is visually separated.
- Icons are **inline SVG** (Heroicons-style stroke), never emoji.
- Responsive at 720px (rows collapse, latency tile hides); `100dvh` not `100vh`.

## Reuse

Copy the `:root` block + the component CSS into the target app's page, keep the class names, and swap the domain markup (askdocs: documents + answer; roundup: sources + items + digest). Same tokens → consistent suite.
