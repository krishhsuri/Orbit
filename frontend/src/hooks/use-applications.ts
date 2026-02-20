/**
 * React Query hooks for applications
 * Provides data fetching with caching and automatic updates
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { applicationsApi, analyticsApi } from '@/lib/api';
import type { Application, ApplicationStatus, CreateApplicationInput, UpdateApplicationInput } from '@/stores';

// Query keys
export const applicationKeys = {
  all: ['applications'] as const,
  lists: () => [...applicationKeys.all, 'list'] as const,
  list: (filters: Record<string, unknown>) => [...applicationKeys.lists(), filters] as const,
  details: () => [...applicationKeys.all, 'detail'] as const,
  detail: (id: string) => [...applicationKeys.details(), id] as const,
  events: (id: string) => [...applicationKeys.detail(id), 'events'] as const,
};

export const analyticsKeys = {
  all: ['analytics'] as const,
  summary: () => [...analyticsKeys.all, 'summary'] as const,
  funnel: (startDate?: string) => [...analyticsKeys.all, 'funnel', startDate] as const,
  sources: () => [...analyticsKeys.all, 'sources'] as const,
  insights: () => [...analyticsKeys.all, 'insights'] as const,
};

// List applications hook
export function useApplications(params?: {
  page?: number;
  limit?: number;
  status?: string;
  search?: string;
  source?: string;
  sort?: string;
}) {
  return useQuery({
    queryKey: applicationKeys.list(params || {}),
    queryFn: () => applicationsApi.list(params),
  });
}

// Get single application
export function useApplication(id: string) {
  return useQuery({
    queryKey: applicationKeys.detail(id),
    queryFn: () => applicationsApi.get(id),
    enabled: !!id,
  });
}

// Create application mutation
export function useCreateApplication() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (input: CreateApplicationInput) => applicationsApi.create(input),
    onSuccess: () => {
      // Invalidate all application lists
      queryClient.invalidateQueries({ queryKey: applicationKeys.lists() });
      // Also invalidate analytics since counts changed
      queryClient.invalidateQueries({ queryKey: analyticsKeys.all });
    },
  });
}

// Update application mutation
export function useUpdateApplication() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: UpdateApplicationInput }) =>
      applicationsApi.update(id, input),
    onSuccess: (data) => {
      // Update cache directly
      queryClient.setQueryData(applicationKeys.detail(data.id), data);
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: applicationKeys.lists() });
    },
  });
}

// Update status mutation
export function useUpdateApplicationStatus() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: ApplicationStatus }) =>
      applicationsApi.updateStatus(id, status),
    onSuccess: (data) => {
      // Update cache directly
      queryClient.setQueryData(applicationKeys.detail(data.id), data);
      // Invalidate lists and analytics
      queryClient.invalidateQueries({ queryKey: applicationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: analyticsKeys.all });
    },
  });
}

// Delete application mutation
export function useDeleteApplication() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: string) => applicationsApi.delete(id),
    onSuccess: (_, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: applicationKeys.detail(id) });
      // Invalidate lists and analytics
      queryClient.invalidateQueries({ queryKey: applicationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: analyticsKeys.all });
    },
  });
}

// Get application events
export function useApplicationEvents(id: string) {
  return useQuery({
    queryKey: applicationKeys.events(id),
    queryFn: () => applicationsApi.getEvents(id),
    enabled: !!id,
  });
}

// Create event mutation
export function useCreateEvent() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, event }: { id: string; event: { event_type: string; title?: string; description?: string; data?: Record<string, unknown> } }) =>
      applicationsApi.createEvent(id, event),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: applicationKeys.events(id) });
    },
  });
}

// Analytics hooks
export function useAnalyticsSummary() {
  return useQuery({
    queryKey: analyticsKeys.summary(),
    queryFn: () => analyticsApi.getSummary(),
    staleTime: 30 * 1000, // Cache for 30 seconds
  });
}

export function useAnalyticsFunnel(startDate?: string) {
  return useQuery({
    queryKey: analyticsKeys.funnel(startDate),
    queryFn: () => analyticsApi.getFunnel(startDate),
    staleTime: 30 * 1000,
  });
}

export function useAnalyticsSources() {
  return useQuery({
    queryKey: analyticsKeys.sources(),
    queryFn: () => analyticsApi.getSources(),
    staleTime: 60 * 1000, // Cache for 1 minute
  });
}

export function useAnalyticsInsights() {
  return useQuery({
    queryKey: analyticsKeys.insights(),
    queryFn: () => analyticsApi.getInsights(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });
}
