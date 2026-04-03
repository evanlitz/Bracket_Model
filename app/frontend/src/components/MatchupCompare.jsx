import { HIGHER_BETTER, LOWER_BETTER, fmtStat } from './utils'

const MATCHUP_STATS = [
  // Efficiency — highest model importance
  { key: 'AdjEM',                   label: 'Adj Eff Margin',   group: 'Efficiency' },
  { key: 'AdjOE',                   label: 'Adj Offense',      group: 'Efficiency' },
  { key: 'AdjDE',                   label: 'Adj Defense',      group: 'Efficiency' },
  { key: 'AdjTempo',                label: 'Tempo',            group: 'Efficiency' },
  // Roster — engineered player features
  { key: 'two_way_depth',           label: 'Two-Way Depth',    group: 'Roster' },
  { key: 'star_eup',                label: 'Star EUP',         group: 'Roster' },
  { key: 'depth_eup',               label: 'Depth EUP',        group: 'Roster' },
  { key: 'interior_dom',            label: 'Interior Dom',     group: 'Roster' },
  { key: 'triple_threat',           label: 'Triple Threat',    group: 'Roster' },
  { key: 'returning_min_pct',       label: 'Returning Min%',   group: 'Roster' },
  { key: 'avg_height',              label: 'Avg Height',       group: 'Roster' },
  { key: 'd1_exp',                  label: 'D1 Experience',    group: 'Roster' },
  // Program pedigree
  { key: 'program_tourney_rate_l5', label: 'Tourney Rate 5yr', group: 'Program' },
  { key: 'program_f4_rate_l10',     label: 'F4 Rate 10yr',    group: 'Program' },
  // Four Factors
  { key: 'efg_pct_off',             label: 'eFG% Off',         group: 'Four Factors' },
  { key: 'efg_pct_def',             label: 'eFG% Def',         group: 'Four Factors' },
  { key: 'or_pct_off',              label: 'Off Reb%',         group: 'Four Factors' },
  { key: 'to_pct_off',              label: 'TO% Off',          group: 'Four Factors' },
  { key: 'blk_pct_def',             label: 'Blk% Def',         group: 'Four Factors' },
  // Last-10-game momentum
  { key: 'l10_net_eff',             label: 'L10 Net Eff',     group: 'Momentum' },
  { key: 'l10_off_eff',             label: 'L10 Off Eff',     group: 'Momentum' },
  { key: 'l10_def_eff',             label: 'L10 Def Eff',     group: 'Momentum' },
]

const GREEN = '#22c55e'
const RED   = '#ef4444'
const DIM   = 'rgba(168,159,136,0.6)'

// Returns 1 if team1 is better, 2 if team2 is better, 0 if neutral/unknown
function betterSide(key, v1, v2) {
  if (v1 == null || v2 == null) return 0
  if (Math.abs(v1 - v2) < 0.0001) return 0
  if (HIGHER_BETTER.has(key)) return v1 > v2 ? 1 : 2
  if (LOWER_BETTER.has(key))  return v1 < v2 ? 1 : 2
  return 0
}

// Bar fill fractions — each team "owns" half the bar, fill shows relative advantage
function barFills(key, v1, v2) {
  if (v1 == null || v2 == null) return [0.5, 0.5]
  const a1 = Math.abs(v1)
  const a2 = Math.abs(v2)
  const total = a1 + a2
  if (total === 0) return [0.5, 0.5]
  const lb = LOWER_BETTER.has(key)
  // For lower-better stats, invert so the better (lower) team gets the bigger bar
  const f1 = lb ? a2 / total : a1 / total
  const f2 = lb ? a1 / total : a2 / total
  const clamp = f => Math.max(0.08, Math.min(0.92, f))
  return [clamp(f1), clamp(f2)]
}

export default function MatchupCompare({ team1Name, team2Name, team1Stats, team2Stats }) {
  const s1 = team1Stats ?? {}
  const s2 = team2Stats ?? {}

  let lastGroup = null
  const rows = []

  for (const { key, label, group } of MATCHUP_STATS) {
    const v1 = s1[key] ?? null
    const v2 = s2[key] ?? null
    if (v1 == null && v2 == null) continue

    if (group !== lastGroup) {
      rows.push(
        <div key={`grp-${group}`} className="mc-group-label mono">
          {group.toUpperCase()}
        </div>
      )
      lastGroup = group
    }

    const better = betterSide(key, v1, v2)
    const [f1, f2] = barFills(key, v1, v2)
    const c1 = better === 1 ? GREEN : better === 2 ? RED : DIM
    const c2 = better === 2 ? GREEN : better === 1 ? RED : DIM
    const barC1 = better === 1 ? GREEN : better === 2 ? RED : 'rgba(255,255,255,0.15)'
    const barC2 = better === 2 ? GREEN : better === 1 ? RED : 'rgba(255,255,255,0.15)'

    rows.push(
      <div key={key} className="mc-row">
        <span className="mc-val mc-val-left mono" style={{ color: c1 }}>
          {v1 != null ? fmtStat(key, v1) : '—'}
        </span>
        <div className="mc-bar-wrap">
          {/* Two-column bar: left half grows right, right half grows left */}
          <div className="mc-bar-track">
            <div className="mc-half mc-half-left">
              <div className="mc-fill-left" style={{ width: `${f1 * 100}%`, background: barC1 }} />
            </div>
            <div className="mc-half mc-half-right">
              <div className="mc-fill-right" style={{ width: `${f2 * 100}%`, background: barC2 }} />
            </div>
          </div>
          <div className="mc-label mono">{label}</div>
        </div>
        <span className="mc-val mc-val-right mono" style={{ color: c2 }}>
          {v2 != null ? fmtStat(key, v2) : '—'}
        </span>
      </div>
    )
  }

  return (
    <div className="matchup-compare">
      <div className="mc-headers">
        <span className="mono" style={{ color: 'var(--cream-dim)', fontSize: 10, letterSpacing: 1 }}>
          {team1Name}
        </span>
        <span />
        <span className="mono" style={{ color: 'var(--cream-dim)', fontSize: 10, letterSpacing: 1, textAlign: 'right', display: 'block' }}>
          {team2Name}
        </span>
      </div>
      {rows}
    </div>
  )
}
