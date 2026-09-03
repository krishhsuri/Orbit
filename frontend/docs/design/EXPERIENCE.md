status: in-progress
created: 2026-06-13
owner: user
designer: OpenCode

# Orbit — EXPERIENCE.md

> How Orbit works. For *how it looks*, see `DESIGN.md`.

---

## Foundation

### Form Factor

Orbit is a **web-first, desktop-primary** application. The primary use case is a user sitting at a desk, managing applications in a focused session. Mobile support is responsive and functional, but the experience is optimized for `1024px` and above.

- **Target viewport:** 1280px+ (desktop)
- **Minimum viable viewport:** 768px (tablet)
- **Mobile:** Single-column stack, hamburger navigation, touch-optimized tap targets (44px minimum).

### UI System

- **CSS Architecture:** CSS Modules (`.module.css`) with a global design token system (`globals.css`).
- **React framework:** Next.js 14+ App Router.
- **Animation library:** Framer Motion for orchestrated transitions; CSS transitions for simple hover states.
- **Icons:** `lucide-react` (monoline, consistent stroke width).

---

## Information Architecture

### Global Navigation

The application has a **persistent left sidebar** on desktop. On mobile, it collapses into a hamburger menu.

```
[ Sidebar ]
├── Quick Actions (Search / New)
├── Main Nav
│   ├── Dashboard          [ / ]
│   ├── Applications       [ /applications ]
│   ├── Kanban             [ /kanban ]
│   ├── Emails             [ /emails ]
│   ├── Leads              [ /leads ]
│   ├── AI Agents          [ /agents ]
│   └── Analytics          [ /analytics ]
└── Footer
    ├── Settings           [ /settings ]
    └── User / Logout
```

### Page Structure (Desktop)

Every authenticated page follows a consistent layout:

```
[ Sidebar | Fixed, 220px ]
[ Main Content Area ]
├── Header (Title, Subtitle, Actions, Search)
├── Scrollable Content
│   ├── Panels / Cards
│   ├── Tables / Lists
│   └── Modals (overlays)
```

### Surface Inventory

| Surface | Description | Responsive Behavior |
|---------|-------------|---------------------|
| `Sidebar` | Persistent nav, collapsible to 52px. | Hidden, toggled via hamburger on < 768px. |
| `Header` | Page title, global search, primary action. | Wraps, search moves to top. |
| `Card` | Primary content container. | Full width, stacked. |
| `Panel` | Grouped content within a card. | Full width. |
| `Modal` | Overlays for creation, editing, confirmation. | Full screen on mobile, centered on desktop. |
| `Toast` | Ephemeral feedback. | Bottom center. |

---

## Voice and Tone

### Language

- **Command-oriented, not salesy.** The user is here to *do*, not to be sold to.
- **Plain, active verbs.** "Save changes", "Track application", not "Submit your application details for processing".
- **Conversational register.** Sentence case. No exclamation marks unless celebrating a genuine win (e.g., "Offer received!").
- **Empathy in empty states.** "No applications yet. Start your journey by tracking your first one." Not just "No data."

### Examples

| Context | Do | Don't |
|---------|-----|-------|
| Button | "Add new application" | "Submit Application Form" |
| Empty state | "You have no upcoming deadlines. You're all caught up!" | "0 items found." |
| Error | "Couldn't save. Please check your connection and try again." | "Error 500." |

---

## Component Patterns

### Theme Toggle

Located in the **Header** or **Sidebar Footer**.

- **Icon:** Sun (light) / Moon (dark).
- **Interaction:** Single click toggles between explicit `light` and `dark`.
- **Default:** Follows `prefers-color-scheme`.
- **Persistence:** Saves to `localStorage`.
- **Flash prevention:** Inline script in `<head>` sets `data-theme` before paint.

### Stat Cards

- **Purpose:** Provide at-a-glance dashboard metrics.
- **Layout:** Label (top left), Numeric Value (bottom left), Contextual Badge (top right), Mini-chart (bottom).
- **Behavior:** Clicking a stat card should ideally filter the main list to show items contributing to that number.
- **Animation:** Subtle `scale(1.01)` and shadow increase on hover. Numeric values animate count-up on mount.

### Activity Feed

- **Purpose:** Show recent actions across the platform.
- **Layout:** Icon (left) + Content (center) + Time (right).
- **Behavior:** Clicking an item navigates to the relevant application detail page.
- **Truncation:** Company and Role names truncate with ellipsis.

### Application List / Table

- **Purpose:** Primary data view for all tracked jobs.
- **Columns:** Company | Role | Status | Date | Actions (More)
- **Interactivity:**
  - Click row to navigate to detail.
  - Hover row highlights.
  - Status badge is a dropdown to quick-change status.
  - "More" menu for edit/delete.

### Kanban Board

- **Purpose:** Visual pipeline stage management.
- **Columns:** Applied → Screening → OA → Interview → Offer → Accepted.
- **Drag & Drop:** Uses `@dnd-kit`. Cards lift with shadow on drag. Drop zones highlight.

---

## State Patterns

### Loading

- **Skeletons > Spinners.** Use the `Skeleton` component to mimic the shape of the content.
- **Error:** Full-page error boundary for catastrophic failures. Inline retry for component-level errors.

### Empty

- Every list, table, or charted area must have an intentional empty state.
- Include a primary CTA to create/populate the missing data.

### Success / Feedback

- Use `sonner` toasts for mutations (save, delete, status update).
- Toasts should auto-dismiss in 3 seconds.
- Use inline indicators (checkmark, color change) for optimistic updates.

---

## Interaction Primitives

### Hover

- **Cards:** `translateY(-2px)`, shadow increases to `var(--shadow-lg)`.
- **Buttons:** Background darkens (or lightens in dark mode). If icon-only, background fills.
- **Links:** Underline appears (native behavior preferred).

### Focus

- **Keyboard focus:** `box-shadow: 0 0 0 2px var(--bg-base), 0 0 0 4px var(--accent-primary);`
- **Visible for all interactive elements.** No `outline: none` without a replacement.

### Reduced Motion

- Wrap all motion in `motion-safe` media query.
- If `prefers-reduced-motion: reduce` is active, all transitions should be instant (`transition: none`).

---

## Accessibility Floor

- **Contrast ratio:** Minimum 4.5:1 for all text.
- **Touch targets:** 44px x 44px minimum.
- **Keyboard navigation:** All interactive elements reachable via Tab. Focus order is logical.
- **Screen readers:** Semantic HTML (`<nav>`, `<main>`, `<article>`). `aria-label` for icon-only buttons.
- **Color independence:** Status is not conveyed by color alone (badge text or icons must accompany color).

---

## Key Flows

### Flow: First-Time User

**Protagonist:** Alex, a new grad starting their job search.

1. Alex lands on the **Login** page. Clean, centered form. Authenticates via Google.
2. Redirected to **Dashboard**. Sees an empty state with a clear CTA: "Track your first application."
3. Alex clicks the CTA. **Add Application Modal** opens.
4. Fills out Company, Role, Status (Applied). Saves.
5. Dashboard updates. Alex sees their first **Stat Card** (Total: 1) and sees the new entry in the **Recent Activity** feed.
6. Alex explores the **Applications** page. Sees their entry in a clean table.
7. Alex switches to the **Kanban** view. Sees their application in the "Applied" column.
8. Alex feels organized and in control. Closes the app, confident they can track their progress.

### Flow: Power User Review

**Protagonist:** Priya, actively interviewing at 12 companies.

1. Opens Orbit during a coffee break. Dashboard loads instantly with cached data.
2. Scans the **Upcoming Deadlines** panel. Sees an interview in 2 days.
3. Drills down into `/applications/:id`. Reviews notes, past communications.
4. Returns to dashboard. Changes the status of one application from "Interview" to "Offer" using the quick status change in the table.
5. Dashboard updates optimistically. **Response Rate** stat card updates. Toast confirms: "Status updated to Offer."
6. Checks **Analytics** for trends in her response rate over the past month.
7. Feels calm and prepared. Closes the app.

---

## Theme Switching

### Behavior

1. **`localStorage` Key:** `orbit-theme`.
2. **Values:** `light`, `dark`.
3. **Script placement:** Inline `<script>` in `<head>` of `layout.tsx`.
   - Reads `localStorage.getItem('orbit-theme')`.
   - If unset, reads `window.matchMedia('(prefers-color-scheme: dark)').matches`.
   - Sets `document.documentElement.setAttribute('data-theme', theme)`.
4. **React interaction:** A `ThemeToggle` component uses a Zustand store.
   - Store syncs with `localStorage`.
   - Toggling triggers a store update, which calls `document.documentElement.setAttribute('data-theme', ...)`.
   - `globals.css` has `[data-theme="dark"]` rules that override the default (light) variables.

### Edge Cases

- **SSR:** The inline script runs before React hydration to prevent a flash of the wrong theme. The server renders a `data-theme="light"` (or system default) as a safe fallback.
- **Storage errors:** If `localStorage` is unavailable (e.g., private mode), fall back to `prefers-color-scheme`.

---
