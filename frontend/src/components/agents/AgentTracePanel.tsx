'use client';

import { useAgentTrace } from '@/hooks/use-agents';
import styles from './AgentTracePanel.module.css';
import { AlertTriangle, CheckCircle2, Loader2, ShieldX, Wrench, XCircle } from 'lucide-react';
import { useState } from 'react';

export function AgentTracePanel({ runId }: { runId: string | null }) {
  const { data, isLoading, error } = useAgentTrace(runId);

  if (!runId) {
    return (
      <div className={styles.empty}>
        <p>Select a run to inspect the full decision trace.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={styles.loading}>
        <Loader2 size={20} className={styles.spin} />
        <span>Loading trace…</span>
      </div>
    );
  }

  if (error || !data) {
    return <div className={styles.empty}>Could not load trace.</div>;
  }

  const decision = data.final_decision || {};
  const statusClass =
    data.status === 'failed'
      ? styles.statusFailed
      : data.status === 'degraded'
        ? styles.statusDegraded
        : styles.statusOk;

  return (
    <div className={styles.panel}>
      <div className={styles.summary}>
        <div>
          <div className={styles.metaRow}>
            <span className={`${styles.statusBadge} ${statusClass}`}>{data.status}</span>
            <span className={styles.trigger}>{data.trigger}</span>
          </div>
          <div className={styles.label}>FINAL DECISION</div>
          <div className={styles.decisionAction}>{String(decision.action || 'unknown')}</div>
          <div className={styles.decisionReason}>{String(decision.reason || '—')}</div>
        </div>
        <div className={styles.stats}>
          <span>{data.iterations} iterations</span>
          <span>{data.tool_call_count} tool calls</span>
          <span>{Math.round(data.latency_ms)}ms</span>
          <span>{data.prompt_tokens + data.completion_tokens} tokens</span>
          <span className={styles.tokenDetail}>
            {data.prompt_tokens}↑ / {data.completion_tokens}↓
          </span>
        </div>
      </div>

      {data.error_message && (
        <div className={styles.errorBanner}>
          <AlertTriangle size={14} />
          <span>{data.error_message}</span>
        </div>
      )}

      {data.policy_vetoes.length > 0 && (
        <div className={styles.vetoes}>
          <ShieldX size={14} />
          <span>Policy vetoes: {data.policy_vetoes.join(', ')}</span>
        </div>
      )}

      <div className={styles.sectionLabel}>TOOL TRACE</div>
      <div className={styles.traceList}>
        {data.tool_trace.length === 0 ? (
          <p className={styles.muted}>No tool calls recorded (rules fallback or degraded run).</p>
        ) : (
          data.tool_trace.map((step, i) => (
            <TraceStep key={i} step={step} />
          ))
        )}
      </div>
    </div>
  );
}

function TraceStep({
  step,
}: {
  step: {
    iteration: number;
    tool: string;
    arguments: Record<string, unknown>;
    result: Record<string, unknown>;
    latency_ms: number;
    error?: string;
  };
}) {
  const [showArgs, setShowArgs] = useState(false);
  const hasArgs = step.arguments && Object.keys(step.arguments).length > 0;

  return (
    <div className={styles.traceStep}>
      <div className={styles.traceHeader}>
        <Wrench size={12} />
        <span className={styles.toolName}>{step.tool}</span>
        <span className={styles.iteration}>#{step.iteration}</span>
        <span className={styles.toolLatency}>{Math.round(step.latency_ms)}ms</span>
        {step.error ? (
          <XCircle size={12} className={styles.errorIcon} />
        ) : (
          <CheckCircle2 size={12} className={styles.okIcon} />
        )}
      </div>
      {hasArgs && (
        <button className={styles.argsToggle} onClick={() => setShowArgs((v) => !v)} type="button">
          {showArgs ? 'Hide args' : 'Show args'}
        </button>
      )}
      {showArgs && hasArgs && (
        <pre className={styles.traceBody}>{JSON.stringify(step.arguments, null, 2)}</pre>
      )}
      {step.error && <div className={styles.stepError}>{step.error}</div>}
      <pre className={styles.traceBody}>{JSON.stringify(step.result, null, 2)}</pre>
    </div>
  );
}
