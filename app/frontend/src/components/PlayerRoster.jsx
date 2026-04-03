import { useState } from 'react'

const CLASS_COLORS = {
  Fr: '#60a5fa',
  So: '#34d399',
  Jr: '#fbbf24',
  Sr: '#f87171',
}

function fmt(v, decimals = 1) {
  if (v == null) return '—'
  return Number(v).toFixed(decimals)
}

function fmtPct(v, already100 = false) {
  if (v == null) return '—'
  const f = Number(v)
  // Values already in percent range (e.g. 47.3) or decimal (e.g. 0.473)
  const pct = already100 ? f : (f <= 1 ? f * 100 : f)
  return pct.toFixed(1) + '%'
}

// ESPN box score columns — order matches broadcast/ESPN layout
const COLS = [
  { key: 'games',    head: 'G',     render: p => p.games ?? '—',                     title: 'Games Played' },
  { key: 'ppg',      head: 'PPG',   render: p => fmt(p.ppg, 1),                      title: 'Points Per Game' },
  { key: 'fg_pct',   head: 'FG%',   render: p => p.fg_pct != null ? p.fg_pct.toFixed(1) + '%' : '—', title: 'Field Goal %' },
  { key: 'fg3_pct',  head: '3P%',   render: p => fmtPct(p.fg3_pct),                  title: '3-Point %' },
  { key: 'ft_pct',   head: 'FT%',   render: p => fmtPct(p.ft_pct),                   title: 'Free Throw %' },
  { key: 'or_pct',   head: 'OR%',   render: p => fmt(p.or_pct) + '%',                title: 'Offensive Rebound %' },
  { key: 'dr_pct',   head: 'DR%',   render: p => fmt(p.dr_pct) + '%',                title: 'Defensive Rebound %' },
  { key: 'a_rate',   head: 'A%',    render: p => fmt(p.a_rate) + '%',                title: 'Assist Rate' },
  { key: 'to_rate',  head: 'TO%',   render: p => fmt(p.to_rate) + '%',               title: 'Turnover Rate' },
  { key: 'stl_pct',  head: 'STL%',  render: p => fmt(p.stl_pct) + '%',              title: 'Steal %' },
  { key: 'blk_pct',  head: 'BLK%',  render: p => fmt(p.blk_pct) + '%',              title: 'Block %' },
]

export default function PlayerRoster({ players = [], label = 'Player Roster' }) {
  const [open, setOpen] = useState(true)

  if (!players.length) return null

  return (
    <div className="player-roster">
      <button className="expand-btn" onClick={() => setOpen(s => !s)}>
        {open ? `▲ Hide ${label}` : `▼ ${label} (${players.length})`}
      </button>

      {open && (
        <div className="player-table-wrap">
          <table className="player-table">
            <thead>
              <tr>
                <th className="pt-name">Player</th>
                {COLS.map(c => (
                  <th key={c.key} title={c.title}>{c.head}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {players.map((p, i) => (
                <tr key={i} className={p.starter ? 'starter-row' : ''}>
                  <td className="pt-name">
                    <span className="player-name">{p.name || '—'}</span>
                    <span className="player-meta">
                      {p.year_class && (
                        <span
                          className="class-chip"
                          style={{ color: CLASS_COLORS[p.year_class] || 'var(--cream-dim)' }}
                        >
                          {p.year_class}
                        </span>
                      )}
                      {p.height && p.height !== 'nan' && (
                        <span className="height-chip">{p.height}</span>
                      )}
                    </span>
                  </td>
                  {COLS.map(c => (
                    <td key={c.key} className="mono">{c.render(p)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
