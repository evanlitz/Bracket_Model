import { useState, useEffect } from 'react'
import TeamAvatar from './TeamAvatar'
import MatchupCompare from './MatchupCompare'
import PlayerRoster from './PlayerRoster'
import { resultBadgeClass } from './utils'

// Normalise a 0–1 decimal OR already-percent value to display string
function fmtPct(v, decimals = 1) {
  if (v == null) return null
  const pct = v > 1 ? v : v * 100
  return pct.toFixed(decimals) + '%'
}

// Tab label: up to 4-char abbreviation from team name
function teamAbbr(name) {
  const SKIP = new Set(['of', 'the', 'at', 'and', 'a'])
  const words = name.replace(/\./g, '').trim().split(/\s+/)
  const m = words.filter(w => !SKIP.has(w.toLowerCase()))
  if (m.length === 0) return name.slice(0, 4).toUpperCase()
  if (m.length === 1) return m[0].slice(0, 4).toUpperCase()
  return m.map(w => w[0]).join('').slice(0, 4).toUpperCase()
}

const TEAM_DISPLAY = [
  { key: 'AdjEM',                   label: 'Adj EM',           fmt: v => v?.toFixed(1) },
  { key: 'AdjOE',                   label: 'Adj OE',           fmt: v => v?.toFixed(1) },
  { key: 'AdjDE',                   label: 'Adj DE',           fmt: v => v?.toFixed(1) },
  { key: 'AdjTempo',                label: 'Tempo',            fmt: v => v?.toFixed(1) },
  { key: 'efg_pct_off',             label: 'eFG% Off',         fmt: v => fmtPct(v) },
  { key: 'efg_pct_def',             label: 'eFG% Def',         fmt: v => fmtPct(v) },
  { key: 'or_pct_off',              label: 'Off Reb%',         fmt: v => fmtPct(v) },
  { key: 'to_pct_off',              label: 'TO% Off',          fmt: v => fmtPct(v) },
  { key: 'blk_pct_def',             label: 'Blk% Def',         fmt: v => fmtPct(v) },
  { key: 'program_tourney_rate_l5', label: 'Tourney Rate',     fmt: v => fmtPct(v) },
  { key: 'program_f4_rate_l10',     label: 'F4 Rate 10yr',    fmt: v => fmtPct(v) },
  { key: 'avg_height',              label: 'Avg Height',       fmt: v => v != null ? v.toFixed(1) + '"' : null },
  { key: 'd1_exp',                  label: 'D1 Exp',           fmt: v => v?.toFixed(2) },
  { key: 'l10_net_eff',             label: 'L10 Net Eff',     fmt: v => v?.toFixed(1) },
  { key: 'l10_off_eff',             label: 'L10 Off Eff',     fmt: v => v?.toFixed(1) },
  { key: 'l10_def_eff',             label: 'L10 Def Eff',     fmt: v => v?.toFixed(1) },
]

const PLAYER_DISPLAY = [
  { key: 'star_eup',          label: 'Star EUP',    fmt: v => v?.toFixed(2) },
  { key: 'depth_eup',         label: 'Depth EUP',   fmt: v => v?.toFixed(2) },
  { key: 'two_way_depth',     label: 'Two-Way',     fmt: v => v?.toFixed(2) },
  { key: 'interior_dom',      label: 'Interior',    fmt: v => v?.toFixed(2) },
  { key: 'triple_threat',     label: 'Triple',      fmt: v => v?.toFixed(3) },
  { key: 'returning_min_pct', label: 'Returning%',  fmt: v => fmtPct(v, 0) },
]

function TeamDetailPanel({ profile }) {
  if (!profile) {
    return <div className="state-msg" style={{ marginTop: 24 }}>No data available</div>
  }

  const { seed, conf, round_label, is_champion, key_stats = {}, player_roster = [] } = profile
  const badgeClass = resultBadgeClass(round_label, is_champion)

  return (
    <div className="team-detail-panel">
      <div className="team-meta" style={{ marginBottom: 14 }}>
        {seed      && <span className="badge seed-badge">#{seed} Seed</span>}
        {conf      && <span className="badge">{conf}</span>}
        {round_label && (
          <span className={`badge ${badgeClass}`}>
            {is_champion ? '★ CHAMPION' : round_label}
          </span>
        )}
      </div>

      <div className="section-label">Team Stats</div>
      <div className="stat-grid" style={{ marginTop: 8, marginBottom: 14 }}>
        {TEAM_DISPLAY.map(({ key, label, fmt }) => {
          const v = key_stats[key]
          if (v == null) return null
          const formatted = fmt(v)
          if (formatted == null) return null
          return (
            <div key={key} className="stat-item">
              <div className="stat-label">{label}</div>
              <div className="stat-value">{formatted}</div>
            </div>
          )
        })}
      </div>

      <div className="section-label">Player Profile</div>
      <div className="stat-grid" style={{ marginTop: 8, marginBottom: 14 }}>
        {PLAYER_DISPLAY.map(({ key, label, fmt }) => {
          const v = key_stats[key]
          if (v == null) return null
          const formatted = fmt(v)
          if (formatted == null) return null
          return (
            <div key={key} className="stat-item">
              <div className="stat-label">{label}</div>
              <div className="stat-value neutral">{formatted}</div>
            </div>
          )
        })}
      </div>

      <PlayerRoster players={player_roster} label="Roster" />
    </div>
  )
}

export default function MatchupModal({ game, year, seedLookup, is2026, picks, onClose, onPick }) {
  const [activeTab, setActiveTab]     = useState('compare')
  const [team1Profile, setTeam1Profile] = useState(null)
  const [team2Profile, setTeam2Profile] = useState(null)
  const [loading, setLoading]         = useState(true)
  const [fetchError, setFetchError]   = useState(null)

  const {
    match_id, team1, team2, prob,
    winner, actual_winner, score1, score2, correct, round_name,
  } = game

  const seed1      = seedLookup?.[team1]
  const seed2      = seedLookup?.[team2]
  const prob1Pct   = Math.round((prob ?? 0.5) * 100)
  const prob2Pct   = 100 - prob1Pct
  const pickedTeam = picks?.[match_id]

  // Fetch both team profiles in parallel whenever the matchup changes
  useEffect(() => {
    setLoading(true)
    setFetchError(null)
    setTeam1Profile(null)
    setTeam2Profile(null)
    setActiveTab('compare')

    Promise.all([
      fetch(`/api/team/${year}/${encodeURIComponent(team1)}`).then(r => r.ok ? r.json() : null).catch(() => null),
      fetch(`/api/team/${year}/${encodeURIComponent(team2)}`).then(r => r.ok ? r.json() : null).catch(() => null),
    ])
      .then(([p1, p2]) => {
        setTeam1Profile(p1)
        setTeam2Profile(p2)
      })
      .catch(() => setFetchError('Failed to load team data'))
      .finally(() => setLoading(false))
  }, [team1, team2, year])

  // Close on Escape key
  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  function handleOverlayClick(e) {
    if (e.target === e.currentTarget) onClose()
  }

  // prob is always team1's win probability.
  // Color the higher-probability side in green, lower in dim.
  const team1IsWinner = prob1Pct >= prob2Pct
  const leftPct   = prob1Pct
  const rightPct  = prob2Pct
  const leftColor  = team1IsWinner ? '#22c55e' : 'var(--cream-dim)'
  const rightColor = team1IsWinner ? 'var(--cream-dim)' : '#22c55e'

  // Score: show winner's score first regardless of team1/team2 order
  const winnerScore = actual_winner === team1 ? score1 : score2
  const loserScore  = actual_winner === team1 ? score2 : score1

  return (
    <div className="matchup-overlay" onClick={handleOverlayClick}>
      <div className="matchup-modal">

        {/* Close */}
        <button className="matchup-close" onClick={onClose} aria-label="Close">✕</button>

        {/* ── Header ── */}
        <div className="matchup-header">

          {/* Team 1 */}
          <div className="matchup-team matchup-team-left">
            <TeamAvatar team={team1} size={52} />
            {seed1 != null && <span className="matchup-seed mono">#{seed1} SEED</span>}
            <span className="matchup-team-name display">{team1}</span>
            <span className="matchup-team-prob mono" style={{ color: leftColor }}>{leftPct}%</span>
          </div>

          {/* Center — bar + round */}
          <div className="matchup-center">
            <div className="matchup-vs-label mono">VS</div>
            <div className="matchup-prob-bar-track">
              <div className="matchup-prob-bar-fill" style={{ width: `${leftPct}%` }} />
            </div>
            <div className="matchup-round mono">{round_name}</div>
          </div>

          {/* Team 2 */}
          <div className="matchup-team matchup-team-right">
            <TeamAvatar team={team2} size={52} />
            {seed2 != null && <span className="matchup-seed mono">#{seed2} SEED</span>}
            <span className="matchup-team-name display">{team2}</span>
            <span className="matchup-team-prob mono" style={{ color: rightColor }}>{rightPct}%</span>
          </div>

        </div>

        {/* ── Result banner (historical only) ── */}
        {actual_winner && (
          <div className={`matchup-result-banner ${correct ? 'banner-correct' : 'banner-wrong'}`}>
            <span className="mono">
              {correct ? '✓' : '✗'}&nbsp;{actual_winner} won {winnerScore}–{loserScore}
              {!correct && (
                <span style={{ opacity: 0.65 }}>&nbsp;· model predicted {winner}</span>
              )}
            </span>
          </div>
        )}

        {/* ── Tab bar ── */}
        <div className="matchup-tabs">
          <button
            className={`matchup-tab-btn${activeTab === 'team1' ? ' active' : ''}`}
            onClick={() => setActiveTab('team1')}
          >
            {teamAbbr(team1)}
          </button>
          <button
            className={`matchup-tab-btn${activeTab === 'compare' ? ' active' : ''}`}
            onClick={() => setActiveTab('compare')}
          >
            COMPARE
          </button>
          <button
            className={`matchup-tab-btn${activeTab === 'team2' ? ' active' : ''}`}
            onClick={() => setActiveTab('team2')}
          >
            {teamAbbr(team2)}
          </button>
        </div>

        {/* ── Body ── */}
        <div className="matchup-body">
          {loading && <div className="state-msg loading">Loading team data…</div>}
          {fetchError && (
            <div className="state-msg" style={{ color: 'var(--red-bright)' }}>{fetchError}</div>
          )}
          {!loading && !fetchError && (
            <>
              {activeTab === 'compare' && (
                <MatchupCompare
                  team1Name={team1}
                  team2Name={team2}
                  team1Stats={team1Profile?.key_stats}
                  team2Stats={team2Profile?.key_stats}
                />
              )}
              {activeTab === 'team1' && <TeamDetailPanel profile={team1Profile} />}
              {activeTab === 'team2' && <TeamDetailPanel profile={team2Profile} />}
            </>
          )}
        </div>

        {/* ── Pick buttons (2026 only) ── */}
        {is2026 && (
          <div className="matchup-picks">
            <button
              className={`pick-btn pick-btn-left${pickedTeam === team1 ? ' picked' : ''}`}
              onClick={() => onPick(match_id, team1)}
            >
              ← Pick {team1}
            </button>
            <button
              className={`pick-btn pick-btn-right${pickedTeam === team2 ? ' picked' : ''}`}
              onClick={() => onPick(match_id, team2)}
            >
              Pick {team2} →
            </button>
          </div>
        )}

      </div>
    </div>
  )
}
