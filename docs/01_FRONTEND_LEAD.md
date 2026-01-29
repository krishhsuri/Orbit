# Frontend Lead Engineer — Orbit

> **Owner:** Frontend Lead  
> **Scope:** All client-side code, UI/UX implementation, state management

---

## 🎯 Mission

Build a **Linear-quality** frontend for Orbit — the student career launchpad. The UI should feel premium, fast, and delightful. Every interaction should be buttery smooth.

---

## 📐 Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND ARCHITECTURE                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │   React     │    │  React      │    │  Zustand    │          │
│  │   Router    │───▶│  Components │◀───│  (UI State) │          │
│  │   (Routes)  │    │  (Views)    │    │             │          │
│  └─────────────┘    └──────┬──────┘    └─────────────┘          │
│                            │                                      │
│                            ▼                                      │
│                    ┌─────────────┐                               │
│                    │  TanStack   │                               │
│                    │  Query      │                               │
│                    │ (API Cache) │                               │
│                    └──────┬──────┘                               │
│                           │                                       │
│                           ▼                                       │
│                    ┌─────────────┐                               │
│                    │  API Client │                               │
│                    │  (fetch)    │                               │
│                    └─────────────┘                               │
│                           │                                       │
└───────────────────────────┼───────────────────────────────────────┘
                            │
                            ▼
                    ┌─────────────┐
                    │  Backend    │
                    │  REST API   │
                    └─────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|------------|-----|
| **Framework** | React 18 + TypeScript | Type safety, ecosystem |
| **Build Tool** | Vite | Fast HMR, modern bundling |
| **Routing** | React Router v6 | Standard, nested routes |
| **Server State** | TanStack Query v5 | Caching, mutations, sync |
| **Client State** | Zustand | Simple, no boilerplate |
| **Forms** | React Hook Form + Zod | Performant, validation |
| **Styling** | CSS Variables + Modules | No framework lock-in |
| **Animation** | Framer Motion | Production-grade motion |
| **Icons** | Lucide React | Clean, consistent icons |
| **Date** | date-fns | Lightweight date utils |

---

## 📁 Project Structure

```
frontend/
├── public/
│   ├── logo.png
│   ├── favicon.ico
│   └── manifest.json
│
├── src/
│   ├── main.tsx                 # Entry point
│   ├── App.tsx                  # Root component
│   ├── routes.tsx               # Route definitions
│   │
│   ├── components/
│   │   ├── ui/                  # Primitive components
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Dropdown.tsx
│   │   │   ├── Skeleton.tsx
│   │   │   └── index.ts
│   │   │
│   │   ├── layout/              # Layout components
│   │   │   ├── AppShell.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── CommandPalette.tsx
│   │   │   └── index.ts
│   │   │
│   │   ├── applications/        # Feature: Applications
│   │   │   ├── ApplicationCard.tsx
│   │   │   ├── ApplicationList.tsx
│   │   │   ├── ApplicationForm.tsx
│   │   │   ├── ApplicationDetail.tsx
│   │   │   ├── StatusBadge.tsx
│   │   │   ├── KanbanBoard.tsx
│   │   │   └── index.ts
│   │   │
│   │   ├── dashboard/           # Feature: Dashboard
│   │   │   ├── StatsCards.tsx
│   │   │   ├── UpcomingDeadlines.tsx
│   │   │   ├── ActivityFeed.tsx
│   │   │   ├── WeeklyGoal.tsx
│   │   │   └── index.ts
│   │   │
│   │   ├── analytics/           # Feature: Analytics
│   │   │   ├── FunnelChart.tsx
│   │   │   ├── ResponseRates.tsx
│   │   │   ├── InsightsPanel.tsx
│   │   │   └── index.ts
│   │   │
│   │   └── common/              # Shared components
│   │       ├── EmptyState.tsx
│   │       ├── ErrorState.tsx
│   │       ├── LoadingState.tsx
│   │       └── index.ts
│   │
│   ├── pages/                   # Route pages
│   │   ├── Dashboard.tsx
│   │   ├── Applications.tsx
│   │   ├── ApplicationDetail.tsx
│   │   ├── Kanban.tsx
│   │   ├── Analytics.tsx
│   │   ├── Settings.tsx
│   │   ├── Login.tsx
│   │   ├── AuthCallback.tsx
│   │   └── NotFound.tsx
│   │
│   ├── hooks/                   # Custom hooks
│   │   ├── useApplications.ts
│   │   ├── useApplication.ts
│   │   ├── useAnalytics.ts
│   │   ├── useAuth.ts
│   │   ├── useKeyboard.ts
│   │   ├── useTheme.ts
│   │   └── useLocalStorage.ts
│   │
│   ├── stores/                  # Zustand stores
│   │   ├── ui-store.ts          # Modals, sidebar, theme
│   │   ├── auth-store.ts        # User, tokens
│   │   └── index.ts
│   │
│   ├── api/                     # API layer
│   │   ├── client.ts            # Base fetch wrapper
│   │   ├── applications.ts      # Application endpoints
│   │   ├── analytics.ts         # Analytics endpoints
│   │   ├── auth.ts              # Auth endpoints
│   │   └── index.ts
│   │
│   ├── types/                   # TypeScript types
│   │   ├── application.ts
│   │   ├── user.ts
│   │   ├── analytics.ts
│   │   └── api.ts
│   │
│   ├── utils/                   # Utility functions
│   │   ├── format.ts            # String formatting
│   │   ├── date.ts              # Date helpers
│   │   ├── cn.ts                # Class merging
│   │   └── constants.ts         # App constants
│   │
│   ├── styles/                  # Global styles
│   │   ├── globals.css          # Reset, base styles
│   │   ├── tokens.css           # Design tokens
│   │   └── animations.css       # Keyframes
│   │
│   └── lib/                     # Third-party configs
│       └── query-client.ts      # TanStack Query setup
│
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── .env.example
```

---

## 🎨 Design System

### Color Tokens

```css
:root {
  /* Backgrounds */
  --bg-base: #0a0a0b;
  --bg-surface: #111113;
  --bg-elevated: #18181b;
  --bg-hover: #1f1f23;
  
  /* Text */
  --text-primary: #fafafa;
  --text-secondary: #a1a1aa;
  --text-muted: #52525b;
  
  /* Accent */
  --accent-primary: #6366f1;
  --accent-hover: #818cf8;
  
  /* Status Colors */
  --status-applied: #3b82f6;
  --status-interview: #10b981;
  --status-offer: #22c55e;
  --status-rejected: #ef4444;
  --status-ghosted: #6b7280;
  
  /* Borders */
  --border-subtle: #27272a;
  --border-default: #3f3f46;
}
```

### Typography

```css
:root {
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.25rem;
  --text-2xl: 1.5rem;
  --text-3xl: 2rem;
}
```

### Spacing (8px grid)

```css
:root {
  --space-1: 0.25rem;   /* 4px */
  --space-2: 0.5rem;    /* 8px */
  --space-3: 0.75rem;   /* 12px */
  --space-4: 1rem;      /* 16px */
  --space-6: 1.5rem;    /* 24px */
  --space-8: 2rem;      /* 32px */
}
```

---

## 📱 Pages Specification

### 1. Dashboard (`/`)
- Stats cards (total, in-progress, interviews, offers)
- Upcoming deadlines (next 7 days)
- Recent activity feed
- Weekly application goal with progress bar

### 2. Applications (`/applications`)
- List view with infinite scroll
- Search bar (company, role)
- Filters (status, tags, date range)
- Sort (date, company, status)
- Quick status change inline

### 3. Kanban (`/applications/kanban`)
- Columns: Applied, OA, Interview, Offer, Rejected
- Drag-drop between columns
- Card shows company, role, days since applied

### 4. Application Detail (`/applications/:id`)
- Full details (company, role, salary, source)
- Timeline of all events
- Notes section
- Linked emails (if synced)
- Edit/Delete actions

### 5. Analytics (`/analytics`)
- Conversion funnel visualization
- Response rate by source (referral vs cold)
- Time to response histogram
- AI-generated insights

### 6. Settings (`/settings`)
- Profile info
- Theme toggle
- Tag management
- Import/Export data

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd/Ctrl + K` | Open command palette |
| `Cmd/Ctrl + N` | New application |
| `Cmd/Ctrl + /` | Toggle sidebar |
| `j / k` | Navigate list up/down |
| `Enter` | Open selected item |
| `Esc` | Close modal/dropdown |

---

## 🚀 Performance Targets

| Metric | Target |
|--------|--------|
| **LCP** | < 1.5s |
| **FID** | < 100ms |
| **CLS** | < 0.1 |
| **Bundle Size** | < 200KB gzipped |
| **Time to Interactive** | < 2s |

### Optimization Strategies
- Code splitting by route (lazy loading)
- Virtualized lists for 100+ applications
- Optimistic updates for mutations
- Preload critical fonts
- Image optimization (WebP, lazy load)

---

## 🧪 Testing Strategy

| Type | Tool | Coverage Target |
|------|------|-----------------|
| **Unit** | Vitest | 80% utilities, hooks |
| **Component** | React Testing Library | Critical paths |
| **E2E** | Playwright | Happy paths |
| **Visual** | Chromatic (optional) | Design system |

### Critical Test Paths
1. User can login via Google OAuth
2. User can add a new application
3. User can update application status
4. User can filter/search applications
5. User can drag-drop in Kanban view

---

## 📅 Milestones

### Week 1: Foundation
- [ ] Vite + React + TS setup
- [ ] Design tokens implemented
- [ ] Layout shell (sidebar, header)
- [ ] Routing structure
- [ ] Auth store (mock)

### Week 2: Core CRUD
- [ ] Applications list page
- [ ] Add Application modal
- [ ] Application detail page
- [ ] Status badge dropdown
- [ ] Local storage persistence

### Week 3: Features
- [ ] Dashboard with stats
- [ ] Kanban drag-drop view
- [ ] Basic analytics charts
- [ ] Settings page

### Week 4: Polish
- [ ] Command palette
- [ ] Keyboard shortcuts
- [ ] Animations & transitions
- [ ] Empty/loading/error states
- [ ] Mobile responsive

---

## 📋 Definition of Done

Before marking any feature complete:

- [ ] TypeScript strict, no `any`
- [ ] All interactive states (hover, focus, active, disabled)
- [ ] Loading state
- [ ] Error state  
- [ ] Empty state
- [ ] Mobile responsive
- [ ] Keyboard accessible
- [ ] Animation uses Framer Motion
- [ ] No console errors/warnings

---

*Frontend Lead Engineer — Orbit v1.0*
