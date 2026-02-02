'use client';

import { motion } from 'framer-motion';
import styles from './EmptyState.module.css';
import { Button } from './Button';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  size?: 'sm' | 'md' | 'lg';
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  size = 'md',
}: EmptyStateProps) {
  return (
    <motion.div
      className={`${styles.container} ${styles[size]}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      {icon && <div className={styles.icon}>{icon}</div>}
      <h3 className={styles.title}>{title}</h3>
      {description && <p className={styles.description}>{description}</p>}
      {action && (
        <Button 
          variant="secondary" 
          size="sm" 
          onClick={action.onClick}
          className={styles.action}
        >
          {action.label}
        </Button>
      )}
    </motion.div>
  );
}

// Convenience wrappers
export function LoadingState({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className={styles.loadingContainer}>
      <div className={styles.spinner} />
      <span className={styles.loadingText}>{message}</span>
    </div>
  );
}

export function ErrorState({ 
  message = 'Something went wrong',
  onRetry,
}: { 
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <EmptyState
      title="Error"
      description={message}
      action={onRetry ? { label: 'Try again', onClick: onRetry } : undefined}
    />
  );
}
