import { useState, useEffect, useRef } from 'react'
import StatCompare from './StatCompare'
import BracketPath from './BracketPath'
import PlayerRoster from './PlayerRoster'
import { resultBadgeClass, resultLabel } from './utils'

// Tier color for the combined score badge
function tierStyle(score) {
  if (score >= 80) return { border: '2px solid var(--gold)',        color: 'var(--gold-bright)', bg: 'rgba(201,168,76,0.10)' }
  if (score >= 65) return { border: '2px solid #8a9bb0',            color: '#b0c4de',            bg: 'rgba(138,155,176,0.10)' }
  if (score >= 50) return { border: '2px solid #8b5e3c',            color: '#c4855a',            bg: 'rgba(139,94,60,0.10)' }
  return           { border: '2px solid #4a5568',                   color: '#718096',            bg: 'rgba(74,85,104,0.10)' }
}

function SubBar({ label, value, type }) {
  const [w, setW] = useState(0)
  useEffect(() => { const t = setTimeout(() => setW(value ?? 0), 80); return () => clearTimeout(t) }, [value])
  return (
    <div className="sim-sub-row">
      <div className="sim-sub-label mono">{label}</div>
      <div className="sim-sub-track">
        <div className={`sim-bar-fill ${type}-bar`} style={{ width: `${w}%` }} />
      </div>
      <div className="sim-sub-value display">{value ?? '—'}</div>
    </div>
  )
}

export default function MatchCard({ match, rank, queryStats = {}, queryRoster = [] }) {
  const [showCompare, setShowCompare] = useState(false)
  const [showBracket, setShowBracket] = useState(true)

  const {
    team, year, seed, conf, region,
    round_label, is_champion,
    team_sim, player_sim, combined_sim,
    key_stats = {},
    bracket_path = [],
    player_roster = [],
  } = match

  const { border, color, bg } = tierStyle(combined_sim)
  const badgeClass = resultBadgeClass(round_label, is_champion)
  const label      = resultLabel(round_label, is_champion)

  return (
    <div className="match-card">
      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="match-card-header">
        <div>
          <div className="match-rank mono">#{rank} Match</div>
          <div className="match-team-name display">{team}</div>
          <div className="match-year-conf mono">
            {year} · {region || conf || ''}
          </div>
        </div>
        <div className="badges">
          {seed && <span className="badge seed-badge">#{seed}</span>}
          {label && <span className={`badge ${badgeClass}`}>{label}</span>}
        </div>
      </div>

      {/* ── Body ──────────────────────────────────────────────────── */}
      <div className="match-card-body">

        {/* Similarity score display */}
        <div className="sim-score-card">
          {/* Big combined score badge */}
          <div className="sim-combined-badge" style={{ border, background: bg }}>
            <div className="sim-combined-number display" style={{ color }}>{combined_sim}</div>
            <div className="sim-combined-label mono">MATCH</div>
          </div>

          {/* Team + Player sub-bars */}
          <div className="sim-sub-scores">
            <SubBar label="Team"   value={team_sim}   type="team"   />
            <SubBar label="Player" value={player_sim} type="player" />
          </div>
        </div>

        {/* Stat comparison */}
        <div>
          <button className="expand-btn" onClick={() => setShowCompare(s => !s)}>
            {showCompare ? '▲ Hide Stats' : '▼ Compare Stats'}
          </button>
          {showCompare && (
            <div style={{ marginTop: 10 }}>
              <StatCompare queryStats={queryStats} matchStats={key_stats} />
            </div>
          )}
        </div>

        {/* Player roster for the MATCHED team */}
        <PlayerRoster players={player_roster} label="Match Roster" />

        {/* Bracket path */}
        <div>
          <button className="expand-btn" onClick={() => setShowBracket(s => !s)}>
            {showBracket ? '▲ Hide Bracket' : '▼ Show Bracket'}
          </button>
          {showBracket && (
            <div style={{ marginTop: 10 }}>
              <BracketPath games={bracket_path} />
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
