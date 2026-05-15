import { supabase } from '@/lib/supabase'

export const revalidate = 3600

async function getStats() {
  const [
    { count: totalArticles },
    { count: totalIssues },
    { count: unreviewed },
    { data: byGemeinde },
    { data: byYear },
    { data: byCategory },
    { data: recentIssues },
  ] = await Promise.all([
    supabase.from('articles').select('*', { count: 'exact', head: true }),
    supabase.from('issues').select('*', { count: 'exact', head: true }),
    supabase.from('articles').select('*', { count: 'exact', head: true }).eq('status', 'automatisch'),
    supabase.from('articles').select('gemeinde').not('gemeinde', 'is', null),
    supabase.from('articles').select('jahr').not('jahr', 'is', null),
    supabase.from('article_categories').select('category_id, categories(name)'),
    supabase.from('issues').select('id, title, gemeinde, saison, jahr, status, created_at').order('created_at', { ascending: false }).limit(5),
  ])

  // Group by gemeinde
  const gemeindeMap: Record<string, number> = {}
  for (const r of byGemeinde || []) {
    const g = (r as { gemeinde: string }).gemeinde
    gemeindeMap[g] = (gemeindeMap[g] || 0) + 1
  }
  const gemeindeStats = Object.entries(gemeindeMap)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)

  // Group by year
  const yearMap: Record<number, number> = {}
  for (const r of byYear || []) {
    const y = (r as { jahr: number }).jahr
    yearMap[y] = (yearMap[y] || 0) + 1
  }
  const yearStats = Object.entries(yearMap)
    .map(([year, count]) => ({ year: parseInt(year), count }))
    .sort((a, b) => b.year - a.year)
    .slice(0, 10)

  // Group by category
  const catMap: Record<string, number> = {}
  for (const r of byCategory || []) {
    const cats = (r as { categories: { name: string }[] | null }).categories
    const name = Array.isArray(cats) ? cats[0]?.name : (cats as { name: string } | null)?.name
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
