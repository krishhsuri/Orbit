status: in-progress
created: 2026-06-13
owner: user
designer: OpenCode

---

# Orbit — DESIGN.md

> Visual identity for Orbit: the job application tracker that makes you feel in control.
> This file owns *how it looks*. For *how it works*, see `EXPERIENCE.md`.

---

## Brand & Style

Orbit is a job application tracker that transforms the chaotic career search into a calm, actionable journey. The brand voice is **confident, precise, and quietly warm** — a professional command center that still feels personal.

Key personality: **"Command Journal"** — the precision of a Swiss-made tool with the warmth of a well-loved notebook. Every detail is intentional. Nothing is wasted. The user feels in control from the first second.

---

## Colors

We support **light** and **dark** modes with the same accent hierarchy. Either user or system can control the theme.

### Light Mode

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-base` | `#F7F5F0` | Page background. Warm off-white, reduces screen fatigue. |
| `--bg-surface` | `#FFFFFF` | Cards, panels, elevated surfaces. |
| `--bg-elevated` | `#FAF9F6` | Hover states, subtle differentiation. |
| `--bg-hover` | `rgba(0,0,0,0.03)` | Interactive element hover. |
| `--bg-active` | `rgba(0,0,0,0.05)` | Press / active state. |
| `--border-subtle` | `rgba(0,0,0,0.06)` | Dividers, hairlines. |
| `--border-default` | `rgba(0,0,0,0.09)` | Card borders, input borders. |
| `--text-primary` | `#1B1A19` | Primary text, headings. |
| `--text-secondary` | `#6B665F` | Body text, descriptions. |
| `--text-muted` | `#9C98A0` | Placeholders, disabled text. |
| `--text-disabled` | `#B5B0B8` | Very faint labels. |

### Dark Mode

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-base` | `#161618` | Page background. Deep, not pure black. |
| `--bg-surface` | `#1E1E22` | Cards, panels. |
| `--bg-elevated` | `#252528` | Hover states. |
| `--bg-hover` | `rgba(255,255,255,0.04)` | Interactive hover. |
| `--bg-active` | `rgba(255,255,255,0.08)` | Active state. |
| `--border-subtle` | `rgba(255,255,255,0.05)` | Dividers. |
| `--border-default` | `rgba(255,255,255,0.08)` | Card / input borders. |
| `--text-primary` | `#E8E6E1` | Primary text. |
| `--text-secondary` | `#A3A09B` | Body text. |
| `--text-muted` | `#6B6966` | Placeholders, faint labels. |
| `--text-disabled` | `#4A4845` | Very faint. |

### Accent Palette (Shared)

| Token | Hex | Usage |
|-------|-----|-------|
| `--accent-primary` | `#0A5F52` | Primary action, status "applied", accepted. Calm, in-control. |
| `--accent-hover` | `#0D7A6B` | Hover state for primary. |
| `--accent-muted` | `#E0F2EE` | Light background tint for primary. |
| `--accent-primary-dark` | `#2DD4BF` | Used in dark mode for legibility where needed. |
| `--accent-secondary` | `#D4860F` | Energy, momentum, urgency. Offers, deadlines. |
| `--accent-secondary-hover` | `#F5A623` | Hover state. |
| `--accent-secondary-muted` | `#FDF2E0` | Light background tint for secondary. |
| `--status-success` | `#0A5F52` | Positive outcome. |
| `--status-warning` | `#D4860F` | Attention needed. |
| `--status-error` | `#C0392B` | Rejections, critical errors. |
| `--status-info` | `#3B82F6` | General information. |

---

## Typography

### Font Stack

| Role | Font | Weight | Usage |
|------|------|--------|-------|
| Display | `Playfair Display` or `Crimson Pro` | 400 / 500 | Page titles, hero headings. |
| Body | `Inter` | 400 / 500 / 600 | UI text, body copy, buttons. |
| Mono | `JetBrains Mono` | 400 / 500 | Labels, data, dates, shortcuts. |

### Scale

| Size | Value | Line Height | Letter Spacing | Usage |
|------|-------|-------------|----------------|-------|
| `--text-xs` | 11px | 1.4 | 0.02em | Labels, badges, meta. |
| `--text-sm` | 13px | 1.5 | 0em | Body small, secondary text. |
| `--text-base` | 14px | 1.6 | 0em | Primary body. |
| `--text-lg` | 16px | 1.5 | -0.01em | Emphasized body. |
| `--text-xl` | 18px | 1.4 | -0.02em | Sub-headings. |
| `--text-2xl` | 22px | 1.3 | -0.02em | Section headings. |
| `--text-3xl` | 28px | 1.2 |开明：| Page titles (Display). |
| `--text-4xl` | 36px | 1.1 | -0.03em | Hero / Dashboard numbers. |

---

## Layout & Spacing

### Base Grid

Base unit: **4px**

| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | 4px | Tight padding, small gaps. |
| `--space-2` | 8px | Icon padding, inline spacing. |
| `--space-3` | 12px | Component internal padding. |
| `--space-4` | 16px | Card internal padding, section gutters. |
| `--space-5` | 20px | Horizontal padding in panels. |
| `--space-6` | 24px | Large internal padding, section separation. |
| `--space-8` | 32px | Page padding, major separation. |
| `--space-10` | 40px | Section breaks. |
| `--space-12` | 48px | Hero spacing. |

### Border Radii

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 4px | Small buttons, tags. |
| `--radius-md` | 6px | Standard buttons, inputs. |
| `--radius-lg` | 12px | Cards, panels. |
| `--radius-xl` | 16px | Modals, large containers. |
| `--radius-full` | 9999px | Pills, avatars. |

---

## Elevation & Depth

### Shadows

| Token | Light Mode | Dark Mode |
|-------|------------|-----------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.04)` | `0 1px 2px rgba(0,0,0,0.2)` |
| `--shadow-md` | `0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06)` | `0 2px 8px rgba(0,0,0,0.3)` |
| `--shadow-lg` | `0 4px 12px rgba(0,0,0,0.05)` | `0 4px 16px rgba(0,0,0,0.32)` |
| `--shadow-xl` | `0 8px 24px rgba(0,0,0,0.08)` | `0 8px 32px rgba(0,0,0,0.4)` |

---

## Shapes

All shapes use **CSS border-radius** (no border-images). Interactable elements have a minimum 44px touch target.

---

## Components

### Button

| State | Background | Border | Text | Shadow |
|-------|------------|--------|------|--------|
| Default | `var(--accent-primary)` | none | `#FFFFFF` | none |
| Hover | `var(--accent-hover)` | none | `#FFFFFF` | `var(--shadow-md)` |
| Active / Press | `var(--accent-primary)` | none | `#FFFFFF` | `inset 0 0 0 1px rgba(0,0,0,0.05)` |
| Disabled | `var(--bg-hover)` | none | `var(--text-muted)` | none |

- **Height:** 32px (inline), 40px (standard)
- **Padding:** 0 14px
- **Border radius:** `var(--radius-md)` (6px)
- **Font:** 13px / 500 weight
- **Transition:** `all 150ms ease`

### Card

- **Background:** `var(--bg-surface)`
- **Border:** 1px solid `var(--border-default)`
- **Border radius:** `var(--radius-lg)` (12px)
- **Padding:** `var(--space-5)` (20px)
- **Shadow (light):** `var(--shadow-md)`
- **Shadow (dark):** `var(--shadow-md)` — maintaining subtle lift without blowout

### Stat Card

- **Top Row:** Label (11px mono, `var(--text-muted)`) + Value (28px, `var(--text-primary)`)
- **Bottom Row:** Mini chart/area chart using `var(--accent-primary)` or `var(--accent-secondary)`.
- **Badge (optional):** Pill, `var(--radius-full)`, colored per status.

### Input / Search

- **Height:** 32px
- **Background:** transparent (bordered) or `var(--bg-surface)` (filled)
- **Border:** 1px solid `var(--border-default)`
- **Hover:** Border color transitions to `var(--text-muted)`
- **Focus:** Border color `var(--accent-primary)`, subtle ring `0 0 0 2px var(--accent-muted)`
- **Border radius:** `var(--radius-md)`

### Badge / Tag

- **Padding:** 2px 8px
- **Border radius:** `var(--radius-full)` (pill)
- **Font:** 11px mono, 500 weight
- **Variants:**
  - **Applied:** `bg: var(--accent-muted)`, `text: var(--accent-primary)`
  - **Interview:** `bg: var(--accent-secondary-muted)`, `text: var(--accent-secondary)`
  - **Rejected:** `bg: rgba(192, 57, 43, 0.1)`, `text: var(--status-error)`

---

## Do's and Don'ts

### Do
- Use warm off-white in light mode to reduce eye strain.
- Use serif for page titles to introduce editorial personality.
- Keep the accent teal consistent for "success / applied / accepted" to reinforce calm control.
- Use amber for "urgency / offer / deadline" to introduce energy without alarm.
- Ensure all interactive elements have visible focus states (ring system).
- Use subtle, ambient motion (hover, entrance) — never bouncing or distracting.

### Don't
- Use pure black (`#000000`) for backgrounds or text in dark mode — too harsh.
- Use more than two accent colors on a single surface.
- Use default system shadows in either mode — always use the design system shadows.
- Clutter cards with borders on all sides — use 1px `border-default` and let whitespace do the heavy lifting.

---

## Theme Implementation

- **Switching:** CSS custom properties swapped via `data-theme="dark" | "light"` on `<html>`.
- **Default:** Follows `prefers-color-scheme`. Store explicit overrides in `localStorage`.
- **Flash prevention:** Inline script in `<head>` reads `localStorage` and sets `data-theme` before React mounts.
