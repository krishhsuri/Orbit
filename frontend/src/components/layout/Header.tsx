'use client';

import { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Search, Command } from 'lucide-react';
import { useUIStore } from '@/stores';
import styles from './Header.module.css';

interface HeaderProps {
  title: string;
  subtitle?: string;
  showAddButton?: boolean;
  action?: ReactNode;
  children?: ReactNode;
}

export function Header({ 
  title, 
  subtitle, 
  showAddButton = false,
  action,
  children 
}: HeaderProps) {
  const { openCommandPalette, openAddModal } = useUIStore();

  return (
    <motion.header 
      className={styles.header}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
    >
      <div className={styles.titleSection}>
        <h1 className={styles.title}>{title}</h1>
        {subtitle && <span className={styles.subtitle}>{subtitle}</span>}
      </div>

      <div className={styles.actions}>
        {/* Custom children */}
        {children}
        
        {/* Search Button */}
        <button className={styles.searchButton} onClick={openCommandPalette}>
          <Search size={14} />
          <span>Search...</span>
          <kbd className={styles.kbd}>
            <Command size={10} />K
          </kbd>
        </button>

        {/* Custom action (like Add button) */}
        {action}
      </div>
    </motion.header>
  );
}
