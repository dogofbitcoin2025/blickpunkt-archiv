'use client'

import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import ContentTypeBadge from '@/components/ContentTypeBadge'
import DetectionPanel from '@/components/DetectionPanel'
import Link from 'next/link'
import { useParams } from 'next/navigation'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function extractField(val: any, field: string): string | null {
  if (!val) return null
  if (Array.isArray(val)) return val[0]?.[field] ?? null
  if (typeof val === 'object') return val[field] ?? null
  return null
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ArticleData = Record<string, any>

export default function ArticlePage() {
  const params = useParams()
  const id = parseInt(params.id as string)

  const [article, setArticle] = useState<ArticleData | null>(null)
  const [categoryNames, setCategoryNames] = useState<string[]>([])
  const [keywordList, setKeywordList] = useState<string[]>([])
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [similar, setSimilar] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (isNaN(id)) { setNotFound(true); setLoading(false); return }

    async function load() {
      const [
        { data: art, error: artErr },
        { data: cats },
        { data: keywords },
        { data: sim },
      ] = await Promise.all([
        supabase.from('articles').select('*, issues(title, pdf_url)').eq('id', id).single(),
        supabase.from('article_categories').select('categories(name)').eq('article_id', id),
        supabase.from('article_keywords').select('keywords(word)').eq('article_id', id),
        supabase.from('similar_articles')
          .select('similar_article_id, similarity_score, shared_keywords, articles!similar_article_id(title, gemeinde, saison, jahr)')
          .eq('article_id', id)
          .order('similarity_score', { ascending: false })
          .limit(8),
      ])

      if (artErr || !art) { setNotFound(true); setLoading(false); return }

      setArticle(art)
      setCategoryNames(
        (cats || []).map((c: ArticleData) => extractField(c.categories, 'name')).filter(Boolean) as string[]
      )
      setKeywordList(
        (keywords || []).map((k: ArticleData) => extractField(k.keywords, 'word')).filter(Boolean) as string[]
      )
      setSimilar(sim || [])
      setLoading(false)
    }

    load()
  }, [id])

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        Artikel wird geladen…
      </div>
    )
  }

  if (notFound || !article) {
    return (
      <div style={{ padding: '2rem', maxWidth: '600px', margin: '0 auto' }}>
        <Link href="/" className="detail-back">← Zurück zur Suche</Link>
        <h2 style={{ marginTop: '1.5rem' }}>Artikel nicht gefunden</h2>
        <p style={{ color: 'var(--text-muted)' }}>Der gesuchte Artikel existiert nicht.</p>
      </div>
    )
  }

  const isAd = article.article_type === 'anzeige' || article.content_type === 'anzeige'
  const issues = Array.isArray(article.issues) ? article.issues[0] : article.issues

  return (
    <article className="article-detail">
      <Link href="/" className="detail-back">← Zurück zur Suche</Link>

      <header className="detail-header">
        <h1 className="detail-title">{article.title || '(Kein Titel)'}</h1>
        <div className="detail-meta">
          {article.gemeinde && <span className="badge badge-gemeinde">{article.gemeinde}</span>}
          {article.saison && <span className="badge badge-saison">{article.saison}</span>}
          {article.jahr && <span className="badge badge-saison">{article.jahr}</span>}
          {isAd && <span className="badge badge-anzeige">Anzeige</span>}
          {!isAd && <span className="badge badge-redaktionell">Redaktionell</span>}
          <ContentTypeBadge contentType={article.content_type} confidence={article.content_type_confidence} />
          {article.page_start && (
            <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Seite {article.page_start}{article.page_end && article.page_end !== article.page_start ? `–${article.page_end}` : ''}
            </span>
          )}
        </div>
      </header>

      {article.summary && (
        <div className="detail-section">
          <h3>Zusammenfassung</h3>
          <p className="detail-summary">{article.summary}</p>
        </div>
      )}

      {(categoryNames.length > 0 || keywordList.length > 0) && (
        <div className="detail-section">
          <h3>Kategorien & Schlagwörter</h3>
          <div className="card-tags" style={{ gap: '0.5rem' }}>
            {categoryNames.map((c) => <span key={c} className="badge badge-cat">{c}</span>)}
            {keywordList.map((k) => (
              <span key={k} style={{ fontSize: '0.78rem', background: '#f0ece6', padding: '0.2rem 0.5rem', borderRadius: '4px', color: '#5a4a3a' }}>{k}</span>
            ))}
          </div>
        </div>
      )}

      <div className="detail-section">
        <h3>Inhaltstyp-Erkennung</h3>
        <DetectionPanel
          adScore={article.ad_score || 0}
          editorialScore={article.editorial_score || 0}
          contentType={article.content_type}
          confidence={article.content_type_confidence || 0}
          signals={article.detected_signals || []}
        />
      </div>

      {article.full_text && (
        <div className="detail-section">
          <h3>Volltext</h3>
          <div className="detail-fulltext">{article.full_text}</div>
        </div>
      )}

      {issues?.pdf_url && (
        <div className="detail-section">
          <h3>Ausgabe</h3>
          <p style={{ fontSize: '0.88rem' }}>
            {issues.title && <strong>{issues.title} – </strong>}
            <a href={issues.pdf_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent)' }}>
              PDF öffnen
            </a>
          </p>
        </div>
      )}

      {similar.length > 0 && (
        <div className="detail-section">
          <h3>Ähnliche Artikel ({similar.length})</h3>
          <div className="similar-list">
            {similar.map((s) => {
              const a = Array.isArray(s.articles) ? s.articles[0] : s.articles
              return (
                <Link key={s.similar_article_id} href={`/article/${s.similar_article_id}`} className="similar-card">
                  <div>
                    <div className="similar-title">{a?.title || '(Kein Titel)'}</div>
                    <div className="similar-meta">
                      {a?.gemeinde} · {a?.saison} {a?.jahr}
                      {s.shared_keywords && <span> · {s.shared_keywords}</span>}
                    </div>
                  </div>
                  <span className="similar-score">{Math.round((s.similarity_score || 0) * 100)}%</span>
                </Link>
              )
            })}
          </div>
        </div>
      )}
    </article>
  )
}
