'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { Header } from '@/components/layout/Header';
import { useUIStore } from '@/stores';
import { useApplications, useUpdateApplicationStatus, useDeleteApplication } from '@/hooks/use-applications';
import { useListNavigation } from '@/hooks';
import { 
  Card,
  LoadingState,
  ErrorState,
  StatusBadge,
  Button,
  EmptyState,
  StaggerContainer,
  StaggerItem,
  ApplicationsSkeleton,
} from '@/components/ui';
import type { ApplicationStatus } from '@/stores';
import { 
  Search, 
  Filter,  
  ExternalLink,
  Star,
  Calendar,
  Building2,
  Trash2,
  ChevronDown,
  Plus,
  Briefcase,
  MapPin,
} from 'lucide-react';
import styles from './page.module.css';

// Status configuration
const statusConfig: Record<ApplicationStatus, { label: string; color: string }> = {
  applied: { label: 'Applied', color: 'var(--status-applied)' },
  screening: { label: 'Screening', color: 'var(--status-screening)' },
  oa: { label: 'OA', color: 'var(--status-oa)' },
  interview: { label: 'Interview', color: 'var(--status-interview)' },
  offer: { label: 'Offer', color: 'var(--status-offer)' },
  accepted: { label: 'Accepted', color: 'var(--status-accepted)' },
  rejected: { label: 'Rejected', color: 'var(--status-rejected)' },
  withdrawn: { label: 'Withdrawn', color: 'var(--status-withdrawn)' },
  ghosted: { label: 'Ghosted', color: 'var(--status-ghosted)' },
};

const allStatuses: ApplicationStatus[] = [
  'applied', 'screening', 'oa', 'interview', 'offer', 'accepted', 'rejected', 'withdrawn', 'ghosted'
];

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function getDaysAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffTime = Math.abs(now.getTime() - date.getTime());
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  return `${diffDays}d ago`;
}

export default function ApplicationsPage() {
  const { openAddModal } = useUIStore();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<ApplicationStatus | ''>('');
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  // Fetch data
  const { data, isLoading, error } = useApplications({
    status: selectedStatus || undefined,
    search: searchQuery || undefined,
  });

  const { mutate: updateStatus } = useUpdateApplicationStatus();
  const { mutate: deleteApplication } = useDeleteApplication();

  const applications = data?.applications || [];

  // Keyboard navigation
  const { selectedIndex } = useListNavigation({
    items: applications,
    onSelect: (app) => {
      window.location.href = `/applications/${app.id}`;
    },
    enabled: !openDropdown,
  });

  const handleStatusChange = (id: string, newStatus: ApplicationStatus) => {
    updateStatus({ id, status: newStatus });
    setOpenDropdown(null);
  };

  const handleDelete = (id: string) => {
    if (confirm('Are you sure you want to delete this application?')) {
      deleteApplication(id);
    }
  };

  if (isLoading) {
    return (
      <div className={styles.page}>
        <Header title="Applications" subtitle="Loading..." />
        <ApplicationsSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.page}>
        <Header title="Applications" subtitle="Error" />
        <div className={styles.content}>
          <ErrorState 
            message="Failed to load applications. Please try again." 
            onRetry={() => window.location.reload()}
          />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <Header 
        title="Applications" 
        subtitle={`${data?.meta.total || 0} total applications`}
        action={
          <Button onClick={openAddModal} leftIcon={<Plus size={16} />}>
            Add Application
          </Button>
        }
      />
      
      <div className={styles.content}>
        {/* Toolbar */}
        <motion.div 
          className={styles.toolbar}
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          <div className={styles.searchWrapper}>
            <Search size={16} className={styles.searchIcon} />
            <input
              type="text"
              placeholder="Search companies, roles..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={styles.searchInput}
            />
            {searchQuery && (
              <button 
                className={styles.clearSearch}
                onClick={() => setSearchQuery('')}
              >
                ×
              </button>
            )}
          </div>
          
          <div className={styles.filters}>
            <div className={styles.statusFilters}>
              <button 
                className={`${styles.statusChip} ${!selectedStatus ? styles.active : ''}`}
                onClick={() => setSelectedStatus('')}
              >
                All
              </button>
              {['applied', 'interview', 'offer', 'rejected'].map((status) => (
                <button
                  key={status}
                  className={`${styles.statusChip} ${selectedStatus === status ? styles.active : ''}`}
                  onClick={() => setSelectedStatus(status as ApplicationStatus)}
                  style={{ '--chip-color': statusConfig[status as ApplicationStatus].color } as React.CSSProperties}
                >
                  <span className={styles.chipDot} />
                  {statusConfig[status as ApplicationStatus].label}
                </button>
              ))}
            </div>
            
            <button className={styles.moreFiltersButton}>
              <Filter size={14} />
              More
            </button>
          </div>
        </motion.div>

        {/* Stats bar */}
        <div className={styles.statsBar}>
          <div className={styles.statPill}>
            <span className={styles.statValue}>{applications.filter(a => a.status === 'interview').length}</span>
            <span className={styles.statLabel}>Interviews</span>
          </div>
          <div className={styles.statPill}>
            <span className={styles.statValue}>{applications.filter(a => a.status === 'offer').length}</span>
            <span className={styles.statLabel}>Offers</span>
          </div>
          <div className={styles.statPill}>
            <span className={styles.statValue}>
              {applications.length > 0 
                ? Math.round((applications.filter(a => ['interview', 'offer', 'accepted'].includes(a.status)).length / applications.length) * 100)
                : 0}%
            </span>
            <span className={styles.statLabel}>Response Rate</span>
          </div>
        </div>

        {/* Applications List */}
        <StaggerContainer className={styles.list}>
          <AnimatePresence mode="popLayout">
            {applications.map((app, index) => (
              <StaggerItem key={app.id}>
                <motion.div 
                  className={`${styles.applicationCard} ${index === selectedIndex ? styles.selected : ''}`}
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.15 }}
                >
                  {/* Company Logo */}
                  <div className={styles.companyLogo}>
                    <Building2 size={18} />
                  </div>
                  
                  {/* Info - Clickable */}
                  <Link href={`/applications/${app.id}`} className={styles.cardInfo}>
                    <div className={styles.cardHeader}>
                      <h3 className={styles.companyName}>{app.company}</h3>
                      <div className={styles.priorityStars}>
                        {Array.from({ length: 5 }).map((_, i) => (
                          <Star 
                            key={i} 
                            size={10} 
                            className={i < app.priority ? styles.starFilled : styles.starEmpty}
                          />
                        ))}
                      </div>
                    </div>
                    <p className={styles.roleTitle}>{app.role}</p>
                    <div className={styles.cardMeta}>
                      <span className={styles.metaItem}>
                        <Calendar size={11} />
                        {formatDate(app.appliedDate)}
                      </span>
                      {app.location && (
                        <span className={styles.metaItem}>
                          <MapPin size={11} />
                          {app.location}
                        </span>
                      )}
                      <span className={styles.metaDaysAgo}>{getDaysAgo(app.appliedDate)}</span>
                    </div>
                  </Link>
                  
                  {/* Tags */}
                  <div className={styles.tags}>
                    {app.tags.slice(0, 2).map((tag) => (
                      <span key={tag} className={styles.tag}>{tag}</span>
                    ))}
                    {app.tags.length > 2 && (
                      <span className={styles.tagMore}>+{app.tags.length - 2}</span>
                    )}
                  </div>
                  
                  {/* Status Dropdown */}
                  <div className={styles.statusWrapper}>
                    <button 
                      className={styles.statusBadge}
                      style={{ '--status-color': statusConfig[app.status]?.color } as React.CSSProperties}
                      onClick={() => setOpenDropdown(openDropdown === app.id ? null : app.id)}
                    >
                      <span className={styles.statusDot} />
                      {statusConfig[app.status]?.label}
                      <ChevronDown size={12} className={styles.statusChevron} />
                    </button>
                    
                    <AnimatePresence>
                      {openDropdown === app.id && (
                        <motion.div 
                          className={styles.statusDropdown}
                          initial={{ opacity: 0, y: -5, scale: 0.95 }}
                          animate={{ opacity: 1, y: 0, scale: 1 }}
                          exit={{ opacity: 0, y: -5, scale: 0.95 }}
                          transition={{ duration: 0.1 }}
                        >
                          {allStatuses.map((status) => (
                            <button
                              key={status}
                              className={`${styles.statusOption} ${status === app.status ? styles.active : ''}`}
                              onClick={() => handleStatusChange(app.id, status)}
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
                  
                  {/* Actions */}
                  <div className={styles.cardActions}>
                    {app.url && (
                      <a 
                        href={app.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className={styles.actionButton}
                        title="Open job posting"
                      >
                        <ExternalLink size={14} />
                      </a>
                    )}
                    <button 
                      className={`${styles.actionButton} ${styles.deleteButton}`}
                      title="Delete"
                      onClick={() => handleDelete(app.id)}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </motion.div>
              </StaggerItem>
            ))}
          </AnimatePresence>
        </StaggerContainer>

        {/* Empty State */}
        {applications.length === 0 && (
          <EmptyState
            icon={<Briefcase size={48} />}
            title="No applications found"
            description={
              !searchQuery && !selectedStatus 
                ? "Start tracking your job search by adding your first application."
                : "Try adjusting your search or filters."
            }
            action={!searchQuery && !selectedStatus ? {
              label: 'Add Application',
              onClick: openAddModal,
            } : undefined}
          />
        )}

        {/* Keyboard hint */}
        {applications.length > 0 && (
          <div className={styles.keyboardHint}>
            <kbd>j</kbd><kbd>k</kbd> to navigate • <kbd>Enter</kbd> to open
          </div>
        )}
      </div>
    </div>
  );
}
