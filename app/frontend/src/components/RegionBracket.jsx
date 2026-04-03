import GameSlot from './GameSlot'

// Fixed match ID ranges per region — consistent across all bracket years
const REGION_ROUNDS = {
  South:   { r64: [1,2,3,4,5,6,7,8],          r32: [9,10,11,12],   s16: [13,14], e8: [15] },
  West:    { r64: [16,17,18,19,20,21,22,23],   r32: [24,25,26,27], s16: [28,29], e8: [30] },
  East:    { r64: [31,32,33,34,35,36,37,38],   r32: [39,40,41,42], s16: [43,44], e8: [45] },
  Midwest: { r64: [46,47,48,49,50,51,52,53],   r32: [54,55,56,57], s16: [58,59], e8: [60] },
}

export default function RegionBracket({ region, byId, direction, seedLookup = {}, onGameSelect }) {
  const { r64, r32, s16, e8 } = REGION_ROUNDS[region]

  // rounds[0] = R64 (8 games), rounds[1] = R32 (4), rounds[2] = S16 (2), rounds[3] = E8 (1)
  const rounds = [r64, r32, s16, e8]

  // RTL: reverse so E8 column is displayed on the left (toward center)
  const displayRounds = direction === 'rtl' ? [...rounds].reverse() : rounds

  return (
    <div className="region-bracket">
      <div className="region-label mono">{region.toUpperCase()}</div>
      <div className={`region-rounds region-rounds-${direction}`}>
        {displayRounds.map((ids, colIdx) => {
          // roundDepth: 0=R64 (smallest slots), 3=E8 (tallest slots)
          const roundDepth = direction === 'rtl'
            ? rounds.length - 1 - colIdx
            : colIdx
          const slotMultiplier = Math.pow(2, roundDepth)

          return (
            <div key={colIdx} className="round-col">
              {ids.map(id => (
                <div
                  key={id}
                  className={`game-wrapper game-wrapper-${direction}`}
                  style={{ height: `calc(var(--slot-h) * ${slotMultiplier})` }}
                >
                  <GameSlot
                    game={byId[id]}
                    seedLookup={seedLookup}
                    onClick={onGameSelect && byId[id] ? onGameSelect : undefined}
                  />
                </div>
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}
