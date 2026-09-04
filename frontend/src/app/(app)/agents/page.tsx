'use client';

import { AgentTracePanel } from '@/components/agents/AgentTracePanel';
import { OutreachInboxPanel } from '@/components/agents/OutreachInboxPanel';
import {
  useAgentActions,
  useAgentFollowUps,
  useAgentRuns,
  useDismissFollowUp,
  useKillSwitch,
  useOutreachInbox,
  useSetKillSwitch,
  useTriggerScan,
} from '@/hooks/use-agents';
import styles from './page.module.css';
import {
  AlertTriangle,
  Bot,
  Calendar,
  Check,
  ClipboardCheck,
  Clock,
  Code,
  Copy,
  ExternalLink,
  FileText,
  Inbox,
  Loader2,
  Mail,
  MessageSquare,
  Power,
  RefreshCw,
  Shield,
  Workflow,
  X,
  Zap,
} from 'lucide-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useMemo, useState } from 'react';

type Tab = 'overview' | 'outreach' | 'trace';

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
  return (
    <Suspense fallback={
      <div className={styles.page}>
        <div className={styles.loadingState} style={{ padding: 48 }}>
          <Loader2 size={18} className={styles.spin} />
          <span>Loading agents…</span>
        </div>
      </div>
    }>
      <AgentsPageInner />
    </Suspense>
  );
}

function AgentsPageInner() {
  const searchParams = useSearchParams();
  const runFromQuery = searchParams.get('run');
  const [tab, setTab] = useState<Tab>(runFromQuery ? 'trace' : 'overview');
  const [selectedRunId, setSelectedRunId] = useState<string | null>(runFromQuery);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const { data: actionsData, isLoading: actionsLoading } = useAgentActions();
  const { data: followUpsData, isLoading: followUpsLoading } = useAgentFollowUps();
  const { data: outreachData } = useOutreachInbox();
  const { data: runsData } = useAgentRuns();
  const { data: killSwitch } = useKillSwitch();
  const { mutate: dismissFollowUp } = useDismissFollowUp();
  const { mutate: triggerScan, isPending: isScanning } = useTriggerScan();
  const { mutate: setKillSwitch, isPending: togglingKill } = useSetKillSwitch();

  useEffect(() => {
    if (runFromQuery) {
      setSelectedRunId(runFromQuery);
      setTab('trace');
    }
  }, [runFromQuery]);

  useEffect(() => {
    if (!selectedRunId && (runsData?.runs?.length ?? 0) > 0) {
      setSelectedRunId(runsData!.runs[0].run_id);
    }
  }, [runsData, selectedRunId]);

  const actions = actionsData?.actions || [];
  const followUps = followUpsData?.follow_ups || [];
  const lastScan = followUpsData?.last_scan;
  const confirmedActions = actions.filter((a) => !a.needs_review);
  const reviewActions = actions.filter((a) => a.needs_review);

  const outreachByApp = useMemo(() => {
    const map = new Map<string, { id: string; status: string; agent_run_id: string | null }>();
    for (const a of outreachData?.actions || []) {
      const existing = map.get(a.application_id);
      if (!existing || ['pending_approval', 'pending_undo'].includes(a.status)) {
        map.set(a.application_id, {
          id: a.id,
          status: a.status,
          agent_run_id: a.agent_run_id,
        });
      }
    }
    return map;
  }, [outreachData?.actions]);

  const runByApp = useMemo(() => {
    const map = new Map<string, string>();
    for (const run of runsData?.runs || []) {
      if (!map.has(run.application_id)) {
        map.set(run.application_id, run.run_id);
      }
    }
    return map;
  }, [runsData?.runs]);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const openTrace = (runId: string) => {
    setSelectedRunId(runId);
    setTab('trace');
  };

  const pendingApproval = outreachData?.pending_approval ?? 0;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.pageTitle}>AI Agents</h1>
          <span className={styles.headerSep}>/</span>
          <span className={styles.headerMeta}>BOUNDED OUTREACH LOOP</span>
        </div>
        <div className={styles.headerRight}>
          {killSwitch?.active && (
            <span className={styles.killSwitchActive} title={killSwitch.reason || undefined}>
              <Power size={12} />
              Sends paused
              {killSwitch.reason ? `: ${killSwitch.reason}` : ''}
              {killSwitch.global ? ' (global)' : ''}
            </span>
          )}
          <button
            className={`${styles.killSwitchBtn} ${killSwitch?.user ? styles.killSwitchOn : ''}`}
            onClick={() => setKillSwitch(!killSwitch?.user)}
            disabled={togglingKill || killSwitch?.global}
            title={killSwitch?.global ? 'Global kill switch active' : 'Toggle user kill switch'}
          >
            <Power size={12} />
            {killSwitch?.user ? 'Resume sends' : 'Pause sends'}
          </button>
          {lastScan && (
            <span className={styles.lastScan}>
              <span className={styles.lastScanDot} />
              Last scan: {getRelativeTime(lastScan)}
            </span>
          )}
          <button className={styles.scanBtn} onClick={() => triggerScan()} disabled={isScanning}>
            {isScanning ? (
              <><Loader2 size={12} className={styles.spin} /> Scanning…</>
            ) : (
              <><RefreshCw size={12} /> Scan</>
            )}
          </button>
        </div>
      </div>

      <div className={styles.tabBar}>
        <button className={tab === 'overview' ? styles.tabActive : styles.tab} onClick={() => setTab('overview')}>
          Overview
          {followUps.length > 0 && <span className={styles.tabCount}>{followUps.length}</span>}
        </button>
        <button className={tab === 'outreach' ? styles.tabActive : styles.tab} onClick={() => setTab('outreach')}>
          Send Queue
          {pendingApproval > 0 && <span className={styles.tabCountWarn}>{pendingApproval}</span>}
        </button>
        <button className={tab === 'trace' ? styles.tabActive : styles.tab} onClick={() => setTab('trace')}>
          <Workflow size={14} /> Agent Trace
          {(runsData?.total ?? 0) > 0 && <span className={styles.tabCount}>{runsData?.total}</span>}
        </button>
      </div>

      <div className={styles.scrollArea}>
        {tab === 'outreach' && <OutreachInboxPanel onViewTrace={openTrace} />}

        {tab === 'trace' && (
          <div className={styles.traceLayout}>
            <div className={styles.runList}>
              <div className={styles.sectionLabel}>RECENT RUNS</div>
              {(runsData?.runs || []).length === 0 ? (
                <p className={styles.emptyDescription}>
                  No traces yet. Click Scan — each application gets a run with the decision, tools used, and any policy vetoes.
                </p>
              ) : (
                runsData?.runs.map((run) => {
                  const decision = run.final_decision as { action?: string } | null;
                  return (
                    <button
                      key={run.run_id}
                      className={`${styles.runItem} ${selectedRunId === run.run_id ? styles.runItemActive : ''}`}
                      onClick={() => setSelectedRunId(run.run_id)}
                    >
                      <div className={styles.runItemTitle}>{run.company}</div>
                      <div className={styles.runItemMeta}>
                        <span className={
                          run.status === 'failed' ? styles.runStatusFailed
                            : run.status === 'degraded' ? styles.runStatusDegraded
                              : styles.runStatusOk
                        }>
                          {run.status}
                        </span>
                        {' · '}
                        {decision?.action ? `${decision.action} · ` : ''}
                        {run.tool_call_count} tools · {getRelativeTime(run.created_at)}
                      </div>
                      {run.policy_vetoes?.length > 0 && (
                        <div className={styles.runVeto}>vetoed: {run.policy_vetoes.join(', ')}</div>
                      )}
                    </button>
                  );
                })
              )}
            </div>
            <AgentTracePanel runId={selectedRunId} />
          </div>
        )}

        {tab === 'overview' && (
          <div className={styles.contentGrid}>
            <div className={styles.panel}>
              <div className={styles.panelHeader}>
                <h3 className={styles.panelTitle}><Mail size={15} /> Follow-Up Queue</h3>
              </div>
              <div className={styles.panelBody}>
                {followUpsLoading ? (
                  <div className={styles.loadingState}><Loader2 size={16} className={styles.spin} /><span>Loading…</span></div>
                ) : !lastScan ? (
                  <div className={styles.scanBanner}>
                    <div className={styles.emptyIcon}><Bot size={22} /></div>
                    <p className={styles.scanBannerText}>Run an initial scan to evaluate follow-ups.</p>
                    <button className={styles.scanBannerBtn} onClick={() => triggerScan()} disabled={isScanning}>
                      {isScanning ? <><Loader2 size={14} className={styles.spin} /> Scanning…</> : <><Bot size={14} /> Run Scan</>}
                    </button>
                  </div>
                ) : followUps.length === 0 ? (
                  <div className={styles.emptyState}>
                    <div className={styles.emptyIcon}><Check size={22} /></div>
                    <p className={styles.emptyTitle}>All caught up</p>
                    <p className={styles.emptyDescription}>No follow-ups recommended. Check Send Queue for queued outreach.</p>
                  </div>
                ) : (
                  followUps.map((fu) => {
                    const queued = outreachByApp.get(fu.application_id);
                    const linkedRunId = queued?.agent_run_id || runByApp.get(fu.application_id) || null;
                    const isPendingSend = queued && ['pending_approval', 'pending_undo'].includes(queued.status);

                    return (
                      <div key={fu.id} className={styles.followUpCard}>
                        <div className={styles.followUpCardHeader}>
                          <div>
                            <div className={styles.followUpCompany}>{fu.company}</div>
                            <div className={styles.followUpRole}>{fu.role} · {fu.status}</div>
                          </div>
                          <div className={styles.daysBadge}><Clock size={11} /> {fu.days_since_last_contact}d</div>
                        </div>
                        <p className={styles.followUpReason}>{fu.decision_reason}</p>
                        {isPendingSend && (
                          <div className={styles.queuedHint}>
                            <Shield size={11} /> In Send Queue · {queued!.status.replace(/_/g, ' ')}
                          </div>
                        )}
                        {fu.email_draft && (
                          <div className={styles.emailDraft}>
                            <div className={styles.draftLabel}>DRAFT</div>
                            <div className={styles.draftText}>{fu.email_draft}</div>
                          </div>
                        )}
                        <div className={styles.followUpActions}>
                          {isPendingSend && (
                            <button className={styles.queueBtn} onClick={() => setTab('outreach')}>
                              <Inbox size={11} /> Open Send Queue
                            </button>
                          )}
                          {linkedRunId && (
                            <button className={styles.traceLinkBtn} onClick={() => openTrace(linkedRunId)}>
                              <Workflow size={11} /> Trace
                            </button>
                          )}
                          {fu.email_draft && (
                            <button className={styles.copyBtn} onClick={() => handleCopy(fu.email_draft!, fu.id)}>
                              {copiedId === fu.id ? <><Check size={11} /> Copied</> : <><Copy size={11} /> Copy</>}
                            </button>
                          )}
                          <button className={styles.dismissBtn} onClick={() => dismissFollowUp(fu.id)}><X size={11} /> Dismiss</button>
                          <Link href={`/applications/${fu.application_id}`} className={styles.viewAppLink}>View <ExternalLink size={10} /></Link>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            <div className={styles.panel}>
              <div className={styles.panelHeader}>
                <h3 className={styles.panelTitle}><Zap size={15} /> Action Inbox</h3>
                <div className={styles.panelStats}>
                  {(actionsData?.confirmed ?? 0) > 0 && (
                    <span className={`${styles.statChip} ${styles.statChipConfirmed}`}><Shield size={10} /> {actionsData?.confirmed}</span>
                  )}
                  {(actionsData?.needs_review ?? 0) > 0 && (
                    <span className={`${styles.statChip} ${styles.statChipReview}`}><AlertTriangle size={10} /> {actionsData?.needs_review}</span>
                  )}
                </div>
              </div>
              <div className={styles.panelBody}>
                {actionsLoading ? (
                  <div className={styles.loadingState}><Loader2 size={16} className={styles.spin} /><span>Loading…</span></div>
                ) : actions.length === 0 ? (
                  <div className={styles.emptyState}>
                    <div className={styles.emptyIcon}><Inbox size={22} /></div>
                    <p className={styles.emptyTitle}>No pending actions</p>
                  </div>
                ) : (
                  <>
                    {confirmedActions.length > 0 && (
                      <>
                        <div className={styles.sectionLabel}>CONFIRMED</div>
                        {confirmedActions.map((action) => <ActionCard key={action.id} action={action} />)}
                      </>
                    )}
                    {reviewActions.length > 0 && (
                      <>
                        <div className={styles.sectionLabel}>NEEDS REVIEW</div>
                        {reviewActions.map((action) => <ActionCard key={action.id} action={action} />)}
                      </>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ActionCard({ action }: { action: {
  id: string; application_id: string; company: string; role: string;
  action_type: string; urgency: string; confidence: number;
  source_text: string | null; title?: string; description: string; deadline: string | null;
  needs_review: boolean; created_at: string;
}}) {
  const urgencyClass = action.urgency === 'high' ? styles.urgencyHigh : action.urgency === 'medium' ? styles.urgencyMedium : styles.urgencyLow;
  const iconClass = action.urgency === 'high' ? styles.actionTypeIconHigh : action.urgency === 'medium' ? styles.actionTypeIconMedium : styles.actionTypeIconLow;

  return (
    <Link href={`/applications/${action.application_id}`} className={styles.actionCard}>
      <div className={styles.actionCardHeader}>
        <div className={styles.actionType}>
          <span className={`${styles.actionTypeIcon} ${iconClass}`}>{getActionIcon(action.action_type)}</span>
          {action.action_type.replace(/_/g, ' ')}
        </div>
        <span className={`${styles.urgencyBadge} ${urgencyClass}`}>{action.urgency.toUpperCase()}</span>
      </div>
      <div className={styles.actionCompany}>{action.company}</div>
      <div className={styles.actionRole}>{action.role}</div>
      {(action.title || action.description) && (
        <div className={styles.actionDesc}>{action.title || action.description}</div>
      )}
      {action.source_text && <div className={styles.actionSourceText}>&ldquo;{action.source_text}&rdquo;</div>}
      <div className={styles.actionMeta}>
        <span className={styles.confidencePill}>
          <div className={styles.confidenceBar}><div className={styles.confidenceFill} style={{ width: `${Math.round(action.confidence * 100)}%` }} /></div>
          {Math.round(action.confidence * 100)}%
        </span>
        {action.needs_review && <span className={styles.reviewBadge}>REVIEW</span>}
        {action.deadline && <span className={styles.deadlinePill}><Calendar size={10} />{formatDate(action.deadline)}</span>}
        <span>{getRelativeTime(action.created_at)}</span>
      </div>
    </Link>
  );
}
