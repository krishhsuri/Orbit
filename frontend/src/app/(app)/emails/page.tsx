'use client';

import { Header } from '@/components/layout/Header';
import { Mail, RefreshCw, Link2, Check, X, Loader2, AlertCircle, Trash2, Sparkles } from 'lucide-react';
import styles from './page.module.css';
import { useGmail } from '@/hooks/use-gmail';
import { formatDistanceToNow } from 'date-fns';

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
    isProcessingAI
  } = useGmail({ autoSync: true }); // Auto-sync on page load

  const handleSync = () => {
    syncEmails();
  };

  const handleCleanup = () => {
    cleanupNonJobRelated();
  };

  const handleProcessAI = () => {
    processWithAI();
  };

  const handleConnect = () => {
    // Redirect to backend login endpoint which initiates Google OAuth
    // This ensures we get the correct scopes and refresh token
    window.location.href = 'http://localhost:8000/auth/login';
  };

  return (
    <div className={styles.page}>
      <Header 
        title="Email Sync" 
        subtitle="Automatically detect applications from your Gmail" 
        showAddButton={false}
      >
        <div className={styles.headerButtons}>
          <button 
            className={styles.cleanupButton} 
            onClick={handleCleanup}
            disabled={isCleaning}
            title="Remove non-job-related emails"
          >
            {isCleaning ? <Loader2 className={styles.spin} size={16} /> : <Trash2 size={16} />}
            {isCleaning ? 'Cleaning...' : 'Cleanup'}
          </button>
          <button 
            className={styles.aiButton} 
            onClick={handleProcessAI}
            disabled={isProcessingAI || pendingApplications.length === 0}
            title="Let AI automatically sort emails into applications"
          >
            {isProcessingAI ? <Loader2 className={styles.spin} size={16} /> : <Sparkles size={16} />}
            {isProcessingAI ? 'Processing...' : 'Process with AI'}
          </button>
          <button 
            className={styles.syncButton} 
            onClick={handleSync}
            disabled={isSyncing}
          >
            {isSyncing ? <Loader2 className={styles.spin} size={16} /> : <RefreshCw size={16} />}
            {isSyncing ? 'Syncing...' : 'Sync Now'}
          </button>
        </div>
      </Header>
      
      <div className={styles.content}>
        {isLoading ? (
          <div className={styles.loading}>
            <Loader2 className={styles.spin} size={32} />
            <p>Loading pending applications...</p>
          </div>
        ) : pendingApplications.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>
              <Mail size={48} />
            </div>
            <h2>No pending applications</h2>
            <p>Sync your emails to find new job applications</p>
            
            <button className={styles.connectButton} onClick={handleConnect}>
              <img src="https://www.google.com/favicon.ico" alt="Google" width={20} height={20} />
              Connect Gmail
            </button>
            
            <div className={styles.features}>
              <div className={styles.feature}>
                <RefreshCw size={16} />
                <span>AI-powered detection</span>
              </div>
              <div className={styles.feature}>
                <Link2 size={16} />
                <span>Auto-link to tracker</span>
              </div>
            </div>
          </div>
        ) : (
          <div className={styles.list}>
            {pendingApplications.map((app) => (
              <div key={app.id} className={styles.card}>
                <div className={styles.cardHeader}>
                  <div className={styles.companyInfo}>
                    <h3>{app.parsed_company || 'Unknown Company'}</h3>
                    <div className={styles.meta}>
                      <span className={styles.role}>{app.parsed_role || 'Unknown Role'}</span>
                      <span className={styles.dot}>•</span>
                      <span className={styles.date}>
                        {formatDistanceToNow(new Date(app.email_date), { addSuffix: true })}
                      </span>
                    </div>
                  </div>
                  <div className={styles.confidence}>
                    <div 
                      className={styles.confidenceBadge}
                      data-level={app.confidence_score > 0.8 ? 'high' : app.confidence_score > 0.5 ? 'medium' : 'low'}
                    >
                      {Math.round(app.confidence_score * 100)}% Confidence
                    </div>
                  </div>
                </div>

                <div className={styles.emailPreview}>
                  <div className={styles.emailSubject}>
                    <Mail size={14} />
                    {app.email_subject}
                  </div>
                  <p className={styles.snippet}>{app.email_snippet}</p>
                </div>

                <div className={styles.actions}>
                  <div className={styles.parsedData}>
                    {app.parsed_status && (
                      <span className={styles.tag}>Status: {app.parsed_status}</span>
                    )}
                    {app.parsed_job_url && (
                      <a href={app.parsed_job_url} target="_blank" rel="noopener noreferrer" className={styles.link}>
                        <Link2 size={12} /> Job Link
                      </a>
                    )}
                  </div>
                  <div className={styles.buttons}>
                    <button 
                      className={styles.rejectButton}
                      onClick={() => rejectApplication(app.id)}
                      title="Dismiss"
                    >
                      <X size={18} />
                    </button>
                    <button 
                      className={styles.confirmButton}
                      onClick={() => confirmApplication(app.id)}
                      title="Add to Applications"
                    >
                      <Check size={18} />
                      Add to Tracker
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
