'use client'

import { useState, useEffect, useCallback } from 'react'
import { supabase, expandSearchQuery, GEMEINDEN, SAISONEN, type Article, type Category } from '@/lib/supabase'
import ArticleCard from '@/components/ArticleCard'

const PAGE_SIZE = 20

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [inputValue, setInputValue] = useState('')
  const [kategorie, setKategorie] = useState('')
  const [gemeinde, setGemeinde] = useState('')
  const [jahr, setJahr] = useState('')
  const [saison, setSaison] = useState('')
  const [excludeAds, setExcludeAds] = useState(true)
  const [page, setPage] = useState(0)
  const [articles, setArticles] = useState<Article[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [categories, setCategories] = useState<Category[]>([])
  const [years, setYears] = useState<number[]>([])

  useEffect(() => {
    supabase.from('categories').select('*').is('parent_id', null).order('sort_order')
      .then(({ data }) => setCategories(data || []))
    supabase.from('articles').select('jahr').not('jahr', 'is', null)
      .then(({ data }) => {
        const unique = [...new Set((data || []).map((r: { jahr: number }) => r.jahr))].sort((a, b) => b - a)
        setYears(unique)
      })
  }, [])

  const search = useCallback(async (resetPage = true) => {
    const currentPage = resetPage ? 0 : page
    if (resetPage) setPage(0)
    setLoading(true)

    const terms = query ? expandSearchQuery(query) : []
    const from = currentPage * PAGE_SIZE
    const to = from + PAGE_SIZE - 1

    let q = supabase
      .from('articles')
      .select(`
        id, issue_id, title, summary, gemeinde, saison, jahr,
        article_type, content_type, content_type_confidence,
        ad_score, editorial_score, detected_signals, status, created_at,
        article_categories(category_id, categories(name))
      `, { count: 'exact' })
      .range(from, to)
      .order('jahr', { ascending: false })
      .order('id', { ascending: false })

    if (terms.length > 0) {
      const orParts = terms.map(t => `title.ilike.%${t}%,summary.ilike.%${t}%`).join(',')
      q = q.or(orParts)
    }
    if (kategorie) {
      const { data: catData } = await supabase.from('categories').select('id').eq('name', kategorie).single()
      if (catData) {
        const { data: acData } = await supabase.from('article_categories').select('article_id').eq('category_id', catData.id)
        const ids = (acData || []).map((r: { article_id: number }) => r.article_id)
        if (ids.length > 0) q = q.in('id', ids)
        else { setArticles([]); setTotal(0); setLoading(false); return }
      }
    }
    if (gemeinde) q = q.eq('gemeinde', gemeinde)
    if (jahr) q = q.eq('jahr', parseInt(jahr))
    if (saison) q = q.eq('saison', saison)
    if (excludeAds) q = q.neq('content_type', 'anzeige').neq('article_type', 'anzeige')

    const { data, count, error } = await q
    if (error) { console.error(error); setLoading(false); return }

    const mapped = (data || []).map((a: Record<string, unknown>) => ({
      ...a,
      category_names: ((a.article_categories as Array<{ categories: { name: string } | null }>) || [])
        .map(ac => ac.categories?.name).filter(Boolean),
    })) as Article[]

    setArticles(mapped)
    setTotal(count || 0)
    setLoading(false)
  }, [query, kategorie, gemeinde, jahr, saison, excludeAds, page])

  useEffect(() => { search(false) }, [page]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setQuery(inputValue)
    setTimeout(() => search(true), 0)
  }

  const handleFilterChange = () => { search(true) }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div>
      <section className="search-section">
        <form className="search-form" onSubmit={handleSubmit}>
          <input
            className="search-input"
            type="text"
            placeholder="Suche nach Themen, Personen, Vereinen, Orten..."
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
          />
          <button type="submit" className="btn btn-primary">Suchen</button>
          {(inputValue || query) && (
            <button type="button" className="btn btn-ghost" onClick={() => { setInputValue(''); setQuery(''); setTimeout(() => search(true), 0) }}>
              Leeren
            </button>
          )}
        </form>
      </section>

      <div className="filter-bar">
        <select className="filter-select" value={kategorie} onChange={e => { setKategorie(e.target.value); handleFilterChange() }}>
          <option value="">Alle Kategorien</option>
          {categories.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
        </select>

        <select className="filter-select" value={gemeinde} onChange={e => { setGemeinde(e.target.value); handleFilterChange() }}>
          <option value="">Alle Gemeinden</option>
          {GEMEINDEN.map(g => <option key={g} value={g}>{g}</option>)}
        </select>

        <select className="filter-select" value={jahr} onChange={e => { setJahr(e.target.value); handleFilterChange() }}>
          <option value="">Alle Jahre</option>
          {years.map(y => <option key={y} value={y}>{y}</option>)}
        </select>

        <select className="filter-select" value={saison} onChange={e => { setSaison(e.target.value); handleFilterChange() }}>
          <option value="">Alle Saisonen</option>
          {SAISONEN.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        <div className="filter-divider" />

        <label className="filter-checkbox">
          <input type="checkbox" checked={excludeAds} onChange={e => { setExcludeAds(e.target.checked); handleFilterChange() }} />
          Anzeigen ausblenden
        </label>

        <span className="results-count">
          {loading ? 'Suche...' : `${total} Ergebnis${total !== 1 ? 'se' : ''}`}
        </span>
      </div>

      {loading ? (
        <div className="loading">Suche läuft...</div>
      ) : articles.length === 0 ? (
        <div className="empty-state">
          <h3>Keine Artikel gefunden</h3>
          <p>Versuche andere Suchbegriffe oder Filter.</p>
        </div>
      ) : (
        <>
          <div className="articles-grid">
            {articles.map(a => <ArticleCard key={a.id} article={a} />)}
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button className="page-btn" disabled={page === 0} onClick={() => setPage(p => p - 1)}>
                Zurück
              </button>
              <span className="page-info">Seite {page + 1} von {totalPages}</span>
              <button className="page-btn" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>
                Weiter
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
