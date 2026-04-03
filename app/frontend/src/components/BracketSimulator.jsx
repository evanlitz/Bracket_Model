import { useState } from 'react'

// ── Constants ─────────────────────────────────────────────────────────────────

const ROUNDS = [
  { key: 'r64',   label: 'R64'  },
  { key: 'r32',   label: 'R32'  },
  { key: 's16',   label: 'S16'  },
  { key: 'e8',    label: 'E8'   },
  { key: 'f4',    label: 'F4'   },
  { key: 'champ', label: 'CHAMP'},
]

const REGIONS = ['All', 'South', 'East', 'West', 'Midwest']

const SIM_OPTIONS = [
  { value: 1000,  label: '1k'  },
  { value: 5000,  label: '5k'  },
  { value: 10000, label: '10k' },
]

// ── Helpers ───────────────────────────────────────────────────────────────────

function pct(v) {
  if (v == null) return '—'
  const p = Math.round(v * 100)
  return p === 0 ? '<1%' : p === 100 ? '>99%' : p + '%'
}

function cellBg(v, isChamp) {
  if (v == null) return 'transparent'
  const a = Math.min(v, 1)
  if (isChamp) return `rgba(201,168,76,${a * 0.75})`
  return `rgba(59,130,246,${a * 0.65})`
}

function cellColor(v) {
  if (v == null) return 'var(--cream-dim)'
  return v >= 0.4 ? 'var(--cream)' : v >= 0.15 ? 'var(--cream-dim)' : 'rgba(200,200,200,0.4)'
}

// ── Champion spotlight cards ──────────────────────────────────────────────────

function ChampionSpotlight({ teams }) {
  const top = teams.filter(t => t.adv.champ > 0).slice(0, 4)
  if (!top.length) return null
  return (
    <div className="bs-spotlight">
      {top.map((t, i) => (
        <div key={t.team} className={`bs-spotlight-card ${i === 0 ? 'bs-spotlight-winner' : ''}`}>
          <div className="bs-spot-rank mono">MODEL RANK #{i + 1}</div>
          <div className="bs-spot-team display">{t.team}</div>
          <div className="bs-spot-meta mono">
            {t.seed ? `${t.seed}-seed` : ''}{t.seed && t.region ? ' · ' : ''}{t.region || ''}
          </div>
          <div className="bs-spot-pct mono">{pct(t.adv.champ)}</div>
          <div className="bs-spot-label mono">championship</div>
          <div className="bs-spot-bar">
            <div className="bs-spot-fill" style={{ width: `${Math.min(t.adv.champ * 100 * 4, 100)}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Heat table ────────────────────────────────────────────────────────────────

function HeatTable({ teams, sortKey, sortDir, onSort }) {
  if (!teams.length) return null

  return (
    <div className="bs-table-wrap">
      <table className="bs-table">
        <thead>
          <tr>
            <th className="bs-th-team" onClick={() => onSort('team')}>
              Team {sortKey === 'team' ? (sortDir === 'asc' ? '▴' : '▾') : ''}
            </th>
            <th className="bs-th-seed" onClick={() => onSort('seed')}>
              Seed {sortKey === 'seed' ? (sortDir === 'asc' ? '▴' : '▾') : ''}
            </th>
            {ROUNDS.map(r => (
              <th
                key={r.key}
                className={`bs-th-round ${r.key === 'champ' ? 'bs-th-champ' : ''}`}
                onClick={() => onSort(r.key)}
              >
                {r.label} {sortKey === r.key ? (sortDir === 'asc' ? '▴' : '▾') : ''}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {teams.map(t => (
            <tr key={t.team} className="bs-row">
              <td className="bs-td-team">
                <span className="bs-team-name">{t.team}</span>
                {t.region && <span className="bs-team-region mono">{t.region}</span>}
              </td>
              <td className="bs-td-seed mono">
                {t.seed ? `#${t.seed}` : '—'}
              </td>
              {ROUNDS.map(r => {
                const v = t.adv[r.key]
                const isChamp = r.key === 'champ'
                return (
                  <td
                    key={r.key}
                    className={`bs-td-round ${isChamp ? 'bs-td-champ' : ''}`}
                    style={{ background: cellBg(v, isChamp), color: cellColor(v) }}
                    title={`${t.team} · ${r.label}: ${v != null ? (v * 100).toFixed(1) : '—'}%`}
                  >
                    <span className="mono">{pct(v)}</span>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Deterministic bracket path ────────────────────────────────────────────────

function DetBracket({ games }) {
  if (!games?.length) return null

  const byRound = {}
  for (const g of games) {
    if (!byRound[g.round]) byRound[g.round] = []
    byRound[g.round].push(g)
  }

  const roundLabels = { 1:'R64', 2:'R32', 3:'S16', 4:'E8', 5:'F4', 6:'NCG' }

  return (
    <div className="bs-det-section">
      <div className="bs-section-label display">Model's Deterministic Pick</div>
      <div className="bs-section-sub mono">Each game: model picks the higher-probability winner</div>
      <div className="bs-det-rounds">
        {Object.keys(byRound).sort((a,b) => +a - +b).map(rnd => (
          <div key={rnd} className="bs-det-round-col">
            <div className="bs-det-round-label mono">{roundLabels[rnd] || `R${rnd}`}</div>
            {byRound[rnd].map(g => (
              <div key={g.match_id} className={`bs-det-game ${g.round >= 5 ? 'bs-det-final' : ''}`}>
                <div className={`bs-det-team ${g.winner === g.t1 ? 'bs-det-winner' : 'bs-det-loser'}`}>
                  {g.t1}
                </div>
                <div className={`bs-det-team ${g.winner === g.t2 ? 'bs-det-winner' : 'bs-det-loser'}`}>
                  {g.t2}
                </div>
                <div className="bs-det-prob mono">
                  {Math.round(Math.max(g.prob, 1 - g.prob) * 100)}%
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function BracketSimulator({ allTeams }) {
  const years = [...new Set((allTeams || []).map(t => t.year))].sort((a, b) => b - a)
  const [year,    setYear]    = useState(years[0] ?? 2026)
  const [nSims,   setNSims]   = useState(5000)
  const [region,  setRegion]  = useState('All')
  const [sortKey, setSortKey] = useState('champ')
  const [sortDir, setSortDir] = useState('desc') // 'asc' | 'desc'
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)
  const [view,    setView]    = useState('table') // 'table' | 'det'

  async function runSimulation() {
    setLoading(true)
    setError(null)
    setData(null)
    try {
      const res = await fetch(`/api/simulate/${year}?n=${nSims}`)
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `${res.status} ${res.statusText}`)
      }
      setData(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // Filter + sort
  const filteredTeams = (data?.teams ?? [])
    .filter(t => region === 'All' || t.region === region)
    .sort((a, b) => {
      let cmp = 0
      if (sortKey === 'team') cmp = a.team.localeCompare(b.team)
      else if (sortKey === 'seed') cmp = (a.seed ?? 99) - (b.seed ?? 99)
      else { const va = a.adv[sortKey] ?? 0; const vb = b.adv[sortKey] ?? 0; cmp = vb - va }
      return sortDir === 'asc' ? -cmp : cmp
    })

  return (
    <div className="bs-viewer">

      {/* Toolbar */}
      <div className="bs-toolbar">
        <div className="bs-toolbar-title display">Bracket Simulator</div>
        <div className="bs-toolbar-controls">
          <div className="bs-control-group">
            <label className="bs-label mono">YEAR</label>
            <select className="bs-select" value={year} onChange={e => { setYear(+e.target.value); setData(null) }}>
              {years.map(y => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>
          <div className="bs-control-group">
            <label className="bs-label mono">SIMS</label>
            <div className="bs-sim-btns">
              {SIM_OPTIONS.map(o => (
                <button
                  key={o.value}
                  className={`bs-sim-btn${nSims === o.value ? ' active' : ''}`}
                  onClick={() => setNSims(o.value)}
                >
                  {o.label}
                </button>
              ))}
            </div>
          </div>
          <button className="bs-run-btn" onClick={runSimulation} disabled={loading}>
            {loading ? 'Simulating…' : `▶ Run ${(nSims/1000).toFixed(0)}k Simulations`}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && <div className="bs-error mono">{error}</div>}

      {/* Loading */}
      {loading && (
        <div className="bs-loading">
          <div className="bs-loading-spinner" />
          <div className="bs-loading-text mono">
            Running {nSims.toLocaleString()} simulations for {year}…
          </div>
          <div className="bs-loading-sub mono">Precomputing probability matrix + Monte Carlo sampling</div>
        </div>
      )}

      {/* Empty state */}
      {!loading && !data && !error && (
        <div className="bs-empty">
          <div className="bs-empty-title display">Run a Simulation</div>
          <div className="bs-empty-sub mono">
            Select a year and simulation count, then click Run.
            The model will simulate the full 64-team bracket {nSims.toLocaleString()} times
            using probabilistic game-by-game predictions.
          </div>
        </div>
      )}

      {/* Results */}
      {data && !loading && (
        <>
          {/* Stats bar */}
          <div className="bs-stats-bar mono">
            <span>{data.n_sims.toLocaleString()} simulations</span>
            <span className="bs-stats-dot"> · </span>
            <span>{data.year} tournament</span>
            <span className="bs-stats-dot"> · </span>
            <span>{data.teams.length} teams</span>
          </div>

          {/* Champion spotlight */}
          <ChampionSpotlight teams={data.teams} />

          {/* View toggle + region filter */}
          <div className="bs-filter-bar">
            <div className="bs-view-btns">
              <button className={`bs-view-btn${view === 'table' ? ' active' : ''}`} onClick={() => setView('table')}>
                📊 Advancement Table
              </button>
              <button className={`bs-view-btn${view === 'det' ? ' active' : ''}`} onClick={() => setView('det')}>
                🏆 Deterministic Picks
              </button>
            </div>
            {view === 'table' && (
              <div className="bs-region-tabs">
                {REGIONS.map(r => (
                  <button
                    key={r}
                    className={`bs-region-btn${region === r ? ' active' : ''}`}
                    onClick={() => setRegion(r)}
                  >
                    {r}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Heat table */}
          {view === 'table' && (
            <HeatTable
              teams={filteredTeams}
              sortKey={sortKey}
              sortDir={sortDir}
              onSort={k => {
                if (k === sortKey) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
                else { setSortKey(k); setSortDir('desc') }
              }}
            />
          )}

          {/* Deterministic picks */}
          {view === 'det' && <DetBracket games={data.deterministic} />}
        </>
      )}
    </div>
  )
}
