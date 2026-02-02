'use client';

import styles from './Badge.module.css';

type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info';
type StatusType = 'applied' | 'screening' | 'oa' | 'interview' | 'offer' | 'accepted' | 'rejected' | 'withdrawn' | 'ghosted';

interface BadgeProps {
  children?: React.ReactNode;
  variant?: BadgeVariant;
  status?: StatusType;
  size?: 'sm' | 'md';
  dot?: boolean;
}

const statusLabels: Record<StatusType, string> = {
  applied: 'Applied',
  screening: 'Screening',
  oa: 'OA',
  interview: 'Interview',
  offer: 'Offer',
  accepted: 'Accepted',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn',
  ghosted: 'Ghosted',
};

export function Badge({ 
  children, 
  variant = 'default',
  status,
  size = 'md',
  dot = false,
}: BadgeProps) {
  const badgeClass = status 
    ? `${styles.badge} ${styles[status]} ${styles[size]}`
    : `${styles.badge} ${styles[variant]} ${styles[size]}`;

  return (
    <span className={badgeClass}>
      {dot && <span className={styles.dot} />}
      {status ? statusLabels[status] : children}
    </span>
  );
}

// Convenience component for status badges
export function StatusBadge({ status }: { status: StatusType }) {
  return <Badge status={status} dot />;
}
