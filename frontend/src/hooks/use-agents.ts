/**
 * React Query hooks for the AI Agents page.
 * Auto-fetches pre-computed Agent A and Agent B results.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { agentsApi } from '@/lib/api';

export const agentKeys = {
  all: ['agents'] as const,
  actions: () => [...agentKeys.all, 'actions'] as const,
  followUps: () => [...agentKeys.all, 'follow-ups'] as const,
};

/** Agent A: Extracted actions across all applications */
export function useAgentActions() {
  return useQuery({
    queryKey: agentKeys.actions(),
    queryFn: () => agentsApi.getActions(),
    refetchInterval: 60 * 1000, // Auto-refresh every 60s
    staleTime: 30 * 1000,
  });
}

/** Agent B: Pre-computed follow-up evaluations */
export function useAgentFollowUps() {
  return useQuery({
    queryKey: agentKeys.followUps(),
    queryFn: () => agentsApi.getFollowUps(),
    refetchInterval: 60 * 1000,
    staleTime: 30 * 1000,
  });
}

/** Dismiss a follow-up recommendation */
export function useDismissFollowUp() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => agentsApi.dismissFollowUp(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.followUps() });
    },
  });
}

/** Manually trigger Agent B scan for immediate results */
export function useTriggerScan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => agentsApi.triggerScan(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.followUps() });
    },
  });
}
