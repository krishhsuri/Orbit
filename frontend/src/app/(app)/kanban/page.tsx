'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { Header } from '@/components/layout/Header';
import { useApplications, useUpdateApplicationStatus } from '@/hooks/use-applications';
import { KanbanSkeleton } from '@/components/ui';
import type { ApplicationStatus } from '@/stores';
import { 
  Building2, 
  Sparkles,
  Clock,
  GripVertical,
} from 'lucide-react';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
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

// Kanban column configuration
const columns: { status: ApplicationStatus; label: string; color: string; description: string }[] = [
  { status: 'applied', label: 'Applied', color: 'var(--status-applied)', description: 'Waiting for response' },
  { status: 'screening', label: 'Screening', color: 'var(--status-screening)', description: 'Recruiter reviewing' },
  { status: 'oa', label: 'OA', color: 'var(--status-oa)', description: 'Online assessment' },
  { status: 'interview', label: 'Interview', color: 'var(--status-interview)', description: 'Interview stage' },
  { status: 'offer', label: 'Offer 🎉', color: 'var(--status-offer)', description: 'Received offer' },
];

const collapsedStatuses: { status: ApplicationStatus; label: string; color: string }[] = [
  { status: 'accepted', label: 'Accepted', color: 'var(--status-accepted)' },
  { status: 'rejected', label: 'Rejected', color: 'var(--status-rejected)' },
  { status: 'withdrawn', label: 'Withdrawn', color: 'var(--status-withdrawn)' },
  { status: 'ghosted', label: 'Ghosted', color: 'var(--status-ghosted)' },
];

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffDays = Math.ceil((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
  
  if (diffDays <= 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ── Draggable Card ────────────────────────────────────────
function DraggableCard({ app }: { app: any }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: app.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div 
      ref={setNodeRef} 
      style={style} 
      className={`${styles.kanbanCard} ${isDragging ? styles.dragging : ''}`}
    >
      {/* Drag Handle */}
      <div className={styles.dragHandle} {...attributes} {...listeners}>
        <GripVertical size={14} />
      </div>

      {/* Card Header */}
      <div className={styles.cardHeader}>
        <div className={styles.cardLogo}>
          <Building2 size={16} />
        </div>
        <Link href={`/applications/${app.id}`} className={styles.cardInfo}>
          <h4>{app.company}</h4>
          <p>{app.role}</p>
        </Link>
      </div>

      {/* Card Footer */}
      <div className={styles.cardFooter}>
        <span className={styles.cardDate}>
          <Clock size={12} />
          {formatDate(app.updatedAt)}
        </span>
      </div>

      {/* Tags */}
      {app.tags.length > 0 && (
        <div className={styles.cardTags}>
          {app.tags.slice(0, 2).map((tag: string) => (
            <span key={tag} className={styles.tag}>{tag}</span>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Overlay Card (ghost while dragging) ───────────────────
function OverlayCard({ app }: { app: any }) {
  return (
    <div className={`${styles.kanbanCard} ${styles.overlayCard}`}>
      <div className={styles.dragHandle}>
        <GripVertical size={14} />
      </div>
      <div className={styles.cardHeader}>
        <div className={styles.cardLogo}>
          <Building2 size={16} />
        </div>
        <div className={styles.cardInfo}>
          <h4>{app.company}</h4>
          <p>{app.role}</p>
        </div>
      </div>
    </div>
  );
}

// ── Droppable Column ──────────────────────────────────────
function DroppableColumn({ 
  column, 
  apps, 
  isOver 
}: { 
  column: typeof columns[0]; 
  apps: any[];
  isOver: boolean;
}) {
  return (
    <div className={`${styles.column} ${isOver ? styles.columnOver : ''}`}>
      <div className={styles.columnHeader}>
        <div className={styles.columnTitle}>
          <span 
            className={styles.columnDot}
            style={{ backgroundColor: column.color }}
          />
          <span>{column.label}</span>
          <span className={styles.columnCount}>{apps.length}</span>
        </div>
        <span className={styles.columnDescription}>{column.description}</span>
      </div>

      <div className={styles.columnContent}>
        <SortableContext 
          items={apps.map(a => a.id)} 
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

// ── Main Kanban Page ──────────────────────────────────────
export default function KanbanPage() {
  const { data, isLoading, error } = useApplications();
  const { mutate: updateStatus } = useUpdateApplicationStatus();
  
  const [activeId, setActiveId] = useState<string | null>(null);
  const [overColumn, setOverColumn] = useState<string | null>(null);

  const applications = data?.applications || [];

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    })
  );

  const getByStatus = useCallback((status: ApplicationStatus) => {
    return applications.filter(app => app.status === status);
  }, [applications]);

  const activeApp = activeId ? applications.find(app => app.id === activeId) : null;

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragOver = (event: any) => {
    const { over } = event;
    if (!over) {
      setOverColumn(null);
      return;
    }
    // Determine which column the card is over
    const overId = over.id as string;
    // Check if over is a column status or a card in a column
    const isColumnStatus = columns.some(c => c.status === overId) || 
                           collapsedStatuses.some(c => c.status === overId);
    
    if (isColumnStatus) {
      setOverColumn(overId);
    } else {
      // Find which column this card belongs to
      const overApp = applications.find(app => app.id === overId);
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

    const activeApp = applications.find(app => app.id === active.id);
    if (!activeApp) return;

    const overId = over.id as string;
    
    // Determine target status
    let targetStatus: ApplicationStatus | null = null;
    
    // Check if dropped on a column
    const targetColumn = columns.find(c => c.status === overId);
    if (targetColumn) {
      targetStatus = targetColumn.status;
    } else {
      // Dropped on a card — get that card's status
      const overApp = applications.find(app => app.id === overId);
      if (overApp) {
        targetStatus = overApp.status;
      }
    }

    if (targetStatus && targetStatus !== activeApp.status) {
      updateStatus({ id: activeApp.id, status: targetStatus });
    }
  };

  const collapsedCounts = collapsedStatuses.map(s => ({
    ...s,
    count: getByStatus(s.status).length
  }));

  if (isLoading) {
    return (
      <div className={styles.page}>
        <Header title="Kanban Board" subtitle="Loading..." showAddButton={true} />
        <KanbanSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.page}>
        <Header title="Kanban Board" subtitle="Error" showAddButton={true} />
        <div className={styles.errorContainer}>
          <p>Failed to load board. Please try again.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <Header title="Kanban Board" subtitle="Drag cards between columns to update status" showAddButton={true} />
      
      <div className={styles.content}>
        {/* AI Hint */}
        <div className={styles.aiHint}>
          <Sparkles size={16} />
          <span>
            <strong>Smart Kanban:</strong> Drag cards between columns to update status. AI auto-moves cards when it detects changes in your email.
          </span>
        </div>

        {/* Kanban Board with DnD */}
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
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

          {/* Drag Overlay — ghost card that follows cursor */}
          <DragOverlay>
            {activeApp ? <OverlayCard app={activeApp} /> : null}
          </DragOverlay>
        </DndContext>

        {/* Collapsed Statuses */}
        {collapsedCounts.some(s => s.count > 0) && (
          <div className={styles.collapsedSection}>
            <h3>Other Statuses</h3>
            <div className={styles.collapsedGrid}>
              {collapsedCounts.filter(s => s.count > 0).map((status) => (
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
          </div>
        )}
      </div>
    </div>
  );
}
