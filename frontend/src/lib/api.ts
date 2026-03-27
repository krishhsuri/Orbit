/**
 * Applications API
 * API functions for application CRUD operations
 */

import { api, PaginatedResponse } from './api-client';
import type { Application, ApplicationStatus, CreateApplicationInput, UpdateApplicationInput } from '@/stores';

// API Response types (matching backend schemas)
export interface ApplicationApiResponse {
  id: string;
  user_id: string;
  company_name: string;
  role_title: string;
  status: ApplicationStatus;
  applied_date: string;
  job_url?: string;
  salary_min?: number;
  salary_max?: number;
  salary_currency: string;
  location?: string;
  remote_type?: string;
  source?: string;
  referrer_name?: string;
  priority: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  status_updated_at: string;
  tags: { id: string; name: string; color: string }[];
  // Email context (from gmail sync)
  email_subject?: string;
  email_snippet?: string;
  email_from?: string;
}

export interface EventApiResponse {
  id: string;
  event_type: string;
  title?: string;
  description?: string;
  data: Record<string, unknown>;
  scheduled_at?: string;
  created_at: string;
}

export interface ApplicationDetailApiResponse extends ApplicationApiResponse {
  events: EventApiResponse[];
}

// Transform API response to frontend Application type
function transformApplication(apiApp: ApplicationApiResponse): Application {
  return {
    id: apiApp.id,
    company: apiApp.company_name,
    role: apiApp.role_title,
    status: apiApp.status,
    appliedDate: apiApp.applied_date,
    source: apiApp.source || 'Direct',
    priority: apiApp.priority,
    url: apiApp.job_url,
    location: apiApp.location,
    salaryMin: apiApp.salary_min,
    salaryMax: apiApp.salary_max,
    notes: undefined, // Notes come separately
    tags: apiApp.tags.map(t => t.name),
    createdAt: apiApp.created_at,
    updatedAt: apiApp.updated_at,
    // Email context
    email_subject: apiApp.email_subject,
    email_snippet: apiApp.email_snippet,
    email_from: apiApp.email_from,
  };
}

// Transform frontend input to API format
function transformCreateInput(input: CreateApplicationInput) {
  return {
    company_name: input.company,
    role_title: input.role,
    applied_date: input.appliedDate,
    source: input.source,
    priority: input.priority,
    job_url: input.url,
    location: input.location,
    salary_min: input.salaryMin,
    salary_max: input.salaryMax,
    notes: input.notes,
    tags: input.tags || [],
  };
}

function transformUpdateInput(input: UpdateApplicationInput) {
  const result: Record<string, unknown> = {};
  
  if (input.company !== undefined) result.company_name = input.company;
  if (input.role !== undefined) result.role_title = input.role;
  if (input.status !== undefined) result.status = input.status;
  if (input.appliedDate !== undefined) result.applied_date = input.appliedDate;
  if (input.source !== undefined) result.source = input.source;
  if (input.priority !== undefined) result.priority = input.priority;
  if (input.url !== undefined) result.job_url = input.url;
  if (input.location !== undefined) result.location = input.location;
  if (input.salaryMin !== undefined) result.salary_min = input.salaryMin;
  if (input.salaryMax !== undefined) result.salary_max = input.salaryMax;
  if (input.notes !== undefined) result.notes = input.notes;
  
  return result;
}

// API Functions
export const applicationsApi = {
  // List applications
  async list(params?: {
    page?: number;
    limit?: number;
    status?: string;
    search?: string;
    source?: string;
    sort?: string;
  }): Promise<{ applications: Application[]; meta: PaginatedResponse<unknown>['meta'] }> {
    const response = await api.get<PaginatedResponse<ApplicationApiResponse>>(
      '/api/v1/applications',
      params
    );
    
    return {
      applications: response.data.map(transformApplication),
      meta: response.meta,
    };
  },

  // Get single application
  async get(id: string): Promise<Application> {
    const response = await api.get<ApplicationDetailApiResponse>(
      `/api/v1/applications/${id}`
    );
    return transformApplication(response);
  },

  // Create application
  async create(input: CreateApplicationInput): Promise<Application> {
    const response = await api.post<ApplicationApiResponse>(
      '/api/v1/applications',
      transformCreateInput(input)
    );
    return transformApplication(response);
  },

  // Update application
  async update(id: string, input: UpdateApplicationInput): Promise<Application> {
    const response = await api.patch<ApplicationApiResponse>(
      `/api/v1/applications/${id}`,
      transformUpdateInput(input)
    );
    return transformApplication(response);
  },

  // Update status (quick)
  async updateStatus(id: string, status: ApplicationStatus): Promise<Application> {
    const response = await api.patch<ApplicationApiResponse>(
      `/api/v1/applications/${id}/status`,
      { status }
    );
    return transformApplication(response);
  },

  // Delete application
  async delete(id: string): Promise<void> {
    await api.delete(`/api/v1/applications/${id}`);
  },

  // Get events
  async getEvents(id: string): Promise<EventApiResponse[]> {
    return api.get<EventApiResponse[]>(`/api/v1/applications/${id}/events`);
  },

  // Create event
  async createEvent(
    id: string,
    event: { event_type: string; title?: string; description?: string; data?: Record<string, unknown> }
  ): Promise<EventApiResponse> {
    return api.post<EventApiResponse>(`/api/v1/applications/${id}/events`, event);
  },
};

// Analytics API
export interface QuickStats {
  total: number;
  active: number;
  interviews: number;
  offers: number;
  this_week: number;
}

export interface FunnelStage {
  status: string;
  count: number;
  percentage: number;
}

export interface SourceStats {
  source: string;
  total: number;
  responded: number;
  response_rate: number;
}

export interface AIInsight {
  type: string;
  title: string;
  description: string;
  confidence?: number;
}

export const analyticsApi = {
  async getSummary(): Promise<QuickStats> {
    return api.get<QuickStats>('/api/v1/analytics/summary');
  },

  async getFunnel(startDate?: string): Promise<{ stages: FunnelStage[]; total: number }> {
    return api.get('/api/v1/analytics/funnel', { start_date: startDate });
  },

  async getSources(): Promise<{ sources: SourceStats[] }> {
    return api.get('/api/v1/analytics/sources');
  },

  async getInsights(): Promise<{ insights: AIInsight[]; generated_at: string }> {
    return api.get('/api/v1/analytics/insights');
  },

  async getMlStats(): Promise<{
    model_active: boolean;
    model_example_count: number;
    min_examples_required: number;
    user_decisions: number;
    user_positive: number;
    user_negative: number;
    global_training_examples: number;
    progress_pct: number;
  }> {
    return api.get('/api/v1/analytics/ml-stats');
  },

  async getGhosting(): Promise<{
    total_ghosted: number;
    ghost_rate: number;
    ghosted_applications: { id: string; company: string; role?: string; applied_date: string; days_waiting: number }[];
  }> {
    return api.get('/api/v1/analytics/ghosting');
  },
};

// Tags API
export interface Tag {
  id: string;
  name: string;
  color: string;
}

export const tagsApi = {
  async list(): Promise<Tag[]> {
    return api.get<Tag[]>('/api/v1/tags');
  },

  async create(name: string, color?: string): Promise<Tag> {
    return api.post<Tag>('/api/v1/tags', { name, color });
  },

  async update(id: string, data: { name?: string; color?: string }): Promise<Tag> {
    return api.patch<Tag>(`/api/v1/tags/${id}`, data);
  },

  async delete(id: string): Promise<void> {
    await api.delete(`/api/v1/tags/${id}`);
  },
};

// Gmail API
export interface PendingApplication {
  id: string;
  user_id: string;
  email_id: string;
  email_subject: string;
  email_snippet?: string;
  email_from?: string;  // Sender info for leads extraction
  email_date: string;
  parsed_company?: string;
  parsed_role?: string;
  parsed_status?: string;
  parsed_job_url?: string;
  confidence_score: number;
  status: 'pending' | 'confirmed' | 'rejected';
}

export const gmailApi = {
  async sync(): Promise<{ status: string; message: string }> {
    return api.post('/api/v1/gmail/sync', {});
  },

  async listPending(): Promise<PendingApplication[]> {
    return api.get<PendingApplication[]>('/api/v1/gmail/pending');
  },

  async confirm(id: string): Promise<{ message: string; application_id: string }> {
    return api.post(`/api/v1/gmail/pending/${id}/confirm`, {});
  },

  async reject(id: string, reason?: string): Promise<{ message: string }> {
    const params = reason ? `?reason=${reason}` : '';
    return api.delete(`/api/v1/gmail/pending/${id}${params}`);
  },

  async undoReject(id: string): Promise<{ message: string; id: string }> {
    return api.post(`/api/v1/gmail/pending/${id}/undo-reject`, {});
  },

  async cleanup(): Promise<{ message: string; deleted_count: number }> {
    return api.delete('/api/v1/gmail/pending/cleanup');
  },

  async processWithAI(): Promise<{ message: string; added: number; discarded: number }> {
    return api.post('/api/v1/gmail/pending/process-ai', {});
  },
};

// Leads API (global shared job board)
export interface LeadApiResponse {
  id: string;
  company: string;
  role?: string;
  job_site?: string;
  job_url?: string;
  recruiter_name?: string;
  recruiter_email?: string;
  source_email_id?: string;
  date: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export const leadsApi = {
  async list(params?: {
    role?: string;
    company?: string;
    search?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<LeadApiResponse[]> {
    return api.get<LeadApiResponse[]>('/api/v1/leads', params);
  },

  async get(id: string): Promise<LeadApiResponse> {
    return api.get<LeadApiResponse>(`/api/v1/leads/${id}`);
  },

  async create(data: {
    company: string;
    role?: string;
    job_site?: string;
    job_url?: string;
    recruiter_name?: string;
    recruiter_email?: string;
  }): Promise<LeadApiResponse> {
    return api.post<LeadApiResponse>('/api/v1/leads', data);
  },

  async archive(id: string): Promise<{ message: string }> {
    return api.delete(`/api/v1/leads/${id}`);
  },

  async count(): Promise<{ count: number }> {
    return api.get('/api/v1/leads/count');
  },
};
