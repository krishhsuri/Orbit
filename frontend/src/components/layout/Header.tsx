'use client';

import { Plus, Search, Command } from 'lucide-react';
import { useUIStore } from '@/stores';
import styles from './Header.module.css';
import { ReactNode } from 'react';

interface HeaderProps {
  title: string;
  subtitle?: string;
  showAddButton?: boolean;
  children?: ReactNode;
}

export function Header({ title, subtitle, showAddButton = true, children }: HeaderProps) {
  const { openAddModal } = useUIStore();

  return (
    <header className={styles.header}>
      <div className={styles.titleSection}>
        <h1 className={styles.title}>{title}</h1>
        {subtitle && <span className={styles.subtitle}>{subtitle}</span>}
      </div>

      <div className={styles.actions}>
        {/* Custom children (like Sync button) */}
        {children}
        
        {/* Search */}
        <button className={styles.searchButton}>
          <Search size={16} />
          <span>Search...</span>
          <kbd className={styles.kbd}>
            <Command size={12} />K
          </kbd>
        </button>

        {/* Add Button */}
        {showAddButton && (
          <button className={styles.addButton} onClick={openAddModal}>
            <Plus size={18} />
            <span>Add Application</span>
          </button>
        )}
      </div>
    </header>
  );
}

