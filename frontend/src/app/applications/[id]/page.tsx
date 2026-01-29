'use client';

import { useParams, useRouter } from 'next/navigation';
import { useApplication, useUpdateApplication, useUpdateApplicationStatus, useDeleteApplication } from '@/hooks/use-applications';
import type { ApplicationStatus } from '@/stores';
import { 
  ArrowLeft, 
  ExternalLink, 
  Edit3, 
  Trash2, 
  Calendar,
  MapPin,
  DollarSign,
  Tag,
  Star,
  Clock,
  Building2,
  ChevronDown,
  Save,
  X
} from 'lucide-react';
import { useState } from 'react';
import Link from 'next/link';
import styles from './page.module.css';

const statusConfig: Record<ApplicationStatus, { label: string; color: string }> = {
  applied: { label: 'Applied', color: 'var(--status-applied)' },
  screening: { label: 'Screening', color: 'var(--status-screening)' },
  oa: { label: 'Online Assessment', color: 'var(--status-oa)' },
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
  return new Date(dateString).toLocaleDateString('en-US', { 
    month: 'long', 
    day: 'numeric',
    year: 'numeric'
  });
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
  }).format(amount);
}

export default function ApplicationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const applicationId = params.id as string;

  const { data: application, isLoading, error } = useApplication(applicationId);
  const { mutate: updateApplication } = useUpdateApplication();
  const { mutate: updateStatus } = useUpdateApplicationStatus();
  const { mutate: deleteApplication } = useDeleteApplication();
  
  const [isEditing, setIsEditing] = useState(false);
  const [showStatusDropdown, setShowStatusDropdown] = useState(false);
  const [editForm, setEditForm] = useState({
    company: '',
    role: '',
    url: '',
    location: '',
    notes: '',
  });

  if (isLoading) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.spinner}></div>
        <p>Loading application...</p>
      </div>
    );
  }

  if (error || !application) {
    return (
      <div className={styles.notFound}>
        <h1>Application not found</h1>
        <p>This application may have been deleted or does not exist.</p>
        <Link href="/applications" className={styles.backLink}>
          <ArrowLeft size={16} />
          Back to Applications
        </Link>
      </div>
    );
  }

  const handleDelete = () => {
    if (confirm(`Delete application for ${application.company}?`)) {
      deleteApplication(application.id, {
        onSuccess: () => router.push('/applications')
      });
    }
  };

  const handleStatusChange = (newStatus: ApplicationStatus) => {
    updateStatus({ id: application.id, status: newStatus });
    setShowStatusDropdown(false);
  };

  const startEditing = () => {
    setEditForm({
      company: application.company,
      role: application.role,
      url: application.url || '',
      location: application.location || '',
      notes: application.notes || '',
    });
    setIsEditing(true);
  };

  const saveEdits = () => {
    updateApplication({
      id: application.id,
      input: {
        company: editForm.company,
        role: editForm.role,
        url: editForm.url || undefined,
        location: editForm.location || undefined,
        notes: editForm.notes || undefined,
      }
    });
    setIsEditing(false);
  };

  const cancelEditing = () => {
    setIsEditing(false);
  };

  return (
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.header}>
        <Link href="/applications" className={styles.backButton}>
          <ArrowLeft size={18} />
          <span>Applications</span>
        </Link>

        <div className={styles.headerActions}>
          {isEditing ? (
            <>
              <button className={styles.cancelButton} onClick={cancelEditing}>
                <X size={16} />
                Cancel
              </button>
              <button className={styles.saveButton} onClick={saveEdits}>
                <Save size={16} />
                Save Changes
              </button>
            </>
          ) : (
            <>
              <button className={styles.editButton} onClick={startEditing}>
                <Edit3 size={16} />
                Edit
              </button>
              <button className={styles.deleteButton} onClick={handleDelete}>
                <Trash2 size={16} />
                Delete
              </button>
            </>
          )}
        </div>
      </header>

      <div className={styles.content}>
        {/* Main Info Card */}
        <div className={styles.mainCard}>
          <div className={styles.companyHeader}>
            <div className={styles.companyLogo}>
              <Building2 size={32} />
            </div>
            
            <div className={styles.companyInfo}>
              {isEditing ? (
                <>
                  <input
                    type="text"
                    value={editForm.company}
                    onChange={(e) => setEditForm({ ...editForm, company: e.target.value })}
                    className={styles.editInput}
                    placeholder="Company name"
                  />
                  <input
                    type="text"
                    value={editForm.role}
                    onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                    className={styles.editInputSmall}
                    placeholder="Role title"
                  />
                </>
              ) : (
                <>
                  <h1 className={styles.companyName}>{application.company}</h1>
                  <p className={styles.roleTitle}>{application.role}</p>
                </>
              )}
            </div>

            {/* Status Badge */}
            <div className={styles.statusWrapper}>
              <button 
                className={styles.statusBadge}
                style={{ '--status-color': statusConfig[application.status]?.color } as React.CSSProperties}
                onClick={() => setShowStatusDropdown(!showStatusDropdown)}
              >
                {statusConfig[application.status]?.label}
                <ChevronDown size={14} />
              </button>
              
              {showStatusDropdown && (
                <div className={styles.statusDropdown}>
                  {allStatuses.map((status) => (
                    <button
                      key={status}
                      className={`${styles.statusOption} ${status === application.status ? styles.active : ''}`}
                      onClick={() => handleStatusChange(status)}
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
          </div>

          {/* Priority */}
          <div className={styles.priority}>
            <span className={styles.priorityLabel}>Priority:</span>
            <div className={styles.priorityStars}>
              {Array.from({ length: 5 }).map((_, i) => (
                <Star 
                  key={i} 
                  size={16} 
                  className={i < application.priority ? styles.starFilled : styles.starEmpty}
                />
              ))}
            </div>
          </div>

          {/* Details Grid */}
          <div className={styles.detailsGrid}>
            <div className={styles.detailItem}>
              <Calendar size={16} />
              <div>
                <span className={styles.detailLabel}>Applied</span>
                <span className={styles.detailValue}>{formatDate(application.appliedDate)}</span>
              </div>
            </div>

            <div className={styles.detailItem}>
              <Clock size={16} />
              <div>
                <span className={styles.detailLabel}>Source</span>
                <span className={styles.detailValue}>{application.source}</span>
              </div>
            </div>

            {(application.location || isEditing) && (
              <div className={styles.detailItem}>
                <MapPin size={16} />
                <div>
                  <span className={styles.detailLabel}>Location</span>
                  {isEditing ? (
                    <input
                      type="text"
                      value={editForm.location}
                      onChange={(e) => setEditForm({ ...editForm, location: e.target.value })}
                      className={styles.editInputInline}
                      placeholder="Add location"
                    />
                  ) : (
                    <span className={styles.detailValue}>{application.location}</span>
                  )}
                </div>
              </div>
            )}

            {(application.salaryMin || application.salaryMax) && (
              <div className={styles.detailItem}>
                <DollarSign size={16} />
                <div>
                  <span className={styles.detailLabel}>Salary</span>
                  <span className={styles.detailValue}>
                    {application.salaryMin && application.salaryMax
                      ? `${formatCurrency(application.salaryMin)} - ${formatCurrency(application.salaryMax)}`
                      : formatCurrency(application.salaryMin || application.salaryMax || 0)}
                    /mo
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Tags */}
          {application.tags.length > 0 && (
            <div className={styles.tags}>
              <Tag size={16} />
              <div className={styles.tagList}>
                {application.tags.map((tag) => (
                  <span key={tag} className={styles.tag}>{tag}</span>
                ))}
              </div>
            </div>
          )}

          {/* URL */}
          {(application.url || isEditing) && (
            <div className={styles.urlSection}>
              {isEditing ? (
                <input
                  type="text"
                  value={editForm.url}
                  onChange={(e) => setEditForm({ ...editForm, url: e.target.value })}
                  className={styles.editInputFull}
                  placeholder="Job posting URL"
                />
              ) : (
                <a 
                  href={application.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className={styles.urlLink}
                >
                  <ExternalLink size={14} />
                  View Job Posting
                </a>
              )}
            </div>
          )}
        </div>

        {/* Notes Section */}
        <div className={styles.notesCard}>
          <h2>Notes</h2>
          {isEditing ? (
            <textarea
              value={editForm.notes}
              onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
              className={styles.notesTextarea}
              placeholder="Add notes about this application..."
              rows={6}
            />
          ) : (
            <div className={styles.notesContent}>
              {application.notes || (
                <span className={styles.emptyNotes}>
                  No notes yet. Click Edit to add notes.
                </span>
              )}
            </div>
          )}
        </div>

        {/* Timeline Section */}
        <div className={styles.timelineCard}>
          <h2>Timeline</h2>
          <div className={styles.timeline}>
            <div className={styles.timelineItem}>
              <div className={styles.timelineDot} style={{ backgroundColor: 'var(--status-applied)' }} />
              <div className={styles.timelineContent}>
                <span className={styles.timelineTitle}>Application Created</span>
                <span className={styles.timelineDate}>{formatDate(application.createdAt)}</span>
              </div>
            </div>
            
            {application.status !== 'applied' && (
              <div className={styles.timelineItem}>
                <div 
                  className={styles.timelineDot} 
                  style={{ backgroundColor: statusConfig[application.status].color }} 
                />
                <div className={styles.timelineContent}>
                  <span className={styles.timelineTitle}>
                    Status changed to {statusConfig[application.status].label}
                  </span>
                  <span className={styles.timelineDate}>{formatDate(application.updatedAt)}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
