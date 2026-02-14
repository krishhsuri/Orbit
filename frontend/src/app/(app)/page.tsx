'use client';

import { useApplications } from '@/hooks/use-applications';
import {
  Briefcase,
  PhoneCall,
  Trophy,
  Clock,
  Send,
  Calendar,
  FileText,
  MoreHorizontal,
  ChevronLeft,
  ChevronRight,
  Filter,
  Loader2,
  Plus,
  Search,
} from 'lucide-react';
import Link from 'next/link';
import { useMemo } from 'react';
import styles from './page.module.css';

// ── Helper ──────────────────────────────────────────
function getRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m`;
  if (diffHours < 24) return `${diffHours}h`;
  if (diffDays === 1) return '1d';
  return `${diffDays}d`;
}

function getStatusLabel(status: string): string {
  switch (status) {
    case 'applied': return 'APPLICATION_SENT';
    case 'interview': return 'INTERVIEW_SCHEDULED';
    case 'screening': return 'SCREENING';
    case 'oa': return 'ONLINE_ASSESSMENT';
    case 'offer': return 'OFFER_RECEIVED';
    case 'accepted': return 'ACCEPTED';
    case 'rejected': return 'REJECTED';
    default: return 'STATUS_UPDATE';
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'applied': return '#3b82f6';
    case 'interview': return '#22c55e';
    case 'screening': return '#a855f7';
    case 'oa': return '#f59e0b';
    case 'offer': return '#22c55e';
    case 'accepted': return '#22c55e';
    case 'rejected': return '#ef4444';
    default: return '#6b7280';
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'applied': return <Send size={16} />;
    case 'interview': return <Calendar size={16} />;
    case 'screening': return <FileText size={16} />;
    case 'oa': return <FileText size={16} />;
    case 'offer': return <Trophy size={16} />;
    default: return <Send size={16} />;
  }
}

// ── Mini Calendar ───────────────────────────────────
function MiniCalendar() {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();
  const today = now.getDate();
  const monthName = now.toLocaleString('default', { month: 'long' });
  const firstDay = (new Date(year, month, 1).getDay() + 6) % 7;
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const days = [];
  for (let i = 0; i < firstDay; i++) {
    days.push(<div key={`b${i}`} className={styles.calBlank} />);
  }
  for (let d = 1; d <= daysInMonth; d++) {
    days.push(
      <div
        key={d}
        className={`${styles.calDay} ${d === today ? styles.calToday : ''}`}
      >
        {d}
      </div>
    );
  }

  return (
    <div className={styles.calendarWidget}>
      <div className={styles.calHeader}>
        <span className={styles.calMonth}>{monthName} {year}</span>
        <div className={styles.calNav}>
          <button className={styles.calNavBtn}><ChevronLeft size={12} /></button>
          <button className={styles.calNavBtn}><ChevronRight size={12} /></button>
        </div>
      </div>
      <div className={styles.calGrid}>
        {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((d, i) => (
          <div key={i} className={styles.calLabel}>{d}</div>
        ))}
        {days}
      </div>
    </div>
  );
}

// ── Main Dashboard ──────────────────────────────────
export default function DashboardPage() {
  const { data, isLoading, error } = useApplications();
  const applications = data?.applications || [];

  const stats = useMemo(() => {
    const total = applications.length;
    const interviews = applications.filter((a) => a.status === 'interview').length;
    const responded = applications.filter((a) =>
      ['interview', 'offer', 'accepted', 'screening'].includes(a.status)
    ).length;
    const rate = total > 0 ? Math.round((responded / total) * 100) : 0;
    return { total, interviews, rate };
  }, [applications]);

  const recentActivity = useMemo(() => {
    return [...applications]
      .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
      .slice(0, 5)
      .map((app) => ({
        id: app.id,
        action:
          app.status === 'applied' ? 'Applied to' :
          app.status === 'interview' ? 'Scheduled interview with' :
          app.status === 'offer' ? 'Received offer from' :
          `Updated`,
        company: app.company,
        role: app.role,
        time: getRelativeTime(app.updatedAt),
        status: app.status,
      }));
  }, [applications]);

  const upcomingDeadlines = useMemo(() => {
    return applications
      .filter((a) => ['interview', 'screening', 'oa'].includes(a.status))
      .slice(0, 3)
      .map((app, i) => ({
        id: app.id,
        company: app.company,
        task: app.status === 'interview' ? 'Interview' : app.status === 'oa' ? 'Online Assessment' : 'Screening',
        role: app.role,
        urgency: i === 0 ? 'high' : i === 1 ? 'medium' : 'low',
        daysLabel: i === 0 ? '2 days left' : i === 1 ? '4 days left' : 'Next week',
        progress: i === 0 ? 75 : i === 1 ? 50 : 25,
      }));
  }, [applications]);

  // Weekly mock bars (sourced from real data day-of-week distribution)
  const weeklyBars = useMemo(() => {
    const bars = [0, 0, 0, 0, 0, 0, 0];
    applications.forEach((a) => {
      const day = (new Date(a.appliedDate).getDay() + 6) % 7;
      bars[day]++;
    });
    const max = Math.max(...bars, 1);
    return bars.map((v) => Math.round((v / max) * 100));
  }, [applications]);

  if (isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.loadingState}>
          <Loader2 className={styles.spin} size={20} />
          <span>Loading dashboard...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.page}>
        <div className={styles.loadingState}>
          <span>Failed to load dashboard.</span>
        </div>
      </div>
    );
  }

  const dayLabels = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];

  return (
    <div className={styles.page}>
      {/* ── Header ──────────────────────────────── */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.pageTitle}>Dashboard</h1>
          <span className={styles.headerSep}>/</span>
          <span className={styles.headerMeta}>OVERVIEW</span>
        </div>
        <div className={styles.headerRight}>
          <div className={styles.searchWrapper}>
            <Search size={14} className={styles.searchIcon} />
            <input
              className={styles.searchInput}
              placeholder="Search..."
              type="text"
            />
          </div>
          <Link href="/applications" className={styles.newButton}>
            <Plus size={14} />
            New Application
          </Link>
        </div>
      </div>

      {/* ── Scrollable Content ──────────────────── */}
      <div className={styles.scrollArea}>
        <div className={styles.contentGrid}>
          {/* ── Stat Cards ─────────────────────── */}
          <div className={styles.statsRow}>
            {/* Total Applications */}
            <div className={styles.statCard}>
              <div className={styles.statTop}>
                <div>
                  <p className={styles.statLabel}>Total Applications</p>
                  <h3 className={styles.statValue}>{stats.total}</h3>
                </div>
                <span className={styles.statBadgeGreen}>+{Math.round(stats.total * 0.12)}%</span>
              </div>
              <div className={styles.miniChart}>
                {[20, 40, 30, 60, 45, 75, 65].map((h, i) => (
                  <div
                    key={i}
                    className={styles.miniBar}
                    style={{ height: `${h}%` }}
                  />
                ))}
              </div>
            </div>

            {/* Interviews */}
            <div className={styles.statCard}>
              <div className={styles.statTop}>
                <div>
                  <p className={styles.statLabel}>Interviews</p>
                  <h3 className={styles.statValue}>{stats.interviews}</h3>
                </div>
                <span className={styles.statBadgeBlue}>Active</span>
              </div>
              <div className={styles.miniChart}>
                {[10, 10, 30, 20, 50, 80, 40].map((h, i) => (
                  <div
                    key={i}
                    className={styles.miniBar}
                    style={{ height: `${h}%` }}
                  />
                ))}
              </div>
            </div>

            {/* Response Rate */}
            <div className={styles.statCard}>
              <div className={styles.statTop}>
                <div>
                  <p className={styles.statLabel}>Response Rate</p>
                  <h3 className={styles.statValue}>
                    {stats.rate}<span className={styles.statUnit}>%</span>
                  </h3>
                </div>
                <span className={styles.statBadgeNeutral}>Avg</span>
              </div>
              <div className={styles.miniChart}>
                {[40, 35, 50, 45, 60, 55, 70].map((h, i) => (
                  <div
                    key={i}
                    className={styles.miniBar}
                    style={{ height: `${h}%` }}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* ── Main Layout: Left + Right ──────── */}
          <div className={styles.mainLayout}>
            {/* Left Column */}
            <div className={styles.leftColumn}>
              {/* Recent Activity */}
              <div className={styles.panel}>
                <div className={styles.panelHeader}>
                  <h3 className={styles.panelTitle}>Recent Activity</h3>
                  <Link href="/applications" className={styles.panelAction}>View All</Link>
                </div>
                <div className={styles.activityList}>
                  {recentActivity.map((item) => (
                    <Link
                      href={`/applications/${item.id}`}
                      key={item.id}
                      className={styles.activityItem}
                    >
                      <div className={styles.activityIcon}>
                        {getStatusIcon(item.status)}
                      </div>
                      <div className={styles.activityContent}>
                        <p className={styles.activityText}>
                          {item.action}{' '}
                          <span className={styles.activityHighlight}>{item.role}</span>
                          {' at '}
                          <span className={styles.activityHighlight}>{item.company}</span>
                        </p>
                        <p className={styles.activityMeta}>
                          <span
                            className={styles.activityDot}
                            style={{ backgroundColor: getStatusColor(item.status) }}
                          />
                          {getStatusLabel(item.status)}
                        </p>
                      </div>
                      <span className={styles.activityTime}>{item.time}</span>
                    </Link>
                  ))}
                  {recentActivity.length === 0 && (
                    <div className={styles.emptyState}>
                      <p>No recent activity</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Weekly Activity Chart */}
              <div className={styles.panel}>
                <div className={styles.panelHeader}>
                  <h3 className={styles.panelTitle}>Weekly Activity</h3>
                  <div className={styles.chartLegend}>
                    <span className={styles.legendItem}>
                      <span className={styles.legendDotWhite} />
                      APPLICATIONS
                    </span>
                    <span className={styles.legendItem}>
                      <span className={styles.legendDotGray} />
                      INTERVIEWS
                    </span>
                  </div>
                </div>
                <div className={styles.chartArea}>
                  {weeklyBars.map((height, i) => (
                    <div key={i} className={styles.chartColumn}>
                      <div className={styles.chartBarGroup}>
                        <div
                          className={styles.chartBarBack}
                          style={{ height: `${Math.max(height * 0.3, 2)}%` }}
                        />
                        <div
                          className={styles.chartBarFront}
                          style={{ height: `${Math.max(height, 5)}%` }}
                        />
                      </div>
                      <span className={styles.chartLabel}>{dayLabels[i]}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Column */}
            <div className={styles.rightColumn}>
              <div className={styles.panel}>
                <div className={styles.panelHeader}>
                  <h3 className={styles.panelTitle}>Upcoming Deadlines</h3>
                  <button className={styles.panelFilterBtn}>
                    <Filter size={14} />
                  </button>
                </div>

                <div className={styles.deadlineList}>
                  {upcomingDeadlines.map((item) => (
                    <Link
                      href={`/applications/${item.id}`}
                      key={item.id}
                      className={styles.deadlineCard}
                    >
                      <div
                        className={styles.deadlineAccent}
                        style={{
                          backgroundColor:
                            item.urgency === 'high' ? 'rgba(239,68,68,0.8)' :
                            item.urgency === 'medium' ? 'rgba(249,115,22,0.8)' :
                            'rgba(107,114,128,0.8)',
                        }}
                      />
                      <div className={styles.deadlineTop}>
                        <span
                          className={styles.deadlineTag}
                          style={{
                            color:
                              item.urgency === 'high' ? '#f87171' :
                              item.urgency === 'medium' ? '#fb923c' : '#9ca3af',
                            backgroundColor:
                              item.urgency === 'high' ? 'rgba(248,113,113,0.1)' :
                              item.urgency === 'medium' ? 'rgba(251,146,60,0.1)' :
                              'rgba(156,163,175,0.1)',
                            borderColor:
                              item.urgency === 'high' ? 'rgba(248,113,113,0.2)' :
                              item.urgency === 'medium' ? 'rgba(251,146,60,0.2)' :
                              'rgba(156,163,175,0.2)',
                          }}
                        >
                          {item.daysLabel}
                        </span>
                        <button className={styles.deadlineMore}>
                          <MoreHorizontal size={14} />
                        </button>
                      </div>
                      <h4 className={styles.deadlineName}>{item.company}</h4>
                      <p className={styles.deadlineTask}>{item.task}</p>
                      <div className={styles.deadlineProgress}>
                        <div className={styles.deadlineProgressBar}>
                          <div
                            className={styles.deadlineProgressFill}
                            style={{
                              width: `${item.progress}%`,
                              backgroundColor:
                                item.urgency === 'high' ? 'rgba(239,68,68,0.5)' :
                                item.urgency === 'medium' ? 'rgba(249,115,22,0.5)' :
                                'rgba(107,114,128,0.5)',
                            }}
                          />
                        </div>
                      </div>
                    </Link>
                  ))}
                  {upcomingDeadlines.length === 0 && (
                    <div className={styles.emptyState}>
                      <p>No upcoming deadlines</p>
                    </div>
                  )}
                </div>

                {/* Calendar */}
                <MiniCalendar />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
