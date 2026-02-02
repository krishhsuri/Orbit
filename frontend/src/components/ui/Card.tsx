'use client';

import { HTMLAttributes, forwardRef } from 'react';
import styles from './Card.module.css';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'glass';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  hover?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      variant = 'default',
      padding = 'md',
      hover = false,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    const classes = [
      styles.card,
      styles[variant],
      styles[`padding-${padding}`],
      hover ? styles.hoverable : '',
      className,
    ].filter(Boolean).join(' ');

    return (
      <div ref={ref} className={classes} {...props}>
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

// Sub-components for structured cards
export function CardHeader({ 
  children, 
  className = '' 
}: { 
  children: React.ReactNode; 
  className?: string;
}) {
  return (
    <div className={`${styles.header} ${className}`}>
      {children}
    </div>
  );
}

export function CardTitle({ 
  children,
  className = '',
}: { 
  children: React.ReactNode;
  className?: string;
}) {
  return <h3 className={`${styles.title} ${className}`}>{children}</h3>;
}

export function CardDescription({ 
  children,
  className = '',
}: { 
  children: React.ReactNode;
  className?: string;
}) {
  return <p className={`${styles.description} ${className}`}>{children}</p>;
}

export function CardContent({ 
  children, 
  className = '' 
}: { 
  children: React.ReactNode; 
  className?: string;
}) {
  return <div className={`${styles.content} ${className}`}>{children}</div>;
}

export function CardFooter({ 
  children, 
  className = '' 
}: { 
  children: React.ReactNode; 
  className?: string;
}) {
  return <div className={`${styles.footer} ${className}`}>{children}</div>;
}
