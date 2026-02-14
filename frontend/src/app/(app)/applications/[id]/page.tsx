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
  X,
  Check,
  Mail,
  FileText,
  Send,
  Loader2,
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
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatDateShort(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  }).toUpperCase();
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
        <Loader2 className={styles.spin} size={20} />
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
        onSuccess: () => router.push('/applications'),
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
      },
    });
    setIsEditing(false);
  };

  const cancelEditing = () => {
    setIsEditing(false);
  };

  return (
    <div className={styles.page}>
      {/* ── Header ──────────────────────────── */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <Link href="/applications" className={styles.backButton}>
            <ArrowLeft size={14} />
            Back
          </Link>
          <span className={styles.headerSep}>/</span>
          <div className={styles.headerCompany}>
            <div className={styles.headerIcon}>
              {application.company.charAt(0)}
            </div>
            <h1 className={styles.headerTitle}>
              {application.company} - {application.role}
            </h1>
          </div>
          <span className={styles.headerTag}>
            APP-{application.id.slice(-4).toUpperCase()}
          </span>
        </div>

        <div className={styles.headerActions}>
          {isEditing ? (
            <>
              <button className={styles.cancelBtn} onClick={cancelEditing}>
                <X size={14} /> Cancel
              </button>
              <button className={styles.saveBtn} onClick={saveEdits}>
                <Save size={14} /> Save Changes
              </button>
            </>
          ) : (
            <>
              <button className={styles.editBtn} onClick={startEditing}>
                <Edit3 size={14} /> Edit
              </button>
              <button className={styles.deleteBtn} onClick={handleDelete}>
                <Trash2 size={14} /> Delete
              </button>
            </>
          )}
        </div>
      </header>

      {/* ── Scrollable Content ──────────────── */}
      <div className={styles.scrollArea}>
        <div className={styles.layoutGrid}>
          {/* ── Left Column ─────────────────── */}
          <div className={styles.leftColumn}>
            {/* Info Card */}
            <div className={styles.infoCard}>
              <div className={styles.infoHeader}>
                <div className={styles.infoHeaderLeft}>
                  <div className={styles.companyLogo}>
                    <Building2 size={24} />
                  </div>
                  <div>
                    {isEditing ? (
                      <>
                        <input
                          type="text"
                          value={editForm.role}
                          onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                          className={styles.editInput}
                          placeholder="Role title"
                        />
                        <input
                          type="text"
                          value={editForm.company}
                          onChange={(e) => setEditForm({ ...editForm, company: e.target.value })}
                          className={styles.editInputSmall}
                          placeholder="Company name"
                        />
                      </>
                    ) : (
                      <>
                        <h2 className={styles.infoRole}>{application.role}</h2>
                        <p className={styles.infoCompanyMeta}>
                          {application.company}
                          {application.location && ` • ${application.location}`}
                          {' • Full-time'}
                        </p>
                      </>
                    )}
                  </div>
                </div>

                {/* Status Badge */}
                <div className={styles.statusWrapper}>
                  <button
                    className={styles.statusBadge}
                    onClick={() => setShowStatusDropdown(!showStatusDropdown)}
                  >
                    {statusConfig[application.status]?.label.toUpperCase()}
                    <ChevronDown size={12} />
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

              {/* Metadata Grid */}
              <div className={styles.metaGrid}>
                {(application.salaryMin || application.salaryMax) && (
                  <div className={styles.metaItem}>
                    <p className={styles.metaLabel}>Salary Range</p>
                    <p className={styles.metaValue}>
                      {application.salaryMin && application.salaryMax
                        ? `${formatCurrency(application.salaryMin)} - ${formatCurrency(application.salaryMax)}`
                        : formatCurrency(application.salaryMin || application.salaryMax || 0)}
                    </p>
                  </div>
                )}
                <div className={styles.metaItem}>
                  <p className={styles.metaLabel}>Applied Date</p>
                  <p className={styles.metaValue}>{formatDate(application.appliedDate)}</p>
                </div>
                <div className={styles.metaItem}>
                  <p className={styles.metaLabel}>Source</p>
                  <p className={styles.metaValue}>{application.source}</p>
                </div>
                {application.location && (
                  <div className={styles.metaItem}>
                    <p className={styles.metaLabel}>Location</p>
                    <p className={styles.metaValue}>{application.location}</p>
                  </div>
                )}
              </div>

              {/* URL */}
              {application.url && !isEditing && (
                <div className={styles.urlRow}>
                  <a
                    href={application.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={styles.urlLink}
                  >
                    <ExternalLink size={12} />
                    View Job Posting
                  </a>
                </div>
              )}
              {isEditing && (
                <div className={styles.urlRow}>
                  <input
                    type="text"
                    value={editForm.url}
                    onChange={(e) => setEditForm({ ...editForm, url: e.target.value })}
                    className={styles.editInputFull}
                    placeholder="Job posting URL"
                  />
                </div>
              )}

              {/* Tags */}
              {application.tags && application.tags.length > 0 && (
                <div className={styles.tagRow}>
                  {application.tags.map((tag) => (
                    <span key={tag} className={styles.tag}>{tag}</span>
                  ))}
                </div>
              )}

              {/* Priority */}
              <div className={styles.priorityRow}>
                <span className={styles.metaLabel}>Priority</span>
                <div className={styles.priorityStars}>
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star
                      key={i}
                      size={14}
                      className={i < application.priority ? styles.starFilled : styles.starEmpty}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Timeline */}
            <div className={styles.timelineSection}>
              <div className={styles.timelineSectionHeader}>
                <h3 className={styles.sectionTitle}>Application Timeline</h3>
              </div>
              <div className={styles.timeline}>
                {/* Current status event */}
                {application.status !== 'applied' && (
                  <div className={styles.timelineItem}>
                    <span className={styles.timelineNode}>
                      <Check size={14} />
                    </span>
                    <div className={styles.timelineCard}>
                      <div className={styles.timelineCardHeader}>
                        <p className={styles.timelineCardTitle}>
                          Status: {statusConfig[application.status].label}
                        </p>
                        <span className={styles.timelineCardDate}>
                          {formatDateShort(application.updatedAt)}
                        </span>
                      </div>
                      <p className={styles.timelineCardDesc}>
                        Application moved to {statusConfig[application.status].label.toLowerCase()} stage.
                      </p>
                    </div>
                  </div>
                )}

                {/* Application submitted */}
                <div className={`${styles.timelineItem} ${styles.timelineItemLast}`}>
                  <span className={styles.timelineNodeMuted}>
                    <Mail size={14} />
                  </span>
                  <div className={styles.timelineSimple}>
                    <p className={styles.timelineSimpleText}>
                      Application submitted via {application.source}
                    </p>
                    <span className={styles.timelineSimpleDate}>
                      {formatDateShort(application.appliedDate)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* ── Right Column ────────────────── */}
          <div className={styles.rightColumn}>
            {/* Notes */}
            <div className={styles.sidePanel}>
              <div className={styles.sidePanelHeader}>
                <h3 className={styles.sidePanelTitle}>Notes</h3>
                <span className={styles.sidePanelTag}>PRIVATE</span>
              </div>
              {isEditing ? (
                <textarea
                  value={editForm.notes}
                  onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                  className={styles.notesTextarea}
                  placeholder="Jot down quick thoughts..."
                  rows={5}
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

            {/* Quick Info */}
            <div className={styles.sidePanel}>
              <h3 className={styles.sidePanelTitle}>Quick Info</h3>
              <div className={styles.quickInfoList}>
                <div className={styles.quickInfoItem}>
                  <Calendar size={14} />
                  <span>Applied {formatDate(application.appliedDate)}</span>
                </div>
                <div className={styles.quickInfoItem}>
                  <Clock size={14} />
                  <span>Last updated {formatDate(application.updatedAt)}</span>
                </div>
                {application.location && (
                  <div className={styles.quickInfoItem}>
                    <MapPin size={14} />
                    <span>{application.location}</span>
                  </div>
                )}
                {application.url && (
                  <div className={styles.quickInfoItem}>
                    <ExternalLink size={14} />
                    <a
                      href={application.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={styles.quickInfoLink}
                    >
                      Job posting
                    </a>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
