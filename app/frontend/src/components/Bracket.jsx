import RegionBracket from './RegionBracket'
import GameSlot from './GameSlot'

export default function Bracket({ games, seedLookup = {}, onGameSelect }) {
  const byId = {}
  games.forEach(g => { byId[g.match_id] = g })

  const sel = onGameSelect
    ? (game) => game && onGameSelect(game)
    : undefined

  return (
    <div className="bracket-scroll">
      <div className="bracket-layout">

        {/* Top half: South (LTR) | F4 Game 61 | East (RTL) */}
        <div className="bracket-half-row">
          <RegionBracket region="South" byId={byId} direction="ltr" seedLookup={seedLookup} onGameSelect={sel} />
          <div className="bracket-f4-col">
            <GameSlot game={byId[61]} label="F4" seedLookup={seedLookup} onClick={byId[61] ? sel : undefined} />
          </div>
          <RegionBracket region="East" byId={byId} direction="rtl" seedLookup={seedLookup} onGameSelect={sel} />
        </div>

        {/* National Championship */}
        <div className="bracket-ncg-row">
          <div className="bracket-center-label display">CHAMPIONSHIP</div>
          <GameSlot game={byId[63]} label="NCG" seedLookup={seedLookup} onClick={byId[63] ? sel : undefined} />
        </div>

        {/* Bottom half: West (LTR) | F4 Game 62 | Midwest (RTL) */}
        <div className="bracket-half-row">
          <RegionBracket region="West" byId={byId} direction="ltr" seedLookup={seedLookup} onGameSelect={sel} />
          <div className="bracket-f4-col">
            <GameSlot game={byId[62]} label="F4" seedLookup={seedLookup} onClick={byId[62] ? sel : undefined} />
          </div>
          <RegionBracket region="Midwest" byId={byId} direction="rtl" seedLookup={seedLookup} onGameSelect={sel} />
        </div>

      </div>
    </div>
  )
}
