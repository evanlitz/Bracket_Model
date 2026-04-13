import { useState, useEffect, useMemo } from 'react'
import TeamAvatar from './TeamAvatar'

// ── Constants ─────────────────────────────────────────────────────────────────

const ROUND_NUM    = { R64:1, R32:2, S16:3, E8:4, F4:5, NCG:6 }
const CURRENT_YEAR = 2026

const CIN_MILESTONES = [
  { key: 's16', label: 'Sweet 16' },
  { key: 'e8',  label: 'Elite 8'  },
  { key: 'f4',  label: 'Final Four' },
]

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
  const { favorite, favorite_seed, underdog, underdog_seed,
          model_upset_prob, upset_happened, model_called_upset,
          completed, round_name, region, year,
          score_fav, score_und } = game

  const t = tier(model_upset_prob)
  const barW = Math.round(model_upset_prob * 100)
  const favWon = completed && !upset_happened
  const undWon = completed && upset_happened

  return (
    <div className={`uf-card uf-alert-card ${completed ? (upset_happened ? 'uf-card-upset' : 'uf-card-held') : 'uf-card-upcoming'}`}>

      <div className="uf-card-header">
        <span className="uf-card-tag mono">{region} · {round_name} · {year}</span>
        <div className="uf-card-header-badges">
          {model_called_upset && (
            <span className="uf-model-called mono">★ MODEL</span>
          )}
          <span className={`uf-tier ${t.cls} mono`}>{t.label}</span>
        </div>
      </div>

      <div className="uf-matchup">
        <div className="uf-team uf-team-fav">
          <span className="uf-seed mono">{favorite_seed}</span>
          <TeamAvatar team={favorite} size={22} />
          <span className="uf-name">{favorite}</span>
          {completed && (
            <span className={`uf-score mono ${favWon ? 'uf-score-win' : 'uf-score-lose'}`}>
              {score_fav ?? '—'}
            </span>
          )}
        </div>
        <div className="uf-team uf-team-und">
          <span className="uf-seed uf-seed-und mono">{underdog_seed}</span>
          <TeamAvatar team={underdog} size={22} />
          <span className="uf-name uf-name-und">{underdog}</span>
          {completed && (
            <span className={`uf-score mono ${undWon ? 'uf-score-win' : 'uf-score-lose'}`}>
              {score_und ?? '—'}
            </span>
          )}
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
            ✓ UPSET — {underdog} wins {score_und != null && score_fav != null ? `${score_und}–${score_fav}` : ''}
          </span>
        )}
        {completed && !upset_happened && (
          <span className="uf-status uf-status-held mono">
            ✗ FAVORITE HELD — {favorite} wins {score_fav != null && score_und != null ? `${score_fav}–${score_und}` : ''}
          </span>
        )}
      </div>
    </div>
  )
}

// ── Cinderella Card ───────────────────────────────────────────────────────────

function CinderellaCard({ team, baselines }) {
  const { team: name, seed, region, adv } = team
  const bl = baselines[String(seed)] || {}

  const milestones = CIN_MILESTONES.map(({ key, label }) => {
    const sim  = adv[key] ?? 0
    const avg  = bl[key]  ?? 0
    return { key, label, sim, avg, edge: sim - avg }
  })

  const s16Edge = milestones[0].edge
  const isCinderella = s16Edge > 0.005

  return (
    <div className={`uf-card uf-cin-card ${isCinderella ? 'uf-cin-positive' : 'uf-cin-neutral'}`}>

      {/* Logo + name header */}
      <div className="uf-cin-team-header">
        <TeamAvatar team={name} size={40} />
        <div className="uf-cin-team-info">
          <div className="uf-cin-name display">{name}</div>
          <div className="uf-cin-team-meta mono">
            #{seed} seed · {region}
            {isCinderella && <span className="uf-cin-badge">CINDERELLA</span>}
          </div>
        </div>
      </div>

      {/* Three milestone sections */}
      {milestones.map(({ key, label, sim, avg, edge }) => (
        <div key={key} className="uf-cin-milestone">
          <div className="uf-cin-stat-label mono">{label}</div>
          <div className="uf-cin-bars">
            <div className="uf-cin-bar-row">
              <span className="uf-cin-bar-label mono">MODEL</span>
              <div className="uf-cin-bar-track">
                <div className="uf-cin-bar-fill uf-cin-bar-model" style={{ width: `${Math.min(sim * 300, 100)}%` }} />
              </div>
              <span className={`uf-cin-bar-pct mono ${edge > 0.02 ? 'uf-cin-pct-hot' : ''}`}>{pct(sim)}</span>
            </div>
            <div className="uf-cin-bar-row">
              <span className="uf-cin-bar-label mono">AVG</span>
              <div className="uf-cin-bar-track">
                <div className="uf-cin-bar-fill uf-cin-bar-avg" style={{ width: `${Math.min(avg * 300, 100)}%` }} />
              </div>
              <span className="uf-cin-bar-pct mono">{pct(avg)}</span>
            </div>
          </div>
          <div className={`uf-cin-edge mono ${edge > 0 ? 'uf-edge-pos' : edge < 0 ? 'uf-edge-neg' : ''}`}>
            {edge > 0 ? '+' : ''}{pct(edge)} vs seed avg
          </div>
        </div>
      ))}
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
        const s16sim = t.adv['s16'] ?? 0
        const s16avg = (bl[String(t.seed)] || {})['s16'] ?? 0
        return { ...t, _s16: s16sim, _edge: s16sim - s16avg }
      })
      .sort((a, b) => b._s16 - a._s16)   // highest S16 chance first
  }, [simData, upsetData])

  const cinFiltered = useMemo(() => {
    return cinPositiveOnly ? cinderellas.filter(t => t._edge > 0.005) : cinderellas
  }, [cinderellas, cinPositiveOnly])

  // ── Stats summary ────────────────────────────────────────────────────────────

  const alertStats = useMemo(() => {
    const completed   = alerts2026.filter(g => g.completed)
    const upsets      = completed.filter(g => g.upset_happened)
    const backed      = completed.filter(g => g.model_called_upset)   // model gave und > 50%
    const backedHit   = backed.filter(g => g.upset_happened)          // backed + happened
    const highAlert   = completed.filter(g => g.model_upset_prob >= 0.40)
    const highHit     = highAlert.filter(g => g.upset_happened)
    const upcoming    = alerts2026.filter(g => !g.completed)
    return {
      upsets:    upsets.length,
      backed:    backed.length,
      backedHit: backedHit.length,
      highAlert: highAlert.length,
      highHit:   highHit.length,
      upcoming:  upcoming.length,
    }
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
            <span className="uf-stat-label mono">upsets happened</span>
          </div>
          <div className="uf-stat-pill">
            <span className="uf-stat-val mono">{alertStats.backedHit}/{alertStats.backed}</span>
            <span className="uf-stat-label mono">model backed hit</span>
          </div>
          <div className="uf-stat-pill">
            <span className="uf-stat-val mono">{alertStats.highHit}/{alertStats.highAlert}</span>
            <span className="uf-stat-label mono">high alerts fired</span>
          </div>
        </div>
      </div>

      {/* Tab bar */}
      <div className="uf-tabs">
        {[['alerts','2026 Alerts'], ['cinderella','Cinderella Watch']].map(([key, label]) => (
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


    </div>
  )
}
