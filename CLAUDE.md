# OFL (Overseas FilipinoLoan) — project notes for Claude

Read this first. It records how the owner wants this project handled.

## Working with the owner
- The owner writes short English. Answer in simple, plain English; show results with
  screenshots (side by side with their mockup when there is one).
- The owner uses a **Mac** (Terminal, not PowerShell). They preview locally with:
  `cd ~/mana_system2 && git pull && venv/bin/python manage.py runserver` → http://127.0.0.1:8000
  (needs a `.env` file containing `DEBUG=True`, otherwise the site redirects to https).
- **Never deploy.** `main` is the live site. Work on the feature branch, commit and push
  there; the owner merges when they are ready. Never push to `main`.
- For each page the owner sends an HTML mockup (Tailwind CDN + Font Awesome). Rebuild it
  faithfully in the Django template, **keep every existing feature and data binding**, and
  fix the mockup's own glitches (say which ones you fixed).

## Client UI design system (login, register, dashboard, …)
- Forest green. Header gradient `#133224 → #1B4332 → #0F281C` (dashboard: `#0B1C14 → #133224`).
  Primary `#1B4332` (hover `#122e22`), sage `#E8F3ED`, accent orange `#F97316`,
  text `#374151` / headings `#111827`, muted `#9ca3af`, lines `#e5e7eb` / `#f3f4f6`,
  page background `#f9fafb` / `#f3f4f6`.
- Fonts: Inter on login/register; the dashboard mockup uses Plus Jakarta Sans.
- Phone-first app shell (max-width 400–420px). On desktop show a centred rounded card —
  **no** fake phone bezel or iPhone home bar from the mockups.
- White cards that overlap the dark header are **solid white, not glass** (glass over the dark
  header turns grey/muddy).
- Icons: Font Awesome Free 6.4.0 **inlined as SVG** (keep the attribution comment). Insert
  paths programmatically from `@fortawesome/fontawesome-free/svgs/...` — never hand-type them.
  No icon fonts and no Tailwind CDN in production; write plain CSS in the template.
- Same look in light and dark theme: base.html forces dark inputs in dark mode, so override
  with an `#id`-scoped selector.
- Footer: "Overseas FilipinoLoan • v2.2.1 / © 2026 All rights reserved".
- Money inputs: `inputmode="decimal"`, no `maxlength` (it cuts pasted "PHP 1,500,000" before
  cleaning); clean to digits + one point + 2 decimals, no leading zeros, 9 digits max.
- Client drafts kept in localStorage must carry the user id (`__uid`) — phones are shared.

## Client guides / onboarding (see templates/register.html)
- Glass guide card (`rgba(17,42,31,.85)` + `backdrop-filter: blur(24px)`), step label + dots,
  "Skip guide" / "Next".
- The guide **must never drift away from its target**: put it inside the content and move it
  with `transform` relative to its container. Never `position: fixed` with coordinates
  measured once (they go wrong mid-scroll, when the keyboard opens, or inside a transformed
  ancestor).
- Glide between targets; stay inside the card/frame (flip above the target near the bottom).
- Keep the phone keyboard open between fields (`mousedown` preventDefault on guide buttons,
  `focus({preventScroll:true})`), then scroll just enough using `visualViewport`.
- Show validation errors inside the guide; clear them as the user types.
- No `filter`/`opacity` on ancestors of a `backdrop-filter` element (it switches the blur off).
- After a tap on a guide button, swallow clicks on the content under it for ~450 ms (capture
  listener on the guide's container): a double tap must not tick a tile or pick a term.
- Guides with no mockup: the first-loan chain is dashboard → quick loan (`ofl_onboard='ql'` or
  `?ofl=1`) → loan apply (always, when the form is open) → payment method (`ofl_onboard='pm'`,
  then `'done'`). Start at the first unfinished step; remember Skip; a field to fix is scrolled
  into view (keyboard), not the guide.

## Motion and smoothness (the owner cares about this a lot)
- Everything must feel smooth: no glitches, no lag, no stuck pages, nothing running off-screen.
- Page-to-page transitions live in base.html (native cross-document View Transitions with a
  slide in / slide out; older browsers get a short fade). No JavaScript click interception and
  no artificial navigation delay.
- **Never leave a `transform` on `#pageRoot`** — it makes `position: fixed` children scroll
  away with the page.
- Animate only `transform` and `opacity`. Never animate `box-shadow`, `width`, `left/top`,
  `background-position` or `filter` in endless loops — put a glow on its own layer and fade its
  opacity instead.
- Closed overlays: `visibility: hidden` as well as `opacity: 0`, so their blur costs nothing.
- No full-screen `backdrop-filter` on overlays (menus, sheets, modals): it drops frames while
  they fade. Use a plain dim (`rgba(11,28,20,.5)`); keep blur for small elements (nav, guide).
- Respect `prefers-reduced-motion`.
  (also shakes, sheet slides and smooth scrolling: `behavior: SMOOTH` that is `'auto'` there).
- Do not show a "minimum amount" error from the first digit: it grows the card and makes the
  guide jump while typing. Flag the minimum on blur / Next / submit; the maximum can stay live.
- Bottom sheets: build the content first and slide up on the next frame; ignore taps for
  ~400 ms after opening (the second tap of a double tap would hit a list item).

## How to check work before pushing
- After building a page, run fresh-eyes reviewers (old-vs-new parity + adversarial runtime QA)
  and fix what they confirm; owner pages so far: login, register, dashboard, quick loan, loan
  apply, payment method; Claude-led redesigns since: wallet, profile, notifications, transactions,
  payment schedule, credit score, change password, contact us, explore (sources with `[[s:icon]]` placeholders live in the scratchpad).
- Local preview in the cloud container: run Django with DEBUG settings on 127.0.0.1 only.
  `cdn.tailwindcss.com` is blocked there: to render a mockup, build its CSS with
  `tailwindcss@3` from npm and use `@fortawesome/fontawesome-free@6.4.0`.
- Playwright (preinstalled Chromium, never `playwright install`) at 320×568, 375×667,
  390×844 and desktop; light and dark theme; a new user and a user with data.
- Smoothness: 4× CPU throttle — idle main-thread %, dropped frames (>34 ms) while scrolling
  and animating, no paint-heavy endless animations.
- Compare against the mockup side by side and send the owner screenshots.

## Known open items (tell the owner, do not fix silently)
- The GitHub repo is public and contains secrets: Render DB URL in
  `accounts/migrations/0048_restore_render_data.py`, admin passwords in
  `accounts/management/commands/bootstrap_admin.py` (runs on every deploy), production data
  in `data_backup.json`, uploads in `id_cards/`.
- `/control/login/` returns 500: `control_login.html` does not exist.
- Home page (choose.html) headline shine animation costs CPU; owner has not decided whether
  to stop it after a few runs.
- base.html's realtime poller is not wired into the dashboard on purpose: `/api/realtime/`
  always returns `notif_count: 0`, sends the raw balance (no commas) and an empty status label,
  and colours statuses differently — wiring it in would make the bell dot vanish and the badge
  and balance flicker. Fix the API first if live updates are wanted.
- Loan apply input filters (kept from the old page, owner to decide): ID number is digits only
  (passport numbers lose their letters); names drop ñ, hyphens, periods; addresses drop commas.
- What `identity_name` should hold (ID type such as "Passport", or the name on the ID) is not
  defined; the client page keeps the old label "Identity name".
- register.html's validation sheet still has a full-screen backdrop blur (built before that rule).
- Change password does not ask for the current password, and every password is also stored in
  plain text (`User.plain_password`, shown to staff). Owner to decide.
- Count text length with `Array.from(v).length` in JS (Python counts code points) and normalise
  textarea CRLF to `\n` on the server, or the page and the server disagree on limits.
