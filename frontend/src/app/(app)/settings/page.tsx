'use client';

import { useAuthStore } from '@/stores';
import {
  User,
  Bell,
  Download,
  Trash2,
  Search,
  Shield,
  Palette,
} from 'lucide-react';
import styles from './page.module.css';

export default function SettingsPage() {
  const { user } = useAuthStore();

  return (
    <div className={styles.page}>
      {/* ── Header ────────────────────────── */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.pageTitle}>Settings</h1>
          <span className={styles.headerSep}>/</span>
          <span className={styles.headerMeta}>PREFERENCES</span>
        </div>
        <div className={styles.headerRight}>
          <div className={styles.searchWrapper}>
            <Search size={14} className={styles.searchIcon} />
            <input
              className={styles.searchInput}
              placeholder="Search settings..."
              type="text"
            />
          </div>
        </div>
      </div>

      {/* ── Scroll Area ───────────────────── */}
      <div className={styles.scrollArea}>
        <div className={styles.maxWidth}>

          {/* Profile Section */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div className={styles.sectionIcon}>
                <User size={16} />
              </div>
              <div>
                <h2 className={styles.sectionTitle}>Profile</h2>
                <p className={styles.sectionDesc}>Manage your account information</p>
              </div>
            </div>
            <div className={styles.sectionBody}>
              <div className={styles.field}>
                <label className={styles.fieldLabel}>Name</label>
                <input
                  type="text"
                  placeholder="Your name"
                  defaultValue={user?.name || ''}
                  disabled
                  className={styles.fieldInput}
                />
              </div>
              <div className={styles.field}>
                <label className={styles.fieldLabel}>Email</label>
                <input
                  type="email"
                  placeholder="your@email.com"
                  defaultValue={user?.email || ''}
                  disabled
                  className={styles.fieldInput}
                />
              </div>
            </div>
          </section>

          {/* Notifications */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div className={styles.sectionIcon}>
                <Bell size={16} />
              </div>
              <div>
                <h2 className={styles.sectionTitle}>Notifications</h2>
                <p className={styles.sectionDesc}>Control how you receive alerts</p>
              </div>
            </div>
            <div className={styles.sectionBody}>
              <div className={styles.toggleRow}>
                <div>
                  <span className={styles.toggleLabel}>Email reminders for upcoming interviews</span>
                  <span className={styles.toggleHint}>Get notified the day before</span>
                </div>
                <label className={styles.switch}>
                  <input type="checkbox" defaultChecked />
                  <span className={styles.slider} />
                </label>
              </div>
              <div className={styles.toggleRow}>
                <div>
                  <span className={styles.toggleLabel}>Weekly summary email</span>
                  <span className={styles.toggleHint}>Digest of your application activity</span>
                </div>
                <label className={styles.switch}>
                  <input type="checkbox" defaultChecked />
                  <span className={styles.slider} />
                </label>
              </div>
              <div className={styles.toggleRow}>
                <div>
                  <span className={styles.toggleLabel}>Ghost detection alerts</span>
                  <span className={styles.toggleHint}>Alert when no response after 14 days</span>
                </div>
                <label className={styles.switch}>
                  <input type="checkbox" />
                  <span className={styles.slider} />
                </label>
              </div>
            </div>
          </section>

          {/* Appearance */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div className={styles.sectionIcon}>
                <Palette size={16} />
              </div>
              <div>
                <h2 className={styles.sectionTitle}>Appearance</h2>
                <p className={styles.sectionDesc}>Customize the look and feel</p>
              </div>
            </div>
            <div className={styles.sectionBody}>
              <div className={styles.toggleRow}>
                <div>
                  <span className={styles.toggleLabel}>Theme</span>
                  <span className={styles.toggleHint}>Currently: Midnight Dark</span>
                </div>
                <span className={styles.readonlyTag}>DARK</span>
              </div>
            </div>
          </section>

          {/* Data */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div className={styles.sectionIcon}>
                <Shield size={16} />
              </div>
              <div>
                <h2 className={styles.sectionTitle}>Data &amp; Privacy</h2>
                <p className={styles.sectionDesc}>Manage your data and account</p>
              </div>
            </div>
            <div className={styles.sectionBody}>
              <div className={styles.dataActions}>
                <button className={styles.dataButton}>
                  <Download size={14} />
                  Export all data (JSON)
                </button>
                <button className={`${styles.dataButton} ${styles.danger}`}>
                  <Trash2 size={14} />
                  Delete all data
                </button>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
