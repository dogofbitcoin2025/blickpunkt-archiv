export default function ContentTypeBadge({ contentType, confidence }: { contentType: string; confidence?: number }) {
  if (!contentType || contentType === 'unklar') return null

  const labels: Record<string, string> = {
    anzeige: 'Anzeige',
    advertorial: 'Advertorial',
    redaktionell: 'Redaktionell',
    vereinsbericht: 'Vereinsbericht',
    portrait: 'Porträt',
    veranstaltung: 'Veranstaltung',
    bericht: 'Bericht',
  }

  const label = labels[contentType] || contentType
  const cls = contentType === 'anzeige' || contentType === 'advertorial'
    ? 'badge badge-anzeige'
    : 'badge badge-content'

  return (
    <span className={cls} title={confidence ? `Konfidenz: ${confidence}%` : undefined}>
      {label}
    </span>
  )
}
