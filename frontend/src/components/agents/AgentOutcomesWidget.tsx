'use client';

import { useOutcomesDashboard } from '@/hooks/use-agents';
import styles from './AgentOutcomesWidget.module.css';
import {
  AlertTriangle,
  Bot,
  DollarSign,
  Loader2,
  Mail,
  MessageSquare,
  Shield,
  TrendingUp,
  Workflow,
} from 'lucide-react';

export function AgentOutcomesWidget() {
  const { data, isLoading, isError } = useOutcomesDashboard();

  if (isLoading) {
    return (
      <section className={styles.card}>
        <h2 className={styles.title}>
          <TrendingUp size={18} />
          Agent Outcomes
        </h2>
        <div className={styles.stateRow}>
          <Loader2 size={16} className={styles.spin} />
          <span>Loading agent metrics…</span>
        </div>
      </section>
    );
  }

  if (isError || !data) {
    return (
      <section className={styles.card}>
        <h2 className={styles.title}>
          <TrendingUp size={18} />
          Agent Outcomes
        </h2>
        <div className={styles.stateRow}>
          <AlertTriangle size={16} />
          <span>Could not load agent outcomes.</span>
        </div>
      </section>
    );
  }

  return (
    <section className={styles.card}>
      <h2 className={styles.title}>
        <TrendingUp size={18} />
        Agent Outcomes
      </h2>
      <p className={styles.subtitle}>
        Value, safety, and cost from the follow-up agent loop.
      </p>

      <div className={styles.groupLabel}>VALUE</div>
      <div className={styles.grid}>
        <Metric icon={<Mail size={16} />} label="Follow-ups sent" value={data.follow_ups_sent} />
        <Metric icon={<MessageSquare size={16} />} label="Replies received" value={data.replies_received} />
        <Metric icon={<TrendingUp size={16} />} label="Positive replies" value={data.positive_replies} />
        <Metric
          icon={<MessageSquare size={16} />}
          label="Reply rate"
          value={data.reply_rate != null ? `${Math.round(data.reply_rate * 100)}%` : '—'}
        />
        <Metric icon={<TrendingUp size={16} />} label="Ghost recovered" value={data.ghost_recovered} />
        <Metric icon={<Shield size={16} />} label="Deadlines caught" value={data.deadlines_caught} />
      </div>

      <div className={styles.groupLabel}>SAFETY & COST</div>
      <div className={styles.grid}>
        <Metric icon={<Workflow size={16} />} label="Agent runs" value={data.agent_runs_total} />
        <Metric
          icon={<AlertTriangle size={16} />}
          label="Degraded rate"
          value={`${Math.round((data.degraded_rate ?? 0) * 100)}%`}
          negative
        />
        <Metric icon={<AlertTriangle size={16} />} label="Failed sends" value={data.failed_sends} negative />
        <Metric icon={<Shield size={16} />} label="Policy vetoes" value={data.policy_vetoes} />
        <Metric
          icon={<Shield size={16} />}
          label="Veto rate"
          value={`${Math.round(data.policy_veto_rate * 100)}%`}
        />
        <Metric
          icon={<Bot size={16} />}
          label="Escalation rate"
          value={`${Math.round(data.escalation_rate * 100)}%`}
        />
        <Metric
          icon={<DollarSign size={16} />}
          label="Est. LLM cost"
          value={`$${data.estimated_llm_cost_usd.toFixed(3)}`}
        />
        <Metric
          icon={<DollarSign size={16} />}
          label="Cost / application"
          value={`$${data.cost_per_application_usd.toFixed(4)}`}
        />
      </div>
    </section>
  );
}

function Metric({
  icon,
  label,
  value,
  negative,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  negative?: boolean;
}) {
  return (
    <div className={styles.metric}>
      <div className={styles.metricIcon}>{icon}</div>
      <div>
        <div className={`${styles.metricValue} ${negative && Number(value) > 0 ? styles.negative : ''}`}>
          {value}
        </div>
        <div className={styles.metricLabel}>{label}</div>
      </div>
    </div>
  );
}
