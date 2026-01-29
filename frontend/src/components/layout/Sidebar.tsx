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
  User
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { useAuthStore } from '@/stores';
import styles from './Sidebar.module.css';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: number;
}

const navItems: NavItem[] = [
  { 
    label: 'Dashboard', 
    href: '/', 
    icon: <LayoutDashboard size={20} /> 
  },
  { 
    label: 'Applications', 
    href: '/applications', 
    icon: <Briefcase size={20} />,
  },
  { 
    label: 'Kanban', 
    href: '/kanban', 
    icon: <Kanban size={20} /> 
  },
  { 
    label: 'Emails', 
    href: '/emails', 
    icon: <Mail size={20} /> 
  },
  { 
    label: 'Analytics', 
    href: '/analytics', 
    icon: <BarChart3 size={20} /> 
  },
];

const bottomNavItems: NavItem[] = [
  { 
    label: 'Settings', 
    href: '/settings', 
    icon: <Settings size={20} /> 
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);
  const { user, isAuthenticated, logout } = useAuthStore();

  useEffect(() => {
    setMounted(true);
  }, []);

  // Hide sidebar on public routes
  if (pathname === '/login' || pathname === '/auth/callback') {
    return null;
  }

  const handleLogout = async () => {
    try {
      // Call backend logout
      await fetch('http://localhost:8000/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch (e) {
      // Ignore errors
    }
    
    // Clear local state
    logout();
    router.push('/login');
  };

  return (
    <aside className={`${styles.sidebar} ${isCollapsed ? styles.collapsed : ''}`}>
      {/* Logo */}
      <div className={styles.logo}>
        <div className={styles.logoIcon}>
          <Rocket size={24} />
        </div>
        {!isCollapsed && <span className={styles.logoText}>Orbit</span>}
      </div>

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
                  {!isCollapsed && (
                    <>
                      <span className={styles.navLabel}>{item.label}</span>
                      {item.badge !== undefined && (
                        <span className={styles.badge}>{item.badge}</span>
                      )}
                    </>
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
                  <User size={16} />
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
              <LogOut size={18} />
            </button>
          </div>
        )}

        {/* Collapse Toggle */}
        <button 
          className={styles.collapseButton}
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
    </aside>
  );
}
