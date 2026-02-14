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
import { gmailApi } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';

interface Lead {
  id: string;
  company: string;
  role: string | null;
  recruiterName: string | null;
  recruiterEmail: string | null;
  links: string[];
  source: string;
  date: string;
}

export default function LeadsPage() {
  const { data: pendingApps, isLoading, refetch } = useQuery({
    queryKey: ['gmail', 'pending'],
    queryFn: () => gmailApi.listPending(),
    refetchInterval: 15000,
  });

  // Transform pending apps into leads
  const leads: Lead[] = (pendingApps || []).map((app: any) => {
    const urlRegex = /(https?:\/\/[^\s<>"]+)/g;
    const links = (app.email_snippet || '').match(urlRegex) || [];

    const fromMatch = (app.email_from || '').match(/^([^<]+)\s*</);
    const recruiterName = fromMatch ? fromMatch[1].trim() : null;

    const emailMatch = (app.email_from || '').match(/<([^>]+)>/) ||
                       (app.email_from || '').match(/([^\s]+@[^\s]+)/);
    const recruiterEmail = emailMatch ? emailMatch[1] : app.email_from;

    return {
      id: app.id,
      company: app.parsed_company || 'Unknown Company',
      role: app.parsed_role,
      recruiterName,
      recruiterEmail,
      links: links.slice(0, 3),
      source: app.email_subject || 'Email',
      date: app.email_date,
    };
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
            <span>Extracting leads from emails...</span>
          </div>
        ) : leads.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>
              <Users size={32} />
            </div>
            <h2 className={styles.emptyTitle}>No leads yet</h2>
            <p className={styles.emptyDesc}>
              Sync your emails to extract recruiter contacts and job links
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
                {(lead.recruiterName || lead.recruiterEmail) && (
                  <div className={styles.recruiterRow}>
                    <div className={styles.recruiterAvatar}>
                      {(lead.recruiterName || '?').charAt(0).toUpperCase()}
                    </div>
                    <div className={styles.recruiterInfo}>
                      {lead.recruiterName && (
                        <span className={styles.recruiterName}>{lead.recruiterName}</span>
                      )}
                      {lead.recruiterEmail && (
                        <a
                          href={`mailto:${lead.recruiterEmail}`}
                          className={styles.recruiterEmail}
                        >
                          {lead.recruiterEmail}
                        </a>
                      )}
                    </div>
                    {lead.recruiterEmail && (
                      <a
                        href={`mailto:${lead.recruiterEmail}`}
                        className={styles.recruiterMailBtn}
                      >
                        <Mail size={14} />
                      </a>
                    )}
                  </div>
                )}

                {/* Links */}
                {lead.links.length > 0 && (
                  <div className={styles.linksSection}>
                    <span className={styles.linksLabel}>
                      <Link2 size={10} /> Links
                    </span>
                    <div className={styles.linksList}>
                      {lead.links.map((link, idx) => {
                        let hostname = link;
                        try { hostname = new URL(link).hostname.replace('www.', ''); } catch {}
                        return (
                          <a
                            key={idx}
                            href={link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={styles.linkChip}
                          >
                            <ExternalLink size={10} />
                            {hostname}
                          </a>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Source */}
                <div className={styles.cardSource}>
                  {lead.source.slice(0, 60)}{lead.source.length > 60 ? '…' : ''}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
