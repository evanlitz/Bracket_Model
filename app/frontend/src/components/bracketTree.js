/**
 * bracketTree.js
 *
 * Encodes the NCAA tournament bracket tree structure.
 * Maps each match_id to its parent game + which slot (team1/team2) the winner fills.
 * Used to propagate user picks forward through the 2026 bracket.
 *
 * Match ID ranges (from RegionBracket.jsx):
 *   South:   R64 [1-8]   R32 [9-12]  S16 [13-14] E8 [15]  → F4 [61]
 *   West:    R64 [16-23] R32 [24-27] S16 [28-29] E8 [30]  → F4 [62]
 *   East:    R64 [31-38] R32 [39-42] S16 [43-44] E8 [45]  → F4 [61]
 *   Midwest: R64 [46-53] R32 [54-57] S16 [58-59] E8 [60]  → F4 [62]
 *   F4: [61, 62] → NCG [63]
 */

export const PARENT_MAP = {
  // South: R64 → R32
  1:  { parentId: 9,  slot: 'team1' },  2:  { parentId: 9,  slot: 'team2' },
  3:  { parentId: 10, slot: 'team1' },  4:  { parentId: 10, slot: 'team2' },
  5:  { parentId: 11, slot: 'team1' },  6:  { parentId: 11, slot: 'team2' },
  7:  { parentId: 12, slot: 'team1' },  8:  { parentId: 12, slot: 'team2' },
  // South: R32 → S16
  9:  { parentId: 13, slot: 'team1' },  10: { parentId: 13, slot: 'team2' },
  11: { parentId: 14, slot: 'team1' },  12: { parentId: 14, slot: 'team2' },
  // South: S16 → E8
  13: { parentId: 15, slot: 'team1' },  14: { parentId: 15, slot: 'team2' },
  // South: E8 → F4
  15: { parentId: 61, slot: 'team1' },

  // West: R64 → R32
  16: { parentId: 24, slot: 'team1' },  17: { parentId: 24, slot: 'team2' },
  18: { parentId: 25, slot: 'team1' },  19: { parentId: 25, slot: 'team2' },
  20: { parentId: 26, slot: 'team1' },  21: { parentId: 26, slot: 'team2' },
  22: { parentId: 27, slot: 'team1' },  23: { parentId: 27, slot: 'team2' },
  // West: R32 → S16
  24: { parentId: 28, slot: 'team1' },  25: { parentId: 28, slot: 'team2' },
  26: { parentId: 29, slot: 'team1' },  27: { parentId: 29, slot: 'team2' },
  // West: S16 → E8
  28: { parentId: 30, slot: 'team1' },  29: { parentId: 30, slot: 'team2' },
  // West: E8 → F4
  30: { parentId: 62, slot: 'team1' },

  // East: R64 → R32
  31: { parentId: 39, slot: 'team1' },  32: { parentId: 39, slot: 'team2' },
  33: { parentId: 40, slot: 'team1' },  34: { parentId: 40, slot: 'team2' },
  35: { parentId: 41, slot: 'team1' },  36: { parentId: 41, slot: 'team2' },
  37: { parentId: 42, slot: 'team1' },  38: { parentId: 42, slot: 'team2' },
  // East: R32 → S16
  39: { parentId: 43, slot: 'team1' },  40: { parentId: 43, slot: 'team2' },
  41: { parentId: 44, slot: 'team1' },  42: { parentId: 44, slot: 'team2' },
  // East: S16 → E8
  43: { parentId: 45, slot: 'team1' },  44: { parentId: 45, slot: 'team2' },
  // East: E8 → F4
  45: { parentId: 61, slot: 'team2' },

  // Midwest: R64 → R32
  46: { parentId: 54, slot: 'team1' },  47: { parentId: 54, slot: 'team2' },
  48: { parentId: 55, slot: 'team1' },  49: { parentId: 55, slot: 'team2' },
  50: { parentId: 56, slot: 'team1' },  51: { parentId: 56, slot: 'team2' },
  52: { parentId: 57, slot: 'team1' },  53: { parentId: 57, slot: 'team2' },
  // Midwest: R32 → S16
  54: { parentId: 58, slot: 'team1' },  55: { parentId: 58, slot: 'team2' },
  56: { parentId: 59, slot: 'team1' },  57: { parentId: 59, slot: 'team2' },
  // Midwest: S16 → E8
  58: { parentId: 60, slot: 'team1' },  59: { parentId: 60, slot: 'team2' },
  // Midwest: E8 → F4
  60: { parentId: 62, slot: 'team2' },

  // F4 → NCG
  61: { parentId: 63, slot: 'team1' },
  62: { parentId: 63, slot: 'team2' },
}

/**
 * Apply user picks to the games array (2026 only).
 * For each pick, overwrites the parent game's team1 or team2 slot.
 *
 * @param {Array} originalGames - games array from bracket_loo.json
 * @param {Object} picks        - { [match_id]: teamName }
 * @returns {Array} new games array with overridden team names
 */
export function applyPicksToGames(originalGames, picks) {
  const byId = {}
  originalGames.forEach(g => { byId[g.match_id] = { ...g } })

  Object.entries(picks).forEach(([matchId, pickedTeam]) => {
    const entry = PARENT_MAP[+matchId]
    if (!entry) return
    const parentGame = byId[entry.parentId]
    if (parentGame) parentGame[entry.slot] = pickedTeam
  })

  return Object.values(byId)
}

/**
 * When a pick changes, all ancestor games in the bracket tree may have
 * had their participants changed, making existing picks for those games stale.
 * Walk upward and remove picks for all ancestor games.
 *
 * @param {Object} picks          - current picks map
 * @param {number} changedMatchId - the game that just got a new pick
 * @returns {Object} new picks with downstream invalidations removed
 */
export function clearDownstreamPicks(picks, changedMatchId) {
  const toInvalidate = new Set()
  let cur = PARENT_MAP[+changedMatchId]
  while (cur) {
    toInvalidate.add(cur.parentId)
    cur = PARENT_MAP[cur.parentId]
  }
  const next = { ...picks }
  toInvalidate.forEach(id => delete next[id])
  return next
}
