'use client';

import {
  Users,
  Link2,
  Briefcase,
  Mail,
  ExternalLink,
  Loader2,
  RefreshCw,
  Search,
} from 'lucide-react';
import styles from './page.module.css';
import { useQuery } from '@tanstack/react-query';
import { leadsApi, LeadApiResponse } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';
import { useState } from 'react';

export default function LeadsPage() {
  const [search, setSearch] = useState('');

  const { data: leads = [], isLoading, refetch } = useQuery<LeadApiResponse[]>({
    queryKey: ['leads', search],
    queryFn: () => leadsApi.list({ search: search || undefined, limit: 200 }),
    refetchInterval: 30000,
  });

  return (
    <div className={styles.page}>
      {/* ── Header ──────────────────────────── */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.pageTitle}>Leads</h1>
          <span className={styles.headerSep}>/</span>
          <span className={styles.headerMeta}>JOB_DISCOVERY</span>
          {leads.length > 0 && (
            <span className={styles.headerCount}>{leads.length}</span>
          )}
        </div>
        <div className={styles.headerRight}>
          <div className={styles.searchWrapper}>
            <Search size={14} className={styles.searchIcon} />
            <input
              className={styles.searchInput}
              placeholder="Search leads..."
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button
            className={styles.refreshBtn}
            onClick={() => refetch()}
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className={styles.spin} size={14} />
            ) : (
              <RefreshCw size={14} />
            )}
            Refresh
          </button>
        </div>
      </div>

      {/* ── Content ─────────────────────────── */}
      <div className={styles.scrollArea}>
        {isLoading ? (
          <div className={styles.loadingState}>
            <Loader2 className={styles.spin} size={20} />
            <span>Loading leads...</span>
          </div>
        ) : leads.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>
              <Users size={32} />
            </div>
            <h2 className={styles.emptyTitle}>No leads yet</h2>
            <p className={styles.emptyDesc}>
              Sync your emails to auto-discover job opportunities and recruiter contacts
            </p>
          </div>
        ) : (
          <div className={styles.grid}>
            {leads.map((lead) => (
              <div key={lead.id} className={styles.card}>
                {/* Card Header */}
                <div className={styles.cardTop}>
                  <div className={styles.companyBadge}>
                    <Briefcase size={12} />
                    <span>{lead.company}</span>
                  </div>
                  <span className={styles.cardDate}>
                    {formatDistanceToNow(new Date(lead.date), { addSuffix: true })}
                  </span>
                </div>

                {/* Role */}
                {lead.role && (
                  <h3 className={styles.cardRole}>{lead.role}</h3>
                )}

                {/* Recruiter */}
                {(lead.recruiter_name || lead.recruiter_email) && (
                  <div className={styles.recruiterRow}>
                    <div className={styles.recruiterAvatar}>
                      {(lead.recruiter_name || '?').charAt(0).toUpperCase()}
                    </div>
                    <div className={styles.recruiterInfo}>
                      {lead.recruiter_name && (
                        <span className={styles.recruiterName}>{lead.recruiter_name}</span>
                      )}
                      {lead.recruiter_email && (
                        <a
                          href={`mailto:${lead.recruiter_email}`}
                          className={styles.recruiterEmail}
                        >
                          {lead.recruiter_email}
                        </a>
                      )}
                    </div>
                    {lead.recruiter_email && (
                      <a
                        href={`mailto:${lead.recruiter_email}`}
                        className={styles.recruiterMailBtn}
                      >
                        <Mail size={14} />
                      </a>
                    )}
                  </div>
                )}

                {/* Job URL / Site */}
                {lead.job_url && (
                  <div className={styles.linksSection}>
                    <span className={styles.linksLabel}>
                      <Link2 size={10} /> {lead.job_site || 'Link'}
                    </span>
                    <div className={styles.linksList}>
                      <a
                        href={lead.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.linkChip}
                      >
                        <ExternalLink size={10} />
                        {lead.job_site || (() => {
                          try { return new URL(lead.job_url!).hostname.replace('www.', ''); } catch { return 'Link'; }
                        })()}
                      </a>
                    </div>
                  </div>
                )}

                {/* Source badge */}
                {lead.job_site && (
                  <div className={styles.cardSource}>
                    via {lead.job_site}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
