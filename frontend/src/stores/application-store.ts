import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Types
export interface Application {
  id: string;
  company: string;
  role: string;
  status: ApplicationStatus;
  appliedDate: string;
  source: string;
  priority: number;
  url?: string;
  location?: string;
  salaryMin?: number;
  salaryMax?: number;
  notes?: string;
  tags: string[];
  createdAt: string;
  updatedAt: string;
  // Email context (from gmail sync)
  email_subject?: string;
  email_snippet?: string;
  email_from?: string;
}

export type ApplicationStatus = 
  | 'applied'
  | 'screening'
  | 'oa'
  | 'interview'
  | 'offer'
  | 'accepted'
  | 'rejected'
  | 'withdrawn'
  | 'ghosted';

export interface CreateApplicationInput {
  company: string;
  role: string;
  appliedDate?: string;
  source?: string;
  priority?: number;
  url?: string;
  location?: string;
  salaryMin?: number;
  salaryMax?: number;
  notes?: string;
  tags?: string[];
}

export interface UpdateApplicationInput {
  company?: string;
  role?: string;
  status?: ApplicationStatus;
  appliedDate?: string;
  source?: string;
  priority?: number;
  url?: string;
  location?: string;
  salaryMin?: number;
  salaryMax?: number;
  notes?: string;
  tags?: string[];
}

interface ApplicationStore {
  // Client-side UI state mostly
  // Actual data now lives in React Query cache
  
  viewMode: 'list' | 'kanban';
  setViewMode: (mode: 'list' | 'kanban') => void;
  
  // NOTE: Legacy actions removed in favor of useCreateApplication/useUpdateApplication hooks
  // This store now primarily handles UI preferences for the application view
}

export const useApplicationStore = create<ApplicationStore>()(
  persist(
    (set) => ({
      viewMode: 'list',
      setViewMode: (mode) => set({ viewMode: mode }),
    }),
    {
      name: 'orbit-application-ui',
    }
  )
);
