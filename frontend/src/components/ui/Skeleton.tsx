'use client';

import styles from './Skeleton.module.css';

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  variant?: 'text' | 'title' | 'circle' | 'rect';
  className?: string;
}

export function Skeleton({ 
  width, 
  height, 
  variant = 'rect',
  className = '',
}: SkeletonProps) {
  return (
    <div 
      className={`${styles.skeleton} ${styles[variant]} ${className}`}
      style={{ width, height }}
    />
  );
}

/* ─────────────────────────────────────────────────
   Page-specific skeleton layouts
   ───────────────────────────────────────────────── */

export function DashboardSkeleton() {
  return (
    <div className={styles.dashboardSkeleton}>
      {/* Stats Grid */}
      <div className={styles.statsGridSkeleton}>
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className={styles.statCardSkeleton}>
            <Skeleton variant="rect" width={40} height={40} className={styles.statIconSkeleton} />
            <div className={styles.statContentSkeleton}>
              <Skeleton variant="title" width="50%" height={28} />
              <Skeleton variant="text" width="80%" />
            </div>
          </div>
        ))}
      </div>

      {/* Main Grid */}
      <div className={styles.mainGridSkeleton}>
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className={styles.cardSkeleton}>
            <div className={styles.cardHeaderSkeleton}>
              <Skeleton variant="text" width="40%" />
            </div>
            <div className={styles.cardBodySkeleton}>
              <Skeleton variant="text" width="100%" />
              <Skeleton variant="text" width="75%" />
              <Skeleton variant="text" width="60%" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ApplicationsSkeleton() {
  return (
    <div className={styles.appListSkeleton}>
      {/* Toolbar */}
      <div className={styles.appToolbarSkeleton}>
        <Skeleton variant="rect" width={240} height={34} />
        <Skeleton variant="rect" width={80} height={34} />
        <Skeleton variant="rect" width={80} height={34} />
      </div>

      {/* List rows */}
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className={styles.appRowSkeleton}>
          <Skeleton variant="rect" width={36} height={36} />
          <div className={styles.appRowContentSkeleton}>
            <Skeleton variant="text" width="30%" />
            <Skeleton variant="text" width="50%" />
          </div>
          <Skeleton variant="rect" width={80} height={24} />
        </div>
      ))}
    </div>
  );
}

export function KanbanSkeleton() {
  return (
    <div className={styles.kanbanSkeleton}>
      {Array.from({ length: 5 }).map((_, col) => (
        <div key={col} className={styles.kanbanColumnSkeleton}>
          <div className={styles.kanbanColumnHeaderSkeleton}>
            <Skeleton variant="text" width="60%" />
          </div>
          <div className={styles.kanbanColumnBodySkeleton}>
            {Array.from({ length: col === 0 ? 3 : col === 1 ? 2 : 1 }).map((_, card) => (
              <div key={card} className={styles.kanbanCardSkeleton}>
                <Skeleton variant="text" width="70%" />
                <Skeleton variant="text" width="100%" />
                <Skeleton variant="text" width="40%" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function EmailsSkeleton() {
  return (
    <div className={styles.appListSkeleton}>
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className={styles.appRowSkeleton} style={{ minHeight: 80 }}>
          <Skeleton variant="rect" width={40} height={40} />
          <div className={styles.appRowContentSkeleton}>
            <Skeleton variant="text" width="25%" />
            <Skeleton variant="text" width="60%" />
            <Skeleton variant="text" width="40%" />
          </div>
          <Skeleton variant="rect" width={100} height={28} />
        </div>
      ))}
    </div>
  );
}
