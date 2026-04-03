import { useState, useEffect, useMemo } from 'react'
import Bracket from './Bracket'
import MatchupModal from './MatchupModal'
import { applyPicksToGames, clearDownstreamPicks } from './bracketTree'

const ROUND_LABELS = { 1: 'R64', 2: 'R32', 3: 'S16', 4: 'E8', 5: 'F4', 6: 'NCG' }

export default function BracketViewer({ allTeams = [] }) {
  const [years, setYears]           = useState([])
  const [year, setYear]             = useState(null)
  const [data, setData]             = useState(null)
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState(null)
  const [selectedGame, setSelectedGame] = useState(null)
  const [picks, setPicks]           = useState({})

  const is2026 = year === 2026

  useEffect(() => {
    fetch('/api/bracket/years')
      .then(r => r.json())
      .then(ys => {
        const sorted = [...ys].sort((a, b) => b - a)
        setYears(sorted)
        setYear(sorted[0] ?? null)
      })
      .catch(() => {})
  }, [])

  async function loadBracket() {
    setLoading(true)
    setError(null)
    setData(null)
    setSelectedGame(null)
    setPicks({})
    try {
      const res = await fetch(`/api/bracket/${year}`)
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `${res.status} ${res.statusText}`)
      }
      setData(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // Seed lookup: prefer seeds embedded in bracket response, fall back to allTeams
  const seedLookup = useMemo(() => {
    if (data?.seeds && Object.keys(data.seeds).length > 0) return data.seeds
    const lkp = {}
    allTeams
      .filter(t => t.year === year && t.seed != null)
      .forEach(t => { lkp[t.team] = t.seed })
    return lkp
  }, [data, allTeams, year])

  // For 2026: apply user picks to propagate winners into downstream slots
  const computedGames = useMemo(() => {
    if (!data) return []
    if (!is2026 || Object.keys(picks).length === 0) return data.games
    return applyPicksToGames(data.games, picks)
  }, [data, picks, is2026])

  // The selected game, refreshed from computedGames so pick overrides are reflected
  const selectedComputedGame = useMemo(() => {
    if (!selectedGame || !computedGames.length) return null
    return computedGames.find(g => g.match_id === selectedGame.match_id) ?? selectedGame
  }, [selectedGame, computedGames])

  function handlePick(matchId, teamName) {
    setPicks(prev => {
      const withPick = { ...prev, [matchId]: teamName }
      return clearDownstreamPicks(withPick, matchId)
    })
    setSelectedGame(null)
  }

  function handleYearChange(newYear) {
    setYear(+newYear)
    setData(null)
    setSelectedGame(null)
    setPicks({})
  }

  return (
    <div className="bracket-viewer">
      <div className="bracket-toolbar">
        <div className="bracket-toolbar-inner">
          <div className="bracket-toolbar-title display">Bracket Predictor</div>
          <div className="bracket-toolbar-controls">
            <label className="bracket-year-label">
              <span className="mono" style={{ color: 'var(--cream-dim)', fontSize: '10px', letterSpacing: '1.5px' }}>
                YEAR
              </span>
              <select
                value={year}
                onChange={e => handleYearChange(e.target.value)}
              >
                {years.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            </label>
            <button
              className="search-btn"
              onClick={loadBracket}
              disabled={loading}
            >
              {loading ? 'Loading…' : 'Load Bracket'}
            </button>
          </div>
          {loading && (
            <div className="bracket-toolbar-hint mono">
              Training leave-year-out model — this takes ~30 seconds
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="state-msg" style={{ color: 'var(--red-bright)' }}>{error}</div>
      )}

      {!data && !loading && !error && (
        <div className="state-msg" style={{ maxWidth: 500 }}>
          {year === 2026
            ? 'Select 2026 and click Load Bracket to see the model\'s predictions for the upcoming tournament.'
            : 'Select a year and click Load Bracket. The model is trained on all other years, then predicts the selected year\'s bracket from scratch.'
          }
        </div>
      )}

      {data && (
        <>
          <BracketStats data={data} />
          <Bracket
            games={computedGames}
            seedLookup={seedLookup}
            onGameSelect={setSelectedGame}
          />
        </>
      )}

      {selectedComputedGame && (
        <MatchupModal
          game={selectedComputedGame}
          year={year}
          seedLookup={seedLookup}
          is2026={is2026}
          picks={picks}
          onClose={() => setSelectedGame(null)}
          onPick={handlePick}
        />
      )}
    </div>
  )
}

function BracketStats({ data }) {
  const { year, accuracy, accuracy_by_round } = data
  const roundEntries = Object.entries(accuracy_by_round).sort((a, b) => +a[0] - +b[0])
  const is2026 = year === 2026

  return (
    <div className="bracket-stats-header">
      <div className="bracket-overall">
        {is2026
          ? <div className="bracket-overall-pct mono" style={{ fontSize: '22px', color: 'var(--gold-bright)', textShadow: 'var(--glow-gold)' }}>2026</div>
          : <div className="bracket-overall-pct mono">{(accuracy * 100).toFixed(1)}%</div>
        }
        <div className="bracket-overall-label">{is2026 ? 'NCAA Tournament' : 'LYO Accuracy'}</div>
        {!is2026 && <div className="bracket-overall-year display">{year}</div>}
      </div>
      {!is2026 && (
        <div className="bracket-round-bars">
          {roundEntries.map(([rnd, acc]) => (
            <div key={rnd} className="bracket-round-bar-row">
              <span className="mono bracket-round-name">{ROUND_LABELS[+rnd] || `R${rnd}`}</span>
              <div className="bracket-round-bar-track">
                <div
                  className="bracket-round-bar-fill"
                  style={{ width: `${acc * 100}%` }}
                />
              </div>
              <span className="mono bracket-round-pct">{(acc * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      )}
      <div className="bracket-stats-note mono">
        {is2026
          ? <>Model trained on 2002–2025<br />predicting 2026 tournament</>
          : <>Model trained on all years<br />except {year} (leave-year-out)</>
        }
      </div>
    </div>
  )
}
