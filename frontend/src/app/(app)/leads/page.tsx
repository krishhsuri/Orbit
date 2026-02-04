'use client';

import { Header } from '@/components/layout/Header';
import { Users, Link2, Briefcase, Mail, ExternalLink, Loader2, RefreshCw } from 'lucide-react';
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
  // Fetch pending applications and extract lead info
  const { data: pendingApps, isLoading, refetch } = useQuery({
    queryKey: ['gmail', 'pending'],
    queryFn: () => gmailApi.listPending(),
    refetchInterval: 15000,
  });

  // Transform pending apps into leads
  const leads: Lead[] = (pendingApps || []).map((app: any) => {
    // Extract links from snippet
    const urlRegex = /(https?:\/\/[^\s<>"]+)/g;
    const links = (app.email_snippet || '').match(urlRegex) || [];
    
    // Extract recruiter name from email pattern "Name <email>"
    const fromMatch = (app.email_from || '').match(/^([^<]+)\s*</);
    const recruiterName = fromMatch ? fromMatch[1].trim() : null;
    
    // Extract email
    const emailMatch = (app.email_from || '').match(/<([^>]+)>/) || 
                       (app.email_from || '').match(/([^\s]+@[^\s]+)/);
    const recruiterEmail = emailMatch ? emailMatch[1] : app.email_from;

    return {
      id: app.id,
      company: app.parsed_company || 'Unknown Company',
      role: app.parsed_role,
      recruiterName,
      recruiterEmail,
      links: links.slice(0, 3), // Max 3 links
      source: app.email_subject || 'Email',
      date: app.email_date,
    };
  });

  return (
    <div className={styles.page}>
      <Header 
        title="Leads" 
        subtitle="Extracted contacts and links from job emails" 
        showAddButton={false}
      >
        <button 
          className={styles.refreshButton}
          onClick={() => refetch()}
          disabled={isLoading}
        >
          {isLoading ? <Loader2 className={styles.spin} size={16} /> : <RefreshCw size={16} />}
          Refresh
        </button>
      </Header>
      
      <div className={styles.content}>
        {isLoading ? (
          <div className={styles.loading}>
            <Loader2 className={styles.spin} size={32} />
            <p>Extracting leads from emails...</p>
          </div>
        ) : leads.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>
              <Users size={48} />
            </div>
            <h2>No leads yet</h2>
            <p>Sync your emails to extract recruiter contacts and job links</p>
          </div>
        ) : (
          <div className={styles.grid}>
            {leads.map((lead) => (
              <div key={lead.id} className={styles.card}>
                <div className={styles.cardHeader}>
                  <div className={styles.companyBadge}>
                    <Briefcase size={14} />
                    <span>{lead.company}</span>
                  </div>
                  <span className={styles.date}>
                    {formatDistanceToNow(new Date(lead.date), { addSuffix: true })}
                  </span>
                </div>
                
                {lead.role && (
                  <h3 className={styles.role}>{lead.role}</h3>
                )}
                
                {(lead.recruiterName || lead.recruiterEmail) && (
                  <div className={styles.recruiter}>
                    <Mail size={14} />
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
                  </div>
                )}
                
                {lead.links.length > 0 && (
                  <div className={styles.links}>
                    <span className={styles.linksLabel}>
                      <Link2 size={12} />
                      Links
                    </span>
                    <div className={styles.linksList}>
                      {lead.links.map((link, idx) => (
                        <a 
                          key={idx}
                          href={link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={styles.link}
                        >
                          <ExternalLink size={12} />
                          {new URL(link).hostname.replace('www.', '')}
                        </a>
                      ))}
                    </div>
                  </div>
                )}
                
                <div className={styles.source}>
                  <span>From: {lead.source.slice(0, 50)}{lead.source.length > 50 ? '...' : ''}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
