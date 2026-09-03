'use client';

import { useParams, useRouter } from 'next/navigation';
import { useApplication, useUpdateApplication, useUpdateApplicationStatus, useDeleteApplication, useApplicationEvents, useEvaluateFollowUp, useExtractActions } from '@/hooks/use-applications';
import type { ApplicationStatus } from '@/stores';
import type { FollowUpEvaluation, ExtractActionsResult } from '@/lib/api';
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
  Users,
  Phone,
  Upload,
  Paperclip,
  Bot,
  Copy,
  Zap,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ClipboardCheck,
  Shield,
  Workflow,
} from 'lucide-react';
import { useState, useMemo } from 'react';
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

function CollapsibleText({ text, maxLength = 300 }: { text: string; maxLength?: number }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const shouldTruncate = text.length > maxLength;

  if (!shouldTruncate) return <p className={styles.timelineCardDesc}>{text}</p>;

  return (
    <div className={styles.collapsibleTextContainer}>
      <p className={styles.timelineCardDesc}>
        {isExpanded ? text : `${text.slice(0, maxLength)}...`}
      </p>
      <button 
        className={styles.toggleTextBtn} 
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? 'Show less' : 'Show more'}
      </button>
    </div>
  );
}

export default function ApplicationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const applicationId = params.id as string;

  const { data: application, isLoading, error } = useApplication(applicationId);
  const { mutate: updateApplication } = useUpdateApplication();
  const { mutate: updateStatus } = useUpdateApplicationStatus();
  const { mutate: deleteApplication } = useDeleteApplication();
  const { data: events = [] } = useApplicationEvents(applicationId);
  const { mutate: evaluateFollowUp, isPending: isEvaluating } = useEvaluateFollowUp();
  const { mutate: extractActions, isPending: isExtracting } = useExtractActions();

  const [isEditing, setIsEditing] = useState(false);
  const [showStatusDropdown, setShowStatusDropdown] = useState(false);
  const [showEmailSource, setShowEmailSource] = useState(false);
  const [followUpResult, setFollowUpResult] = useState<FollowUpEvaluation | null>(null);
  const [extractResult, setExtractResult] = useState<ExtractActionsResult | null>(null);
  const [copied, setCopied] = useState(false);
  const [editForm, setEditForm] = useState({
    company: '',
    role: '',
    url: '',
    location: '',
    notes: '',
  });

  // Extract action_required events for the Actions panel
  const actionEvents = useMemo(() =>
    events.filter((e) => e.event_type === 'action_required'),
    [events]
  );

  const handleEvaluateFollowUp = () => {
    setFollowUpResult(null);
    evaluateFollowUp(applicationId, {
      onSuccess: (data) => setFollowUpResult(data),
      onError: () => setFollowUpResult({
        application_id: applicationId,
        should_follow_up: false,
        decision_reason: 'Failed to evaluate. Check API connection.',
        error: 'Request failed',
      }),
    });
  };

  const handleCopyDraft = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

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

            {/* Moved Notes from sidebar to here */}
            <div className={styles.mainNotesPanel}>
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

            {/* Timeline */}
            <div className={styles.timelineSection}>
              <div className={styles.timelineSectionHeader}>
                <h3 className={styles.sectionTitle}>Application Timeline</h3>
              </div>
              <div className={styles.timeline}>
                {/* Real events from API */}
                {events.length > 0 && events.map((event, idx) => (
                  <div key={event.id} className={`${styles.timelineItem} ${idx === events.length - 1 && application.status === 'applied' ? styles.timelineItemLast : ''}`}>
                    <span className={styles.timelineNode}>
                      <Check size={14} />
                    </span>
                    <div className={styles.timelineCard}>
                      <div className={styles.timelineCardHeader}>
                        <p className={styles.timelineCardTitle}>
                          {event.title || event.event_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                        </p>
                        <span className={styles.timelineCardDate}>
                          {formatDateShort(event.scheduled_at || event.created_at)}
                        </span>
                      </div>
                      {event.description && (
                        <div className={styles.timelineCardDescWrapper}>
                          <CollapsibleText text={event.description} />
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {/* Current status event (if not applied) */}
                {application.status !== 'applied' && events.length === 0 && (
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

                {/* Application submitted (always shown) */}
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

            {/* Email Source — shows original email context */}
            {(application.email_subject || application.email_snippet) && (
              <div className={styles.sidePanel}>
                <div className={styles.sidePanelHeader}>
                  <h3 className={styles.sidePanelTitle}>Email Source</h3>
                  <span className={styles.sidePanelTag}>GMAIL</span>
                </div>
                <div className={styles.quickInfoList}>
                  {application.email_subject && (
                    <div className={styles.quickInfoItem}>
                      <Mail size={14} />
                      <span style={{ fontWeight: 500 }}>{application.email_subject}</span>
                    </div>
                  )}
                  {application.email_from && (
                    <div className={styles.quickInfoItem}>
                      <Send size={14} />
                      <span style={{ opacity: 0.7, fontSize: '0.85rem' }}>{application.email_from}</span>
                    </div>
                  )}
                  {application.email_snippet && (
                    <p style={{
                      fontSize: '0.82rem',
                      lineHeight: 1.6,
                      opacity: 0.6,
                      margin: '4px 0 0 0',
                      padding: '0 4px',
                      overflowWrap: 'anywhere',
                      wordBreak: 'break-word',
                    }}>
                      {application.email_snippet.length > 300 
                        ? application.email_snippet.slice(0, 300) + '...'
                        : application.email_snippet
                      }
                    </p>
                  )}
                </div>
              </div>
            )}

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

            {/* AI Follow-Up Agent */}
            <div className={styles.sidePanel}>
              <div className={styles.sidePanelHeader}>
                <h3 className={styles.sidePanelTitle}>Follow-Up Agent</h3>
                <span className={styles.sidePanelTag}>AI AGENT</span>
              </div>
              <p className={styles.agentDesc}>
                Evaluate whether a follow-up is appropriate and generate a draft email.
              </p>
              <button
                id="evaluate-follow-up-btn"
                className={styles.agentBtn}
                onClick={handleEvaluateFollowUp}
                disabled={isEvaluating}
              >
                {isEvaluating ? (
                  <><Loader2 size={14} className={styles.spin} /> Evaluating…</>
                ) : (
                  <><Bot size={14} /> Evaluate Follow-Up</>
                )}
              </button>

              {followUpResult && (
                <div className={styles.agentResult}>
                  {/* Verdict */}
                  <div className={`${styles.agentVerdict} ${followUpResult.should_follow_up ? styles.verdictYes : styles.verdictNo}`}>
                    {followUpResult.should_follow_up
                      ? <><CheckCircle2 size={14} /> Follow-up recommended</>
                      : <><XCircle size={14} /> No follow-up needed</>
                    }
                  </div>

                  {/* Stats */}
                  {followUpResult.days_since_last_contact !== undefined && (
                    <div className={styles.agentStat}>
                      <Clock size={12} />
                      <span>{followUpResult.days_since_last_contact} days since last contact</span>
                    </div>
                  )}

                  {(followUpResult.risk_tier || followUpResult.needs_approval) && (
                    <div className={styles.agentMetaRow}>
                      {followUpResult.risk_tier && (
                        <span className={`${styles.riskPill} ${followUpResult.risk_tier === 'high' ? styles.riskHigh : styles.riskLow}`}>
                          <Shield size={11} /> {followUpResult.risk_tier} risk
                        </span>
                      )}
                      {followUpResult.needs_approval && (
                        <span className={styles.approvalPill}>Needs approval</span>
                      )}
                    </div>
                  )}

                  {/* Reason */}
                  <div className={styles.agentReason}>
                    <AlertTriangle size={12} />
                    <span>{followUpResult.decision_reason}</span>
                  </div>

                  {followUpResult.agent_run_id && (
                    <Link
                      href={`/agents?run=${followUpResult.agent_run_id}`}
                      className={styles.traceLink}
                    >
                      <Workflow size={12} /> View agent trace
                    </Link>
                  )}

                  {/* Draft */}
                  {followUpResult.email_draft && (
                    <div className={styles.draftSection}>
                      <div className={styles.draftHeader}>
                        <span className={styles.draftLabel}>Generated Draft</span>
                        <button
                          className={styles.copyBtn}
                          onClick={() => handleCopyDraft(followUpResult.email_draft!)}
                        >
                          {copied
                            ? <><Check size={12} /> Copied</>
                            : <><Copy size={12} /> Copy</>
                          }
                        </button>
                      </div>
                      <pre className={styles.draftBody}>{followUpResult.email_draft}</pre>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Extracted Actions (Agent A output) */}
            <div className={styles.sidePanel}>
              <div className={styles.sidePanelHeader}>
                <h3 className={styles.sidePanelTitle}>Extracted Actions</h3>
                <span className={styles.sidePanelTag}>AGENT A</span>
              </div>
              {actionEvents.length > 0 ? (
                <div className={styles.actionsList}>
                  {actionEvents.map((event) => {
                    const data = event.data || {};
                    const urgencyClass = data.urgency === 'high'
                      ? styles.urgencyHigh
                      : data.urgency === 'medium'
                        ? styles.urgencyMedium
                        : styles.urgencyLow;
                    return (
                      <div key={event.id} className={styles.actionItem}>
                        <div className={styles.actionItemHeader}>
                          <div className={styles.actionType}>
                            <Zap size={12} />
                            <span>{String(data.action_type || 'action').replace(/_/g, ' ')}</span>
                          </div>
                          <span className={`${styles.urgencyBadge} ${urgencyClass}`}>
                            {String(data.urgency || 'low').toUpperCase()}
                          </span>
                        </div>
                        {event.description && (
                          <p className={styles.actionReasoning}>{event.description}</p>
                        )}
                        {Boolean(data.source_text) && (
                          <p className={styles.actionSource}>&quot;{String(data.source_text)}&quot;</p>
                        )}
                        {Boolean(data.deadline) && (
                          <div className={styles.actionDeadline}>
                            <Calendar size={11} />
                            <span>Deadline: {formatDate(String(data.deadline))}</span>
                          </div>
                        )}
                        {data.confidence != null && (
                          <div className={styles.confidenceBar}>
                            <div className={styles.confidenceFill} style={{ width: `${Math.round(Number(data.confidence) * 100)}%` }} />
                            <span className={styles.confidenceLabel}>{Math.round(Number(data.confidence) * 100)}% confidence</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className={styles.emptyNotes}>
                  <ClipboardCheck size={16} style={{ opacity: 0.4 }} />
                  <span>No actions extracted yet.</span>
                  <button
                    id="extract-actions-btn"
                    className={styles.agentBtn}
                    onClick={() => {
                      setExtractResult(null);
                      extractActions(applicationId, {
                        onSuccess: (data) => setExtractResult(data),
                        onError: () => setExtractResult({
                          application_id: applicationId,
                          actions: [],
                          message: 'Failed to extract actions. Check API connection.',
                        }),
                      });
                    }}
                    disabled={isExtracting}
                    style={{ marginTop: '8px', width: '100%' }}
                  >
                    {isExtracting ? (
                      <><Loader2 size={14} className={styles.spin} /> Extracting…</>
                    ) : (
                      <><Zap size={14} /> Extract Actions</>
                    )}
                  </button>
                  {extractResult && (
                    <div className={styles.agentReason} style={{ marginTop: '8px' }}>
                      <AlertTriangle size={12} />
                      <span>{extractResult.message}</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Contacts */}
            <div className={styles.sidePanel}>
              <div className={styles.sidePanelHeader}>
                <h3 className={styles.sidePanelTitle}>Contacts</h3>
              </div>
              <div className={styles.quickInfoList}>
                <div className={styles.emptyNotes}>
                  <Users size={16} style={{ opacity: 0.4 }} />
                  <span>No contacts linked yet. Contacts are auto-created from email leads.</span>
                </div>
              </div>
            </div>

            {/* Documents */}
            <div className={styles.sidePanel}>
              <div className={styles.sidePanelHeader}>
                <h3 className={styles.sidePanelTitle}>Documents</h3>
                <span className={styles.sidePanelTag}>ATTACHMENTS</span>
              </div>
              <div className={styles.quickInfoList}>
                <div className={styles.emptyNotes}>
                  <Paperclip size={16} style={{ opacity: 0.4 }} />
                  <span>No documents attached. Coming soon.</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
