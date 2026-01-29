'use client';

import { Header } from '@/components/layout/Header';
import { 
  useAnalyticsSummary,
  useAnalyticsFunnel,
  useAnalyticsSources,
  useAnalyticsInsights
} from '@/hooks/use-applications';
import { 
  TrendingDown, 
  TrendingUp,
  Target,
  Clock,
  Users,
  Lightbulb,
  AlertCircle
} from 'lucide-react';
import styles from './page.module.css';

export default function AnalyticsPage() {
  const { data: summary, isLoading: isLoadingSummary } = useAnalyticsSummary();
  const { data: funnelData, isLoading: isLoadingFunnel } = useAnalyticsFunnel();
  const { data: sourceData, isLoading: isLoadingSources } = useAnalyticsSources();
  const { data: insightsData, isLoading: isLoadingInsights } = useAnalyticsInsights();

  const isLoading = isLoadingSummary || isLoadingFunnel || isLoadingSources || isLoadingInsights;

  if (isLoading) {
    return (
      <div className={styles.page}>
        <Header title="Analytics" subtitle="Loading analytics..." showAddButton={false} />
        <div className={styles.loadingContainer}>
          <div className={styles.spinner}></div>
        </div>
      </div>
    );
  }

  // Use defaults if data is missing or empty
  const funnel = funnelData?.stages || [];
  const sources = sourceData?.sources || [];
  const insights = insightsData?.insights || [];
  const stats = summary || { total: 0, active: 0, interviews: 0, offers: 0, this_week: 0 };

  // Calculate derived stats
  const conversionRate = stats.total > 0 ? (stats.offers / stats.total) * 100 : 0;
  
  // Calculate global response rate from sources data
  const totalResponded = sources.reduce((acc, curr) => acc + curr.responded, 0);
  const totalTrackedSource = sources.reduce((acc, curr) => acc + curr.total, 0);
  const responseRate = totalTrackedSource > 0 ? (totalResponded / totalTrackedSource) * 100 : 0;

  return (
    <div className={styles.page}>
      <Header title="Analytics" subtitle="Track your job search performance" showAddButton={false} />
      
      <div className={styles.content}>
        {/* Quick Stats */}
        <div className={styles.quickStats}>
          <div className={styles.quickStat}>
            <Target size={20} />
            <div>
              <span className={styles.statValue}>{conversionRate.toFixed(1)}%</span>
              <span className={styles.statLabel}>Overall Conversion</span>
            </div>
          </div>
          <div className={styles.quickStat}>
            <Clock size={20} />
            <div>
              <span className={styles.statValue}>--</span>
              <span className={styles.statLabel}>Avg. Response Time</span>
            </div>
          </div>
          <div className={styles.quickStat}>
            <Users size={20} />
            <div>
              <span className={styles.statValue}>{responseRate.toFixed(1)}%</span>
              <span className={styles.statLabel}>Response Rate</span>
            </div>
          </div>
        </div>

        <div className={styles.grid}>
          {/* Conversion Funnel */}
          <section className={styles.card}>
            <h2 className={styles.cardTitle}>Conversion Funnel</h2>
            {funnel.length > 0 ? (
              <div className={styles.funnel}>
                {funnel.map((stage) => (
                  <div key={stage.status} className={styles.funnelStage}>
                    <div className={styles.funnelInfo}>
                      <span className={styles.stageName}>{stage.status}</span>
                      <span className={styles.stageCount}>{stage.count}</span>
                    </div>
                    <div className={styles.funnelBar}>
                      <div 
                        className={styles.funnelFill}
                        style={{ width: `${stage.percentage}%` }}
                      />
                    </div>
                    <span className={styles.stagePercentage}>{stage.percentage}%</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.emptyState}>
                <p>No data available yet</p>
              </div>
            )}
          </section>

          {/* Response by Source */}
          <section className={styles.card}>
            <h2 className={styles.cardTitle}>Response Rate by Source</h2>
            {sources.length > 0 ? (
              <div className={styles.sourceTable}>
                <div className={styles.tableHeader}>
                  <span>Source</span>
                  <span>Applied</span>
                  <span>Response</span>
                  <span>Rate</span>
                </div>
                {sources.map((source) => (
                  <div key={source.source} className={styles.tableRow}>
                    <span className={styles.sourceName}>{source.source}</span>
                    <span>{source.total}</span>
                    <span>{source.responded}</span>
                    <span className={`${styles.rate} ${source.response_rate >= 50 ? styles.good : styles.poor}`}>
                      {source.response_rate >= 50 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                      {source.response_rate}%
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.emptyState}>
                <p>No data available yet</p>
              </div>
            )}
          </section>

          {/* AI Insights */}
          <section className={`${styles.card} ${styles.insightsCard}`}>
            <h2 className={styles.cardTitle}>
              <Lightbulb size={18} />
              AI Insights
            </h2>
            {insights.length > 0 ? (
              <div className={styles.insights}>
                {insights.map((insight, index) => (
                  <div key={index} className={`${styles.insight} ${styles[insight.type] || styles.info}`}>
                    <h3>{insight.title}</h3>
                    <p>{insight.description}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.emptyInsights}>
                <AlertCircle size={24} />
                <p>Not enough data to generate insights yet.</p>
                <span>Add more applications to get AI-powered tips!</span>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
