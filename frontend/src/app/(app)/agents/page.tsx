'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Zap,
  Mail,
  Clock,
  Calendar,
  Copy,
  Check,
  X,
  ExternalLink,
  Loader2,
  Inbox,
  ClipboardCheck,
  Bot,
  RefreshCw,
  Shield,
  FileText,
  Code,
  MessageSquare,
  AlertTriangle,
} from 'lucide-react';
import { useAgentActions, useAgentFollowUps, useDismissFollowUp, useTriggerScan } from '@/hooks/use-agents';
import styles from './page.module.css';

function formatDate(d: string | null): string {
  if (!d || d === 'None') return '—';
  try {
    return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return d;
  }
}

function getRelativeTime(dateStr: string | null): string {
  if (!dateStr || dateStr === 'None') return '';
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
  } catch {
    return '';
  }
}

function getActionIcon(actionType: string) {
  switch (actionType) {
    case 'online_assessment': return <FileText size={12} />;
    case 'coding_test': return <Code size={12} />;
    case 'interview_scheduling': return <Calendar size={12} />;
    case 'document_upload': return <ClipboardCheck size={12} />;
    case 'general_response_required': return <MessageSquare size={12} />;
    default: return <Zap size={12} />;
  }
}

export default function AgentsPage() {
  const { data: actionsData, isLoading: actionsLoading } = useAgentActions();
  const { data: followUpsData, isLoading: followUpsLoading } = useAgentFollowUps();
  const { mutate: dismissFollowUp } = useDismissFollowUp();
  const { mutate: triggerScan, isPending: isScanning } = useTriggerScan();
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const actions = actionsData?.actions || [];
  const followUps = followUpsData?.follow_ups || [];
  const lastScan = followUpsData?.last_scan;

  const confirmedActions = actions.filter(a => !a.needs_review);
  const reviewActions = actions.filter(a => a.needs_review);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.pageTitle}>AI Agents</h1>
          <span className={styles.headerSep}>/</span>
          <span className={styles.headerMeta}>AUTOMATED INSIGHTS</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {lastScan && (
            <span className={styles.lastScan}>
              <span className={styles.lastScanDot} />
              Last scan: {getRelativeTime(lastScan)}
            </span>
          )}
          {!lastScan && !followUpsLoading && (
            <button
              className={styles.scanBtn}
              onClick={() => triggerScan()}
              disabled={isScanning}
            >
              {isScanning ? (
                <><Loader2 size={12} className={styles.spin} /> Scanning…</>
              ) : (
                <><RefreshCw size={12} /> Run Initial Scan</>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className={styles.scrollArea}>
        <div className={styles.contentGrid}>
          {/* ── Left Panel: Follow-Up Queue (Agent B) ──────── */}
          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <h3 className={styles.panelTitle}>
                <Mail size={15} />
                Follow-Up Queue
              </h3>
              <span className={styles.panelTag}>AGENT B</span>
            </div>

            <div className={styles.panelBody}>
              {followUpsLoading ? (
                <div className={styles.loadingState}>
                  <Loader2 size={16} className={styles.spin} />
                  <span>Loading evaluations…</span>
                </div>
              ) : !lastScan ? (
                <div className={styles.scanBanner}>
                  <div className={styles.emptyIcon}>
                    <Bot size={22} />
                  </div>
                  <p className={styles.scanBannerText}>
                    Agent B hasn&apos;t scanned your applications yet.<br />
                    Run an initial scan to evaluate which applications need follow-ups.
                  </p>
                  <button
                    className={styles.scanBannerBtn}
                    onClick={() => triggerScan()}
                    disabled={isScanning}
                  >
                    {isScanning ? (
                      <><Loader2 size={14} className={styles.spin} /> Scanning all applications…</>
                    ) : (
                      <><Bot size={14} /> Run Agent B Scan</>
                    )}
                  </button>
                </div>
              ) : followUps.length === 0 ? (
                <div className={styles.emptyState}>
                  <div className={styles.emptyIcon}>
                    <Check size={22} />
                  </div>
                  <p className={styles.emptyTitle}>All caught up</p>
                  <p className={styles.emptyDescription}>
                    No follow-ups needed right now. Agent B will automatically re-evaluate on the next scheduled scan.
                  </p>
                </div>
              ) : (
                followUps.map((fu) => (
                  <div key={fu.id} className={styles.followUpCard}>
                    <div className={styles.followUpCardHeader}>
                      <div>
                        <div className={styles.followUpCompany}>{fu.company}</div>
                        <div className={styles.followUpRole}>{fu.role} • {fu.status}</div>
                      </div>
                      <div className={styles.daysBadge}>
                        <Clock size={11} /> {fu.days_since_last_contact}d waiting
                      </div>
                    </div>

                    <p className={styles.followUpReason}>{fu.decision_reason}</p>

                    {fu.email_draft && (
                      <div className={styles.emailDraft}>
                        <div className={styles.draftLabel}>GENERATED DRAFT</div>
                        <div className={styles.draftText}>{fu.email_draft}</div>
                      </div>
                    )}

                    <div className={styles.followUpActions}>
                      {fu.email_draft && (
                        <button
                          className={styles.copyBtn}
                          onClick={() => handleCopy(fu.email_draft!, fu.id)}
                        >
                          {copiedId === fu.id ? (
                            <><Check size={11} /> Copied!</>
                          ) : (
                            <><Copy size={11} /> Copy Draft</>
                          )}
                        </button>
                      )}
                      <button
                        className={styles.dismissBtn}
                        onClick={() => dismissFollowUp(fu.id)}
                      >
                        <X size={11} /> Dismiss
                      </button>
                      <Link
                        href={`/applications/${fu.application_id}`}
                        className={styles.viewAppLink}
                      >
                        View App <ExternalLink size={10} />
                      </Link>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* ── Right Panel: Action Inbox (Agent A) ──────── */}
          <div className={styles.panel}>
            <div className={styles.panelHeader}>
              <h3 className={styles.panelTitle}>
                <Zap size={15} />
                Action Inbox
              </h3>
              <div className={styles.panelStats}>
                {(actionsData?.confirmed ?? 0) > 0 && (
                  <span className={`${styles.statChip} ${styles.statChipConfirmed}`}>
                    <Shield size={10} /> {actionsData?.confirmed} confirmed
                  </span>
                )}
                {(actionsData?.needs_review ?? 0) > 0 && (
                  <span className={`${styles.statChip} ${styles.statChipReview}`}>
                    <AlertTriangle size={10} /> {actionsData?.needs_review} review
                  </span>
                )}
                <span className={styles.panelTag}>AGENT A</span>
              </div>
            </div>

            <div className={styles.panelBody}>
              {actionsLoading ? (
                <div className={styles.loadingState}>
                  <Loader2 size={16} className={styles.spin} />
                  <span>Loading actions…</span>
                </div>
              ) : actions.length === 0 ? (
                <div className={styles.emptyState}>
                  <div className={styles.emptyIcon}>
                    <Inbox size={22} />
                  </div>
                  <p className={styles.emptyTitle}>No pending actions</p>
                  <p className={styles.emptyDescription}>
                    Your inbox is clear. Actions are automatically extracted when job emails are processed.
                  </p>
                </div>
              ) : (
                <>
                  {/* Confirmed actions (confidence ≥ 0.8) */}
                  {confirmedActions.length > 0 && (
                    <>
                      <div className={styles.sectionLabel}>CONFIRMED ACTIONS</div>
                      {confirmedActions.map((action) => (
                        <ActionCard key={action.id} action={action} />
                      ))}
                    </>
                  )}

                  {/* Needs review actions (0.4 ≤ confidence < 0.8) */}
                  {reviewActions.length > 0 && (
                    <>
                      <div className={styles.sectionLabel}>NEEDS REVIEW</div>
                      {reviewActions.map((action) => (
                        <ActionCard key={action.id} action={action} />
                      ))}
                    </>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Action Card Sub-Component ─────────────────────── */

function ActionCard({ action }: { action: {
  id: string;
  application_id: string;
  company: string;
  role: string;
  action_type: string;
  urgency: string;
  confidence: number;
  source_text: string | null;
  description: string;
  deadline: string | null;
  needs_review: boolean;
  created_at: string;
}}) {
  const urgencyClass =
    action.urgency === 'high' ? styles.urgencyHigh :
    action.urgency === 'medium' ? styles.urgencyMedium :
    styles.urgencyLow;

  const iconClass =
    action.urgency === 'high' ? styles.actionTypeIconHigh :
    action.urgency === 'medium' ? styles.actionTypeIconMedium :
    styles.actionTypeIconLow;

  return (
    <Link href={`/applications/${action.application_id}`} className={styles.actionCard}>
      <div className={styles.actionCardHeader}>
        <div className={styles.actionType}>
          <span className={`${styles.actionTypeIcon} ${iconClass}`}>
            {getActionIcon(action.action_type)}
          </span>
          {action.action_type.replace(/_/g, ' ')}
        </div>
        <span className={`${styles.urgencyBadge} ${urgencyClass}`}>
          {action.urgency.toUpperCase()}
        </span>
      </div>

      <div className={styles.actionCompany}>{action.company}</div>
      <div className={styles.actionRole}>{action.role}</div>

      {action.source_text && (
        <div className={styles.actionSourceText}>
          &ldquo;{action.source_text}&rdquo;
        </div>
      )}

      {action.description && (
        <div className={styles.actionRole}>{action.description}</div>
      )}

      <div className={styles.actionMeta}>
        <span className={styles.confidencePill}>
          <div className={styles.confidenceBar}>
            <div
              className={styles.confidenceFill}
              style={{ width: `${Math.round(action.confidence * 100)}%` }}
            />
          </div>
          {Math.round(action.confidence * 100)}%
        </span>

        {action.needs_review && (
          <span className={styles.reviewBadge}>NEEDS REVIEW</span>
        )}

        {action.deadline && (
          <span className={styles.deadlinePill}>
            <Calendar size={10} />
            {formatDate(action.deadline)}
          </span>
        )}

        <span>{getRelativeTime(action.created_at)}</span>
      </div>
    </Link>
  );
}
