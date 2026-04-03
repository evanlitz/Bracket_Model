export default function BracketPath({ games = [] }) {
  if (!games.length) {
    return (
      <div className="bracket-path">
        <div className="bracket-path-header">Tournament Path</div>
        <div className="mono" style={{ fontSize: '0.7rem', color: 'var(--cream-dim)' }}>
          No bracket data available.
        </div>
      </div>
    )
  }

  return (
    <div className="bracket-path">
      <div className="bracket-path-header">Tournament Path</div>
      {games.map((g, i) => (
        <div key={i} className={`bracket-game ${g.outcome === 'W' ? 'win' : 'loss'}`}>
          <div className="bracket-round-label mono">{g.round_name}</div>
          <div className="bracket-opponent">
            {g.opp_seed ? (
              <span className="bracket-seed-badge mono">#{g.opp_seed} </span>
            ) : null}
            {g.opponent}
          </div>
          {g.team_score != null && g.opp_score != null ? (
            <div className="bracket-score mono">
              {g.team_score}–{g.opp_score}
            </div>
          ) : (
            <div className="bracket-score mono">—</div>
          )}
          <div className={`bracket-outcome ${g.outcome}`}>{g.outcome}</div>
        </div>
      ))}
    </div>
  )
}
