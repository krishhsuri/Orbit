'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { 
  LayoutDashboard, 
  Briefcase, 
  BarChart3, 
  Settings,
  Rocket,
  Kanban,
  Mail,
  ChevronLeft,
  ChevronRight,
  LogOut,
  User,
  Command,
  Plus,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore, useUIStore } from '@/stores';
import styles from './Sidebar.module.css';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: number;
  shortcut?: string;
}

const navItems: NavItem[] = [
  { 
    label: 'Dashboard', 
    href: '/', 
    icon: <LayoutDashboard size={18} />,
    shortcut: 'G D',
  },
  { 
    label: 'Applications', 
    href: '/applications', 
    icon: <Briefcase size={18} />,
    shortcut: 'G A',
  },
  { 
    label: 'Kanban', 
    href: '/kanban', 
    icon: <Kanban size={18} />,
    shortcut: 'G K',
  },
  { 
    label: 'Emails', 
    href: '/emails', 
    icon: <Mail size={18} />,
    shortcut: 'G E',
  },
  { 
    label: 'Analytics', 
    href: '/analytics', 
    icon: <BarChart3 size={18} />,
    shortcut: 'G N',
  },
];

const bottomNavItems: NavItem[] = [
  { 
    label: 'Settings', 
    href: '/settings', 
    icon: <Settings size={18} />,
    shortcut: 'G S',
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);
  const { user, isAuthenticated, logout } = useAuthStore();
  const { openCommandPalette, openAddModal } = useUIStore();

  useEffect(() => {
    setMounted(true);
  }, []);

  // Hide sidebar on public routes
  if (pathname === '/login' || pathname === '/auth/callback') {
    return null;
  }

  const handleLogout = async () => {
    try {
      await fetch('http://localhost:8000/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch (e) {
      // Ignore errors
    }
    logout();
    router.push('/login');
  };

  return (
    <motion.aside 
      className={`${styles.sidebar} ${isCollapsed ? styles.collapsed : ''}`}
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Logo */}
      <div className={styles.logo}>
        <div className={styles.logoIcon}>
          <Rocket size={20} />
        </div>
        <AnimatePresence>
          {!isCollapsed && (
            <motion.span 
              className={styles.logoText}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.15 }}
            >
              Orbit
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* Quick Actions */}
      {!isCollapsed && (
        <div className={styles.quickActions}>
          <button 
            className={styles.searchButton}
            onClick={openCommandPalette}
          >
            <Command size={14} />
            <span>Search...</span>
            <kbd>⌘K</kbd>
          </button>
          <button 
            className={styles.newButton}
            onClick={openAddModal}
          >
            <Plus size={16} />
          </button>
        </div>
      )}

      {/* Main Navigation */}
      <nav className={styles.nav}>
        <ul className={styles.navList}>
          {navItems.map((item) => {
            const isActive = pathname === item.href || 
              (item.href !== '/' && pathname.startsWith(item.href));
            
            return (
              <li key={item.href}>
                <Link 
                  href={item.href}
                  className={`${styles.navItem} ${isActive ? styles.active : ''}`}
                  title={isCollapsed ? item.label : undefined}
                >
                  <span className={styles.navIcon}>{item.icon}</span>
                  <AnimatePresence>
                    {!isCollapsed && (
                      <motion.div 
                        className={styles.navContent}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.1 }}
                      >
                        <span className={styles.navLabel}>{item.label}</span>
                        {item.shortcut && (
                          <span className={styles.navShortcut}>{item.shortcut}</span>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                  {isActive && (
                    <motion.div 
                      className={styles.activeIndicator}
                      layoutId="activeIndicator"
                      transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                    />
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Bottom Navigation */}
      <div className={styles.bottomNav}>
        <ul className={styles.navList}>
          {bottomNavItems.map((item) => {
            const isActive = pathname === item.href;
            
            return (
              <li key={item.href}>
                <Link 
                  href={item.href}
                  className={`${styles.navItem} ${isActive ? styles.active : ''}`}
                  title={isCollapsed ? item.label : undefined}
                >
                  <span className={styles.navIcon}>{item.icon}</span>
                  {!isCollapsed && <span className={styles.navLabel}>{item.label}</span>}
                </Link>
              </li>
            );
          })}
        </ul>

        {/* User Profile & Logout */}
        {mounted && isAuthenticated && user && (
          <div className={styles.userSection}>
            <div className={styles.userInfo} title={user.email}>
              {user.avatar_url ? (
                <img 
                  src={user.avatar_url} 
                  alt={user.name || 'User'} 
                  className={styles.userAvatar}
                />
              ) : (
                <div className={styles.userAvatarPlaceholder}>
                  <User size={14} />
                </div>
              )}
              {!isCollapsed && (
                <div className={styles.userDetails}>
                  <span className={styles.userName}>{user.name || 'User'}</span>
                  <span className={styles.userEmail}>{user.email}</span>
                </div>
              )}
            </div>
            <button 
              onClick={handleLogout}
              className={styles.logoutButton}
              title="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        )}

        {/* Collapse Toggle */}
        <button 
          className={styles.collapseButton}
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>
    </motion.aside>
  );
}
