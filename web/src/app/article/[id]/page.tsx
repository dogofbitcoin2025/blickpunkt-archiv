import { supabase } from '@/lib/supabase'
import ContentTypeBadge from '@/components/ContentTypeBadge'
import DetectionPanel from '@/components/DetectionPanel'
import Link from 'next/link'
import { notFound } from 'next/navigation'

export const revalidate = 3600

export default async function ArticlePage({ params }: { params: { id: string } }) {
  const id = parseInt(params.id)
  if (isNaN(id)) notFound()

  const [{ data: article }, { data: cats }, { data: keywords }, { data: similar }] = await Promise.all([
    supabase.from('articles').select('*, issues(title, pdf_url)').eq('id', id).single(),
    supabase.from('article_categories').select('categories(name)').eq('article_id', id),
    supabase.from('article_keywords').select('keywords(word)').eq('article_id', id),
    supabase.from('similar_articles')
      .select('similar_article_id, similarity_score, shared_keywords, articles!similar_article_id(title, gemeinde, saison, jahr)')
      .eq('article_id', id)
      .order('similarity_score', { ascending: false })
      .limit(8),
  ])

  if (!article) notFound()

  const categoryNames = (cats || [])
    .map((c: { categories: { name: string } | { name: string }[] | null }) => {
      const cat = c.categories
      if (!cat) return null
      return Array.isArray(cat) ? cat[0]?.name : cat.name
    })
    .filter((n): n is string => n != null)

  const keywordList = (keywords || [])
    .map((k: { keywords: { word: string } | { word: string }[] | null }) => {
      const kw = k.keywords
      if (!kw) return null
      return Array.isArray(kw) ? kw[0]?.word : kw.word
    })
    .filter((w): w is string => w != null)

  const isAd = article.article_type === 'anzeige' || article.content_type === 'anzeige'

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
            {categoryNames.map((c: string) => <span key={c} className="badge badge-cat">{c}</span>)}
            {keywordList.map((k: string) => (
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

      {(article as { issues?: { title?: string; pdf_url?: string } }).issues?.pdf_url && (
        <div className="detail-section">
          <h3>Ausgabe</h3>
          <p style={{ fontSize: '0.88rem' }}>
            {(article as { issues?: { title?: string; pdf_url?: string } }).issues?.title && (
              <strong>{(article as { issues?: { title?: string; pdf_url?: string } }).issues?.title} – </strong>
            )}
            <a href={(article as { issues?: { title?: string; pdf_url?: string } }).issues?.pdf_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent)' }}>
              PDF öffnen
            </a>
          </p>
        </div>
      )}

      {similar && similar.length > 0 && (
        <div className="detail-section">
          <h3>Ähnliche Artikel ({similar.length})</h3>
          <div className="similar-list">
            {similar.map((s: {
              similar_article_id: number
              similarity_score: number
              shared_keywords: string
              articles: { title?: string; gemeinde?: string; saison?: string; jahr?: number }[] | null
            }) => {
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
            )})}

          </div>
        </div>
      )}
    </article>
  )
}
