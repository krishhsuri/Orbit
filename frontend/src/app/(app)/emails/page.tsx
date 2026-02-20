'use client';

import { useState, useRef, useEffect } from 'react';
import { Mail, RefreshCw, Loader2, Trash2, Sparkles, Settings, Search, Filter, Check, X, ChevronDown } from 'lucide-react';
import styles from './page.module.css';
import { useGmail } from '@/hooks/use-gmail';
import { formatDistanceToNow } from 'date-fns';

const REJECT_REASONS = [
  { value: 'not_for_me', label: 'Not for me', desc: 'Valid job email but not mine' },
  { value: 'not_job_email', label: 'Not a job email', desc: 'Newsletter, spam, promo' },
  { value: 'wrong_detection', label: 'Wrong detection', desc: 'AI misclassified this' },
  { value: 'duplicate', label: 'Duplicate', desc: 'Already tracking this' },
];

export default function EmailsPage() {
  const {
    pendingApplications,
    isLoading,
    syncEmails,
    isSyncing,
    confirmApplication,
    rejectApplication,
    cleanupNonJobRelated,
    isCleaning,
    processWithAI,
    isProcessingAI,
  } = useGmail({ autoSync: true });

  const [searchQuery, setSearchQuery] = useState('');
  const [openDropdownId, setOpenDropdownId] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpenDropdownId(null);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleSync = () => syncEmails();
  const handleCleanup = () => cleanupNonJobRelated();
  const handleProcessAI = () => processWithAI();

  const handleConnect = () => {
    window.location.href = 'http://localhost:8000/auth/login';
  };

  // Filter emails by search
  const filtered = pendingApplications.filter((app) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      (app.parsed_company || '').toLowerCase().includes(q) ||
      (app.email_subject || '').toLowerCase().includes(q)
    );
  });

  // Determine status label
  function getStatusLabel(app: any): string {
    if (app.parsed_status === 'confirmed') return 'SYNCED';
    if (app.parsed_status === 'rejected' || app.parsed_status === 'ignored') return 'IGNORED';
    return 'DETECTED';
  }

  function getStatusClass(label: string): string {
    if (label === 'SYNCED') return styles.statusSynced;
    if (label === 'IGNORED') return styles.statusIgnored;
    return styles.statusDetected;
  }

  return (
    <div className={styles.page}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.pageTitle}>Email Sync</h1>
          <span className={styles.headerSep}>/</span>
          <div className={styles.connectedBadge}>
            <span className={styles.connectedDot} />
            <span className={styles.connectedText}>CONNECTED</span>
          </div>
        </div>
        <div className={styles.headerRight}>
          <button
            className={styles.settingsButton}
            onClick={handleCleanup}
            disabled={isCleaning}
          >
            {isCleaning ? <Loader2 size={14} className={styles.spin} /> : <Trash2 size={14} />}
            Cleanup
          </button>
          <button
            className={styles.settingsButton}
            onClick={handleProcessAI}
            disabled={isProcessingAI || pendingApplications.length === 0}
          >
            {isProcessingAI ? <Loader2 size={14} className={styles.spin} /> : <Sparkles size={14} />}
            AI Process
          </button>
          <button
            className={styles.syncButton}
            onClick={handleSync}
            disabled={isSyncing}
          >
            {isSyncing ? <Loader2 size={14} className={styles.spin} /> : <RefreshCw size={14} />}
            {isSyncing ? 'Syncing...' : 'Sync Now'}
          </button>
        </div>
      </header>

      {/* Stats Bar */}
      <div className={styles.statsBar}>
        <div className={styles.statsLeft}>
          <div className={styles.stat}>
            <span className={styles.statLabel}>TOTAL SCANNED</span>
            <div className={styles.statValue}>
              <span className={styles.statNumber}>{pendingApplications.length}</span>
              <span className={styles.statUnit}>emails</span>
            </div>
          </div>
          <div className={styles.stat}>
            <span className={styles.statLabel}>FOUND APPLICATIONS</span>
            <div className={styles.statValue}>
              <span className={styles.statNumber}>
                {pendingApplications.filter((a) => a.confidence_score > 0.5).length}
              </span>
              <span className={styles.statUnit}>matches</span>
            </div>
          </div>
          <div className={styles.stat}>
            <span className={styles.statLabel}>LAST SYNC</span>
            <div className={styles.statValue}>
              <span className={styles.statNumber}>now</span>
            </div>
          </div>
        </div>
        <div className={styles.statsRight}>
          <div className={styles.searchWrapper}>
            <Search size={14} className={styles.searchIcon} />
            <input
              type="text"
              placeholder="Search subject or sender..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={styles.searchInput}
            />
          </div>
          <button className={styles.filterButton}>
            <Filter size={14} />
          </button>
        </div>
      </div>

      {/* Table Header */}
      <div className={styles.tableHeader}>
        <div className={styles.colStatus}>Status</div>
        <div className={styles.colSender}>Sender</div>
        <div className={styles.colSubject}>Subject</div>
        <div className={styles.colDate}>Received</div>
        <div className={styles.colActions}>Actions</div>
      </div>

      {/* Table Body */}
      <div className={styles.tableBody}>
        {isLoading ? (
          <div className={styles.loadingState}>
            <Loader2 size={24} className={styles.spin} />
            <span>Loading emails...</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className={styles.emptyState}>
            <Mail size={40} className={styles.emptyIcon} />
            <h3>No pending emails</h3>
            <p>
              {isSyncing
                ? 'Syncing your emails...'
                : 'All caught up! Click Sync Now to check for new emails.'}
            </p>
            {!isSyncing && (
              <button className={styles.syncButton} onClick={handleSync}>
                <RefreshCw size={14} />
                Sync Now
              </button>
            )}
          </div>
        ) : (
          filtered.map((app) => {
            const statusLabel = getStatusLabel(app);
            const isPending = app.status === 'pending';
            return (
              <div key={app.id} className={styles.tableRow}>
                <div className={styles.colStatus}>
                  <span className={`${styles.statusBadge} ${getStatusClass(statusLabel)}`}>
                    {statusLabel}
                  </span>
                </div>
                <div className={styles.colSender}>
                  <div className={styles.senderAvatar}>
                    {(app.parsed_company || app.email_subject || '?')[0].toUpperCase()}
                  </div>
                  <span className={styles.senderName}>
                    {app.parsed_company || 'Unknown'}
                  </span>
                </div>
                <div className={styles.colSubject}>
                  <span className={styles.subjectText}>{app.email_subject}</span>
                  {app.email_snippet && (
                    <span className={styles.snippetText}>
                      — {app.email_snippet.substring(0, 60)}...
                    </span>
                  )}
                </div>
                <div className={styles.colDate}>
                  {formatDistanceToNow(new Date(app.email_date), { addSuffix: false })}
                </div>
                <div className={styles.colActions}>
                  {isPending && (
                    <div className={styles.actionButtons}>
                      <button
                        className={styles.confirmBtn}
                        onClick={(e) => { e.stopPropagation(); confirmApplication(app.id); }}
                        title="Confirm — add to tracker"
                      >
                        <Check size={14} />
                      </button>
                      <div className={styles.rejectWrapper} ref={openDropdownId === app.id ? dropdownRef : null}>
                        <button
                          className={styles.rejectBtn}
                          onClick={(e) => {
                            e.stopPropagation();
                            setOpenDropdownId(openDropdownId === app.id ? null : app.id);
                          }}
                          title="Dismiss"
                        >
                          <X size={14} />
                          <ChevronDown size={10} />
                        </button>
                        {openDropdownId === app.id && (
                          <div className={styles.rejectDropdown}>
                            {REJECT_REASONS.map((r) => (
                              <button
                                key={r.value}
                                className={styles.rejectOption}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  rejectApplication({ id: app.id, reason: r.value });
                                  setOpenDropdownId(null);
                                }}
                              >
                                <span className={styles.rejectOptionLabel}>{r.label}</span>
                                <span className={styles.rejectOptionDesc}>{r.desc}</span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
