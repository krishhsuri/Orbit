'use client';

import { ClipboardPaste, Plus, Sparkles } from 'lucide-react';
import { useUIStore } from '@/stores';
import styles from './NewApplicationActions.module.css';

type Variant = 'header' | 'empty' | 'sidebar' | 'compact';

interface NewApplicationActionsProps {
  variant?: Variant;
}

export function NewApplicationActions({ variant = 'header' }: NewApplicationActionsProps) {
  const { openPasteModal, openAddModal } = useUIStore();

  if (variant === 'sidebar') {
    return (
      <div className={styles.sidebarGroup}>
        <button type="button" className={styles.pasteSidebar} onClick={openPasteModal}>
          <ClipboardPaste size={14} />
          <span>Paste job</span>
        </button>
        <button
          type="button"
          className={styles.manualSidebar}
          onClick={() => openAddModal('form')}
          title="Add manually"
        >
          <Plus size={16} />
        </button>
      </div>
    );
  }

  if (variant === 'empty') {
    return (
      <div className={styles.emptyGroup}>
        <button type="button" className={styles.pastePrimary} onClick={openPasteModal}>
          <Sparkles size={14} />
          Paste job posting
        </button>
        <button type="button" className={styles.manualSecondary} onClick={() => openAddModal('form')}>
          <Plus size={14} />
          Add manually
        </button>
      </div>
    );
  }

  if (variant === 'compact') {
    return (
      <div className={styles.compactGroup}>
        <button type="button" className={styles.pasteCompact} onClick={openPasteModal}>
          <ClipboardPaste size={14} />
          Paste
        </button>
        <button type="button" className={styles.manualCompact} onClick={() => openAddModal('form')}>
          <Plus size={14} />
        </button>
      </div>
    );
  }

  return (
    <div className={styles.headerGroup}>
      <button type="button" className={styles.pastePrimary} onClick={openPasteModal}>
        <Sparkles size={14} />
        Paste job posting
      </button>
      <button type="button" className={styles.manualSecondary} onClick={() => openAddModal('form')}>
        <Plus size={14} />
        Add manually
      </button>
    </div>
  );
}
