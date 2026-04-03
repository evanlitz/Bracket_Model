import { useState, useEffect } from 'react'

const ROUND_ORDER = ['1', '2', '3', '4', '5', '6']
const ROUND_LABELS = { '1': 'R64', '2': 'R32', '3': 'S16', '4': 'E8', '5': 'F4', '6': 'NCG' }

function pct(v) {
  if (v == null) return '—'
  const p = Math.round(v * 100)
  return p === 0 ? '<1%' : p === 100 ? '>99%' : `${p}%`
}

// ── Accuracy pill ─────────────────────────────────────────────────────────────

function AccPill({ correct, total, label, active, onClick }) {
  const acc = total > 0 ? correct / total : null
  return (
    <button
      className={`sc-acc-pill${active ? ' active' : ''}${total === 0 ? ' empty' : ''}`}
      onClick={onClick}
      disabled={total === 0}
    >
      <span className="sc-pill-label mono">{label}</span>
      {total > 0
        ? <span className="sc-pill-pct mono">{Math.round(acc * 100)}%</span>
        : <span className="sc-pill-pct mono">—</span>
      }
      {total > 0 && <span className="sc-pill-frac mono">{correct}/{total}</span>}
    </button>
  )
}

// ── Game card ─────────────────────────────────────────────────────────────────

function GameCard({ game }) {
  const { team1, team2, score1, score2, model_winner, model_prob_t1,
          actual_winner, actual_winner_prob, completed, correct, region, round_name } = game

  const prob1 = model_prob_t1 ?? 0.5
  const prob2 = 1 - prob1

  const hasScore = score1 != null && score2 != null

  return (
    <div className={`sc-card ${!completed ? 'sc-card-upcoming' : correct ? 'sc-card-correct' : 'sc-card-wrong'}`}>

      {/* Card header */}
      <div className="sc-card-header">
        <span className="sc-card-tag mono">{region} · {round_name}</span>
        {completed && (
          <span className={`sc-card-result ${correct ? 'correct' : 'wrong'}`}>
            {correct ? '✓' : '✗'}
          </span>
        )}
        {!completed && <span className="sc-card-upcoming-badge mono">UPCOMING</span>}
      </div>

      {/* Team rows */}
      {[
        { team: team1, score: score1, prob: prob1 },
        { team: team2, score: score2, prob: prob2 },
      ].map(({ team, score, prob }) => {
        const isModelPick = team === model_winner
        const isActualWinner = team === actual_winner
        const isActualLoser = completed && actual_winner && !isActualWinner

        return (
          <div
            key={team}
            className={`sc-team-row
              ${isActualWinner ? 'sc-team-winner' : ''}
              ${isActualLoser  ? 'sc-team-loser'  : ''}
              ${!completed && isModelPick ? 'sc-team-model-pick' : ''}
            `}
          >
            {/* Probability bar */}
            <div className="sc-bar-track">
              <div
                className={`sc-bar-fill ${isModelPick ? 'sc-bar-model' : ''}`}
                style={{ width: `${Math.round(prob * 100)}%` }}
              />
            </div>

            <div className="sc-team-info">
              <span className="sc-team-name">{team}</span>
              {hasScore && isActualWinner && (
                <span className="sc-score mono">{isActualWinner ? Math.max(score1, score2) : Math.min(score1, score2)}</span>
              )}
              {hasScore && isActualLoser && (
                <span className="sc-score sc-score-loser mono">{isActualWinner ? Math.max(score1, score2) : Math.min(score1, score2)}</span>
              )}
            </div>

            <span className={`sc-prob mono ${isModelPick ? 'sc-prob-model' : ''}`}>
              {pct(prob)}
            </span>
          </div>
        )
      })}

      {/* Footer: model confidence on actual winner */}
      {completed && actual_winner_prob != null && (
        <div className="sc-card-footer mono">
          Model gave {actual_winner} {pct(actual_winner_prob)}
        </div>
      )}
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function Scorecard() {
  const [data,        setData]        = useState(null)
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState(null)
  const [activeRound, setActiveRound] = useState('all')

  useEffect(() => {
    setLoading(true)
    fetch('/api/scorecard/2026')
      .then(r => {
        if (!r.ok) return r.json().then(e => { throw new Error(e.detail || r.statusText) })
        return r.json()
      })
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  if (loading) return (
    <div className="sc-viewer">
      <div className="sc-loading">
        <div className="sc-spinner" />
        <div className="mono" style={{ color: 'var(--cream-dim)', fontSize: '0.82rem' }}>Loading scorecard…</div>
      </div>
    </div>
  )

  if (error) return (
    <div className="sc-viewer">
      <div className="sc-error mono">{error}</div>
    </div>
  )

  if (!data) return null

  const { accuracy, games } = data
  const byRound = accuracy.by_round

  // All rounds that have at least one completed game
  const completedRounds = ROUND_ORDER.filter(r => byRound[r]?.total > 0)
  const latestRound = completedRounds[completedRounds.length - 1] ?? '1'

  // Filter games for display
  const displayGames = activeRound === 'all'
    ? games
    : games.filter(g => String(g.round) === activeRound)

  // Group by round then region
  const grouped = {}
  for (const g of displayGames) {
    const rk = String(g.round)
    if (!grouped[rk]) grouped[rk] = {}
    const reg = g.region || 'Other'
    if (!grouped[rk][reg]) grouped[rk][reg] = []
    grouped[rk][reg].push(g)
  }

  return (
    <div className="sc-viewer">

      {/* Header */}
      <div className="sc-header">
        <div>
          <div className="sc-header-title display">2026 Live Scorecard</div>
          <div className="sc-header-sub mono">Model predictions vs actual tournament results</div>
        </div>
        {accuracy.total > 0 && (
          <div className="sc-overall">
            <span className="sc-overall-pct mono">{Math.round(accuracy.overall * 100)}%</span>
            <span className="sc-overall-label mono">{accuracy.correct}/{accuracy.total} correct</span>
          </div>
        )}
      </div>

      {/* Round accuracy pills */}
      <div className="sc-pills">
        <AccPill
          label="All"
          correct={accuracy.correct}
          total={accuracy.total}
          active={activeRound === 'all'}
          onClick={() => setActiveRound('all')}
        />
        {ROUND_ORDER.map(r => {
          const rd = byRound[r]
          const upcoming = games.some(g => String(g.round) === r && !g.completed)
          return (
            <AccPill
              key={r}
              label={ROUND_LABELS[r]}
              correct={rd?.correct ?? 0}
              total={rd?.total ?? 0}
              active={activeRound === r}
              onClick={() => setActiveRound(r)}
            />
          )
        })}
      </div>

      {/* Games */}
      {ROUND_ORDER.filter(r => grouped[r]).map(r => {
        const isLateRound = parseInt(r) >= 4
        const allRoundGames = Object.values(grouped[r]).flat()
        return (
          <div key={r} className="sc-round-section">
            <div className="sc-round-header">
              <span className="sc-round-title display">{ROUND_LABELS[r]}</span>
              {byRound[r] ? (
                <span className="sc-round-acc mono">
                  {byRound[r].correct}/{byRound[r].total} · {Math.round(byRound[r].accuracy * 100)}%
                </span>
              ) : (
                <span className="sc-round-acc mono">
                  {allRoundGames.length} upcoming
                </span>
              )}
            </div>

            {isLateRound ? (
              <div className="sc-cards-grid sc-cards-grid-late">
                {allRoundGames.map(g => <GameCard key={g.match_id} game={g} />)}
              </div>
            ) : (
              Object.entries(grouped[r])
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([region, regionGames]) => (
                  <div key={region} className="sc-region-group">
                    <div className="sc-region-label mono">{region}</div>
                    <div className="sc-cards-grid">
                      {regionGames.map(g => <GameCard key={g.match_id} game={g} />)}
                    </div>
                  </div>
                ))
            )}
          </div>
        )
      })}

    </div>
  )
}
