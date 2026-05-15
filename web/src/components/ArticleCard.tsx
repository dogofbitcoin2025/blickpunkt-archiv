import Link from 'next/link'
import type { Article } from '@/lib/supabase'
import ContentTypeBadge from './ContentTypeBadge'

export default function ArticleCard({ article: a }: { article: Article }) {
  const isAd = a.article_type === 'anzeige' || a.content_type === 'anzeige'
  return (
    <Link href={`/article/${a.id}`} className="article-card">
      <div className="card-header">
        <div className="card-title">{a.title || '(Kein Titel)'}</div>
        {isAd && <span className="badge badge-anzeige">Anzeige</span>}
      </div>
      <div className="card-meta">
        {a.gemeinde && <span className="badge badge-gemeinde">{a.gemeinde}</span>}
        {a.saison && <span className="badge badge-saison">{a.saison}</span>}
        {a.jahr && <span>{a.jahr}</span>}
        {a.page_start && <span>S. {a.page_start}{a.page_end && a.page_end !== a.page_start ? `–${a.page_end}` : ''}</span>}
        <ContentTypeBadge contentType={a.content_type} confidence={a.content_type_confidence} />
      </div>
      {a.summary && <p className="card-summary">{a.summary.slice(0, 220)}{a.summary.length > 220 ? '…' : ''}</p>}
      {a.category_names && a.category_names.length > 0 && (
        <div className="card-tags">
          {a.category_names.slice(0, 3).map(c => (
            <span key={c} className="badge badge-cat">{c}</span>
          ))}
        </div>
      )}
    </Link>
  )
}
