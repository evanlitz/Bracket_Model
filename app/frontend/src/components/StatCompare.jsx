import { fmtStat, diffClass, HIGHER_BETTER, LOWER_BETTER } from './utils'

const COMPARE_STATS = [
  { key: 'AdjEM',           label: 'Adj EM' },
  { key: 'AdjOE',           label: 'Adj OE' },
  { key: 'AdjDE',           label: 'Adj DE' },
  { key: 'efg_pct_off',     label: 'eFG% Off' },
  { key: 'efg_pct_def',     label: 'eFG% Def' },
  { key: 'or_pct_off',      label: 'OR%' },
  { key: 'to_pct_off',      label: 'TO% Off' },
  { key: 'blk_pct_def',     label: 'Blk% Def' },
  { key: 'avg_height',      label: 'Avg Ht' },
  { key: 'd1_exp',          label: 'D1 Exp' },
  { key: 'star_eup',        label: 'Star EUP' },
  { key: 'depth_eup',       label: 'Depth EUP' },
  { key: 'interior_dom',    label: 'Interior' },
  { key: 'triple_threat',   label: 'Triple' },
  { key: 'returning_min_pct', label: 'Returning' },
]

function diffVal(key, qv, mv) {
  if (qv == null || mv == null) return null
  // Compute raw diff in display-unit space
  const pcts = ['efg_pct_off', 'efg_pct_def', 'to_pct_off', 'or_pct_off', 'returning_min_pct']
  const scale = pcts.includes(key) ? 100 : 1
  const diff = (mv - qv) * scale
  return diff
}

function fmtDiff(key, qv, mv) {
  const d = diffVal(key, qv, mv)
  if (d == null) return '—'
  const pcts = ['efg_pct_off', 'efg_pct_def', 'to_pct_off', 'or_pct_off', 'returning_min_pct']
  const decimals = pcts.includes(key) ? 1 : (Math.abs(d) < 1 ? 3 : 1)
  const sign = d > 0 ? '+' : ''
  return `${sign}${d.toFixed(decimals)}`
}

function diffBg(key, qv, mv) {
  const d = diffVal(key, qv, mv)
  if (d == null || Math.abs(d) < 0.0001) return ''
  const cls = diffClass(key, qv, mv)
  if (cls === 'better') return 'rgba(34,197,94,0.15)'
  if (cls === 'worse')  return 'rgba(239,68,68,0.15)'
  return ''
}

function diffTextColor(key, qv, mv) {
  const cls = diffClass(key, qv, mv)
  if (cls === 'better') return '#22c55e'
  if (cls === 'worse')  return '#ef4444'
  return 'var(--cream-dim)'
}

export default function StatCompare({ queryStats = {}, matchStats = {} }) {
  const rows = COMPARE_STATS.filter(
    ({ key }) => queryStats[key] != null || matchStats[key] != null
  )
  if (rows.length === 0) return null

  return (
    <div className="stat-compare">
      {/* Header: Stat | Diff | Query | Match */}
      <div className="stat-compare-header">
        <span>Stat</span>
        <span style={{ textAlign: 'center' }}>Diff</span>
        <span style={{ textAlign: 'right' }}>Query</span>
        <span style={{ textAlign: 'right' }}>Match</span>
      </div>

      {rows.map(({ key, label }) => {
        const qv = queryStats[key]
        const mv = matchStats[key]
        const bg    = diffBg(key, qv, mv)
        const tclr  = diffTextColor(key, qv, mv)

        return (
          <div key={key} className="stat-compare-row" style={{ gridTemplateColumns: '1fr 52px 52px 52px' }}>
            <span className="stat-compare-name">{label}</span>

            {/* Diff column — leftmost of the value trio */}
            <span
              className="stat-compare-val mono"
              style={{
                background: bg,
                color: tclr,
                textAlign: 'center',
                borderRadius: 3,
                padding: '0 3px',
                fontWeight: 700,
              }}
            >
              {fmtDiff(key, qv, mv)}
            </span>

            <span className="stat-compare-val query-val mono">
              {qv != null ? fmtStat(key, qv) : '—'}
            </span>
            <span className="stat-compare-val mono" style={{ color: 'var(--cream-dim)' }}>
              {mv != null ? fmtStat(key, mv) : '—'}
            </span>
          </div>
        )
      })}
    </div>
  )
}
