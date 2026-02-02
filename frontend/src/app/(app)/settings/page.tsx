'use client';

import { Header } from '@/components/layout/Header';
import { useAuthStore } from '@/stores';
import { User, Tag, Bell, Download, Trash2 } from 'lucide-react';
import styles from './page.module.css';

export default function SettingsPage() {
  const { user } = useAuthStore();

  return (
    <div className={styles.page}>
      <Header title="Settings" showAddButton={false} />
      
      <div className={styles.content}>
        <div className={styles.sections}>
          {/* Profile Section */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <User size={20} />
              <h2>Profile</h2>
            </div>
            <div className={styles.sectionContent}>
              <div className={styles.field}>
                <label>Name</label>
                <input 
                  type="text" 
                  placeholder="Your name" 
                  defaultValue={user?.name || ''} 
                  disabled 
                />
              </div>
              <div className={styles.field}>
                <label>Email</label>
                <input 
                  type="email" 
                  placeholder="your@email.com" 
                  defaultValue={user?.email || ''} 
                  disabled 
                />
              </div>
            </div>
          </section>

          {/* Notifications Section */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <Bell size={20} />
              <h2>Notifications</h2>
            </div>
            <div className={styles.sectionContent}>
              <div className={styles.toggle}>
                <span>Email reminders for upcoming interviews</span>
                <input type="checkbox" defaultChecked />
              </div>
              <div className={styles.toggle}>
                <span>Weekly summary email</span>
                <input type="checkbox" defaultChecked />
              </div>
              <div className={styles.toggle}>
                <span>Ghost detection alerts</span>
                <input type="checkbox" />
              </div>
            </div>
          </section>

          {/* Data Section */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <Download size={20} />
              <h2>Data</h2>
            </div>
            <div className={styles.sectionContent}>
              <button className={styles.dataButton}>
                <Download size={16} />
                Export all data (JSON)
              </button>
              <button className={`${styles.dataButton} ${styles.danger}`}>
                <Trash2 size={16} />
                Delete all data
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
