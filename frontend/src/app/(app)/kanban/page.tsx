'use client';

import { useState, useCallback, useMemo } from 'react';
import Link from 'next/link';
import { useApplications, useUpdateApplicationStatus } from '@/hooks/use-applications';
import { KanbanSkeleton } from '@/components/ui';
import type { ApplicationStatus } from '@/stores';
import {
  Search,
  Plus,
  Filter,
  ChevronLeft,
  ChevronRight,
  MoreHorizontal,
  Loader2,
} from 'lucide-react';
import {
  DndContext,
  DragOverlay,
  rectIntersection,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
  type DragStartEvent,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import styles from './page.module.css';

// Kanban column config — keep existing statuses
const columns: { status: ApplicationStatus; label: string; color: string }[] = [
  { status: 'applied', label: 'Applied', color: 'var(--status-applied)' },
  { status: 'screening', label: 'Screening', color: 'var(--status-screening)' },
  { status: 'oa', label: 'OA', color: 'var(--status-oa)' },
  { status: 'interview', label: 'Interview', color: 'var(--status-interview)' },
  { status: 'offer', label: 'Offer', color: 'var(--status-offer)' },
];

const collapsedStatuses: { status: ApplicationStatus; label: string; color: string }[] = [
  { status: 'accepted', label: 'Accepted', color: 'var(--status-accepted)' },
  { status: 'rejected', label: 'Rejected', color: 'var(--status-rejected)' },
  { status: 'withdrawn', label: 'Withdrawn', color: 'var(--status-withdrawn)' },
  { status: 'ghosted', label: 'Ghosted', color: 'var(--status-ghosted)' },
];

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays <= 0) return 'today';
  if (diffDays === 1) return '1d';
  if (diffDays < 7) return `${diffDays}d`;
  return `${Math.floor(diffDays / 7)}w`;
}

// ── Draggable Card ──────────────────────────────────
function DraggableCard({ app }: { app: any }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: app.id,
    transition: {
      duration: 200,
      easing: 'cubic-bezier(0.25, 1, 0.5, 1)',
    },
  });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
    zIndex: isDragging ? 10 : undefined,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`${styles.kanbanCard} ${isDragging ? styles.dragging : ''}`}
      {...attributes}
      {...listeners}
    >
      <div className={styles.cardTop}>
        <span className={styles.cardCompany}>{app.company}</span>
        <div className={styles.cardTopRight}>
          <span className={styles.cardTime}>{formatTimeAgo(app.updatedAt || app.appliedDate)}</span>
        </div>
      </div>
      <Link href={`/applications/${app.id}`} className={styles.cardTitle} onClick={(e) => { if (isDragging) e.preventDefault(); }}>
        {app.role}
      </Link>
      {app.tags && app.tags.length > 0 && (
        <div className={styles.cardTags}>
          {app.tags.slice(0, 2).map((tag: string) => (
            <span key={tag} className={styles.tag}>{tag}</span>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Drop animation config ───────────────────────────
const dropAnimationConfig = {
  duration: 250,
  easing: 'cubic-bezier(0.25, 1, 0.5, 1)',
};

// ── Overlay Card ────────────────────────────────────
function OverlayCard({ app }: { app: any }) {
  return (
    <div className={`${styles.kanbanCard} ${styles.overlayCard}`}>
      <div className={styles.cardTop}>
        <span className={styles.cardCompany}>{app.company}</span>
      </div>
      <span className={styles.cardTitle}>{app.role}</span>
    </div>
  );
}

// ── Droppable Column ────────────────────────────────
function DroppableColumn({
  column,
  apps,
  isOver,
}: {
  column: typeof columns[0];
  apps: any[];
  isOver: boolean;
}) {
  const { setNodeRef } = useDroppable({ id: column.status });

  return (
    <div className={`${styles.column} ${isOver ? styles.columnOver : ''}`}>
      <div className={styles.columnHeader}>
        <div className={styles.columnTitle}>
          <span
            className={styles.columnDot}
            style={{ backgroundColor: column.color }}
          />
          <span>{column.label}</span>
        </div>
        <span className={styles.columnCount}>{apps.length}</span>
      </div>

      <div ref={setNodeRef} className={styles.columnContent} style={{ minHeight: 120 }}>
        <SortableContext
          items={apps.map((a) => a.id)}
          strategy={verticalListSortingStrategy}
        >
          {apps.map((app) => (
            <DraggableCard key={app.id} app={app} />
          ))}
        </SortableContext>

        {apps.length === 0 && (
          <div className={styles.emptyColumn}>
            <span>Drop here</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Calendar Widget ─────────────────────────────────
function CalendarWidget() {
  const now = new Date();
  const month = now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }).toUpperCase();
  const today = now.getDate();
  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).getDay();
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  const offset = firstDay === 0 ? 6 : firstDay - 1; // Mon-start

  const days = [];
  for (let i = 0; i < offset; i++) {
    days.push(<div key={`e-${i}`} className={styles.calBlank} />);
  }
  for (let d = 1; d <= daysInMonth; d++) {
    days.push(
      <div
        key={d}
        className={`${styles.calDay} ${d === today ? styles.calToday : ''}`}
      >
        {d}
      </div>
    );
  }

  return (
    <div className={styles.calendarSection}>
      <div className={styles.calHeader}>
        <span className={styles.calMonth}>{month}</span>
        <div className={styles.calNav}>
          <button className={styles.calNavBtn}><ChevronLeft size={12} /></button>
          <button className={styles.calNavBtn}><ChevronRight size={12} /></button>
        </div>
      </div>
      <div className={styles.calGrid}>
        {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((d, i) => (
          <div key={i} className={styles.calLabel}>{d}</div>
        ))}
        {days}
      </div>
    </div>
  );
}

// ── Main Kanban Page ────────────────────────────────
export default function KanbanPage() {
  const { data, isLoading, error } = useApplications();
  const { mutate: updateStatus } = useUpdateApplicationStatus();

  const [activeId, setActiveId] = useState<string | null>(null);
  const [overColumn, setOverColumn] = useState<string | null>(null);

  const applications = data?.applications || [];

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 5 },
    })
  );

  const getByStatus = useCallback(
    (status: ApplicationStatus) => applications.filter((app) => app.status === status),
    [applications]
  );

  const activeApp = activeId ? applications.find((app) => app.id === activeId) : null;

  // Stats from real data
  const stats = useMemo(() => {
    const total = applications.length;
    const interviews = applications.filter((a) => a.status === 'interview').length;
    const responded = applications.filter((a) => ['interview', 'offer', 'accepted', 'screening'].includes(a.status)).length;
    const rate = total > 0 ? Math.round((responded / total) * 100) : 0;
    return { total, interviews, rate };
  }, [applications]);

  // Upcoming deadlines (take first 3 most recent)
  const deadlines = useMemo(() => {
    return applications
      .filter((a) => ['interview', 'screening', 'oa'].includes(a.status))
      .slice(0, 3)
      .map((a) => ({
        id: a.id,
        company: a.company,
        role: a.role,
        date: new Date(a.updatedAt || a.appliedDate),
      }));
  }, [applications]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragOver = (event: any) => {
    const { over } = event;
    if (!over) {
      setOverColumn(null);
      return;
    }
    const overId = over.id as string;
    const isColumnStatus =
      columns.some((c) => c.status === overId) ||
      collapsedStatuses.some((c) => c.status === overId);

    if (isColumnStatus) {
      setOverColumn(overId);
    } else {
      const overApp = applications.find((app) => app.id === overId);
      if (overApp) {
        setOverColumn(overApp.status);
      }
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveId(null);
    setOverColumn(null);

    if (!over) return;

    const draggedApp = applications.find((app) => app.id === active.id);
    if (!draggedApp) return;

    const overId = over.id as string;
    let targetStatus: ApplicationStatus | null = null;

    const targetColumn = columns.find((c) => c.status === overId);
    if (targetColumn) {
      targetStatus = targetColumn.status;
    } else {
      const overApp = applications.find((app) => app.id === overId);
      if (overApp) {
        targetStatus = overApp.status;
      }
    }

    if (targetStatus && targetStatus !== draggedApp.status) {
      updateStatus({ id: draggedApp.id, status: targetStatus });
    }
  };

  const collapsedCounts = collapsedStatuses.map((s) => ({
    ...s,
    count: getByStatus(s.status).length,
  }));

  if (isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.loadingState}>
          <Loader2 size={24} className={styles.spin} />
          <span>Loading board...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      {/* Header Bar */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.pageTitle}>Dashboard</h1>
          <span className={styles.headerSep}>/</span>
          <span className={styles.headerMeta}>KANBAN</span>
        </div>
        <div className={styles.headerRight}>
          <div className={styles.searchWrapper}>
            <Search size={14} className={styles.searchIcon} />
            <input
              type="text"
              placeholder="Search..."
              className={styles.searchInput}
            />
          </div>
          <button className={styles.newButton}>
            <Plus size={14} />
            New
          </button>
        </div>
      </header>

      {/* Stats Cards */}
      <div className={styles.statsRow}>
        <div className={styles.statCard}>
          <div className={styles.statTop}>
            <span className={styles.statLabel}>APPLICATIONS</span>
            <span className={styles.statBadge}>↗ 12%</span>
          </div>
          <span className={styles.statValue}>{stats.total}</span>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statTop}>
            <span className={styles.statLabel}>INTERVIEWS</span>
            <span className={styles.statPulse} />
          </div>
          <span className={styles.statValue}>{stats.interviews}</span>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statTop}>
            <span className={styles.statLabel}>RESPONSE RATE</span>
            <span className={styles.statMeta}>AVG</span>
          </div>
          <span className={styles.statValue}>
            {stats.rate}<span className={styles.statUnit}>%</span>
          </span>
        </div>
      </div>

      {/* Main Layout: Kanban + Sidebar */}
      <div className={styles.mainLayout}>
        {/* Kanban Columns */}
        <div className={styles.boardArea}>
          <DndContext
            sensors={sensors}
            collisionDetection={rectIntersection}
            onDragStart={handleDragStart}
            onDragOver={handleDragOver}
            onDragEnd={handleDragEnd}
          >
            <div className={styles.board}>
              {columns.map((column) => {
                const columnApps = getByStatus(column.status);
                return (
                  <DroppableColumn
                    key={column.status}
                    column={column}
                    apps={columnApps}
                    isOver={overColumn === column.status}
                  />
                );
              })}
            </div>
            <DragOverlay dropAnimation={dropAnimationConfig}>
              {activeApp ? <OverlayCard app={activeApp} /> : null}
            </DragOverlay>
          </DndContext>

          {/* Collapsed Statuses */}
          {collapsedCounts.some((s) => s.count > 0) && (
            <div className={styles.collapsedSection}>
              {collapsedCounts
                .filter((s) => s.count > 0)
                .map((status) => (
                  <div key={status.status} className={styles.collapsedItem}>
                    <span
                      className={styles.collapsedDot}
                      style={{ backgroundColor: status.color }}
                    />
                    <span className={styles.collapsedLabel}>{status.label}</span>
                    <span className={styles.collapsedCount}>{status.count}</span>
                  </div>
                ))}
            </div>
          )}
        </div>

        {/* Right Sidebar */}
        <aside className={styles.sidebar}>
          {/* Upcoming Deadlines */}
          <div className={styles.sidebarSection}>
            <div className={styles.sidebarSectionHeader}>
              <h3>Upcoming Deadlines</h3>
              <button className={styles.sidebarFilterBtn}>
                <Filter size={14} />
              </button>
            </div>
            <div className={styles.deadlineList}>
              {deadlines.length === 0 ? (
                <p className={styles.noDeadlines}>No upcoming deadlines</p>
              ) : (
                deadlines.map((d) => {
                  const diffDays = Math.max(0, Math.ceil((d.date.getTime() - Date.now()) / 86400000));
                  return (
                    <Link
                      key={d.id}
                      href={`/applications/${d.id}`}
                      className={styles.deadlineItem}
                    >
                      <div className={styles.deadlineDateBox}>
                        <span className={styles.deadlineMonth}>
                          {d.date.toLocaleDateString('en-US', { month: 'short' }).toUpperCase()}
                        </span>
                        <span className={styles.deadlineDay}>{d.date.getDate()}</span>
                      </div>
                      <div className={styles.deadlineInfo}>
                        <span className={styles.deadlineName}>{d.company}</span>
                        <div className={styles.deadlineBar}>
                          <div
                            className={styles.deadlineBarFill}
                            style={{ width: `${Math.max(10, 100 - diffDays * 10)}%` }}
                          />
                        </div>
                        <span className={styles.deadlineDays}>
                          {diffDays === 0 ? 'TODAY' : `${diffDays} DAYS`}
                        </span>
                      </div>
                    </Link>
                  );
                })
              )}
            </div>
          </div>

          {/* Calendar */}
          <CalendarWidget />

          {/* Weekly Focus */}
          <div className={styles.sidebarSection}>
            <span className={styles.weeklyLabel}>WEEKLY FOCUS</span>
            <div className={styles.weeklyBars}>
              {[20, 40, 70, 50, 30, 10, 10].map((h, i) => (
                <div
                  key={i}
                  className={`${styles.weeklyBar} ${i === 2 ? styles.weeklyBarActive : ''}`}
                  style={{ height: `${h}%` }}
                />
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
