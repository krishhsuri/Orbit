'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Header } from '@/components/layout/Header';
import { useUIStore } from '@/stores';
import { useApplications, useUpdateApplicationStatus, useDeleteApplication } from '@/hooks/use-applications';
import type { ApplicationStatus } from '@/stores';
import { 
  Search, 
  Filter,  
  ExternalLink,
  Star,
  Calendar,
  Building2,
  Trash2,
  ChevronDown
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
  return `${diffDays} days ago`;
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
        <div className={styles.loadingContainer}>
          <div className={styles.spinner}></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.page}>
        <Header title="Applications" subtitle="Error" />
        <div className={styles.errorContainer}>
          <p>Failed to load applications. Please try again.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <Header title="Applications" subtitle={`${data?.meta.total || 0} total`} />
      
      <div className={styles.content}>
        {/* Toolbar */}
        <div className={styles.toolbar}>
          <div className={styles.searchWrapper}>
            <Search size={16} className={styles.searchIcon} />
            <input
              type="text"
              placeholder="Search by company or role..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={styles.searchInput}
            />
          </div>
          
          <div className={styles.filters}>
            <select 
              className={styles.filterSelect}
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value as ApplicationStatus | '')}
            >
              <option value="">All Status</option>
              {allStatuses.map((status) => (
                <option key={status} value={status}>{statusConfig[status].label}</option>
              ))}
            </select>
            
            <button className={styles.filterButton}>
              <Filter size={16} />
              More Filters
            </button>
          </div>
        </div>

        {/* Applications List */}
        <div className={styles.list}>
          {applications.map((app) => (
            <div key={app.id} className={styles.applicationCard}>
              <div className={styles.cardMain}>
                {/* Company Logo Placeholder */}
                <div className={styles.companyLogo}>
                  <Building2 size={20} />
                </div>
                
                {/* Info - Clickable to detail page */}
                <Link href={`/applications/${app.id}`} className={styles.cardInfo}>
                  <div className={styles.cardHeader}>
                    <h3 className={styles.companyName}>{app.company}</h3>
                    <div className={styles.priorityStars}>
                      {Array.from({ length: 5 }).map((_, i) => (
                        <Star 
                          key={i} 
                          size={12} 
                          className={i < app.priority ? styles.starFilled : styles.starEmpty}
                        />
                      ))}
                    </div>
                  </div>
                  <p className={styles.roleTitle}>{app.role}</p>
                  <div className={styles.cardMeta}>
                    <span className={styles.metaItem}>
                      <Calendar size={12} />
                      {formatDate(app.appliedDate)} ({getDaysAgo(app.appliedDate)})
                    </span>
                    <span className={styles.metaItem}>via {app.source}</span>
                  </div>
                </Link>
                
                {/* Tags */}
                <div className={styles.tags}>
                  {app.tags.map((tag) => (
                    <span key={tag} className={styles.tag}>{tag}</span>
                  ))}
                </div>
                
                {/* Status Badge with Dropdown */}
                <div className={styles.statusWrapper}>
                  <button 
                    className={styles.statusBadge}
                    style={{ '--status-color': statusConfig[app.status]?.color } as React.CSSProperties}
                    onClick={() => setOpenDropdown(openDropdown === app.id ? null : app.id)}
                  >
                    {statusConfig[app.status]?.label || app.status}
                    <ChevronDown size={14} />
                  </button>
                  
                  {openDropdown === app.id && (
                    <div className={styles.statusDropdown}>
                      {allStatuses.map((status) => (
                        <button
                          key={status}
                          className={`${styles.statusOption} ${status === app.status ? styles.active : ''}`}
                          onClick={() => handleStatusChange(app.id, status)}
                        >
                          <span 
                            className={styles.statusDot}
                            style={{ backgroundColor: statusConfig[status].color }}
                          />
                          {statusConfig[status].label}
                        </button>
                      ))}
                    </div>
                  )}
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
                      <ExternalLink size={16} />
                    </a>
                  )}
                  <button 
                    className={`${styles.actionButton} ${styles.deleteButton}`}
                    title="Delete application"
                    onClick={() => handleDelete(app.id)}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Empty State */}
        {applications.length === 0 && (
          <div className={styles.emptyState}>
            <p>No applications found</p>
            <span>
              {!searchQuery && !selectedStatus 
                ? 'Click "Add Application" to get started!'
                : 'Try adjusting your search or filters'}
            </span>
            {!searchQuery && !selectedStatus && (
              <button className={styles.emptyAddButton} onClick={openAddModal}>
                Add Your First Application
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
