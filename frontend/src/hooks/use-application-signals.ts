/**
 * Agent-derived signals for kanban cards and deadline widgets.
 */

import { useMemo } from 'react';
import { useAgentActions, useAgentFollowUps, useOutreachInbox } from '@/hooks/use-agents';

export interface ApplicationSignal {
  followUp?: boolean;
  pendingSend?: boolean;
  actionRequired?: boolean;
  actionLabel?: string;
}

export interface UpcomingDeadline {
  id: string;
  actionId: string;
  company: string;
  role: string;
  actionType: string;
  deadline: Date;
  urgency: string;
  needsReview: boolean;
}

function daysUntil(date: Date): number {
  return Math.ceil((date.getTime() - Date.now()) / 86400000);
}

export function useApplicationSignals() {
  const { data: actionsData } = useAgentActions();
  const { data: followUpsData } = useAgentFollowUps();
  const { data: outreachData } = useOutreachInbox();

  const signalsByApp = useMemo(() => {
    const map = new Map<string, ApplicationSignal>();

    for (const fu of followUpsData?.follow_ups || []) {
      const prev = map.get(fu.application_id) || {};
      map.set(fu.application_id, { ...prev, followUp: true });
    }

    for (const o of outreachData?.actions || []) {
      if (['pending_approval', 'pending_undo'].includes(o.status)) {
        const prev = map.get(o.application_id) || {};
        map.set(o.application_id, { ...prev, pendingSend: true });
      }
    }

    for (const a of actionsData?.actions || []) {
      const hasDeadline = a.deadline && daysUntil(new Date(a.deadline)) <= 14;
      if (a.needs_review || hasDeadline) {
        const prev = map.get(a.application_id) || {};
        map.set(a.application_id, {
          ...prev,
          actionRequired: true,
          actionLabel: a.action_type.replace(/_/g, ' '),
        });
      }
    }

    return map;
  }, [actionsData, followUpsData, outreachData]);

  const upcomingDeadlines = useMemo((): UpcomingDeadline[] => {
    return (actionsData?.actions || [])
      .filter((a) => a.deadline)
      .map((a) => ({
        id: a.application_id,
        actionId: a.id,
        company: a.company,
        role: a.role,
        actionType: a.action_type.replace(/_/g, ' '),
        deadline: new Date(a.deadline!),
        urgency: a.urgency,
        needsReview: a.needs_review,
      }))
      .sort((a, b) => a.deadline.getTime() - b.deadline.getTime())
      .slice(0, 6);
  }, [actionsData]);

  const pendingApprovalCount = outreachData?.pending_approval ?? 0;

  return { signalsByApp, upcomingDeadlines, pendingApprovalCount };
}
