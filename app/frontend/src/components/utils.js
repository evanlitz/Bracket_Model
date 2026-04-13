export function resultBadgeClass(roundLabel, isChampion) {
  if (isChampion) return 'champ'
  const map = {
    'R64': 'r64', 'Round of 64': 'r64',
    'R32': 'r32', 'Round of 32': 'r32',
    'Sweet 16': 's16',
    'Elite 8': 'e8',
    'Final Four': 'f4',
    'Runner Up': 'runner-up',
    'Champion': 'champ',
  }
  return map[roundLabel] || 'r64'
}

export function resultLabel(roundLabel, isChampion) {
  if (isChampion) return '★ CHAMPION'
  if (roundLabel === 'Runner Up') return '★ RUNNER UP'
  return roundLabel || ''
}

// Format a stat value for display
export function fmtStat(key, val) {
  if (val == null) return '—'
  const pcts = [
    'efg_pct_off', 'efg_pct_def', 'to_pct_off', 'to_pct_def',
    'or_pct_off', 'or_pct_def', 'ftr_off', 'ftr_def',
    'fg3a_rate_off', 'fg3a_rate_def', 'fr_min_pct',
    'returning_min_pct', 'star_min_conc',
    'program_tourney_rate_l5', 'program_f4_rate_l10',
  ]
  if (pcts.includes(key)) {
    // Some stats stored as fraction (0.566), others as percent (56.6) — normalise both
    const pct = val > 1 ? val : val * 100
    return pct.toFixed(1) + '%'
  }
  const ones = ['AdjEM', 'AdjOE', 'AdjDE', 'AdjTempo',
                 'l10_off_eff', 'l10_def_eff', 'l10_net_eff']
  if (ones.includes(key)) return val.toFixed(1)
  if (key === 'avg_height') return val.toFixed(1) + '"'
  if (key === 'd1_exp') return val.toFixed(2)
  return val.toFixed(3)
}

// Higher = better direction (true = more is better)
export const HIGHER_BETTER = new Set([
  'AdjEM', 'AdjOE', 'AdjTempo',
  'efg_pct_off', 'or_pct_off', 'ftr_off',
  'fg2_pct_off', 'fg3_pct_off',
  'blk_pct_def', 'stl_rate_def',
  'd1_exp', 'avg_height',
  'program_tourney_rate_l5', 'program_f4_rate_l10',
  'l10_win_pct', 'l10_net_eff', 'l10_off_eff',
  'momentum_off',
  'star_eup', 'depth_eup', 'two_way_depth',
  'interior_dom', 'triple_threat',
  'returning_min_pct',
  'apl_off',
])

export const LOWER_BETTER = new Set([
  'AdjDE',
  'to_pct_off', 'efg_pct_def', 'or_pct_def',
  'blk_pct_off', 'nst_rate_off',
  'l10_def_eff', 'momentum_def',
  'fr_min_pct',
  'star_min_conc',
])

export function diffClass(key, queryVal, matchVal) {
  if (queryVal == null || matchVal == null) return 'neutral'
  const diff = matchVal - queryVal
  const eps  = 0.0001
  if (Math.abs(diff) < eps) return 'neutral'
  const higherBetter = HIGHER_BETTER.has(key)
  const lowerBetter  = LOWER_BETTER.has(key)
  if (!higherBetter && !lowerBetter) return 'neutral'
  const better = (higherBetter && diff > 0) || (lowerBetter && diff < 0)
  return better ? 'better' : 'worse'
}
