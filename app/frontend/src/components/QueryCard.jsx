import { resultBadgeClass } from './utils'
import PlayerRoster from './PlayerRoster'
import TeamAvatar from './TeamAvatar'

const TEAM_DISPLAY = [
  { key: 'AdjEM',        label: 'Adj EM',  fmt: v => v?.toFixed(1) },
  { key: 'AdjOE',        label: 'Adj OE',  fmt: v => v?.toFixed(1) },
  { key: 'AdjDE',        label: 'Adj DE',  fmt: v => v?.toFixed(1) },
  { key: 'AdjTempo',     label: 'Tempo',   fmt: v => v?.toFixed(1) },
  { key: 'efg_pct_off',  label: 'eFG% O',  fmt: v => v != null ? (v * 100).toFixed(1) + '%' : null },
  { key: 'efg_pct_def',  label: 'eFG% D',  fmt: v => v != null ? (v * 100).toFixed(1) + '%' : null },
  { key: 'or_pct_off',   label: 'OR%',     fmt: v => v != null ? (v * 100).toFixed(1) + '%' : null },
  { key: 'd1_exp',       label: 'D1 Exp',  fmt: v => v?.toFixed(2) },
]

const PLAYER_DISPLAY = [
  { key: 'star_eup',          label: 'Star EUP',  fmt: v => v?.toFixed(3) },
  { key: 'depth_eup',         label: 'Depth EUP', fmt: v => v?.toFixed(3) },
  { key: 'triple_threat',     label: 'Triple',    fmt: v => v?.toFixed(4) },
  { key: 'interior_dom',      label: 'Interior',  fmt: v => v?.toFixed(3) },
  { key: 'returning_min_pct', label: 'Returning', fmt: v => v != null ? (v * 100).toFixed(0) + '%' : null },
  { key: 'two_way_depth',     label: 'Two-Way',   fmt: v => v?.toFixed(3) },
]

export default function QueryCard({ profile }) {
  if (!profile) return null
  const { team, year, seed, conf, round_label, is_champion, key_stats = {}, player_roster = [] } = profile

  const badgeClass = resultBadgeClass(round_label, is_champion)

  return (
    <div className="query-card">
      <div className="query-card-team-header">
        <TeamAvatar team={team} size={48} />
        <div className="team-name-large display">{team}</div>
      </div>
      <div className="team-meta">
        <span className="badge mono">{year}</span>
        {seed && <span className="badge seed-badge">#{seed} Seed</span>}
        {conf && <span className="badge">{conf}</span>}
        {round_label && (
          <span className={`badge ${badgeClass}`}>
            {is_champion ? '★ CHAMPION' : round_label}
          </span>
        )}
      </div>

      {/* Team stats */}
      <div className="section-label">Team Stats</div>
      <div className="stat-grid" style={{ marginTop: 8, marginBottom: 12 }}>
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

      {/* Aggregated player profile */}
      <div className="section-label">Player Profile</div>
      <div className="stat-grid" style={{ marginTop: 8, marginBottom: 12 }}>
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

      {/* Individual player roster */}
      <PlayerRoster players={player_roster} label="Roster" />
    </div>
  )
}
