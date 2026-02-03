import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { gmailApi, PendingApplication } from '@/lib/api';
import { toast } from 'sonner';
import { useEffect, useRef } from 'react';

export function useGmail(options?: { autoSync?: boolean }) {
  const queryClient = useQueryClient();
  const hasSynced = useRef(false);

  const pendingQuery = useQuery({
    queryKey: ['gmail', 'pending'],
    queryFn: () => gmailApi.listPending(),
    refetchInterval: 10000, // Poll every 10 seconds for real-time updates
  });

  // Silent sync - doesn't show toast (used for auto-sync on mount)
  const silentSyncMutation = useMutation({
    mutationFn: () => gmailApi.sync(),
    onSuccess: () => {
      // Silently refresh the list after a few seconds
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ['gmail', 'pending'] }), 3000);
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ['gmail', 'pending'] }), 8000);
    },
  });

  // Auto-sync on mount (only once)
  useEffect(() => {
    if (options?.autoSync && !hasSynced.current) {
      hasSynced.current = true;
      silentSyncMutation.mutate();
    }
  }, [options?.autoSync]);

  const syncMutation = useMutation({
    mutationFn: () => gmailApi.sync(),
    onSuccess: (data) => {
      toast.success('Sync started', {
        description: 'Emails are being processed in the background.'
      });
      // Invalidate pending to refresh list
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ['gmail', 'pending'] }), 2000);
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ['gmail', 'pending'] }), 5000);
    },
    onError: (error) => {
      toast.error('Sync failed', {
        description: 'Could not trigger email sync.'
      });
    }
  });

  const confirmMutation = useMutation({
    mutationFn: (id: string) => gmailApi.confirm(id),
    onSuccess: (data) => {
      toast.success('Application confirmed', {
        description: 'Added to your applications list.'
      });
      queryClient.invalidateQueries({ queryKey: ['gmail', 'pending'] });
      queryClient.invalidateQueries({ queryKey: ['applications'] }); // Refresh main app list
    },
    onError: () => {
      toast.error('Failed to confirm application');
    }
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => gmailApi.reject(id),
    onSuccess: () => {
      toast.success('Application dismissed');
      queryClient.invalidateQueries({ queryKey: ['gmail', 'pending'] });
    },
    onError: () => {
      toast.error('Failed to dismiss application');
    }
  });

  const cleanupMutation = useMutation({
    mutationFn: () => gmailApi.cleanup(),
    onSuccess: (data) => {
      toast.success('Cleanup complete', {
        description: `Removed ${data.deleted_count} non-job-related entries.`
      });
      queryClient.invalidateQueries({ queryKey: ['gmail', 'pending'] });
    },
    onError: () => {
      toast.error('Cleanup failed');
    }
  });

  const processAIMutation = useMutation({
    mutationFn: () => gmailApi.processWithAI(),
    onSuccess: (data) => {
      toast.success('AI Processing complete', {
        description: `Added ${data.added} to tracker, discarded ${data.discarded} emails.`
      });
      queryClient.invalidateQueries({ queryKey: ['gmail', 'pending'] });
      queryClient.invalidateQueries({ queryKey: ['applications'] });
    },
    onError: () => {
      toast.error('AI Processing failed');
    }
  });

  return {
    pendingApplications: pendingQuery.data || [],
    isLoading: pendingQuery.isLoading,
    isError: pendingQuery.isError,
    refetch: pendingQuery.refetch,
    syncEmails: syncMutation.mutate,
    isSyncing: syncMutation.isPending,
    confirmApplication: confirmMutation.mutate,
    isConfirming: confirmMutation.isPending,
    rejectApplication: rejectMutation.mutate,
    isRejecting: rejectMutation.isPending,
    cleanupNonJobRelated: cleanupMutation.mutate,
    isCleaning: cleanupMutation.isPending,
    processWithAI: processAIMutation.mutate,
    isProcessingAI: processAIMutation.isPending,
  };
}
