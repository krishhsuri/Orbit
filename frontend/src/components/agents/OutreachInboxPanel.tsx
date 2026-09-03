'use client';

import {
  useApproveOutreach,
  useCancelOutreach,
  useOutreachInbox,
} from '@/hooks/use-agents';
import styles from './OutreachInboxPanel.module.css';
import { AlertTriangle, Check, Clock, Loader2, Shield, Workflow, X } from 'lucide-react';

function riskClass(tier: string) {
  return tier === 'high' ? styles.riskHigh : styles.riskLow;
}

function formatStatus(status: string) {
  return status.replace(/_/g, ' ');
}

function undoCountdown(undoUntil: string | null): string | null {
  if (!undoUntil) return null;
  const ms = new Date(undoUntil).getTime() - Date.now();
  if (ms <= 0) return 'Undo expired';
  const secs = Math.ceil(ms / 1000);
  return `Undo ${secs}s`;
}

export function OutreachInboxPanel({
  onViewTrace,
}: {
  onViewTrace?: (runId: string) => void;
}) {
  const { data, isLoading } = useOutreachInbox();
  const { mutate: approve, isPending: approving } = useApproveOutreach();
  const { mutate: cancel, isPending: cancelling } = useCancelOutreach();

  if (isLoading) {
    return (
      <div className={styles.loading}>
        <Loader2 size={18} className={styles.spin} />
        <span>Loading send queue…</span>
      </div>
    );
  }

  const actions = data?.actions || [];
  const pending = actions.filter((a) => ['pending_approval', 'pending_undo'].includes(a.status));
  const history = actions
    .filter((a) => !['pending_approval', 'pending_undo'].includes(a.status))
    .slice(0, 12);

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h3>Send Queue</h3>
        <div className={styles.badges}>
          {(data?.pending_approval ?? 0) > 0 && (
            <span className={styles.badgeApproval}>
              <AlertTriangle size={12} /> {data?.pending_approval} need approval
            </span>
          )}
          {(data?.pending_undo ?? 0) > 0 && (
            <span className={styles.badgeUndo}>
              <Clock size={12} /> {data?.pending_undo} in undo window
            </span>
          )}
        </div>
      </div>

      {pending.length === 0 ? (
        <div className={styles.empty}>
          <Shield size={24} />
          <p>Nothing waiting to send. Click Scan on Overview — recommended follow-ups land here for approval before they go out.</p>
        </div>
      ) : (
        <div className={styles.list}>
          {pending.map((action) => (
            <div key={action.id} className={styles.card}>
              <div className={styles.cardHeader}>
                <div>
                  <div className={styles.company}>{action.company}</div>
                  <div className={styles.role}>{action.role}</div>
                </div>
                <div className={styles.badgeStack}>
                  <span className={`${styles.riskBadge} ${riskClass(action.risk_tier)}`}>
                    {action.risk_tier.toUpperCase()} RISK
                  </span>
                  <span className={styles.modeBadge}>{action.approval_mode.replace(/_/g, ' ')}</span>
                </div>
              </div>
              <p className={styles.draft}>{action.draft_preview || 'No draft preview'}</p>
              <div className={styles.meta}>
                <span className={styles.status}>{formatStatus(action.status)}</span>
                {action.undo_until && (
                  <span className={styles.undoHint}>{undoCountdown(action.undo_until)}</span>
                )}
                {action.sent_at && (
                  <span>Sent {new Date(action.sent_at).toLocaleString()}</span>
                )}
              </div>
              <div className={styles.actions}>
                {action.status === 'pending_approval' && (
                  <button
                    className={styles.approveBtn}
                    onClick={() => approve(action.id)}
                    disabled={approving}
                  >
                    <Check size={12} /> Approve
                  </button>
                )}
                <button
                  className={styles.cancelBtn}
                  onClick={() => cancel(action.id)}
                  disabled={cancelling}
                >
                  <X size={12} /> Cancel
                </button>
                {action.agent_run_id && onViewTrace && (
                  <button
                    className={styles.traceBtn}
                    onClick={() => onViewTrace(action.agent_run_id!)}
                  >
                    <Workflow size={12} /> Trace
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {history.length > 0 && (
        <>
          <div className={styles.sectionLabel}>HISTORY</div>
          <div className={styles.history}>
            {history.map((a) => (
              <div key={a.id} className={styles.historyRow}>
                <div className={styles.historyMain}>
                  <span className={styles.historyCompany}>{a.company}</span>
                  <span className={styles.historyRole}>{a.role}</span>
                </div>
                <div className={styles.historyRight}>
                  <span className={`${styles.riskDot} ${riskClass(a.risk_tier)}`}>{a.risk_tier}</span>
                  <span className={styles.historyStatus}>{formatStatus(a.status)}</span>
                  {a.agent_run_id && onViewTrace && (
                    <button
                      className={styles.historyTrace}
                      onClick={() => onViewTrace(a.agent_run_id!)}
                      type="button"
                    >
                      <Workflow size={11} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
