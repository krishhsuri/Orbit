'use client';

import { useEffect, useCallback, useState } from 'react';
import { useRouter } from 'next/navigation';

interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  meta?: boolean;
  shift?: boolean;
  action: () => void;
  description?: string;
}

interface UseKeyboardShortcutsOptions {
  enabled?: boolean;
  shortcuts?: KeyboardShortcut[];
}

export function useKeyboardShortcuts(options: UseKeyboardShortcutsOptions = {}) {
  const { enabled = true, shortcuts = [] } = options;

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    // Don't trigger shortcuts when typing in inputs
    const target = e.target as HTMLElement;
    if (
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable
    ) {
      return;
    }

    for (const shortcut of shortcuts) {
      const ctrlMatch = shortcut.ctrl ? (e.ctrlKey || e.metaKey) : true;
      const metaMatch = shortcut.meta ? e.metaKey : true;
      const shiftMatch = shortcut.shift ? e.shiftKey : !e.shiftKey;
      const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase();

      if (keyMatch && ctrlMatch && metaMatch && shiftMatch) {
        e.preventDefault();
        shortcut.action();
        return;
      }
    }
  }, [shortcuts]);

  useEffect(() => {
    if (!enabled) return;
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enabled, handleKeyDown]);
}

// Hook for global Cmd+K and other app-wide shortcuts
export function useGlobalShortcuts({
  onOpenCommandPalette,
  onAddApplication,
}: {
  onOpenCommandPalette: () => void;
  onAddApplication?: () => void;
}) {
  const router = useRouter();

  const shortcuts: KeyboardShortcut[] = [
    // Cmd+K - Command Palette
    { key: 'k', ctrl: true, action: onOpenCommandPalette },
    // Cmd+N - New Application
    { key: 'n', ctrl: true, action: () => onAddApplication?.() },
    // G then D - Go to Dashboard (two-key sequence handled separately)
  ];

  useKeyboardShortcuts({ shortcuts });

  // Handle two-key sequences (g+letter)
  const [pendingG, setPendingG] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;

      if (e.key === 'g' && !e.ctrlKey && !e.metaKey) {
        setPendingG(true);
        setTimeout(() => setPendingG(false), 1000);
        return;
      }

      if (pendingG && !e.ctrlKey && !e.metaKey) {
        setPendingG(false);
        switch (e.key.toLowerCase()) {
          case 'd': router.push('/'); break;
          case 'a': router.push('/applications'); break;
          case 'n': router.push('/analytics'); break;
          case 'e': router.push('/emails'); break;
          case 's': router.push('/settings'); break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [pendingG, router]);
}

// Hook for list navigation with j/k
export function useListNavigation<T>({
  items,
  onSelect,
  enabled = true,
}: {
  items: T[];
  onSelect: (item: T) => void;
  enabled?: boolean;
}) {
  const [selectedIndex, setSelectedIndex] = useState(0);

  useEffect(() => {
    setSelectedIndex(0);
  }, [items.length]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    const target = e.target as HTMLElement;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;

    switch (e.key) {
      case 'j':
        e.preventDefault();
        setSelectedIndex(i => Math.min(i + 1, items.length - 1));
        break;
      case 'k':
        e.preventDefault();
        setSelectedIndex(i => Math.max(i - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (items[selectedIndex]) {
          onSelect(items[selectedIndex]);
        }
        break;
    }
  }, [items, selectedIndex, onSelect]);

  useEffect(() => {
    if (!enabled) return;
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enabled, handleKeyDown]);

  return { selectedIndex, setSelectedIndex };
}
