'use client';

import { Header } from '@/components/layout/Header';
import { DashboardSkeleton } from '@/components/ui';
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
import {
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import styles from './page.module.css';

// Chart color palette matching Orbit design system
const CHART_COLORS = {
  applied: '#5E6AD2',
  screening: '#9B7DD4',
  oa: '#F2994A',
  interview: '#5DCE87',
  offer: '#4ECDC4',
  accepted: '#45B36B',
  rejected: '#E66A6A',
  withdrawn: '#6B7280',
  ghosted: '#404145',
};

const PIE_COLORS = [
  '#5E6AD2', '#9B7DD4', '#F2994A', '#5DCE87', 
  '#4ECDC4', '#45B36B', '#E66A6A', '#6B7280', '#404145'
];

// Custom tooltip component
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className={styles.tooltip}>
      <p className={styles.tooltipLabel}>{label}</p>
      {payload.map((entry: any, i: number) => (
        <p key={i} className={styles.tooltipValue} style={{ color: entry.color }}>
          {entry.name}: <strong>{entry.value}</strong>
        </p>
      ))}
    </div>
  );
}

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
        <DashboardSkeleton />
      </div>
    );
  }

  const funnel = funnelData?.stages || [];
  const sources = sourceData?.sources || [];
  const insights = insightsData?.insights || [];
  const stats = summary || { total: 0, active: 0, interviews: 0, offers: 0, this_week: 0 };

  // Derived stats
  const conversionRate = stats.total > 0 ? (stats.offers / stats.total) * 100 : 0;
  const totalResponded = sources.reduce((acc: number, curr: any) => acc + curr.responded, 0);
  const totalTrackedSource = sources.reduce((acc: number, curr: any) => acc + curr.total, 0);
  const responseRate = totalTrackedSource > 0 ? (totalResponded / totalTrackedSource) * 100 : 0;

  // Prepare pie chart data from funnel
  const pieData = funnel
    .filter((s: any) => s.count > 0)
    .map((s: any) => ({
      name: s.status,
      value: s.count,
      color: CHART_COLORS[s.status as keyof typeof CHART_COLORS] || '#5E6AD2',
    }));

  // Prepare bar chart data from sources
  const barData = sources.map((s: any) => ({
    name: s.source.length > 12 ? s.source.slice(0, 12) + '…' : s.source,
    applied: s.total,
    responded: s.responded,
    rate: s.response_rate,
  }));

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
          {/* Status Distribution — Pie Chart */}
          <section className={styles.card}>
            <h2 className={styles.cardTitle}>Status Distribution</h2>
            {pieData.length > 0 ? (
              <div className={styles.chartContainer}>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={65}
                      outerRadius={100}
                      paddingAngle={3}
                      dataKey="value"
                      animationBegin={0}
                      animationDuration={800}
                    >
                      {pieData.map((entry: any, index: number) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={entry.color} 
                          stroke="transparent"
                        />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                    <Legend 
                      verticalAlign="bottom"
                      iconType="circle"
                      iconSize={8}
                      formatter={(value: string) => (
                        <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{value}</span>
                      )}
                    />
                  </PieChart>
                </ResponsiveContainer>
                {/* Center label */}
                <div className={styles.pieCenter}>
                  <span className={styles.pieCenterValue}>{stats.total}</span>
                  <span className={styles.pieCenterLabel}>Total</span>
                </div>
              </div>
            ) : (
              <div className={styles.emptyState}>
                <p>No data available yet</p>
              </div>
            )}
          </section>

          {/* Conversion Funnel — Horizontal Bar Chart */}
          <section className={styles.card}>
            <h2 className={styles.cardTitle}>Conversion Funnel</h2>
            {funnel.length > 0 ? (
              <div className={styles.chartContainer}>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart
                    data={funnel.map((s: any) => ({
                      name: s.status,
                      count: s.count,
                      fill: CHART_COLORS[s.status as keyof typeof CHART_COLORS] || '#5E6AD2',
                    }))}
                    layout="vertical"
                    margin={{ top: 0, right: 20, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid 
                      strokeDasharray="3 3" 
                      stroke="rgba(255,255,255,0.04)" 
                      horizontal={false}
                    />
                    <XAxis 
                      type="number" 
                      tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                      axisLine={{ stroke: 'var(--border-subtle)' }}
                      tickLine={false}
                    />
                    <YAxis 
                      dataKey="name" 
                      type="category" 
                      width={80}
                      tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar 
                      dataKey="count" 
                      radius={[0, 4, 4, 0]}
                      animationBegin={0}
                      animationDuration={800}
                    >
                      {funnel.map((s: any, i: number) => (
                        <Cell 
                          key={i} 
                          fill={CHART_COLORS[s.status as keyof typeof CHART_COLORS] || '#5E6AD2'} 
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className={styles.emptyState}>
                <p>No data available yet</p>
              </div>
            )}
          </section>

          {/* Response by Source — Bar Chart */}
          <section className={styles.card}>
            <h2 className={styles.cardTitle}>Response Rate by Source</h2>
            {sources.length > 0 ? (
              <div className={styles.chartContainer}>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart 
                    data={barData}
                    margin={{ top: 0, right: 20, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid 
                      strokeDasharray="3 3" 
                      stroke="rgba(255,255,255,0.04)" 
                      vertical={false}
                    />
                    <XAxis 
                      dataKey="name"
                      tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                      axisLine={{ stroke: 'var(--border-subtle)' }}
                      tickLine={false}
                    />
                    <YAxis 
                      tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend 
                      verticalAlign="top"
                      iconType="circle"
                      iconSize={8}
                      formatter={(value: string) => (
                        <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{value}</span>
                      )}
                    />
                    <Bar 
                      dataKey="applied" 
                      name="Applied" 
                      fill="#5E6AD2" 
                      radius={[4, 4, 0, 0]}
                      animationDuration={800}
                    />
                    <Bar 
                      dataKey="responded" 
                      name="Responded" 
                      fill="#5DCE87" 
                      radius={[4, 4, 0, 0]}
                      animationDuration={800}
                    />
                  </BarChart>
                </ResponsiveContainer>
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
                {insights.map((insight: any, index: number) => (
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
