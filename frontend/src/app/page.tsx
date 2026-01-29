'use client';

import { Header } from '@/components/layout/Header';
import { useApplications } from '@/hooks/use-applications';
import { 
  Briefcase, 
  PhoneCall, 
  Trophy, 
  TrendingUp,
  Clock,
  ArrowUpRight,
  Zap
} from 'lucide-react';
import styles from './page.module.css';

export default function DashboardPage() {
  const { data, isLoading, error } = useApplications();
  const applications = data?.applications || [];

  if (isLoading) {
    return (
      <div className={styles.page}>
        <Header title="Dashboard" subtitle="Loading..." />
        <div className={styles.loadingContainer}>
          <div className={styles.spinner}></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.page}>
        <Header title="Dashboard" subtitle="Error" />
        <div className={styles.errorContainer}>
          <p>Failed to load dashboard. Please try again.</p>
        </div>
      </div>
    );
  }
  
  // Calculate Stats
  const now = new Date();
  const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

  const stats = {
    total: applications.length,
    active: applications.filter(a => ['applied', 'screening', 'oa', 'interview'].includes(a.status)).length,
    interviews: applications.filter(a => a.status === 'interview').length,
    offers: applications.filter(a => ['offer', 'accepted'].includes(a.status)).length,
    thisWeek: applications.filter(a => new Date(a.appliedDate) >= weekAgo).length,
  };

  // Get recent activity (last 5 updated)
  const recentActivity = [...applications]
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
    .slice(0, 4)
    .map(app => ({
      id: app.id,
      action: app.status === 'applied' ? 'Applied to' : 
              app.status === 'interview' ? 'Interview with' :
              app.status === 'offer' ? 'Received offer from' :
              'Updated',
      company: app.company,
      role: app.role,
      time: getRelativeTime(app.updatedAt),
      type: app.status,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      status: app.status, 
    }));

  // Get upcoming (interviews scheduled)
  const upcomingDeadlines = applications
    .filter(a => a.status === 'interview' || a.status === 'oa')
    .slice(0, 3)
    .map(app => ({
      id: app.id,
      company: app.company,
      task: app.status === 'interview' ? 'Interview' : 'Online Assessment',
      date: 'Scheduled',
      urgent: app.status === 'interview',
    }));

  const statsCards = [
    { label: 'Total Applications', value: stats.total, icon: Briefcase, change: `+${stats.thisWeek} this week` },
    { label: 'In Progress', value: stats.active, icon: Clock, change: `${stats.active} pending response` },
    { label: 'Interviews', value: stats.interviews, icon: PhoneCall, change: `${stats.interviews} scheduled` },
    { label: 'Offers', value: stats.offers, icon: Trophy, change: stats.offers > 0 ? '🎉 Congrats!' : 'Keep going!' },
  ];

  // Calculate weekly goal progress
  const weeklyGoal = 10;
  const weeklyProgress = Math.min((stats.thisWeek / weeklyGoal) * 100, 100);

  return (
    <div className={styles.page}>
      <Header title="Dashboard" subtitle="Welcome back! Here's your job search overview." />
      
      <div className={styles.content}>
        {/* Stats Grid */}
        <section className={styles.statsGrid}>
          {statsCards.map((stat, index) => (
            <div key={index} className={styles.statCard}>
              <div className={styles.statIcon}>
                <stat.icon size={20} />
              </div>
              <div className={styles.statContent}>
                <span className={styles.statValue}>{stat.value}</span>
                <span className={styles.statLabel}>{stat.label}</span>
                <span className={styles.statChange}>{stat.change}</span>
              </div>
            </div>
          ))}
        </section>

        <div className={styles.mainGrid}>
          {/* Weekly Goal */}
          <section className={styles.card}>
            <div className={styles.cardHeader}>
              <h2 className={styles.cardTitle}>
                <Zap size={18} />
                Weekly Goal
              </h2>
            </div>
            <div className={styles.cardContent}>
              <div className={styles.goalProgress}>
                <div className={styles.goalInfo}>
                  <span className={styles.goalCurrent}>{stats.thisWeek}</span>
                  <span className={styles.goalTotal}>/ {weeklyGoal} applications</span>
                </div>
                <div className={styles.progressBar}>
                  <div className={styles.progressFill} style={{ width: `${weeklyProgress}%` }} />
                </div>
                <span className={styles.goalMessage}>
                  {stats.thisWeek >= weeklyGoal 
                    ? '🎉 Goal reached! Great work!'
                    : `🔥 ${weeklyGoal - stats.thisWeek} more to hit your goal!`}
                </span>
              </div>
            </div>
          </section>

          {/* Upcoming Deadlines */}
          <section className={styles.card}>
            <div className={styles.cardHeader}>
              <h2 className={styles.cardTitle}>
                <Clock size={18} />
                Upcoming
              </h2>
            </div>
            <div className={styles.cardContent}>
              {upcomingDeadlines.length > 0 ? (
                <ul className={styles.deadlineList}>
                  {upcomingDeadlines.map((item) => (
                    <li key={item.id} className={styles.deadlineItem}>
                      <div className={styles.deadlineInfo}>
                        <span className={styles.deadlineCompany}>{item.company}</span>
                        <span className={styles.deadlineTask}>{item.task}</span>
                      </div>
                      <span className={`${styles.deadlineDate} ${item.urgent ? styles.urgent : ''}`}>
                        {item.date}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className={styles.emptyText}>No upcoming interviews or OAs</p>
              )}
            </div>
          </section>

          {/* Recent Activity */}
          <section className={`${styles.card} ${styles.activityCard}`}>
            <div className={styles.cardHeader}>
              <h2 className={styles.cardTitle}>
                <TrendingUp size={18} />
                Recent Activity
              </h2>
              <a href="/applications" className={styles.viewAll}>
                View all <ArrowUpRight size={14} />
              </a>
            </div>
            <div className={styles.cardContent}>
              {recentActivity.length > 0 ? (
                <ul className={styles.activityList}>
                  {recentActivity.map((item) => (
                    <li key={item.id} className={styles.activityItem}>
                      <div className={`${styles.activityDot} ${styles[item.type] || ''}`} />
                      <div className={styles.activityContent}>
                        <span className={styles.activityAction}>
                          {item.action} <strong>{item.company}</strong>
                        </span>
                        <span className={styles.activityRole}>{item.role}</span>
                      </div>
                      <span className={styles.activityTime}>{item.time}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className={styles.emptyText}>No recent activity. Add your first application!</p>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function getRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'Yesterday';
  return `${diffDays} days ago`;
}
