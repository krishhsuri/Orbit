'use client';

import { useState } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { useUIStore } from '@/stores';
import { useApplications, useUpdateApplicationStatus, useDeleteApplication } from '@/hooks/use-applications';
import type { ApplicationStatus } from '@/stores';
import {
  Search,
  Filter,
  Plus,
  MoreHorizontal,
  Briefcase,
  ChevronDown,
  Loader2,
} from 'lucide-react';
import styles from './page.module.css';

const statusConfig: Record<ApplicationStatus, { label: string; color: string }> = {
  applied: { label: 'APPLIED', color: 'var(--status-applied)' },
  screening: { label: 'SCREENING', color: 'var(--status-screening)' },
  oa: { label: 'OA', color: 'var(--status-oa)' },
  interview: { label: 'INTERVIEWING', color: 'var(--status-interview)' },
  offer: { label: 'OFFER', color: 'var(--status-offer)' },
  accepted: { label: 'ACCEPTED', color: 'var(--status-accepted)' },
  rejected: { label: 'REJECTED', color: 'var(--status-rejected)' },
  withdrawn: { label: 'WITHDRAWN', color: 'var(--status-withdrawn)' },
  ghosted: { label: 'GHOSTED', color: 'var(--status-ghosted)' },
};

const allStatuses: ApplicationStatus[] = [
  'applied', 'screening', 'oa', 'interview', 'offer', 'accepted', 'rejected', 'withdrawn', 'ghosted'
];

function formatDateMono(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { 
    month: 'short', 
    day: '2-digit',
    year: 'numeric'
  }).toUpperCase().replace(',', ',');
}

function getTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  const diffWeeks = Math.floor(diffDays / 7);

  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return `${diffWeeks}w ago`;
}

type TabFilter = 'all' | 'active' | 'archived';

export default function ApplicationsPage() {
  const { openAddModal } = useUIStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<TabFilter>('all');
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  const { data, isLoading, error } = useApplications({
    search: searchQuery || undefined,
  });

  const { mutate: updateStatus } = useUpdateApplicationStatus();
  const { mutate: deleteApplication } = useDeleteApplication();

  const applications = data?.applications || [];

  // Filter by tab
  const filteredApps = applications.filter((app) => {
    if (activeTab === 'active') {
      return !['rejected', 'withdrawn', 'ghosted'].includes(app.status);
    }
    if (activeTab === 'archived') {
      return ['rejected', 'withdrawn', 'ghosted'].includes(app.status);
    }
    return true;
  });

  const handleStatusChange = (id: string, newStatus: ApplicationStatus) => {
    updateStatus({ id, status: newStatus });
    setOpenDropdown(null);
  };

  return (
    <div className={styles.page}>
      {/* Header Bar */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.pageTitle}>Applications</h1>
          <span className={styles.headerSep}>/</span>
          <span className={styles.headerMeta}>ALL_VIEWS</span>
        </div>
        <div className={styles.headerRight}>
          <div className={styles.searchWrapper}>
            <Search size={14} className={styles.searchIcon} />
            <input
              type="text"
              placeholder="Filter by company, role..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={styles.searchInput}
            />
            <kbd className={styles.searchKbd}>/</kbd>
          </div>
          <div className={styles.headerDivider} />
          <button className={styles.displayButton}>
            <Filter size={14} />
            Display
          </button>
          <button className={styles.newButton} onClick={openAddModal}>
            <Plus size={14} />
            New
          </button>
        </div>
      </header>

      {/* Tabs */}
      <div className={styles.tabBar}>
        <div className={styles.tabs}>
          {(['all', 'active', 'archived'] as TabFilter[]).map((tab) => (
            <button
              key={tab}
              className={`${styles.tab} ${activeTab === tab ? styles.activeTab : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab === 'all' ? 'All Applications' : tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
        <span className={styles.recordCount}>{filteredApps.length} records</span>
      </div>

      {/* Table Header */}
      <div className={styles.tableHeader}>
        <div className={styles.colCompany}>
          <input type="checkbox" className={styles.checkbox} />
          <span>Company & Role</span>
        </div>
        <div className={styles.colStatus}>Status</div>
        <div className={styles.colDate}>Date Applied</div>
        <div className={styles.colUpdate}>Last Update</div>
        <div className={styles.colActions}>Actions</div>
      </div>

      {/* Table Body */}
      <div className={styles.tableBody}>
        {isLoading ? (
          <div className={styles.loadingState}>
            <Loader2 size={24} className={styles.spin} />
            <span>Loading applications...</span>
          </div>
        ) : error ? (
          <div className={styles.emptyState}>
            <p>Failed to load applications. Please refresh.</p>
          </div>
        ) : filteredApps.length === 0 ? (
          <div className={styles.emptyState}>
            <Briefcase size={40} className={styles.emptyIcon} />
            <h3>No applications found</h3>
            <p>
              {!searchQuery && activeTab === 'all'
                ? 'Start tracking your job search by adding your first application.'
                : 'Try adjusting your search or filters.'}
            </p>
            {!searchQuery && activeTab === 'all' && (
              <button className={styles.newButton} onClick={openAddModal}>
                <Plus size={14} />
                Add Application
              </button>
            )}
          </div>
        ) : (
          filteredApps.map((app) => (
            <Link
              key={app.id}
              href={`/applications/${app.id}`}
              className={styles.tableRow}
            >
              <div className={styles.colCompany}>
                <input
                  type="checkbox"
                  className={styles.checkbox}
                  onClick={(e) => e.stopPropagation()}
                />
                <div className={styles.companyCell}>
                  <div className={styles.avatar}>
                    {(app.company || '?')[0].toUpperCase()}
                  </div>
                  <div className={styles.companyInfo}>
                    <span className={styles.companyName}>{app.company}</span>
                    <span className={styles.roleName}>{app.role}</span>
                  </div>
                </div>
              </div>

              <div className={styles.colStatus} onClick={(e) => e.preventDefault()}>
                <div className={styles.statusWrapper}>
                  <button
                    className={styles.statusBadge}
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setOpenDropdown(openDropdown === app.id ? null : app.id);
                    }}
                  >
                    {statusConfig[app.status]?.label || app.status.toUpperCase()}
                  </button>

                  <AnimatePresence>
                    {openDropdown === app.id && (
                      <motion.div
                        className={styles.statusDropdown}
                        initial={{ opacity: 0, y: -5, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -5, scale: 0.95 }}
                        transition={{ duration: 0.1 }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        {allStatuses.map((status) => (
                          <button
                            key={status}
                            className={`${styles.statusOption} ${status === app.status ? styles.activeOption : ''}`}
                            onClick={(e) => {
                              e.preventDefault();
                              handleStatusChange(app.id, status);
                            }}
                          >
                            <span
                              className={styles.optionDot}
                              style={{ backgroundColor: statusConfig[status].color }}
                            />
                            {statusConfig[status].label}
                          </button>
                        ))}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>

              <div className={styles.colDate}>
                {formatDateMono(app.appliedDate)}
              </div>

              <div className={styles.colUpdate}>
                {getTimeAgo(app.updatedAt || app.appliedDate)}
              </div>

              <div className={styles.colActions}>
                <button
                  className={styles.moreButton}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                  }}
                >
                  <MoreHorizontal size={16} />
                </button>
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
