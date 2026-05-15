import { supabase } from '@/lib/supabase'

export const revalidate = 3600

async function getStats() {
  const [
    { count: totalArticles },
    { count: totalIssues },
    { count: unreviewed },
    { data: issues },
    { data: byCategory },
    { data: recentIssues },
  ] = await Promise.all([
    supabase.from('articles').select('*', { count: 'exact', head: true }),
    supabase.from('issues').select('*', { count: 'exact', head: true }),
    supabase.from('articles').select('*', { count: 'exact', head: true }).eq('status', 'automatisch'),
    // Issues are small (138 rows) – use them for gemeinde/jahr stats to avoid
    // the 1000-row default limit when scanning all 19k+ articles
    supabase.from('issues').select('id, gemeinde, jahr, saison').limit(500),
    supabase.from('article_categories').select('category_id, categories(name)').limit(5000),
    supabase.from('issues')
      .select('id, title, gemeinde, saison, jahr, status, created_at')
      .order('created_at', { ascending: false })
      .limit(5),
  ])

  // Count articles per issue via batched counts
  const issueList = issues || []
  const articleCountPerIssue: Record<number, number> = {}

  // Fetch article counts in 5 parallel batches to avoid N+1 queries
  const batchSize = 30
  for (let i = 0; i < issueList.length; i += batchSize) {
    const batch = issueList.slice(i, i + batchSize)
    const batchIds = batch.map(iss => iss.id)
    // Fetch issue_id for articles in this batch
    const { data: arts } = await supabase
      .from('articles')
      .select('issue_id')
      .in('issue_id', batchIds)
      .limit(10000)
    for (const a of arts || []) {
      articleCountPerIssue[a.issue_id] = (articleCountPerIssue[a.issue_id] || 0) + 1
    }
  }

  // Group by gemeinde
  const gemeindeMap: Record<string, number> = {}
  for (const iss of issueList) {
    const g = iss.gemeinde
    if (!g) continue
    const cnt = articleCountPerIssue[iss.id] || 0
    gemeindeMap[g] = (gemeindeMap[g] || 0) + cnt
  }
  const gemeindeStats = Object.entries(gemeindeMap)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)

  // Group by year
  const yearMap: Record<number, number> = {}
  for (const iss of issueList) {
    const y = iss.jahr
    if (!y) continue
    const cnt = articleCountPerIssue[iss.id] || 0
    yearMap[y] = (yearMap[y] || 0) + cnt
  }
  const yearStats = Object.entries(yearMap)
    .map(([year, count]) => ({ year: parseInt(year), count }))
    .sort((a, b) => b.year - a.year)
    .slice(0, 10)

  // Group by category
  const catMap: Record<string, number> = {}
  for (const r of byCategory || []) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const cats = (r as any).categories
    const name = Array.isArray(cats) ? cats[0]?.name : cats?.name
    if (name) catMap[name] = (catMap[name] || 0) + 1
  }
  const catStats = Object.entries(catMap)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)

  return {
    totalArticles: totalArticles || 0,
    totalIssues: totalIssues || 0,
    unreviewed: unreviewed || 0,
    gemeindeStats,
    yearStats,
    catStats,
    recentIssues: recentIssues || [],
  }
}

function BarChart({ data, max }: { data: { name: string; count: number }[]; max: number }) {
  return (
    <div className="bar-chart">
      {data.map(item => (
        <div key={item.name} className="bar-row">
          <span className="bar-label" title={item.name}>{item.name}</span>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(item.count / max) * 100}%` }} />
          </div>
          <span className="bar-count">{item.count}</span>
        </div>
      ))}
    </div>
  )
}

export default async function DashboardPage() {
  const stats = await getStats()
  const maxGemeinde = stats.gemeindeStats[0]?.count || 1
  const maxCat = stats.catStats[0]?.count || 1
  const maxYear = Math.max(...stats.yearStats.map(y => y.count), 1)

  return (
    <div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '1.5rem' }}>Dashboard</h1>

      <div className="dashboard-grid">
        <div className="stat-card">
          <div className="stat-label">Artikel gesamt</div>
          <div className="stat-value">{stats.totalArticles.toLocaleString('de')}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Ausgaben</div>
          <div className="stat-value">{stats.totalIssues}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Nicht geprüft</div>
          <div className="stat-value">{stats.unreviewed.toLocaleString('de')}</div>
          <div className="stat-sub">Status: automatisch</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Gemeinden</div>
          <div className="stat-value">{stats.gemeindeStats.length}</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1rem' }}>
        <div className="chart-section">
          <div className="chart-title">Artikel nach Gemeinde</div>
          <BarChart data={stats.gemeindeStats} max={maxGemeinde} />
        </div>

        <div className="chart-section">
          <div className="chart-title">Artikel nach Kategorie</div>
          <BarChart data={stats.catStats.slice(0, 12)} max={maxCat} />
        </div>

        <div className="chart-section">
          <div className="chart-title">Artikel nach Jahr</div>
          <BarChart
            data={stats.yearStats.map(y => ({ name: String(y.year), count: y.count }))}
            max={maxYear}
          />
        </div>

        <div className="chart-section">
          <div className="chart-title">Zuletzt erfasste Ausgaben</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {stats.recentIssues.map((issue: {
              id: number
              title?: string
              gemeinde?: string
              saison?: string
              jahr?: number
              status?: string
            }) => (
              <div key={issue.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', padding: '0.5rem', background: 'var(--bg)', borderRadius: '6px' }}>
                <span>{issue.title || `${issue.gemeinde} ${issue.saison} ${issue.jahr}`}</span>
                <span style={{ color: 'var(--text-muted)' }}>{issue.status}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
