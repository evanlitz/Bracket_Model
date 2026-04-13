import TeamAvatar from './TeamAvatar'

function SeedBadge({ seed }) {
  if (!seed) return null
  return <span className="gs-seed mono">{seed}</span>
}

export default function GameSlot({ game, label, seedLookup = {}, onClick }) {
  if (!game) {
    return <div className="game-slot game-slot-empty" />
  }

  const { team1, team2, prob, winner, actual_winner, score1, score2, correct, round_name } = game

  const borderClass =
    correct === true  ? 'game-slot-correct' :
    correct === false ? 'game-slot-wrong'   : 'game-slot-unknown'

  const rawPct    = Math.round((prob ?? 0.5) * 100)
  const winnerPct = winner === team1 ? rawPct : 100 - rawPct
  const probPct   = winnerPct
  const loser     = winner === team1 ? team2 : team1

  const winnerScore = actual_winner === team1 ? score1 : score2
  const loserScore  = actual_winner === team1 ? score2 : score1

  const winnerSeed = seedLookup[winner]
  const loserSeed  = seedLookup[loser]

  return (
    <div
      className={`game-slot ${borderClass}${onClick ? ' game-slot-clickable' : ''}`}
      onClick={onClick ? () => onClick(game) : undefined}
    >
      <div className="gs-header mono">
        <span className="gs-round">{label || round_name}</span>
        <span className="gs-pct">{probPct}%</span>
      </div>

      <div className="gs-winner">
        <SeedBadge seed={winnerSeed} />
        <TeamAvatar team={winner} size={18} />
        <span className="gs-team-name">{winner}</span>
      </div>
      <div className="gs-loser">
        <SeedBadge seed={loserSeed} />
        <TeamAvatar team={loser} size={18} />
        <span className="gs-team-name">{loser}</span>
      </div>

      <div className="gs-bar-track">
        <div className="gs-bar-fill" style={{ width: `${probPct}%` }} />
      </div>

      {actual_winner && (
        <div className={`gs-result ${correct ? 'gs-result-correct' : 'gs-result-wrong'}`}>
          <span className="gs-result-name">{correct ? '✓' : '✗'} {actual_winner}</span>
          {winnerScore != null && loserScore != null && (
            <span className="gs-score">{winnerScore}–{loserScore}</span>
          )}
        </div>
      )}
    </div>
  )
}
