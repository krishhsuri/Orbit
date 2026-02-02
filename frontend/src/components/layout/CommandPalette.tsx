'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Search, 
  Plus, 
  Home, 
  Briefcase, 
  BarChart3, 
  Settings, 
  Mail,
  ArrowRight,
  Command
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import styles from './CommandPalette.module.css';

interface CommandItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  shortcut?: string;
  action: () => void;
  category: 'navigation' | 'actions' | 'settings';
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onAddApplication?: () => void;
}

export function CommandPalette({ isOpen, onClose, onAddApplication }: CommandPaletteProps) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Define commands
  const commands: CommandItem[] = useMemo(() => [
    // Navigation
    { id: 'home', label: 'Go to Dashboard', icon: <Home size={16} />, shortcut: 'G D', action: () => router.push('/'), category: 'navigation' },
    { id: 'applications', label: 'Go to Applications', icon: <Briefcase size={16} />, shortcut: 'G A', action: () => router.push('/applications'), category: 'navigation' },
    { id: 'analytics', label: 'Go to Analytics', icon: <BarChart3 size={16} />, shortcut: 'G N', action: () => router.push('/analytics'), category: 'navigation' },
    { id: 'emails', label: 'Go to Emails', icon: <Mail size={16} />, shortcut: 'G E', action: () => router.push('/emails'), category: 'navigation' },
    { id: 'settings', label: 'Go to Settings', icon: <Settings size={16} />, shortcut: 'G S', action: () => router.push('/settings'), category: 'navigation' },
    // Actions
    { id: 'new-app', label: 'Add New Application', icon: <Plus size={16} />, shortcut: '⌘ N', action: () => onAddApplication?.(), category: 'actions' },
  ], [router, onAddApplication]);

  // Filter commands based on query
  const filteredCommands = useMemo(() => {
    if (!query) return commands;
    const lowerQuery = query.toLowerCase();
    return commands.filter(
      cmd => cmd.label.toLowerCase().includes(lowerQuery)
    );
  }, [commands, query]);

  // Reset selection when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(i => Math.min(i + 1, filteredCommands.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(i => Math.max(i - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (filteredCommands[selectedIndex]) {
          filteredCommands[selectedIndex].action();
          onClose();
        }
        break;
      case 'Escape':
        onClose();
        break;
    }
  }, [filteredCommands, selectedIndex, onClose]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, handleKeyDown]);

  // Reset on open
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Group commands by category
  const groupedCommands = useMemo(() => {
    const groups: Record<string, CommandItem[]> = {};
    filteredCommands.forEach(cmd => {
      if (!groups[cmd.category]) groups[cmd.category] = [];
      groups[cmd.category].push(cmd);
    });
    return groups;
  }, [filteredCommands]);

  const categoryLabels: Record<string, string> = {
    navigation: 'Navigation',
    actions: 'Actions',
    settings: 'Settings',
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            className={styles.backdrop}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <div className={styles.container}>
            <motion.div
              className={styles.palette}
              initial={{ opacity: 0, scale: 0.95, y: -20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -20 }}
              transition={{ duration: 0.15 }}
            >
              {/* Search Input */}
              <div className={styles.inputWrapper}>
                <Search size={16} className={styles.searchIcon} />
                <input
                  autoFocus
                  type="text"
                  className={styles.input}
                  placeholder="Search commands..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <span className={styles.hint}>
                  <Command size={12} />
                  K
                </span>
              </div>

              {/* Results */}
              <div className={styles.results}>
                {Object.entries(groupedCommands).map(([category, items]) => (
                  <div key={category} className={styles.group}>
                    <div className={styles.groupLabel}>{categoryLabels[category]}</div>
                    {items.map((cmd, idx) => {
                      const globalIdx = filteredCommands.findIndex(c => c.id === cmd.id);
                      return (
                        <button
                          key={cmd.id}
                          className={`${styles.item} ${globalIdx === selectedIndex ? styles.selected : ''}`}
                          onClick={() => {
                            cmd.action();
                            onClose();
                          }}
                          onMouseEnter={() => setSelectedIndex(globalIdx)}
                        >
                          <span className={styles.itemIcon}>{cmd.icon}</span>
                          <span className={styles.itemLabel}>{cmd.label}</span>
                          {cmd.shortcut && (
                            <span className={styles.shortcut}>{cmd.shortcut}</span>
                          )}
                          <ArrowRight size={14} className={styles.arrow} />
                        </button>
                      );
                    })}
                  </div>
                ))}

                {filteredCommands.length === 0 && (
                  <div className={styles.empty}>No commands found</div>
                )}
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
