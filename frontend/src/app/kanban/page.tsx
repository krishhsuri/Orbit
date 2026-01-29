'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Header } from '@/components/layout/Header';
import { useApplications, useUpdateApplicationStatus } from '@/hooks/use-applications';
import type { ApplicationStatus } from '@/stores';
import { 
  Building2, 
  ChevronDown,
  Sparkles,
  Clock,
  ExternalLink
} from 'lucide-react';
import styles from './page.module.css';

// Kanban column configuration
const columns: { status: ApplicationStatus; label: string; color: string; description: string }[] = [
  { status: 'applied', label: 'Applied', color: 'var(--status-applied)', description: 'Waiting for response' },
  { status: 'screening', label: 'Screening', color: 'var(--status-screening)', description: 'Recruiter reviewing' },
  { status: 'oa', label: 'OA', color: 'var(--status-oa)', description: 'Online assessment' },
  { status: 'interview', label: 'Interview', color: 'var(--status-interview)', description: 'Interview stage' },
  { status: 'offer', label: 'Offer 🎉', color: 'var(--status-offer)', description: 'Received offer' },
];

// Collapsed statuses shown at the bottom
const collapsedStatuses: { status: ApplicationStatus; label: string; color: string }[] = [
  { status: 'accepted', label: 'Accepted', color: 'var(--status-accepted)' },
  { status: 'rejected', label: 'Rejected', color: 'var(--status-rejected)' },
  { status: 'withdrawn', label: 'Withdrawn', color: 'var(--status-withdrawn)' },
  { status: 'ghosted', label: 'Ghosted', color: 'var(--status-ghosted)' },
];

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffDays = Math.ceil((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
  
  if (diffDays <= 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function KanbanPage() {
  const { data, isLoading, error } = useApplications();
  const { mutate: updateStatus } = useUpdateApplicationStatus();
  
  const [selectedCard, setSelectedCard] = useState<string | null>(null);

  const applications = data?.applications || [];

  const getByStatus = (status: ApplicationStatus) => {
    return applications.filter(app => app.status === status);
  };

  const handleStatusChange = (id: string, newStatus: ApplicationStatus) => {
    updateStatus({ id, status: newStatus });
    setSelectedCard(null);
  };

  // Get counts for collapsed statuses
  const collapsedCounts = collapsedStatuses.map(s => ({
    ...s,
    count: getByStatus(s.status).length
  }));

  if (isLoading) {
    return (
      <div className={styles.page}>
        <Header title="Kanban Board" subtitle="Loading..." showAddButton={true} />
        <div className={styles.loadingContainer}>
          <div className={styles.spinner}></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.page}>
        <Header title="Kanban Board" subtitle="Error" showAddButton={true} />
        <div className={styles.errorContainer}>
          <p>Failed to load board. Please try again.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <Header title="Kanban Board" subtitle="Applications auto-organize by status" showAddButton={true} />
      
      <div className={styles.content}>
        {/* AI Hint */}
        <div className={styles.aiHint}>
          <Sparkles size={16} />
          <span>
            <strong>Smart Kanban:</strong> Cards automatically move when AI detects status changes in your email.
            Connect Gmail to enable auto-updates.
          </span>
        </div>

        {/* Kanban Board */}
        <div className={styles.board}>
          {columns.map((column) => {
            const columnApps = getByStatus(column.status);
            
            return (
              <div key={column.status} className={styles.column}>
                {/* Column Header */}
                <div className={styles.columnHeader}>
                  <div className={styles.columnTitle}>
                    <span 
                      className={styles.columnDot}
                      style={{ backgroundColor: column.color }}
                    />
                    <span>{column.label}</span>
                    <span className={styles.columnCount}>{columnApps.length}</span>
                  </div>
                  <span className={styles.columnDescription}>{column.description}</span>
                </div>

                {/* Column Content */}
                <div className={styles.columnContent}>
                  {columnApps.map((app) => (
                    <div key={app.id} className={styles.kanbanCard}>
                      {/* Card Header */}
                      <div className={styles.cardHeader}>
                        <div className={styles.cardLogo}>
                          <Building2 size={16} />
                        </div>
                        <Link href={`/applications/${app.id}`} className={styles.cardInfo}>
                          <h4>{app.company}</h4>
                          <p>{app.role}</p>
                        </Link>
                      </div>

                      {/* Card Footer */}
                      <div className={styles.cardFooter}>
                        <span className={styles.cardDate}>
                          <Clock size={12} />
                          {formatDate(app.updatedAt)}
                        </span>
                        
                        {/* Quick Status Change */}
                        <div className={styles.statusWrapper}>
                          <button 
                            className={styles.moveButton}
                            onClick={() => setSelectedCard(selectedCard === app.id ? null : app.id)}
                          >
                            Move <ChevronDown size={12} />
                          </button>
                          
                          {selectedCard === app.id && (
                            <div className={styles.statusDropdown}>
                              {columns.map((col) => (
                                <button
                                  key={col.status}
                                  className={`${styles.statusOption} ${col.status === app.status ? styles.active : ''}`}
                                  onClick={() => handleStatusChange(app.id, col.status)}
                                  disabled={col.status === app.status}
                                >
                                  <span 
                                    className={styles.statusDot}
                                    style={{ backgroundColor: col.color }}
                                  />
                                  {col.label}
                                </button>
                              ))}
                              <div className={styles.dropdownDivider} />
                              {collapsedStatuses.map((col) => (
                                <button
                                  key={col.status}
                                  className={styles.statusOption}
                                  onClick={() => handleStatusChange(app.id, col.status)}
                                >
                                  <span 
                                    className={styles.statusDot}
                                    style={{ backgroundColor: col.color }}
                                  />
                                  {col.label}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Tags */}
                      {app.tags.length > 0 && (
                        <div className={styles.cardTags}>
                          {app.tags.slice(0, 2).map((tag) => (
                            <span key={tag} className={styles.tag}>{tag}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Empty State */}
                  {columnApps.length === 0 && (
                    <div className={styles.emptyColumn}>
                      <span>No applications</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Collapsed Statuses */}
        {collapsedCounts.some(s => s.count > 0) && (
          <div className={styles.collapsedSection}>
            <h3>Other Statuses</h3>
            <div className={styles.collapsedGrid}>
              {collapsedCounts.filter(s => s.count > 0).map((status) => (
                <div key={status.status} className={styles.collapsedItem}>
                  <span 
                    className={styles.collapsedDot}
                    style={{ backgroundColor: status.color }}
                  />
                  <span className={styles.collapsedLabel}>{status.label}</span>
                  <span className={styles.collapsedCount}>{status.count}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
