import { useState, useEffect, useCallback, useRef } from 'react'
import TeamAvatar from './TeamAvatar'

// ── Constants ─────────────────────────────────────────────────────────────────

const CATEGORIES = ['Efficiency', 'Four Factors', 'Shooting', 'Momentum', 'Roster', 'Program']

const CAT_ICONS = {
  Efficiency:    '⚡',
  'Four Factors':'🏀',
  Shooting:      '🎯',
  Momentum:      '📈',
  Roster:        '👥',
  Program:       '🏆',
}

// Higher = better for these stats (team1 advantage if diff > 0)
const HIGHER_IS_BETTER = new Set([
  'AdjEM_diff','AdjOE_diff','AdjTempo_diff','net_score_rate_diff',
  'efg_pct_off_diff','or_pct_off_diff','ftr_off_diff','fg3a_rate_off_diff',
  'fg3_pct_off_diff','fg2_pct_off_diff','blk_pct_def_diff','stl_rate_def_diff',
  'apl_off_diff','apl_def_diff','avg_height_diff','d1_exp_diff',
  'two_way_depth_diff','star_eup_diff','depth_eup_diff','interior_dom_diff',
  'returning_min_pct_diff','program_tourney_rate_l5_diff','program_f4_rate_l10_diff',
  'l10_net_eff_diff','l10_off_eff_diff','l10_win_pct_diff','l10_efg_diff',
])
// Lower = better
const LOWER_IS_BETTER = new Set([
  'AdjDE_diff','efg_pct_def_diff','to_pct_off_diff','to_pct_def_diff',
  'or_pct_def_diff','ftr_def_diff','fg3a_rate_def_diff','l10_def_eff_diff',
  'l10_to_pct_diff','l10_opp_rank_diff',
])

function team1Wins(feat) {
  if (feat.diff == null) return null
  if (HIGHER_IS_BETTER.has(feat.key)) return feat.diff > 0
  if (LOWER_IS_BETTER.has(feat.key))  return feat.diff < 0
  return feat.diff > 0
}

function fmtVal(v, key) {
  if (v == null) return '—'
  const k = key.replace('_diff','')
  if (k.includes('pct') || k.includes('rate') || k.includes('win_pct') ||
      k.includes('tourney') || k.includes('f4')) {
    const f = v <= 1 ? v * 100 : v
    return f.toFixed(1) + '%'
  }
  if (k === 'avg_height') return v.toFixed(1) + '"'
  return Math.abs(v) < 1 ? v.toFixed(3) : v.toFixed(1)
}

// ── Win probability bar ───────────────────────────────────────────────────────

function ProbBar({ prob1, team1, team2, loading }) {
  const p1 = Math.round((prob1 ?? 0.5) * 100)
  const p2 = 100 - p1
  const favor = p1 > p2 ? 1 : p1 < p2 ? 2 : 0

  return (
    <div className="mb-prob-wrap">
      <div className="mb-prob-pcts">
        <span className="mb-prob-pct mono" style={{ color: favor === 1 ? '#22c55e' : 'var(--cream-dim)' }}>
          {p1}%
        </span>
        <span className="mb-prob-label mono">WIN PROBABILITY</span>
        <span className="mb-prob-pct mono" style={{ color: favor === 2 ? '#22c55e' : 'var(--cream-dim)' }}>
          {p2}%
        </span>
      </div>
      <div className="mb-prob-bar-track">
        <div
          className="mb-prob-bar-t1"
          style={{ width: `${p1}%`, opacity: loading ? 0.4 : 1, transition: 'width 0.6s cubic-bezier(.4,0,.2,1)' }}
        />
      </div>
      {favor !== 0 && !loading && (
        <div className="mb-prob-verdict mono">
          {favor === 1 ? team1 : team2} wins {Math.max(p1, p2)}–{Math.min(p1, p2)}
        </div>
      )}
      {!prob1 && !loading && (
        <div className="mb-prob-verdict mono" style={{ opacity: 0.4 }}>Select both teams to see prediction</div>
      )}
    </div>
  )
}

// ── Feature category summary pills ───────────────────────────────────────────

function CategorySummary({ features, team1Name, team2Name }) {
  const catScores = {}
  CATEGORIES.forEach(c => { catScores[c] = { t1: 0, t2: 0 } })

  features.forEach(f => {
    const cat = f.category
    if (!catScores[cat]) return
    const w = team1Wins(f)
    if (w === true)  catScores[cat].t1++
    if (w === false) catScores[cat].t2++
  })

  return (
    <div className="mb-cat-summary">
      {CATEGORIES.map(cat => {
        const { t1, t2 } = catScores[cat] || { t1: 0, t2: 0 }
        const total = t1 + t2
        if (total === 0) return null
        const winner = t1 > t2 ? 1 : t2 > t1 ? 2 : 0
        return (
          <div key={cat} className={`mb-cat-pill ${winner === 1 ? 'pill-t1' : winner === 2 ? 'pill-t2' : 'pill-tie'}`}>
            <span className="mb-cat-icon">{CAT_ICONS[cat]}</span>
            <span className="mb-cat-name">{cat}</span>
            <span className="mb-cat-score mono">{t1}–{t2}</span>
          </div>
        )
      })}
    </div>
  )
}

// ── Feature breakdown table ───────────────────────────────────────────────────

function FeatureBreakdown({ features, team1Name, team2Name }) {
  const [activeCat, setActiveCat] = useState('Efficiency')

  const cats = CATEGORIES.filter(c =>
    features.some(f => f.category === c && f.v1 != null && f.v2 != null)
  )

  const shown = features.filter(f =>
    f.category === activeCat && f.v1 != null && f.v2 != null
  )

  if (!features.length) return null

  const maxDiff = Math.max(...shown.map(f => Math.abs(f.diff ?? 0)), 0.001)

  return (
    <div className="mb-breakdown">
      {/* Category tabs */}
      <div className="mb-cat-tabs">
        {cats.map(c => (
          <button
            key={c}
            className={`mb-cat-tab${activeCat === c ? ' active' : ''}`}
            onClick={() => setActiveCat(c)}
          >
            {CAT_ICONS[c]} {c}
          </button>
        ))}
      </div>

      {/* Rows */}
      <div className="mb-feat-rows">
        <div className="mb-feat-header">
          <span className="mb-feat-h-team mono">{team1Name.split(' ').slice(-1)[0].toUpperCase()}</span>
          <span className="mb-feat-h-label" />
          <span className="mb-feat-h-team mono">{team2Name.split(' ').slice(-1)[0].toUpperCase()}</span>
        </div>

        {shown.map(f => {
          const w = team1Wins(f)
          const barPct = (Math.abs(f.diff ?? 0) / maxDiff) * 100
          const t1Wins = w === true
          const t2Wins = w === false

          return (
            <div key={f.key} className="mb-feat-row">
              {/* Team 1 value */}
              <span className={`mb-feat-val mono ${t1Wins ? 'val-win' : t2Wins ? 'val-lose' : ''}`}>
                {fmtVal(f.v1, f.key)}
              </span>

              {/* Label + diverging bar */}
              <div className="mb-feat-center">
                <div className="mb-feat-label">{f.label}</div>
                <div className="mb-feat-bar-wrap">
                  {/* Team 1 bar — extends LEFT from center */}
                  <div className="mb-feat-bar mb-feat-bar-t1"
                    style={{ width: `${barPct / 2}%`, right: '50%', opacity: t1Wins ? 1 : 0.15 }} />
                  {/* Team 2 bar — extends RIGHT from center */}
                  <div className="mb-feat-bar mb-feat-bar-t2"
                    style={{ width: `${barPct / 2}%`, left: '50%', opacity: t2Wins ? 1 : 0.15 }} />
                  <div className="mb-feat-bar-center" />
                </div>
              </div>

              {/* Team 2 value */}
              <span className={`mb-feat-val mono ${t2Wins ? 'val-win' : t1Wins ? 'val-lose' : ''}`}>
                {fmtVal(f.v2, f.key)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Roster side-by-side ───────────────────────────────────────────────────────

function RosterTable({ roster, name }) {
  const CLASS_COLORS = { Fr:'#60a5fa', So:'#34d399', Jr:'#fbbf24', Sr:'#f87171' }
  return (
    <div className="mb-roster-col">
      <div className="mb-roster-team-label mono">{name}</div>
      {!roster?.length ? (
        <div className="mb-roster-empty mono">No player data available for this season</div>
      ) : (
        <table className="mb-roster-table">
          <thead>
            <tr>
              <th>Player</th><th>G</th><th>PPG</th><th>FG%</th><th>3P%</th><th>FT%</th>
            </tr>
          </thead>
          <tbody>
            {roster.map((p, i) => (
              <tr key={i} className={p.starter ? 'mb-starter' : ''}>
                <td>
                  <span className="mb-p-name">{p.name || '—'}</span>
                  {p.year_class && (
                    <span className="mb-p-class" style={{ color: CLASS_COLORS[p.year_class] || 'var(--cream-dim)' }}>
                      {p.year_class}
                    </span>
                  )}
                </td>
                <td className="mono">{p.games ?? '—'}</td>
                <td className="mono">{p.ppg ?? '—'}</td>
                <td className="mono">{p.fg_pct != null ? p.fg_pct.toFixed(1) + '%' : '—'}</td>
                <td className="mono">{p.fg3_pct != null ? (p.fg3_pct <= 1 ? (p.fg3_pct * 100).toFixed(1) : p.fg3_pct.toFixed(1)) + '%' : '—'}</td>
                <td className="mono">{p.ft_pct != null ? (p.ft_pct <= 1 ? (p.ft_pct * 100).toFixed(1) : p.ft_pct.toFixed(1)) + '%' : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function RosterCompare({ roster1, roster2, name1, name2 }) {
  if (!roster1?.length && !roster2?.length) return null
  return (
    <div className="mb-rosters">
      <div className="mb-roster-title display">Rosters</div>
      <div className="mb-roster-grid">
        <RosterTable roster={roster1} name={name1} />
        <RosterTable roster={roster2} name={name2} />
      </div>
    </div>
  )
}

// ── Team selector panel ───────────────────────────────────────────────────────

function TeamSelector({ allTeams, year, team, onYearChange, onTeamChange, side, result, meta }) {
  const years = [...new Set(allTeams.map(t => t.year))].sort((a, b) => b - a)
  const teamsForYear = allTeams.filter(t => t.year === year).sort((a, b) =>
    (a.seed ?? 99) - (b.seed ?? 99) || a.team.localeCompare(b.team)
  )

  const roundColors = {
    Champion: '#c9a84c', 'Final Four': '#22c55e', 'Elite 8': '#3b82f6',
    'Sweet 16': '#a78bfa', R32: 'var(--cream-dim)', R64: 'var(--cream-dim)',
  }

  return (
    <div className={`mb-team-panel mb-team-${side}`}>
      <div className="mb-selectors">
        <select className="mb-select" value={year} onChange={e => onYearChange(+e.target.value)}>
          {years.map(y => <option key={y} value={y}>{y}</option>)}
        </select>
        <select className="mb-select mb-select-team" value={team || ''} onChange={e => onTeamChange(e.target.value)}>
          <option value="">— select team —</option>
          {teamsForYear.map(t => (
            <option key={t.team} value={t.team}>
              {t.seed ? `#${t.seed} ` : ''}{t.team}
            </option>
          ))}
        </select>
      </div>

      {team && (
        <div className="mb-team-card">
          <TeamAvatar team={team} size={56} />
          <div className="mb-team-info">
            <div className="mb-team-name display">{team}</div>
            <div className="mb-team-badges">
              {meta?.seed    && <span className="badge seed-badge">#{meta.seed} Seed</span>}
              {meta?.conf    && <span className="badge">{meta.conf}</span>}
              {meta?.round_label && (
                <span className="badge" style={{ borderColor: roundColors[meta.round_label] || 'var(--border-color)', color: roundColors[meta.round_label] || 'var(--cream-dim)' }}>
                  {meta.is_champion ? '★ Champion' : meta.round_label}
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function MatchupBuilder({ allTeams = [] }) {
  const years    = [...new Set(allTeams.map(t => t.year))].sort((a, b) => b - a)
  const initYear = years[0] ?? 2025

  const [year1,  setYear1]  = useState(initYear)
  const [team1,  setTeam1]  = useState('')
  const [year2,  setYear2]  = useState(initYear)
  const [team2,  setTeam2]  = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,  setError]  = useState(null)

  // Fetch whenever both teams are selected
  const fetchMatchup = useCallback(async (y1, t1, y2, t2) => {
    if (!t1 || !t2) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `/api/matchup/${y1}/${encodeURIComponent(t1)}/${y2}/${encodeURIComponent(t2)}`
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || res.statusText)
      }
      setResult(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchMatchup(year1, team1, year2, team2) }, [year1, team1, year2, team2])

  // Random matchup
  function randomMatchup() {
    const pool = allTeams.filter(t => t.year !== 2026)
    if (pool.length < 2) return
    const picks = []
    while (picks.length < 2) {
      const p = pool[Math.floor(Math.random() * pool.length)]
      if (!picks.find(x => x.team === p.team && x.year === p.year)) picks.push(p)
    }
    setYear1(picks[0].year); setTeam1(picks[0].team)
    setYear2(picks[1].year); setTeam2(picks[1].team)
  }

  // Flip teams
  function flipTeams() {
    const [oy1, ot1, oy2, ot2] = [year1, team1, year2, team2]
    setYear1(oy2); setTeam1(ot2)
    setYear2(oy1); setTeam2(ot1)
  }

  const crossEra  = team1 && team2 && year1 !== year2
  const sameResult = result?.same_year_result

  const meta1 = result?.team1_meta ?? {}
  const meta2 = result?.team2_meta ?? {}

  return (
    <div className="mb-viewer">

      {/* ── Toolbar ── */}
      <div className="mb-toolbar">
        <div className="mb-toolbar-title display">Matchup Builder</div>
        <div className="mb-toolbar-actions">
          {crossEra && (
            <span className="mb-cross-era-badge mono">⚡ Cross-Era Showdown</span>
          )}
          <button className="mb-action-btn" onClick={randomMatchup} title="Random matchup">
            🎲 Random
          </button>
          <button className="mb-action-btn" onClick={flipTeams} disabled={!team1 || !team2}>
            ⇄ Flip
          </button>
        </div>
      </div>

      {/* ── Main matchup row ── */}
      <div className="mb-matchup-row">
        <TeamSelector
          allTeams={allTeams} year={year1} team={team1}
          onYearChange={y => { setYear1(y); setTeam1('') }}
          onTeamChange={setTeam1}
          side="left" meta={meta1}
        />

        <div className="mb-center-col">
          <div className="mb-vs mono">VS</div>
          {(team1 && team2) && (
            <ProbBar
              prob1={result?.prob1}
              team1={team1} team2={team2}
              loading={loading}
            />
          )}
          {sameResult && (
            <div className="mb-history-badge mono">
              {sameResult.winner ? `${sameResult.winner} won ${sameResult.score} · ${sameResult.round}` : 'These teams met'}
            </div>
          )}
          {error && (
            <div className="mb-error mono">{error}</div>
          )}
        </div>

        <TeamSelector
          allTeams={allTeams} year={year2} team={team2}
          onYearChange={y => { setYear2(y); setTeam2('') }}
          onTeamChange={setTeam2}
          side="right" meta={meta2}
        />
      </div>

      {/* ── Content (only when both selected) ── */}
      {result && (
        <>
          {/* Category summary */}
          <CategorySummary
            features={result.features}
            team1Name={team1} team2Name={team2}
          />

          {/* Feature breakdown */}
          <FeatureBreakdown
            features={result.features}
            team1Name={team1} team2Name={team2}
          />

          {/* Roster comparison */}
          <RosterCompare
            roster1={result.team1_roster}
            roster2={result.team2_roster}
            name1={team1} name2={team2}
          />
        </>
      )}

      {!team1 && !team2 && (
        <div className="state-msg" style={{ marginTop: 32 }}>
          Pick any two teams — from any year, any era — to see a head-to-head prediction.
          <br />
          <span className="mono" style={{ fontSize: '0.72rem', opacity: 0.5 }}>
            Try: 2008 Memphis vs 2015 Duke · 2012 Kentucky vs 2019 Virginia · 2026 vs any legend
          </span>
        </div>
      )}
    </div>
  )
}
