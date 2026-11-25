const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })

/** "2 hours ago", "yesterday", "3 days ago" */
export function timeAgo(iso: string, now = Date.now()) {
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000)
  const abs = Math.abs(seconds)
  if (abs < 60) return 'just now'
  if (abs < 3600) return rtf.format(Math.round(seconds / 60), 'minute')
  if (abs < 86_400) return rtf.format(Math.round(seconds / 3600), 'hour')
  if (abs < 86_400 * 30) return rtf.format(Math.round(seconds / 86_400), 'day')
  return rtf.format(Math.round(seconds / (86_400 * 30)), 'month')
}
