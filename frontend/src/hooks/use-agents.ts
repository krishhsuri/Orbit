/**
 * React Query hooks for agent trace, outreach inbox, and outcomes.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { agentsApi } from '@/lib/api';

export const agentKeys = {
  all: ['agents'] as const,
  actions: () => [...agentKeys.all, 'actions'] as const,
  followUps: () => [...agentKeys.all, 'follow-ups'] as const,
  outreach: () => [...agentKeys.all, 'outreach'] as const,
  runs: () => [...agentKeys.all, 'runs'] as const,
  trace: (runId: string) => [...agentKeys.all, 'trace', runId] as const,
  killSwitch: () => [...agentKeys.all, 'kill-switch'] as const,
  outcomes: () => [...agentKeys.all, 'outcomes'] as const,
};

function invalidateAgentSurface(
  queryClient: ReturnType<typeof useQueryClient>,
  keys: Array<readonly unknown[]>,
) {
  keys.forEach((queryKey) => {
    queryClient.invalidateQueries({ queryKey });
  });
}

export function useAgentActions() {
  return useQuery({
    queryKey: agentKeys.actions(),
    queryFn: () => agentsApi.getActions(),
    refetchInterval: 60 * 1000,
    staleTime: 30 * 1000,
  });
}

export function useAgentFollowUps() {
  return useQuery({
    queryKey: agentKeys.followUps(),
    queryFn: () => agentsApi.getFollowUps(),
    refetchInterval: 60 * 1000,
    staleTime: 30 * 1000,
  });
}

export function useDismissFollowUp() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => agentsApi.dismissFollowUp(id),
    onSuccess: () => {
      invalidateAgentSurface(queryClient, [agentKeys.followUps()]);
    },
  });
}

export function useTriggerScan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => agentsApi.triggerScan(),
    onSuccess: () => {
      invalidateAgentSurface(queryClient, [
        agentKeys.followUps(),
        agentKeys.runs(),
        agentKeys.outreach(),
        agentKeys.outcomes(),
        agentKeys.actions(),
      ]);
    },
  });
}

export function useOutreachInbox() {
  return useQuery({
    queryKey: agentKeys.outreach(),
    queryFn: () => agentsApi.getOutreach(),
    refetchInterval: 15 * 1000,
  });
}

export function useApproveOutreach() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => agentsApi.approveOutreach(id),
    onSuccess: () => {
      invalidateAgentSurface(queryClient, [
        agentKeys.outreach(),
        agentKeys.outcomes(),
        agentKeys.followUps(),
      ]);
    },
  });
}

export function useCancelOutreach() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => agentsApi.cancelOutreach(id),
    onSuccess: () => {
      invalidateAgentSurface(queryClient, [
        agentKeys.outreach(),
        agentKeys.outcomes(),
      ]);
    },
  });
}

export function useKillSwitch() {
  return useQuery({
    queryKey: agentKeys.killSwitch(),
    queryFn: () => agentsApi.getKillSwitch(),
    refetchInterval: 30 * 1000,
  });
}

export function useSetKillSwitch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (enabled: boolean) => agentsApi.setKillSwitch(enabled),
    onSuccess: () => {
      invalidateAgentSurface(queryClient, [
        agentKeys.killSwitch(),
        agentKeys.outreach(),
      ]);
    },
  });
}

export function useAgentRuns() {
  return useQuery({
    queryKey: agentKeys.runs(),
    queryFn: () => agentsApi.listRuns(),
    staleTime: 30 * 1000,
  });
}

export function useAgentTrace(runId: string | null) {
  return useQuery({
    queryKey: agentKeys.trace(runId || ''),
    queryFn: () => agentsApi.getRunTrace(runId!),
    enabled: !!runId,
  });
}

export function useOutcomesDashboard() {
  return useQuery({
    queryKey: agentKeys.outcomes(),
    queryFn: () => agentsApi.getOutcomesDashboard(),
    staleTime: 60 * 1000,
  });
}
