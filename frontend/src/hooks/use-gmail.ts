import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { gmailApi, PendingApplication } from '@/lib/api';
import { toast } from 'sonner';

export function useGmail() {
  const queryClient = useQueryClient();

  const pendingQuery = useQuery({
    queryKey: ['gmail', 'pending'],
    queryFn: () => gmailApi.listPending(),
  });

  const syncMutation = useMutation({
    mutationFn: () => gmailApi.sync(),
    onSuccess: (data) => {
      toast.success('Sync started', {
        description: 'Emails are being processed in the background.'
      });
      // Invalidate pending to refresh list (though sync takes time)
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
  };
}
