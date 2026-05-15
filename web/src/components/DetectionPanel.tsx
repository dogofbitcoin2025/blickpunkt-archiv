type Signal = {
  type?: string
  text?: string
  weight?: number
  [key: string]: unknown
}

export default function DetectionPanel({
  adScore,
  editorialScore,
  contentType,
  confidence,
  signals,
}: {
  adScore: number
  editorialScore: number
  contentType: string
  confidence: number
  signals: Signal[] | string
}) {
  let parsedSignals: Signal[] = []
  if (typeof signals === 'string') {
    try { parsedSignals = JSON.parse(signals) } catch { parsedSignals = [] }
  } else if (Array.isArray(signals)) {
    parsedSignals = signals
  }

  const verdict = adScore > editorialScore ? 'Wahrscheinlich Anzeige' : 'Wahrscheinlich Redaktionell'
  const verdictColor = adScore > editorialScore ? '#856404' : '#155724'

  return (
    <div className="detection-panel">
      <div style={{ marginBottom: '0.75rem', fontSize: '0.85rem' }}>
        <strong style={{ color: verdictColor }}>{verdict}</strong>
        {confidence > 0 && <span style={{ color: 'var(--text-muted)', marginLeft: '0.5rem' }}>({confidence}% Konfidenz)</span>}
        {contentType && contentType !== 'unklar' && (
          <span style={{ marginLeft: '0.5rem', color: 'var(--text-muted)' }}>
            · Typ: <strong>{contentType}</strong>
          </span>
        )}
      </div>

      <div className="detection-scores">
        <div className="score-item">
          <span className="score-label">Anzeigen-Score</span>
          <span className={`score-value score-ad`}>{adScore}</span>
        </div>
        <div className="score-item">
          <span className="score-label">Redaktions-Score</span>
          <span className={`score-value score-editorial`}>{editorialScore}</span>
        </div>
      </div>

      {parsedSignals.length > 0 && (
        <>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
            Erkannte Signale ({parsedSignals.length})
          </div>
          <ul className="signal-list">
            {parsedSignals.map((s, i) => (
              <li key={i} className="signal-item">
                <span>{s.text || s.type || JSON.stringify(s)}</span>
                {s.type && <span className="signal-type">{s.type}</span>}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
