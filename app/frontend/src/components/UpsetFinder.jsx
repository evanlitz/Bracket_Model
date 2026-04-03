import { useState, useEffect, useMemo } from 'react'

// ── Constants ─────────────────────────────────────────────────────────────────

const ROUND_ORDER  = ['R64','R32','S16','E8','F4','NCG']
const ROUND_NUM    = { R64:1, R32:2, S16:3, E8:4, F4:5, NCG:6 }
const CURRENT_YEAR = 2026

// Which round is the "meaningful milestone" for each seed group
function targetRound(seed) {
  if (seed <= 4)  return 's16'
  if (seed <= 6)  return 'f4'
  if (seed <= 9)  return 'e8'
  if (seed <= 12) return 's16'
  return 'r32'
}

const ROUND_LABELS = { r32:'R32', s16:'S16', e8:'E8', f4:'F4', ncg:'NCG', champ:'Champ' }

function pct(v, decimals = 0) {
  if (v == null) return '—'
  return `${(v * 100).toFixed(decimals)}%`
}

function tier(prob) {
  if (prob >= 0.40) return { label: 'HIGH ALERT', cls: 'uf-tier-high' }
  if (prob >= 0.30) return { label: 'WATCH',      cls: 'uf-tier-watch' }
  if (prob >= 0.20) return { label: 'POSSIBLE',   cls: 'uf-tier-possible' }
  return               { label: 'LONG SHOT',   cls: 'uf-tier-long' }
}

// ── Upset Alert Card ──────────────────────────────────────────────────────────

function AlertCard({ game }) {
  const { favorite, favorite_seed, underdog, underdog_seed, seed_diff,
          model_upset_prob, upset_happened, model_called_upset,
          completed, round_name, region, year,
          score_fav, score_und } = game

  const t = tier(model_upset_prob)
  const barW = Math.round(model_upset_prob * 100)

  return (
    <div className={`uf-card uf-alert-card ${completed ? (upset_happened ? 'uf-card-upset' : 'uf-card-held') : 'uf-card-upcoming'}`}>

      <div className="uf-card-header">
        <span className="uf-card-tag mono">{region} · {round_name} · {year}</span>
        <span className={`uf-tier ${t.cls} mono`}>{t.label}</span>
      </div>

      <div className="uf-matchup">
        <div className="uf-team uf-team-fav">
          <span className="uf-seed mono">{favorite_seed}</span>
          <span className="uf-name">{favorite}</span>
          {completed && !upset_happened && score_fav != null &&
            <span className="uf-score mono">{score_fav}</span>}
        </div>
        <div className="uf-team uf-team-und">
          <span className="uf-seed uf-seed-und mono">{underdog_seed}</span>
          <span className="uf-name uf-name-und">{underdog}</span>
          {completed && upset_happened && score_und != null &&
            <span className="uf-score mono">{score_und}</span>}
        </div>
      </div>

      <div className="uf-prob-row">
        <div className="uf-prob-bar-track">
          <div className="uf-prob-bar-fill" style={{ width: `${barW}%` }} />
        </div>
        <span className="uf-prob-label mono">{pct(model_upset_prob)} upset odds</span>
      </div>

      <div className="uf-card-footer">
        {!completed && (
          <span className="uf-status uf-status-upcoming mono">
            MODEL: {model_called_upset ? `BACKING ${underdog}` : `FAVORS ${favorite}`}
          </span>
        )}
        {completed && upset_happened && (
          <span className="uf-status uf-status-upset mono">
            ✓ UPSET — {underdog} {score_und != null ? `${score_und}–${score_fav}` : 'won'}
          </span>
        )}
        {completed && !upset_happened && (
          <span className="uf-status uf-status-held mono">
            ✗ FAVORITE HELD — {favorite} {score_fav != null ? `${score_fav}–${score_und}` : 'won'}
          </span>
        )}
      </div>
    </div>
  )
}

// ── Cinderella Card ───────────────────────────────────────────────────────────

function CinderellaCard({ team, baselines, rank }) {
  const { team: name, seed, region, adv } = team
  const bl = baselines[String(seed)] || {}
  const rk = targetRound(seed)
  const rkLabel = ROUND_LABELS[rk] || rk.toUpperCase()

  const simPct = adv[rk]    ?? 0
  const blPct  = bl[rk]     ?? 0
  const edge   = simPct - blPct

  // Secondary stat: F4 for seeds 9-12, NCG for 5-8
  const rk2      = seed <= 8 ? 'champ' : 'f4'
  const rkLabel2 = ROUND_LABELS[rk2]
  const simPct2  = adv[rk2] ?? 0
  const blPct2   = bl[rk2]  ?? 0

  const edgePositive = edge > 0.005

  return (
    <div className={`uf-card uf-cin-card ${edgePositive ? 'uf-cin-positive' : 'uf-cin-neutral'}`}>

      <div className="uf-card-header">
        <span className="uf-card-tag mono">{seed}-seed · {region}</span>
        {edgePositive && <span className="uf-cin-badge mono">CINDERELLA</span>}
      </div>

      <div className="uf-cin-name display">{name}</div>

      <div className="uf-cin-stat">
        <div className="uf-cin-stat-label mono">{rkLabel} odds</div>
        <div className="uf-cin-bars">
          <div className="uf-cin-bar-row">
            <span className="uf-cin-bar-label mono">MODEL</span>
            <div className="uf-cin-bar-track">
              <div className="uf-cin-bar-fill uf-cin-bar-model" style={{ width: `${Math.min(simPct * 300, 100)}%` }} />
            </div>
            <span className={`uf-cin-bar-pct mono ${edgePositive ? 'uf-cin-pct-hot' : ''}`}>{pct(simPct)}</span>
          </div>
          <div className="uf-cin-bar-row">
            <span className="uf-cin-bar-label mono">AVG</span>
            <div className="uf-cin-bar-track">
              <div className="uf-cin-bar-fill uf-cin-bar-avg" style={{ width: `${Math.min(blPct * 300, 100)}%` }} />
            </div>
            <span className="uf-cin-bar-pct mono">{pct(blPct)}</span>
          </div>
        </div>
        <div className={`uf-cin-edge mono ${edge > 0 ? 'uf-edge-pos' : edge < 0 ? 'uf-edge-neg' : ''}`}>
          {edge > 0 ? '+' : ''}{pct(edge)} model edge
        </div>
      </div>

      <div className="uf-cin-secondary mono">
        {rkLabel2}: model {pct(simPct2)} vs avg {pct(blPct2)}
      </div>
    </div>
  )
}

// ── Calibration strip ─────────────────────────────────────────────────────────

function CalibrationStrip({ games }) {
  const buckets = [
    { label: '20–30%', min: 0.20, max: 0.30 },
    { label: '30–40%', min: 0.30, max: 0.40 },
    { label: '40–50%', min: 0.40, max: 0.50 },
    { label: '50%+',   min: 0.50, max: 1.01 },
  ]

  return (
    <div className="uf-calibration">
      <div className="uf-cal-title mono">MODEL CALIBRATION — when model gives underdog X%, how often does the upset happen?</div>
      <div className="uf-cal-buckets">
        {buckets.map(b => {
          const inBucket = games.filter(g =>
            g.completed && g.model_upset_prob >= b.min && g.model_upset_prob < b.max
          )
          const happened = inBucket.filter(g => g.upset_happened).length
          const rate = inBucket.length > 0 ? happened / inBucket.length : null
          return (
            <div key={b.label} className="uf-cal-bucket">
              <div className="uf-cal-bucket-label mono">{b.label}</div>
              <div className="uf-cal-bucket-bar-track">
                <div className="uf-cal-bucket-bar" style={{ width: `${Math.round((rate ?? 0) * 100)}%` }} />
                {(() => {
                  const mean = inBucket.length > 0
                    ? inBucket.reduce((s, g) => s + g.model_upset_prob, 0) / inBucket.length
                    : (b.min + b.max) / 2
                  return <div className="uf-cal-bucket-expected" style={{ left: `${mean * 100}%` }} />
                })()}
              </div>
              <div className="uf-cal-bucket-stat mono">
                {rate != null ? `${pct(rate)} (${happened}/${inBucket.length})` : '—'}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function UpsetFinder() {
  const [upsetData,   setUpsetData]   = useState(null)
  const [simData,     setSimData]     = useState(null)
  const [tab,         setTab]         = useState('alerts')
  const [loading,     setLoading]     = useState(true)
  const [simLoading,  setSimLoading]  = useState(false)
  const [error,       setError]       = useState(null)
  const [simError,    setSimError]    = useState(null)

  // Alerts filters
  const [alertRound,  setAlertRound]  = useState('all')
  const [alertTier,   setAlertTier]   = useState('all')

  // Cinderella filter
  const [cinPositiveOnly, setCinPositiveOnly] = useState(false)

  // History filters
  const [histRound,   setHistRound]   = useState('all')
  const [histSeedMin, setHistSeedMin] = useState(3)  // min seed_diff
  const [histSort,    setHistSort]    = useState({ col: 'model_upset_prob', dir: 'desc' })

  useEffect(() => {
    fetch('/api/upsets')
      .then(r => r.json())
      .then(d => { setUpsetData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  function loadSim() {
    if (simData || simLoading) return
    setSimLoading(true)
    fetch(`/api/simulate/${CURRENT_YEAR}?n=2000`)
      .then(r => r.json())
      .then(d => { setSimData(d); setSimLoading(false) })
      .catch(e => { setSimError(e.message); setSimLoading(false) })
  }

  function handleTab(t) {
    setTab(t)
    if (t === 'cinderella') loadSim()
  }

  // ── Derived data ────────────────────────────────────────────────────────────

  const alerts2026 = useMemo(() => {
    if (!upsetData) return []
    return upsetData.upset_games
      .filter(g => g.year === CURRENT_YEAR && g.seed_diff >= 3)
      .sort((a, b) => b.model_upset_prob - a.model_upset_prob)
  }, [upsetData])

  const filteredAlerts = useMemo(() => {
    return alerts2026
      .filter(g => alertRound === 'all' || g.round_name === alertRound)
      .filter(g => {
        if (alertTier === 'all') return true
        if (alertTier === 'high')     return g.model_upset_prob >= 0.40
        if (alertTier === 'watch')    return g.model_upset_prob >= 0.30 && g.model_upset_prob < 0.40
        if (alertTier === 'possible') return g.model_upset_prob >= 0.20 && g.model_upset_prob < 0.30
        if (alertTier === 'longshot') return g.model_upset_prob < 0.20
        return true
      })
  }, [alerts2026, alertRound, alertTier])

  const cinderellas = useMemo(() => {
    if (!simData || !upsetData) return []
    const bl = upsetData.seed_baselines
    return simData.teams
      .filter(t => t.seed != null && t.seed >= 5)
      .map(t => {
        const rk    = targetRound(t.seed)
        const simPct = t.adv[rk] ?? 0
        const blPct  = (bl[String(t.seed)] || {})[rk] ?? 0
        return { ...t, _edge: simPct - blPct }
      })
      .sort((a, b) => b._edge - a._edge)
  }, [simData, upsetData])

  const histGames = useMemo(() => {
    if (!upsetData) return []
    const sorted = upsetData.upset_games
      .filter(g => g.year !== CURRENT_YEAR && g.completed)
      .filter(g => histRound === 'all' || g.round_name === histRound)
      .filter(g => g.seed_diff >= histSeedMin)
      .slice()
      .sort((a, b) => {
        const { col, dir } = histSort
        let av = a[col], bv = b[col]
        if (typeof av === 'string') av = av.toLowerCase(), bv = bv.toLowerCase()
        if (av < bv) return dir === 'asc' ? -1 : 1
        if (av > bv) return dir === 'asc' ? 1 : -1
        return 0
      })
    return sorted
  }, [upsetData, histRound, histSeedMin, histSort])

  function toggleHistSort(col) {
    setHistSort(prev => ({
      col,
      dir: prev.col === col && prev.dir === 'desc' ? 'asc' : 'desc'
    }))
  }

  const cinFiltered = useMemo(() => {
    return cinPositiveOnly ? cinderellas.filter(t => t._edge > 0.005) : cinderellas
  }, [cinderellas, cinPositiveOnly])

  // ── Stats summary ────────────────────────────────────────────────────────────

  const alertStats = useMemo(() => {
    const completed = alerts2026.filter(g => g.completed)
    const upsets    = completed.filter(g => g.upset_happened)
    const called    = upsets.filter(g => g.model_called_upset)
    const upcoming  = alerts2026.filter(g => !g.completed)
    return { total: alerts2026.length, completed: completed.length, upsets: upsets.length, called: called.length, upcoming: upcoming.length }
  }, [alerts2026])

  // ── Render ───────────────────────────────────────────────────────────────────

  if (loading) return (
    <div className="uf-viewer">
      <div className="uf-loading"><div className="uf-spinner" /><span className="mono">Loading upset data…</span></div>
    </div>
  )

  if (error) return (
    <div className="uf-viewer"><div className="uf-error mono">{error}</div></div>
  )

  const activeRounds2026 = [...new Set(alerts2026.map(g => g.round_name))].sort((a,b) => ROUND_NUM[a] - ROUND_NUM[b])

  return (
    <div className="uf-viewer">

      {/* Header */}
      <div className="uf-header">
        <div>
          <div className="uf-header-title display">Upset Finder</div>
          <div className="uf-header-sub mono">Model-backed underdogs · First-round shocks · Cinderella runs</div>
        </div>
        <div className="uf-header-stats">
          <div className="uf-stat-pill">
            <span className="uf-stat-val mono">{alertStats.upsets}</span>
            <span className="uf-stat-label mono">upsets so far</span>
          </div>
          <div className="uf-stat-pill">
            <span className="uf-stat-val mono">{alertStats.called}/{alertStats.upsets}</span>
            <span className="uf-stat-label mono">model called</span>
          </div>
          <div className="uf-stat-pill">
            <span className="uf-stat-val mono">{alertStats.upcoming}</span>
            <span className="uf-stat-label mono">alerts remaining</span>
          </div>
        </div>
      </div>

      {/* Tab bar */}
      <div className="uf-tabs">
        {[['alerts','2026 Alerts'], ['cinderella','Cinderella Watch'], ['history','Historical']].map(([key, label]) => (
          <button key={key} className={`uf-tab${tab === key ? ' active' : ''}`} onClick={() => handleTab(key)}>
            {label}
          </button>
        ))}
      </div>

      {/* ── 2026 Alerts ─────────────────────────────────────────────────── */}
      {tab === 'alerts' && (
        <div className="uf-section">
          <div className="uf-filters">
            <div className="uf-filter-group">
              <span className="uf-filter-label mono">ROUND</span>
              <div className="uf-filter-btns">
                <button className={`uf-filter-btn${alertRound === 'all' ? ' active' : ''}`} onClick={() => setAlertRound('all')}>All</button>
                {activeRounds2026.map(r => (
                  <button key={r} className={`uf-filter-btn${alertRound === r ? ' active' : ''}`} onClick={() => setAlertRound(r)}>{r}</button>
                ))}
              </div>
            </div>
            <div className="uf-filter-group">
              <span className="uf-filter-label mono">TIER</span>
              <div className="uf-filter-btns">
                {[['all','All'],['high','High Alert'],['watch','Watch'],['possible','Possible'],['longshot','Long Shot']].map(([k,l]) => (
                  <button key={k} className={`uf-filter-btn${alertTier === k ? ' active' : ''}`} onClick={() => setAlertTier(k)}>{l}</button>
                ))}
              </div>
            </div>
          </div>
          <div className="uf-cards-grid">
            {filteredAlerts.map(g => <AlertCard key={`${g.year}-${g.match_id}`} game={g} />)}
          </div>
          {filteredAlerts.length === 0 && (
            <div className="uf-empty mono">No games match the current filters.</div>
          )}
        </div>
      )}

      {/* ── Cinderella Watch ────────────────────────────────────────────── */}
      {tab === 'cinderella' && (
        <div className="uf-section">
          {simLoading && (
            <div className="uf-loading"><div className="uf-spinner" /><span className="mono">Running 2,000 simulations…</span></div>
          )}
          {simError && <div className="uf-error mono">{simError}</div>}
          {!simData && !simLoading && !simError && (
            <div className="uf-empty mono">Loading simulation data…</div>
          )}
          {simData && upsetData && (
            <>
              <div className="uf-cin-intro mono">
                Teams ranked by how much the model <em>exceeds</em> the historical average for their seed.
                A +10% edge means the model thinks this team is significantly better than their seed suggests.
              </div>
              <div className="uf-filters" style={{ marginBottom: 16 }}>
                <div className="uf-filter-group">
                  <span className="uf-filter-label mono">FILTER</span>
                  <div className="uf-filter-btns">
                    <button
                      className={`uf-filter-btn${cinPositiveOnly ? ' active' : ''}`}
                      onClick={() => setCinPositiveOnly(v => !v)}
                    >
                      Positive edge only
                    </button>
                  </div>
                </div>
              </div>
              <div className="uf-cards-grid uf-cin-grid">
                {cinFiltered.map((t, i) => (
                  <CinderellaCard key={t.team} team={t} baselines={upsetData.seed_baselines} rank={i + 1} />
                ))}
              </div>
              {cinFiltered.length === 0 && (
                <div className="uf-empty mono">No teams with positive model edge.</div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Historical ──────────────────────────────────────────────────── */}
      {tab === 'history' && upsetData && (
        <div className="uf-section">
          <CalibrationStrip games={upsetData.upset_games.filter(g => g.year !== CURRENT_YEAR && g.completed)} />

          <div className="uf-filters">
            <div className="uf-filter-group">
              <span className="uf-filter-label mono">ROUND</span>
              <div className="uf-filter-btns">
                {['all',...ROUND_ORDER].map(r => (
                  <button key={r} className={`uf-filter-btn${histRound === (r==='all'?'all':r) ? ' active' : ''}`}
                    onClick={() => setHistRound(r === 'all' ? 'all' : r)}>
                    {r === 'all' ? 'All' : r}
                  </button>
                ))}
              </div>
            </div>
            <div className="uf-filter-group">
              <span className="uf-filter-label mono">MIN SEED DIFF</span>
              <div className="uf-filter-btns">
                {[[2,'2+'],[3,'3+'],[5,'5+'],[7,'7+']].map(([v,l]) => (
                  <button key={v} className={`uf-filter-btn${histSeedMin === v ? ' active' : ''}`} onClick={() => setHistSeedMin(v)}>{l}</button>
                ))}
              </div>
            </div>
          </div>

          <div className="uf-hist-table-wrap">
            <table className="uf-hist-table">
              <thead>
                <tr>
                  {[['year','Year'],['round_name','Round'],['matchup','Matchup'],['model_upset_prob','Model Odds'],['upset_happened','Result']].map(([col, label]) => {
                    const sortable = col !== 'matchup'
                    const active   = histSort.col === col
                    return (
                      <th key={col} className="mono"
                        style={sortable ? { cursor: 'pointer', userSelect: 'none' } : {}}
                        onClick={sortable ? () => toggleHistSort(col) : undefined}
                      >
                        {label}{active ? (histSort.dir === 'desc' ? ' ▾' : ' ▴') : (sortable ? ' ·' : '')}
                      </th>
                    )
                  })}
                </tr>
              </thead>
              <tbody>
                {histGames.slice(0, 120).map(g => (
                  <tr key={`${g.year}-${g.match_id}`} className={`uf-hist-row ${g.upset_happened ? 'uf-hist-upset' : 'uf-hist-held'}`}>
                    <td className="mono">{g.year}</td>
                    <td className="mono">{g.round_name}</td>
                    <td>
                      <span className="uf-hist-seed mono">({g.underdog_seed})</span>
                      <span className="uf-hist-team">{g.underdog}</span>
                      <span className="uf-hist-vs mono"> vs </span>
                      <span className="uf-hist-seed mono">({g.favorite_seed})</span>
                      <span className="uf-hist-team">{g.favorite}</span>
                    </td>
                    <td className={`mono ${g.model_upset_prob >= 0.4 ? 'uf-prob-hot' : ''}`}>
                      {pct(g.model_upset_prob)}
                    </td>
                    <td className="mono">
                      {g.upset_happened
                        ? <span className="uf-result-upset">UPSET ✓</span>
                        : <span className="uf-result-held">held ✗</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  )
}
