'use client'

import Link from 'next/link'

export default function ArticleError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div style={{ padding: '2rem', maxWidth: '600px', margin: '0 auto' }}>
      <Link href="/" style={{ display: 'inline-block', marginBottom: '1.5rem', color: 'var(--accent)', textDecoration: 'none' }}>
        ← Zurück zur Suche
      </Link>
      <h2 style={{ color: '#c0392b', marginBottom: '1rem' }}>Artikel konnte nicht geladen werden</h2>
      <p style={{ color: '#666', marginBottom: '1rem' }}>
        {process.env.NODE_ENV === 'development'
          ? error.message
          : 'Beim Laden des Artikels ist ein Fehler aufgetreten.'}
      </p>
      {error.digest && (
        <p style={{ fontSize: '0.8rem', color: '#999', marginBottom: '1rem' }}>
          Fehler-ID: {error.digest}
        </p>
      )}
      <button
        onClick={reset}
        style={{
          padding: '0.5rem 1rem',
          background: 'var(--accent)',
          color: '#fff',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
        }}
      >
        Erneut versuchen
      </button>
    </div>
  )
}
